import logging
import math
import os
import tempfile
import warnings
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from PIL import Image, UnidentifiedImageError

from common.decorators import login_required
from common.exceptions import (
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

from .artifact import EXPECTED_CLASSES, check_artifact_readiness
from .models import Pest, PestDetection, PestModelClass

logger = logging.getLogger(__name__)

MAX_DETECTION_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DETECTION_IMAGE_PIXELS = 20_000_000
IMAGE_FORMATS_BY_EXTENSION = {
    'jpg': ('image/jpeg', 'JPEG'),
    'jpeg': ('image/jpeg', 'JPEG'),
    'png': ('image/png', 'PNG'),
    'webp': ('image/webp', 'WEBP'),
}

DEFAULT_MODEL_PATH = Path(settings.BASE_DIR) / 'best.pt'
CONFIDENCE_THRESHOLD = 0.6
REFERENCE_IMAGE_LICENSE = '공공누리 제2유형: 출처표시 + 상업적 이용금지'
MAPPING_UNAVAILABLE_MESSAGE = '병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다.'
MODEL_CONTRACT_MISMATCH_MESSAGE = '병해 탐지 모델의 클래스 계약이 일치하지 않습니다.'
MODEL_OUTPUT_INVALID_MESSAGE = '병해 탐지 모델이 유효하지 않은 결과를 반환했습니다.'
EXPECTED_MODEL_CLASS_NAMES = EXPECTED_CLASSES
MODEL_PATH = DEFAULT_MODEL_PATH
_yolo_model = None


def resolve_model_path():
    configured_path = os.getenv('YOLO_MODEL_PATH')
    if not configured_path:
        return DEFAULT_MODEL_PATH

    path = Path(configured_path)
    return path if path.is_absolute() else Path(settings.BASE_DIR) / path


MODEL_PATH = resolve_model_path()


def validate_model_contract(model):
    try:
        model_names = {int(class_id): label for class_id, label in model.names.items()}
    except (AttributeError, TypeError, ValueError) as exc:
        raise ServiceUnavailableError(MODEL_CONTRACT_MISMATCH_MESSAGE) from exc
    if model_names != EXPECTED_MODEL_CLASS_NAMES:
        raise ServiceUnavailableError(MODEL_CONTRACT_MISMATCH_MESSAGE)


def get_yolo_model():
    readiness = check_artifact_readiness(MODEL_PATH)
    if not readiness['ready'] or _yolo_model is None:
        raise ServiceUnavailableError(
            'Image detection model failed integrity, runtime, or inference readiness checks.'
        )
    validate_model_contract(_yolo_model)
    return _yolo_model


def validate_image_file(image_file):
    if not image_file:
        raise ValidationError('No image uploaded.')
    if image_file.size == 0:
        raise ValidationError('Uploaded image is empty.')
    if image_file.size > MAX_DETECTION_UPLOAD_BYTES:
        raise ValidationError('Image file must be 10 MiB or smaller.')

    extension = Path(image_file.name).suffix.lower().lstrip('.')
    expected_format = IMAGE_FORMATS_BY_EXTENSION.get(extension)
    if not expected_format or image_file.content_type != expected_format[0]:
        raise ValidationError('Only JPEG, PNG, and WebP images are allowed.')

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(image_file) as image:
                if image.format != expected_format[1]:
                    raise ValidationError('Only JPEG, PNG, and WebP images are allowed.')
                if image.width * image.height > MAX_DETECTION_IMAGE_PIXELS:
                    raise ValidationError('Image dimensions must not exceed 20 megapixels.')
                image.verify()

        image_file.seek(0)
        with Image.open(image_file) as image:
            if image.width * image.height > MAX_DETECTION_IMAGE_PIXELS:
                raise ValidationError('Image dimensions must not exceed 20 megapixels.')
            image.load()
    except ValidationError:
        raise
    except (
        UnidentifiedImageError,
        OSError,
        SyntaxError,
        Image.DecompressionBombWarning,
        Image.DecompressionBombError,
    ) as exc:
        raise ValidationError('Uploaded file is not a valid image.') from exc
    finally:
        image_file.seek(0)


def save_temp_image(image_file):
    extension = Path(image_file.name).suffix or '.img'
    temp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
            temp_path = temp_file.name
            for chunk in image_file.chunks():
                temp_file.write(chunk)
        return temp_path
    except Exception:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
        raise


def get_original_image_content(image_path):
    with open(image_path, 'rb') as original_file:
        return ContentFile(original_file.read(), name=os.path.basename(image_path))


def map_model_class_to_pest_id(model_class_id):
    """Resolve an explicit class mapping; never interpret a class as a DB PK."""
    try:
        class_id = int(model_class_id)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ServiceUnavailableError(MAPPING_UNAVAILABLE_MESSAGE) from exc

    try:
        mapping = PestModelClass.objects.select_related('pest').get(class_id=class_id)
    except PestModelClass.DoesNotExist as exc:
        raise ServiceUnavailableError(MAPPING_UNAVAILABLE_MESSAGE) from exc
    return mapping.pest_id


def detection_image_url_or_none(detection):
    if not detection.image:
        return None
    return reverse('detect:detection_image', args=[detection.id])


def delete_detection_image(image_field):
    """Best-effort cleanup for storage that is not covered by DB transactions."""
    if not image_field or not image_field.name:
        return
    image_name = image_field.name
    try:
        image_field.delete(save=False)
    except Exception as exc:
        logger.warning('Failed to delete a detection image from storage: %s', exc)
    if not settings.USE_S3:
        media_root = Path(settings.MEDIA_ROOT).resolve()
        legacy_path = (media_root / image_name).resolve()
        if legacy_path.is_relative_to(media_root) and legacy_path.is_file():
            try:
                legacy_path.unlink()
            except OSError:
                logger.warning('Failed to remove a legacy public detection image.')


def get_owned_detection(user, session_id):
    """Resolve an owned session and keep malformed identifiers on the 404 boundary."""
    try:
        normalized_session_id = int(session_id)
    except (TypeError, ValueError, OverflowError) as exc:
        raise NotFoundError('Detection session not found') from exc
    if normalized_session_id <= 0:
        raise NotFoundError('Detection session not found')

    try:
        return PestDetection.objects.select_related('pest').get(
            id=normalized_session_id,
            user=user,
        )
    except PestDetection.DoesNotExist as exc:
        raise NotFoundError('Detection session not found') from exc


def reference_image_url(pest):
    """Resolve a fixture-owned static asset without hard-coding the static host."""
    if not pest.image_url:
        return None
    if pest.image_url.startswith(('http://', 'https://')):
        return pest.image_url
    return static(pest.image_url.lstrip('/'))


def extract_box_prediction(box):
    """Validate one YOLO box and return its class index and 0..1 confidence."""
    try:
        confidence = float(box.conf.item())
        raw_class_id = float(box.cls.item())
    except (AttributeError, TypeError, ValueError, OverflowError) as exc:
        raise ServiceUnavailableError(MODEL_OUTPUT_INVALID_MESSAGE) from exc

    if (
        not math.isfinite(confidence)
        or not 0.0 <= confidence <= 1.0
        or not math.isfinite(raw_class_id)
        or not raw_class_id.is_integer()
        or raw_class_id < 0
    ):
        raise ServiceUnavailableError(MODEL_OUTPUT_INVALID_MESSAGE)
    return int(raw_class_id), confidence


def serialize_detection(detection):
    """Build the shared successful upload/detail response contract."""
    pest = detection.pest
    return {
        'session_id': detection.id,
        'pest_name': pest.pest_name,
        'occurrence_environment': pest.occurrence_environment,
        'symptom_description': pest.symptom_description,
        'prevention_methods': pest.prevention_methods,
        'pesticide_name': pest.pesticide_name,
        'information_source': pest.information_source,
        'information_source_url': pest.information_source_url,
        'confidence': detection.confidence,
        'user_image_url': detection_image_url_or_none(detection),
        'db_image_url': reference_image_url(pest),
        'reference_image_license': REFERENCE_IMAGE_LICENSE,
        'detection_date': timezone.localtime(detection.detection_date).strftime('%Y-%m-%d %H:%M'),
    }


def process_image(image_path):
    """Run inference and return (Pest PK or None, confidence, image content)."""
    model = get_yolo_model()
    try:
        # TTA restores the inference behavior used for the demonstration
        # images and is configurable for environments that prioritize speed.
        results = model(
            image_path,
            augment=settings.YOLO_AUGMENTED_INFERENCE,
            verbose=False,
        )
        pest_id = None
        confidence = 0.0
        result_image_content = None

        if results and len(results) > 0:
            best_result = results[0]
            if best_result.boxes and len(best_result.boxes) > 0:
                predictions = [extract_box_prediction(box) for box in best_result.boxes]
                eligible_predictions = [
                    prediction
                    for prediction in predictions
                    if prediction[1] >= CONFIDENCE_THRESHOLD
                ]
                if eligible_predictions:
                    class_id, raw_confidence = max(
                        eligible_predictions, key=lambda prediction: prediction[1]
                    )
                    confidence = raw_confidence * 100
                    annotated_image = best_result.plot()
                    try:
                        cv2 = import_module('cv2')
                        is_success, buffer = cv2.imencode('.jpg', annotated_image)
                    except Exception as exc:
                        raise ServiceUnavailableError(
                            'Image annotation runtime is unavailable.'
                        ) from exc
                    if not is_success or buffer is None:
                        raise ServiceUnavailableError(
                            'Failed to encode the annotated detection image.'
                        )
                    result_image_content = ContentFile(
                        buffer.tobytes(), name=os.path.basename(image_path)
                    )
                    pest_id = map_model_class_to_pest_id(class_id)

        if result_image_content is None:
            result_image_content = get_original_image_content(image_path)
        return pest_id, confidence, result_image_content
    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as exc:
        logger.warning('Image detection inference failed: %s', exc)
        raise ServiceUnavailableError('Image detection runtime failed during inference.') from exc


@login_required
def upload_image_for_detection(request):
    if request.method != 'POST':
        return JsonResponse(
            {'error': 'Invalid request method. Only POST requests are allowed'}, status=405
        )

    image_file = request.FILES.get('image')
    validate_image_file(image_file)
    temp_image_path = None
    try:
        temp_image_path = save_temp_image(image_file)

        pest_id, confidence, result_image_content = process_image(temp_image_path)
        if pest_id is None:
            raise ValidationError('No pest was detected in the uploaded image.')
        try:
            pest_info = Pest.objects.get(id=pest_id)
        except Pest.DoesNotExist as exc:
            raise ValidationError('Detected pest is not registered.') from exc

        detection = PestDetection(
            user=request.user,
            pest=pest_info,
            image=result_image_content,
            detection_date=timezone.now(),
            confidence=confidence,
        )
        try:
            with transaction.atomic():
                detection.save()
        except Exception:
            delete_detection_image(detection.image)
            raise

        return JsonResponse(serialize_detection(detection), status=200)

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as exc:
        logger.exception('Unhandled exception during image processing: %s', exc)
        raise InternalServerError('An unexpected error occurred.')
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            try:
                os.remove(temp_image_path)
            except OSError:
                logger.warning('Failed to remove a temporary detection upload file.')


@login_required
def list_detection_sessions(request):
    try:
        sessions = (
            PestDetection.objects.select_related('pest')
            .filter(user=request.user)
            .order_by('-detection_date')
        )
        session_list = [
            {
                'session_id': session.id,
                'pest_name': session.pest.pest_name,
                'detection_date': timezone.localtime(session.detection_date).strftime(
                    '%Y-%m-%d %H:%M'
                ),
                'confidence': session.confidence,
                'user_image_url': detection_image_url_or_none(session),
            }
            for session in sessions
        ]
        return JsonResponse(session_list, safe=False)
    except Exception as exc:
        logger.exception('Error retrieving sessions: %s', exc)
        raise InternalServerError(
            'An unexpected error occurred while retrieving detection sessions.'
        )


@login_required
def detection_session_details(request, session_id):
    try:
        session = get_owned_detection(request.user, session_id)
        return JsonResponse(serialize_detection(session))
    except NotFoundError:
        raise
    except Exception as exc:
        logger.exception('Unhandled exception in session details: %s', exc)
        raise InternalServerError('An unexpected error occurred while fetching session details.')


@login_required
@require_GET
def detection_image(request, session_id):
    session = get_owned_detection(request.user, session_id)
    if not session.image:
        raise NotFoundError('Detection image not found')

    image_file = None
    try:
        try:
            image_file = session.image.open('rb')
        except FileNotFoundError:
            if settings.USE_S3:
                raise
            media_root = Path(settings.MEDIA_ROOT).resolve()
            legacy_path = (media_root / session.image.name).resolve()
            if not legacy_path.is_relative_to(media_root) or not legacy_path.is_file():
                raise
            image_file = legacy_path.open('rb')
        with Image.open(image_file) as image:
            content_type = Image.MIME.get(image.format)
            if content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                raise UnidentifiedImageError('Unsupported stored image format')
        image_file.seek(0)
    except (FileNotFoundError, UnidentifiedImageError, OSError, ValueError) as exc:
        if image_file:
            image_file.close()
        raise NotFoundError('Detection image not found') from exc
    except Exception as exc:
        if image_file:
            image_file.close()
        logger.exception('Failed to open a stored detection image: %s', exc)
        raise InternalServerError('Failed to retrieve detection image.') from exc

    response = FileResponse(image_file, content_type=content_type)
    response['Cache-Control'] = 'private, no-store, max-age=0'
    response['X-Content-Type-Options'] = 'nosniff'
    return response


@login_required
@require_http_methods(['DELETE'])
def delete_detection_session(request, session_id):
    try:
        session = get_owned_detection(request.user, session_id)
        image = session.image
        with transaction.atomic():
            session.delete()
            transaction.on_commit(lambda: delete_detection_image(image))
        return JsonResponse({'success': 'Detection session deleted successfully'}, status=200)
    except NotFoundError:
        raise
    except Exception as exc:
        logger.exception('Error deleting detection session: %s', exc)
        raise InternalServerError(
            'An unexpected error occurred while deleting the detection session.'
        )
