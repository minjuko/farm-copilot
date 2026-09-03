import logging
import os
import tempfile
import warnings
from importlib import import_module
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from PIL import Image, UnidentifiedImageError

from common.decorators import login_required
from common.exceptions import (
    InternalServerError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

from .models import Pest, PestDetection, PestModelClass

logger = logging.getLogger(__name__)

DEFAULT_MODEL_PATH = Path(settings.BASE_DIR) / 'best.pt'
CONFIDENCE_THRESHOLD = 0.6
MAPPING_UNAVAILABLE_MESSAGE = '병해 탐지 모델의 상세정보 매핑이 준비되지 않았습니다.'
MODEL_CONTRACT_MISMATCH_MESSAGE = '병해 탐지 모델의 클래스 계약이 일치하지 않습니다.'
EXPECTED_MODEL_CLASS_NAMES = {
    0: '고추 탄저병',
    1: '고추 흰가루병',
    2: '오이 노균병',
    3: '토마토 흰가루병',
    4: '오이 노균병',
    5: '오이 흰가루병',
}
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
    global _yolo_model

    if _yolo_model is not None:
        return _yolo_model

    if not MODEL_PATH.exists():
        raise ServiceUnavailableError(
            'Image detection model is not available in this public repository.'
        )

    try:
        yolo_class = import_module('ultralytics').YOLO
        model = yolo_class(str(MODEL_PATH))
        validate_model_contract(model)
        _yolo_model = model
    except ServiceUnavailableError:
        raise
    except Exception as exc:
        logger.warning('Image detection runtime is unavailable: %s', exc)
        raise ServiceUnavailableError(
            'Image detection runtime is not installed or failed to initialize.'
        ) from exc

    return _yolo_model


def validate_image_file(image_file):
    if not image_file:
        raise ValidationError('No image uploaded.')
    if image_file.size == 0:
        raise ValidationError('Uploaded image is empty.')

    allowed_types = {'image/jpeg', 'image/png', 'image/webp'}
    allowed_extensions = {'jpg', 'jpeg', 'png', 'webp'}
    extension = Path(image_file.name).suffix.lower().lstrip('.')
    if image_file.content_type not in allowed_types or extension not in allowed_extensions:
        raise ValidationError('Only JPEG, PNG, and WebP images are allowed.')

    try:
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(image_file) as image:
                if image.format not in {'JPEG', 'PNG', 'WEBP'}:
                    raise ValidationError('Only JPEG, PNG, and WebP images are allowed.')
                image.verify()

        image_file.seek(0)
        with Image.open(image_file) as image:
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
    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as temp_file:
        for chunk in image_file.chunks():
            temp_file.write(chunk)
        return temp_file.name


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


def image_url_or_none(image_field):
    if not image_field:
        return None
    try:
        return image_field.url
    except (ValueError, OSError):
        return None


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
                eligible_boxes = [
                    box
                    for box in best_result.boxes
                    if float(box.conf.item()) >= CONFIDENCE_THRESHOLD
                ]
                if eligible_boxes:
                    box = max(eligible_boxes, key=lambda item: float(item.conf.item()))
                    confidence = float(box.conf.item()) * 100
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
                    pest_id = map_model_class_to_pest_id(box.cls.item())

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
        detection.save()

        detection_payload = {
            'session_id': detection.id,
            'pest_name': pest_info.pest_name,
            'occurrence_environment': pest_info.occurrence_environment,
            'symptom_description': pest_info.symptom_description,
            'prevention_methods': pest_info.prevention_methods,
            'pesticide_name': pest_info.pesticide_name,
            'information_source': pest_info.information_source,
            'information_source_url': pest_info.information_source_url,
            'confidence': confidence,
            'user_image_url': image_url_or_none(detection.image),
            'db_image_url': detection.pest.image_url,
            'detection_date': timezone.localtime(detection.detection_date).strftime(
                '%Y-%m-%d %H:%M'
            ),
        }

        return JsonResponse(detection_payload, status=200)

    except (ServiceUnavailableError, ValidationError):
        raise
    except Exception as exc:
        logger.exception('Unhandled exception during image processing: %s', exc)
        raise InternalServerError('An unexpected error occurred.')
    finally:
        if temp_image_path and os.path.exists(temp_image_path):
            os.remove(temp_image_path)


@login_required
def list_detection_sessions(request):
    try:
        sessions = PestDetection.objects.filter(user=request.user).order_by('-detection_date')
        session_list = [
            {
                'session_id': session.id,
                'pest_name': session.pest.pest_name,
                'detection_date': timezone.localtime(session.detection_date).strftime(
                    '%Y-%m-%d %H:%M'
                ),
                'confidence': session.confidence,
                'user_image_url': image_url_or_none(session.image),
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
        session = PestDetection.objects.get(id=session_id, user=request.user)
        details = {
            'session_id': session.id,
            'pest_name': session.pest.pest_name,
            'occurrence_environment': session.pest.occurrence_environment,
            'symptom_description': session.pest.symptom_description,
            'prevention_methods': session.pest.prevention_methods,
            'pesticide_name': session.pest.pesticide_name,
            'information_source': session.pest.information_source,
            'information_source_url': session.pest.information_source_url,
            'detection_date': timezone.localtime(session.detection_date).strftime('%Y-%m-%d %H:%M'),
            'confidence': session.confidence,
            'user_image_url': image_url_or_none(session.image),
            'db_image_url': session.pest.image_url,
        }
        return JsonResponse(details)
    except PestDetection.DoesNotExist:
        raise NotFoundError('Detection session not found')
    except Exception as exc:
        logger.exception('Unhandled exception in session details: %s', exc)
        raise InternalServerError('An unexpected error occurred while fetching session details.')


@login_required
@require_http_methods(['DELETE'])
def delete_detection_session(request, session_id):
    try:
        session = PestDetection.objects.get(id=session_id, user=request.user)
        session.delete()
        return JsonResponse({'success': 'Detection session deleted successfully'}, status=200)
    except PestDetection.DoesNotExist:
        raise NotFoundError('Detection session not found')
    except Exception as exc:
        logger.exception('Error deleting detection session: %s', exc)
        raise InternalServerError(
            'An unexpected error occurred while deleting the detection session.'
        )
