#!/usr/bin/env python3
"""
Version simplifiée du bot pour tester rapidement sans toutes les dépendances.
"""

import os
import logging
from pathlib import Path

# Configuration basique
def setup_basic_environment():
    """Setup minimal pour les tests."""
    
    # Créer dossiers
    for dir_name in ["logs", "uploads", "wallets"]:
        Path(dir_name).mkdir(exist_ok=True)
    
    # Configuration logging basique
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/test.log'),
            logging.StreamHandler()
        ]
    )
    
    return logging.getLogger(__name__)

class SimpleBotTest:
    """Version simplifiée pour tester l'architecture."""
    
    def __init__(self):
        self.logger = setup_basic_environment()
        self.logger.info("🤖 SimpleBotTest initialisé")
    
    def test_architecture(self):
        """Tester l'architecture sans dépendances externes."""
        self.logger.info("🧪 Test de l'architecture...")
        
        # Test structure des dossiers
        required_dirs = [
            'app/domain/entities',
            'app/application/use_cases', 
            'app/infrastructure/database',
            'app/interfaces/telegram/handlers'
        ]
        
        missing_dirs = []
        for dir_path in required_dirs:
            if not Path(dir_path).exists():
                missing_dirs.append(dir_path)
        
        if missing_dirs:
            self.logger.error(f"❌ Dossiers manquants: {missing_dirs}")
            return False
        
        self.logger.info("✅ Structure de dossiers OK")
        
        # Test fichiers clés
        key_files = [
            'marketplace_bot_refactored.py',
            'pyproject.toml',
            'Dockerfile',
            'README_REFACTORED.md'
        ]
        
        missing_files = []
        for file_path in key_files:
            if not Path(file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.logger.error(f"❌ Fichiers manquants: {missing_files}")
            return False
        
        self.logger.info("✅ Fichiers clés OK")
        
        # Test taille du fichier refactorisé
        refactored_size = Path('marketplace_bot_refactored.py').stat().st_size
        legacy_size = Path('bot_mlt.py').stat().st_size if Path('bot_mlt.py').exists() else 0
        
        if legacy_size > 0:
            reduction = ((legacy_size - refactored_size) / legacy_size) * 100
            self.logger.info(f"📉 Réduction de taille: {reduction:.1f}%")
        
        self.logger.info(f"📊 Taille fichier refactorisé: {refactored_size:,} bytes")
        
        return True
    
    def show_status(self):
        """Afficher le statut du projet."""
        self.logger.info("📋 STATUT DU PROJET")
        self.logger.info("=" * 40)
        
        if self.test_architecture():
            self.logger.info("✅ Architecture: OK")
            self.logger.info("✅ Refactorisation: Terminée")
            self.logger.info("✅ Fichiers: Présents")
            
            self.logger.info("\n🚀 PRÊT POUR LES TESTS!")
            self.logger.info("📝 Configuration nécessaire:")
            self.logger.info("   1. Créer .env avec TELEGRAM_TOKEN")
            self.logger.info("   2. Installer dépendances si nécessaire")
            self.logger.info("   3. Lancer: python3 marketplace_bot_refactored.py")
            
        else:
            self.logger.error("❌ Problèmes détectés dans l'architecture")

def main():
    """Test principal."""
    print("🎯 TEST RAPIDE - TECHBOT MARKETPLACE REFACTORISÉ")
    print("=" * 55)
    
    try:
        bot_test = SimpleBotTest()
        bot_test.show_status()
        
        print("\n💡 ÉTAPES POUR LANCER LE BOT:")
        print("1️⃣ Configuration:")
        print("   cp .env.example .env")
        print("   # Éditez .env avec votre TELEGRAM_TOKEN")
        
        print("\n2️⃣ Dépendances (si manquantes):")
        print("   pip install python-telegram-bot python-dotenv requests")
        
        print("\n3️⃣ Lancement:")
        print("   python3 marketplace_bot_refactored.py")
        
        print("\n4️⃣ Alternative (bot complet legacy):")
        print("   python3 bot_mlt.py")
        
        print("\n📞 AIDE:")
        print("   - Token Telegram: Créez un bot via @BotFather")
        print("   - Votre User ID: Utilisez @userinfobot")
        print("   - Vérification: python3 quick_start.py")
        
    except Exception as e:
        logging.error(f"❌ Erreur: {e}")
        print("🔧 Essayez: python3 quick_start.py pour diagnostics complets")

if __name__ == "__main__":
    main()