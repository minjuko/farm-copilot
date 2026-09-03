import os
from pathlib import Path

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_GET


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
    model_path = Path(os.getenv('YOLO_MODEL_PATH', settings.BASE_DIR / 'best.pt'))
    if not model_path.is_absolute():
        model_path = settings.BASE_DIR / model_path
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
            'detection': _capability(
                True,
                model_path.is_file(),
            ),
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
