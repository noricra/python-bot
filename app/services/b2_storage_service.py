"""
Backblaze B2 Object Storage Service
Handles upload/download/delete of product files to B2
"""
import boto3
import logging
import os
import asyncio
from typing import Optional, BinaryIO
from botocore.exceptions import ClientError
from app.core import settings

logger = logging.getLogger(__name__)

class B2StorageService:
    """Service for managing files on Backblaze B2 (Singleton Pattern)"""
    
    _client_instance = None # Stocke la connexion pour la réutiliser pour tout le monde

    def __init__(self):
        """Initialize B2 client using S3-compatible API (Only once)"""
        self.bucket_name = settings.B2_BUCKET_NAME

        if not settings.B2_KEY_ID or not settings.B2_APPLICATION_KEY:
            logger.warning("⚠️ B2 credentials not configured - file uploads will fail")
            self.client = None
            return

        # Singleton: Si le client existe déjà, on ne le recrée pas
        # Cela gagne 1 à 2 secondes par upload/téléchargement
        if B2StorageService._client_instance is None:
            try:
                B2StorageService._client_instance = boto3.client(
                    's3',
                    endpoint_url=settings.B2_ENDPOINT,
                    aws_access_key_id=settings.B2_KEY_ID,
                    aws_secret_access_key=settings.B2_APPLICATION_KEY
                )
                logger.info("✅ B2 Storage Client initialized (New Connection)")
            except Exception as e:
                logger.error(f"❌ Failed to initialize B2 client: {e}")
                B2StorageService._client_instance = None
        
        # On utilise l'instance partagée
        self.client = B2StorageService._client_instance

    def _upload_file_blocking(self, file_path: str, object_key: str) -> Optional[str]:
        """
        Blocking file upload to B2 (to be called via asyncio.to_thread)
        """
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return None

        try:
            # Upload file
            with open(file_path, 'rb') as file:
                self.client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_key
                )

            # Generate URL
            url = f"{settings.B2_ENDPOINT}/{self.bucket_name}/{object_key}"
            logger.info(f"✅ File uploaded to B2: {object_key}")
            return url

        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            return None
        except ClientError as e:
            logger.error(f"❌ B2 upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during upload: {e}")
            return None

    async def upload_file(self, file_path: str, object_key: str) -> Optional[str]:
        """
        Upload a file to B2 (async, non-bloquant)
        C'est cette méthode que sell_handlers appelle avec 'await'
        """
        return await asyncio.to_thread(self._upload_file_blocking, file_path, object_key)

    def _upload_fileobj_blocking(self, file_obj: BinaryIO, object_key: str) -> Optional[str]:
        """Blocking file object upload to B2"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return None

        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key
            )

            url = f"{settings.B2_ENDPOINT}/{self.bucket_name}/{object_key}"
            logger.info(f"✅ File object uploaded to B2: {object_key}")
            return url

        except ClientError as e:
            logger.error(f"❌ B2 upload failed: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error during upload: {e}")
            return None

    async def upload_fileobj(self, file_obj: BinaryIO, object_key: str) -> Optional[str]:
        return await asyncio.to_thread(self._upload_fileobj_blocking, file_obj, object_key)

    def _download_file_blocking(self, object_key: str, destination_path: str) -> bool:
        """Blocking file download from B2"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return False

        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(destination_path), exist_ok=True)

            self.client.download_file(
                Bucket=self.bucket_name,
                Key=object_key,
                Filename=destination_path
            )

            logger.info(f"✅ File downloaded from B2: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"❌ B2 download failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during download: {e}")
            return False

    async def download_file(self, object_key: str, destination_path: str) -> bool:
        return await asyncio.to_thread(self._download_file_blocking, object_key, destination_path)

    def get_download_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for downloading a file"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return None

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key
                },
                ExpiresIn=expires_in
            )
            logger.info(f"✅ Presigned URL generated for: {object_key}")
            return url

        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned URL: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error generating URL: {e}")
            return None

    def generate_presigned_upload_url(self, object_key: str, content_type: str = 'application/octet-stream', expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for uploading a file (PUT)"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return None

        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_key,
                    'ContentType': content_type
                },
                ExpiresIn=expires_in
            )
            logger.info(f"✅ Presigned upload URL generated for: {object_key} (Content-Type: {content_type})")
            return url

        except ClientError as e:
            logger.error(f"❌ Failed to generate presigned upload URL: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error generating upload URL: {e}")
            return None

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from B2"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return False

        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"✅ File deleted from B2: {object_key}")
            return True

        except ClientError as e:
            logger.error(f"❌ B2 delete failed: {e}")
            return False
        except Exception as e:
            logger.error(f"❌ Unexpected error during delete: {e}")
            return False

    def file_exists(self, object_key: str) -> bool:
        """Check if a file exists in B2"""
        if not self.client:
            return False

        try:
            self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return True

        except ClientError:
            return False
        except Exception:
            return False

    def get_file_size(self, object_key: str) -> Optional[int]:
        """Get the size of a file in B2"""
        if not self.client:
            return None

        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            return response['ContentLength']

        except ClientError as e:
            logger.error(f"❌ Failed to get file size: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Unexpected error getting file size: {e}")
            return None