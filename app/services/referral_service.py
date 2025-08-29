from typing import List, Optional
import random

from app.domain.repositories.referral_repo import ReferralRepository


class ReferralService:
    def __init__(self, database_path: Optional[str] = None) -> None:
        self.repo = ReferralRepository(database_path)

    def list_all_codes(self) -> List[str]:
        defaults = self.repo.list_default_codes()
        partners = self.repo.list_partner_codes()
        return defaults + partners

    def choose_random(self) -> Optional[str]:
        codes = self.list_all_codes()
        return random.choice(codes) if codes else None

    def set_partner_code_for_user(self, user_id: int, partner_code: str) -> bool:
        return self.repo.set_user_partner_code(user_id, partner_code)

