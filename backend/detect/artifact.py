"""Shared metadata and validation helpers for the externally stored YOLO artifact."""

import hashlib
import importlib
import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)


class RuntimeUnavailableError(Exception):
    pass


class ModelContractMismatchError(Exception):
    pass


class ModelLoadFailedError(Exception):
    pass

EXPECTED_SHA256 = 'b4e90d9feef9c9e35923c4e5fbf386d6e37ae6b2a3df687edfb14173bd7c10f4'
EXPECTED_SIZE = 87_631_411
EXPECTED_CLASSES = {
    0: '고추 탄저병',
    1: '고추 흰가루병',
    2: '오이 노균병',
    3: '토마토 흰가루병',
    4: '오이 노균병',
    5: '오이 흰가루병',
}
_ARTIFACT_CHECK_CACHE = {}


def resolve_model_path():
    """Resolve YOLO_MODEL_PATH the same way as the inference service."""
    import os

    configured = os.getenv('YOLO_MODEL_PATH')
    path = Path(configured) if configured else Path(settings.BASE_DIR) / 'best.pt'
    return path if path.is_absolute() else Path(settings.BASE_DIR) / path


def sha256_file(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def validate_loaded_model(model):
    try:
        names = {int(class_id): label for class_id, label in model.names.items()}
        task = model.task
        class_count = int(model.model.yaml.get('nc', len(names)))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ModelContractMismatchError('Model metadata is incomplete.') from exc
    if task != 'detect' or class_count != len(EXPECTED_CLASSES) or names != EXPECTED_CLASSES:
        raise ModelContractMismatchError('Model task or class ID/name contract does not match the service.')


def load_validated_model(path):
    """Import the optional runtime, load a YOLO checkpoint and validate its contract."""
    try:
        importlib.import_module('torch')
        ultralytics = importlib.import_module('ultralytics')
    except ImportError as exc:
        raise RuntimeUnavailableError('PyTorch or Ultralytics is not installed.') from exc
    try:
        model = ultralytics.YOLO(str(path))
        validate_loaded_model(model)
    except ModelContractMismatchError:
        raise
    except Exception as exc:
        logger.warning('YOLO artifact failed to load: %s', exc)
        raise ModelLoadFailedError('YOLO model loading failed.') from exc
    return model


def check_artifact_readiness(path):
    """Load and smoke-test once per file fingerprint in this process."""
    path = Path(path)
    try:
        stat = path.stat()
    except OSError:
        return {'ready': False, 'reason': 'model_missing'}
    if not path.is_file():
        return {'ready': False, 'reason': 'model_missing'}
    key = (str(path.resolve()), stat.st_size, stat.st_mtime_ns)
    if key in _ARTIFACT_CHECK_CACHE:
        return _ARTIFACT_CHECK_CACHE[key]
    try:
        digest = sha256_file(path)
    except OSError:
        return {'ready': False, 'reason': 'model_missing'}
    if stat.st_size != EXPECTED_SIZE or digest != EXPECTED_SHA256:
        result = {'ready': False, 'reason': 'model_integrity_mismatch'}
    else:
        try:
            from detect import views as detection_views

            # Keep the readiness model and request inference cache aligned to avoid
            # holding two copies of the 87 MB checkpoint in memory.
            for old_key in tuple(_ARTIFACT_CHECK_CACHE):
                if old_key != key:
                    detection_views._yolo_model = None
            model = detection_views._yolo_model
            if model is None:
                model = load_validated_model(path)
                detection_views._yolo_model = model
            else:
                validate_loaded_model(model)
        except RuntimeUnavailableError:
            result = {'ready': False, 'reason': 'runtime_unavailable'}
        except ModelContractMismatchError:
            result = {'ready': False, 'reason': 'model_contract_mismatch'}
        except ModelLoadFailedError:
            result = {'ready': False, 'reason': 'model_load_failed'}
        else:
            try:
                from PIL import Image

                image = Image.new('RGB', (64, 64), color=(96, 128, 64))
                model(image, device='cpu', verbose=False)
            except Exception as exc:
                logger.warning('Detection readiness smoke test failed: %s', exc)
                result = {'ready': False, 'reason': 'inference_unavailable'}
            else:
                result = {'ready': True, 'reason': None}
    _ARTIFACT_CHECK_CACHE.clear()
    _ARTIFACT_CHECK_CACHE[key] = result
    return result
