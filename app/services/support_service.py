from typing import Optional, List, Dict
from datetime import datetime
import random

from app.domain.repositories.ticket_repo import SupportTicketRepository


class SupportService:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.database_path = database_path
        self.repo = SupportTicketRepository(database_path)

    def create_ticket(self, user_id: int, subject: str, message: str) -> Optional[str]:
        from app.core.utils import generate_ticket_id
        ticket_id = generate_ticket_id(self.database_path)
        created = self.repo.create_ticket(user_id=user_id, ticket_id=ticket_id, subject=subject[:100], message=message[:2000])
        return ticket_id if created else None

    def list_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict]:
        return self.repo.list_user_tickets(user_id, limit)

