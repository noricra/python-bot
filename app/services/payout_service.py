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

    def get_pending_payouts(self, limit: int = None) -> List:
        """Get pending payouts"""
        return self.repo.get_pending_payouts(limit)

    def get_all_payouts(self) -> List:
        """Get all payouts"""
        return self.repo.get_all_payouts()

    def mark_all_payouts_paid(self) -> int:
        """Mark all pending payouts as paid and return count"""
        # Get count first
        pending = self.repo.get_pending_payouts()
        count = len(pending)
        # Mark as completed
        self.repo.mark_all_pending_as_completed()
        return count

