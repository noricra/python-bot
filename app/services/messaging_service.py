from typing import Optional, List, Dict

from app.domain.repositories.messaging_repo import MessagingRepository


class MessagingService:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.repo = MessagingRepository(database_path)

    def start_or_get_ticket(self, buyer_user_id: int, order_id: str, seller_user_id: int, subject: str) -> Optional[str]:
        return self.repo.get_or_create_ticket(buyer_user_id, order_id, seller_user_id, subject)

    def post_user_message(self, ticket_id: str, user_id: int, message: str) -> bool:
        return self.repo.insert_message(ticket_id, user_id, 'user', message)

    def post_seller_message(self, ticket_id: str, seller_user_id: int, message: str) -> bool:
        return self.repo.insert_message(ticket_id, seller_user_id, 'seller', message)

    def post_admin_message(self, ticket_id: str, admin_user_id: int, message: str) -> bool:
        return self.repo.insert_message(ticket_id, admin_user_id, 'admin', message)

    def list_recent_messages(self, ticket_id: str, limit: int = 10) -> List[Dict]:
        return self.repo.list_messages(ticket_id, limit)

    def set_status(self, ticket_id: str, status: str) -> bool:
        return self.repo.set_ticket_status(ticket_id, status)

    def get_participants(self, ticket_id: str) -> Optional[Dict]:
        return self.repo.get_ticket_participants(ticket_id)

    def escalate(self, ticket_id: str, admin_user_id: int) -> bool:
        return self.repo.escalate_ticket(ticket_id, admin_user_id)

    def list_recent_tickets(self, limit: int = 10) -> List[Dict]:
        return self.repo.list_recent_tickets(limit)

    def get_ticket(self, ticket_id: str) -> Optional[Dict]:
        return self.repo.get_ticket(ticket_id)

