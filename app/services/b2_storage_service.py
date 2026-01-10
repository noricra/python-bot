"""
Cloud Object Storage Service
Supports Cloudflare R2 (priority) and Backblaze B2 (fallback)
Handles upload/download/delete of product files
"""
import boto3
import logging
import os
import asyncio
import base64
import requests
from typing import Optional, BinaryIO, Dict
from botocore.exceptions import ClientError
from botocore.config import Config
from app.core import settings

logger = logging.getLogger(__name__)

class B2StorageService:
    """
    Service for managing files on Cloud Object Storage (Singleton Pattern)
    Priority: Cloudflare R2 (if configured) -> Backblaze B2 (fallback)
    """

    _client_instance = None
    _storage_type = None  # 'r2' or 'b2'

    def __init__(self):
        """Initialize storage client using S3-compatible API (R2 priority, B2 fallback)"""

        # Check if R2 is configured (priority)
        r2_endpoint = os.getenv('R2_ENDPOINT')
        r2_application_key = os.getenv('R2_APPLICATION_KEY')
        r2_secret_key = os.getenv('R2_SECRET_KEY')
        r2_bucket = os.getenv('R2_BUCKET_NAME')

        use_r2 = all([r2_endpoint, r2_application_key, r2_secret_key, r2_bucket])

        if use_r2:
            # Use Cloudflare R2
            self.bucket_name = r2_bucket

            if B2StorageService._client_instance is None or B2StorageService._storage_type != 'r2':
                try:
                    B2StorageService._client_instance = boto3.client(
                        's3',
                        endpoint_url=r2_endpoint,
                        aws_access_key_id=r2_application_key,
                        aws_secret_access_key=r2_secret_key,
                        region_name='auto',
                        config=Config(s3={'addressing_style': 'path'})
                    )
                    B2StorageService._storage_type = 'r2'
                    logger.info("✅ Cloudflare R2 Storage Client initialized (New Connection)")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize R2 client: {e}")
                    B2StorageService._client_instance = None
                    B2StorageService._storage_type = None
        else:
            # Fallback to Backblaze B2
            self.bucket_name = settings.B2_BUCKET_NAME

            if not settings.B2_KEY_ID or not settings.B2_APPLICATION_KEY:
                logger.warning("⚠️ Neither R2 nor B2 credentials configured - file uploads will fail")
                self.client = None
                return

            if B2StorageService._client_instance is None or B2StorageService._storage_type != 'b2':
                try:
                    B2StorageService._client_instance = boto3.client(
                        's3',
                        endpoint_url=settings.B2_ENDPOINT,
                        aws_access_key_id=settings.B2_KEY_ID,
                        aws_secret_access_key=settings.B2_APPLICATION_KEY
                    )
                    B2StorageService._storage_type = 'b2'
                    logger.info("✅ Backblaze B2 Storage Client initialized (New Connection)")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize B2 client: {e}")
                    B2StorageService._client_instance = None
                    B2StorageService._storage_type = None

        self.client = B2StorageService._client_instance
        self.storage_type = B2StorageService._storage_type

    def _upload_file_blocking(self, file_path: str, object_key: str) -> Optional[str]:
        """
        Blocking file upload to cloud storage (to be called via asyncio.to_thread)
        """
        if not self.client:
            logger.error(f"❌ [{self.storage_type.upper() if self.storage_type else 'STORAGE'}] Client not initialized")
            return None

        try:
            # Upload file
            with open(file_path, 'rb') as file:
                self.client.upload_fileobj(
                    file,
                    self.bucket_name,
                    object_key
                )

            # Generate URL based on storage type
            if self.storage_type == 'r2':
                endpoint = os.getenv('R2_ENDPOINT')
                url = f"{endpoint}/{self.bucket_name}/{object_key}"
                logger.info(f"✅ File uploaded to R2: {object_key}")
            else:
                url = f"{settings.B2_ENDPOINT}/{self.bucket_name}/{object_key}"
                logger.info(f"✅ File uploaded to B2: {object_key}")

            return url

        except FileNotFoundError:
            logger.error(f"❌ File not found: {file_path}")
            return None
        except ClientError as e:
            logger.error(f"❌ [{self.storage_type.upper()}] Upload failed: {e}")
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
        """Blocking file object upload to cloud storage"""
        if not self.client:
            logger.error(f"❌ [{self.storage_type.upper() if self.storage_type else 'STORAGE'}] Client not initialized")
            return None

        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                object_key
            )

            # Generate URL based on storage type
            if self.storage_type == 'r2':
                endpoint = os.getenv('R2_ENDPOINT')
                url = f"{endpoint}/{self.bucket_name}/{object_key}"
                logger.info(f"✅ File object uploaded to R2: {object_key}")
            else:
                url = f"{settings.B2_ENDPOINT}/{self.bucket_name}/{object_key}"
                logger.info(f"✅ File object uploaded to B2: {object_key}")

            return url

        except ClientError as e:
            logger.error(f"❌ [{self.storage_type.upper()}] Upload failed: {e}")
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
        """
        Generate a presigned URL for downloading a file

        R2: Supports ResponseContentDisposition - forces download
        B2: Does not support ResponseContentDisposition - files open in browser
        """
        logger.info(f"🔗 [{self.storage_type.upper() if self.storage_type else 'STORAGE'}-DOWNLOAD] get_download_url called with object_key={object_key}, expires_in={expires_in}")

        if not self.client:
            logger.error(f"❌ [{self.storage_type.upper() if self.storage_type else 'STORAGE'}-DOWNLOAD] Client not initialized")
            return None

        try:
            # Extract filename for Content-Disposition header
            filename = object_key.split('/')[-1]

            # Encode filename for RFC 5987 (handles spaces, accents, special chars)
            from urllib.parse import quote
            encoded_filename = quote(filename)

            # Build params based on storage type
            params = {
                'Bucket': self.bucket_name,
                'Key': object_key
            }

            # R2 supports ResponseContentDisposition - force download
            if self.storage_type == 'r2':
                # RFC 5987 format: attachment; filename*=UTF-8''encoded_name
                params['ResponseContentDisposition'] = f"attachment; filename*=UTF-8''{encoded_filename}"
                logger.info(f"🔧 [R2-DOWNLOAD] Using ResponseContentDisposition for forced download (RFC 5987)")
            else:
                logger.info(f"🔧 [B2-DOWNLOAD] ResponseContentDisposition not supported - files may open in browser")

            url = self.client.generate_presigned_url(
                'get_object',
                Params=params,
                ExpiresIn=expires_in
            )

            logger.info(f"✅ [{self.storage_type.upper()}-DOWNLOAD] Presigned URL generated successfully: {url[:100]}...")
            logger.info(f"🔍 [{self.storage_type.upper()}-DOWNLOAD] URL length: {len(url)}, contains bucket: {self.bucket_name in url}")

            return url

        except ClientError as e:
            logger.error(f"❌ [{self.storage_type.upper()}-DOWNLOAD] ClientError generating presigned URL: {e}")
            logger.error(f"❌ [{self.storage_type.upper()}-DOWNLOAD] Error code: {e.response.get('Error', {}).get('Code', 'Unknown')}")
            logger.error(f"❌ [{self.storage_type.upper()}-DOWNLOAD] Error message: {e.response.get('Error', {}).get('Message', 'Unknown')}")
            return None
        except Exception as e:
            logger.error(f"❌ [{self.storage_type.upper()}-DOWNLOAD] Unexpected error generating URL: {e}")
            import traceback
            logger.error(f"❌ [{self.storage_type.upper()}-DOWNLOAD] Traceback:\n{traceback.format_exc()}")
            return None

    def generate_presigned_upload_url(self, object_key: str, content_type: str = 'application/octet-stream', expires_in: int = 3600) -> Optional[str]:
        """Generate a presigned URL for uploading a file (PUT)"""
        if not self.client:
            logger.error("❌ B2 client not initialized")
            return None

        try:
            # Log params before generation
            params = {
                'Bucket': self.bucket_name,
                'Key': object_key,
                'ContentType': content_type
            }
            logger.info(f"🔧 Generating presigned URL with params: {params}")

            url = self.client.generate_presigned_url(
                'put_object',
                Params=params,
                ExpiresIn=expires_in
            )

            # Log URL details
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            query_params = parse_qs(parsed.query)
            logger.info(
                f"✅ Presigned URL generated:\n"
                f"   Host: {parsed.scheme}://{parsed.netloc}\n"
                f"   Path: {parsed.path}\n"
                f"   Query params keys: {list(query_params.keys())}\n"
                f"   Content-Type in URL: {'Content-Type' in url or 'content-type' in url.lower()}"
            )
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
        logger.info(f"🔍 [B2-EXISTS] Checking if file exists: bucket={self.bucket_name}, key={object_key}")

        if not self.client:
            logger.error("❌ [B2-EXISTS] B2 client not initialized")
            return False

        try:
            response = self.client.head_object(
                Bucket=self.bucket_name,
                Key=object_key
            )
            logger.info(f"✅ [B2-EXISTS] File exists: {object_key}, size={response.get('ContentLength', 0)} bytes")
            return True

        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.warning(f"⚠️ [B2-EXISTS] File not found or access error: {object_key}, error_code={error_code}")
            return False
        except Exception as e:
            logger.error(f"❌ [B2-EXISTS] Unexpected error checking file: {e}")
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

    def _get_b2_auth_token(self) -> Optional[tuple]:
        """Authenticate with B2 Native API and get authorization token"""
        # Clean credentials
        key_id = settings.B2_KEY_ID.split('#')[0] if settings.B2_KEY_ID else None
        app_key = settings.B2_APPLICATION_KEY.split('#')[0] if settings.B2_APPLICATION_KEY else None

        if not key_id or not app_key:
            return None

        # Encode credentials
        auth_string = f"{key_id}:{app_key}"
        auth_b64 = base64.b64encode(auth_string.encode()).decode()

        # Authenticate
        try:
            response = requests.get(
                'https://api.backblazeb2.com/b2api/v2/b2_authorize_account',
                headers={'Authorization': f'Basic {auth_b64}'}
            )

            if response.status_code != 200:
                logger.error(f"❌ B2 Auth failed: {response.text}")
                return None

            data = response.json()
            return data['authorizationToken'], data['apiUrl'], data['accountId']

        except Exception as e:
            logger.error(f"❌ B2 Auth exception: {e}")
            return None

    def _get_bucket_id(self, auth_token: str, api_url: str, account_id: str) -> Optional[str]:
        """Get bucket ID from bucket name"""
        try:
            response = requests.post(
                f"{api_url}/b2api/v2/b2_list_buckets",
                headers={'Authorization': auth_token},
                json={
                    'accountId': account_id,
                    'bucketName': self.bucket_name
                }
            )

            if response.status_code != 200:
                logger.error(f"❌ Failed to list buckets: {response.text}")
                return None

            data = response.json()
            buckets = data.get('buckets', [])

            if not buckets:
                logger.error(f"❌ Bucket '{self.bucket_name}' not found")
                return None

            return buckets[0]['bucketId']

        except Exception as e:
            logger.error(f"❌ Get bucket ID exception: {e}")
            return None

    def get_native_upload_url(self, object_key: str, content_type: str = 'application/octet-stream') -> Optional[Dict]:
        """
        Get upload URL for direct browser uploads (CORS-compatible)

        R2: Uses S3 presigned URLs (standard)
        B2: Uses B2 Native API (for CORS compatibility)

        Returns:
            dict with 'upload_url', 'authorization_token', 'object_key', 'content_type'
        """
        # R2: Use S3-compatible presigned URL
        if self.storage_type == 'r2':
            presigned_url = self.generate_presigned_upload_url(object_key, content_type, expires_in=3600)
            if not presigned_url:
                logger.error("❌ Failed to generate R2 presigned upload URL")
                return None

            logger.info(f"✅ R2 presigned upload URL generated for: {object_key}")

            return {
                'upload_url': presigned_url,
                'authorization_token': None,  # Not needed for S3 presigned URLs
                'object_key': object_key,
                'content_type': content_type
            }

        # B2: Use Native API
        # Step 1: Authenticate
        auth_result = self._get_b2_auth_token()
        if not auth_result:
            logger.error("❌ Failed to authenticate with B2")
            return None

        auth_token, api_url, account_id = auth_result

        # Step 2: Get bucket ID
        bucket_id = self._get_bucket_id(auth_token, api_url, account_id)
        if not bucket_id:
            logger.error("❌ Failed to get bucket ID")
            return None

        # Step 3: Get upload URL
        try:
            response = requests.post(
                f"{api_url}/b2api/v2/b2_get_upload_url",
                headers={'Authorization': auth_token},
                json={'bucketId': bucket_id}
            )

            if response.status_code != 200:
                logger.error(f"❌ Failed to get upload URL: {response.text}")
                return None

            data = response.json()

            logger.info(f"✅ B2 Native upload URL generated for: {object_key}")

            return {
                'upload_url': data['uploadUrl'],
                'authorization_token': data['authorizationToken'],
                'object_key': object_key,
                'content_type': content_type
            }

        except Exception as e:
            logger.error(f"❌ Get upload URL exception: {e}")
            return None

    def get_native_download_url(self, object_key: str, expires_in: int = 3600) -> Optional[str]:
        """
        Get download URL (R2: uses S3 presigned, B2: uses Native API)

        Returns:
            Presigned download URL or None if failed
        """
        # R2: Use S3 presigned URL (same as get_download_url)
        if self.storage_type == 'r2':
            logger.info(f"🔗 [R2-NATIVE-DOWNLOAD] Using S3 presigned URL for R2")
            return self.get_download_url(object_key, expires_in)

        # B2: Use B2 Native API
        logger.info(f"🔗 [B2-NATIVE-DOWNLOAD] Getting native download URL for: {object_key}")

        # Step 1: Authenticate
        auth_result = self._get_b2_auth_token()
        if not auth_result:
            logger.error("❌ [B2-NATIVE-DOWNLOAD] Failed to authenticate with B2")
            return None

        auth_token, api_url, account_id = auth_result

        # Step 2: Get bucket ID
        bucket_id = self._get_bucket_id(auth_token, api_url, account_id)
        if not bucket_id:
            logger.error("❌ [B2-NATIVE-DOWNLOAD] Failed to get bucket ID")
            return None

        # Step 3: Generate download authorization
        try:
            response = requests.post(
                f"{api_url}/b2api/v2/b2_get_download_authorization",
                headers={'Authorization': auth_token},
                json={
                    'bucketId': bucket_id,
                    'fileNamePrefix': object_key,
                    'validDurationInSeconds': expires_in
                }
            )

            if response.status_code != 200:
                logger.error(f"❌ [B2-NATIVE-DOWNLOAD] Failed to get download auth: {response.text}")
                return None

            data = response.json()
            download_auth_token = data['authorizationToken']

            # Step 4: Construct download URL with auth token
            # Format: https://f{bucket_id}.backblazeb2.com/file/{bucket_name}/{object_key}?Authorization={token}
            download_url = f"https://f{bucket_id[:3]}{bucket_id[3:]}.backblazeb2.com/file/{self.bucket_name}/{object_key}?Authorization={download_auth_token}"

            logger.info(f"✅ [B2-NATIVE-DOWNLOAD] Native download URL generated: {download_url[:100]}...")
            return download_url

        except Exception as e:
            logger.error(f"❌ [B2-NATIVE-DOWNLOAD] Exception: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
