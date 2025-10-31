#!/usr/bin/env python3
"""
Test script pour vérifier la migration PostgreSQL
"""
import psycopg2
import psycopg2.extras
from app.core.database_init import get_postgresql_connection

def test_connection():
    """Test de connexion PostgreSQL"""
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        # Test query
        cursor.execute("SELECT version()")
        result = cursor.fetchone()
        print(f"✅ Connexion PostgreSQL réussie!")
        print(f"   Version: {result['version']}")

        # Test tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        print(f"\n✅ Tables trouvées ({len(tables)}):")
        for table in tables:
            print(f"   - {table['table_name']}")

        # Test SELECT with RealDictCursor
        cursor.execute("SELECT COUNT(*) as total FROM users")
        result = cursor.fetchone()
        print(f"\n✅ Test RealDictCursor réussi!")
        print(f"   Nombre d'utilisateurs: {result['total']}")

        conn.close()
        return True

    except Exception as e:
        print(f"❌ Erreur: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Test de la base de données PostgreSQL\n")
    print("=" * 50)
    success = test_connection()
    print("=" * 50)
    if success:
        print("\n✅ Tous les tests ont réussi!")
    else:
        print("\n❌ Des erreurs ont été détectées")
