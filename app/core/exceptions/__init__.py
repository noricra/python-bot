"""
Custom exceptions for the marketplace application.
"""

class MarketplaceException(Exception):
    """Base exception for marketplace domain."""
    pass


class ValidationError(MarketplaceException):
    """Raised when validation fails."""
    pass


class NotFoundError(MarketplaceException):
    """Raised when a resource is not found."""
    pass


class UnauthorizedError(MarketplaceException):
    """Raised when user is not authorized."""
    pass


class PaymentError(MarketplaceException):
    """Raised when payment processing fails."""
    pass


class InsufficientFundsError(PaymentError):
    """Raised when user has insufficient funds."""
    pass


class InvalidAddressError(ValidationError):
    """Raised when crypto address is invalid."""
    pass