# Author: DUC LONG
# Year: 2026
# Project: VideoDubAI

"""
Cloud storage service — S3/MinIO integration.

Provides a unified interface for file storage that works with:
- Local filesystem (default)
- S3-compatible storage (MinIO, AWS S3, etc.)
"""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import BinaryIO

from backend.config import get_settings

logger = logging.getLogger(__name__)


class BaseStorage(ABC):
    """Base class for storage providers."""

    @abstractmethod
    async def put(self, key: str, data: bytes, content_type: str = "") -> str:
        """Store data. Returns the storage URL/path."""
        ...

    @abstractmethod
    async def get(self, key: str) -> bytes:
        """Retrieve data by key."""
        ...

    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """Get a pre-signed URL for the key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete a file."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Check if a file exists."""
        ...


class LocalStorage(BaseStorage):
    """Local filesystem storage."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        os.makedirs(base_dir, exist_ok=True)

    async def put(self, key: str, data: bytes, content_type: str = "") -> str:
        path = os.path.join(self._base_dir, key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    async def get(self, key: str) -> bytes:
        path = os.path.join(self._base_dir, key)
        with open(path, "rb") as f:
            return f.read()

    async def get_url(self, key: str, expires: int = 3600) -> str:
        path = os.path.join(self._base_dir, key)
        return f"file://{os.path.abspath(path)}"

    async def delete(self, key: str) -> bool:
        path = os.path.join(self._base_dir, key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        path = os.path.join(self._base_dir, key)
        return os.path.exists(path)


class S3Storage(BaseStorage):
    """S3-compatible storage (MinIO, AWS S3, etc.)."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str = "",
        access_key: str = "",
        secret_key: str = "",
        region: str = "us-east-1",
    ) -> None:
        self._bucket = bucket
        self._endpoint_url = endpoint_url
        self._access_key = access_key
        self._secret_key = secret_key
        self._region = region
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import aioboto3
                session = aioboto3.Session()
                self._client = session.client(
                    "s3",
                    endpoint_url=self._endpoint_url or None,
                    aws_access_key_id=self._access_key,
                    aws_secret_access_key=self._secret_key,
                    region_name=self._region,
                )
            except ImportError:
                raise RuntimeError("aioboto3 not installed. Run: pip install aioboto3")
        return self._client

    async def put(self, key: str, data: bytes, content_type: str = "") -> str:
        client = self._get_client()
        async with client as s3:
            kwargs = {"Bucket": self._bucket, "Key": key, "Body": data}
            if content_type:
                kwargs["ContentType"] = content_type
            await s3.put_object(**kwargs)
        return f"s3://{self._bucket}/{key}"

    async def get(self, key: str) -> bytes:
        client = self._get_client()
        async with client as s3:
            response = await s3.get_object(Bucket=self._bucket, Key=key)
            return await response["Body"].read()

    async def get_url(self, key: str, expires: int = 3600) -> str:
        client = self._get_client()
        async with client as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
            return url

    async def delete(self, key: str) -> bool:
        try:
            client = self._get_client()
            async with client as s3:
                await s3.delete_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            client = self._get_client()
            async with client as s3:
                await s3.head_object(Bucket=self._bucket, Key=key)
            return True
        except Exception:
            return False


def get_storage() -> BaseStorage:
    """Get the configured storage provider."""
    settings = get_settings()

    # Check if S3/MinIO is configured
    s3_endpoint = os.environ.get("S3_ENDPOINT_URL", "")
    s3_bucket = os.environ.get("S3_BUCKET", "videodub")
    s3_access_key = os.environ.get("S3_ACCESS_KEY", "")
    s3_secret_key = os.environ.get("S3_SECRET_KEY", "")

    if s3_endpoint or s3_access_key:
        logger.info("Using S3 storage: %s", s3_endpoint or "AWS S3")
        return S3Storage(
            bucket=s3_bucket,
            endpoint_url=s3_endpoint,
            access_key=s3_access_key,
            secret_key=s3_secret_key,
        )

    # Fallback to local storage
    logger.info("Using local storage: %s", settings.UPLOAD_DIR)
    return LocalStorage(settings.UPLOAD_DIR)
