"""Object storage abstraction — E04 Async Jobs & Storage.

Backends:
  - FilesystemStore: local dev (default when no S3_ENDPOINT set)
  - S3Store: MinIO / AWS S3 / Cloudflare R2 via boto3

All artifacts are content-addressed by SHA-256. The key may also include
a human-readable prefix but the hash is always included for verification.
"""
from __future__ import annotations

import hashlib
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path


class ObjectStore(ABC):
    @abstractmethod
    def put(self, key: str, data: bytes) -> str:
        """Store data at key, return SHA-256 hex of the bytes."""

    @abstractmethod
    def get(self, key: str) -> bytes:
        """Retrieve bytes at key."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if the key exists."""

    @staticmethod
    def sha256(data: bytes) -> str:
        return hashlib.sha256(data).hexdigest()


class FilesystemStore(ObjectStore):
    """Local filesystem store — for development and testing."""

    def __init__(self, base_path: str | Path = "./artifacts") -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        # Sanitize: replace path separators to prevent traversal
        safe = key.replace("/", os.sep).replace("..", "__")
        p = self.base / safe
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def put(self, key: str, data: bytes) -> str:
        digest = self.sha256(data)
        self._path(key).write_bytes(data)
        return digest

    def get(self, key: str) -> bytes:
        p = self._path(key)
        if not p.exists():
            raise FileNotFoundError(f"Object not found: {key}")
        return p.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).exists()


class S3Store(ObjectStore):
    """S3-compatible store (MinIO / AWS / R2)."""

    def __init__(
        self,
        bucket: str,
        endpoint_url: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
    ) -> None:
        import boto3  # type: ignore[import]

        self.bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        # Ensure bucket exists
        try:
            self._client.head_bucket(Bucket=bucket)
        except Exception:
            self._client.create_bucket(Bucket=bucket)

    def put(self, key: str, data: bytes) -> str:
        digest = self.sha256(data)
        self._client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            Metadata={"sha256": digest},
        )
        return digest

    def get(self, key: str) -> bytes:
        resp = self._client.get_object(Bucket=self.bucket, Key=key)
        return resp["Body"].read()

    def exists(self, key: str) -> bool:
        try:
            self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False


def get_object_store() -> ObjectStore:
    """Factory — returns the appropriate backend from environment."""
    endpoint = os.environ.get("S3_ENDPOINT")
    if endpoint:
        return S3Store(
            bucket=os.environ.get("S3_BUCKET", "advocate-artifacts"),
            endpoint_url=endpoint,
            access_key=os.environ.get("S3_ACCESS_KEY"),
            secret_key=os.environ.get("S3_SECRET_KEY"),
        )
    local_path = os.environ.get("ARTIFACT_PATH", "./artifacts")
    return FilesystemStore(base_path=local_path)
