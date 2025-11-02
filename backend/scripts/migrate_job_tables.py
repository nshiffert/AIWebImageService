"""
Migration script to create generation_jobs and generation_tasks tables.
"""
import sys
import os

# Add parent directory to path to import from api module
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from api.db.database import engine
from api.db.models import Base, GenerationJob, GenerationTask

def run_migration():
    """Create the new job tracking tables."""
    print("Creating generation_jobs and generation_tasks tables...")

    # Create only the new tables
    GenerationJob.__table__.create(engine, checkfirst=True)
    GenerationTask.__table__.create(engine, checkfirst=True)

    print("✅ Migration complete!")
    print("  - generation_jobs table created")
    print("  - generation_tasks table created")

if __name__ == "__main__":
    run_migration()
