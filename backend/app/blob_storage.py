"""
app/blob_storage.py -- thin wrapper around Azure Blob Storage for the
avatars container. Extracted as its own module since the same client
setup is needed by both the upload route (patients.py) and the
download/streaming route (main.py or wherever it ends up).

Replaces local-disk storage (uploads/avatars/) which doesn't survive a
redeploy on Azure Container Apps' ephemeral filesystem -- see the
now-removed comment on upload_my_profile_photo for the original bug
report.
"""

import os
from functools import lru_cache

from azure.storage.blob import BlobServiceClient

AVATARS_CONTAINER = "avatars"


@lru_cache(maxsize=1)
def _get_blob_service_client() -> BlobServiceClient:
    conn_str = os.environ["AZURE_STORAGE_CONNECTION_STRING"]
    return BlobServiceClient.from_connection_string(conn_str)


def get_avatars_container_client():
    return _get_blob_service_client().get_container_client(AVATARS_CONTAINER)


def upload_avatar(filename: str, contents: bytes, content_type: str) -> None:
    container = get_avatars_container_client()
    container.upload_blob(
        name=filename,
        data=contents,
        overwrite=True,
        content_settings=_content_settings(content_type),
    )


def download_avatar(filename: str) -> bytes:
    container = get_avatars_container_client()
    blob = container.get_blob_client(filename)
    return blob.download_blob().readall()


def avatar_exists(filename: str) -> bool:
    container = get_avatars_container_client()
    return container.get_blob_client(filename).exists()


def _content_settings(content_type: str):
    from azure.storage.blob import ContentSettings
    return ContentSettings(content_type=content_type)
