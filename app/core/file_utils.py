"""File utilities for handling uploads and file operations"""

import os
import logging
from typing import Optional
from app.core.settings import settings

logger = logging.getLogger(__name__)

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