import os
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests
from django.conf import settings

from aivle_big.exceptions import NotFoundError, ServiceUnavailableError, ValidationError


APP_DIR = Path(__file__).resolve().parent
CROP_CODE_PATH = APP_DIR / "crop_code.csv"
REQUEST_TIMEOUT_SECONDS = 10
KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"
SOIL_EXAM_V2_URL = "https://apis.data.go.kr/1390802/SoilEnviron/SoilExam/V2/getSoilExamList"
FERTILIZER_V2_URL = "https://apis.data.go.kr/1390802/SoilEnviron_FrtlzrUse_V2/getSoilFrtlzrExamInfo"


def _required_env(name):
    if not settings.SOIL_SERVICE_ENABLED:
        raise ServiceUnavailableError("Soil information service is disabled.")
    value = os.getenv(name, "").strip()
    if not value:
        raise ServiceUnavailableError("Soil information service is not configured.")
    return value


def _public_api_key(name):
    return unquote(_required_env(name))


def _xml_text(root, name):
    element = root.find(f".//{name}")
    return element.text if element is not None else None


def _parse_xml(response, service_name):
    if response.status_code != 200:
        raise ServiceUnavailableError(
            f"{service_name} request failed with HTTP {response.status_code}."
        )
    try:
        return ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ServiceUnavailableError(f"{service_name} returned invalid XML.") from exc


def get_crop_names():
    return pd.read_csv(CROP_CODE_PATH)["crop_name"].dropna().tolist()


def get_crop_code(crop_name):
    frame = pd.read_csv(CROP_CODE_PATH)
    row = frame.loc[frame["crop_name"] == crop_name]
    if row.empty:
        raise ValidationError("Invalid crop name provided.")
    return str(row["crop_code"].values[0]).zfill(5)


def build_pnu_code(b_code, mountain_yn, main_address_no, sub_address_no=""):
    b_code = str(b_code or "")
    mountain_yn = str(mountain_yn or "").upper()
    main_address_no = str(main_address_no or "")
    sub_address_no = str(sub_address_no or "")
    if not b_code.isdigit() or len(b_code) != 10:
        raise ValidationError("Invalid legal district code for parcel lookup.")
    if mountain_yn not in {"N", "Y"}:
        raise ValidationError("Invalid mountain parcel flag.")
    if not main_address_no.isdigit() or len(main_address_no) > 4:
        raise ValidationError("Invalid main parcel number.")
    if sub_address_no and (not sub_address_no.isdigit() or len(sub_address_no) > 4):
        raise ValidationError("Invalid sub parcel number.")
    pnu = (
        b_code
        + ("1" if mountain_yn == "N" else "2")
        + main_address_no.zfill(4)
        + (sub_address_no.zfill(4) if sub_address_no else "0000")
    )
    if len(pnu) != 19 or not pnu.isdigit():
        raise ValidationError("Invalid parcel identifier.")
    return pnu


def _find_address_document(address):
    if not isinstance(address, str) or not address.strip():
        raise ValidationError("Address is required.")
    api_key = _required_env("KAKAO_REST_API_KEY")
    try:
        response = requests.get(
            KAKAO_ADDRESS_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={"query": address.strip()},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Address search service request failed.") from exc

    if response.status_code != 200:
        raise ServiceUnavailableError("Address search service request failed.")
    try:
        documents = response.json().get("documents", [])
    except (requests.RequestException, ValueError, AttributeError) as exc:
        raise ServiceUnavailableError("Address search service returned an invalid response.") from exc
    if not documents:
        raise NotFoundError("No address search result was found.")

    for document in documents:
        parcel = document.get("address") or {}
        if parcel.get("b_code"):
            return parcel
    raise NotFoundError("No legal district code was found for the address.")


def find_legal_district_code(address):
    parcel = _find_address_document(address)
    return str(parcel["b_code"])[:10]


def find_address_codes(address):
    """Resolve a parcel address to both legal-district and 19-digit PNU codes."""
    parcel = _find_address_document(address)
    legal_code = parcel["b_code"]
    return {
        "stdg_code": str(legal_code)[:10],
        "pnu_code": build_pnu_code(
            legal_code,
            parcel.get("mountain_yn"),
            parcel.get("main_address_no"),
            parcel.get("sub_address_no"),
        ),
    }


def fetch_soil_exam(stdg_code):
    params = {
        "serviceKey": _public_api_key("DATA_GO_KR_SOIL_SERVICE_KEY"),
        "Page_Size": "200",
        "Page_No": "1",
        "STDG_CD": stdg_code,
    }
    try:
        response = requests.get(SOIL_EXAM_V2_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Soil examination service request failed.") from exc

    root = _parse_xml(response, "Soil examination service")
    result_code = _xml_text(root, "Result_Code")
    result_message = _xml_text(root, "Result_Msg")
    if result_code is None:
        raise ServiceUnavailableError("Soil examination service returned an invalid response.")
    if result_code != "200":
        if result_code in {"201", "203", "204"}:
            raise ValidationError("Soil examination request parameters are invalid.")
        if result_code == "301":
            raise NotFoundError("No soil examination data was found for the address.")
        raise ServiceUnavailableError(
            f"Soil examination service failed: {result_code} / {result_message or ''}"
        )

    items = root.find(".//items")
    if items is None:
        raise NotFoundError("No soil examination data was found for the address.")
    # Preserve the original frontend contract: SoilResults reads the public API's
    # field names (for example PNU_Nm, ACID and POSIFERT_K) directly.
    result = [
        {
            ("SELC" if child.tag == "ELCD" else child.tag): child.text
            for child in item
        }
        for item in items.findall("item")
    ]
    if not result:
        raise NotFoundError("Soil examination data was empty.")
    return result


def fetch_fertilizer(crop_name, soil_values, pnu_code=None):
    pnu_code = pnu_code or soil_values.get("pnu_code")
    if not pnu_code:
        raise ValidationError("Parcel identifier is required for fertilizer recommendation.")
    params = {
        "serviceKey": _public_api_key("DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY"),
        "PNU_Code": pnu_code,
        "crop_Code": get_crop_code(crop_name),
        "animix_Ratio_Cattl": "28",
        "animix_Ratio_Pig": "22",
        "animix_Ratio_Chick": "19",
        "animix_Ratio_Sawdust": "21",
    }
    try:
        response = requests.get(FERTILIZER_V2_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Fertilizer service request failed.") from exc

    root = _parse_xml(response, "Fertilizer service")
    result_code = (
        _xml_text(root, "resultCode")
        or _xml_text(root, "Result_Code")
        or _xml_text(root, "result_Code")
    )
    if result_code and result_code not in {"00", "0", "200", "NORMAL_CODE"}:
        raise ServiceUnavailableError("Fertilizer service returned an API error.")
    if _xml_text(root, "returnAuthMsg") or _xml_text(root, "errMsg"):
        raise ServiceUnavailableError("Fertilizer service returned an API error.")

    fields = [
        "crop_Code", "crop_Nm", "pre_Fert_N", "pre_Fert_P", "pre_Fert_K",
        "post_Fert_N", "post_Fert_P", "post_Fert_K", "pre_Compost_Cattl",
        "pre_Compost_Pig", "pre_Compost_Chick", "pre_Compost_Mix",
    ]
    items = root.findall(".//items/item")
    result = [{field: item.findtext(field) for field in fields} for item in items]
    if not result:
        raise NotFoundError("No fertilizer recommendation data was found.")
    filtered_params = {
        key: value for key, value in soil_values.items() if key not in {"serviceKey", "crop_Code", "PNU_Code"}
    }
    return result, filtered_params
