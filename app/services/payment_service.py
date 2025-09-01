import logging
import time
from typing import Dict, Optional, List

from app.core import settings as core_settings
from app.integrations.nowpayments_client import NowPaymentsClient


logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self) -> None:
        self.client = NowPaymentsClient(core_settings.NOWPAYMENTS_API_KEY)
        self._fx_cache = {}
        self._currencies_cache = {}

    def create_payment(self, amount_usd: float, currency: str, order_id: str) -> Optional[Dict]:
        try:
            resp = self.client.create_payment(
                amount_usd=amount_usd,
                pay_currency=currency,
                order_id=order_id,
                description="Formation TechBot Marketplace",
                ipn_callback_url=core_settings.IPN_CALLBACK_URL,
            )
            if not resp:
                logger.error(f"PaymentService.create_payment returned None order_id={order_id} currency={currency} amount_usd={amount_usd}")
            return resp
        except Exception as e:
            logger.error(f"PaymentService.create_payment exception order_id={order_id} currency={currency} error={e}")
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

