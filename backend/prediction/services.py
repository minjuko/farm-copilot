import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import pandas as pd
import requests

from aivle_big.exceptions import NotFoundError, ServiceUnavailableError


REQUEST_TIMEOUT_SECONDS = 10
KAMIS_API_URL = "http://www.kamis.or.kr/service/price/xml.do"
WEATHER_API_URL = "http://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"


def _required_env(name, service_name):
    value = os.getenv(name, "").strip()
    if not value:
        raise ServiceUnavailableError(f"{service_name} is not configured.")
    return value


def _parse_xml(response, service_name):
    if response.status_code != 200:
        raise ServiceUnavailableError(
            f"{service_name} request failed with HTTP {response.status_code}."
        )
    try:
        return ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ServiceUnavailableError(
            f"{service_name} returned an invalid XML response."
        ) from exc


def fetch_market_prices(crop_name, region, start_date, end_date, price_code, region_codes):
    cert_key = _required_env("KAMIS_CERT_KEY", "Market price service")
    cert_id = _required_env("KAMIS_CERT_ID", "Market price service")

    code_rows = price_code.loc[price_code["품목명"] == crop_name]
    if code_rows.empty or region not in region_codes:
        raise NotFoundError("Market price mapping was not found.")

    params = {
        "action": "periodProductList",
        "p_productclscode": "02",
        "p_startday": start_date,
        "p_endday": end_date,
        "p_itemcategorycode": int(code_rows["부류코드"].values[0]),
        "p_itemcode": int(code_rows["품목코드"].values[0]),
        "p_kindcode": "",
        "p_productrankcode": "",
        "p_countrycode": region_codes[region][0],
        "p_convert_kg_yn": "Y",
        "p_cert_key": cert_key,
        "p_cert_id": cert_id,
        "p_returntype": "xml",
    }
    try:
        response = requests.get(KAMIS_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Market price service request failed.") from exc

    root = _parse_xml(response, "Market price service")
    rows = [
        {
            "yyyy": item.findtext("yyyy"),
            "regday": item.findtext("regday"),
            "itemname": item.findtext("itemname"),
            "kindname": item.findtext("kindname"),
            "price": item.findtext("price"),
        }
        for item in root.findall(".//item")
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        raise NotFoundError(f"No market price data was found for {crop_name}.")

    try:
        frame["regday"] = frame["regday"].apply(
            lambda value: value.replace("/", "-") if value else ""
        )
        frame["price"] = (
            frame["price"].replace("-", pd.NA).str.replace(",", "").astype(float)
        )
        frame["tm"] = pd.to_datetime(frame["yyyy"] + "-" + frame["regday"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ServiceUnavailableError("Market price service returned malformed data.") from exc

    frame.drop(columns=["yyyy", "regday"], inplace=True)
    frame.dropna(inplace=True)
    frame.reset_index(drop=True, inplace=True)
    if frame.empty:
        raise NotFoundError(f"No valid market price data was found for {crop_name}.")
    kind_to_keep = frame.loc[0, "kindname"]
    frame = frame[frame["kindname"] == kind_to_keep]
    frame.drop(columns=["kindname"], inplace=True)
    return frame


def fetch_weather_data(region, region_codes):
    service_key = _required_env("DATA_GO_KR_WEATHER_SERVICE_KEY", "Weather service")
    if region not in region_codes:
        raise NotFoundError("Weather station mapping was not found.")

    end_date = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
    start_date = (datetime.now() - timedelta(days=366)).strftime("%Y%m%d")
    params = {
        "serviceKey": service_key,
        "pageNo": "1",
        "numOfRows": "365",
        "dataType": "XML",
        "dataCd": "ASOS",
        "dateCd": "DAY",
        "startDt": start_date,
        "endDt": end_date,
        "stnIds": region_codes[region][1],
    }
    try:
        response = requests.get(WEATHER_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise ServiceUnavailableError("Weather service request failed.") from exc

    root = _parse_xml(response, "Weather service")
    result_code = root.findtext(".//resultCode") or root.findtext(".//Result_Code")
    if result_code and result_code not in {"00", "0", "200", "NORMAL_SERVICE"}:
        raise ServiceUnavailableError("Weather service returned an API error.")

    columns = ["tm", "avgRhm", "minTa", "maxTa", "maxWs", "avgTa", "avgWs", "sumRn", "ddMes"]
    rows = [{child.tag: child.text for child in item if child.tag in columns} for item in root.iter("item")]
    frame = pd.DataFrame(rows, columns=columns)
    if frame.empty:
        raise NotFoundError("No weather data was found.")
    try:
        for column in columns[1:]:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")
        frame.fillna(0, inplace=True)
        frame["tm"] = pd.to_datetime(frame["tm"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ServiceUnavailableError("Weather service returned malformed data.") from exc
    return frame
