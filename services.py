import time
import requests
from typing import List


class PricingService:
    def __init__(self, cache: dict):
        self.cache = cache

    def get_eur_usd(self) -> float:
        try:
            now = time.time()
            hit = self.cache.get('eur_usd')
            if hit and (now - hit['ts'] < 3600):
                return hit['value']
            r = requests.get("https://api.exchangerate-api.com/v4/latest/EUR", timeout=10)
            if r.status_code == 200:
                val = r.json()['rates']['USD']
                self.cache['eur_usd'] = {'value': val, 'ts': now}
                return val
            return 1.10
        except Exception:
            return self.cache.get('eur_usd', {}).get('value', 1.10)


class PaymentsService:
    def __init__(self, api_key: str, cache: dict):
        self.api_key = api_key
        self.cache = cache

    def get_currencies(self) -> List[str]:
        try:
            now = time.time()
            hit = self.cache.get('currencies')
            if hit and (now - hit['ts'] < 3600):
                return hit['value']
            if not self.api_key:
                return ['btc', 'eth', 'usdt', 'usdc']
            headers = {"x-api-key": self.api_key}
            r = requests.get("https://api.nowpayments.io/v1/currencies", headers=headers, timeout=10)
            if r.status_code == 200:
                currencies = r.json()['currencies']
                allow = ['btc', 'eth', 'usdt', 'usdc', 'bnb', 'sol', 'ltc', 'xrp']
                val = [c for c in currencies if c in allow]
                self.cache['currencies'] = {'value': val, 'ts': now}
                return val
            return ['btc', 'eth', 'usdt', 'usdc']
        except Exception:
            return self.cache.get('currencies', {}).get('value', ['btc', 'eth', 'usdt', 'usdc'])

    def create_payment(self, amount_usd: float, currency: str, order_id: str):
        try:
            if not self.api_key:
                return None
            headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
            payload = {
                "price_amount": float(amount_usd),
                "price_currency": "usd",
                "pay_currency": currency.lower(),
                "order_id": order_id,
                "order_description": "Formation TechBot Marketplace"
            }
            r = requests.post("https://api.nowpayments.io/v1/payment", headers=headers, json=payload, timeout=30)
            return r.json() if r.status_code == 201 else None
        except Exception:
            return None

    def get_payment_status(self, payment_id: str):
        try:
            if not self.api_key:
                return None
            headers = {"x-api-key": self.api_key}
            r = requests.get(f"https://api.nowpayments.io/v1/payment/{payment_id}", headers=headers, timeout=10)
            return r.json() if r.status_code == 200 else None
        except Exception:
            return None

