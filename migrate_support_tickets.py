"""
Migration script to create/update support_tickets table
"""
import psycopg2
from app.core.database_init import get_postgresql_connection

def migrate():
    """Create or update support_tickets table"""
    conn = get_postgresql_connection()
    cursor = conn.cursor()

    try:
        # Create support_tickets table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS support_tickets (
                id SERIAL PRIMARY KEY,
                ticket_id TEXT UNIQUE NOT NULL,
                user_id BIGINT NOT NULL,
                subject TEXT NOT NULL,
                message TEXT NOT NULL,
                client_email TEXT,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add client_email column if it doesn't exist (for existing tables)
        cursor.execute('''
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_name = 'support_tickets' AND column_name = 'client_email'
                ) THEN
                    ALTER TABLE support_tickets ADD COLUMN client_email TEXT;
                END IF;
            END $$;
        ''')

        conn.commit()
        print("Migration completed successfully!")
        print("- Table support_tickets created/verified")
        print("- Column client_email added/verified")

    except Exception as e:
        conn.rollback()
        print(f"Migration failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    migrate()
