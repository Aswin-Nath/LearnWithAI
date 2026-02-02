from sqlalchemy import text
from app.core.database import engine
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_db():
    try:
        with engine.connect() as conn:
            conn.commit() # Ensure we start fresh
            
            # --- Update 'roadmap_phase_problems' table ---
            logger.info("Checking 'roadmap_phase_problems' table schema...")
            
            # Check for 'is_solved' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmap_phase_problems' AND column_name='is_solved'"
            ))
            if not result.fetchone():
                logger.info("Adding 'is_solved' column to 'roadmap_phase_problems'...")
                conn.execute(text("ALTER TABLE roadmap_phase_problems ADD COLUMN is_solved BOOLEAN DEFAULT FALSE NOT NULL"))
            else:
                logger.info("'is_solved' column already exists.")

            conn.commit()
            logger.info("Migration successful! Database schema is now up to date.")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        # conn.rollback() # Context manager handles rollback on exception usually, but safe to leave explicit or rely on auto
        
if __name__ == "__main__":
    migrate_db()
