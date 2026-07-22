"""
Database Session Management (`src/backend/db/session.py`).

Provides async SQLAlchemy session factories and multi-document table initialization (`init_db`).
Supports local persistent SQLite (`data/gpr_workspace.db`) and cloud PostgreSQL (`DATABASE_URL`).
All system and terminal messages are strictly English.
"""

import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import inspect, text

try:
    from ..models.orm import Base as UniversalBase
except ImportError:
    from models.orm import Base as UniversalBase

try:
    from ..models import Base as LegacyBase
except ImportError:
    try:
        from models import Base as LegacyBase
    except ImportError:
        LegacyBase = None

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///data/gpr_workspace.db")

# Normalize cloud PostgreSQL connection URLs (SnapDeploy, Supabase, Neon, Railway, AWS RDS) for async SQLAlchemy (`asyncpg`)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgresql://") and "+asyncpg" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

if DATABASE_URL.startswith("sqlite"):
    os.makedirs("data", exist_ok=True)

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


def _ensure_lightweight_migrations(sync_conn):
    """Add columns required by newer app versions when an existing SQLite/Postgres DB is reused."""
    inspector = inspect(sync_conn)
    table_names = set(inspector.get_table_names())
    if "chunks" not in table_names:
        return
    chunk_columns = {column["name"] for column in inspector.get_columns("chunks")}
    if "metadata_json" not in chunk_columns:
        sync_conn.execute(text("ALTER TABLE chunks ADD COLUMN metadata_json TEXT DEFAULT '{}'"))


async def init_db():
    """Create all universal (`documents`, `chunks`, `chunk_connections`, `document_tables`) and legacy tables."""
    async with engine.begin() as conn:
        await conn.run_sync(UniversalBase.metadata.create_all)
        await conn.run_sync(_ensure_lightweight_migrations)
        if LegacyBase is not None and LegacyBase is not UniversalBase:
            await conn.run_sync(LegacyBase.metadata.create_all)


async def get_db():
    """FastAPI dependency yielding an active async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
