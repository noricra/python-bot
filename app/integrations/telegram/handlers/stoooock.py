
    def create_payment(self, amount_usd: float, currency: str,
                       order_id: str) -> Optional[Dict]:
        """Crée un paiement NOWPayments (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().create_payment(amount_usd, currency, order_id)
        except Exception as e:
            logger.error(f"Erreur PaymentService.create_payment: {e}")
            return None

    def check_payment_status(self, payment_id: str) -> Optional[Dict]:
        """Vérifie le statut d'un paiement (via PaymentService)"""
        try:
            from app.services.payment_service import PaymentService
            return PaymentService().check_payment_status(payment_id)
        except Exception as e:
            logger.error(f"Erreur PaymentService.check_payment_status: {e}")
            return None
