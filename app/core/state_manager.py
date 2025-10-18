"""
State Manager - Gestion centralisée des états utilisateur
"""
from typing import Dict, Any, Optional
import logging
from app.core.settings import settings

logger = logging.getLogger(__name__)

class StateManager:
    """Gestionnaire centralisé des états utilisateur"""

    def __init__(self):
        self.user_states: Dict[int, Dict[str, Any]] = {}

    def get_state(self, user_id: int) -> Dict[str, Any]:
        """Récupère l'état complet d'un utilisateur"""
        return self.user_states.get(user_id, {})

    def get_state_value(self, user_id: int, key: str, default: Any = None) -> Any:
        """Récupère une valeur spécifique de l'état utilisateur"""
        user_state = self.get_state(user_id)
        return user_state.get(key, default)

    def update_state(self, user_id: int, **kwargs) -> None:
        """Met à jour l'état utilisateur avec les nouvelles valeurs"""
        if user_id not in self.user_states:
            self.user_states[user_id] = {}

        for key, value in kwargs.items():
            self.user_states[user_id][key] = value

        logger.debug(f"State updated for user {user_id}: {kwargs}")

    def reset_state(self, user_id: int, keep: Optional[set] = None) -> None:
        """Remet à zéro l'état utilisateur, optionnellement en gardant certaines clés"""
        if user_id not in self.user_states:
            return

        if keep:
            old_state = self.user_states[user_id]
            self.user_states[user_id] = {k: v for k, v in old_state.items() if k in keep}
        else:
            self.user_states[user_id] = {}

        logger.debug(f"State reset for user {user_id}, kept: {keep}")

    def reset_conflicting_states(self, user_id: int, keep: Optional[set] = None) -> None:
        """Remet à zéro les états conflictuels tout en gardant certaines clés"""
        conflicting_keys = set(settings.CONFLICTING_STATES)

        if user_id not in self.user_states:
            return

        keep_set = keep or set()
        user_state = self.user_states[user_id]

        # Supprimer tous les états conflictuels sauf ceux à garder
        for key in conflicting_keys:
            if key not in keep_set and key in user_state:
                del user_state[key]

        logger.debug(f"Conflicting states reset for user {user_id}, kept: {keep_set}")

    def is_user_in_state(self, user_id: int, state_key: str) -> bool:
        """Vérifie si un utilisateur est dans un état spécifique"""
        return self.get_state_value(user_id, state_key, False)

    # Utility methods removed - never used (10 lines removed)