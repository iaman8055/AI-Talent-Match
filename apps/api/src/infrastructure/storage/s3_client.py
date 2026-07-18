import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError


class S3StorageClient:
    """Generic S3-compatible client — works against Supabase Storage's S3-compatible API
    (via endpoint_url) or real AWS S3 (endpoint_url=None) with no code difference."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None,
        access_key_id: str | None,
        secret_access_key: str | None,
        region: str,
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
            region_name=region,
            config=BotoConfig(s3={"addressing_style": "path"}),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._bucket)

    def upload(self, key: str, data: bytes, content_type: str) -> None:
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def download(self, key: str) -> bytes:
        response = self._client.get_object(Bucket=self._bucket, Key=key)
        body: bytes = response["Body"].read()
        return body

    def generate_presigned_url(self, key: str, expires_in_seconds: int) -> str:
        url: str = self._client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self._bucket, "Key": key},
            ExpiresIn=expires_in_seconds,
        )
        return url
