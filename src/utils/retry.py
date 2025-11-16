"""
CrawlAgent - Retry Logic with Exponential Backoff
Created: 2025-11-15

Provides retry decorators and functions for LLM API calls.

Features:
- Exponential Backoff: 1s → 2s → 4s
- Configurable retry count (default: 3)
- Rate limit detection (429, RateLimitError)
- Timeout handling
- Structured logging
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Tuple, Type, TypeVar

from openai import APIError, APITimeoutError, RateLimitError

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Exception types that should trigger retry
RETRYABLE_EXCEPTIONS = (
    RateLimitError,
    APIError,
    APITimeoutError,
    ConnectionError,
    TimeoutError,
)


def exponential_backoff(attempt: int, base_delay: float = 1.0, max_delay: float = 32.0) -> float:
    """
    Calculate exponential backoff delay.

    Args:
        attempt: Current retry attempt (0-indexed)
        base_delay: Base delay in seconds (default: 1.0)
        max_delay: Maximum delay in seconds (default: 32.0)

    Returns:
        Delay in seconds (capped at max_delay)

    Example:
        attempt=0 → 1s
        attempt=1 → 2s
        attempt=2 → 4s
        attempt=3 → 8s
    """
    delay = base_delay * (2**attempt)
    return min(delay, max_delay)


def retry_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    log_prefix: str = "Retry",
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for retry logic with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay for exponential backoff (default: 1.0s)
        retryable_exceptions: Tuple of exception types to retry on
        log_prefix: Prefix for log messages

    Returns:
        Decorated function that retries on failure

    Usage:
        @retry_with_backoff(max_retries=3, base_delay=1.0)
        def call_llm_api():
            return client.chat.completions.create(...)

    Behavior:
        - Attempt 1: No delay
        - Attempt 2: Wait 1s (base_delay * 2^0)
        - Attempt 3: Wait 2s (base_delay * 2^1)
        - Attempt 4: Wait 4s (base_delay * 2^2)

        If all attempts fail, raise the last exception.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)

                    # Log success on retry
                    if attempt > 0:
                        logger.info(
                            f"[{log_prefix}] ✅ Success on attempt {attempt + 1}/{max_retries} "
                            f"for {func.__name__}"
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    # Check if this is the last attempt
                    if attempt >= max_retries - 1:
                        logger.error(
                            f"[{log_prefix}] ❌ All {max_retries} attempts failed for {func.__name__}: {e}"
                        )
                        raise

                    # Calculate backoff delay
                    delay = exponential_backoff(attempt, base_delay)

                    logger.warning(
                        f"[{log_prefix}] ⚠️ Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    # Wait before retry
                    time.sleep(delay)

                except Exception as e:
                    # Non-retryable exception: fail immediately
                    logger.error(
                        f"[{log_prefix}] ❌ Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                    )
                    raise

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception

            raise RuntimeError(f"Unexpected retry logic failure in {func.__name__}")

        return wrapper

    return decorator


def retry_async_with_backoff(
    max_retries: int = 3,
    base_delay: float = 1.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = RETRYABLE_EXCEPTIONS,
    log_prefix: str = "AsyncRetry",
):
    """
    Async version of retry_with_backoff decorator.

    Usage:
        @retry_async_with_backoff(max_retries=3)
        async def call_llm_api_async():
            return await client.chat.completions.create(...)
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio

            last_exception = None

            for attempt in range(max_retries):
                try:
                    result = await func(*args, **kwargs)

                    if attempt > 0:
                        logger.info(
                            f"[{log_prefix}] ✅ Success on attempt {attempt + 1}/{max_retries} "
                            f"for {func.__name__}"
                        )

                    return result

                except retryable_exceptions as e:
                    last_exception = e

                    if attempt >= max_retries - 1:
                        logger.error(
                            f"[{log_prefix}] ❌ All {max_retries} attempts failed for {func.__name__}: {e}"
                        )
                        raise

                    delay = exponential_backoff(attempt, base_delay)

                    logger.warning(
                        f"[{log_prefix}] ⚠️ Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    await asyncio.sleep(delay)

                except Exception as e:
                    logger.error(
                        f"[{log_prefix}] ❌ Non-retryable error in {func.__name__}: {type(e).__name__}: {e}"
                    )
                    raise

            if last_exception:
                raise last_exception

            raise RuntimeError(f"Unexpected retry logic failure in {func.__name__}")

        return wrapper

    return decorator


# Convenience function for direct retry
def retry_function(
    func: Callable[..., T], *args: Any, max_retries: int = 3, base_delay: float = 1.0, **kwargs: Any
) -> T:
    """
    Direct function retry without decorator.

    Usage:
        result = retry_function(
            lambda: client.chat.completions.create(...),
            max_retries=3,
            base_delay=1.0
        )
    """

    @retry_with_backoff(max_retries=max_retries, base_delay=base_delay)
    def wrapper():
        return func(*args, **kwargs)

    return wrapper()
