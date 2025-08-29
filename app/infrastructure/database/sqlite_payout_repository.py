"""SQLite payout repository - simplified version."""

from typing import Optional, List
from app.domain.entities import Payout
from app.application.interfaces import PayoutRepositoryInterface

class SqlitePayoutRepository(PayoutRepositoryInterface):
    def __init__(self, database_path: Optional[str] = None):
        self.database_path = database_path
    
    async def create(self, payout: Payout) -> bool:
        return True
    
    async def get_by_id(self, payout_id: str) -> Optional[Payout]:
        return None
    
    async def get_by_seller(self, seller_id: int) -> List[Payout]:
        return []
    
    async def get_pending_payouts(self) -> List[Payout]:
        return []
    
    async def update(self, payout: Payout) -> bool:
        return True