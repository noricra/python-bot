"""
File Validation Module - Security enforcement for file uploads
Implements whitelist/blacklist approach to prevent malware distribution
"""
import os
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# CRITICAL: Blocked extensions - Executable and dangerous files
BLOCKED_EXTENSIONS = {
    # Windows executables
    '.exe', '.bat', '.cmd', '.com', '.msi', '.scr', '.vbs', '.ps1',
    '.dll', '.sys', '.drv', '.pif', '.application', '.gadget', '.msp',
    '.cpl', '.inf', '.ins', '.isp', '.job', '.jse', '.lnk', '.msc',
    '.msh', '.msh1', '.msh2', '.mshxml', '.msh1xml', '.msh2xml',
    '.ps1xml', '.ps2', '.ps2xml', '.psc1', '.psc2', '.reg', '.rgs',
    '.sct', '.shb', '.shs', '.u3p', '.vbe', '.vbscript', '.ws', '.wsf',
    '.wsh',

    # Unix/Linux executables
    '.sh', '.bash', '.zsh', '.fish', '.csh', '.tcsh', '.ksh',
    '.run', '.bin', '.command',

    # Java/Android
    '.jar', '.class', '.apk', '.dex',

    # macOS
    '.dmg', '.pkg', '.app',

    # Linux packages
    '.deb', '.rpm', '.snap',

    # Script files with execution risk
    '.vb', '.vbe', '.wsc', '.wsf', '.wsh',

    # Other dangerous
    '.hta', '.cpl', '.msc', '.jar',
}

# Allowed extensions - Safe file types for marketplace
ALLOWED_EXTENSIONS = {
    # Documents & eBooks
    '.pdf', '.epub', '.mobi', '.azw', '.azw3',
    '.doc', '.docx', '.odt', '.rtf', '.txt',
    '.xls', '.xlsx', '.ods', '.csv',
    '.ppt', '.pptx', '.odp',

    # Videos
    '.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm',
    '.m4v', '.mpg', '.mpeg', '.3gp', '.ogv',

    # Audio
    '.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma',
    '.opus', '.ape', '.alac',

    # Images
    '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg',
    '.ico', '.tiff', '.tif', '.heic', '.heif',

    # Archives (WARNING: contents not scanned)
    '.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz',

    # Creative & Design
    '.psd', '.ai', '.sketch', '.fig', '.xd', '.afdesign',
    '.blend', '.fbx', '.obj', '.stl', '.3ds', '.dae',
    '.indd', '.eps', '.cdr',

    # Code (source files only - NOT executables)
    '.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss',
    '.json', '.xml', '.yaml', '.yml', '.md', '.markdown',
    '.c', '.cpp', '.h', '.hpp', '.java', '.go', '.rs', '.php',
    '.rb', '.swift', '.kt', '.dart', '.lua', '.r', '.sql',

    # Fonts
    '.ttf', '.otf', '.woff', '.woff2', '.eot',

    # Other safe formats
    '.ics', '.vcf', '.kml', '.gpx', '.kmz',
}


def validate_file_extension(filename: str) -> Tuple[bool, str]:
    """
    Validate file extension against whitelist and blacklist.

    Args:
        filename: Name of the file to validate

    Returns:
        Tuple of (is_valid: bool, error_message: str)
        - (True, "") if valid
        - (False, "error message") if invalid

    Security:
        - Blocks executable files (exe, bat, sh, dll, etc.)
        - Blocks package files (msi, deb, rpm, dmg, etc.)
        - Only allows whitelisted extensions
        - Case-insensitive checking
    """
    if not filename:
        return False, "Nom de fichier vide"

    # Extract extension (case-insensitive)
    _, ext = os.path.splitext(filename.lower())

    if not ext:
        return False, "Fichier sans extension non autorisé"

    # CRITICAL: Check blacklist first (security priority)
    if ext in BLOCKED_EXTENSIONS:
        logger.warning(f"🚫 BLOCKED: Attempted upload of dangerous file type: {ext} (filename: {filename})")
        return False, f"Type de fichier {ext} bloqué pour raisons de sécurité. Les fichiers exécutables ne sont pas autorisés."

    # Check whitelist
    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"⚠️ REJECTED: Unsupported file type: {ext} (filename: {filename})")
        return False, f"Type de fichier {ext} non supporté. Consultez la FAQ pour voir les formats acceptés."

    logger.info(f"✅ VALIDATED: File extension {ext} is allowed (filename: {filename})")
    return True, ""


def get_file_category(filename: str) -> str:
    """
    Get the category of a file based on its extension.

    Args:
        filename: Name of the file

    Returns:
        Category name: "document", "video", "audio", "image", "archive", "code", "design", "other"
    """
    _, ext = os.path.splitext(filename.lower())

    if ext in {'.pdf', '.epub', '.mobi', '.azw', '.azw3', '.doc', '.docx', '.odt', '.rtf', '.txt',
               '.xls', '.xlsx', '.ods', '.csv', '.ppt', '.pptx', '.odp'}:
        return "document"
    elif ext in {'.mp4', '.avi', '.mov', '.wmv', '.flv', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg',
                 '.3gp', '.ogv'}:
        return "video"
    elif ext in {'.mp3', '.wav', '.flac', '.aac', '.ogg', '.m4a', '.wma', '.opus', '.ape', '.alac'}:
        return "audio"
    elif ext in {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico', '.tiff', '.tif',
                 '.heic', '.heif'}:
        return "image"
    elif ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}:
        return "archive"
    elif ext in {'.py', '.js', '.ts', '.jsx', '.tsx', '.html', '.css', '.scss', '.json', '.xml',
                 '.yaml', '.yml', '.md', '.markdown', '.c', '.cpp', '.h', '.hpp', '.java', '.go',
                 '.rs', '.php', '.rb', '.swift', '.kt', '.dart', '.lua', '.r', '.sql'}:
        return "code"
    elif ext in {'.psd', '.ai', '.sketch', '.fig', '.xd', '.afdesign', '.blend', '.fbx', '.obj',
                 '.stl', '.3ds', '.dae', '.indd', '.eps', '.cdr'}:
        return "design"
    else:
        return "other"


def is_archive_file(filename: str) -> bool:
    """
    Check if file is an archive format.

    WARNING: Archives can contain dangerous files. This function only checks
    the extension, not the contents. Consider implementing archive scanning.

    Args:
        filename: Name of the file

    Returns:
        True if archive format, False otherwise
    """
    _, ext = os.path.splitext(filename.lower())
    return ext in {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'}


def get_allowed_extensions_list() -> list:
    """
    Get list of allowed extensions for display.

    Returns:
        Sorted list of allowed extensions
    """
    return sorted(list(ALLOWED_EXTENSIONS))


def get_blocked_extensions_list() -> list:
    """
    Get list of blocked extensions for display.

    Returns:
        Sorted list of blocked extensions
    """
    return sorted(list(BLOCKED_EXTENSIONS))
