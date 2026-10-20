import os

from django.conf import settings
from django.db import DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from detect.artifact import check_artifact_readiness, resolve_model_path
from detect.models import PestModelClass

EXPECTED_CLASS_TO_PEST_CODE = {
    0: 'PEPPER_ANTHRACNOSE',
    1: 'PEPPER_POWDERY_MILDEW',
    2: 'CUCUMBER_DOWNY_MILDEW',
    3: 'TOMATO_POWDERY_MILDEW',
    4: 'CUCUMBER_DOWNY_MILDEW',
    5: 'CUCUMBER_POWDERY_MILDEW',
}
REQUIRED_PEST_DETAILS = (
    'code',
    'pest_name',
    'occurrence_environment',
    'symptom_description',
    'prevention_methods',
    'pesticide_name',
    'image_url',
    'information_source',
    'information_source_url',
)


def _configured(*names):
    return all(bool(os.getenv(name, '').strip()) for name in names)


def _capability(enabled, configured):
    available = bool(enabled and configured)
    if available:
        status = 'available'
        reason = None
    elif not enabled:
        status = 'archived'
        reason = 'disabled'
    else:
        status = 'limited'
        reason = 'not_configured'
    return {
        'status': status,
        'available': available,
        'reason': reason,
    }


def _storage_capability():
    if not settings.USE_S3:
        return {'status': 'local', 'available': True, 'reason': None}
    configured = _configured(
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_STORAGE_BUCKET_NAME',
    )
    return {
        'status': 's3' if configured else 'limited',
        'available': configured,
        'reason': None if configured else 'not_configured',
    }


def _detection_readiness():
    """Check artifact execution readiness and the full database class catalog."""
    artifact = check_artifact_readiness(resolve_model_path())
    if not artifact['ready']:
        return False, artifact['reason']
    try:
        mappings = list(PestModelClass.objects.select_related('pest').all())
    except DatabaseError:
        return False, 'database_unavailable'
    by_class_id = {mapping.class_id: mapping for mapping in mappings}
    if set(by_class_id) != set(EXPECTED_CLASS_TO_PEST_CODE):
        return False, 'catalog_incomplete'
    for class_id, expected_code in EXPECTED_CLASS_TO_PEST_CODE.items():
        mapping = by_class_id[class_id]
        if mapping.pest.code != expected_code or not mapping.model_label:
            return False, 'catalog_incomplete'
        if any(not getattr(mapping.pest, field, None) for field in REQUIRED_PEST_DETAILS):
            return False, 'catalog_incomplete'
    return True, None


@require_GET
def capabilities(request):
    """Expose support state without leaking credentials or provider details."""
    from chatbot.views import (
        CHATBOT_DEPENDENCIES_AVAILABLE,
        vector_index_available,
    )

    chatbot_configured = (
        _configured('OPENAI_API_KEY')
        and CHATBOT_DEPENDENCIES_AVAILABLE
        and vector_index_available()
    )
    detection_ready, detection_reason = _detection_readiness()
    return JsonResponse(
        {
            'soil': _capability(
                settings.SOIL_SERVICE_ENABLED,
                _configured(
                    'KAKAO_REST_API_KEY',
                    'DATA_GO_KR_SOIL_SERVICE_KEY',
                    'DATA_GO_KR_FERTILIZER_V2_SERVICE_KEY',
                ),
            ),
            'prediction': _capability(
                settings.PREDICTION_SERVICE_ENABLED,
                _configured(
                    'DATA_GO_KR_WEATHER_SERVICE_KEY',
                    'DATA_GO_KR_MARKET_SERVICE_KEY',
                ),
            ),
            'chatbot': _capability(
                settings.CHATBOT_ENABLED,
                chatbot_configured,
            ),
            'detection': {
                'status': 'available' if detection_ready else 'limited',
                'available': detection_ready,
                'reason': detection_reason,
            },
            'email': _capability(
                True,
                _configured(
                    'EMAIL_HOST_USER',
                    'EMAIL_HOST_PASSWORD',
                    'DEFAULT_FROM_EMAIL',
                ),
            ),
            'storage': _storage_capability(),
        }
    )
