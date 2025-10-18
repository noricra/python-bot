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


def format_user_display_name(user_data: Dict[str, Any]) -> str:
    """
    Formate le nom d'affichage d'un utilisateur

    Args:
        user_data: Données utilisateur

    Returns:
        str: Nom formaté pour affichage
    """
    if not user_data:
        return "Utilisateur inconnu"

    first_name = user_data.get('first_name', '')
    last_name = user_data.get('last_name', '')
    username = user_data.get('username', '')

    if first_name:
        if last_name:
            return f"{first_name} {last_name}"
        return first_name
    elif username:
        return f"@{username}"
    else:
        return f"User {user_data.get('user_id', '???')}"


def is_user_admin(user_id: int) -> bool:
    """
    Vérifie si un utilisateur est administrateur

    Args:
        user_id: ID utilisateur

    Returns:
        bool: True si admin
    """
    from app.core.settings import settings
    return user_id in settings.ADMIN_USER_IDS


def sanitize_user_input(text: str, max_length: int = 500) -> str:
    """
    Nettoie et limite la saisie utilisateur

    Args:
        text: Texte à nettoyer
        max_length: Longueur maximale

    Returns:
        str: Texte nettoyé
    """
    if not text:
        return ""

    # Supprime les caractères de contrôle et limite la longueur
    cleaned = ''.join(char for char in text if ord(char) >= 32 or char in '\n\t')
    return cleaned.strip()[:max_length]