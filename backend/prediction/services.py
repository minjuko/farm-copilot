import os
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from urllib.parse import unquote

import pandas as pd
import requests
from django.conf import settings

from aivle_big.exceptions import NotFoundError, ServiceUnavailableError


REQUEST_TIMEOUT_SECONDS = 10
MARKET_API_URL = "https://apis.data.go.kr/B552845/periodWholesale/price"
WEATHER_API_URL = "https://apis.data.go.kr/1360000/AsosDalyInfoService/getWthrDataList"
MARKET_PAGE_SIZE = 1000
MARKET_MAX_PAGES = 1000


def _required_env(name, service_name):
    if not settings.PREDICTION_SERVICE_ENABLED:
        raise ServiceUnavailableError(f"{service_name} is disabled.")
    value = os.getenv(name, "").strip()
    if not value:
        raise ServiceUnavailableError(f"{service_name} is not configured.")
    return value


def _parse_response(response, service_name):
    if response.status_code != 200:
        raise ServiceUnavailableError(
            f"{service_name} request failed with HTTP {response.status_code}."
        )
    try:
        return response.json()
    except (ValueError, TypeError) as exc:
        raise ServiceUnavailableError(
            f"{service_name} returned an invalid JSON response."
        ) from exc


def fetch_market_prices(crop_name, region, start_date, end_date, price_code, region_codes):
    service_key = unquote(
        _required_env("DATA_GO_KR_MARKET_SERVICE_KEY", "Market price service")
    )

    # The CSV's first three columns are category code, item code, and crop name.
    code_rows = price_code.loc[price_code.iloc[:, 2] == crop_name]
    if code_rows.empty:
        raise NotFoundError("Market price mapping was not found.")

    category_code = int(code_rows.iloc[0, 0])
    item_code = int(code_rows.iloc[0, 1])
    rows = []
    page_no = 1
    expected_pages = None
    while page_no <= MARKET_MAX_PAGES:
        params = {
            "serviceKey": service_key,
            "pageNo": page_no,
            "numOfRows": MARKET_PAGE_SIZE,
            "cond[exmn_ymd::GTE]": start_date,
            "cond[exmn_ymd::LTE]": end_date,
            "cond[ctgry_cd::EQ]": category_code,
            "cond[item_cd::EQ]": item_code,
            "returnType": "JSON",
        }
        try:
            response = requests.get(MARKET_API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException as exc:
            raise ServiceUnavailableError("Market price service request failed.") from exc

        payload = _parse_response(response, "Market price service")
        response_data = payload.get("response") if isinstance(payload, dict) else None
        if not isinstance(response_data, dict):
            raise ServiceUnavailableError("Market price service returned a malformed response.")
        header = response_data.get("header") or {}
        result_code = str(header.get("resultCode", "00"))
        if result_code not in {"00", "0", "200"}:
            raise ServiceUnavailableError("Market price service returned an API error.")
        body = response_data.get("body") or {}
        items = body.get("items") or {}
        page_items = items.get("item", []) if isinstance(items, dict) else []
        if isinstance(page_items, dict):
            page_items = [page_items]
        if not isinstance(page_items, list):
            raise ServiceUnavailableError("Market price service returned malformed items.")
        rows.extend(page_items)
        try:
            total_count = int(body.get("totalCount", 0))
        except (TypeError, ValueError):
            raise ServiceUnavailableError("Market price service returned malformed pagination data.")
        expected_pages = max(1, (total_count + MARKET_PAGE_SIZE - 1) // MARKET_PAGE_SIZE)
        if not page_items or page_no >= expected_pages:
            break
        page_no += 1

    if not rows:
        raise NotFoundError(f"No market price data was found for {crop_name}.")

    frame = pd.DataFrame(rows)
    date_column = "exmn_ymd"
    price_column = "exmn_dd_cnvs_prc"
    item_name_column = next(
        (column for column in ("item_nm", "item_name", "itemname") if column in frame),
        None,
    )
    if date_column not in frame or price_column not in frame:
        raise ServiceUnavailableError("Market price service returned malformed data.")
    frame["tm"] = pd.to_datetime(frame[date_column], errors="coerce")
    frame["price"] = pd.to_numeric(
        frame[price_column].astype(str).str.replace(",", "", regex=False),
        errors="coerce",
    )
    frame["itemname"] = frame[item_name_column] if item_name_column else crop_name
    frame = frame.dropna(subset=["tm", "price"])
    if frame.empty:
        raise NotFoundError(f"No valid market price data was found for {crop_name}.")
    # Multiple varieties/grades can exist per date; retain the complete series
    # while producing one deterministic daily kg-price value for prediction.
    frame = frame.groupby("tm", as_index=False).agg(
        price=("price", "mean"), itemname=("itemname", "first")
    )
    return frame.sort_values("tm").reset_index(drop=True)


def fetch_weather_data(region, region_codes):
    service_key = unquote(
        _required_env("DATA_GO_KR_WEATHER_SERVICE_KEY", "Weather service")
    )
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

    try:
        root = ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ServiceUnavailableError("Weather service returned an invalid XML response.") from exc
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
