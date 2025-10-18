"""
Critical Unit Tests - Essential service and business logic tests
"""
import unittest
import tempfile
import os
from unittest.mock import Mock, patch

from app.services.product_service import ProductService
from app.services.seller_service import SellerService
from app.services.payment_processing_service import PaymentProcessingService
from app.core.database_adapter import SQLiteAdapter, DatabaseFactory
from app.core.monitoring import MetricsCollector, PerformanceMonitor


class TestProductService(unittest.TestCase):
    """Test ProductService business logic"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.service = ProductService(db_path=self.temp_db.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_validate_product_id_format(self):
        """Test product ID format validation"""
        # Valid formats
        self.assertTrue(self.service.validate_product_id_format("TBF-2501-ABC123"))
        self.assertTrue(self.service.validate_product_id_format("TBF-2412-XYZ789"))

        # Invalid formats
        self.assertFalse(self.service.validate_product_id_format(""))
        self.assertFalse(self.service.validate_product_id_format("TBF-25-ABC123"))  # Year too short
        self.assertFalse(self.service.validate_product_id_format("TBF-2501-AB12"))   # Code too short
        self.assertFalse(self.service.validate_product_id_format("ABC-2501-ABC123")) # Wrong prefix
        self.assertFalse(self.service.validate_product_id_format("TBF-2501-ABC12O")) # Contains O (forbidden)

    @patch('app.services.product_service.get_sqlite_connection')
    def test_get_product_with_seller_info(self, mock_conn):
        """Test product retrieval with seller information"""
        # Mock database response
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {
            'product_id': 'TBF-2501-ABC123',
            'title': 'Test Product',
            'seller_name': 'Test Seller'
        }
        mock_conn.return_value.cursor.return_value = mock_cursor

        result = self.service.get_product_with_seller_info('TBF-2501-ABC123')

        self.assertIsNotNone(result)
        self.assertEqual(result['product_id'], 'TBF-2501-ABC123')
        self.assertEqual(result['title'], 'Test Product')
        mock_cursor.execute.assert_called_once()


class TestSellerService(unittest.TestCase):
    """Test SellerService business logic"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.service = SellerService(db_path=self.temp_db.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_password_hashing(self):
        """Test password hashing functionality"""
        from app.services.seller_service import generate_salt, hash_password

        # Test salt generation
        salt = generate_salt()
        self.assertEqual(len(salt), 32)  # 16 bytes = 32 hex chars

        # Test password hashing
        password = "test_password_123"
        hashed = hash_password(password, salt)
        self.assertEqual(len(hashed), 64)  # SHA256 = 64 hex chars

        # Same password + salt should produce same hash
        hashed2 = hash_password(password, salt)
        self.assertEqual(hashed, hashed2)

        # Different salt should produce different hash
        salt2 = generate_salt()
        hashed3 = hash_password(password, salt2)
        self.assertNotEqual(hashed, hashed3)

    def test_authenticate_seller_invalid_user(self):
        """Test seller authentication with invalid user"""
        result = self.service.authenticate_seller(999999)
        self.assertFalse(result)


class TestPaymentProcessingService(unittest.TestCase):
    """Test PaymentProcessingService business logic"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()
        self.service = PaymentProcessingService(db_path=self.temp_db.name)

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_payment_status_invalid_order(self):
        """Test payment status for non-existent order"""
        result = self.service.get_payment_status('invalid_order_id')
        self.assertIsNone(result)


class TestDatabaseAdapter(unittest.TestCase):
    """Test database adapter functionality"""

    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.temp_db.close()

    def tearDown(self):
        os.unlink(self.temp_db.name)

    def test_sqlite_adapter_creation(self):
        """Test SQLite adapter creation"""
        adapter = SQLiteAdapter(self.temp_db.name)
        self.assertEqual(adapter.db_path, self.temp_db.name)
        self.assertIsNone(adapter.connection)

    def test_database_factory(self):
        """Test database factory"""
        adapter = DatabaseFactory.create_adapter('sqlite', db_path=self.temp_db.name)
        self.assertIsInstance(adapter, SQLiteAdapter)

        with self.assertRaises(ValueError):
            DatabaseFactory.create_adapter('invalid_type')

    def test_sqlite_connection(self):
        """Test SQLite connection and basic operations"""
        adapter = SQLiteAdapter(self.temp_db.name)
        conn = adapter.connect()
        self.assertIsNotNone(conn)

        # Test basic query
        cursor = adapter.execute('CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT)')
        self.assertIsNotNone(cursor)

        adapter.close()
        self.assertIsNone(adapter.connection)


class TestMonitoring(unittest.TestCase):
    """Test monitoring and metrics functionality"""

    def test_metrics_collector(self):
        """Test metrics collection"""
        collector = MetricsCollector(max_events=10)

        # Test counter
        collector.increment('test_counter', 5)
        self.assertEqual(collector.counters['test_counter'], 5)

        collector.increment('test_counter', 3)
        self.assertEqual(collector.counters['test_counter'], 8)

        # Test gauge
        collector.gauge('test_gauge', 42.5)
        self.assertEqual(collector.gauges['test_gauge'], 42.5)

        # Test timer
        collector.timer('test_timer', 1.234)
        self.assertEqual(len(collector.timers['test_timer']), 1)
        self.assertEqual(collector.timers['test_timer'][0], 1.234)

        # Test summary
        summary = collector.get_summary()
        self.assertIn('counters', summary)
        self.assertIn('gauges', summary)
        self.assertIn('timers', summary)
        self.assertEqual(summary['counters']['test_counter'], 8)
        self.assertEqual(summary['gauges']['test_gauge'], 42.5)

    def test_performance_monitor(self):
        """Test performance monitoring"""
        collector = MetricsCollector()
        monitor = PerformanceMonitor(collector)

        # Test timer context
        with monitor.measure_time('test_operation'):
            pass  # Simulate work

        # Check that metric was recorded
        self.assertIn('test_operation', collector.timers)
        self.assertEqual(len(collector.timers['test_operation']), 1)

        # Test function decorator
        @monitor.measure_function('test_function')
        def test_func():
            return "test_result"

        result = test_func()
        self.assertEqual(result, "test_result")
        self.assertIn('test_function', collector.timers)


if __name__ == '__main__':
    unittest.main()