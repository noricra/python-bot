"""
Restore PostgreSQL Database from Backblaze B2 Backup

⚠️ WARNING: This will OVERWRITE the current database!

Usage:
    # List available backups
    python -m app.tasks.restore_database --list

    # Restore specific backup
    python -m app.tasks.restore_database --restore backup_20251110_030000.sql.gz

    # Restore latest backup
    python -m app.tasks.restore_database --restore latest
"""
import os
import sys
import subprocess
import gzip
import logging
import argparse
from datetime import datetime
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

BACKUP_PREFIX = "backups/postgresql/"
BACKUP_TEMP_DIR = tempfile.gettempdir()


def list_available_backups():
    """
    List all available backups in B2.

    Returns:
        list: List of backup objects with keys and timestamps
    """
    try:
        logger.info("📋 Listing available backups...")

        b2_service = B2StorageService()

        response = b2_service.s3_client.list_objects_v2(
            Bucket=b2_service.bucket_name,
            Prefix=BACKUP_PREFIX
        )

        if 'Contents' not in response:
            logger.info("No backups found in B2")
            return []

        backups = []
        for obj in response['Contents']:
            key = obj['Key']
            size_mb = obj['Size'] / 1024 / 1024
            last_modified = obj['LastModified']

            backups.append({
                'key': key,
                'filename': os.path.basename(key),
                'size_mb': size_mb,
                'date': last_modified
            })

        # Sort by date (newest first)
        backups.sort(key=lambda x: x['date'], reverse=True)

        logger.info(f"✅ Found {len(backups)} backups")

        return backups

    except Exception as e:
        logger.error(f"❌ Failed to list backups: {e}")
        return []


def download_backup_from_b2(backup_filename: str) -> str:
    """
    Download backup file from B2.

    Args:
        backup_filename: Name of backup file or 'latest'

    Returns:
        str: Path to downloaded file

    Raises:
        Exception: If download fails
    """
    try:
        b2_service = B2StorageService()

        # If 'latest', get the most recent backup
        if backup_filename == 'latest':
            backups = list_available_backups()
            if not backups:
                raise Exception("No backups available")

            backup_filename = backups[0]['filename']
            logger.info(f"📥 Downloading latest backup: {backup_filename}")

        else:
            logger.info(f"📥 Downloading backup: {backup_filename}")

        # Build B2 key
        b2_key = f"{BACKUP_PREFIX}{backup_filename}"

        # Download to temp directory
        local_path = os.path.join(BACKUP_TEMP_DIR, backup_filename)

        b2_service.s3_client.download_file(
            b2_service.bucket_name,
            b2_key,
            local_path
        )

        if not os.path.exists(local_path):
            raise Exception(f"Downloaded file not found: {local_path}")

        size_mb = os.path.getsize(local_path) / 1024 / 1024
        logger.info(f"✅ Backup downloaded: {size_mb:.2f} MB")

        return local_path

    except Exception as e:
        logger.error(f"❌ Failed to download backup: {e}")
        raise


def decompress_backup(compressed_path: str) -> str:
    """
    Decompress gzipped backup file.

    Args:
        compressed_path: Path to .gz file

    Returns:
        str: Path to decompressed file
    """
    try:
        logger.info("🗜️ Decompressing backup...")

        decompressed_path = compressed_path.replace('.gz', '')

        with gzip.open(compressed_path, 'rb') as f_in:
            with open(decompressed_path, 'wb') as f_out:
                f_out.write(f_in.read())

        if not os.path.exists(decompressed_path):
            raise Exception(f"Decompressed file not created: {decompressed_path}")

        size_mb = os.path.getsize(decompressed_path) / 1024 / 1024
        logger.info(f"✅ Decompressed: {size_mb:.2f} MB")

        return decompressed_path

    except Exception as e:
        logger.error(f"❌ Failed to decompress backup: {e}")
        raise


