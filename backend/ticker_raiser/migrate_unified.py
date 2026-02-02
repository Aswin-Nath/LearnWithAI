import os
import sys
from sqlalchemy import create_engine, text

# Ensure we can import from app
sys.path.append(os.getcwd())

from app.core.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

def run_migration():
    with engine.connect() as conn:
        print("Starting migration...")
        trans = conn.begin()
        try:
            # 1. Drop old tables
            print("Dropping custom_test_cases...")
            conn.execute(text("DROP TABLE IF EXISTS custom_test_cases CASCADE;"))
            print("Dropping custom_problems...")
            conn.execute(text("DROP TABLE IF EXISTS custom_problems CASCADE;"))
            
            # 2. Add columns to problems
            print("Altering problems table...")
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT FALSE;"))
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS generation_topic VARCHAR;"))
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS generation_query TEXT;"))
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS editorial_markdown TEXT;"))
            conn.execute(text("ALTER TABLE problems ADD COLUMN IF NOT EXISTS canonical_code TEXT;"))
            
            # 3. Make created_by nullable (optional, mostly for flexibility)
            # Check if it is nullable first? Or just execute
            print("Altering created_by column...")
            conn.execute(text("ALTER TABLE problems ALTER COLUMN created_by DROP NOT NULL;"))
            
            trans.commit()
            print("Migration successful!")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    run_migration()
