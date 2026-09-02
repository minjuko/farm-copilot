import json
import os
from unittest.mock import Mock, patch

import numpy as np
import pandas as pd
import requests
from django.test import Client, TestCase
from django.urls import reverse

from common.exceptions import NotFoundError, ServiceUnavailableError
from login.models import User

from ..services import fetch_market_prices, fetch_weather_data
from ..models import PredictionResult, PredictionSession
from ..views import _build_price_dataset, fetch_crop_data, predict_prices, read_csv_data


class PredictionRuntimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="prediction-runtime@example.com",
            username="prediction-runtime",
            password="test-password",
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_only_disable_prediction_endpoint(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("prediction:predict_income"),
            data=json.dumps({
                "crop_names": ["감자"],
                "crop_ratios": [1],
                "land_area": 100,
                "region": "서울",
            }),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], 2001)

    @patch("prediction.views.fetch_weather_data")
    def test_prediction_rejects_misaligned_crops_before_external_calls(self, mock_weather):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("prediction:predict_income"),
            data=json.dumps({
                "crop_names": ["감자", "고구마"],
                "crop_ratios": [1],
                "land_area": 100,
                "region": "서울",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], 1001)
        mock_weather.assert_not_called()

    @patch("prediction.views.fetch_weather_data")
    def test_prediction_rejects_ninety_percent_total_before_external_calls(self, mock_weather):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse("prediction:predict_income"),
            data=json.dumps({
                "crop_names": ["감자", "고구마", "양파"],
                "crop_ratios": [0.3, 0.3, 0.3],
                "land_area": 100,
                "region": "서울",
            }),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 400)
        mock_weather.assert_not_called()

    @patch("prediction.services.requests.get", side_effect=requests.Timeout)
    @patch.dict(os.environ, {"DATA_GO_KR_WEATHER_SERVICE_KEY": "test-key"}, clear=True)
    def test_weather_timeout_is_controlled(self, _mock_get):
        with self.assertRaises(ServiceUnavailableError):
            fetch_weather_data("서울", {"서울": ["1101", "108"]})

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_WEATHER_SERVICE_KEY": "encoded%2Bkey"}, clear=True)
    def test_weather_service_key_is_url_decoded(self, mock_get):
        mock_get.return_value = Mock(
            status_code=200,
            content=(
                b"<response><body><items><item>"
                b"<tm>2026-01-01</tm><avgRhm>50</avgRhm><minTa>1</minTa>"
                b"<maxTa>5</maxTa><maxWs>2</maxWs><avgTa>3</avgTa>"
                b"<avgWs>1</avgWs><sumRn>0</sumRn><ddMes>0</ddMes>"
                b"</item></items></body></response>"
            ),
        )

        fetch_weather_data("?쒖슱", {"?쒖슱": ["1101", "108"]})

        self.assertEqual(mock_get.call_args.kwargs["params"]["serviceKey"], "encoded+key")

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {
        "DATA_GO_KR_MARKET_SERVICE_KEY": "test-key",
    }, clear=True)
    def test_invalid_market_json_is_controlled(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"unexpected": {}})
        codes = pd.DataFrame([[100, 152, "감자"]], columns=["category", "item", "crop"])
        with self.assertRaises(ServiceUnavailableError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", codes, {"서울": ["1101", "108"]})

    @staticmethod
    def _market_codes():
        return pd.DataFrame([[100, 152, "감자"]], columns=["category", "item", "crop"])

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_MARKET_SERVICE_KEY": "encoded%2Bkey"}, clear=True)
    def test_market_decodes_service_key_and_normalizes_json(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"response": {
            "header": {"resultCode": "00"}, "body": {"totalCount": 2, "items": {"item": [
                {"exmn_ymd": "20260101", "exmn_dd_cnvs_prc": "1,200", "item_nm": "감자"},
                {"exmn_ymd": "20260102", "exmn_dd_cnvs_prc": "1300", "item_nm": "감자"},
            ]}
        }}})
        frame = fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})
        self.assertEqual(mock_get.call_args.kwargs["params"]["serviceKey"], "encoded+key")
        self.assertEqual(list(frame.columns), ["tm", "price", "itemname"])
        self.assertEqual(frame["price"].tolist(), [1200.0, 1300.0])
        self.assertTrue(pd.api.types.is_datetime64_any_dtype(frame["tm"]))

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_MARKET_SERVICE_KEY": "test-key"}, clear=True)
    def test_market_paginates_until_total_count(self, mock_get):
        mock_get.side_effect = [
            Mock(status_code=200, json=lambda: {"response": {"header": {"resultCode": "00"}, "body": {
                "totalCount": 2, "items": {"item": [{"exmn_ymd": "20260101", "exmn_dd_cnvs_prc": "100"}]}}}}),
            Mock(status_code=200, json=lambda: {"response": {"header": {"resultCode": "00"}, "body": {
                "totalCount": 2, "items": {"item": [{"exmn_ymd": "20260102", "exmn_dd_cnvs_prc": "200"}]}}}}),
        ]
        with patch("prediction.services.MARKET_PAGE_SIZE", 1):
            frame = fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})
        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(frame["price"].tolist(), [100.0, 200.0])

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_MARKET_SERVICE_KEY": "test-key"}, clear=True)
    def test_market_uses_public_api_maximum_page_size(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"response": {
            "header": {"resultCode": "00"}, "body": {"totalCount": 0, "items": {"item": []}}
        }})

        with self.assertRaises(NotFoundError):
            codes = self._market_codes()
            fetch_market_prices(codes.iloc[0, 2], "region", "20260101", "20260102", codes, {})

        self.assertEqual(mock_get.call_args.kwargs["params"]["numOfRows"], 1000)

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_MARKET_SERVICE_KEY": "test-key"}, clear=True)
    def test_market_empty_api_response_is_controlled(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"response": {
            "header": {"resultCode": "00"}, "body": {"totalCount": 0, "items": {"item": []}}
        }})
        with self.assertRaises(NotFoundError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_MARKET_SERVICE_KEY": "test-key"}, clear=True)
    def test_market_api_error_timeout_and_invalid_price_are_controlled(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"response": {
            "header": {"resultCode": "30"}, "body": {}
        }})
        with self.assertRaises(ServiceUnavailableError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})

        mock_get.side_effect = requests.Timeout
        with self.assertRaises(ServiceUnavailableError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})

        mock_get.side_effect = None
        mock_get.return_value = Mock(status_code=200, json=lambda: {"response": {
            "header": {"resultCode": "00"}, "body": {"totalCount": 1,
            "items": {"item": [{"exmn_ymd": "20260101", "exmn_dd_cnvs_prc": "-"}]}}
        }})
        with self.assertRaises(NotFoundError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", self._market_codes(), {})

    def test_runtime_crop_csv_and_income_calculation(self):
        frame = read_csv_data()
        self.assertFalse(frame.empty)
        crop_name = frame["작물명"].dropna().iloc[0]
        income, adjusted, latest_year = fetch_crop_data(crop_name, frame, 302.5, 1)
        self.assertIsNotNone(income)
        self.assertIsInstance(adjusted, dict)
        self.assertIsNotNone(latest_year)

    def test_crop_adjustment_does_not_scale_year_rates_or_unit_price(self):
        frame = read_csv_data()
        crop_name = frame["작물명"].dropna().iloc[0]
        source = frame[frame["작물명"] == crop_name].sort_values("시점").iloc[-1]

        _income, adjusted, latest_year = fetch_crop_data(crop_name, frame, 151.25, 1)

        self.assertEqual(adjusted["시점"], latest_year)
        self.assertEqual(adjusted["농가수취가격 (원/kg)"], source["농가수취가격 (원/kg)"])
        self.assertEqual(adjusted["소득률 (%)"], source["소득률 (%)"])
        self.assertAlmostEqual(adjusted["소득 (원)"], source["소득 (원)"] / 2)

    @staticmethod
    def _prediction_frame(days=80):
        dates = pd.date_range("2026-01-01", periods=days, freq="D")
        price = pd.Series(range(100, 100 + days), dtype=float)
        return pd.DataFrame({
            "tm": dates,
            "avgRhm": 50.0,
            "minTa": 5.0,
            "maxTa": 15.0,
            "maxWs": 3.0,
            "avgTa": 10.0,
            "avgWs": 1.0,
            "sumRn": 0.0,
            "ddMes": 0.0,
            "price": price,
            "itemname": "감자",
        })

    def test_price_features_use_only_prices_observed_by_feature_date(self):
        frame = self._prediction_frame()
        X, y, target = _build_price_dataset(frame)

        feature_date_index = X.index[-1]
        self.assertEqual(X.loc[feature_date_index, "price_lag_1"], frame.loc[feature_date_index, "price"])
        self.assertEqual(y.loc[feature_date_index], frame.loc[feature_date_index + 1, "price"])
        self.assertEqual(target.iloc[0]["price_lag_1"], frame.iloc[-1]["price"])

    def test_price_prediction_is_finite_non_negative_and_does_not_mutate_input(self):
        frame = self._prediction_frame()
        original = frame.copy(deep=True)

        price, r2, rmse = predict_prices(frame)

        pd.testing.assert_frame_equal(frame, original)
        self.assertGreaterEqual(price, 0)
        self.assertTrue(np.isfinite(r2))
        self.assertTrue(np.isfinite(rmse))

    @patch("prediction.views.fetch_market_prices", side_effect=ServiceUnavailableError("unavailable"))
    def test_session_details_survive_market_chart_outage(self, _mock_market):
        session = PredictionSession.objects.create(
            user=self.user,
            session_id="runtime-session",
            session_name="runtime",
            crop_names="媛먯옄",
            land_area=100,
            region="?쒖슱",
            total_income=1000,
        )
        PredictionResult.objects.create(
            session=session,
            crop_name="媛먯옄",
            predicted_income=1000,
            adjusted_data={},
            price=100,
        )
        self.client.force_login(self.user)

        response = self.client.get(
            reverse("prediction:prediction_session_details", args=[session.session_id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["crop_chart_data"], [])


class PredictionCsrfBoundaryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="prediction-csrf@example.com",
            username="prediction-csrf",
            password="test-password",
        )
        self.client = Client(enforce_csrf_checks=True)
        self.client.force_login(self.user)

    def csrf_token(self):
        return self.client.get("/login/auth_check/").cookies["csrftoken"].value

    def test_prediction_write_requires_csrf(self):
        payload = {"invalid": True}
        without_token = self.client.post(
            reverse("prediction:predict_income"),
            data=json.dumps(payload),
            content_type="application/json",
        )
        self.assertEqual(without_token.status_code, 403)

        with_token = self.client.post(
            reverse("prediction:predict_income"),
            data="not-json",
            content_type="application/json",
            HTTP_X_CSRFTOKEN=self.csrf_token(),
        )
        self.assertEqual(with_token.status_code, 400)
