"""
User Utilities - Fonctions utilitaires pour la gestion des utilisateurs
"""
from typing import Dict, Any, Optional
from app.domain.repositories.user_repo import UserRepository


def get_user_language(user_id: int, user_repo: UserRepository, user_state: Dict[str, Any] = None) -> str:
    """
    Récupère la langue utilisateur (état ou DB)

    Args:
        user_id: ID de l'utilisateur
        user_repo: Repository utilisateur
        user_state: État utilisateur optionnel

    Returns:
        str: Code langue ('fr' ou 'en')
    """
    # Priorité 1: État utilisateur en mémoire
    if user_state and 'lang' in user_state:
        return user_state['lang']

    # Priorité 2: Langue sauvegardée en DB
    user_data = user_repo.get_user(user_id)
    if user_data and user_data.get('language_code'):
        return user_data['language_code']

    # Défaut: français
    return 'fr'


# Fonctions mortes supprimées: format_user_display_name, is_user_admin, sanitize_user_input
# Aucune n'était appelée dans la codebase