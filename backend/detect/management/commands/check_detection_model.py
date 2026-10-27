"""Preflight the external YOLO model before starting or deploying the service."""

import logging
import tempfile
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from PIL import Image

from detect.artifact import (
    EXPECTED_CLASSES,
    EXPECTED_SHA256,
    EXPECTED_SIZE,
    ModelContractMismatchError,
    ModelLoadFailedError,
    RuntimeUnavailableError,
    load_validated_model,
    resolve_model_path,
    sha256_file,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Validate the YOLO artifact, runtime, class contract, and CPU inference.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--model-path', help='Optional model path; defaults to YOLO_MODEL_PATH.'
        )

    def handle(self, *args, **options):
        path = Path(options['model_path']) if options['model_path'] else resolve_model_path()
        if not path.is_absolute():
            path = settings.BASE_DIR / path
        self.stdout.write(f'Model path: {path}')
        if not path.is_file():
            raise CommandError(
                'Model file is missing. Place the approved best.pt artifact at this path.'
            )
        try:
            size = path.stat().st_size
            digest = sha256_file(path)
        except OSError as exc:
            raise CommandError(
                'Model file became unavailable or unreadable during preflight.'
            ) from exc
        self.stdout.write(f'File size: {size} bytes')
        self.stdout.write(f'SHA-256: {digest}')
        if digest != EXPECTED_SHA256 or size != EXPECTED_SIZE:
            raise CommandError('Model artifact integrity mismatch; no replacement was attempted.')
        try:
            model = load_validated_model(path)
        except RuntimeUnavailableError as exc:
            raise CommandError(f'AI runtime unavailable: {exc}') from exc
        except ModelContractMismatchError as exc:
            raise CommandError(f'Model class contract mismatch: {exc}') from exc
        except ModelLoadFailedError as exc:
            raise CommandError(f'Model load failed: {exc}') from exc
        self.stdout.write(f'Task/classes: detect / {len(EXPECTED_CLASSES)}')
        try:
            with tempfile.TemporaryDirectory(prefix='farm-copilot-preflight-') as temp_dir:
                smoke_path = Path(temp_dir) / 'cpu-smoke.png'
                Image.new('RGB', (64, 64), color=(96, 128, 64)).save(smoke_path)
                model(str(smoke_path), device='cpu', verbose=False)
        except Exception as exc:
            logger.warning('CPU model smoke test failed: %s', exc)
            raise CommandError('CPU inference smoke test failed.') from exc
        self.stdout.write(
            self.style.SUCCESS('CPU inference smoke test passed (synthetic 64x64 image).')
        )
        self.stdout.write(self.style.SUCCESS('Detection model preflight passed.'))
