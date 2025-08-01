from contextlib import asynccontextmanager
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.database import async_session_maker


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@asynccontextmanager
async def db_context() -> AsyncGenerator[AsyncSession, None]:
    generator = get_db()
    session = await anext(generator)
    try:
        yield session
    finally:
        await session.close()
