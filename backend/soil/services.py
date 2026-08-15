import os
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

import pandas as pd
import requests

from aivle_big.exceptions import NotFoundError, ServiceUnavailableError, ValidationError


APP_DIR = Path(__file__).resolve().parent
CROP_CODE_PATH = APP_DIR / "crop_code.csv"
REQUEST_TIMEOUT_SECONDS = 10
KAKAO_ADDRESS_URL = "https://dapi.kakao.com/v2/local/search/address.json"
SOIL_EXAM_V2_URL = "https://apis.data.go.kr/1390802/SoilEnviron/SoilExam/V2/getSoilExamList"
FERTILIZER_URL = "http://apis.data.go.kr/1390802/SoilEnviron/FrtlzrUseExp/getSoilFrtlzrExprnInfo"


def _required_env(name):
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


def find_legal_district_code(address):
    api_key = _required_env("KAKAO_REST_API_KEY")
    try:
        response = requests.get(
            KAKAO_ADDRESS_URL,
            headers={"Authorization": f"KakaoAK {api_key}"},
            params={"query": address},
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
        legal_code = (document.get("address") or {}).get("b_code")
        if legal_code:
            # SoilExam V2 accepts the 10-digit legal district standard code.
            return str(legal_code)[:10]
    raise NotFoundError("No legal district code was found for the address.")


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
        {child.tag: child.text for child in item}
        for item in items.findall("item")
    ]
    if not result:
        raise NotFoundError("Soil examination data was empty.")
    return result


def _bounded(value, minimum, maximum):
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = minimum
    return str(max(minimum, min(number, maximum)))


def fetch_fertilizer(crop_name, soil_values):
    params = {
        "serviceKey": _public_api_key("DATA_GO_KR_FERTILIZER_SERVICE_KEY"),
        "crop_Code": get_crop_code(crop_name),
        "acid": _bounded(soil_values.get("acid"), 4, 9),
        "om": _bounded(soil_values.get("om"), 5, 300),
        "vldpha": _bounded(soil_values.get("vldpha"), 5, 1700),
        "posifert_K": _bounded(soil_values.get("posifert_K"), 0.01, 9),
        "posifert_Ca": _bounded(soil_values.get("posifert_Ca"), 0.1, 30),
        "posifert_Mg": _bounded(soil_values.get("posifert_Mg"), 0.1, 20),
        "vldsia": _bounded(soil_values.get("vldsia"), 5, 1500),
        "selc": _bounded(soil_values.get("selc"), 0, 10),
    }
    try:
        response = requests.get(FERTILIZER_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Fertilizer service request failed.") from exc

    root = _parse_xml(response, "Fertilizer service")
    result_code = _xml_text(root, "resultCode") or _xml_text(root, "Result_Code")
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
    filtered_params = {key: value for key, value in params.items() if key not in {"serviceKey", "crop_Code"}}
    return result, filtered_params
