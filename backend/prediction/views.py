import pandas as pd
import numpy as np
from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from sklearn.linear_model import ElasticNet
from sklearn.metrics import r2_score, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from django.views.decorators.http import require_POST
from aivle_big.decorators import login_required
from aivle_big.exceptions import ValidationError, NotFoundError, InternalServerError, InvalidRequestError, UnauthorizedError, ServiceUnavailableError
from .models import PredictionSession, PredictionResult
from .services import fetch_market_prices as request_market_prices
from .services import fetch_weather_data as request_weather_data
from django.db import transaction
import json
import logging
import uuid
import os
from django.utils import timezone
from django.views.decorators.http import require_http_methods
logger = logging.getLogger(__name__)

CSV_FILE_PATH = 'prediction/all_crop_data.csv'  # 수익률 예측
CSV_FILE_PATH_1 = 'prediction/predict_code.csv'  # 품목 코드
re = {'서울': ['1101', '108'], '부산': ['2100', '159'], '대구': ['2200', '143'], '광주': ['2401', '156'], '대전': ['2501', '133']}

def get_crop_names(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid request method. Only GET is allowed.'}, status=405)
    try:
        crop_df= pd.read_csv(CSV_FILE_PATH_1)
        crop_names = crop_df['품목명'].dropna().tolist()
        return JsonResponse({'crop_names': crop_names})
    except Exception as e:
        return JsonResponse({'error': f"An unexpected error occured: {str(e)}"}, status=500)

def get_region_names(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid request method. Only GET is allowed'}, status=400)
    try:
        region_names = list(re.keys())
        return JsonResponse({'region_names': region_names})
    except Exception as e:
        return JsonResponse({'error': f"An unexpected error occured: {str(e)}"}, status = 500)

def read_csv_data():
    df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8')
    df['소득률 (%)'] = df['소득률 (%)'].astype(str)
    df['부가가치율 (%)'] = df['부가가치율 (%)'].astype(str)
    df['농가수취가격 (원/kg)'] = df['농가수취가격 (원/kg)'].astype(str)
    return df

def fetch_crop_data(crop_name, df, land_area, crop_ratio):
    crop_data = df[df['작물명'] == crop_name]
    if not crop_data.empty:
        latest_crop_data = crop_data.sort_values(by='시점', ascending=False).iloc[0]
        crop_income = latest_crop_data['소득 (원)']
        latest_year = latest_crop_data['시점']
        adjusted_income = (crop_income / 302.5) * land_area * crop_ratio  
        adjusted_data = latest_crop_data.copy()
        # The source statistics are per 10a (302.5 pyeong). Scale quantities
        # and aggregate costs only; year, percentages, and per-kg unit prices
        # must remain unchanged.
        non_scalable_columns = {
            '시점', '농가수취가격 (원/kg)', '부가가치율 (%)', '소득률 (%)', '작물명'
        }
        for col in adjusted_data.index:
            if col not in non_scalable_columns and isinstance(adjusted_data[col], (int, float, np.number)):
                adjusted_data[col] = (adjusted_data[col] / 302.5) * land_area * crop_ratio
        return adjusted_income, adjusted_data.to_dict(), latest_year
    else:
        return None, None, None

def fetch_market_prices(crop_name, region, start_date, end_date):
    price_code = pd.read_csv(CSV_FILE_PATH_1, encoding='utf-8')
    return request_market_prices(crop_name, region, start_date, end_date, price_code, re)

def fetch_weather_data(region):
    return request_weather_data(region, re)

def _build_price_dataset(merged_df):
    if 'price' not in merged_df:
        raise ValidationError("Market data does not contain a price column.")

    frame = merged_df.copy().sort_values('tm').reset_index(drop=True)
    frame['tm'] = pd.to_datetime(frame['tm'], errors='coerce')
    frame['observed_price'] = pd.to_numeric(frame['price'], errors='coerce').ffill()
    frame = frame.dropna(subset=['tm', 'observed_price'])
    frame['year'] = frame['tm'].dt.year
    frame['month_sin'] = np.sin(2 * np.pi * frame['tm'].dt.month / 12)
    frame['month_cos'] = np.cos(2 * np.pi * frame['tm'].dt.month / 12)
    frame['day_sin'] = np.sin(2 * np.pi * frame['tm'].dt.day / 31)
    frame['day_cos'] = np.cos(2 * np.pi * frame['tm'].dt.day / 31)

    # Features for day t may use prices observed through day t only. The old
    # implementation calculated rolling values from the shifted target, which
    # leaked tomorrow's price into both training and evaluation features.
    for lag in range(1, 8):
        frame[f'price_lag_{lag}'] = frame['observed_price'].shift(lag - 1)
    frame['price_ma_7'] = frame['observed_price'].rolling(window=7).mean()
    frame['price_ma_30'] = frame['observed_price'].rolling(window=30).mean()
    frame['temp_diff'] = frame['maxTa'] - frame['minTa']
    frame['target_price'] = frame['observed_price'].shift(-1)

    excluded = {'tm', 'price', 'observed_price', 'target_price', 'itemname'}
    feature_columns = [column for column in frame.columns if column not in excluded]
    frame[feature_columns] = frame[feature_columns].apply(pd.to_numeric, errors='coerce')
    target_features = frame.iloc[[-1]][feature_columns].dropna(axis=1, how='all')
    feature_columns = target_features.columns.tolist()
    training = frame.dropna(subset=feature_columns + ['target_price'])
    if len(training) < 10 or len(feature_columns) == 0:
        raise ValidationError("Not enough aligned market and weather data for prediction.")
    return training[feature_columns], training['target_price'], frame.iloc[[-1]][feature_columns]


def predict_prices(merged_df, _weather_df=None):
    X, y, target = _build_price_dataset(merged_df)
    split_index = max(1, int(len(X) * 0.8))
    if len(X) - split_index < 2:
        raise ValidationError("Not enough evaluation data for prediction.")
    X_train, X_test = X.iloc[:split_index], X.iloc[split_index:]
    y_train, y_test = y.iloc[:split_index], y.iloc[split_index:]
    model = make_pipeline(
        StandardScaler(),
        ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=10000),
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    r2 = float(r2_score(y_test, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_test, y_pred)))
    if not np.isfinite(r2):
        r2 = 0.0
    pred_value = max(0, int(round(float(model.predict(target)[0]))))
    return pred_value, r2, rmse

def convert_values(data):
    if isinstance(data, dict):
        return {k: convert_values(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_values(i) for i in data]
    elif isinstance(data, (np.int64, np.int32)):
        return int(data)
    elif isinstance(data, np.float64):
        return float(data)
    else:
        return data

from django.db import transaction

@login_required
@require_POST
def predict_income(request):
    logger.debug("Entered predict_income function")
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id') or str(uuid.uuid4())
        session_name = data.get('session_name', 'Default Prediction Session')
        land_area = float(data['land_area'])
        
        logger.debug(f"Received data: {data}")
        
        if isinstance(data['crop_names'], list):
            crop_names = data['crop_names']
        elif isinstance(data['crop_names'], str):
            crop_names = data['crop_names'].split(',')
        else:
            logger.error("Invalid format for crop_names")
            return JsonResponse({'error': 'Invalid format for crop_names'}, status=400)

        crop_ratios = [float(ratio) for ratio in data['crop_ratios']]
        if len(crop_names) != len(crop_ratios):
            raise ValidationError('작물과 비율의 개수가 일치해야 합니다.')
        if not crop_names or any(not name.strip() for name in crop_names):
            raise ValidationError('작물을 하나 이상 선택해야 합니다.')
        if len(set(crop_names)) != len(crop_names):
            raise ValidationError('같은 작물은 중복해서 선택할 수 없습니다.')
        if land_area <= 0 or any(ratio <= 0 for ratio in crop_ratios):
            raise ValidationError('면적과 작물 비율은 0보다 커야 합니다.')
        if not np.isclose(sum(crop_ratios), 1.0, rtol=0, atol=1e-9):
            logger.error("작물 비율의 합은 1이 되어야합니다.")
            raise ValidationError('작물 비율의 합은 1이 되어야합니다.')
        if len(str(session_id)) > 36:
            raise ValidationError('세션 식별자가 너무 깁니다.')
        if PredictionSession.objects.filter(user=request.user, session_id=session_id).exists():
            raise ValidationError('이미 존재하는 예측 세션입니다.')

        region = data['region']
        df = read_csv_data()
        logger.debug(f"Loaded crop data: {df.head()}")
        
        df_2 = fetch_weather_data(region)
        if df_2 is None or df_2.empty:
            logger.error('날씨데이터를 불러오는 과정에서 오류가 발생했습니다.')
            return JsonResponse({'error': '날씨데이터를 불러오는 과정에서 오류가 발생했습니다.'}, status=404)
        
        total_predicted_value = 0
        crop_results = []
        r2_scores = []

        try:
            with transaction.atomic():
                prediction_session = PredictionSession.objects.create(
                    user=request.user,
                    session_id=session_id,
                    session_name=session_name,
                    crop_names=', '.join(crop_names),
                    land_area=land_area,
                    region=region,
                    total_income=0
                )
                
                start_date = df_2['tm'].iloc[0].strftime('%Y%m%d')
                end_date = df_2['tm'].iloc[-1].strftime('%Y%m%d')
            
                for crop_name, crop_ratio in zip(crop_names, crop_ratios):
                    adjusted_income, adjusted_data, latest_year = fetch_crop_data(crop_name, df, land_area, crop_ratio)
                    logger.debug(f"Fetched crop data for {crop_name}: {adjusted_income}, {latest_year}")
                    
                    if adjusted_income is None:
                        logger.error(f"No data found for {crop_name}")
                        raise ValueError(f"{crop_name}에 대한 데이터는 존재하지 않습니다.")
                    
                    total_predicted_value += int(adjusted_income)
                    
                    df_1 = fetch_market_prices(crop_name, region, start_date, end_date)
                    if df_1 is None or df_1.empty:
                        logger.error(f"No market data found for {crop_name}")
                        raise ValueError(f"{crop_name}에 대한 도매 데이터를 불러오는 과정에서 오류가 발생했습니다.")
                    
                    logger.debug(f"Market data for {crop_name}: {df_1.head()}")
                    
                    merged_df = pd.merge(df_2, df_1, on='tm', how='left')
                    logger.debug(f"Merged dataframe: {merged_df.head()}")
                    if 'price' not in merged_df:
                        logger.error(f"Missing 'price' in merged DataFrame for {crop_name}" )
                    merged_df.drop('itemname', axis=1, inplace=True)
                    

                    pred_value, r2, rmse = predict_prices(merged_df, df_2)
                    logger.debug(f"Predicted prices for {crop_name}: {pred_value}")
                    r2_scores.append(r2)

                    PredictionResult.objects.create(
                        session=prediction_session,
                        crop_name=crop_name,
                        predicted_income=int(adjusted_income), 
                        adjusted_data=convert_values(adjusted_data),
                        price=pred_value,
                        latest_year=latest_year,
                        r2_score=r2,
                        rmse=rmse
                    )
                    
                    df_1_json = df_1.to_json(orient='records', date_format='iso')
                    crop_results.append({
                        'crop_name': crop_name,
                        'latest_year': int(latest_year),
                        'adjusted_data': convert_values(adjusted_data),
                        'price': pred_value,
                        'r2_score': r2,
                        'rmse': rmse,
                        'crop_chart_data': json.loads(df_1_json)
                    })
                
                prediction_session.total_income = int(total_predicted_value)
                prediction_session.save()
            
        except (ValidationError, NotFoundError, ServiceUnavailableError):
            raise
        except ValueError as ve:
            logger.error(f"ValueError: {ve}")
            return JsonResponse({'error': str(ve)}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {repr(e)}, Type: {type(e)}, Args: {e.args}")
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
        
        return JsonResponse({
            'session_id': session_id,
            'total_income': int(total_predicted_value),
            'results': crop_results,
            'r2_scores': r2_scores
        }, status=200)

    except (ValidationError, NotFoundError, ServiceUnavailableError):
        raise
    except json.JSONDecodeError:
        logger.error("JSON decoding failed")
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected error: {repr(e)}, Type: {type(e)}, Args: {e.args}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)
    
    
@login_required
def list_prediction_sessions(request):
    try:
        sessions = PredictionSession.objects.filter(user=request.user).order_by('-created_at')
        session_list = []

        for session in sessions:
            results = session.results.all()
            session_details = {
                'session_id': session.session_id,
                'session_name': session.session_name,
                'crop_names': session.crop_names,
                'land_area': session.land_area,
                'region': session.region,
                'total_income': session.total_income,
                'created_at': timezone.localtime(session.created_at).strftime('%Y-%m-%d %H:%M'),
                'results': []
            }
            for result in results:
                session_details['results'].append({
                    'crop_name': result.crop_name,
                    'predicted_income': result.predicted_income,
                    'r2_score': result.r2_score,
                    'price': result.price,
                    'rmse': result.rmse
                })
            session_list.append(session_details)

        return JsonResponse(session_list, safe=False)

    except Exception as e:
        logger.error(f"Unexpected error in list_prediction_sessions: {repr(e)}, Type: {type(e)}, Args: {e.args}")
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)



@login_required
def prediction_session_details(request, session_id):
    try:
        session = PredictionSession.objects.get(session_id=session_id, user=request.user)
        results = session.results.all().order_by('crop_name')
        details = []

        start_date = (timezone.now() - timezone.timedelta(days=365)).strftime('%Y%m%d')
        end_date = timezone.now().strftime('%Y%m%d')

        for result in results:
            try:
                df_1 = fetch_market_prices(result.crop_name, session.region, start_date, end_date)
                if df_1 is not None and not df_1.empty:
                    df_1_json = df_1.to_json(orient='records', date_format='iso')
                    crop_chart_data_parsed = json.loads(df_1_json)
                else:
                    crop_chart_data_parsed = []
            except (NotFoundError, ServiceUnavailableError) as exc:
                logger.warning(
                    "Market chart data unavailable for prediction session %s: %s",
                    session.session_id,
                    type(exc).__name__,
                )
                crop_chart_data_parsed = []

            details.append({
                'crop_name': result.crop_name,
                'predicted_income': result.predicted_income,
                'adjusted_data': result.adjusted_data,
                'price': result.price,
                'latest_year': result.latest_year,
                'r2_score': result.r2_score,
                'rmse': result.rmse,
                'crop_chart_data': crop_chart_data_parsed
            })

        return JsonResponse({
            'session_id': session.session_id,
            'session_name': session.session_name,
            'land_area': session.land_area,
            'region': session.region,
            'total_income': session.total_income,
            'created_at': timezone.localtime(session.created_at).strftime('%Y-%m-%d %H:%M'),
            'results': details
        })
    except PredictionSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
@login_required
def delete_prediction_session(request, session_id):
    if request.method == 'DELETE':
        try:
            session = PredictionSession.objects.get(session_id=session_id, user=request.user)
            session.delete()
            return JsonResponse({'status': 'success', 'message': 'Prediction session deleted successfully'})
        except PredictionSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
def submit_prediction_view(request):
    return render(request, 'prediction.html')

@login_required
@require_http_methods(["PATCH"])
def update_session_name(request, session_id):
    try:
        data = json.loads(request.body)
        new_session_name = data.get('session_name')

        if not new_session_name:
            raise ValidationError("New session name is required", code=400)

        session = PredictionSession.objects.get(user=request.user, session_id=session_id)
        session.session_name = new_session_name
        session.save()

        return JsonResponse({'status': 'success', 'message': 'Session name updated successfully'})
    except json.JSONDecodeError:
        raise ValidationError("Invalid JSON format", code=400)
    except ValidationError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    except NotFoundError as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=404)
    except Exception as e:
        logger.error(f"Error updating session name: {str(e)}")
        raise InternalServerError("Failed to update session name", code=500)
