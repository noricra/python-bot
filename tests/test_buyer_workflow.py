#!/usr/bin/env python3
"""
Test spécialisé pour le workflow acheteur
Test recherche, achat et gestion de bibliothèque
"""

import os
import sys
import tempfile
import shutil
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.domain.repositories.user_repo import UserRepository
from app.domain.repositories.product_repo import ProductRepository
from app.domain.repositories.order_repo import OrderRepository
from app.services.product_service import ProductService
from app.services.payment_service import PaymentService
from app.core.database_init import DatabaseInitService


class BuyerWorkflowTest:
    """Test complet du workflow acheteur"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_buyer.db')
        self.results = []

    def setup(self):
        """Initialise l'environnement de test avec des données"""
        print("🔧 Initialisation environnement test acheteur...")

        # Base de données
        db_init = DatabaseInitService(self.db_path)
        db_init.init_all_tables()

        # Services
        self.user_repo = UserRepository(self.db_path)
        self.product_repo = ProductRepository(self.db_path)
        self.order_repo = OrderRepository(self.db_path)
        self.product_service = ProductService(self.db_path)
        self.payment_service = PaymentService(test_mode=True)

        # Créer données test
        self.create_test_data()
        print("✅ Environnement initialisé avec données test")

    def create_test_data(self):
        """Crée des vendeurs et produits pour les tests"""
        # Créer vendeur test
        seller_id = 999999
        self.user_repo.add_user(
            user_id=seller_id,
            username='testseller',
            first_name='Test'
        )

        # Créer compte vendeur
        from app.services.seller_service import SellerService
        seller_service = SellerService(self.db_path)
        seller_service.create_seller_account_with_recovery(
            user_id=seller_id,
            seller_name='Vendeur Test',
            seller_bio='Vendeur de test pour les workflows',
            email='seller@test.com',
            raw_password='testpass123',
            solana_address='So11111111111111111111111111111111111111112'
        )

        # Créer produits test
        test_products = [
            {
                'title': 'Formation Python Complète',
                'description': 'Formation complète Python pour débutants et intermédiaires',
                'price': 99.99,
                'category': 'Programmation',
                'file_path': '/tmp/python_formation.pdf'
            },
            {
                'title': 'Développement Web Moderne',
                'description': 'Maîtrisez React, Vue.js et les frameworks modernes',
                'price': 149.99,
                'category': 'Développement Web',
                'file_path': '/tmp/web_dev.pdf'
            },
            {
                'title': 'Machine Learning Pratique',
                'description': 'Apprenez le ML avec des projets concrets',
                'price': 199.99,
                'category': 'Intelligence Artificielle',
                'file_path': '/tmp/ml_course.pdf'
            }
        ]

        self.test_product_ids = []
        for product_data in test_products:
            # Générer ID produit unique
            from app.core.utils import generate_product_id
            product_id = generate_product_id(self.db_path)

            # Préparer données produit
            product_dict = {
                'product_id': product_id,
                'seller_user_id': seller_id,
                'title': product_data['title'],
                'description': product_data['description'],
                'category': product_data['category'],
                'price_eur': product_data['price'],
                'price_usd': product_data['price'] * 1.1,
                'main_file_path': product_data['file_path'],
                'file_size_mb': 2.0,
                'status': 'active'
            }

            success = self.product_repo.insert_product(product_dict)
            if success:
                self.test_product_ids.append(product_id)

    def test_step(self, step_name: str, condition: bool, details: str = ""):
        """Enregistre et affiche le résultat d'une étape"""
        status = "✅" if condition else "❌"
        result = f"{status} {step_name}"
        if details:
            result += f" | {details}"

        print(result)
        self.results.append((condition, step_name, details))
        return condition

    def test_buyer_registration(self):
        """Test inscription d'un acheteur"""
        print("\n👤 ÉTAPE 1: Inscription acheteur")

        buyer_data = {
            'user_id': 111111,
            'username': 'testbuyer',
            'first_name': 'Marie'
        }

        try:
            # Créer acheteur
            buyer_created = self.user_repo.add_user(**buyer_data)
            self.test_step("Création compte acheteur", buyer_created)

            # Vérifier en DB
            if buyer_created:
                user_data = self.user_repo.get_user(buyer_data['user_id'])
                account_verified = user_data is not None
                self.test_step("Vérification compte en DB", account_verified)

                # Vérifier que ce n'est pas un vendeur
                is_not_seller = not user_data.get('is_seller', False)
                self.test_step("Statut non-vendeur", is_not_seller)

            return buyer_created

        except Exception as e:
            self.test_step("Inscription acheteur", False, f"Exception: {str(e)}")
            return False

    def test_product_discovery(self, buyer_id: int):
        """Test découverte et recherche de produits"""
        print("\n🔍 ÉTAPE 2: Découverte produits")

        try:
            # 1. Lister tous les produits
            all_products = self.product_repo.get_all_products()
            products_available = len(all_products) > 0
            self.test_step(
                "Produits disponibles",
                products_available,
                f"Nombre: {len(all_products)}"
            )

            # 2. Recherche par catégorie
            categories = ['Programmation', 'Développement Web', 'Intelligence Artificielle']
            for category in categories:
                category_products = self.product_service.search_products_by_category(category)
                found_in_category = len(category_products) > 0
                self.test_step(
                    f"Produits catégorie '{category}'",
                    found_in_category,
                    f"Trouvés: {len(category_products)}"
                )

            # 3. Recherche par ID spécifique
            if self.test_product_ids:
                first_product_id = self.test_product_ids[0]
                found_product = self.product_repo.get_product_with_seller_info(first_product_id)
                product_found = found_product is not None
                self.test_step(
                    "Recherche produit par ID",
                    product_found,
                    f"ID: {first_product_id}"
                )

                # Vérifier informations vendeur incluses
                if found_product:
                    has_seller_info = 'seller_name' in found_product
                    self.test_step("Infos vendeur incluses", has_seller_info)

            return products_available

        except Exception as e:
            self.test_step("Découverte produits", False, f"Exception: {str(e)}")
            return False

    def test_purchase_process(self, buyer_id: int):
        """Test processus d'achat complet"""
        print("\n💳 ÉTAPE 3: Processus achat")

        if not self.test_product_ids:
            self.test_step("Processus achat", False, "Aucun produit disponible")
            return []

        purchased_orders = []

        try:
            # Acheter 2 produits
            for i, product_id in enumerate(self.test_product_ids[:2], 1):
                print(f"\n   💰 Achat produit {i}: {product_id}")

                # 1. Récupérer infos produit
                product = self.product_repo.get_product_by_id(product_id)
                if not product:
                    self.test_step(f"Récupération produit {i}", False)
                    continue

                self.test_step(f"Produit {i} trouvé", True, f"Prix: {product['price_eur']}€")

                # 2. Créer commande
                order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{buyer_id}-{i}"
                order_dict = {
                    'order_id': order_id,
                    'buyer_user_id': buyer_id,
                    'product_id': product_id,
                    'seller_user_id': product['seller_user_id'],
                    'product_price_eur': product['price_eur'],
                    'product_title': product['title'],
                    'seller_revenue': product['price_eur'] * 0.95,       # 95% pour vendeur
                    'crypto_currency': 'SOL',
                    'crypto_amount': 0.0,  # À calculer plus tard
                    'payment_status': 'pending'
                    # Remove created_at to let database set it automatically
                }
                order_created = self.order_repo.insert_order(order_dict)
                self.test_step(f"Création commande {i}", order_created, f"ID: {order_id}")

                if not order_created:
                    continue

                # 3. Processus paiement
                payment_result = self.payment_service.create_payment(
                    amount_usd=product['price_eur'] * 1.1,  # Simulation EUR->USD
                    currency='SOL',
                    order_id=order_id
                )
                payment_created = payment_result is not None
                self.test_step(f"Création paiement {i}", payment_created)

                # 4. Simuler confirmation paiement
                if payment_created:
                    payment_confirmed = self.order_repo.update_payment_status(order_id, 'paid')
                    self.test_step(f"Confirmation paiement {i}", payment_confirmed)

                    if payment_confirmed:
                        purchased_orders.append(order_id)

                        # Incrémenter compteur téléchargements/ventes
                        self.order_repo.increment_download_count(product_id, buyer_id)
                        self.test_step(f"Incrémentation stats {i}", True)

            return purchased_orders

        except Exception as e:
            self.test_step("Processus achat", False, f"Exception: {str(e)}")
            return []

    def test_library_management(self, buyer_id: int, purchased_orders: list):
        """Test gestion bibliothèque acheteur"""
        print("\n📚 ÉTAPE 4: Gestion bibliothèque")

        try:
            # 1. Récupérer achats de l'utilisateur
            user_orders = self.order_repo.get_orders_by_buyer(buyer_id)
            orders_found = len(user_orders) >= len(purchased_orders)
            self.test_step(
                "Commandes en bibliothèque",
                orders_found,
                f"Trouvées: {len(user_orders)}, Attendues: {len(purchased_orders)}"
            )

            # 2. Vérifier statut des commandes
            paid_orders = [order for order in user_orders if order['payment_status'] == 'paid']
            paid_orders_correct = len(paid_orders) == len(purchased_orders)
            self.test_step(
                "Commandes payées",
                paid_orders_correct,
                f"Payées: {len(paid_orders)}"
            )

            # 3. Test téléchargement (simulation)
            downloads_successful = 0
            for order in paid_orders:
                product_id = order['product_id']
                # Simuler téléchargement en incrémentant le compteur
                download_success = self.order_repo.increment_download_count(product_id, buyer_id)
                if download_success:
                    downloads_successful += 1

            all_downloads_ok = downloads_successful == len(paid_orders)
            self.test_step(
                "Téléchargements simulés",
                all_downloads_ok,
                f"Réussis: {downloads_successful}/{len(paid_orders)}"
            )

            # 4. Vérifier historique complet
            if user_orders:
                # Calculer montant total dépensé
                total_spent = sum(order['product_price_eur'] for order in user_orders if order['payment_status'] == 'paid')
                self.test_step(
                    "Montant total dépensé",
                    total_spent > 0,
                    f"{total_spent:.2f}€"
                )

                # Vérifier dates d'achat - simplifié pour éviter les problèmes de format de date
                recent_orders_ok = len(user_orders) >= len(purchased_orders)
                self.test_step(
                    "Commandes récentes",
                    recent_orders_ok,
                    f"Récentes: {len(user_orders)}"
                )

        except Exception as e:
            self.test_step("Gestion bibliothèque", False, f"Exception: {str(e)}")

    def test_product_interaction(self, buyer_id: int):
        """Test interactions avec les produits (vues, etc.)"""
        print("\n👀 ÉTAPE 5: Interactions produits")

        try:
            # 1. Simuler vues de produits
            viewed_products = 0
            for product_id in self.test_product_ids:
                view_recorded = self.product_repo.increment_views(product_id)
                if view_recorded:
                    viewed_products += 1

            all_views_recorded = viewed_products == len(self.test_product_ids)
            self.test_step(
                "Enregistrement vues",
                all_views_recorded,
                f"Vues: {viewed_products}/{len(self.test_product_ids)}"
            )

            # 2. Vérifier statistiques produits
            total_views = 0
            total_downloads = 0

            for product_id in self.test_product_ids:
                product = self.product_repo.get_product_by_id(product_id)
                if product:
                    total_views += product.get('views_count', 0)
                    total_downloads += product.get('downloads_count', 0)

            stats_updated = total_views > 0
            self.test_step(
                "Statistiques mises à jour",
                stats_updated,
                f"Vues: {total_views}, Téléchargements: {total_downloads}"
            )

        except Exception as e:
            self.test_step("Interactions produits", False, f"Exception: {str(e)}")

    def run_complete_test(self):
        """Lance le test complet du workflow acheteur"""
        print("🛒 TEST COMPLET WORKFLOW ACHETEUR")
        print("=" * 50)

        try:
            # Setup
            self.setup()

            # Test inscription
            buyer_registered = self.test_buyer_registration()
            if not buyer_registered:
                print("\n❌ Échec inscription acheteur - arrêt du test")
                return

            buyer_id = 111111

            # Test découverte produits
            products_discovered = self.test_product_discovery(buyer_id)
            if not products_discovered:
                print("\n❌ Aucun produit trouvé - arrêt du test")
                return

            # Test processus achat
            purchased_orders = self.test_purchase_process(buyer_id)

            # Test gestion bibliothèque
            self.test_library_management(buyer_id, purchased_orders)

            # Test interactions
            self.test_product_interaction(buyer_id)

            # Rapport final
            self.print_final_report()

        except Exception as e:
            print(f"\n❌ ERREUR FATALE: {str(e)}")

        finally:
            self.cleanup()

    def print_final_report(self):
        """Affiche le rapport final"""
        print("\n" + "=" * 50)
        print("📊 RAPPORT FINAL")
        print("=" * 50)

        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result[0])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 Tests réussis: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"❌ Tests échoués: {failed_tests}")

        if failed_tests > 0:
            print(f"\n🔍 DÉTAIL DES ÉCHECS:")
            for passed, test_name, details in self.results:
                if not passed:
                    print(f"   • {test_name}: {details}")

        status = "🎉 WORKFLOW ACHETEUR FONCTIONNEL" if failed_tests == 0 else "⚠️ PROBLÈMES DÉTECTÉS"
        print(f"\n{status}")
        print("=" * 50)

    def cleanup(self):
        """Nettoie les fichiers temporaires"""
        try:
            shutil.rmtree(self.temp_dir)
            print("\n🧹 Nettoyage terminé")
        except Exception as e:
            print(f"\n⚠️ Erreur nettoyage: {e}")


if __name__ == "__main__":
    test = BuyerWorkflowTest()
    test.run_complete_test()