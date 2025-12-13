from contextlib import contextmanager
from fastapi import HTTPException
from sqlalchemy.orm import Session
from loguru import logger
import time
import signal
from src.db.database import SessionLocal


@contextmanager
def db_transaction(db: Session, timeout_seconds: int = 300):
    """
    Context manager to wrap database operations in a transaction.
    Commits on success; rolls back on exception.
    Includes timeout protection to prevent long-running transactions.

    Args:
        db: Database session
        timeout_seconds: Maximum transaction duration (default: 5 minutes)
    """
    start_time = time.time()

    def timeout_handler(_signum, _frame):
        db.rollback()
        raise HTTPException(
            status_code=408,
            detail=f"Database transaction timed out after {timeout_seconds} seconds",
        )

    # Set up timeout protection (only on Unix systems and main thread)
    old_handler = None
    try:
        import threading

        if (
            hasattr(signal, "SIGALRM")
            and threading.current_thread() is threading.main_thread()
        ):
            old_handler = signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

        yield

        # Check transaction duration
        duration = time.time() - start_time
        if duration > 30:  # Log slow transactions
            logger.warning(
                f"Slow database transaction completed in {duration:.2f} seconds"
            )

        db.commit()

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        duration = time.time() - start_time
        logger.exception(
            f"Database transaction failed after {duration:.2f} seconds: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Database operation failed: {str(e)}"
        ) from e
    finally:
        # Clear timeout
        import threading

        if (
            hasattr(signal, "SIGALRM")
            and old_handler is not None
            and threading.current_thread() is threading.main_thread()
        ):
            signal.alarm(0)
            signal.signal(signal.SIGALRM, old_handler)


@contextmanager
def read_db_transaction(db: Session, **kwargs):
    """
    Context manager to wrap database operations in a read transaction.
    """
    try:
        yield
    except Exception as e:
        logger.exception(
            f"Read database transaction failed in with kwargs: {kwargs}: {str(e)}"
        )
        raise HTTPException(
            status_code=500, detail=f"Read database operation failed: {str(e)}"
        ) from e


@contextmanager
def scoped_session():
    """Context manager that yields a SQLAlchemy session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
