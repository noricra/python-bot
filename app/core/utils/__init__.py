"""
Utility functions for the marketplace application.
"""

import re
import base58
import hashlib
import secrets
from typing import Optional


def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_solana_address(address: str) -> bool:
    """Validate a Solana address."""
    try:
        if len(address) < 32 or len(address) > 44:
            return False
        base58.b58decode(address)
        return True
    except Exception:
        return False


def sanitize_filename(name: str) -> str:
    """Sanitize filename for safe storage."""
    if not name:
        return "untitled"
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    return ''.join(c for c in name if c in allowed)[:50]


def escape_markdown(text: str) -> str:
    """Escape markdown special characters."""
    chars_to_escape = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in chars_to_escape:
        text = text.replace(char, f'\\{char}')
    return text


def generate_product_id() -> str:
    """Generate a unique product ID in format TBF-YYMM-XXXXXX."""
    from datetime import datetime
    
    now = datetime.now()
    year_month = f"{now.year % 100:02d}{now.month:02d}"
    
    # Generate 6 random characters (no I/O/0/1 for clarity)
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    random_part = ''.join(secrets.choice(chars) for _ in range(6))
    
    return f"TBF-{year_month}-{random_part}"


def generate_secure_hash(data: str) -> str:
    """Generate a secure hash for sensitive data."""
    salt = secrets.token_hex(16)
    return hashlib.pbkdf2_hmac('sha256', data.encode(), salt.encode(), 100000).hex()


def infer_network_from_address(address: str) -> str:
    """Infer cryptocurrency network from address format."""
    if not address:
        return "unknown"
    
    # Bitcoin
    if address.startswith(('1', '3', 'bc1')):
        return "bitcoin"
    
    # Ethereum
    if address.startswith('0x') and len(address) == 42:
        return "ethereum"
    
    # Solana
    if validate_solana_address(address):
        return "solana"
    
    return "unknown"