# -*- coding: utf-8 -*-
"""
Database connection manager for CloudSQL
Supports both CloudSQL (production) and SQLite (local)
"""

import os
import logging
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker
)
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from utils.secrets import get_secret

logger = logging.getLogger("Database")

# SQLAlchemy Base
Base = declarative_base()

# Global engine and session maker
_engine: Optional[AsyncEngine] = None
_async_session_maker: Optional[async_sessionmaker] = None


def get_database_url() -> str:
    """
    Get database URL based on environment

    Returns:
        Database connection URL
    """
    environment = os.getenv("ENVIRONMENT", "development")

    if environment == "production":
        # CloudSQL connection for production
        db_user = get_secret("DB_USER", required=False) or "mytrade"
        db_pass = get_secret("DB_PASSWORD", required=True)
        db_name = get_secret("DB_NAME", required=False) or "mytrade"

        # CloudSQL connection name format: project:region:instance
        connection_name = get_secret("CLOUDSQL_CONNECTION_NAME", required=False)

        if connection_name:
            # Use Unix socket for CloudSQL
            db_socket_dir = os.getenv("DB_SOCKET_DIR", "/cloudsql")
            cloud_sql_connection_name = connection_name

            url = (
                f"postgresql+asyncpg://{db_user}:{db_pass}"
                f"@/{db_name}?host={db_socket_dir}/{cloud_sql_connection_name}"
            )
            logger.info(f"Using CloudSQL connection: {connection_name}")
        else:
            # Fallback to direct TCP connection
            db_host = get_secret("DB_HOST", required=False) or "localhost"
            db_port = get_secret("DB_PORT", required=False) or "5432"

            url = (
                f"postgresql+asyncpg://{db_user}:{db_pass}"
                f"@{db_host}:{db_port}/{db_name}"
            )
            logger.info(f"Using PostgreSQL TCP connection: {db_host}")

    else:
        # SQLite for local development
        db_path = os.getenv("SQLITE_PATH", "/tmp/mytrade.db")
        url = f"sqlite+aiosqlite:///{db_path}"
        logger.info(f"Using SQLite: {db_path}")

    return url


async def init_database(echo: bool = False) -> AsyncEngine:
    """
    Initialize database engine and create tables

    Args:
        echo: Whether to echo SQL statements

    Returns:
        Database engine
    """
    global _engine, _async_session_maker

    if _engine is not None:
        logger.info("Database already initialized")
        return _engine

    logger.info("Initializing database...")

    # Get database URL
    database_url = get_database_url()

    # Create async engine with optimized connection pooling
    if "postgresql" in database_url:
        # PostgreSQL / CloudSQL - Optimized pooling
        _engine = create_async_engine(
            database_url,
            echo=echo,
            # Connection pool settings
            pool_size=10,              # Base connection pool size (increased from 5)
            max_overflow=20,           # Additional connections when pool is full
            pool_timeout=30,           # Timeout waiting for connection from pool
            pool_recycle=3600,         # Recycle connections after 1 hour (prevent stale)
            pool_pre_ping=True,        # Verify connections before using
            # Query execution settings
            connect_args={
                "statement_cache_size": 100,  # Cache prepared statements
                "prepared_statement_cache_size": 100,
                "command_timeout": 60,         # Query timeout (60 seconds)
                "server_settings": {
                    "application_name": "MyTrade",
                    "jit": "off"               # Disable JIT compilation for faster small queries
                }
            }
        )
        logger.info("✓ PostgreSQL connection pool: size=10, max_overflow=20, recycle=3600s")

    elif "sqlite" in database_url:
        # SQLite - No pooling needed
        _engine = create_async_engine(
            database_url,
            echo=echo,
            poolclass=NullPool,
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )
        logger.info("✓ SQLite connection: no pooling (NullPool)")

    else:
        # Fallback
        _engine = create_async_engine(
            database_url,
            echo=echo,
            pool_pre_ping=True
        )

    # Create session maker
    _async_session_maker = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # Create tables
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    logger.info("✓ Database initialized successfully")
    return _engine


async def close_database():
    """Close database connections"""
    global _engine, _async_session_maker

    if _engine:
        await _engine.dispose()
        _engine = None
        _async_session_maker = None
        logger.info("✓ Database connections closed")


def get_pool_status() -> dict:
    """
    Get connection pool status for monitoring

    Returns:
        Dictionary with pool statistics
    """
    if _engine is None:
        return {"status": "not_initialized"}

    pool = _engine.pool

    # Check if pool exists (not NullPool)
    if pool is None or pool.__class__.__name__ == "NullPool":
        return {
            "status": "no_pooling",
            "pool_type": "NullPool"
        }

    # Get pool statistics
    return {
        "status": "active",
        "pool_type": pool.__class__.__name__,
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total_connections": pool.size() + pool.overflow(),
    }


def get_engine() -> AsyncEngine:
    """Get database engine"""
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first")
    return _engine


def get_session_maker() -> async_sessionmaker:
    """Get session maker"""
    if _async_session_maker is None:
        raise RuntimeError("Database not initialized. Call init_database() first")
    return _async_session_maker


@asynccontextmanager
async def get_db_session(auto_retry: bool = True, max_retries: int = 3) -> AsyncGenerator[AsyncSession, None]:
    """
    Get database session (async context manager) with automatic retry

    Args:
        auto_retry: Enable automatic retry on connection errors
        max_retries: Maximum retry attempts

    Usage:
        async with get_db_session() as session:
            result = await session.execute(query)
    """
    import asyncio
    from sqlalchemy.exc import DBAPIError, OperationalError

    session_maker = get_session_maker()

    retries = 0
    last_error = None

    while retries <= (max_retries if auto_retry else 0):
        try:
            async with session_maker() as session:
                try:
                    yield session
                    await session.commit()
                    return  # Success - exit retry loop
                except (DBAPIError, OperationalError) as e:
                    await session.rollback()
                    # Connection errors - retry
                    if auto_retry and retries < max_retries:
                        logger.warning(f"Database connection error, retrying... ({retries + 1}/{max_retries}): {e}")
                        last_error = e
                        retries += 1
                        await asyncio.sleep(2 ** retries)  # Exponential backoff
                        continue
                    else:
                        logger.error(f"Database session error: {e}")
                        raise
                except Exception as e:
                    await session.rollback()
                    logger.error(f"Database session error: {e}")
                    raise
                finally:
                    await session.close()

        except Exception as e:
            if auto_retry and retries < max_retries:
                logger.warning(f"Session creation failed, retrying... ({retries + 1}/{max_retries}): {e}")
                last_error = e
                retries += 1
                await asyncio.sleep(2 ** retries)
            else:
                raise

    # If we get here, all retries failed
    if last_error:
        logger.error(f"Database session failed after {max_retries} retries")
        raise last_error


class DatabaseManager:
    """Database manager for easier access"""

    def __init__(self):
        self.engine: Optional[AsyncEngine] = None
        self.session_maker: Optional[async_sessionmaker] = None

    async def initialize(self, echo: bool = False):
        """Initialize database"""
        self.engine = await init_database(echo=echo)
        self.session_maker = get_session_maker()

    async def close(self):
        """Close database"""
        await close_database()

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session"""
        if self.session_maker is None:
            raise RuntimeError("Database not initialized")

        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error: {e}")
                raise
            finally:
                await session.close()


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager() -> DatabaseManager:
    """Get database manager singleton"""
    global _db_manager
    if _db_manager is None:
        _db_manager = DatabaseManager()
    return _db_manager