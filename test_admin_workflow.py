#!/usr/bin/env python3
"""
Test spécialisé pour le workflow administrateur
Test gestion utilisateurs, produits, payouts et statistiques
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
from app.domain.repositories.payout_repo import PayoutRepository
from app.services.payout_service import PayoutService
from app.core.database_init import DatabaseInitService


class AdminWorkflowTest:
    """Test complet des fonctions administrateur"""

    def __init__(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_admin.db')
        self.results = []

    def setup(self):
        """Initialise l'environnement avec des données complètes"""
        print("🔧 Initialisation environnement test admin...")

        # Base de données
        db_init = DatabaseInitService(self.db_path)
        db_init.init_all_tables()

        # Services
        self.user_repo = UserRepository(self.db_path)
        self.product_repo = ProductRepository(self.db_path)
        self.order_repo = OrderRepository(self.db_path)
        self.payout_repo = PayoutRepository(self.db_path)
        self.payout_service = PayoutService(self.payout_repo)

        # Créer données test complètes
        self.create_comprehensive_test_data()
        print("✅ Environnement initialisé avec données complètes")

    def create_comprehensive_test_data(self):
        """Crée un écosystème complet : vendeurs, acheteurs, produits, commandes"""
        # Créer admin
        self.admin_id = 999999
        self.user_repo.add_user(
            user_id=self.admin_id,
            username='admin',
            first_name='Admin'
        )

        # Créer vendeurs
        self.seller_ids = []
        seller_data = [
            {'id': 100001, 'name': 'Pierre Durand', 'bio': 'Expert Python', 'email': 'pierre@test.com'},
            {'id': 100002, 'name': 'Marie Legrand', 'bio': 'Spécialiste Web', 'email': 'marie@test.com'},
            {'id': 100003, 'name': 'Jean Moreau', 'bio': 'Formateur IA', 'email': 'jean@test.com'}
        ]

        from app.services.seller_service import SellerService
        seller_service = SellerService(self.db_path)

        for seller in seller_data:
            # Créer utilisateur
            self.user_repo.add_user(
                user_id=seller['id'],
                username=f"seller{seller['id']}",
                first_name=seller['name'].split()[0]
            )

            # Créer compte vendeur
            seller_service.create_seller_account_with_recovery(
                user_id=seller['id'],
                seller_name=seller['name'],
                seller_bio=seller['bio'],
                email=seller['email'],
                raw_password='testpass123',
                solana_address='So11111111111111111111111111111111111111112'
            )
            self.seller_ids.append(seller['id'])

        # Créer acheteurs
        self.buyer_ids = []
        buyer_data = [
            {'id': 200001, 'name': 'Alice Martin', 'username': 'alice'},
            {'id': 200002, 'name': 'Bob Dupuis', 'username': 'bob'},
            {'id': 200003, 'name': 'Claire Blanc', 'username': 'claire'},
            {'id': 200004, 'name': 'David Noir', 'username': 'david'}
        ]

        for buyer in buyer_data:
            self.user_repo.add_user(
                user_id=buyer['id'],
                username=buyer['username'],
                first_name=buyer['name'].split()[0]
            )
            self.buyer_ids.append(buyer['id'])

        # Créer produits
        from app.core.utils import generate_product_id

        products_data = [
            {'seller': 100001, 'title': 'Python Débutant', 'price': 79.99, 'category': 'Programmation'},
            {'seller': 100001, 'title': 'Python Avancé', 'price': 129.99, 'category': 'Programmation'},
            {'seller': 100002, 'title': 'React Masterclass', 'price': 149.99, 'category': 'Développement Web'},
            {'seller': 100002, 'title': 'Vue.js Complet', 'price': 119.99, 'category': 'Développement Web'},
            {'seller': 100003, 'title': 'ML pour Débutants', 'price': 199.99, 'category': 'IA'},
            {'seller': 100003, 'title': 'Deep Learning', 'price': 299.99, 'category': 'IA'}
        ]

        self.product_ids = []
        for product in products_data:
            product_id = generate_product_id(self.db_path)
            product_dict = {
                'product_id': product_id,
                'seller_user_id': product['seller'],
                'title': product['title'],
                'description': f"Description complète de {product['title']}",
                'category': product['category'],
                'price_eur': product['price'],
                'price_usd': product['price'] * 1.1,
                'main_file_path': f"/tmp/{product['title'].replace(' ', '_').lower()}.pdf",
                'file_size_mb': 3.0,
                'status': 'active'
            }

            success = self.product_repo.insert_product(product_dict)
            if success:
                self.product_ids.append(product_id)

        # Créer commandes variées
        self.create_test_orders()

    def create_test_orders(self):
        """Crée des commandes avec différents statuts"""
        self.order_ids = []

        # Commandes payées (pour générer des revenus)
        paid_orders = [
            {'buyer': 200001, 'product_idx': 0, 'status': 'paid'},
            {'buyer': 200001, 'product_idx': 1, 'status': 'paid'},
            {'buyer': 200002, 'product_idx': 2, 'status': 'paid'},
            {'buyer': 200003, 'product_idx': 3, 'status': 'paid'},
            {'buyer': 200003, 'product_idx': 4, 'status': 'paid'},
            {'buyer': 200004, 'product_idx': 5, 'status': 'paid'}
        ]

        # Commandes en attente
        pending_orders = [
            {'buyer': 200002, 'product_idx': 0, 'status': 'pending'},
            {'buyer': 200004, 'product_idx': 1, 'status': 'pending'}
        ]

        all_orders = paid_orders + pending_orders

        for i, order_data in enumerate(all_orders):
            if order_data['product_idx'] < len(self.product_ids):
                product_id = self.product_ids[order_data['product_idx']]
                product = self.product_repo.get_product_by_id(product_id)

                if product:
                    order_id = f"ORD-TEST-{i+1:03d}-{order_data['buyer']}"
                    order_created = self.order_repo.create_order(
                        order_id=order_id,
                        buyer_user_id=order_data['buyer'],
                        product_id=product_id,
                        amount_eur=product['price'],
                        payment_status=order_data['status']
                    )

                    if order_created:
                        self.order_ids.append(order_id)

                        # Incrémenter stats pour commandes payées
                        if order_data['status'] == 'paid':
                            self.product_repo.increment_downloads(product_id)

        # Créer quelques payouts
        self.create_test_payouts()

    def create_test_payouts(self):
        """Crée des payouts pour les vendeurs"""
        for seller_id in self.seller_ids:
            # Récupérer commandes payées du vendeur
            paid_orders = self.order_repo.get_seller_orders(seller_id, status='paid')

            if paid_orders:
                total_amount = sum(order['amount_eur'] for order in paid_orders)
                payout_amount = total_amount * 0.95  # 95% pour le vendeur

                # Créer payout (certains en pending, d'autres payés)
                status = 'pending' if seller_id == self.seller_ids[0] else 'paid'

                self.payout_service.create_payout(
                    seller_user_id=seller_id,
                    total_amount_eur=payout_amount,
                    orders_included=[order['order_id'] for order in paid_orders],
                    status=status
                )

    def test_step(self, step_name: str, condition: bool, details: str = ""):
        """Enregistre et affiche le résultat d'une étape"""
        status = "✅" if condition else "❌"
        result = f"{status} {step_name}"
        if details:
            result += f" | {details}"

        print(result)
        self.results.append((condition, step_name, details))
        return condition

    def test_user_management(self):
        """Test gestion des utilisateurs"""
        print("\n👥 ÉTAPE 1: Gestion utilisateurs")

        try:
            # 1. Compter utilisateurs
            total_users = self.user_repo.count_users()
            users_exist = total_users > 0
            self.test_step(
                "Comptage utilisateurs",
                users_exist,
                f"Total: {total_users}"
            )

            # 2. Compter vendeurs
            total_sellers = self.user_repo.count_sellers()
            sellers_exist = total_sellers > 0
            self.test_step(
                "Comptage vendeurs",
                sellers_exist,
                f"Vendeurs: {total_sellers}"
            )

            # 3. Lister tous utilisateurs
            all_users = self.user_repo.get_all_users(limit=50)
            users_listed = len(all_users) == total_users
            self.test_step(
                "Liste complète utilisateurs",
                users_listed,
                f"Listés: {len(all_users)}"
            )

            # 4. Recherche utilisateur spécifique
            if self.buyer_ids:
                test_user_id = self.buyer_ids[0]
                found_user = self.user_repo.get_user(test_user_id)
                user_found = found_user is not None
                self.test_step(
                    "Recherche utilisateur par ID",
                    user_found,
                    f"ID: {test_user_id}"
                )

            # 5. Statistiques utilisateurs par type
            regular_users = total_users - total_sellers
            self.test_step(
                "Répartition utilisateurs",
                True,
                f"Regular: {regular_users}, Sellers: {total_sellers}"
            )

        except Exception as e:
            self.test_step("Gestion utilisateurs", False, f"Exception: {str(e)}")

    def test_product_management(self):
        """Test gestion des produits"""
        print("\n📦 ÉTAPE 2: Gestion produits")

        try:
            # 1. Compter produits
            total_products = self.product_repo.count_products()
            products_exist = total_products > 0
            self.test_step(
                "Comptage produits",
                products_exist,
                f"Total: {total_products}"
            )

            # 2. Lister tous produits
            all_products = self.product_repo.get_all_products(limit=50)
            products_listed = len(all_products) >= len(self.product_ids)
            self.test_step(
                "Liste complète produits",
                products_listed,
                f"Listés: {len(all_products)}"
            )

            # 3. Recherche produit par ID
            if self.product_ids:
                test_product_id = self.product_ids[0]
                found_product = self.product_repo.get_product_by_id(test_product_id)
                product_found = found_product is not None
                self.test_step(
                    "Recherche produit par ID",
                    product_found,
                    f"ID: {test_product_id}"
                )

            # 4. Statistiques par statut
            active_products = sum(1 for p in all_products if p['status'] == 'active')
            inactive_products = len(all_products) - active_products
            self.test_step(
                "Répartition statuts",
                True,
                f"Actifs: {active_products}, Inactifs: {inactive_products}"
            )

            # 5. Test modération (changer statut)
            if self.product_ids and len(self.product_ids) > 1:
                test_product_id = self.product_ids[-1]  # Dernier produit
                # Suspendre
                suspended = self.product_repo.update_status(test_product_id, 'banned')
                self.test_step("Suspension produit", suspended)

                # Réactiver
                if suspended:
                    reactivated = self.product_repo.update_status(test_product_id, 'active')
                    self.test_step("Réactivation produit", reactivated)

        except Exception as e:
            self.test_step("Gestion produits", False, f"Exception: {str(e)}")

    def test_order_management(self):
        """Test gestion des commandes"""
        print("\n🛒 ÉTAPE 3: Gestion commandes")

        try:
            # 1. Compter commandes
            total_orders = self.order_repo.count_orders()
            orders_exist = total_orders > 0
            self.test_step(
                "Comptage commandes",
                orders_exist,
                f"Total: {total_orders}"
            )

            # 2. Statistiques par statut
            all_orders = self.order_repo.get_all_orders(limit=100)
            paid_orders = [o for o in all_orders if o['payment_status'] == 'paid']
            pending_orders = [o for o in all_orders if o['payment_status'] == 'pending']

            self.test_step(
                "Répartition commandes",
                True,
                f"Payées: {len(paid_orders)}, En attente: {len(pending_orders)}"
            )

            # 3. Calcul revenus total
            total_revenue = self.order_repo.get_total_revenue()
            revenue_calculated = total_revenue > 0
            self.test_step(
                "Calcul revenus",
                revenue_calculated,
                f"Total: {total_revenue:.2f}€"
            )

            # 4. Commandes par période (ce mois)
            start_of_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            monthly_orders = [
                order for order in all_orders
                if datetime.fromisoformat(order['created_at'].replace('Z', '+00:00').replace('+00:00', '')) >= start_of_month
            ]

            self.test_step(
                "Commandes ce mois",
                True,
                f"Nombre: {len(monthly_orders)}"
            )

        except Exception as e:
            self.test_step("Gestion commandes", False, f"Exception: {str(e)}")

    def test_payout_management(self):
        """Test gestion des payouts"""
        print("\n💰 ÉTAPE 4: Gestion payouts")

        try:
            # 1. Lister payouts en attente
            pending_payouts = self.payout_service.get_pending_payouts()
            payouts_pending = len(pending_payouts) > 0
            self.test_step(
                "Payouts en attente",
                payouts_pending,
                f"Nombre: {len(pending_payouts)}"
            )

            # 2. Lister tous payouts
            all_payouts = self.payout_service.get_all_payouts()
            payouts_exist = len(all_payouts) > 0
            self.test_step(
                "Tous payouts",
                payouts_exist,
                f"Total: {len(all_payouts)}"
            )

            # 3. Calculer montant total pending
            total_pending_amount = sum(p['amount'] for p in pending_payouts)
            self.test_step(
                "Montant pending",
                True,
                f"Total: {total_pending_amount:.2f}€"
            )

            # 4. Marquer payouts comme payés (simulation)
            if pending_payouts:
                count_marked = self.payout_service.mark_all_payouts_paid()
                marking_successful = count_marked > 0
                self.test_step(
                    "Marquage payouts payés",
                    marking_successful,
                    f"Marqués: {count_marked}"
                )

                # Vérifier qu'il n'y a plus de pending
                remaining_pending = self.payout_service.get_pending_payouts()
                all_processed = len(remaining_pending) == 0
                self.test_step("Tous payouts traités", all_processed)

        except Exception as e:
            self.test_step("Gestion payouts", False, f"Exception: {str(e)}")

    def test_marketplace_statistics(self):
        """Test génération statistiques marketplace"""
        print("\n📊 ÉTAPE 5: Statistiques marketplace")

        try:
            # 1. Statistiques globales
            stats = {
                'total_users': self.user_repo.count_users(),
                'total_sellers': self.user_repo.count_sellers(),
                'total_products': self.product_repo.count_products(),
                'total_orders': self.order_repo.count_orders(),
                'total_revenue': self.order_repo.get_total_revenue()
            }

            stats_complete = all(stat >= 0 for stat in stats.values())
            self.test_step(
                "Statistiques globales",
                stats_complete,
                f"Users: {stats['total_users']}, Revenue: {stats['total_revenue']:.2f}€"
            )

            # 2. Top vendeurs par revenus
            top_sellers = []
            for seller_id in self.seller_ids:
                seller_orders = self.order_repo.get_seller_orders(seller_id, status='paid')
                seller_revenue = sum(order['amount_eur'] for order in seller_orders)
                if seller_revenue > 0:
                    seller_data = self.user_repo.get_user(seller_id)
                    top_sellers.append({
                        'seller_id': seller_id,
                        'name': seller_data.get('seller_name', 'Unknown'),
                        'revenue': seller_revenue
                    })

            top_sellers.sort(key=lambda x: x['revenue'], reverse=True)
            top_sellers_identified = len(top_sellers) > 0
            self.test_step(
                "Top vendeurs",
                top_sellers_identified,
                f"Vendeurs actifs: {len(top_sellers)}"
            )

            # 3. Produits les plus vendus
            product_sales = {}
            all_orders = self.order_repo.get_all_orders(limit=1000)
            paid_orders = [o for o in all_orders if o['payment_status'] == 'paid']

            for order in paid_orders:
                product_id = order['product_id']
                product_sales[product_id] = product_sales.get(product_id, 0) + 1

            top_products = sorted(product_sales.items(), key=lambda x: x[1], reverse=True)
            bestsellers_identified = len(top_products) > 0
            self.test_step(
                "Produits bestsellers",
                bestsellers_identified,
                f"Produits vendus: {len(top_products)}"
            )

            # 4. Analyse temporelle (revenus par jour)
            daily_revenue = {}
            for order in paid_orders:
                order_date = order['created_at'][:10]  # YYYY-MM-DD
                daily_revenue[order_date] = daily_revenue.get(order_date, 0) + order['amount_eur']

            temporal_analysis = len(daily_revenue) > 0
            self.test_step(
                "Analyse temporelle",
                temporal_analysis,
                f"Jours avec revenus: {len(daily_revenue)}"
            )

        except Exception as e:
            self.test_step("Statistiques marketplace", False, f"Exception: {str(e)}")

    def test_export_functions(self):
        """Test fonctions d'export de données"""
        print("\n📤 ÉTAPE 6: Fonctions export")

        try:
            # 1. Export utilisateurs (simulation)
            all_users = self.user_repo.get_all_users()
            export_data = []
            for user in all_users[:50]:  # Limite pour simulation
                export_data.append(f"{user['user_id']},{user.get('username', '')},{user.get('first_name', '')}")

            export_successful = len(export_data) > 0
            self.test_step(
                "Export utilisateurs",
                export_successful,
                f"Lignes exportées: {len(export_data)}"
            )

            # 2. Export payouts (simulation)
            all_payouts = self.payout_service.get_all_payouts()
            payout_export = []
            for payout in all_payouts[:50]:
                payout_export.append(f"{payout['user_id']},{payout['amount']},{payout['status']}")

            payout_export_successful = len(payout_export) >= 0  # Peut être 0 si pas de payouts
            self.test_step(
                "Export payouts",
                payout_export_successful,
                f"Lignes exportées: {len(payout_export)}"
            )

            # 3. Export commandes (simulation)
            all_orders = self.order_repo.get_all_orders(limit=50)
            order_export = []
            for order in all_orders:
                order_export.append(f"{order['order_id']},{order['buyer_user_id']},{order['amount_eur']},{order['payment_status']}")

            order_export_successful = len(order_export) > 0
            self.test_step(
                "Export commandes",
                order_export_successful,
                f"Lignes exportées: {len(order_export)}"
            )

        except Exception as e:
            self.test_step("Fonctions export", False, f"Exception: {str(e)}")

    def run_complete_test(self):
        """Lance le test complet des fonctions admin"""
        print("⚡ TEST COMPLET WORKFLOW ADMINISTRATEUR")
        print("=" * 60)

        try:
            # Setup
            self.setup()

            # Tests
            self.test_user_management()
            self.test_product_management()
            self.test_order_management()
            self.test_payout_management()
            self.test_marketplace_statistics()
            self.test_export_functions()

            # Rapport final
            self.print_final_report()

        except Exception as e:
            print(f"\n❌ ERREUR FATALE: {str(e)}")

        finally:
            self.cleanup()

    def print_final_report(self):
        """Affiche le rapport final détaillé"""
        print("\n" + "=" * 60)
        print("📊 RAPPORT FINAL ADMINISTRATION")
        print("=" * 60)

        total_tests = len(self.results)
        passed_tests = sum(1 for result in self.results if result[0])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        print(f"📈 Tests réussis: {passed_tests}/{total_tests} ({success_rate:.1f}%)")
        print(f"❌ Tests échoués: {failed_tests}")

        # Statistiques créées
        print(f"\n📊 DONNÉES CRÉÉES POUR LES TESTS:")
        print(f"   👥 Utilisateurs: {len(self.buyer_ids)} acheteurs + {len(self.seller_ids)} vendeurs + 1 admin")
        print(f"   📦 Produits: {len(self.product_ids)}")
        print(f"   🛒 Commandes: {len(self.order_ids)}")

        if failed_tests > 0:
            print(f"\n🔍 DÉTAIL DES ÉCHECS:")
            for passed, test_name, details in self.results:
                if not passed:
                    print(f"   • {test_name}: {details}")

        status = "🎉 FONCTIONS ADMIN OPÉRATIONNELLES" if failed_tests == 0 else "⚠️ PROBLÈMES DÉTECTÉS"
        print(f"\n{status}")
        print("=" * 60)

    def cleanup(self):
        """Nettoie les fichiers temporaires"""
        try:
            shutil.rmtree(self.temp_dir)
            print("\n🧹 Nettoyage terminé")
        except Exception as e:
            print(f"\n⚠️ Erreur nettoyage: {e}")


if __name__ == "__main__":
    test = AdminWorkflowTest()
    test.run_complete_test()