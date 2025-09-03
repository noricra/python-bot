import logging
from typing import Dict, Optional, List
import requests


logger = logging.getLogger(__name__)


class NowPaymentsClient:
    """Thin HTTP client for NOWPayments endpoints used by the bot."""

    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json",
        }

    def create_payment(self, amount_usd: float, pay_currency: str, order_id: str,
                       description: str, ipn_callback_url: Optional[str] = None) -> Optional[Dict]:
        if not self.api_key:
            logger.error("NOWPAYMENTS_API_KEY manquant!")
            return None
        payload = {
            "price_amount": float(amount_usd),
            "price_currency": "usd",
            "pay_currency": pay_currency.lower(),
            "order_id": order_id,
            "order_description": description,
        }
        if ipn_callback_url:
            payload["ipn_callback_url"] = ipn_callback_url
        try:
            logger.info(f"NOWPayments create_payment start order_id={order_id} pay_currency={pay_currency.lower()} price_usd={amount_usd}")
            response = requests.post(
                f"{self.BASE_URL}/payment",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            if response.status_code == 201:
                logger.info(f"NOWPayments create_payment success order_id={order_id} pay_currency={pay_currency.lower()}")
                return response.json()
            # Log détaillé en cas d'erreur
            err_text = response.text
            try:
                err_json = response.json()
            except Exception:
                err_json = None
            logger.error(f"NOWPayments create_payment failed order_id={order_id} pay_currency={pay_currency.lower()} status={response.status_code} body={err_text} json={err_json}")
            return None
        except Exception as exc:
            logger.error(f"NOWPayments create_payment exception order_id={order_id} pay_currency={pay_currency.lower()} error={exc}")
            return None

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        if not self.api_key:
            return None
        try:
            logger.info(f"NOWPayments get_payment payment_id={payment_id}")
            response = requests.get(
                f"{self.BASE_URL}/payment/{payment_id}",
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            if response.status_code == 200:
                return response.json()
            logger.error(f"NOWPayments get_payment failed payment_id={payment_id} status={response.status_code} body={response.text}")
            return None
        except Exception as exc:
            logger.error(f"NOWPayments get_payment exception payment_id={payment_id} error={exc}")
            return None

    def list_currencies(self) -> List[str]:
        if not self.api_key:
            return ["btc", "eth", "usdt", "usdc"]
        try:
            response = requests.get(
                f"{self.BASE_URL}/currencies",
                headers={"x-api-key": self.api_key},
                timeout=10,
            )
            if response.status_code == 200:
                data = response.json()
                currencies = data.get("currencies", [])
                main = ["btc", "eth", "usdt", "usdc", "bnb", "sol", "ltc", "xrp"]
                return [c for c in currencies if c in main]
            return ["btc", "eth", "usdt", "usdc"]
        except Exception:
            return ["btc", "eth", "usdt", "usdc"]

