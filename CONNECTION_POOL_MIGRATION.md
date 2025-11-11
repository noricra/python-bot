# 🔌 Connection Pool Migration Guide

**Date :** 10 novembre 2025
**Objectif :** Migrer tout le code pour utiliser le connection pool PostgreSQL

---

## 📊 Problème Résolu

### Avant (Sans Pool)
```python
def get_user(user_id):
    conn = get_postgresql_connection()  # Nouvelle connexion à chaque appel
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()  # Ferme la connexion (coûteux)
    return user
```

**Conséquences :**
- ❌ 100 appels = 100 nouvelles connexions TCP
- ❌ Railway limite : 20-100 connexions max
- ❌ Erreur : `FATAL: too many connections`

### Après (Avec Pool)
```python
def get_user(user_id):
    conn = get_postgresql_connection()  # Réutilise une connexion du pool
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        conn.commit()
        return user
    except Exception as e:
        conn.rollback()
        raise
    finally:
        put_connection(conn)  # Retourne la connexion au pool (réutilisable)
```

**Avantages :**
- ✅ 10 connexions dans le pool, réutilisées
- ✅ 1000 appels = 10 connexions max
- ✅ Pas d'erreur "too many connections"

---

## 🚀 Fichiers Modifiés

### ✅ Déjà Migré

1. **app/core/db_pool.py** - Connection pool implementation
2. **app/core/db_helpers.py** - Helper functions and decorators
3. **app/core/database_init.py** - Updated to use pool
4. **bot_mlt.py** - Pool initialization at startup

### ⏳ À Migrer (20 fichiers)

| Fichier | Priorité | Statut |
|---------|----------|--------|
| app/core/db.py | 🔴 HAUTE | ⏳ À faire |
| app/core/utils.py | 🔴 HAUTE | ⏳ À faire |
| app/domain/repositories/user_repo.py | 🔴 HAUTE | ⏳ À faire |
| app/domain/repositories/product_repo.py | 🔴 HAUTE | ⏳ À faire |
| app/domain/repositories/order_repo.py | 🔴 HAUTE | ⏳ À faire |
| app/domain/repositories/review_repo.py | 🟠 MOYENNE | ⏳ À faire |
| app/domain/repositories/payout_repo.py | 🟠 MOYENNE | ⏳ À faire |
| app/domain/repositories/ticket_repo.py | 🟠 MOYENNE | ⏳ À faire |
| app/domain/repositories/messaging_repo.py | 🟠 MOYENNE | ⏳ À faire |
| app/services/product_service.py | 🔴 HAUTE | ⏳ À faire |
| app/services/seller_service.py | 🔴 HAUTE | ⏳ À faire |
| app/services/image_sync_service.py | 🟡 BASSE | ⏳ À faire |
| app/integrations/ipn_server.py | 🔴 HAUTE | ⏳ À faire |
| app/integrations/telegram/app_builder.py | 🟠 MOYENNE | ⏳ À faire |
| app/integrations/telegram/handlers/buy_handlers.py | 🔴 HAUTE | ⏳ À faire |
| app/integrations/telegram/handlers/sell_handlers.py | 🔴 HAUTE | ⏳ À faire |
| app/integrations/telegram/handlers/admin_handlers.py | 🟠 MOYENNE | ⏳ À faire |
| app/integrations/telegram/handlers/seller_analytics_enhanced.py | 🟡 BASSE | ⏳ À faire |
| app/tasks/cleanup_deleted_products.py | 🟡 BASSE | ⏳ À faire |

---

## 📝 Patterns de Migration

### Pattern 1 : Fonction Simple (Recommandé)

**Avant :**
```python
def get_user(user_id):
    conn = get_postgresql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user
```

**Après :**
```python
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection

def get_user(user_id):
    conn = None
    try:
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        conn.commit()  # Toujours commit même pour SELECT
        return user
    except Exception as e:
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            put_connection(conn)  # CRITIQUE: Retourne au pool
```

---

### Pattern 2 : Avec Decorator (Plus propre)

**Avant :**
```python
def update_user_email(user_id, new_email):
    conn = get_postgresql_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET email = %s WHERE user_id = %s",
        (new_email, user_id)
    )
    conn.commit()
    conn.close()
```

**Après :**
```python
from app.core.db_helpers import with_db_connection

@with_db_connection
def update_user_email(conn, user_id, new_email):
    # conn est automatiquement injecté par le decorator
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET email = %s WHERE user_id = %s",
        (new_email, user_id)
    )
    conn.commit()
    # Pas besoin de put_connection(), le decorator le fait automatiquement
```

---

### Pattern 3 : Helper Functions (Le plus simple)

**Avant :**
```python
def get_all_sellers():
    conn = get_postgresql_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE is_seller = TRUE")
    sellers = cursor.fetchall()
    conn.close()
    return sellers
```

**Après :**
```python
from app.core.db_helpers import execute_query, execute_dict_query

def get_all_sellers():
    # Méthode 1: Retourne tuples
    return execute_query(
        "SELECT * FROM users WHERE is_seller = TRUE",
        fetch_all=True
    )

    # Méthode 2: Retourne dicts (recommandé)
    return execute_dict_query(
        "SELECT * FROM users WHERE is_seller = TRUE",
        fetch_all=True
    )
```

---

### Pattern 4 : Transactions (Plusieurs requêtes)

**Avant :**
```python
def create_order_and_update_stock(order_data):
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO orders (...) VALUES (...)")
        cursor.execute("UPDATE products SET sales_count = sales_count + 1")
        conn.commit()
    except:
        conn.rollback()
        raise
    finally:
        conn.close()
```

