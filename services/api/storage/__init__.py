"""Storage package — E04."""
from .object_store import FilesystemStore, ObjectStore, S3Store, get_object_store

__all__ = ["FilesystemStore", "ObjectStore", "S3Store", "get_object_store"]
