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
            
            # --- 1. Update 'roadmaps' table ---
            logger.info("Checking 'roadmaps' table schema...")
            
            # Check for 'status' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmaps' AND column_name='status'"
            ))
            if not result.fetchone():
                logger.info("Adding 'status' column to 'roadmaps'...")
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN status VARCHAR(50) DEFAULT 'ACTIVE' NOT NULL"))
            
            # Check for 'current_phase_order' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmaps' AND column_name='current_phase_order'"
            ))
            if not result.fetchone():
                logger.info("Adding 'current_phase_order' column to 'roadmaps'...")
                conn.execute(text("ALTER TABLE roadmaps ADD COLUMN current_phase_order INTEGER DEFAULT 1 NOT NULL"))


            # --- 2. Update 'roadmap_phases' table ---
            logger.info("Checking 'roadmap_phases' table schema...")

            # Check for 'is_completed' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmap_phases' AND column_name='is_completed'"
            ))
            if not result.fetchone():
                logger.info("Adding 'is_completed' column to 'roadmap_phases'...")
                conn.execute(text("ALTER TABLE roadmap_phases ADD COLUMN is_completed BOOLEAN DEFAULT FALSE NOT NULL"))

            # Check for 'completed_at' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmap_phases' AND column_name='completed_at'"
            ))
            if not result.fetchone():
                logger.info("Adding 'completed_at' column to 'roadmap_phases'...")
                conn.execute(text("ALTER TABLE roadmap_phases ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE NULL"))


            # --- 3. Update 'roadmap_phase_problems' table ---
            logger.info("Checking 'roadmap_phase_problems' table schema...")
            
            # Check for 'match_reason' column
            result = conn.execute(text(
                "SELECT column_name FROM information_schema.columns WHERE table_name='roadmap_phase_problems' AND column_name='match_reason'"
            ))
            if not result.fetchone():
                logger.info("Adding 'match_reason' column to 'roadmap_phase_problems'...")
                conn.execute(text("ALTER TABLE roadmap_phase_problems ADD COLUMN match_reason TEXT NULL"))

            conn.commit()
            logger.info("Migration successful! Database schema is now up to date.")
            
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        conn.rollback()

if __name__ == "__main__":
    migrate_db()
