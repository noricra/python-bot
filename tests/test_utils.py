"""
Unit tests for utility functions.
"""

import pytest
from app.core.utils import (
    validate_email,
    validate_solana_address,
    sanitize_filename,
    escape_markdown,
    generate_product_id,
    infer_network_from_address
)


class TestValidationUtils:
    """Test validation utility functions."""
    
    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "test@example.com",
            "user.name@domain.co.uk",
            "admin+test@company.org",
            "12345@numbers.com"
        ]
        
        for email in valid_emails:
            assert validate_email(email), f"Should validate: {email}"
    
    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = [
            "invalid",
            "@domain.com",
            "user@",
            "user@domain",
            "user.domain.com",
            "",
            "user@domain..com"
        ]
        
        for email in invalid_emails:
            assert not validate_email(email), f"Should not validate: {email}"
    
    def test_validate_solana_address_valid(self):
        """Test Solana address validation with valid addresses."""
        valid_addresses = [
            "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
            "11111111111111111111111111111112",  # System program
            "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"  # USDC mint
        ]
        
        for address in valid_addresses:
            assert validate_solana_address(address), f"Should validate: {address}"
    
    def test_validate_solana_address_invalid(self):
        """Test Solana address validation with invalid addresses."""
        invalid_addresses = [
            "",
            "invalid",
            "1234567890",
            "0x" + "a" * 40,  # Ethereum-style address
            "a" * 100,  # Too long
            "invalid-solana-address-format"
        ]
        
        for address in invalid_addresses:
            assert not validate_solana_address(address), f"Should not validate: {address}"


class TestStringUtils:
    """Test string utility functions."""
    
    def test_sanitize_filename_normal(self):
        """Test filename sanitization with normal names."""
        test_cases = [
            ("My Document.pdf", "My Document.pdf"),
            ("test_file-v1.txt", "test_file-v1.txt"),
            ("Simple123", "Simple123")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Expected {expected}, got {result}"
    
    def test_sanitize_filename_special_chars(self):
        """Test filename sanitization with special characters."""
        test_cases = [
            ("file/with\\slashes.txt", "filewithslashes.txt"),
            ("file@#$%^&*().pdf", "file.pdf"),
            ("файл.txt", ".txt"),  # Cyrillic characters
            ("", "untitled")
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Input: {input_name}, Expected: {expected}, Got: {result}"
    
    def test_sanitize_filename_length_limit(self):
        """Test filename length limitation."""
        long_name = "a" * 100 + ".txt"
        result = sanitize_filename(long_name)
        assert len(result) <= 50
        assert result.endswith(".txt")
    
    def test_escape_markdown_basic(self):
        """Test basic markdown escaping."""
        test_cases = [
            ("Normal text", "Normal text"),
            ("Text with *bold*", "Text with \\*bold\\*"),
            ("Text with _italic_", "Text with \\_italic\\_"),
            ("Text with [link](url)", "Text with \\[link\\]\\(url\\)"),
            ("Text with `code`", "Text with \\`code\\`")
        ]
        
        for input_text, expected in test_cases:
            result = escape_markdown(input_text)
            assert result == expected, f"Input: {input_text}, Expected: {expected}, Got: {result}"
    
    def test_escape_markdown_special_chars(self):
        """Test escaping of all special markdown characters."""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        
        for char in special_chars:
            input_text = f"Text {char} more text"
            result = escape_markdown(input_text)
            expected = f"Text \\{char} more text"
            assert result == expected, f"Failed to escape: {char}"


class TestGeneratorUtils:
    """Test generator utility functions."""
    
    def test_generate_product_id_format(self):
        """Test product ID generation format."""
        product_id = generate_product_id()
        
        # Should match format TBF-YYMM-XXXXXX
        parts = product_id.split('-')
        assert len(parts) == 3
        assert parts[0] == "TBF"
        assert len(parts[1]) == 4  # YYMM
        assert len(parts[2]) == 6  # Random part
        assert parts[1].isdigit()
        assert parts[2].isalnum()
    
    def test_generate_product_id_uniqueness(self):
        """Test that product IDs are unique."""
        ids = [generate_product_id() for _ in range(100)]
        assert len(set(ids)) == 100, "Product IDs should be unique"
    
    def test_infer_network_from_address(self):
        """Test network inference from address format."""
        test_cases = [
            ("1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa", "bitcoin"),  # Bitcoin P2PKH
            ("3J98t1WpEZ73CNmQviecrnyiWrnqRhWNLy", "bitcoin"),  # Bitcoin P2SH
            ("bc1qw508d6qejxtdg4y5r3zarvary0c5xw7kv8f3t4", "bitcoin"),  # Bitcoin Bech32
            ("0x742d35Cc6634C0532925a3b8D3c8C1C2f65ff", "ethereum"),  # Ethereum
            ("9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM", "solana"),  # Solana
            ("invalid-address", "unknown"),
            ("", "unknown")
        ]
        
        for address, expected_network in test_cases:
            result = infer_network_from_address(address)
            assert result == expected_network, f"Address: {address}, Expected: {expected_network}, Got: {result}"