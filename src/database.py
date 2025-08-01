import uuid

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config import settings

async_engine = create_async_engine(
    settings.postgress_connection_string,
    poolclass=NullPool,
    echo=True,
    # pool_size=16, # Tests not working with this (have to test on DEV)
    # max_overflow=128,# Tests not working with this (have to test on DEV)
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4()}__",
    },
)

async_session_maker = async_sessionmaker(async_engine, expire_on_commit=False)
