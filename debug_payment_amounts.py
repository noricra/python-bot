"""
Script de diagnostic des montants de paiement
Vérifie ce qui est envoyé à NOWPayments vs ce qui est reçu
"""
import psycopg2.extras
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection

def analyze_recent_orders():
    """Analyse les 10 dernières commandes pour comprendre les montants"""
    conn = get_postgresql_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    try:
        # Get recent orders with all payment details
        cursor.execute('''
            SELECT
                o.order_id,
                o.product_id,
                p.title as product_title,
                p.price_usd as product_price_usd,
                o.product_price_usd as order_product_price,
                o.payment_currency,
                o.nowpayments_id,
                o.payment_status,
                o.created_at
            FROM orders o
            LEFT JOIN products p ON p.product_id = o.product_id
            ORDER BY o.created_at DESC
            LIMIT 10
        ''')

        orders = cursor.fetchall()

        print("=" * 80)
        print("ANALYSE DES MONTANTS DE PAIEMENT")
        print("=" * 80)

        for order in orders:
            print(f"\n📦 ORDER: {order['order_id']}")
            print(f"   Produit: {order['product_title']}")
            print(f"   Prix produit (DB): ${order['product_price_usd']:.2f}")
            print(f"   Prix dans order: ${order['order_product_price']:.2f}")

            # Calculate expected amounts
            base_price = order['product_price_usd']
            platform_fee = round(base_price * 0.0278, 2)
            total_expected = round(base_price + platform_fee, 2)

            print(f"\n   💰 CALCUL ATTENDU:")
            print(f"      Base: ${base_price:.2f}")
            print(f"      Frais plateforme (2.78%): ${platform_fee:.2f}")
            print(f"      Total attendu: ${total_expected:.2f}")

            # Check if we can get NOWPayments data
            if order['nowpayments_id']:
                print(f"\n   🔍 NOWPayments ID: {order['nowpayments_id']}")
                print(f"      Monnaie: {order['payment_currency']}")
                print(f"      Statut: {order['payment_status']}")

                # Try to get actual payment amount from NOWPayments API
                try:
                    from app.integrations.nowpayments_client import NowPaymentsClient
                    from app.core import settings

                    client = NowPaymentsClient(settings.NOWPAYMENTS_API_KEY)
                    payment_info = client.get_payment(order['nowpayments_id'])

                    if payment_info:
                        print(f"\n   ✅ DONNÉES NOWPAYMENTS:")
                        print(f"      price_amount: ${payment_info.get('price_amount', 'N/A')}")
                        print(f"      pay_amount: {payment_info.get('pay_amount', 'N/A')} {payment_info.get('pay_currency', '')}")
                        print(f"      pay_currency: {payment_info.get('pay_currency', 'N/A')}")

                        # Calculate discrepancy
                        if payment_info.get('price_amount'):
                            nowpayments_amount = float(payment_info['price_amount'])
                            difference = total_expected - nowpayments_amount
                            percentage_loss = (difference / total_expected) * 100

                            print(f"\n   ⚠️  ÉCART:")
                            print(f"      Attendu: ${total_expected:.2f}")
                            print(f"      NOWPayments: ${nowpayments_amount:.2f}")
                            print(f"      Différence: ${difference:.2f} ({percentage_loss:.1f}%)")

                            if abs(difference) > 0.01:
                                print(f"      ❌ PROBLÈME DÉTECTÉ!")
                except Exception as e:
                    print(f"   ❌ Erreur récupération données NOWPayments: {e}")
            else:
                print(f"\n   ⚠️  Pas de NOWPayments ID (paiement non créé)")

            print("-" * 80)

        put_connection(conn)

    except Exception as e:
        put_connection(conn)
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

def check_nowpayments_fees():
    """Vérifie les frais NOWPayments officiels"""
    print("\n" + "=" * 80)
    print("FRAIS NOWPAYMENTS OFFICIELS")
    print("=" * 80)
    print("""
NOWPayments prélève automatiquement:
- 0.5% de frais de service minimum
- + Frais réseau variables selon la blockchain

Pour TON (Toncoin):
- Frais de service: ~0.5%
- Frais réseau: ~0.1-0.3 TON (variable)
- Total: peut atteindre 5-7% du montant

⚠️  PROBLÈME: Ces frais sont déduits du price_amount envoyé!

SOLUTION: Il faut soit:
1. Ajouter les frais NOWPayments au montant (complexe car variables)
2. Utiliser 'pay_amount' et laisser le client payer les frais réseau
3. Facturer 3-4% au lieu de 2.78% pour couvrir tous les frais
    """)

if __name__ == "__main__":
    print("🔍 Démarrage du diagnostic...\n")
    analyze_recent_orders()
    check_nowpayments_fees()

    print("\n" + "=" * 80)
    print("📊 RECOMMANDATION")
    print("=" * 80)
    print("""
Le problème vient probablement de:

1. **Frais NOWPayments non comptabilisés**
   Les frais NOWPayments (0.5% service + frais réseau) sont déduits
   du montant envoyé, réduisant ce que le vendeur reçoit.

2. **Solution immédiate:**
   Augmenter les frais plateforme de 2.78% à 4-5% pour couvrir:
   - 2.78% commission plateforme
   - ~0.5-2% frais NOWPayments

3. **Solution à long terme:**
   Utiliser l'API NOWPayments pour calculer dynamiquement le montant
   exact avec frais inclus avant de créer le paiement.

Exécutez ce script pour voir les détails de vos paiements récents.
    """)
