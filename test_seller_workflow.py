#!/usr/bin/env python3
"""
Test spécialisé pour le workflow vendeur
Test simple et direct sans mocks Telegram
"""

import os
import sys
import sqlite3
import tempfile
import shutil
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.domain.repositories.user_repo import UserRepository
from app.domain.repositories.product_repo import ProductRepository
from app.services.seller_service import SellerService
from app.services.product_service import ProductService
from app.core.database_init import DatabaseInitService


class SellerWorkflowTest:
    """Test complet du workflow vendeur sans dépendances Telegram"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_seller.db')
        self.results = []

    def setup(self):
        """Initialise la base de données et les services"""
        print("🔧 Initialisation base de données test...")

        # Créer les tables
        db_init = DatabaseInitService(self.db_path)
        db_init.init_all_tables()

        # Initialiser services
        self.user_repo = UserRepository(self.db_path)
        self.product_repo = ProductRepository(self.db_path)
        self.seller_service = SellerService(self.db_path)
        self.product_service = ProductService(self.db_path)

        print("✅ Base de données initialisée")

    def test_step(self, step_name: str, condition: bool, details: str = ""):
        """Enregistre et affiche le résultat d'une étape"""
        status = "✅" if condition else "❌"
        result = f"{status} {step_name}"
        if details:
            result += f" | {details}"

        print(result)
        self.results.append((condition, step_name, details))
        return condition

    def test_seller_creation(self):
        """Test création complète d'un compte vendeur"""
        print("\n📝 ÉTAPE 1: Création compte vendeur")

        # Données test
        user_id = 123456
        seller_data = {
            'seller_name': 'Jean Dupont',
            'seller_bio': 'Expert en formations Python et développement web. 10 ans d\'expérience.',
            'email': 'jean.dupont@example.com',
            'raw_password': 'monMotDePasse123!',
            'solana_address': 'So11111111111111111111111111111111111111112'
        }

        try:
            # 1. Créer utilisateur de base
            user_created = self.user_repo.add_user(
                user_id=user_id,
                username='jeandupont',
                first_name='Jean'
            )
            self.test_step("Création utilisateur base", user_created)

            # 2. Créer compte vendeur
            result = self.seller_service.create_seller_account_with_recovery(
                user_id=user_id,
                **seller_data
            )

            success = result.get('success', False)
            self.test_step(
                "Création compte vendeur",
                success,
                f"Message: {result.get('message', result.get('error', 'N/A'))}"
            )

            if not success:
                return False

            # 3. Vérifier en base de données
            user_data = self.user_repo.get_user(user_id)
            is_seller = user_data and user_data.get('is_seller', False)
            self.test_step("Statut vendeur en DB", is_seller)

            # 4. Vérifier données vendeur
            if user_data:
                expected_fields = ['seller_name', 'seller_bio', 'email', 'seller_solana_address']
                all_fields_present = all(field in user_data for field in expected_fields)
                self.test_step("Champs vendeur complets", all_fields_present)

            # 5. Test authentification
            auth_success = self.seller_service.authenticate_seller(user_id)
            self.test_step("Authentification vendeur", auth_success)

            return success

        except Exception as e:
            self.test_step("Création compte vendeur", False, f"Exception: {str(e)}")
            return False

    def test_product_creation(self, seller_id: int):
        """Test création de produits par le vendeur"""
        print("\n📦 ÉTAPE 2: Création produits")

        products_data = [
            {
                'title': 'Formation Python pour Débutants',
                'description': 'Apprenez Python de zéro avec des exemples pratiques et des exercices.',
                'price': 79.99,
                'category': 'Programmation',
                'file_path': '/tmp/formation_python.pdf'
            },
            {
                'title': 'Développement Web avec Django',
                'description': 'Maîtrisez Django pour créer des applications web robustes.',
                'price': 129.99,
                'category': 'Développement Web',
                'file_path': '/tmp/formation_django.pdf'
            },
            {
                'title': 'Introduction à l\'IA et Machine Learning',
                'description': 'Découvrez les concepts fondamentaux de l\'intelligence artificielle.',
                'price': 199.99,
                'category': 'Intelligence Artificielle',
                'file_path': '/tmp/formation_ia.pdf'
            }
        ]

        created_products = []

        for i, product_data in enumerate(products_data, 1):
            try:
                # Générer ID produit unique
                from app.core.utils import generate_product_id
                product_id = generate_product_id(self.db_path)

                # Préparer données produit pour insertion
                product_dict = {
                    'product_id': product_id,
                    'seller_user_id': seller_id,
                    'title': product_data['title'],
                    'description': product_data['description'],
                    'category': product_data['category'],
                    'price_eur': product_data['price'],
                    'price_usd': product_data['price'] * 1.1,  # Simulation USD
                    'main_file_path': product_data['file_path'],
                    'file_size_mb': 1.5,  # Simulation
                    'status': 'active'
                }

                success = self.product_repo.insert_product(product_dict)
                self.test_step(
                    f"Création produit {i}",
                    success,
                    f"ID: {product_id}, Titre: {product_data['title'][:30]}..."
                )

                if success:
                    created_products.append(product_id)

                    # Vérifier produit en DB
                    product = self.product_repo.get_product_by_id(product_id)
                    in_db = product is not None
                    self.test_step(f"Produit {i} en DB", in_db)

            except Exception as e:
                self.test_step(f"Création produit {i}", False, f"Exception: {str(e)}")

        return created_products

    def test_product_management(self, seller_id: int, product_ids: list):
        """Test gestion des produits (modification, activation/désactivation)"""
        print("\n⚙️ ÉTAPE 3: Gestion produits")

        if not product_ids:
            self.test_step("Gestion produits", False, "Aucun produit disponible")
            return

        try:
            # 1. Lister produits du vendeur
            seller_products = self.product_repo.get_products_by_seller(seller_id)
            products_found = len(seller_products) >= len(product_ids)
            self.test_step(
                "Liste produits vendeur",
                products_found,
                f"Trouvés: {len(seller_products)}, Attendus: {len(product_ids)}"
            )

            # 2. Modifier prix d'un produit
            if product_ids:
                first_product_id = product_ids[0]
                new_price_eur = 89.99
                new_price_usd = new_price_eur * 1.1
                price_updated = self.product_repo.update_price(first_product_id, seller_id, new_price_eur, new_price_usd)
                self.test_step("Modification prix", price_updated)

                # Vérifier modification
                if price_updated:
                    updated_product = self.product_repo.get_product_by_id(first_product_id)
                    price_correct = updated_product and abs(updated_product['price_eur'] - new_price_eur) < 0.01
                    self.test_step("Vérification nouveau prix", price_correct)

            # 3. Désactiver/Réactiver produit
            if len(product_ids) > 1:
                second_product_id = product_ids[1]

                # Désactiver
                deactivated = self.product_repo.update_status(second_product_id, 'inactive')
                self.test_step("Désactivation produit", deactivated)

                # Réactiver
                reactivated = self.product_repo.update_status(second_product_id, 'active')
                self.test_step("Réactivation produit", reactivated)

            # 4. Statistiques vendeur
            total_products = len(seller_products)
            active_products = sum(1 for p in seller_products if p['status'] == 'active')
            self.test_step(
                "Statistiques produits",
                True,
                f"Total: {total_products}, Actifs: {active_products}"
            )

        except Exception as e:
            self.test_step("Gestion produits", False, f"Exception: {str(e)}")

    def test_seller_profile_management(self, seller_id: int):
        """Test gestion du profil vendeur"""
        print("\n👤 ÉTAPE 4: Gestion profil vendeur")

        try:
            # 1. Récupérer profil actuel
            current_data = self.user_repo.get_user(seller_id)
            profile_exists = current_data and current_data.get('is_seller', False)
            self.test_step("Récupération profil", profile_exists)

            # 2. Modifier nom vendeur
            new_name = "Jean Dupont - Expert Python"
            name_updated = self.user_repo.update_seller_name(seller_id, new_name)
            self.test_step("Modification nom vendeur", name_updated)

            # 3. Modifier biographie
            new_bio = "Expert en développement Python avec plus de 10 ans d'expérience. Spécialisé en formation technique et développement d'applications web modernes."
            bio_updated = self.user_repo.update_seller_bio(seller_id, new_bio)
            self.test_step("Modification biographie", bio_updated)

            # 4. Vérifier modifications
            updated_data = self.user_repo.get_user(seller_id)
            if updated_data:
                name_correct = updated_data.get('seller_name') == new_name
                bio_correct = updated_data.get('seller_bio') == new_bio
                self.test_step("Vérification nom", name_correct)
                self.test_step("Vérification bio", bio_correct)

        except Exception as e:
            self.test_step("Gestion profil vendeur", False, f"Exception: {str(e)}")

    def run_complete_test(self):
        """Lance le test complet du workflow vendeur"""
        print("🚀 TEST COMPLET WORKFLOW VENDEUR")
        print("=" * 50)

        try:
            # Setup
            self.setup()

            # Test création vendeur
            seller_created = self.test_seller_creation()
            if not seller_created:
                print("\n❌ Échec création vendeur - arrêt du test")
                return

            seller_id = 123456

            # Test création produits
            product_ids = self.test_product_creation(seller_id)

            # Test gestion produits
            self.test_product_management(seller_id, product_ids)

            # Test gestion profil
            self.test_seller_profile_management(seller_id)

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

        status = "🎉 WORKFLOW VENDEUR FONCTIONNEL" if failed_tests == 0 else "⚠️ PROBLÈMES DÉTECTÉS"
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
    test = SellerWorkflowTest()
    test.run_complete_test()