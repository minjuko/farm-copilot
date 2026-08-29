from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage


StorageBackend = S3Boto3Storage if settings.USE_S3 else FileSystemStorage

class PostBoardStorage(StorageBackend):
    if settings.USE_S3:
        location = 'post_board'
        default_acl = 'public-read'
    file_overwrite = False

class PestDetectionStorage(StorageBackend):
    if settings.USE_S3:
        location = 'pest_detection'
        default_acl = 'public-read'
    file_overwrite = False


class StaticStorage(S3Boto3Storage):
    location = 'static'
    default_acl = None


class MediaStorage(S3Boto3Storage):
    location = 'media'
    default_acl = None
    file_overwrite = False
