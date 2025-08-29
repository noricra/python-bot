"""
Unit tests for domain entities.
"""

import pytest
from decimal import Decimal
from datetime import datetime

from app.domain.entities import User, Product, Order
from app.domain.entities.product import ProductStatus
from app.domain.entities.order import OrderStatus, PaymentMethod
from app.core.exceptions import ValidationError


class TestUser:
    """Test User entity."""
    
    def test_user_creation(self):
        """Test basic user creation."""
        user = User(
            user_id=123,
            username="testuser",
            first_name="Test",
            language_code="fr"
        )
        
        assert user.user_id == 123
        assert user.username == "testuser"
        assert user.first_name == "Test"
        assert user.language_code == "fr"
        assert not user.is_seller
        assert user.display_name == "Test"
    
    def test_user_invalid_email(self):
        """Test user creation with invalid email."""
        with pytest.raises(ValidationError):
            User(
                user_id=123,
                email="invalid-email"
            )
    
    def test_user_invalid_solana_address(self):
        """Test user creation with invalid Solana address."""
        with pytest.raises(ValidationError):
            User(
                user_id=123,
                seller_solana_address="invalid-address"
            )
    
    def test_make_seller(self):
        """Test converting user to seller."""
        user = User(user_id=123, first_name="Test")
        
        user.make_seller(
            seller_name="Test Seller",
            seller_bio="Test bio",
            solana_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"  # Valid format
        )
        
        assert user.is_seller
        assert user.seller_name == "Test Seller"
        assert user.seller_bio == "Test bio"
    
    def test_display_name_priority(self):
        """Test display name priority logic."""
        user = User(
            user_id=123,
            username="testuser",
            first_name="Test",
            seller_name="Seller Name"
        )
        
        # Should prioritize seller_name when available
        user.is_seller = True
        assert user.display_name == "Seller Name"


class TestProduct:
    """Test Product entity."""
    
    def test_product_creation(self):
        """Test basic product creation."""
        product = Product(
            product_id="TBF-2024-ABCDEF",
            seller_user_id=123,
            title="Test Product",
            description="Test description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        assert product.product_id == "TBF-2024-ABCDEF"
        assert product.seller_user_id == 123
        assert product.title == "Test Product"
        assert product.price_eur == Decimal("99.99")
        assert product.status == ProductStatus.ACTIVE
        assert product.is_available
    
    def test_product_invalid_price(self):
        """Test product creation with invalid price."""
        with pytest.raises(ValidationError):
            Product(
                product_id="TBF-2024-ABCDEF",
                seller_user_id=123,
                title="Test Product",
                description="Test description",
                price_eur=Decimal("-10.00"),  # Negative price
                category="test"
            )
    
    def test_product_empty_title(self):
        """Test product creation with empty title."""
        with pytest.raises(ValidationError):
            Product(
                product_id="TBF-2024-ABCDEF",
                seller_user_id=123,
                title="",  # Empty title
                description="Test description",
                price_eur=Decimal("99.99"),
                category="test"
            )
    
    def test_product_status_changes(self):
        """Test product status changes."""
        product = Product(
            product_id="TBF-2024-ABCDEF",
            seller_user_id=123,
            title="Test Product",
            description="Test description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        # Test deactivation
        product.deactivate()
        assert product.status == ProductStatus.INACTIVE
        assert not product.is_available
        
        # Test reactivation
        product.activate()
        assert product.status == ProductStatus.ACTIVE
        assert product.is_available
        
        # Test suspension
        product.suspend()
        assert product.status == ProductStatus.SUSPENDED
        assert not product.is_available
    
    def test_record_sale(self):
        """Test recording a sale."""
        product = Product(
            product_id="TBF-2024-ABCDEF",
            seller_user_id=123,
            title="Test Product",
            description="Test description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        initial_sales = product.sales_count
        product.record_sale()
        assert product.sales_count == initial_sales + 1


class TestOrder:
    """Test Order entity."""
    
    def test_order_creation(self):
        """Test basic order creation."""
        order = Order(
            order_id="ORD_123456789",
            buyer_user_id=123,
            seller_user_id=456,
            product_id="TBF-2024-ABCDEF",
            amount_eur=Decimal("99.99"),
            payment_method=PaymentMethod.WALLET
        )
        
        assert order.order_id == "ORD_123456789"
        assert order.buyer_user_id == 123
        assert order.seller_user_id == 456
        assert order.amount_eur == Decimal("99.99")
        assert order.status == OrderStatus.PENDING
        assert not order.is_paid
        assert not order.can_download
    
    def test_order_invalid_amount(self):
        """Test order creation with invalid amount."""
        with pytest.raises(ValidationError):
            Order(
                order_id="ORD_123456789",
                buyer_user_id=123,
                seller_user_id=456,
                product_id="TBF-2024-ABCDEF",
                amount_eur=Decimal("-10.00"),  # Negative amount
                payment_method=PaymentMethod.WALLET
            )
    
    def test_order_payment_flow(self):
        """Test order payment flow."""
        order = Order(
            order_id="ORD_123456789",
            buyer_user_id=123,
            seller_user_id=456,
            product_id="TBF-2024-ABCDEF",
            amount_eur=Decimal("99.99"),
            payment_method=PaymentMethod.WALLET
        )
        
        # Mark as paid
        order.mark_as_paid()
        assert order.status == OrderStatus.PAID
        assert order.is_paid
        assert order.can_download
        assert order.payment_date is not None
        
        # Complete order
        order.mark_as_completed()
        assert order.status == OrderStatus.COMPLETED
        assert order.is_completed
        assert order.completion_date is not None
    
    def test_order_cancel(self):
        """Test order cancellation."""
        order = Order(
            order_id="ORD_123456789",
            buyer_user_id=123,
            seller_user_id=456,
            product_id="TBF-2024-ABCDEF",
            amount_eur=Decimal("99.99"),
            payment_method=PaymentMethod.WALLET
        )
        
        # Can cancel pending order
        order.cancel()
        assert order.status == OrderStatus.CANCELLED
        
        # Cannot cancel paid order
        order.status = OrderStatus.PAID
        with pytest.raises(ValidationError):
            order.cancel()
    
    def test_commission_calculation(self):
        """Test commission calculation."""
        order = Order(
            order_id="ORD_123456789",
            buyer_user_id=123,
            seller_user_id=456,
            product_id="TBF-2024-ABCDEF",
            amount_eur=Decimal("100.00"),
            payment_method=PaymentMethod.WALLET,
            referrer_user_id=789
        )
        
        platform_rate = Decimal("0.05")  # 5%
        referrer_rate = Decimal("0.10")  # 10%
        
        order.calculate_commissions(platform_rate, referrer_rate)
        
        assert order.platform_commission_eur == Decimal("5.00")
        assert order.referrer_commission_eur == Decimal("10.00")
        assert order.seller_payout_eur == Decimal("85.00")
    
    def test_record_download(self):
        """Test recording downloads."""
        order = Order(
            order_id="ORD_123456789",
            buyer_user_id=123,
            seller_user_id=456,
            product_id="TBF-2024-ABCDEF",
            amount_eur=Decimal("99.99"),
            payment_method=PaymentMethod.WALLET
        )
        
        # Cannot download unpaid order
        with pytest.raises(ValidationError):
            order.record_download()
        
        # Can download paid order
        order.mark_as_paid()
        initial_downloads = order.download_count
        order.record_download()
        assert order.download_count == initial_downloads + 1