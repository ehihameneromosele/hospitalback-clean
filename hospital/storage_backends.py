# hospital/storage_backends.py
from django.conf import settings
from storages.backends.s3boto3 import S3Boto3Storage
import logging

logger = logging.getLogger(__name__)


class MediaStorage(S3Boto3Storage):
    """
    Custom storage for media files on S3.
    Files go under the 'media/' prefix. Public read access is granted
    by the bucket policy, not by ACLs.
    """
    location = 'media'
    file_overwrite = False
    default_acl = None
    querystring_auth = False

    def __init__(self, *args, **kwargs):
        if settings.AWS_CREDENTIALS_PROVIDED:
            super().__init__(*args, **kwargs)
            logger.info(f'MediaStorage initialized for bucket: {settings.AWS_STORAGE_BUCKET_NAME}')
        else:
            raise ValueError('AWS credentials not provided - cannot use S3 storage')

    # def url(self, name, parameters=None, expire=None, http_method=None):
    #     """
    #     Generate a URL for the file.
    #     With querystring_auth=False and default_acl='public-read',
    #     this returns a public URL.
    #     """
    #     # Override to ensure public URLs
    #     url = super().url(name, parameters=parameters, expire=expire, http_method=http_method)
    #     return url
