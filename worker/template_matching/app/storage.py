import boto3

from app import config

_client = None


def get_bytes(key: str) -> bytes:
    """An object of the store: a page image of a document."""
    global _client
    if _client is None:
        # Built on first use: nothing connects at import, and a test never needs a store.
        _client = boto3.client(
            "s3",
            endpoint_url=config.AWS_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            region_name=config.AWS_REGION,
        )
    return _client.get_object(Bucket=config.AWS_BUCKET, Key=key)["Body"].read()
