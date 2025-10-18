"""
Validation utilities for the marketplace bot
"""
import re
import base58


def validate_email(email: str) -> bool:
    """Validate an email address"""
    if not email:
        return False

    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_solana_address(address: str) -> bool:
    """Validate a Solana address"""
    try:
        # Basic format check
        if len(address) < 32 or len(address) > 44:
            return False

        # Valid Base58 characters
        base58.b58decode(address)
        return True
    except Exception:
        return False