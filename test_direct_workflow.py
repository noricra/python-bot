#!/usr/bin/env python3
"""
Test rapide pour vérifier que buy_menu() saute le menu intermédiaire
et va directement à browse_categories()
"""

def test_buy_menu_redirects():
    """Vérifie que buy_menu() appelle browse_categories() directement"""
    print("🔍 Test du workflow direct...")

    try:
        # Read buy_handlers.py
        with open('app/integrations/telegram/handlers/buy_handlers.py', 'r') as f:
            content = f.read()

        # Find buy_menu function
        import re
        buy_menu_match = re.search(
            r'async def buy_menu\(.*?\):(.*?)(?=\n    async def|\nclass |\Z)',
            content,
            re.DOTALL
        )

        if not buy_menu_match:
            print("❌ Fonction buy_menu() non trouvée")
            return False

        buy_menu_code = buy_menu_match.group(1)

        # Check it calls browse_categories
        if 'await self.browse_categories(bot, query, lang)' in buy_menu_code:
            print("✅ buy_menu() appelle browse_categories() directement")
        else:
            print("❌ buy_menu() n'appelle pas browse_categories()")
            return False

        # Check old code is commented
        if 'buy_menu_keyboard' in buy_menu_code and '# keyboard = buy_menu_keyboard(lang)' in buy_menu_code:
            print("✅ Ancien code buy_menu_keyboard commenté")
        else:
            print("⚠️ Ancien code non commenté (mais pas critique)")

        # Check browse_categories back button points to back_main
        browse_match = re.search(
            r'async def browse_categories\(.*?\):(.*?)(?=\n    async def|\nclass |\Z)',
            content,
            re.DOTALL
        )

        if browse_match:
            browse_code = browse_match.group(1)
            if "callback_data='back_main'" in browse_code and 'Retour' in browse_code:
                print("✅ browse_categories() a bouton Retour → back_main")
            else:
                print("⚠️ browse_categories() bouton Retour à vérifier")

        print("\n✅ WORKFLOW DIRECT IMPLÉMENTÉ")
        print("📱 Flow: /start → Acheter → Catégories → Carousel")
        return True

    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_buy_menu_redirects()
    exit(0 if success else 1)
