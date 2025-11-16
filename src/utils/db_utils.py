"""
Database Utility Functions - Transaction Safety & Context Managers

Provides safe database transaction handling with automatic rollback on errors.
"""

from contextlib import contextmanager
from typing import Generator

from loguru import logger
from sqlalchemy.orm import Session

from src.storage.database import get_db


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.

    Ensures database transactions are properly handled:
    - Commits on success
    - Rolls back on exceptions
    - Always closes the session

    Yields:
        Session: SQLAlchemy database session

    Example:
        >>> from src.utils.db_utils import get_db_session
        >>> from src.storage.models import Selector
        >>>
        >>> with get_db_session() as db:
        >>>     selector = db.query(Selector).filter_by(site_name='yonhap').first()
        >>>     selector.success_count += 1
        >>>     # Automatic commit on exit

        >>> # On error:
        >>> try:
        >>>     with get_db_session() as db:
        >>>         selector = Selector(site_name='invalid', ...)
        >>>         db.add(selector)
        >>>         raise ValueError("Something went wrong")
        >>> except ValueError:
        >>>     pass
        >>> # Automatic rollback occurred

    Raises:
        Exception: Re-raises any exception that occurred within the context
    """
    db = next(get_db())
    try:
        yield db
        db.commit()
        logger.debug("[DB] Transaction committed successfully")
    except Exception as e:
        db.rollback()
        logger.error(f"[DB] Transaction rolled back due to error: {e}")
        raise
    finally:
        db.close()
        logger.debug("[DB] Session closed")


@contextmanager
def get_db_session_no_commit() -> Generator[Session, None, None]:
    """
    Context manager for read-only database sessions.

    Does not commit changes, but still ensures proper session cleanup.
    Useful for read-only queries where you don't want accidental commits.

    Yields:
        Session: SQLAlchemy database session (read-only mode)

    Example:
        >>> from src.utils.db_utils import get_db_session_no_commit
        >>> from src.storage.models import CrawlResult
        >>>
        >>> with get_db_session_no_commit() as db:
        >>>     results = db.query(CrawlResult).filter_by(site_name='donga').all()
        >>>     # No commit, just read

    Raises:
        Exception: Re-raises any exception that occurred within the context
    """
    db = next(get_db())
    try:
        yield db
        logger.debug("[DB] Read-only session completed")
    except Exception as e:
        logger.error(f"[DB] Read-only session error: {e}")
        raise
    finally:
        db.close()
        logger.debug("[DB] Session closed")


def safe_db_operation(operation_func, *args, **kwargs):
    """
    Execute a database operation safely with automatic error handling.

    Args:
        operation_func: Function that takes a db session as first argument
        *args: Additional positional arguments for operation_func
        **kwargs: Additional keyword arguments for operation_func

    Returns:
        Result from operation_func, or None if error occurred

    Example:
        >>> def update_selector(db, site_name, new_selector):
        >>>     selector = db.query(Selector).filter_by(site_name=site_name).first()
        >>>     selector.body_selector = new_selector
        >>>
        >>> result = safe_db_operation(update_selector, 'yonhap', 'div.new-selector')
    """
    try:
        with get_db_session() as db:
            return operation_func(db, *args, **kwargs)
    except Exception as e:
        logger.error(f"[DB] Operation failed: {operation_func.__name__} - {e}")
        return None
