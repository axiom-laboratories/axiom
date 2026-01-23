import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import sys
sys.path.append(os.path.join(os.getcwd(), 'puppeteer'))
from agent_service.db import Base, DATABASE_URL

async def migrate():
    print(f"Connecting to Database: {DATABASE_URL}")
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("Applying Schema Changes...")
        
        # 1. Create New Tables (Signature, ScheduledJob)
        # run_sync calls Metadata.create_all which only creates missing tables
        await conn.run_sync(Base.metadata.create_all)
        print("New tables created (if missing).")
        
        # 2. Alter Job Table (Add scheduled_job_id)
        # We need to check if column exists first or just use IF NOT EXISTS logic handled by SQL usually, 
        # but standard SQL ALTER TABLE ADD COLUMN IF NOT EXISTS is Postgres 9.6+ (we are on 15).
        
        try:
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS scheduled_job_id VARCHAR;"))
            print("'scheduled_job_id' column added to 'jobs' table.")
        except Exception as e:
            print(f"Column add warning (might already exist): {e}")

        try:
             await conn.execute(text("ALTER TABLE scheduled_jobs ADD COLUMN IF NOT EXISTS signature_payload TEXT;"))
             print("'signature_payload' column added to 'scheduled_jobs' table.")
        except Exception as e:
             print(f"Column add warning (might already exist): {e}")

        # 3. Alter Node Table (v0.8 Concurrency)
        try:
            # SQLite doesn't support IF NOT EXISTS in ADD COLUMN until newer versions, but Postgres does.
            # Catching error is safe.
            await conn.execute(text("ALTER TABLE nodes ADD COLUMN concurrency_limit INTEGER DEFAULT 5;"))
            print("'concurrency_limit' column added to 'nodes' table.")
        except Exception as e:
            print(f"Column add warning (concurrency_limit): {e}")

        try:
            await conn.execute(text("ALTER TABLE nodes ADD COLUMN job_memory_limit VARCHAR DEFAULT '512m';"))
            print("'job_memory_limit' column added to 'nodes' table.")
        except Exception as e:
            print(f"Column add warning (job_memory_limit): {e}")

    await engine.dispose()
    print("Migration Complete.")

if __name__ == "__main__":
    # Ensure we load env vars if needed, but db.py usually handles defaults.
    # We might need to set DATABASE_URL env var if it's not default.
    # In Docker compose it is set. Locally we might rely on default or .env
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(migrate())
