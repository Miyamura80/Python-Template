"""
Database connection and session management
"""

from contextlib import contextmanager
from typing import Generator

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from loguru import logger as log

from common import global_config

# Database engine
engine = create_engine(
    global_config.database_uri,
    pool_pre_ping=True,
    pool_recycle=300,
    echo=False,  # Set to True for SQL query logging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency to get a database session.

    Yields:
        Database session
    """
    db_session = SessionLocal()
    try:
        yield db_session
    except Exception as e:
        if isinstance(e, HTTPException) and e.status_code == 402:
            log.warning(f"Database session raised HTTP 402: {e.detail}")
        else:
            log.error(f"Database session error: {e}")
        db_session.rollback()
        raise
    finally:
        db_session.close()


@contextmanager
def use_db_session() -> Generator[Session, None, None]:
    """
    Context manager to use a database session.
    """
    db_session = SessionLocal()
    yield db_session
    db_session.close()


def create_db_session() -> Session:
    """
    Create a new database session.

    Returns:
        Database session
    """
    return SessionLocal()


def close_db_session(db_session: Session) -> None:
    """
    Close a database session.

    Args:
        db_session: Database session to close
    """
    try:
        db_session.close()
    except Exception as e:
        log.error(f"Error closing database session: {e}")
