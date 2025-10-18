#!/usr/bin/env python3
"""
Script de test intégré pour TechBot Marketplace
Tests complets des workflows : vendeur, acheteur, admin, support
"""

import os
import sys
import sqlite3
import tempfile
import shutil
import asyncio
import logging
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Imports du projet
from app.domain.repositories.user_repo import UserRepository
from app.domain.repositories.product_repo import ProductRepository
from app.domain.repositories.order_repo import OrderRepository
from app.domain.repositories.payout_repo import PayoutRepository
from app.domain.repositories.support_repo import SupportRepository
from app.services.seller_service import SellerService
from app.services.product_service import ProductService
from app.services.payment_service import PaymentService
from app.services.payout_service import PayoutService
from app.services.support_service import SupportService
from app.core.database_init import DatabaseInitService
from app.core.email_service import EmailService
from app.core.state_manager import StateManager
from app.core.user_utils import get_user_language, format_user_display_name
from app.integrations.telegram.handlers.sell_handlers import SellHandlers
from app.integrations.telegram.handlers.buy_handlers import BuyHandlers
from app.integrations.telegram.handlers.admin_handlers import AdminHandlers
from app.integrations.telegram.handlers.support_handlers import SupportHandlers
from app.integrations.telegram.handlers.auth_handlers import AuthHandlers
from app.integrations.telegram.handlers.core_handlers import CoreHandlers