**Après :**
```python
from app.core.db_helpers import TransactionContext

def create_order_and_update_stock(order_data):
    with TransactionContext() as (conn, cursor):
        cursor.execute("INSERT INTO orders (...) VALUES (...)")
        cursor.execute("UPDATE products SET sales_count = sales_count + 1")
        # Commit automatique si pas d'erreur
        # Rollback automatique si erreur
        # Connection retournée au pool automatiquement
```

---

### Pattern 5 : Méthodes de Classe (Repositories)

**Avant :**
```python
class UserRepository:
    def get_user(self, user_id):
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user

    def update_user(self, user_id, data):
        conn = get_postgresql_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET ... WHERE user_id = %s", (..., user_id))
        conn.commit()
        conn.close()
```

**Après (Option 1 - Manuel) :**
```python
from app.core.database_init import get_postgresql_connection
from app.core.db_pool import put_connection

class UserRepository:
    def get_user(self, user_id):
        conn = None
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            user = cursor.fetchone()
            conn.commit()
            return user
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                put_connection(conn)

    def update_user(self, user_id, data):
        conn = None
        try:
            conn = get_postgresql_connection()
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET ... WHERE user_id = %s", (..., user_id))
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                put_connection(conn)
```

**Après (Option 2 - Decorator, recommandé) :**
```python
from app.core.db_helpers import with_db_connection

class UserRepository:
    @with_db_connection
    def get_user(self, conn, user_id):
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = cursor.fetchone()
        conn.commit()
        return user

    @with_db_connection
    def update_user(self, conn, user_id, data):
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET ... WHERE user_id = %s", (..., user_id))
        conn.commit()
```

---

## 🎯 Checklist de Migration

Pour chaque fichier :

- [ ] Ajouter les imports nécessaires :
  ```python
  from app.core.db_pool import put_connection
  # ou
  from app.core.db_helpers import with_db_connection, execute_query
  ```

- [ ] Entourer chaque utilisation de `get_postgresql_connection()` avec try/finally :
  ```python
  conn = None
  try:
      conn = get_postgresql_connection()
      # ... code ...
  except Exception as e:
      if conn:
          conn.rollback()
      raise
  finally:
      if conn:
          put_connection(conn)
  ```

- [ ] OU utiliser le decorator `@with_db_connection` pour les fonctions

- [ ] OU utiliser les helpers `execute_query()`, `execute_dict_query()` pour les requêtes simples

- [ ] Remplacer tous les `conn.close()` par `put_connection(conn)` dans finally

- [ ] Supprimer les `conn.close()` en dehors de finally (laissez only finally gérer)

- [ ] Tester la fonction après migration

---

## 🧪 Tests de Validation

### Test 1 : Vérifier que le pool est initialisé

```python
from app.core.db_pool import get_pool_status

status = get_pool_status()
print(status)
# {'initialized': True, 'min_connections': 2, 'max_connections': 10}
```

### Test 2 : Vérifier qu'une connexion est retournée au pool

```python
from app.core.db_pool import get_connection, put_connection

conn1 = get_connection()
print(f"Connection 1: {id(conn1)}")
put_connection(conn1)

conn2 = get_connection()
print(f"Connection 2: {id(conn2)}")  # Devrait être le même ID que conn1
put_connection(conn2)
```

### Test 3 : Test de charge (simuler 100 requêtes)

```python
import concurrent.futures
from app.domain.repositories.user_repo import UserRepository

repo = UserRepository()

def test_query(i):
    try:
        user = repo.get_user(5229892870)
        return f"Query {i}: OK"
    except Exception as e:
        return f"Query {i}: ERROR - {e}"

# 100 requêtes simultanées
with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
    results = list(executor.map(test_query, range(100)))

print("\n".join(results))
# Toutes devraient réussir (avant la migration, ça échouerait après 20-100 requêtes)
```

---

## 📊 Impact Attendu

| Métrique | Avant Pool | Après Pool | Amélioration |
|----------|-----------|------------|--------------|
| Connexions max simultanées | 100+ | 10 | **-90%** |
| Latence connexion | 50-100ms | 1-2ms | **-95%** |
| Erreurs "too many connections" | Fréquent | Jamais | **100%** |
| Scalabilité (req/min) | ~300 | ~3000+ | **+900%** |

---

## 🚨 Points d'Attention

1. **TOUJOURS retourner la connexion au pool** :
   ```python
   finally:
       if conn:
           put_connection(conn)
   ```

2. **NE PAS appeler `conn.close()` directement** :
   ```python
   # ❌ INCORRECT
   conn.close()

   # ✅ CORRECT
   put_connection(conn)
   ```

3. **Toujours utiliser try/finally** :
   ```python
   # ❌ INCORRECT (si erreur avant put_connection, connexion perdue)
   conn = get_postgresql_connection()
   # ... code ...
   put_connection(conn)

   # ✅ CORRECT
   conn = None
   try:
       conn = get_postgresql_connection()
       # ... code ...
   finally:
       if conn:
           put_connection(conn)
   ```

4. **Commit même pour les SELECT** :
   ```python
   # ✅ Toujours commit pour nettoyer l'état de la transaction
   conn.commit()
   ```

---

## 📞 Support

En cas de problème avec la migration :
1. Vérifier les logs : chercher "Connection pool"
2. Vérifier le pool status : `get_pool_status()`
3. Vérifier qu'il n'y a pas de `conn.close()` dans le code

---

**Document généré le :** 10 novembre 2025
**Migration par :** Claude Code (Sonnet 4.5)
