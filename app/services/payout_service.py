from typing import Optional, List, Tuple

from app.domain.repositories.payout_repo import PayoutRepository


class PayoutService:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.repo = PayoutRepository(database_path)

    def create_payout(self, seller_user_id: int, order_ids: List[str], total_amount_sol: float) -> Optional[int]:
        return self.repo.insert_payout(seller_user_id, order_ids, total_amount_sol)

    def list_recent_for_seller(self, seller_user_id: int, limit: int = 10) -> List[Tuple]:
        return self.repo.list_recent_for_seller(seller_user_id, limit)

    def mark_all_pending_as_completed(self) -> bool:
        return self.repo.mark_all_pending_as_completed()

