"""
Application interfaces (ports) for dependency inversion.
"""

from .user_repository_interface import UserRepositoryInterface
from .product_repository_interface import ProductRepositoryInterface
from .order_repository_interface import OrderRepositoryInterface
from .wallet_repository_interface import WalletRepositoryInterface
from .payout_repository_interface import PayoutRepositoryInterface

__all__ = [
    "UserRepositoryInterface",
    "ProductRepositoryInterface", 
    "OrderRepositoryInterface",
    "WalletRepositoryInterface",
    "PayoutRepositoryInterface"
]