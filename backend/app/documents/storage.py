from abc import ABC, abstractmethod
from threading import Lock

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.config import Settings


class Storage(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> None: ...

    @abstractmethod
    def get(self, key: str) -> bytes: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...

    def ensure_ready(self) -> None:
        return None


class MemoryStorage(Storage):
    def __init__(self) -> None:
        self._data: dict[str, bytes] = {}
        self._lock = Lock()

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        with self._lock:
            self._data[key] = data

    def get(self, key: str) -> bytes:
        with self._lock:
            if key not in self._data:
                raise FileNotFoundError(key)
            return self._data[key]

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


class MinioStorage(Storage):
    def __init__(self, settings: Settings) -> None:
        scheme = "https" if settings.minio_secure else "http"
        self.bucket = settings.minio_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_access_key,
            aws_secret_access_key=settings.minio_secret_key,
            region_name="us-east-1",
            config=BotoConfig(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def ensure_ready(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError:
            self.client.create_bucket(Bucket=self.bucket)

    def put(self, key: str, data: bytes, content_type: str = "application/pdf") -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        obj = self.client.get_object(Bucket=self.bucket, Key=key)
        return obj["Body"].read()

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def build_storage(settings: Settings) -> Storage:
    if settings.storage_backend == "s3":
        return MinioStorage(settings)
    return MemoryStorage()
