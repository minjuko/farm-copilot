import json
import uuid

from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from aivle_big.decorators import login_required
from aivle_big.exceptions import BadRequestError, MissingPartError, NotFoundError, ValidationError

from .models import crop_data
from .services import (
    fetch_fertilizer,
    fetch_soil_exam,
    find_address_codes,
    find_legal_district_code,
    get_crop_names as load_crop_names,
    search_addresses,
)


def _json_body(request):
    try:
        return json.loads(request.body or "{}")
    except json.JSONDecodeError as exc:
        raise BadRequestError("Invalid JSON format.") from exc


@require_GET
def get_crop_names(request):
    return JsonResponse({"crop_names": load_crop_names()})


@login_required
@require_GET
def address_search(request):
    normalized_query, results = search_addresses(request.GET.get("query"))
    return JsonResponse({
        "query": request.GET.get("query", "").strip(),
        "normalized_query": normalized_query,
        "results": results,
    })


@login_required
@require_POST
def soil_exam_result(request):
    data = _json_body(request)
    crop_name = data.get("crop_name")
    address = data.get("address")
    if not crop_name or not address:
        raise ValidationError("Address and crop name are required.")

    stdg_code = find_legal_district_code(address)
    soil_data = fetch_soil_exam(stdg_code)
    # Keep the original frontend response fields; only the external V2 contract changes.
    return JsonResponse({
        "crop_name": crop_name,
        "address": address,
        "soil_data": soil_data,
    })


@login_required
@require_POST
def get_soil_fertilizer_info(request):
    data = _json_body(request)
    crop_name = data.get("crop_code")
    if not crop_name:
        raise MissingPartError("Missing crop code.")

    # The first address can be a district-level query. Fertilizer V2 requires
    # the exact parcel selected from the soil-examination result.
    parcel_address = data.get("PNU_Nm")
    if not parcel_address:
        raise MissingPartError("Selected parcel address is required.")
    address_codes = find_address_codes(parcel_address)
    fertilizer_data, filtered_params = fetch_fertilizer(crop_name, data, address_codes["pnu_code"])
    # A soil analysis is an application record, not a browser login session.
    # Reusing Django's session key caused every analysis made in one login
    # session to be grouped together and deleted together from the history UI.
    analysis_id = str(uuid.uuid4())

    with transaction.atomic():
        for item in fertilizer_data:
            crop_data.objects.create(
                user_id=request.user.id,
                session_id=analysis_id,
                crop_name=crop_name,
                address=data.get("address"),
                detailed_address=parcel_address,
                created_at=timezone.now(),
                soil_data=filtered_params,
                fertilizer_data=item,
            )
    return JsonResponse({"session_id": analysis_id, "data": fertilizer_data})


@login_required
@require_GET
def get_crop_data_by_user(request):
    rows = crop_data.objects.filter(user_id=request.user.id).order_by("-created_at")
    result = [{
        "user_id": row.user_id,
        "session_id": row.session_id,
        "crop_name": row.crop_name,
        "address": row.address,
        "detailed_address": row.detailed_address,
        "created_at": timezone.localtime(row.created_at).strftime("%Y-%m-%d %H:%M:%S"),
        "soil_data": row.soil_data,
        "fertilizer_data": row.fertilizer_data,
    } for row in rows]
    return JsonResponse(result, safe=False)


@login_required
@require_http_methods(["DELETE"])
def delete_soil_data_by_session(request, session_id):
    deleted_count, _ = crop_data.objects.filter(
        user_id=request.user.id,
        session_id=session_id,
    ).delete()
    if not deleted_count:
        raise NotFoundError("Soil session not found.")
    return JsonResponse({"message": "Data deleted successfully"})
