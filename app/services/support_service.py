from typing import Optional, List, Dict
from datetime import datetime
import random

from app.domain.repositories.ticket_repo import SupportTicketRepository


class SupportService:
    def __init__(self, ticket_repo: SupportTicketRepository) -> None:
        self.repo = ticket_repo

    def create_ticket(self, user_id: int, subject: str, message: str, client_email: str = None) -> Optional[str]:
        from app.core.utils import generate_ticket_id
        from app.core.email_service import EmailService

        ticket_id = generate_ticket_id()
        created = self.repo.create_ticket(user_id=user_id, ticket_id=ticket_id, subject=subject[:100], message=message[:2000], client_email=client_email)

        if created and client_email:
            # Envoyer une notification email à l'admin
            email_service = EmailService()
            email_service.send_new_ticket_notification(
                ticket_id=ticket_id,
                user_id=user_id,
                subject=subject[:100],
                message=message[:2000],
                client_email=client_email
            )

        return ticket_id if created else None

    def list_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        return self.repo.list_user_tickets(user_id, limit)

