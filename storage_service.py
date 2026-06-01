import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class LocalStorageService:
    def __init__(self, upload_folder):
        self.upload_folder = Path(upload_folder)
        self.upload_folder.mkdir(parents=True, exist_ok=True)

    def save_upload(self, file_storage, user_id, stored_filename):
        user_dir = self.upload_folder / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        local_path = user_dir / stored_filename
        file_storage.save(local_path)
        return {
            "storage_key": str(local_path.relative_to(self.upload_folder)).replace("\\", "/"),
            "local_path": str(local_path),
        }

    def delete(self, storage_key):
        local_path = self.upload_folder / storage_key
        if local_path.exists():
            local_path.unlink()

    def get_local_path(self, storage_key, user_id=None, stored_filename=None):
        return str(self.upload_folder / storage_key)


class S3StorageService(LocalStorageService):
    def __init__(self, upload_folder, bucket_name, region):
        super().__init__(upload_folder)
        self.bucket_name = bucket_name
        self.region = region

    def _client(self):
        import boto3

        return boto3.client("s3", region_name=self.region or None)

    def save_upload(self, file_storage, user_id, stored_filename):
        saved = super().save_upload(file_storage, user_id, stored_filename)
        s3_key = f"users/{user_id}/documents/{stored_filename}"

        self._client().upload_file(saved["local_path"], self.bucket_name, s3_key)
        saved["storage_key"] = s3_key

        # Clean up local temp file after successful S3 upload
        try:
            local_path = Path(saved["local_path"])
            if local_path.exists():
                local_path.unlink()
                logger.debug("Cleaned up local temp file: %s", saved["local_path"])
        except OSError as exc:
            logger.warning("Failed to clean up local temp file %s: %s", saved["local_path"], exc)

        return saved

    def delete(self, storage_key):
        try:
            self._client().delete_object(Bucket=self.bucket_name, Key=storage_key)
        finally:
            local_key = os.path.basename(storage_key)
            for candidate in self.upload_folder.rglob(local_key):
                if candidate.is_file():
                    candidate.unlink()

    def get_local_path(self, storage_key, user_id=None, stored_filename=None):
        if not user_id or not stored_filename:
            raise RuntimeError("user_id and stored_filename are required to restore an S3 document locally.")

        user_dir = self.upload_folder / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)
        local_path = user_dir / stored_filename

        if not local_path.exists():
            self._client().download_file(self.bucket_name, storage_key, str(local_path))

        return str(local_path)


def create_storage_service(config):
    backend = config.get("STORAGE_BACKEND") if isinstance(config, dict) else config.STORAGE_BACKEND
    upload_folder = config.get("UPLOAD_FOLDER") if isinstance(config, dict) else config.UPLOAD_FOLDER
    bucket_name = config.get("S3_BUCKET_NAME") if isinstance(config, dict) else config.S3_BUCKET_NAME
    region = config.get("AWS_REGION") if isinstance(config, dict) else config.AWS_REGION

    if backend == "s3":
        if not bucket_name:
            raise RuntimeError("S3_BUCKET_NAME is required when STORAGE_BACKEND=s3.")
        return S3StorageService(upload_folder, bucket_name, region)
    return LocalStorageService(upload_folder)
