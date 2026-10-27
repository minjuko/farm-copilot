from pathlib import Path

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

StorageBackend = S3Boto3Storage if settings.USE_S3 else FileSystemStorage


class PostBoardStorage(StorageBackend):
    if settings.USE_S3:
        location = 'post_board'
        default_acl = 'public-read'
    file_overwrite = False


class PestDetectionStorage(StorageBackend):
    default_acl = None
    querystring_auth = True
    if settings.USE_S3:
        location = 'pest_detection'
    else:
        location = str(settings.DETECTION_IMAGE_ROOT)
        private_root = Path(location)
        media_root = Path(settings.MEDIA_ROOT).resolve()
        if (
            private_root == media_root
            or private_root.is_relative_to(media_root)
            or media_root.is_relative_to(private_root)
        ):
            raise ImproperlyConfigured(
                'Detection image storage must be separate from public media.'
            )
    file_overwrite = False


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = None


class MediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = None
    file_overwrite = False
