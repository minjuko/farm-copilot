import os

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


@require_GET
def capabilities(request):
    """Expose support state without leaking credentials or provider details."""
    return JsonResponse({
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
            _configured('OPENAI_API_KEY', 'CHROMA_DB_PATH'),
        ),
        'storage': {
            'status': 's3' if settings.USE_S3 else 'local',
            'available': True,
            'reason': None,
        },
    })
