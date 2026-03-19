import asyncio
import json
import os
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from agent_service.db import User, Base, init_db
from agent_service.auth import get_password_hash

async def bootstrap():
    db_url = os.getenv("DATABASE_URL", "postgresql+asyncpg://puppet:masterpassword@db/puppet_db")
    engine = create_async_engine(db_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        result = await session.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin_pwd = os.getenv("ADMIN_PASSWORD", "admin123")
            admin_user = User(
                username="admin",
                password_hash=get_password_hash(admin_pwd),
            )
            session.add(admin_user)
            await session.commit()
            print(f"Manual Bootstrap: Created admin user with password from env")
        else:
            print("Manual Bootstrap: Admin user already exists")

if __name__ == "__main__":
    asyncio.run(bootstrap())
