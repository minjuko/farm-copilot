import json
import os
from unittest.mock import Mock, patch

import requests
from django.test import TestCase
from django.urls import reverse

from aivle_big.exceptions import NotFoundError, ServiceUnavailableError, ValidationError
from login.models import User

from .services import fetch_fertilizer, fetch_soil_exam, find_legal_district_code, get_crop_names


class SoilServiceTests(TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_kakao_key_is_controlled(self):
        with self.assertRaises(ServiceUnavailableError):
            find_legal_district_code("서울")

    @patch("soil.services.requests.get")
    @patch.dict(os.environ, {"KAKAO_REST_API_KEY": "test-key"}, clear=True)
    def test_empty_kakao_result_is_not_found(self, mock_get):
        mock_get.return_value = Mock(status_code=200, json=lambda: {"documents": []})
        with self.assertRaises(NotFoundError):
            find_legal_district_code("unknown")

    @patch("soil.services.requests.get")
    @patch.dict(os.environ, {"KAKAO_REST_API_KEY": "test-key"}, clear=True)
    def test_kakao_code_is_normalized_for_soil_v2(self, mock_get):
        mock_get.return_value = Mock(
            status_code=200,
            json=lambda: {"documents": [{"address": {"b_code": "123456789012345"}}]},
        )
        self.assertEqual(find_legal_district_code("서울"), "1234567890")

    @patch("soil.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_SOIL_SERVICE_KEY": "test-key"}, clear=True)
    def test_soil_v2_success_parsing_and_parameter(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=b"""
            <response><header><Result_Code>200</Result_Code><Result_Msg>OK</Result_Msg></header>
            <body><items><item><Stdg_Cd>1234567890</Stdg_Cd><ACID>6.5</ACID><PNU_Nm>sample</PNU_Nm></item></items></body></response>
        """)
        result = fetch_soil_exam("1234567890")
        self.assertEqual(result[0]["Stdg_Cd"], "1234567890")
        self.assertEqual(mock_get.call_args.kwargs["params"]["STDG_CD"], "1234567890")
        self.assertNotIn("BJD_Code", mock_get.call_args.kwargs["params"])

    @patch("soil.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_SOIL_SERVICE_KEY": "test-key"}, clear=True)
    def test_soil_v2_result_error_is_controlled(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=b"<response><Result_Code>201</Result_Code></response>")
        with self.assertRaises(ValidationError):
            fetch_soil_exam("1234567890")

    @patch("soil.services.requests.get", side_effect=requests.Timeout)
    @patch.dict(os.environ, {"DATA_GO_KR_SOIL_SERVICE_KEY": "test-key"}, clear=True)
    def test_soil_timeout_is_controlled(self, _mock_get):
        with self.assertRaises(ServiceUnavailableError):
            fetch_soil_exam("1234567890")

    @patch("soil.services.requests.get")
    @patch.dict(os.environ, {"DATA_GO_KR_FERTILIZER_SERVICE_KEY": "test-key"}, clear=True)
    def test_fertilizer_response_parsing(self, mock_get):
        mock_get.return_value = Mock(status_code=200, content=b"""
            <response><header><resultCode>00</resultCode></header><body><items><item>
            <crop_Code>00101</crop_Code><crop_Nm>sample</crop_Nm><pre_Fert_N>10</pre_Fert_N>
            </item></items></body></response>
        """)
        result, filtered = fetch_fertilizer(get_crop_names()[0], {})
        self.assertEqual(result[0]["crop_Code"], "00101")
        self.assertNotIn("serviceKey", filtered)

    def test_invalid_crop_mapping_is_controlled(self):
        with patch.dict(os.environ, {"DATA_GO_KR_FERTILIZER_SERVICE_KEY": "test-key"}, clear=True):
            with self.assertRaises(ValidationError):
                fetch_fertilizer("not-a-crop", {})


class SoilEndpointTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="soil-runtime@example.com",
            username="soil-runtime",
            password="test-password",
        )
        self.client.force_login(self.user)

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_only_disable_soil_endpoint(self):
        response = self.client.post(
            reverse("soil:soil_exam_result"),
            data=json.dumps({"crop_name": "벼", "address": "서울"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["code"], 2001)

    @patch("soil.views.fetch_soil_exam", return_value=[{"acid": "6.5"}])
    @patch("soil.views.find_legal_district_code", return_value="1234567890")
    def test_soil_endpoint_preserves_frontend_contract(self, _mock_code, _mock_soil):
        response = self.client.post(
            reverse("soil:soil_exam_result"),
            data=json.dumps({"crop_name": "벼", "address": "서울"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json()), {"crop_name", "address", "soil_data"})