# Configuration des logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TestWorkflows:
    """Classe principale pour tester tous les workflows du marketplace"""

    def __init__(self):
        """Initialise l'environnement de test"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_marketplace.db')
        self.test_results = []
        self.setup_test_environment()

    def setup_test_environment(self):
        """Configure l'environnement de test complet"""
        logger.info("🔧 Configuration environnement de test...")

        # Initialisation base de données
        db_init = DatabaseInitService(self.db_path)
        db_init.init_all_tables()

        # Repositories
        self.user_repo = UserRepository(self.db_path)
        self.product_repo = ProductRepository(self.db_path)
        self.order_repo = OrderRepository(self.db_path)
        self.payout_repo = PayoutRepository(self.db_path)
        self.support_repo = SupportRepository(self.db_path)

        # Services
        self.seller_service = SellerService(self.db_path)
        self.product_service = ProductService(self.db_path)
        self.payment_service = PaymentService(self.db_path)
        self.payout_service = PayoutService(self.payout_repo)
        self.support_service = SupportService(self.support_repo)
        self.email_service = EmailService()
        self.state_manager = StateManager()

        # Handlers
        self.sell_handlers = SellHandlers(self.user_repo, self.product_repo, self.payment_service)
        self.buy_handlers = BuyHandlers(self.user_repo, self.product_repo, self.order_repo)
        self.admin_handlers = AdminHandlers(self.user_repo, self.product_repo, self.order_repo, self.payout_service)
        self.support_handlers = SupportHandlers(self.support_service)
        self.auth_handlers = AuthHandlers(self.user_repo)
        self.core_handlers = CoreHandlers(self.user_repo)

        # Mock Telegram objects
        self.mock_bot = self.create_mock_bot()
        self.mock_update = Mock()
        self.mock_query = Mock()

        logger.info("✅ Environnement de test configuré")

    def create_mock_bot(self):
        """Crée un mock bot avec les méthodes nécessaires"""
        bot = Mock()
        bot.get_db_connection = lambda: sqlite3.connect(self.db_path)
        bot.user_repo = self.user_repo
        bot.product_repo = self.product_repo
        bot.get_user_language = lambda user_id: 'fr'
        bot.update_user_state = lambda user_id, **kwargs: self.state_manager.update_state(user_id, **kwargs)
        bot.reset_user_state = lambda user_id: self.state_manager.reset_state(user_id)
        bot.get_user_state = lambda user_id: self.state_manager.get_state(user_id)
        return bot

    def create_mock_user(self, user_id: int, first_name: str = "TestUser", username: str = None) -> Mock:
        """Crée un mock utilisateur Telegram"""
        user = Mock()
        user.id = user_id
        user.first_name = first_name
        user.last_name = None
        user.username = username
        user.language_code = 'fr'
        return user

    def create_mock_update(self, user_id: int, text: str = None, callback_data: str = None) -> Mock:
        """Crée un mock update Telegram"""
        update = Mock()
        update.effective_user = self.create_mock_user(user_id)

        if text:
            update.message = Mock()
            update.message.text = text
            update.message.reply_text = AsyncMock()

        if callback_data:
            update.callback_query = Mock()
            update.callback_query.data = callback_data
            update.callback_query.from_user = update.effective_user
            update.callback_query.edit_message_text = AsyncMock()
            update.callback_query.answer = AsyncMock()

        return update

    def assert_test(self, condition: bool, test_name: str, details: str = ""):
        """Enregistre le résultat d'un test"""
        status = "✅ PASS" if condition else "❌ FAIL"
        result = f"{status} - {test_name}"
        if details:
            result += f" | {details}"

        self.test_results.append((condition, test_name, details))
        logger.info(result)
        return condition

    async def test_workflow_seller_creation(self) -> bool:
        """Test du workflow de création de compte vendeur"""
        logger.info("\n🧪 TEST: Workflow création vendeur")

        user_id = 12345
        seller_data = {
            'seller_name': 'Test Seller',
            'seller_bio': 'Expert en formations techniques',
            'email': 'test@example.com',
            'raw_password': 'testpassword123',
            'solana_address': 'So11111111111111111111111111111111111111112'
        }

        try:
            # 1. Créer utilisateur de base
            self.user_repo.create_user(
                user_id=user_id,
                username='testseller',
                first_name='Test',
                last_name='Seller'
            )
            self.assert_test(True, "Création utilisateur de base")

            # 2. Créer compte vendeur
            result = self.seller_service.create_seller_account_with_recovery(
                user_id=user_id,
                **seller_data
            )

            self.assert_test(
                result.get('success', False),
                "Création compte vendeur",
                f"Erreur: {result.get('error', 'N/A')}"
            )

            # 3. Vérifier données vendeur en DB
            user_data = self.user_repo.get_user(user_id)
            is_seller = user_data and user_data.get('is_seller', False)
            self.assert_test(is_seller, "Statut vendeur en DB")

            # 4. Test authentification vendeur
            auth_result = self.seller_service.authenticate_seller(user_id)
            self.assert_test(auth_result, "Authentification vendeur")

            # 5. Test mock handlers (sell_handlers.seller_dashboard)
            mock_update = self.create_mock_update(user_id, callback_data='seller_dashboard')
            await self.sell_handlers.seller_dashboard(self.mock_bot, mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler seller_dashboard")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow création vendeur", f"Exception: {str(e)}")
            return False

    async def test_workflow_product_creation(self) -> bool:
        """Test du workflow de création de produit"""
        logger.info("\n🧪 TEST: Workflow création produit")

        seller_id = 12345
        product_data = {
            'title': 'Formation Python Avancé',
            'description': 'Une formation complète en Python pour développeurs',
            'price': 199.99,
            'category': 'Programmation',
            'file_path': '/tmp/test_formation.pdf'
        }

        try:
            # 1. Vérifier que le vendeur existe
            seller_data = self.user_repo.get_user(seller_id)
            seller_exists = seller_data and seller_data.get('is_seller', False)
            self.assert_test(seller_exists, "Vendeur existe pour création produit")

            # 2. Créer le produit
            product_id = self.product_service.create_product(
                seller_user_id=seller_id,
                **product_data
            )

            self.assert_test(
                product_id is not None,
                "Création produit",
                f"ID: {product_id}"
            )

            # 3. Vérifier produit en DB
            if product_id:
                product = self.product_repo.get_product_by_id(product_id)
                self.assert_test(
                    product is not None,
                    "Produit en DB",
                    f"Titre: {product.get('title', 'N/A') if product else 'N/A'}"
                )

                # 4. Test recherche produit
                found_product = self.product_repo.get_product_with_seller_info(product_id)
                self.assert_test(
                    found_product is not None,
                    "Recherche produit avec seller info"
                )

                # 5. Test handler my_products
                mock_update = self.create_mock_update(seller_id, callback_data='my_products')
                await self.sell_handlers.my_products(self.mock_bot, mock_update.callback_query, 'fr')
                self.assert_test(True, "Handler my_products")

                return True

        except Exception as e:
            self.assert_test(False, "Workflow création produit", f"Exception: {str(e)}")
            return False

    async def test_workflow_buyer_purchase(self) -> bool:
        """Test du workflow d'achat par un acheteur"""
        logger.info("\n🧪 TEST: Workflow achat acheteur")

        buyer_id = 67890
        seller_id = 12345

        try:
            # 1. Créer acheteur
            self.user_repo.create_user(
                user_id=buyer_id,
                username='testbuyer',
                first_name='Test',
                last_name='Buyer'
            )
            self.assert_test(True, "Création acheteur")

            # 2. Récupérer produit disponible
            products = self.product_repo.get_all_products(limit=1)
            if not products:
                self.assert_test(False, "Aucun produit disponible pour achat")
                return False

            product = products[0]
            product_id = product['product_id']
            self.assert_test(True, "Produit trouvé pour achat", f"ID: {product_id}")

            # 3. Test affichage produit (buy_handlers.show_product)
            mock_update = self.create_mock_update(buyer_id, callback_data=f'product_{product_id}')
            await self.buy_handlers.show_product(self.mock_bot, mock_update.callback_query, product_id, 'fr')
            self.assert_test(True, "Handler show_product")

            # 4. Simuler création commande
            order_id = f"ORD-{datetime.now().strftime('%Y%m%d')}-{buyer_id}"
            order_created = self.order_repo.create_order(
                order_id=order_id,
                buyer_user_id=buyer_id,
                product_id=product_id,
                amount_eur=product['price'],
                payment_status='pending'
            )
            self.assert_test(order_created, "Création commande")

            # 5. Test payment workflow
            payment_result = self.payment_service.create_payment(
                amount_usd=product['price'] * 1.1,  # EUR to USD simulation
                currency='SOL',
                order_id=order_id
            )
            self.assert_test(
                payment_result is not None,
                "Création paiement",
                f"Status: {payment_result.get('status', 'N/A') if payment_result else 'N/A'}"
            )

            # 6. Simuler paiement confirmé
            if payment_result:
                self.order_repo.update_payment_status(order_id, 'paid')
                self.assert_test(True, "Mise à jour statut paiement")

            # 7. Test bibliothèque acheteur
            mock_update = self.create_mock_update(buyer_id, callback_data='library')
            await self.buy_handlers.show_my_library(self.mock_bot, mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler show_my_library")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow achat acheteur", f"Exception: {str(e)}")
            return False

    async def test_workflow_payout_system(self) -> bool:
        """Test du système de payouts vendeur"""
        logger.info("\n🧪 TEST: Workflow système payouts")

        seller_id = 12345

        try:
            # 1. Vérifier commandes payées du vendeur
            orders = self.order_repo.get_seller_orders(seller_id, status='paid')
            self.assert_test(
                len(orders) > 0,
                "Commandes payées trouvées",
                f"Nombre: {len(orders)}"
            )

            # 2. Calculer montant payout
            total_amount = sum(order['amount_eur'] for order in orders)
            payout_amount = total_amount * 0.95  # 95% pour le vendeur
            self.assert_test(
                payout_amount > 0,
                "Calcul montant payout",
                f"Montant: {payout_amount:.2f}€"
            )

            # 3. Créer payout
            payout_id = self.payout_service.create_payout(
                seller_user_id=seller_id,
                total_amount_eur=payout_amount,
                orders_included=[order['order_id'] for order in orders]
            )
            self.assert_test(
                payout_id is not None,
                "Création payout",
                f"ID: {payout_id}"
            )

            # 4. Test handler payout_history
            mock_update = self.create_mock_update(seller_id, callback_data='sell_payout_history')
            await self.sell_handlers.payout_history(self.mock_bot, mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler payout_history")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow système payouts", f"Exception: {str(e)}")
            return False

    async def test_workflow_support_system(self) -> bool:
        """Test du système de support"""
        logger.info("\n🧪 TEST: Workflow système support")

        buyer_id = 67890
        seller_id = 12345

        try:
            # 1. Récupérer produit pour contact vendeur
            products = self.product_repo.get_products_by_seller(seller_id, limit=1)
            if not products:
                self.assert_test(False, "Aucun produit pour test support")
                return False

            product = products[0]
            product_id = product['product_id']

            # 2. Créer ticket de support
            ticket_data = {
                'user_id': buyer_id,
                'subject': 'Question sur le produit',
                'message': 'J\'ai une question concernant ce produit',
                'related_product_id': product_id,
                'priority': 'medium'
            }

            ticket_id = self.support_service.create_ticket(**ticket_data)
            self.assert_test(
                ticket_id is not None,
                "Création ticket support",
                f"ID: {ticket_id}"
            )

            # 3. Test handler create_ticket_prompt
            mock_update = self.create_mock_update(buyer_id, callback_data='create_ticket')
            await self.support_handlers.create_ticket_prompt(self.mock_bot, mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler create_ticket_prompt")

            # 4. Test my_tickets
            mock_update = self.create_mock_update(buyer_id, callback_data='my_tickets')
            await self.support_handlers.my_tickets(self.mock_bot, mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler my_tickets")

            # 5. Ajouter réponse au ticket
            if ticket_id:
                response_added = self.support_service.add_ticket_response(
                    ticket_id=ticket_id,
                    user_id=seller_id,
                    message="Merci pour votre question. Voici ma réponse..."
                )
                self.assert_test(response_added, "Ajout réponse ticket")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow système support", f"Exception: {str(e)}")
            return False

    async def test_workflow_admin_functions(self) -> bool:
        """Test des fonctions administrateur"""
        logger.info("\n🧪 TEST: Workflow fonctions admin")

        admin_id = 99999

        try:
            # 1. Créer admin
            self.user_repo.create_user(
                user_id=admin_id,
                username='admin',
                first_name='Admin',
                last_name='Test'
            )
            self.assert_test(True, "Création admin")

            # 2. Test admin_users
            mock_update = self.create_mock_update(admin_id, callback_data='admin_users')
            await self.admin_handlers.admin_users(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler admin_users")

            # 3. Test admin_products
            mock_update = self.create_mock_update(admin_id, callback_data='admin_products')
            await self.admin_handlers.admin_products(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler admin_products")

            # 4. Test admin_marketplace_stats
            mock_update = self.create_mock_update(admin_id, callback_data='admin_marketplace_stats')
            await self.admin_handlers.admin_marketplace_stats(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler admin_marketplace_stats")

            # 5. Test admin_payouts
            mock_update = self.create_mock_update(admin_id, callback_data='admin_payouts')
            await self.admin_handlers.admin_payouts(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler admin_payouts")

            # 6. Test marquer payouts comme payés
            mock_update = self.create_mock_update(admin_id, callback_data='admin_mark_all_payouts_paid')
            await self.admin_handlers.admin_mark_all_payouts_paid(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler admin_mark_all_payouts_paid")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow fonctions admin", f"Exception: {str(e)}")
            return False

    async def test_workflow_authentication(self) -> bool:
        """Test du système d'authentification"""
        logger.info("\n🧪 TEST: Workflow authentification")

        user_id = 12345

        try:
            # 1. Test seller_login_prompt
            mock_update = self.create_mock_update(user_id, callback_data='seller_login')
            await self.auth_handlers.seller_login_prompt(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler seller_login_prompt")

            # 2. Test account_recovery_menu
            mock_update = self.create_mock_update(user_id, callback_data='account_recovery')
            await self.auth_handlers.account_recovery_menu(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler account_recovery_menu")

            # 3. Test core handlers
            mock_update = self.create_mock_update(user_id, callback_data='back_main')
            await self.core_handlers.back_to_main(mock_update.callback_query, 'fr')
            self.assert_test(True, "Handler back_to_main")

            return True

        except Exception as e:
            self.assert_test(False, "Workflow authentification", f"Exception: {str(e)}")
            return False

    async def run_all_tests(self) -> Dict[str, Any]:
        """Lance tous les tests et retourne le rapport"""
        logger.info("🚀 Début des tests complets TechBot Marketplace")

        start_time = datetime.now()

        # Exécuter tous les tests
        test_functions = [
            self.test_workflow_seller_creation,
            self.test_workflow_product_creation,
            self.test_workflow_buyer_purchase,
            self.test_workflow_payout_system,
            self.test_workflow_support_system,
            self.test_workflow_admin_functions,
            self.test_workflow_authentication
        ]

        results = []
        for test_func in test_functions:
            try:
                result = await test_func()
                results.append(result)
            except Exception as e:
                logger.error(f"Erreur test {test_func.__name__}: {e}")
                results.append(False)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # Générer rapport
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result[0])
        failed_tests = total_tests - passed_tests

        report = {
            'total_workflows': len(test_functions),
            'successful_workflows': sum(results),
            'failed_workflows': len(results) - sum(results),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': (passed_tests / total_tests * 100) if total_tests > 0 else 0,
            'duration_seconds': duration,
            'test_details': self.test_results
        }

        return report

    def cleanup(self):
        """Nettoie l'environnement de test"""
        try:
            shutil.rmtree(self.temp_dir)
            logger.info("🧹 Environnement de test nettoyé")
        except Exception as e:
            logger.warning(f"Erreur nettoyage: {e}")

    def print_report(self, report: Dict[str, Any]):
        """Affiche le rapport de test formaté"""
        print("\n" + "="*60)
        print("📊 RAPPORT DE TEST TECHBOT MARKETPLACE")
        print("="*60)

        print(f"\n🔄 WORKFLOWS:")
        print(f"   ✅ Réussis: {report['successful_workflows']}/{report['total_workflows']}")
        print(f"   ❌ Échoués: {report['failed_workflows']}/{report['total_workflows']}")

        print(f"\n🧪 TESTS DÉTAILLÉS:")
        print(f"   ✅ Réussis: {report['passed_tests']}")
        print(f"   ❌ Échoués: {report['failed_tests']}")
        print(f"   📈 Taux succès: {report['success_rate']:.1f}%")
        print(f"   ⏱️  Durée: {report['duration_seconds']:.2f}s")

        if report['failed_tests'] > 0:
            print(f"\n❌ ÉCHECS DÉTAILLÉS:")
            for passed, test_name, details in report['test_details']:
                if not passed:
                    print(f"   • {test_name}: {details}")

        print(f"\n{'🎉 TOUS LES TESTS RÉUSSIS !' if report['failed_tests'] == 0 else '⚠️  CERTAINS TESTS ONT ÉCHOUÉ'}")
        print("="*60)


async def main():
    """Fonction principale pour lancer les tests"""
    test_runner = TestWorkflows()

    try:
        report = await test_runner.run_all_tests()
        test_runner.print_report(report)

        # Exit code basé sur les résultats
        exit_code = 0 if report['failed_tests'] == 0 else 1

    except Exception as e:
        logger.error(f"Erreur fatale lors des tests: {e}")
        exit_code = 1

    finally:
        test_runner.cleanup()

    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())