def restore_database(backup_path: str):
    """
    Restore PostgreSQL database using pg_restore.

    ⚠️ WARNING: This will overwrite the current database!

    Args:
        backup_path: Path to backup file

    Raises:
        Exception: If restore fails
    """
    try:
        logger.warning("⚠️ WARNING: About to overwrite current database!")
        logger.info(f"🗄️ Restoring database from: {os.path.basename(backup_path)}")

        # Build pg_restore command
        pg_restore_cmd = [
            'pg_restore',
            '-h', core_settings.PGHOST,
            '-p', str(core_settings.PGPORT),
            '-U', core_settings.PGUSER,
            '-d', core_settings.PGDATABASE,
            '--clean',  # Drop existing objects
            '--if-exists',  # Don't error on missing objects
            '--no-owner',  # Don't restore ownership
            '--no-acl',  # Don't restore access privileges
            backup_path
        ]

        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = core_settings.PGPASSWORD

        # Execute pg_restore
        result = subprocess.run(
            pg_restore_cmd,
            env=env,
            capture_output=True,
            text=True,
            timeout=600  # 10 minutes timeout
        )

        # pg_restore may return non-zero even on success (warnings)
        # Check stderr for actual errors
        if result.returncode != 0:
            logger.warning(f"pg_restore warnings/errors:\n{result.stderr}")

            # Check if errors are fatal
            if "ERROR" in result.stderr and "already exists" not in result.stderr:
                raise Exception(f"pg_restore failed: {result.stderr}")

        logger.info("✅ Database restored successfully")

    except subprocess.TimeoutExpired:
        logger.error("❌ Restore timeout (> 10 minutes)")
        raise
    except Exception as e:
        logger.error(f"❌ Failed to restore database: {e}")
        raise


def confirm_restore():
    """
    Ask user for confirmation before restoring.

    Returns:
        bool: True if user confirms, False otherwise
    """
    print("\n" + "="*60)
    print("⚠️  WARNING: DATABASE RESTORE")
    print("="*60)
    print("This will OVERWRITE your current PostgreSQL database!")
    print("All current data will be LOST!")
    print("="*60)
    print()

    response = input("Type 'YES' to confirm restore: ").strip()

    return response == 'YES'


def main():
    """
    Main restore workflow.
    """
    parser = argparse.ArgumentParser(description='Restore PostgreSQL database from B2 backup')
    parser.add_argument('--list', action='store_true', help='List available backups')
    parser.add_argument('--restore', type=str, help='Restore specific backup (filename or "latest")')
    parser.add_argument('--force', action='store_true', help='Skip confirmation prompt')

    args = parser.parse_args()

    # List backups
    if args.list:
        backups = list_available_backups()

        if not backups:
            print("No backups found")
            sys.exit(0)

        print("\n" + "="*80)
        print("AVAILABLE BACKUPS")
        print("="*80)
        print(f"{'Filename':<40} {'Size (MB)':<12} {'Date':<25}")
        print("-"*80)

        for backup in backups:
            print(f"{backup['filename']:<40} {backup['size_mb']:>11.2f} {backup['date']}")

        print("="*80)
        print(f"\nTotal: {len(backups)} backups")
        print(f"Retention: 30 days\n")

        sys.exit(0)

    # Restore backup
    if args.restore:
        # Confirm restore (unless --force)
        if not args.force:
            if not confirm_restore():
                print("\n❌ Restore cancelled by user")
                sys.exit(1)

        compressed_path = None
        decompressed_path = None

        try:
            # Step 1: Download from B2
            compressed_path = download_backup_from_b2(args.restore)

            # Step 2: Decompress
            decompressed_path = decompress_backup(compressed_path)

            # Step 3: Restore database
            restore_database(decompressed_path)

            print("\n" + "="*60)
            print("✅ DATABASE RESTORED SUCCESSFULLY")
            print("="*60)
            print(f"Backup: {args.restore}")
            print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("="*60 + "\n")

            sys.exit(0)

        except Exception as e:
            print(f"\n❌ Restore failed: {e}\n")
            sys.exit(1)

        finally:
            # Cleanup temp files
            for path in [compressed_path, decompressed_path]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                        logger.info(f"🗑️ Cleaned up: {path}")
                    except:
                        pass

    # No arguments provided
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
