import os
import time
import re
import requests

try:
    import base58  # type: ignore
except Exception:  # pragma: no cover
    base58 = None


def validate_email(email: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email or '') is not None


def validate_solana_address(address: str) -> bool:
    try:
        if not address or len(address) < 32 or len(address) > 44:
            return False
        if base58 is None:
            return False
        base58.b58decode(address)
        return True
    except Exception:
        return False


def get_solana_balance_display(address: str) -> float:
    try:
        response = requests.post(
            "https://api.mainnet-beta.solana.com",
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "getBalance",
                "params": [address]
            },
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            balance_lamports = data.get('result', {}).get('value', 0)
            return balance_lamports / 1_000_000_000
        return 0.0
    except Exception:
        return 0.0


def escape_markdown(text: str) -> str:
    if text is None:
        return ''
    replacements = {
        '_': r'\_', '*': r'\*', '[': r'\[', ']': r'\]', '(': r'\(', ')': r'\)',
        '~': r'\~', '`': r'\`', '>': r'\>', '#': r'\#', '+': r'\+', '-': r'\-',
        '=': r'\=', '|': r'\|', '{': r'\{', '}': r'\}', '.': r'\.', '!': r'\!'
    }
    return ''.join(replacements.get(ch, ch) for ch in text)


def sanitize_filename(name: str) -> str:
    safe_name = os.path.basename(name or '')
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
    sanitized = ''.join(ch if ch in allowed else '_' for ch in safe_name)
    return sanitized or f"file_{int(time.time())}"

