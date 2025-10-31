#!/usr/bin/env python3
"""
Script de vérification complète de la migration PostgreSQL
"""
import os
import re
import subprocess

def check_sqlite_placeholders():
    """Vérifie qu'il n'y a plus de placeholders SQLite (?)"""
    print("🔍 Vérification des placeholders SQLite...")

    issues = []
    for root, dirs, files in os.walk('app'):
        # Skip __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                    for i, line in enumerate(lines, 1):
                        # Check for SQL placeholders with ?
                        if 'cursor.execute' in line or 'VALUES' in line or 'WHERE' in line:
                            # Look for ? not in comments or strings
                            if re.search(r'\s\?[\s,)]', line) and not line.strip().startswith('#'):
                                issues.append(f"{filepath}:{i} - {line.strip()}")

    if issues:
        print("❌ Placeholders SQLite trouvés:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ Aucun placeholder SQLite trouvé!")
        return True

def check_index_access():
    """Vérifie qu'il n'y a pas d'accès par index numérique"""
    print("\n🔍 Vérification des accès par index...")

    issues = []
    for root, dirs, files in os.walk('app'):
        dirs[:] = [d for d in dirs if d != '__pycache__']

        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    lines = content.split('\n')

                    for i, line in enumerate(lines, 1):
                        # Check for numeric index access with fetchone/fetchall
                        if 'fetchone()' in line or 'fetchall()' in line:
                            # Look for [0], [1], etc but not ['key']
                            if re.search(r'fetchone\(\)\[\d+\]|fetchall\(\)\[\d+\]', line):
                                issues.append(f"{filepath}:{i} - {line.strip()}")

    if issues:
        print("❌ Accès par index numérique trouvés:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ Tous les accès utilisent des clés de dictionnaire!")
        return True

def test_database_connection():
    """Test la connexion à la base de données"""
    print("\n🔍 Test de connexion PostgreSQL...")

    try:
        from app.core.database_init import get_postgresql_connection
        import psycopg2.extras

        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute("SELECT COUNT(*) as count FROM users")
        result = cursor.fetchone()
        conn.close()

        print(f"✅ Connexion PostgreSQL réussie! ({result['count']} utilisateurs)")
        return True
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def main():
    print("=" * 60)
    print("VÉRIFICATION DE LA MIGRATION POSTGRESQL")
    print("=" * 60)

    results = []

    results.append(("Placeholders SQLite", check_sqlite_placeholders()))
    results.append(("Accès par index", check_index_access()))
    results.append(("Connexion PostgreSQL", test_database_connection()))

    print("\n" + "=" * 60)
    print("RÉSUMÉ")
    print("=" * 60)

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("\n🎉 TOUTES LES VÉRIFICATIONS ONT RÉUSSI!")
        print("Le bot est prêt pour PostgreSQL!")
        return 0
    else:
        print("\n⚠️  CERTAINES VÉRIFICATIONS ONT ÉCHOUÉ")
        print("Veuillez corriger les problèmes ci-dessus.")
        return 1

if __name__ == "__main__":
    exit(main())
