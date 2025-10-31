import logging
import time
import qrcode
import io
import base64
from typing import Dict, Optional, List
import requests

from app.core import settings as core_settings
from app.integrations.nowpayments_client import NowPaymentsClient


logger = logging.getLogger(__name__)


class PaymentService:
    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self) -> None:
        self.api_key = core_settings.NOWPAYMENTS_API_KEY
        self.client = NowPaymentsClient(core_settings.NOWPAYMENTS_API_KEY)
        self._fx_cache = {}
        self._currencies_cache = {}

    def _headers(self) -> Dict[str, str]:
        """Get headers for NOWPayments API requests"""
        return {
            "x-api-key": self.api_key,
            "Content-Type": "application/json"
        }

    def create_payment(self, amount_usd: float, pay_currency: str, order_id: str,
                       description: str, ipn_callback_url: Optional[str] = None,
                       seller_wallet_address: Optional[str] = None,
                       seller_payout_currency: Optional[str] = "usdttrc20") -> Optional[Dict]:
        """
        Create a comprehensive payment with QR code, exact amount, and split payment support.

        Args:
            amount_usd: Total price in USD
            pay_currency: Currency the customer will pay with
            order_id: Order ID
            description: Order description
            ipn_callback_url: IPN callback URL
            seller_wallet_address: Seller's wallet address (for split payment)
            seller_payout_currency: Currency for seller payout (default: usdttrc20)

        Returns:
            Enhanced payment data with commission info, or None if failed
        """
        if not self.api_key:
            logger.error("NOWPAYMENTS_API_KEY manquant!")
            return None

        if not self.client:
            logger.error("NOWPayments client not initialized")
            return None

        try:
            # Calculate commission (2.78%)
            commission_percent = core_settings.PLATFORM_COMMISSION_PERCENT
            commission_amount = amount_usd * (commission_percent / 100)
            seller_revenue = amount_usd - commission_amount

            logger.info(f"Payment split: total={amount_usd} USD, commission={commission_amount:.2f} USD ({commission_percent}%), seller={seller_revenue:.2f} USD")

            # Step 1: Get exact crypto amount using client
            exact_crypto_amount = self._get_exact_crypto_amount(amount_usd, pay_currency)
            if not exact_crypto_amount:
                logger.error(f"Failed to get exact crypto amount for {pay_currency}")
                return None

            # Step 2: Create payment using client with split payment support
            logger.info(f"Creating payment: order_id={order_id}, currency={pay_currency}, amount_usd={amount_usd}")

            payment_data = self.client.create_payment(
                amount_usd=amount_usd,
                pay_currency=pay_currency,
                order_id=order_id,
                description=description,
                ipn_callback_url=ipn_callback_url,
                payout_address=seller_wallet_address if seller_wallet_address else None,
                payout_currency=seller_payout_currency if seller_wallet_address else None
            )

            if not payment_data:
                logger.error(f"Payment creation failed for order {order_id}")
                return None

            # Step 3: Enhance payment data with QR code and details
            enhanced_payment = self._enhance_payment_data(payment_data, exact_crypto_amount)

            # Step 4: Add commission tracking info
            enhanced_payment['commission_info'] = {
                'commission_percent': commission_percent,
                'commission_amount_usd': commission_amount,
                'seller_revenue_usd': seller_revenue,
                'total_amount_usd': amount_usd
            }

            logger.info(f"Payment created successfully: order_id={order_id}, payment_id={enhanced_payment.get('payment_id')}")
            return enhanced_payment

        except Exception as exc:
            logger.error(f"Payment creation exception: order_id={order_id}, error={exc}")
            return None


    def check_payment_status(self, payment_id: str) -> Optional[Dict]:
        try:
            resp = self.client.get_payment(payment_id)
            if not resp:
                logger.error(f"PaymentService.check_payment_status got no data payment_id={payment_id}")
            return resp
        except Exception as e:
            logger.error(f"PaymentService.check_payment_status exception payment_id={payment_id} error={e}")
            return None

    def get_exchange_rate(self) -> float:
        try:
            now = time.time()
            hit = self._fx_cache.get('eur_usd')
            if hit and (now - hit['ts'] < 3600):
                return hit['value']

            import requests
            response = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10)
            if response.status_code == 200:
                val = response.json()['rates']['USD']
                self._fx_cache['eur_usd'] = {'value': val, 'ts': now}
                return val
            return 1.10
        except Exception:
            return self._fx_cache.get('eur_usd', {}).get('value', 1.10)

    def _get_exact_crypto_amount(self, amount_usd: float, pay_currency: str) -> Optional[float]:
        """Get exact crypto amount using NOWPayments estimate"""
        try:
            # For stablecoins pegged to USD, use 1:1 ratio
            if pay_currency.lower() in ['usdt', 'usdc', 'usdttrc20', 'usdterc20']:
                logger.info(f"Using 1:1 ratio for {pay_currency}: {amount_usd}")
                return amount_usd

            if self.client:
                estimate_data = self.client.get_estimate(amount_usd, "usd", pay_currency)
                if estimate_data:
                    return float(estimate_data.get('estimated_amount', 0))

            # Fallback to direct API call if client fails
            response = requests.get(
                f"{self.BASE_URL}/estimate",
                headers=self._headers(),
                params={
                    "amount": amount_usd,
                    "currency_from": "usd",
                    "currency_to": pay_currency.lower()
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return float(data.get('estimated_amount', 0))

            logger.error(f"Estimate API failed: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            logger.error(f"Error getting crypto estimate: {e}")
            return None

    def _enhance_payment_data(self, payment_data: Dict, exact_crypto_amount: float) -> Dict:
        """Enhance payment data with QR code, exact amount, and professional details"""
        try:
            # Add exact crypto amount
            payment_data['exact_crypto_amount'] = exact_crypto_amount
            payment_data['formatted_amount'] = f"{exact_crypto_amount:.8f}"

            # Generate QR code for payment address
            payment_address = payment_data.get('pay_address', '')
            if payment_address:
                qr_code_base64 = self._generate_qr_code(payment_address, exact_crypto_amount, payment_data.get('pay_currency', ''))
                payment_data['qr_code'] = qr_code_base64

            # Add professional payment details
            payment_data['payment_details'] = {
                'address': payment_address,
                'amount': exact_crypto_amount,
                'currency': payment_data.get('pay_currency', '').upper(),
                'network': payment_data.get('pay_currency', '').upper(),
                'expires_at': payment_data.get('created_at', ''),  # Add expiration logic if needed
                'payment_id': payment_data.get('payment_id', ''),
                'order_id': payment_data.get('order_id', '')
            }

            return payment_data

        except Exception as e:
            logger.error(f"Error enhancing payment data: {e}")
            return payment_data

    def _generate_qr_code(self, address: str, amount: float, currency: str) -> str:
        """Generate QR code for payment address with amount"""
        try:
            # Create payment URI for better UX
            if currency.lower() == 'btc':
                qr_data = f"bitcoin:{address}?amount={amount}"
            elif currency.lower() == 'eth':
                qr_data = f"ethereum:{address}?value={amount}"
            else:
                qr_data = f"{address}?amount={amount}"

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(qr_data)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()

            return img_str

        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return ""


    def get_available_currencies(self) -> List[str]:
        try:
            now = time.time()
            hit = self._currencies_cache.get('list')
            if hit and (now - hit['ts'] < 3600):
                return hit['value']
            val = self.client.list_currencies()
            self._currencies_cache['list'] = {'value': val, 'ts': now}
            return val
        except Exception:
            return self._currencies_cache.get('list', {}).get('value', ["btc", "eth", "usdt", "usdc"])

