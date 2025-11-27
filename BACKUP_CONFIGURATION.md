# 💾 Configuration des Backups PostgreSQL

**Date :** 10 novembre 2025
**Objectif :** Sauvegardes automatiques quotidiennes de la base PostgreSQL vers Backblaze B2

---

## 📋 Vue d'Ensemble

### Fichiers Créés
- `app/tasks/backup_database.py` - Script de backup automatique
- `app/tasks/restore_database.py` - Script de restauration

### Fonctionnalités
- ✅ Backup quotidien automatique (pg_dump)
- ✅ Compression gzip (économie d'espace)
- ✅ Upload vers Backblaze B2
- ✅ Rétention 30 jours (nettoyage automatique)
- ✅ Notifications admin Telegram
- ✅ Restauration facile

---

## 🚀 Configuration Initiale

### Prérequis

1. **PostgreSQL client tools installés** :
   ```bash
   # macOS
   brew install postgresql

   # Ubuntu/Debian
   sudo apt-get install postgresql-client

   # Vérifier installation
   pg_dump --version
   pg_restore --version
   ```

2. **Variables d'environnement configurées** :
   - `PGHOST`
   - `PGPORT`
   - `PGDATABASE`
   - `PGUSER`
   - `PGPASSWORD`
   - `B2_KEY_ID`
   - `B2_APPLICATION_KEY`
   - `B2_BUCKET_NAME`

---

## 🔧 Configuration du Cronjob

### Option 1 : Cronjob Local (Développement)

```bash
# Ouvrir crontab
crontab -e

# Ajouter cette ligne (backup quotidien à 3h du matin)
0 3 * * * cd /Users/noricra/Python-bot && /usr/local/bin/python3 -m app.tasks.backup_database >> /Users/noricra/Python-bot/logs/backup.log 2>&1
```

**Note :** Remplacez `/Users/noricra/Python-bot` par votre chemin absolu.

### Option 2 : Railway (Production)

Railway ne supporte pas nativement les cronjobs. Solutions :

#### Solution A : Service Externe (Recommandé)

Utilisez un service comme **EasyCron** ou **cron-job.org** :

1. Créez un endpoint API dans votre app :
   ```python
   # Dans bot_mlt.py ou nouveau fichier
   @app.get("/admin/backup")
   async def trigger_backup(secret: str):
       if secret != os.getenv('BACKUP_SECRET'):
           raise HTTPException(403)

       # Run backup in background
       asyncio.create_task(run_backup_async())
       return {"status": "started"}
   ```

2. Configurez EasyCron pour appeler `https://votre-app.railway.app/admin/backup?secret=YOUR_SECRET` quotidiennement

#### Solution B : GitHub Actions (Gratuit)

Créez `.github/workflows/backup.yml` :

```yaml
name: Daily Database Backup

on:
  schedule:
    - cron: '0 3 * * *'  # 3 AM UTC daily
  workflow_dispatch:  # Allow manual trigger

jobs:
  backup:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          sudo apt-get install postgresql-client

      - name: Run backup
        env:
          PGHOST: ${{ secrets.PGHOST }}
          PGPORT: ${{ secrets.PGPORT }}
          PGDATABASE: ${{ secrets.PGDATABASE }}
          PGUSER: ${{ secrets.PGUSER }}
          PGPASSWORD: ${{ secrets.PGPASSWORD }}
          B2_KEY_ID: ${{ secrets.B2_KEY_ID }}
          B2_APPLICATION_KEY: ${{ secrets.B2_APPLICATION_KEY }}
          B2_BUCKET_NAME: ${{ secrets.B2_BUCKET_NAME }}
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
          ADMIN_USER_ID: ${{ secrets.ADMIN_USER_ID }}
        run: python -m app.tasks.backup_database
```

**Avantages :**
- ✅ Gratuit
- ✅ Logs disponibles dans GitHub Actions
- ✅ Peut être déclenché manuellement

---

## 📖 Utilisation

### Créer un Backup Manuellement

```bash
# Depuis le répertoire du projet
python -m app.tasks.backup_database
```

**Résultat :**
```
🚀 Starting database backup process...
🗄️ Creating database backup: backup_20251110_143020.sql
✅ Backup created successfully: 12.45 MB
🗜️ Compressing backup...
✅ Compressed: 2.34 MB (81.2% reduction)
☁️ Uploading backup to Backblaze B2...
✅ Backup uploaded to B2: backups/postgresql/backup_20251110_143020.sql.gz
🧹 Cleaning up backups older than 30 days...
✅ Deleted 2 old backups
✅ Database backup completed successfully
✅ Notification sent to admin
```

---

### Lister les Backups Disponibles

```bash
python -m app.tasks.restore_database --list
```

**Résultat :**
```
================================================================================
AVAILABLE BACKUPS
================================================================================
Filename                                 Size (MB)    Date
--------------------------------------------------------------------------------
backup_20251110_030000.sql.gz                2.34    2025-11-10 03:00:15
backup_20251109_030000.sql.gz                2.31    2025-11-09 03:00:12
backup_20251108_030000.sql.gz                2.28    2025-11-08 03:00:09
...
================================================================================
Total: 15 backups
Retention: 30 days
```

---

### Restaurer un Backup

#### Restaurer le Dernier Backup

```bash
python -m app.tasks.restore_database --restore latest
```

#### Restaurer un Backup Spécifique

```bash
python -m app.tasks.restore_database --restore backup_20251110_030000.sql.gz
```

**⚠️ IMPORTANT :** La restauration va **ÉCRASER** la base de données actuelle !

**Confirmation requise :**
```
============================================================
⚠️  WARNING: DATABASE RESTORE
============================================================
This will OVERWRITE your current PostgreSQL database!
All current data will be LOST!
============================================================

Type 'YES' to confirm restore: YES
```

**Skip confirmation (automation) :**
```bash
python -m app.tasks.restore_database --restore latest --force
```

---

## 🔍 Monitoring

### Logs de Backup

Les logs sont envoyés à :
1. **Console** (stdout)
2. **Fichier** : `logs/backup.log` (si configuré dans cronjob)
3. **Admin Telegram** (notification)

### Notification Admin

Après chaque backup, l'admin reçoit un message Telegram :

**✅ Succès :**
```
✅ Backup PostgreSQL Réussi

📅 Date : 2025-11-10 03:00:15
💾 Taille : 2.34 MB
☁️ Stockage : Backblaze B2
🔄 Rétention : 30 jours
```

**❌ Échec :**
```
❌ Backup PostgreSQL Échoué

📅 Date : 2025-11-10 03:00:15
⚠️ Action requise : Vérifier les logs

Commande manuelle :
`python -m app.tasks.backup_database`
```

---

## 🧪 Tests

### Test 1 : Backup Local

```bash
# Créer un backup de test
python -m app.tasks.backup_database

# Vérifier que le fichier a été uploadé sur B2
python -m app.tasks.restore_database --list

# Résultat attendu : Le nouveau backup apparaît dans la liste
```

### Test 2 : Restauration (Base de Test)

**⚠️ NE PAS FAIRE EN PRODUCTION !**

```bash
# 1. Créer une base de test
createdb -h localhost -U postgres test_restore

# 2. Modifier temporairement .env
PGDATABASE=test_restore

# 3. Restaurer un backup
python -m app.tasks.restore_database --restore latest --force

# 4. Vérifier que les tables existent
psql -h localhost -U postgres -d test_restore -c "\dt"

# 5. Supprimer la base de test
dropdb -h localhost -U postgres test_restore
```

### Test 3 : Cronjob

```bash
# Tester que le cronjob fonctionne
# (modifier temporairement pour exécution dans 5 minutes)
crontab -e

# Ajouter :
*/5 * * * * cd /path/to/Python-bot && python -m app.tasks.backup_database

# Attendre 5 minutes, vérifier les logs
tail -f logs/backup.log
```

---

## 📊 Coûts Backblaze B2

### Estimation

| Taille DB | Backup Compressé | 30 Jours | Coût/Mois |
|-----------|------------------|----------|-----------|
| 10 MB | 2 MB | 60 MB | $0.0003 |
| 100 MB | 20 MB | 600 MB | $0.003 |
| 1 GB | 200 MB | 6 GB | $0.03 |
| 10 GB | 2 GB | 60 GB | $0.30 |

**Tarif B2 :** $0.005/GB/mois

**Conclusion :** Très peu coûteux (< 1$/mois pour la plupart des cas)

---

## 🐛 Troubleshooting

### Erreur : "pg_dump: command not found"

**Cause :** PostgreSQL client tools non installés

**Solution :**
```bash
# macOS
brew install postgresql

# Ubuntu/Debian
sudo apt-get install postgresql-client

# Vérifier
which pg_dump
```

---

### Erreur : "connection refused"

**Cause :** Variables d'environnement incorrectes ou base inaccessible

**Solution :**
```bash
# Tester la connexion manuellement
psql -h $PGHOST -p $PGPORT -U $PGUSER -d $PGDATABASE

# Si erreur, vérifier .env
cat .env | grep PG
```

---

### Erreur : "Upload to B2 failed"

**Cause :** Credentials B2 invalides ou bucket inexistant

**Solution :**
```bash
# Tester connexion B2 en Python
python3 << EOF
from app.services.b2_storage_service import B2StorageService
b2 = B2StorageService()
print("B2 connection OK")
EOF
```

---

### Backups ne se suppriment pas après 30 jours

**Cause :** Timezone mismatch ou erreur dans cleanup

**Solution :**
```bash
# Exécuter cleanup manuellement
python3 << EOF
from app.tasks.backup_database import cleanup_old_backups
cleanup_old_backups()
EOF
```

---

## 🔐 Sécurité

### Bonnes Pratiques

1. **✅ Backups chiffrés** :
   - B2 supporte le chiffrement côté serveur (SSE)
   - Activez-le dans les paramètres du bucket

2. **✅ Credentials sécurisées** :
   - Ne jamais commit les credentials dans Git
   - Utiliser variables d'environnement

3. **✅ Accès limité** :
   - Limiter les permissions B2 au minimum nécessaire
   - Application Key avec accès au bucket uniquement

4. **✅ Rotation des credentials** :
   - Changer B2 Application Key tous les 90 jours

---

## 📈 Améliorations Futures

- [ ] Backup incrémental (économie d'espace)
- [ ] Chiffrement client-side avant upload
- [ ] Multiple destinations (B2 + AWS S3)
- [ ] Validation automatique des backups (restore test)
- [ ] Métriques Prometheus
- [ ] Alerting si backup échoue 2x consécutives

---

**Document créé le :** 10 novembre 2025
**Configuration par :** Claude Code (Sonnet 4.5)
