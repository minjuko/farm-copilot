import json
import os
from unittest.mock import Mock, patch

import pandas as pd
import requests
from django.test import TestCase
from django.urls import reverse

from aivle_big.exceptions import ServiceUnavailableError
from login.models import User

from .services import fetch_market_prices, fetch_weather_data
from .views import fetch_crop_data, read_csv_data


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

    @patch("prediction.services.requests.get", side_effect=requests.Timeout)
    @patch.dict(os.environ, {"DATA_GO_KR_WEATHER_SERVICE_KEY": "test-key"}, clear=True)
    def test_weather_timeout_is_controlled(self, _mock_get):
        with self.assertRaises(ServiceUnavailableError):
            fetch_weather_data("서울", {"서울": ["1101", "108"]})

    @patch("prediction.services.requests.get")
    @patch.dict(os.environ, {
        "KAMIS_CERT_KEY": "test-key",
        "KAMIS_CERT_ID": "test-id",
    }, clear=True)
    def test_invalid_market_xml_is_controlled(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=b"not-xml")
        codes = pd.DataFrame([{"품목명": "감자", "부류코드": 100, "품목코드": 1001}])
        with self.assertRaises(ServiceUnavailableError):
            fetch_market_prices("감자", "서울", "20260101", "20260102", codes, {"서울": ["1101", "108"]})

    def test_runtime_crop_csv_and_income_calculation(self):
        frame = read_csv_data()
        self.assertFalse(frame.empty)
        crop_name = frame["작물명"].dropna().iloc[0]
        income, adjusted, latest_year = fetch_crop_data(crop_name, frame, 302.5, 1)
        self.assertIsNotNone(income)
        self.assertIsInstance(adjusted, dict)
        self.assertIsNotNone(latest_year)
