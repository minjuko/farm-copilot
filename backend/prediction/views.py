import json
import logging
import uuid

import numpy as np
import pandas as pd
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST
from sklearn.linear_model import ElasticNet
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from common.decorators import login_required
from common.exceptions import (
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

from .models import PredictionResult, PredictionSession
from .services import fetch_market_prices as request_market_prices
from .services import fetch_weather_data as request_weather_data

logger = logging.getLogger(__name__)

CROP_PROFITABILITY_DATA_PATH = 'prediction/crop_profitability_data.csv'
CROP_MARKET_CODES_PATH = 'prediction/crop_market_codes.csv'
REGION_CODES = {
    '서울': ['1101', '108'],
    '부산': ['2100', '159'],
    '대구': ['2200', '143'],
    '광주': ['2401', '156'],
    '대전': ['2501', '133'],
}


def get_crop_names(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid request method. Only GET is allowed.'}, status=405)
    try:
        crop_df = pd.read_csv(CROP_MARKET_CODES_PATH)
        crop_names = crop_df['품목명'].dropna().tolist()
        return JsonResponse({'crop_names': crop_names})
    except Exception as exc:
        return JsonResponse({'error': f'An unexpected error occured: {str(exc)}'}, status=500)


def get_region_names(request):
    if request.method != 'GET':
        return JsonResponse({'error': 'Invalid request method. Only GET is allowed'}, status=400)
    try:
        region_names = list(REGION_CODES.keys())
        return JsonResponse({'region_names': region_names})
    except Exception as exc:
        return JsonResponse({'error': f'An unexpected error occured: {str(exc)}'}, status=500)


def read_csv_data():
    profitability_frame = pd.read_csv(CROP_PROFITABILITY_DATA_PATH, encoding='utf-8')
    profitability_frame['소득률 (%)'] = profitability_frame['소득률 (%)'].astype(str)
    profitability_frame['부가가치율 (%)'] = profitability_frame['부가가치율 (%)'].astype(str)
    profitability_frame['농가수취가격 (원/kg)'] = profitability_frame[
        '농가수취가격 (원/kg)'
    ].astype(str)
    return profitability_frame


def fetch_crop_data(crop_name, profitability_frame, land_area, crop_ratio):
    crop_data = profitability_frame[profitability_frame['작물명'] == crop_name]
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
            '시점',
            '농가수취가격 (원/kg)',
            '부가가치율 (%)',
            '소득률 (%)',
            '작물명',
        }
        for col in adjusted_data.index:
            if col not in non_scalable_columns and isinstance(
                adjusted_data[col], (int, float, np.number)
            ):
                adjusted_data[col] = (adjusted_data[col] / 302.5) * land_area * crop_ratio
        return adjusted_income, adjusted_data.to_dict(), latest_year
    else:
        return None, None, None


def fetch_market_prices(crop_name, region, start_date, end_date):
    price_code = pd.read_csv(CROP_MARKET_CODES_PATH, encoding='utf-8')
    return request_market_prices(crop_name, region, start_date, end_date, price_code, REGION_CODES)


def fetch_weather_data(region):
    return request_weather_data(region, REGION_CODES)


def _build_price_dataset(merged_df):
    if 'price' not in merged_df:
        raise ValidationError('Market data does not contain a price column.')

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
        raise ValidationError('Not enough aligned market and weather data for prediction.')
    return training[feature_columns], training['target_price'], frame.iloc[[-1]][feature_columns]


def predict_prices(merged_frame):
    features, targets, prediction_input = _build_price_dataset(merged_frame)
    split_index = max(1, int(len(features) * 0.8))
    if len(features) - split_index < 2:
        raise ValidationError('Not enough evaluation data for prediction.')
    features_train = features.iloc[:split_index]
    features_test = features.iloc[split_index:]
    targets_train = targets.iloc[:split_index]
    targets_test = targets.iloc[split_index:]
    model = make_pipeline(
        StandardScaler(),
        ElasticNet(alpha=0.1, l1_ratio=0.5, max_iter=10000),
    )
    model.fit(features_train, targets_train)
    predicted_targets = model.predict(features_test)
    r2_value = float(r2_score(targets_test, predicted_targets))
    rmse = float(np.sqrt(mean_squared_error(targets_test, predicted_targets)))
    if not np.isfinite(r2_value):
        r2_value = 0.0
    predicted_price = max(0, int(round(float(model.predict(prediction_input)[0]))))
    return predicted_price, r2_value, rmse


def convert_values(value):
    if isinstance(value, dict):
        return {key: convert_values(item_value) for key, item_value in value.items()}
    elif isinstance(value, list):
        return [convert_values(item_value) for item_value in value]
    elif isinstance(value, (np.int64, np.int32)):
        return int(value)
    elif isinstance(value, np.float64):
        return float(value)
    else:
        return value


@login_required
@require_POST
def predict_income(request):
    try:
        payload = json.loads(request.body)
        session_id = payload.get('session_id') or str(uuid.uuid4())
        session_name = payload.get('session_name', 'Default Prediction Session')
        land_area = float(payload['land_area'])

        if isinstance(payload['crop_names'], list):
            crop_names = payload['crop_names']
        elif isinstance(payload['crop_names'], str):
            crop_names = payload['crop_names'].split(',')
        else:
            logger.error('Invalid format for crop_names')
            return JsonResponse({'error': 'Invalid format for crop_names'}, status=400)

        crop_ratios = [float(ratio) for ratio in payload['crop_ratios']]
        if len(crop_names) != len(crop_ratios):
            raise ValidationError('작물과 비율의 개수가 일치해야 합니다.')
        if not crop_names or any(not name.strip() for name in crop_names):
            raise ValidationError('작물을 하나 이상 선택해야 합니다.')
        if len(set(crop_names)) != len(crop_names):
            raise ValidationError('같은 작물은 중복해서 선택할 수 없습니다.')
        if land_area <= 0 or any(ratio <= 0 for ratio in crop_ratios):
            raise ValidationError('면적과 작물 비율은 0보다 커야 합니다.')
        if not np.isclose(sum(crop_ratios), 1.0, rtol=0, atol=1e-9):
            logger.info('작물 비율의 합은 1이 되어야합니다.')
            raise ValidationError('작물 비율의 합은 1이 되어야합니다.')
        if len(str(session_id)) > 36:
            raise ValidationError('세션 식별자가 너무 깁니다.')
        if PredictionSession.objects.filter(user=request.user, session_id=session_id).exists():
            raise ValidationError('이미 존재하는 예측 세션입니다.')

        region = payload['region']
        profitability_frame = read_csv_data()
        weather_frame = fetch_weather_data(region)
        if weather_frame is None or weather_frame.empty:
            logger.error('날씨데이터를 불러오는 과정에서 오류가 발생했습니다.')
            return JsonResponse(
                {'error': '날씨데이터를 불러오는 과정에서 오류가 발생했습니다.'}, status=404
            )

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
                    total_income=0,
                )

                start_date = weather_frame['tm'].iloc[0].strftime('%Y%m%d')
                end_date = weather_frame['tm'].iloc[-1].strftime('%Y%m%d')

                for crop_name, crop_ratio in zip(crop_names, crop_ratios):
                    adjusted_income, adjusted_data, latest_year = fetch_crop_data(
                        crop_name, profitability_frame, land_area, crop_ratio
                    )
                    if adjusted_income is None:
                        logger.error(f'No data found for {crop_name}')
                        raise ValueError(f'{crop_name}에 대한 데이터는 존재하지 않습니다.')

                    total_predicted_value += int(adjusted_income)

                    market_frame = fetch_market_prices(crop_name, region, start_date, end_date)
                    if market_frame is None or market_frame.empty:
                        logger.error(f'No market data found for {crop_name}')
                        raise ValueError(
                            f'{crop_name}에 대한 도매 데이터를 불러오는 과정에서 오류가 발생했습니다.'
                        )

                    merged_frame = pd.merge(weather_frame, market_frame, on='tm', how='left')
                    if 'price' not in merged_frame:
                        logger.error(f"Missing 'price' in merged DataFrame for {crop_name}")
                    merged_frame.drop('itemname', axis=1, inplace=True)

                    predicted_price, r2_value, rmse = predict_prices(merged_frame)
                    r2_scores.append(r2_value)

                    PredictionResult.objects.create(
                        session=prediction_session,
                        crop_name=crop_name,
                        predicted_income=int(adjusted_income),
                        adjusted_data=convert_values(adjusted_data),
                        price=predicted_price,
                        latest_year=latest_year,
                        r2_score=r2_value,
                        rmse=rmse,
                    )

                    market_json = market_frame.to_json(orient='records', date_format='iso')
                    crop_results.append(
                        {
                            'crop_name': crop_name,
                            'latest_year': int(latest_year),
                            'adjusted_data': convert_values(adjusted_data),
                            'price': predicted_price,
                            'r2_score': r2_value,
                            'rmse': rmse,
                            'crop_chart_data': json.loads(market_json),
                        }
                    )

                prediction_session.total_income = int(total_predicted_value)
                prediction_session.save()

        except (ValidationError, NotFoundError, ServiceUnavailableError):
            raise
        except ValueError as exc:
            logger.error('ValueError: %s', exc)
            return JsonResponse({'error': str(exc)}, status=400)
        except Exception as exc:
            logger.exception('Unexpected prediction error: %s', exc)
            return JsonResponse({'error': 'An unexpected error occurred'}, status=500)

        return JsonResponse(
            {
                'session_id': session_id,
                'total_income': int(total_predicted_value),
                'results': crop_results,
                'r2_scores': r2_scores,
            },
            status=200,
        )

    except (ValidationError, NotFoundError, ServiceUnavailableError):
        raise
    except json.JSONDecodeError:
        logger.info('JSON decoding failed')
        return JsonResponse({'error': 'Invalid JSON format'}, status=400)
    except Exception as exc:
        logger.exception('Unexpected session-list error: %s', exc)
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
                'results': [],
            }
            for prediction_result in results:
                session_details['results'].append(
                    {
                        'crop_name': prediction_result.crop_name,
                        'predicted_income': prediction_result.predicted_income,
                        'r2_score': prediction_result.r2_score,
                        'price': prediction_result.price,
                        'rmse': prediction_result.rmse,
                    }
                )
            session_list.append(session_details)

        return JsonResponse(session_list, safe=False)

    except Exception as exc:
        logger.exception('Unexpected error in list_prediction_sessions: %s', exc)
        return JsonResponse({'error': 'An unexpected error occurred'}, status=500)


