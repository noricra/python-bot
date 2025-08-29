"""
Unit tests for application services.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, Mock

from app.application.use_cases import UserService, ProductService
from app.domain.entities import User, Product
from app.core.exceptions import ValidationError, NotFoundError


class TestUserService:
    """Test UserService."""
    
    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        return AsyncMock()
    
    @pytest.fixture
    def user_service(self, mock_user_repository):
        """Create UserService with mocked repository."""
        return UserService(mock_user_repository)
    
    @pytest.mark.asyncio
    async def test_register_user_new(self, user_service, mock_user_repository):
        """Test registering a new user."""
        # Mock repository to return None (user doesn't exist)
        mock_user_repository.get_by_id.return_value = None
        mock_user_repository.create.return_value = True
        
        user = await user_service.register_user(
            user_id=123,
            username="testuser",
            first_name="Test",
            language_code="fr"
        )
        
        assert user.user_id == 123
        assert user.username == "testuser"
        assert user.first_name == "Test"
        mock_user_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_register_user_existing(self, user_service, mock_user_repository):
        """Test registering an existing user."""
        existing_user = User(user_id=123, username="testuser", first_name="Test")
        mock_user_repository.get_by_id.return_value = existing_user
        
        user = await user_service.register_user(
            user_id=123,
            username="testuser",
            first_name="Test"
        )
        
        assert user == existing_user
        mock_user_repository.create.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_become_seller_success(self, user_service, mock_user_repository):
        """Test successful seller conversion."""
        user = User(user_id=123, username="testuser", first_name="Test")
        
        mock_user_repository.get_by_id.return_value = user
        mock_user_repository.is_solana_address_taken.return_value = False
        mock_user_repository.update.return_value = True
        
        result = await user_service.become_seller(
            user_id=123,
            seller_name="Test Seller",
            seller_bio="Test bio",
            solana_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
        )
        
        assert result.is_seller
        assert result.seller_name == "Test Seller"
        mock_user_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_become_seller_user_not_found(self, user_service, mock_user_repository):
        """Test seller conversion with non-existent user."""
        mock_user_repository.get_by_id.return_value = None
        
        with pytest.raises(NotFoundError):
            await user_service.become_seller(
                user_id=123,
                seller_name="Test Seller",
                seller_bio="Test bio",
                solana_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
            )
    
    @pytest.mark.asyncio
    async def test_become_seller_already_seller(self, user_service, mock_user_repository):
        """Test seller conversion when user is already a seller."""
        user = User(user_id=123, username="testuser", first_name="Test", is_seller=True)
        mock_user_repository.get_by_id.return_value = user
        
        with pytest.raises(ValidationError, match="already a seller"):
            await user_service.become_seller(
                user_id=123,
                seller_name="Test Seller",
                seller_bio="Test bio",
                solana_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
            )
    
    @pytest.mark.asyncio
    async def test_become_seller_address_taken(self, user_service, mock_user_repository):
        """Test seller conversion with taken Solana address."""
        user = User(user_id=123, username="testuser", first_name="Test")
        
        mock_user_repository.get_by_id.return_value = user
        mock_user_repository.is_solana_address_taken.return_value = True
        
        with pytest.raises(ValidationError, match="already registered"):
            await user_service.become_seller(
                user_id=123,
                seller_name="Test Seller",
                seller_bio="Test bio",
                solana_address="9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM"
            )


class TestProductService:
    """Test ProductService."""
    
    @pytest.fixture
    def mock_product_repository(self):
        """Create mock product repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_user_repository(self):
        """Create mock user repository."""
        return AsyncMock()
    
    @pytest.fixture
    def product_service(self, mock_product_repository, mock_user_repository):
        """Create ProductService with mocked repositories."""
        return ProductService(mock_product_repository, mock_user_repository)
    
    @pytest.mark.asyncio
    async def test_create_product_success(self, product_service, mock_product_repository, mock_user_repository):
        """Test successful product creation."""
        seller = User(user_id=123, username="seller", first_name="Seller", is_seller=True)
        
        mock_user_repository.get_by_id.return_value = seller
        mock_product_repository.exists.return_value = False
        mock_product_repository.create.return_value = True
        
        product = await product_service.create_product(
            seller_id=123,
            title="Test Product",
            description="Test description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        assert product.seller_user_id == 123
        assert product.title == "Test Product"
        assert product.price_eur == Decimal("99.99")
        mock_product_repository.create.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_create_product_seller_not_found(self, product_service, mock_user_repository):
        """Test product creation with non-existent seller."""
        mock_user_repository.get_by_id.return_value = None
        
        with pytest.raises(NotFoundError):
            await product_service.create_product(
                seller_id=123,
                title="Test Product",
                description="Test description",
                price_eur=Decimal("99.99"),
                category="test"
            )
    
    @pytest.mark.asyncio
    async def test_create_product_not_seller(self, product_service, mock_user_repository):
        """Test product creation with non-seller user."""
        user = User(user_id=123, username="user", first_name="User", is_seller=False)
        mock_user_repository.get_by_id.return_value = user
        
        with pytest.raises(ValidationError, match="not authorized"):
            await product_service.create_product(
                seller_id=123,
                title="Test Product",
                description="Test description",
                price_eur=Decimal("99.99"),
                category="test"
            )
    
    @pytest.mark.asyncio
    async def test_update_product_success(self, product_service, mock_product_repository):
        """Test successful product update."""
        product = Product(
            product_id="TBF-2024-ABCDEF",
            seller_user_id=123,
            title="Original Title",
            description="Original description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        mock_product_repository.get_by_id.return_value = product
        mock_product_repository.update.return_value = True
        
        updated_product = await product_service.update_product(
            product_id="TBF-2024-ABCDEF",
            seller_id=123,
            title="Updated Title",
            price_eur=Decimal("149.99")
        )
        
        assert updated_product.title == "Updated Title"
        assert updated_product.price_eur == Decimal("149.99")
        mock_product_repository.update.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_update_product_not_owner(self, product_service, mock_product_repository):
        """Test product update by non-owner."""
        product = Product(
            product_id="TBF-2024-ABCDEF",
            seller_user_id=123,
            title="Original Title",
            description="Original description",
            price_eur=Decimal("99.99"),
            category="test"
        )
        
        mock_product_repository.get_by_id.return_value = product
        
        with pytest.raises(ValidationError, match="don't own"):
            await product_service.update_product(
                product_id="TBF-2024-ABCDEF",
                seller_id=456,  # Different seller
                title="Updated Title"
            )