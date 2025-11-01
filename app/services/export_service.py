"""
Service d'export de données en CSV
Permet aux vendeurs d'exporter leurs statistiques
"""

import csv
import io
import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ExportService:
    """Service pour exporter des données en CSV"""

    def export_seller_stats_to_csv(
        self,
        seller_user_id: int,
        seller_name: str,
        products: List[Dict],
        orders: List[Dict]
    ) -> io.BytesIO:
        """
        Exporte les statistiques vendeur en CSV

        Args:
            seller_user_id: ID du vendeur
            seller_name: Nom du vendeur
            products: Liste des produits
            orders: Liste des commandes

        Returns:
            BytesIO contenant le CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # En-tête du fichier
        writer.writerow(['# STATISTIQUES VENDEUR'])
        writer.writerow(['# Vendeur', seller_name])
        writer.writerow(['# ID Vendeur', seller_user_id])
        writer.writerow(['# Date export', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
        writer.writerow([])

        # ═══════════════════════════════════════════════════════
        # SECTION 1: RÉSUMÉ GLOBAL
        # ═══════════════════════════════════════════════════════
        writer.writerow(['=== RÉSUMÉ GLOBAL ==='])
        writer.writerow([])

        total_products = len(products)
        active_products = sum(1 for p in products if p.get('status') == 'active')
        total_sales = len([o for o in orders if o.get('payment_status') == 'completed'])
        total_revenue = sum(o.get('product_price_usd', 0) for o in orders if o.get('payment_status') == 'completed')
        total_commission = sum(o.get('platform_commission_usd', 0) for o in orders if o.get('payment_status') == 'completed')
        net_revenue = total_revenue - total_commission

        writer.writerow(['Métrique', 'Valeur'])
        writer.writerow(['Total produits', total_products])
        writer.writerow(['Produits actifs', active_products])
        writer.writerow(['Total ventes', total_sales])
        writer.writerow(['Revenus bruts (USD)', f'{total_revenue:.2f}'])
        writer.writerow(['Commission plateforme (USD)', f'{total_commission:.2f}'])
        writer.writerow(['Revenus nets (USD)', f'{net_revenue:.2f}'])
        writer.writerow([])

        # ═══════════════════════════════════════════════════════
        # SECTION 2: DÉTAIL PRODUITS
        # ═══════════════════════════════════════════════════════
        writer.writerow(['=== DÉTAIL PRODUITS ==='])
        writer.writerow([])

        writer.writerow([
            'ID Produit',
            'Titre',
            'Catégorie',
            'Prix (USD)',
            'Vues',
            'Ventes',
            'Revenus (USD)',
            'Note',
            'Avis',
            'Statut',
            'Date création'
        ])

        for product in products:
            product_id = product.get('product_id', '')
            title = product.get('title', '')
            category = product.get('category', '')
            price = product.get('price_usd', 0)
            views = product.get('views_count', 0)
            sales = product.get('sales_count', 0)

            # Calculer revenus réels pour ce produit
            product_revenue = sum(
                o.get('seller_revenue_usd', 0)
                for o in orders
                if o.get('product_id') == product_id and o.get('payment_status') == 'completed'
            )

            rating = product.get('rating', 0)
            reviews_count = product.get('reviews_count', 0)
            status = product.get('status', 'unknown')
            created_at = product.get('created_at', '')

            writer.writerow([
                product_id,
                title,
                category,
                f'{price:.2f}',
                views,
                sales,
                f'{product_revenue:.2f}',
                f'{rating:.1f}' if rating else 'N/A',
                reviews_count,
                status,
                created_at
            ])

        writer.writerow([])

        # ═══════════════════════════════════════════════════════
        # SECTION 3: HISTORIQUE VENTES
        # ═══════════════════════════════════════════════════════
        writer.writerow(['=== HISTORIQUE VENTES ==='])
        writer.writerow([])

        writer.writerow([
            'ID Commande',
            'ID Produit',
            'Titre Produit',
            'Prix (USD)',
            'Commission (USD)',
            'Revenu Net (USD)',
            'Crypto',
            'Statut',
            'Date création',
            'Date confirmation'
        ])

        for order in orders:
            order_id = order.get('order_id', '')
            product_id = order.get('product_id', '')

            # Trouver le titre du produit
            product = next((p for p in products if p.get('product_id') == product_id), None)
            product_title = product.get('title', 'Inconnu') if product else 'Inconnu'

            price = order.get('product_price_usd', 0)
            commission = order.get('platform_commission_usd', 0)
            net_revenue = order.get('seller_revenue_usd', 0)
            crypto = order.get('payment_currency', '')
            status = order.get('payment_status', '')
            created_at = order.get('created_at', '')
            completed_at = order.get('completed_at', '')

            writer.writerow([
                order_id,
                product_id,
                product_title,
                f'{price:.2f}',
                f'{commission:.2f}',
                f'{net_revenue:.2f}',
                crypto,
                status,
                created_at,
                completed_at if completed_at else 'En attente'
            ])

        writer.writerow([])

        # ═══════════════════════════════════════════════════════
        # SECTION 4: PERFORMANCE PAR CATÉGORIE
        # ═══════════════════════════════════════════════════════
        writer.writerow(['=== PERFORMANCE PAR CATÉGORIE ==='])
        writer.writerow([])

        # Agréger par catégorie
        category_stats = {}
        for product in products:
            category = product.get('category', 'Autre')
            if category not in category_stats:
                category_stats[category] = {
                    'products': 0,
                    'sales': 0,
                    'revenue': 0
                }

            category_stats[category]['products'] += 1
            category_stats[category]['sales'] += product.get('sales_count', 0)

            # Revenus pour ce produit
            product_id = product.get('product_id')
            product_revenue = sum(
                o.get('seller_revenue_usd', 0)
                for o in orders
                if o.get('product_id') == product_id and o.get('payment_status') == 'completed'
            )
            category_stats[category]['revenue'] += product_revenue

        writer.writerow(['Catégorie', 'Produits', 'Ventes', 'Revenus (USD)'])
        for category, stats in sorted(category_stats.items()):
            writer.writerow([
                category,
                stats['products'],
                stats['sales'],
                f"{stats['revenue']:.2f}"
            ])

        writer.writerow([])

        # ═══════════════════════════════════════════════════════
        # SECTION 5: TOP PRODUITS
        # ═══════════════════════════════════════════════════════
        writer.writerow(['=== TOP 10 PRODUITS (PAR REVENUS) ==='])
        writer.writerow([])

        # Calculer revenus par produit
        products_with_revenue = []
        for product in products:
            product_id = product.get('product_id')
            product_revenue = sum(
                o.get('seller_revenue_usd', 0)
                for o in orders
                if o.get('product_id') == product_id and o.get('payment_status') == 'completed'
            )
            products_with_revenue.append({
                'title': product.get('title', ''),
                'sales': product.get('sales_count', 0),
                'revenue': product_revenue,
                'views': product.get('views_count', 0),
                'conversion': (product.get('sales_count', 0) / product.get('views_count', 1) * 100) if product.get('views_count', 0) > 0 else 0
            })

        # Trier par revenus
        products_with_revenue.sort(key=lambda x: x['revenue'], reverse=True)

        writer.writerow(['Rang', 'Titre', 'Ventes', 'Revenus (USD)', 'Vues', 'Conversion (%)'])
        for i, product in enumerate(products_with_revenue[:10], 1):
            writer.writerow([
                i,
                product['title'],
                product['sales'],
                f"{product['revenue']:.2f}",
                product['views'],
                f"{product['conversion']:.2f}"
            ])

        # Convertir en BytesIO
        output.seek(0)
        bytes_output = io.BytesIO(output.getvalue().encode('utf-8'))
        bytes_output.seek(0)

        return bytes_output

    def export_orders_to_csv(self, orders: List[Dict]) -> io.BytesIO:
        """
        Exporte une liste de commandes en CSV

        Args:
            orders: Liste des commandes

        Returns:
            BytesIO contenant le CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # En-tête
        writer.writerow([
            'ID Commande',
            'ID Acheteur',
            'ID Vendeur',
            'ID Produit',
            'Prix (USD)',
            'Commission (USD)',
            'Revenu Vendeur (USD)',
            'Crypto',
            'Statut',
            'Date Création',
            'Date Confirmation'
        ])

        # Données
        for order in orders:
            writer.writerow([
                order.get('order_id', ''),
                order.get('buyer_user_id', ''),
                order.get('seller_user_id', ''),
                order.get('product_id', ''),
                f"{order.get('product_price_usd', 0):.2f}",
                f"{order.get('platform_commission_usd', 0):.2f}",
                f"{order.get('seller_revenue_usd', 0):.2f}",
                order.get('payment_currency', ''),
                order.get('payment_status', ''),
                order.get('created_at', ''),
                order.get('completed_at', '')
            ])

        output.seek(0)
        bytes_output = io.BytesIO(output.getvalue().encode('utf-8'))
        bytes_output.seek(0)

        return bytes_output

    def export_products_to_csv(self, products: List[Dict]) -> io.BytesIO:
        """
        Exporte une liste de produits en CSV

        Args:
            products: Liste des produits

        Returns:
            BytesIO contenant le CSV
        """
        output = io.StringIO()
        writer = csv.writer(output)

        # En-tête
        writer.writerow([
            'ID Produit',
            'ID Vendeur',
            'Titre',
            'Description',
            'Catégorie',
            'Prix (USD)',
            'Vues',
            'Ventes',
            'Note',
            'Nombre Avis',
            'Statut',
            'Date Création'
        ])

        # Données
        for product in products:
            writer.writerow([
                product.get('product_id', ''),
                product.get('seller_user_id', ''),
                product.get('title', ''),
                product.get('description', ''),
                product.get('category', ''),
                f"{product.get('price_usd', 0):.2f}",
                product.get('views_count', 0),
                product.get('sales_count', 0),
                f"{product.get('rating', 0):.1f}" if product.get('rating') else 'N/A',
                product.get('reviews_count', 0),
                product.get('status', ''),
                product.get('created_at', '')
            ])

        output.seek(0)
        bytes_output = io.BytesIO(output.getvalue().encode('utf-8'))
        bytes_output.seek(0)

        return bytes_output

    def generate_filename(self, export_type: str, identifier: Optional[str] = None) -> str:
        """
        Génère un nom de fichier pour l'export

        Args:
            export_type: Type d'export ('seller_stats', 'orders', 'products')
            identifier: Identifiant optionnel (seller_id, etc.)

        Returns:
            Nom de fichier formaté
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        if identifier:
            return f"{export_type}_{identifier}_{timestamp}.csv"
        else:
            return f"{export_type}_{timestamp}.csv"
