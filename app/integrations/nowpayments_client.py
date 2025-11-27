import logging
from typing import Dict, Optional, List
import httpx


logger = logging.getLogger(__name__)


class NowPaymentsClient:
    """Comprehensive async HTTP client for NOWPayments API integration."""

    BASE_URL = "https://api.nowpayments.io/v1"

    def __init__(self, api_key: Optional[str]) -> None:
        self.api_key = api_key
        if not api_key:
            logger.warning("NOWPayments API key not provided")

    def _headers(self) -> Dict[str, str]:
        return {
            "x-api-key": self.api_key or "",
            "Content-Type": "application/json",
        }

    async def get_estimate(self, amount: float, currency_from: str, currency_to: str) -> Optional[Dict]:
        """Get exact crypto amount estimation"""
        if not self.api_key:
            logger.error("API key required for estimate")
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/estimate",
                    headers=self._headers(),
                    params={
                        "amount": amount,
                        "currency_from": currency_from.lower(),
                        "currency_to": currency_to.lower()
                    },
                    timeout=10.0
                )

                if response.status_code == 200:
                    return response.json()

                logger.error(f"Get estimate failed: {response.status_code} - {response.text}")
                return None

        except Exception as e:
            logger.error(f"Get estimate exception: {e}")
            return None

    async def create_payment(self, amount_usd: float, pay_currency: str, order_id: str,
                       description: str, ipn_callback_url: Optional[str] = None) -> Optional[Dict]:
        """
        Create a payment - ALL funds go to main wallet (no split payment)
        Supported currencies: btc, eth, sol, usdtsol, usdcsol
        """
        if not self.api_key:
            logger.error("NOWPAYMENTS_API_KEY manquant!")
            return {"error": "API_KEY_MISSING"}

        # Accept BTC, ETH, SOL natives + Solana stablecoins only
        pay_curr_lower = pay_currency.lower()
        allowed_currencies = ['btc', 'eth', 'sol', 'usdtsol', 'usdcsol']

        if pay_curr_lower not in allowed_currencies:
            logger.error(f"Currency {pay_currency} not supported. Only btc, eth, sol, usdtsol, usdcsol allowed.")
            return {"error": "CURRENCY_NOT_SUPPORTED", "message": "Only BTC, ETH, SOL, USDT(Solana), USDC(Solana) are accepted"}

        # CRITICAL: Always use "usd" as price_currency to avoid crypto2crypto classification
        # This ensures the transaction is treated as "crypto" (0.5% fees) instead of "crypto2crypto" (1% fees)
        # The product price is in USD (fiat), the customer pays in crypto (pay_currency)
        price_currency = "usd"

        payload = {
            "price_amount": float(amount_usd),
            "price_currency": price_currency,  # Always "usd" for fiat-based pricing
            "pay_currency": pay_curr_lower,    # Crypto the customer pays with
            "order_id": order_id,
            "order_description": description,
        }

        # For USDT Solana: Force payout in same currency to avoid conversion
        # payout_currency tells NOWPayments what crypto we want to receive (settlement)
        # NOTE: USDCSOL excluded because no wallet configured in dashboard
        stablecoins_with_wallet = ['usdtsol']  # Only USDT has wallet configured
        if pay_curr_lower in stablecoins_with_wallet:
            payload["payout_currency"] = pay_curr_lower
            logger.info(f"Adding payout_currency={pay_curr_lower} to force same-currency settlement")
        elif pay_curr_lower == 'usdcsol':
            logger.info(f"Skipping payout_currency for USDCSOL (no wallet configured, will use main wallet)")

        if ipn_callback_url:
            payload["ipn_callback_url"] = ipn_callback_url

        # NO SPLIT PAYMENT - All funds go to main wallet configured in NOWPayments dashboard
        try:
            import json
            logger.info(f"NOWPayments create_payment start order_id={order_id} pay_currency={pay_currency.lower()} price_usd={amount_usd}")
            logger.info(f"🔍 PAYLOAD SENT TO NOWPAYMENTS: {json.dumps(payload, indent=2)}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.BASE_URL}/payment",
                    headers=self._headers(),
                    json=payload,
                    timeout=30.0,
                )

                if response.status_code == 201:
                    response_data = response.json()
                    logger.info(f"✅ RESPONSE FROM NOWPAYMENTS: {json.dumps(response_data, indent=2)}")
                    logger.info(f"NOWPayments create_payment success order_id={order_id} pay_currency={pay_currency.lower()}")
                    return response_data

                # Log détaillé en cas d'erreur
                err_text = response.text
                try:
                    err_json = response.json()
                    error_code = err_json.get('code', 'UNKNOWN_ERROR')
                    error_message = err_json.get('message', err_text)
                except Exception:
                    err_json = None
                    error_code = f"HTTP_{response.status_code}"
                    error_message = err_text

                logger.error(f"NOWPayments create_payment failed order_id={order_id} pay_currency={pay_currency.lower()} status={response.status_code} body={err_text} json={err_json}")

                # Return error details instead of None for better handling
                return {
                    "error": error_code,
                    "error_message": error_message,
                    "status_code": response.status_code,
                    "currency": pay_currency.lower()
                }
        except Exception as exc:
            logger.error(f"NOWPayments create_payment exception order_id={order_id} pay_currency={pay_currency.lower()} error={exc}")
            return {"error": "EXCEPTION", "error_message": str(exc)}

    async def get_payment(self, payment_id: str) -> Optional[Dict]:
        if not self.api_key:
            return None
        try:
            logger.info(f"NOWPayments get_payment payment_id={payment_id}")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/payment/{payment_id}",
                    headers={"x-api-key": self.api_key},
                    timeout=10.0,
                )
                if response.status_code == 200:
                    return response.json()
                logger.error(f"NOWPayments get_payment failed payment_id={payment_id} status={response.status_code} body={response.text}")
                return None
        except Exception as exc:
            logger.error(f"NOWPayments get_payment exception payment_id={payment_id} error={exc}")
            return None

    def list_currencies(self) -> List[str]:
        """Return accepted currencies: BTC, ETH, SOL, USDT(Solana), USDC(Solana)"""
        return ["btc", "eth", "sol", "usdtsol", "usdcsol"]

    async def get_all_solana_currencies(self) -> List[str]:
        """Diagnostic: List all Solana-related currencies from NOWPayments API"""
        if not self.api_key:
            return []
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/currencies",
                    headers={"x-api-key": self.api_key},
                    timeout=10.0
                )
                if response.status_code == 200:
                    all_currencies = response.json().get("currencies", [])
                    # Filter for Solana-related currencies
                    sol_currencies = [c for c in all_currencies if 'sol' in c.lower() or 'spl' in c.lower()]
                    logger.info(f"🔍 Solana currencies available: {sol_currencies}")
                    return sol_currencies
                else:
                    logger.error(f"Failed to fetch currencies: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Exception fetching currencies: {e}")
            return []

