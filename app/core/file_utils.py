"""File utilities for handling uploads and file operations"""

import os
import logging
from typing import Optional
from app.core.settings import settings
from app.services.b2_storage_service import B2StorageService

logger = logging.getLogger(__name__)

# Initialize B2 service
b2_service = B2StorageService()

async def save_uploaded_file(file_info, filename: str) -> Optional[str]:
    """
    Save an uploaded file from Telegram

    Args:
        file_info: Telegram file info object
        filename: Original filename

    Returns:
        str: Saved filename/path or None if failed
    """
    try:
        # Ensure uploads directory exists
        os.makedirs(settings.UPLOADS_DIR, exist_ok=True)

        # Sanitize filename
        safe_filename = sanitize_filename(filename)

        # Create unique filename to avoid conflicts
        base_name, ext = os.path.splitext(safe_filename)
        counter = 1
        final_filename = safe_filename

        while os.path.exists(os.path.join(settings.UPLOADS_DIR, final_filename)):
            final_filename = f"{base_name}_{counter}{ext}"
            counter += 1

        # Full path for saving
        file_path = os.path.join(settings.UPLOADS_DIR, final_filename)

        # Download and save file using async method
        await file_info.download_to_drive(file_path)

        logger.info(f"File saved: {final_filename}")
        return final_filename

    except Exception as e:
        logger.error(f"Error saving file {filename}: {e}")
        return None

def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage

    Args:
        filename: Original filename

    Returns:
        str: Sanitized filename
    """
    if not filename:
        return "unnamed_file"

    # Remove path separators and other dangerous characters
    filename = os.path.basename(filename)

    # Keep only allowed characters
    allowed_chars = settings.ALLOWED_FILENAME_CHARS
    sanitized = ''.join(c for c in filename if c in allowed_chars)

    # Ensure not empty and not too long
    if not sanitized:
        sanitized = "unnamed_file"

    if len(sanitized) > 100:
        name, ext = os.path.splitext(sanitized)
        sanitized = name[:100-len(ext)] + ext

    return sanitized

def get_product_file_path(relative_path: str) -> str:
    """
    Get the full path for a product file

    Args:
        relative_path: Relative path stored in database

    Returns:
        str: Full absolute path to the file
    """
    if not relative_path:
        return ""

    # If already absolute path, return as is
    if os.path.isabs(relative_path):
        return relative_path

    # Otherwise, join with uploads directory
    return os.path.join(settings.UPLOADS_DIR, relative_path)


# ============================================================================
# BACKBLAZE B2 FUNCTIONS
# ============================================================================

async def upload_product_file_to_b2(local_file_path: str, product_id: str) -> Optional[str]:
    """
    Upload a product file to Backblaze B2 and delete local copy

    Args:
        local_file_path: Path to local file
        product_id: Product ID for organizing in B2

    Returns:
        str: B2 URL of uploaded file, or None if failed
    """
    try:
        # Generate B2 key
        filename = os.path.basename(local_file_path)
        object_key = f"products/{product_id}/{filename}"

        # Upload to B2
        b2_url = b2_service.upload_file(local_file_path, object_key)

        if b2_url:
            # Delete local file after successful upload
            try:
                os.remove(local_file_path)
                logger.info(f"✅ Local file deleted after B2 upload: {local_file_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not delete local file: {e}")

        return b2_url

    except Exception as e:
        logger.error(f"❌ Failed to upload file to B2: {e}")
        return None


async def download_product_file_from_b2(b2_url: str, product_id: str) -> Optional[str]:
    """
    Download a product file from B2 temporarily (for delivery to buyer)

    Args:
        b2_url: B2 URL of file
        product_id: Product ID

    Returns:
        str: Local path to downloaded file, or None if failed
    """
    try:
        # Extract object key from URL
        # URL format: https://s3.us-west-004.backblazeb2.com/bucket-name/products/...
        parts = b2_url.split(f"/{settings.B2_BUCKET_NAME}/")
        if len(parts) < 2:
            logger.error(f"❌ Invalid B2 URL format: {b2_url}")
            return None

        object_key = parts[1]

        # Create temp directory
        temp_dir = os.path.join(settings.UPLOADS_DIR, "temp", product_id)
        os.makedirs(temp_dir, exist_ok=True)

        # Download to temp location
        filename = os.path.basename(object_key)
        local_path = os.path.join(temp_dir, filename)

        if b2_service.download_file(object_key, local_path):
            logger.info(f"✅ File downloaded from B2 to: {local_path}")
            return local_path
        else:
            return None

    except Exception as e:
        logger.error(f"❌ Failed to download file from B2: {e}")
        return None


def get_b2_presigned_url(b2_url: str, expires_in: int = 3600) -> Optional[str]:
    """
    Get a presigned URL for direct download from B2

    Args:
        b2_url: B2 URL of file
        expires_in: Expiration time in seconds (default 1 hour)

    Returns:
        str: Presigned URL, or None if failed
    """
    try:
        # Extract object key from URL
        parts = b2_url.split(f"/{settings.B2_BUCKET_NAME}/")
        if len(parts) < 2:
            logger.error(f"❌ Invalid B2 URL format: {b2_url}")
            return None

        object_key = parts[1]

        # Generate presigned URL
        presigned_url = b2_service.get_download_url(object_key, expires_in)
        return presigned_url

    except Exception as e:
        logger.error(f"❌ Failed to generate presigned URL: {e}")
        return None


def delete_product_file_from_b2(b2_url: str) -> bool:
    """
    Delete a product file from B2

    Args:
        b2_url: B2 URL of file

    Returns:
        bool: True if successful
    """
    try:
        # Extract object key from URL
        parts = b2_url.split(f"/{settings.B2_BUCKET_NAME}/")
        if len(parts) < 2:
            logger.error(f"❌ Invalid B2 URL format: {b2_url}")
            return False

        object_key = parts[1]

        # Delete from B2
        return b2_service.delete_file(object_key)

    except Exception as e:
        logger.error(f"❌ Failed to delete file from B2: {e}")
        return False


def get_b2_file_size(b2_url: str) -> Optional[float]:
    """
    Get file size in MB from B2

    Args:
        b2_url: B2 URL of file

    Returns:
        float: File size in MB, or None if failed
    """
    try:
        # Extract object key from URL
        parts = b2_url.split(f"/{settings.B2_BUCKET_NAME}/")
        if len(parts) < 2:
            return None

        object_key = parts[1]

        # Get file size in bytes
        size_bytes = b2_service.get_file_size(object_key)
        if size_bytes is not None:
            # Convert to MB
            return size_bytes / (1024 * 1024)
        return None

    except Exception as e:
        logger.error(f"❌ Failed to get file size from B2: {e}")
        return None