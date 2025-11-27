"""
Automatic PostgreSQL Database Backup to Backblaze B2
Retains last 30 daily backups

Usage:
    python -m app.tasks.backup_database

Cronjob (daily at 3 AM):
    0 3 * * * cd /path/to/Python-bot && python -m app.tasks.backup_database
"""
import os
import sys
import subprocess
import gzip
import logging
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app.core import settings as core_settings
from app.services.b2_storage_service import B2StorageService

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Backup configuration
BACKUP_RETENTION_DAYS = 30
BACKUP_PREFIX = "backups/postgresql/"
BACKUP_TEMP_DIR = tempfile.gettempdir()


def create_database_backup() -> str:
    """
    Create PostgreSQL database backup using pg_dump.

    Returns:
        str: Path to compressed backup file

    Raises:
        Exception: If backup creation fails
    """
    try:
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"backup_{timestamp}.sql"
        backup_path = os.path.join(BACKUP_TEMP_DIR, backup_filename)
        compressed_path = f"{backup_path}.gz"

        logger.info(f"🗄️ Creating database backup: {backup_filename}")

        # Build pg_dump command
        pg_dump_cmd = [
            'pg_dump',
            '-h', core_settings.PGHOST,
            '-p', str(core_settings.PGPORT),
            '-U', core_settings.PGUSER,
            '-d', core_settings.PGDATABASE,
            '-F', 'c',  # Custom format (compressed)
            '-f', backup_path,
            '--no-password'  # Use PGPASSWORD env var
        ]

        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = core_settings.PGPASSWORD

        # Execute pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        if result.returncode != 0:
            error_msg = result.stderr or "Unknown error"
            raise Exception(f"pg_dump failed: {error_msg}")

        # Check if backup file was created
        if not os.path.exists(backup_path):
            raise Exception(f"Backup file not created: {backup_path}")

        backup_size = os.path.getsize(backup_path)
        logger.info(f"✅ Backup created successfully: {backup_size / 1024 / 1024:.2f} MB")

        # Compress backup with gzip
        logger.info("🗜️ Compressing backup...")
        with open(backup_path, 'rb') as f_in:
            with gzip.open(compressed_path, 'wb') as f_out:
                f_out.writelines(f_in)

        compressed_size = os.path.getsize(compressed_path)
        compression_ratio = (1 - compressed_size / backup_size) * 100
        logger.info(f"✅ Compressed: {compressed_size / 1024 / 1024:.2f} MB ({compression_ratio:.1f}% reduction)")

        # Remove uncompressed backup
        os.remove(backup_path)

        return compressed_path

    except subprocess.TimeoutExpired:
        logger.error("❌ Backup timeout (> 10 minutes)")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to create backup: {e}")
        raise


def upload_backup_to_b2(backup_path: str) -> bool:
    """
    Upload backup file to Backblaze B2.

    Args:
        backup_path: Path to compressed backup file

    Returns:
        bool: True if upload successful, False otherwise
    """
    try:
        logger.info("☁️ Uploading backup to Backblaze B2...")

        b2_service = B2StorageService()

        # Generate B2 key (path in bucket)
        backup_filename = os.path.basename(backup_path)
        b2_key = f"{BACKUP_PREFIX}{backup_filename}"

        # Upload to B2
        with open(backup_path, 'rb') as f:
            b2_service.s3_client.upload_fileobj(
                f,
                b2_service.bucket_name,
                b2_key
            )

        logger.info(f"✅ Backup uploaded to B2: {b2_key}")
        return True

    except Exception as e:
        logger.error(f"❌ Failed to upload backup to B2: {e}")
        return False


def cleanup_old_backups():
    """
    Delete backups older than BACKUP_RETENTION_DAYS from B2.
    """
    try:
        logger.info(f"🧹 Cleaning up backups older than {BACKUP_RETENTION_DAYS} days...")

        b2_service = B2StorageService()

        # List all backups
        response = b2_service.s3_client.list_objects_v2(
            Bucket=b2_service.bucket_name,
            Prefix=BACKUP_PREFIX
        )

        if 'Contents' not in response:
            logger.info("No backups found in B2")
            return

        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=BACKUP_RETENTION_DAYS)

        deleted_count = 0
        for obj in response['Contents']:
            key = obj['Key']
            last_modified = obj['LastModified']

            # Remove timezone info for comparison
            if last_modified.replace(tzinfo=None) < cutoff_date:
                logger.info(f"🗑️ Deleting old backup: {key} (modified: {last_modified})")

                b2_service.s3_client.delete_object(
                    Bucket=b2_service.bucket_name,
                    Key=key
                )

                deleted_count += 1

        if deleted_count > 0:
            logger.info(f"✅ Deleted {deleted_count} old backups")
        else:
            logger.info("✅ No old backups to delete")

    except Exception as e:
        logger.error(f"❌ Failed to cleanup old backups: {e}")


def send_backup_notification(success: bool, backup_size_mb: float = 0):
    """
    Send notification to admin about backup status.

    Args:
        success: Whether backup was successful
        backup_size_mb: Size of backup in MB
    """
    try:
        from telegram import Bot

        bot = Bot(token=core_settings.TELEGRAM_BOT_TOKEN)

        if success:
            message = f"""✅ **Backup PostgreSQL Réussi**

📅 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
💾 Taille : {backup_size_mb:.2f} MB
☁️ Stockage : Backblaze B2
🔄 Rétention : {BACKUP_RETENTION_DAYS} jours"""
        else:
            message = f"""❌ **Backup PostgreSQL Échoué**

📅 Date : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
⚠️ Action requise : Vérifier les logs

Commande manuelle :
`python -m app.tasks.backup_database`"""

        bot.send_message(
            chat_id=core_settings.ADMIN_USER_ID,
            text=message,
            parse_mode='Markdown'
        )

        logger.info("✅ Notification sent to admin")

    except Exception as e:
        logger.error(f"❌ Failed to send notification: {e}")


def main():
    """
    Main backup workflow:
    1. Create database backup (pg_dump)
    2. Compress backup (gzip)
    3. Upload to Backblaze B2
    4. Cleanup old backups
    5. Send notification to admin
    """
    backup_path = None
    success = False
    backup_size_mb = 0

    try:
        logger.info("🚀 Starting database backup process...")

        # Step 1: Create backup
        backup_path = create_database_backup()
        backup_size_mb = os.path.getsize(backup_path) / 1024 / 1024

        # Step 2: Upload to B2
        upload_success = upload_backup_to_b2(backup_path)

        if not upload_success:
            raise Exception("Upload to B2 failed")

        # Step 3: Cleanup old backups
        cleanup_old_backups()

        success = True
        logger.info("✅ Database backup completed successfully")

    except Exception as e:
        logger.error(f"❌ Database backup failed: {e}")
        success = False

    finally:
        # Cleanup temporary file
        if backup_path and os.path.exists(backup_path):
            try:
                os.remove(backup_path)
                logger.info(f"🗑️ Cleaned up temporary file: {backup_path}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup temp file: {e}")

        # Send notification
        send_backup_notification(success, backup_size_mb)

        # Exit with appropriate code
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
