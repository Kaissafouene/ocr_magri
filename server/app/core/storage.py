import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
import hashlib
import io
from pathlib import Path
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class StorageClient:
    def __init__(self) -> None:
        self._mode = settings.storage_mode.lower()
        self._bucket = settings.storage_bucket_name
        self._local_root = Path(settings.local_storage_path).resolve()
        self._client = None

        if self._mode == "local":
            self._local_root.mkdir(parents=True, exist_ok=True)
            return

        self._client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint_url,
            aws_access_key_id=settings.storage_access_key,
            aws_secret_access_key=settings.storage_secret_key,
            region_name=settings.storage_region,
            config=Config(signature_version="s3v4"),
        )

    def _local_path(self, key: str) -> Path:
        return self._local_root.joinpath(*key.split("/"))

    def upload_pdf(self, job_id: str, file_bytes: bytes) -> str:
        """
        Store original PDF immutably.
        Key format: originals/{job_id}/document.pdf
        Returns the storage key.
        """
        key = f"originals/{job_id}/document.pdf"
        if self._mode == "local":
            path = self._local_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(file_bytes)
            logger.info("pdf_uploaded_local", job_id=job_id, key=key, size=len(file_bytes))
            return key

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=file_bytes,
            ContentType="application/pdf",
            Metadata={"sha256": hashlib.sha256(file_bytes).hexdigest()},
        )
        logger.info("pdf_uploaded", job_id=job_id, key=key, size=len(file_bytes))
        return key

    def upload_page_image(self, job_id: str, page_num: int, image_bytes: bytes) -> str:
        """Store preprocessed page image. 30-day TTL set via bucket lifecycle rule."""
        key = f"pages/{job_id}/page_{page_num:03d}.png"
        if self._mode == "local":
            path = self._local_path(key)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(image_bytes)
            return key

        self._client.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=image_bytes,
            ContentType="image/png",
        )
        return key

    def download_pdf(self, storage_key: str) -> bytes:
        if self._mode == "local":
            return self._local_path(storage_key).read_bytes()

        response = self._client.get_object(Bucket=self._bucket, Key=storage_key)
        return response["Body"].read()

    def get_pdf_hash(self, storage_key: str) -> str:
        if self._mode == "local":
            file_bytes = self._local_path(storage_key).read_bytes()
            return hashlib.sha256(file_bytes).hexdigest()

        response = self._client.head_object(Bucket=self._bucket, Key=storage_key)
        return response.get("Metadata", {}).get("sha256", "")


storage_client = StorageClient()
