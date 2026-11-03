import boto3
from botocore.exceptions import ClientError

from app.config import RustFsSettings

_settings = RustFsSettings()
_client = boto3.client(
    "s3",
    endpoint_url=_settings.AWS_ENDPOINT_URL,
    aws_access_key_id=_settings.AWS_ACCESS_KEY_ID,
    aws_secret_access_key=_settings.AWS_SECRET_ACCESS_KEY,
    region_name=_settings.AWS_REGION,
)
_bucket_ready = False


class ObjectNotFoundError(Exception):
    pass


def _ensure_bucket() -> None:
    # Lazy: a network call at import time would run during test collection and when the store is still starting.
    global _bucket_ready
    if _bucket_ready:
        return
    try:
        _client.head_bucket(Bucket=_settings.AWS_BUCKET)
    except ClientError:
        _client.create_bucket(Bucket=_settings.AWS_BUCKET)
    _bucket_ready = True


def put_object(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    _ensure_bucket()
    _client.put_object(Bucket=_settings.AWS_BUCKET, Key=key, Body=data, ContentType=content_type)


def get_object(key: str) -> tuple[bytes, str]:
    """The bytes of an object and its content type."""
    _ensure_bucket()
    try:
        response = _client.get_object(Bucket=_settings.AWS_BUCKET, Key=key)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
            raise ObjectNotFoundError(key) from error
        raise
    return response["Body"].read(), response.get("ContentType", "application/octet-stream")


def delete_prefix(prefix: str) -> None:
    _ensure_bucket()
    paginator = _client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=_settings.AWS_BUCKET, Prefix=prefix):
        objects = [{"Key": item["Key"]} for item in page.get("Contents", [])]
        if objects:
            _client.delete_objects(Bucket=_settings.AWS_BUCKET, Delete={"Objects": objects})