@login_required
def prediction_session_details(request, session_id):
    try:
        session = PredictionSession.objects.get(session_id=session_id, user=request.user)
        results = session.results.all().order_by('crop_name')
        details = []

        start_date = (timezone.now() - timezone.timedelta(days=365)).strftime('%Y%m%d')
        end_date = timezone.now().strftime('%Y%m%d')

        for prediction_result in results:
            try:
                market_frame = fetch_market_prices(
                    prediction_result.crop_name, session.region, start_date, end_date
                )
                if market_frame is not None and not market_frame.empty:
                    market_json = market_frame.to_json(orient='records', date_format='iso')
                    crop_chart_data_parsed = json.loads(market_json)
                else:
                    crop_chart_data_parsed = []
            except (NotFoundError, ServiceUnavailableError) as exc:
                logger.warning(
                    'Market chart data unavailable for prediction session %s: %s',
                    session.session_id,
                    type(exc).__name__,
                )
                crop_chart_data_parsed = []

            details.append(
                {
                    'crop_name': prediction_result.crop_name,
                    'predicted_income': prediction_result.predicted_income,
                    'adjusted_data': prediction_result.adjusted_data,
                    'price': prediction_result.price,
                    'latest_year': prediction_result.latest_year,
                    'r2_score': prediction_result.r2_score,
                    'rmse': prediction_result.rmse,
                    'crop_chart_data': crop_chart_data_parsed,
                }
            )

        return JsonResponse(
            {
                'session_id': session.session_id,
                'session_name': session.session_name,
                'land_area': session.land_area,
                'region': session.region,
                'total_income': session.total_income,
                'created_at': timezone.localtime(session.created_at).strftime('%Y-%m-%d %H:%M'),
                'results': details,
            }
        )
    except PredictionSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)


@login_required
def delete_prediction_session(request, session_id):
    if request.method == 'DELETE':
        try:
            session = PredictionSession.objects.get(session_id=session_id, user=request.user)
            session.delete()
            return JsonResponse(
                {'status': 'success', 'message': 'Prediction session deleted successfully'}
            )
        except PredictionSession.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Session not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)


def submit_prediction_view(request):
    return render(request, 'prediction/prediction.html')


@login_required
@require_http_methods(['PATCH'])
def update_session_name(request, session_id):
    try:
        payload = json.loads(request.body)
        new_session_name = payload.get('session_name')

        if not new_session_name:
            raise ValidationError('New session name is required', code=400)

        session = PredictionSession.objects.get(user=request.user, session_id=session_id)
        session.session_name = new_session_name
        session.save()

        return JsonResponse({'status': 'success', 'message': 'Session name updated successfully'})
    except json.JSONDecodeError:
        raise ValidationError('Invalid JSON format', code=400)
    except ValidationError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=400)
    except NotFoundError as exc:
        return JsonResponse({'status': 'error', 'message': str(exc)}, status=404)
    except Exception as exc:
        logger.exception('Error updating session name: %s', exc)
        raise InternalServerError('Failed to update session name', code=500)
