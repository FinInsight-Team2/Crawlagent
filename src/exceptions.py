"""
CrawlAgent Custom Exceptions
Production-grade error handling with specific exception types

Created: 2025-11-11
Purpose: Replace generic Exception catches with specific error types
"""

from typing import Optional, Dict, Any


# ============================================================================
# Base Exceptions
# ============================================================================

class CrawlAgentError(Exception):
    """Base exception for all CrawlAgent errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self) -> str:
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


# ============================================================================
# LLM API Errors
# ============================================================================

class LLMAPIError(CrawlAgentError):
    """Base exception for LLM API errors (OpenAI, Gemini, Claude)"""
    pass


class OpenAIAPIError(LLMAPIError):
    """OpenAI API specific errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.error_code = error_code
        super().__init__(message, details or {})

    @classmethod
    def from_openai_error(cls, error: Exception):
        """Create from OpenAI SDK error"""
        error_str = str(error)

        # Parse status code from error message
        status_code = None
        if "401" in error_str:
            status_code = 401
        elif "429" in error_str:
            status_code = 429
        elif "500" in error_str:
            status_code = 500

        # Parse error code
        error_code = None
        if "invalid_api_key" in error_str:
            error_code = "invalid_api_key"
        elif "insufficient_quota" in error_str:
            error_code = "insufficient_quota"
        elif "rate_limit_exceeded" in error_str:
            error_code = "rate_limit_exceeded"

        return cls(
            message=f"OpenAI API Error: {error_str}",
            status_code=status_code,
            error_code=error_code,
            details={"original_error": error_str}
        )


class GeminiAPIError(LLMAPIError):
    """Google Gemini API specific errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        reason: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.reason = reason
        super().__init__(message, details or {})

    @classmethod
    def from_gemini_error(cls, error: Exception):
        """Create from Gemini SDK error"""
        error_str = str(error)

        # Parse status code
        status_code = None
        if "400" in error_str:
            status_code = 400
        elif "429" in error_str:
            status_code = 429

        # Parse reason
        reason = None
        if "API_KEY_INVALID" in error_str:
            reason = "API_KEY_INVALID"
        elif "QUOTA_EXCEEDED" in error_str:
            reason = "QUOTA_EXCEEDED"

        return cls(
            message=f"Gemini API Error: {error_str}",
            status_code=status_code,
            reason=reason,
            details={"original_error": error_str}
        )


class ClaudeAPIError(LLMAPIError):
    """Anthropic Claude API specific errors"""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        error_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(message, details or {})


# ============================================================================
# Database Errors
# ============================================================================

class DatabaseError(CrawlAgentError):
    """Base exception for database errors"""
    pass


class DatabaseConnectionError(DatabaseError):
    """Database connection failures"""

    def __init__(self, message: str, retry_count: int = 0, details: Optional[Dict[str, Any]] = None):
        self.retry_count = retry_count
        super().__init__(message, details)


class DatabaseQueryError(DatabaseError):
    """Database query execution failures"""

    def __init__(self, message: str, query: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.query = query
        super().__init__(message, details)


class DatabaseIntegrityError(DatabaseError):
    """Database constraint violations (unique, foreign key, etc.)"""

    def __init__(self, message: str, constraint: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.constraint = constraint
        super().__init__(message, details)


# ============================================================================
# Workflow Errors
# ============================================================================

class WorkflowError(CrawlAgentError):
    """Base exception for LangGraph workflow errors"""
    pass


class UC1ValidationError(WorkflowError):
    """UC1 quality validation failures"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        quality_score: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.url = url
        self.quality_score = quality_score
        super().__init__(message, details)


class UC2ConsensusError(WorkflowError):
    """UC2 self-healing consensus failures"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        consensus_score: Optional[float] = None,
        retry_count: int = 0,
        details: Optional[Dict[str, Any]] = None
    ):
        self.url = url
        self.consensus_score = consensus_score
        self.retry_count = retry_count
        super().__init__(message, details)


class UC3DiscoveryError(WorkflowError):
    """UC3 new site discovery failures"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        confidence: Optional[float] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.url = url
        self.confidence = confidence
        super().__init__(message, details)


class LoopDetectionError(WorkflowError):
    """Infinite loop detected in workflow"""

    def __init__(
        self,
        message: str,
        failure_count: int,
        workflow_history: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.failure_count = failure_count
        self.workflow_history = workflow_history or []
        super().__init__(message, details)


# ============================================================================
# Scraping Errors
# ============================================================================

class ScrapingError(CrawlAgentError):
    """Base exception for web scraping errors"""
    pass


class HTMLFetchError(ScrapingError):
    """Failed to fetch HTML from URL"""

    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.url = url
        self.status_code = status_code
        super().__init__(message, details)


class SelectorNotFoundError(ScrapingError):
    """CSS selector not found in HTML"""

    def __init__(
        self,
        message: str,
        selector: Optional[str] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.selector = selector
        self.url = url
        super().__init__(message, details)


class ExtractionError(ScrapingError):
    """Data extraction from HTML failed"""

    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.field = field
        self.url = url
        super().__init__(message, details)


# ============================================================================
# Configuration Errors
# ============================================================================

class ConfigurationError(CrawlAgentError):
    """Base exception for configuration errors"""
    pass


class MissingAPIKeyError(ConfigurationError):
    """Required API key not found in environment"""

    def __init__(self, key_name: str, details: Optional[Dict[str, Any]] = None):
        self.key_name = key_name
        message = f"Missing required API key: {key_name}"
        super().__init__(message, details)


class InvalidConfigError(ConfigurationError):
    """Invalid configuration value"""

    def __init__(self, config_key: str, value: Any, reason: str, details: Optional[Dict[str, Any]] = None):
        self.config_key = config_key
        self.value = value
        self.reason = reason
        message = f"Invalid config '{config_key}': {reason}"
        super().__init__(message, details)


# ============================================================================
# Utility Functions
# ============================================================================

def is_retryable_error(error: Exception) -> bool:
    """
    Determine if an error is retryable (transient failure)

    Args:
        error: Exception to check

    Returns:
        bool: True if error should be retried
    """
    # Retryable HTTP status codes
    retryable_status_codes = {429, 500, 502, 503, 504}

    # Check if it's an API error with retryable status code
    if isinstance(error, (OpenAIAPIError, GeminiAPIError, ClaudeAPIError)):
        return error.status_code in retryable_status_codes

    # Database connection errors are retryable
    if isinstance(error, DatabaseConnectionError):
        return True

    # HTML fetch errors with specific status codes are retryable
    if isinstance(error, HTMLFetchError):
        return error.status_code in retryable_status_codes

    # Other errors are not retryable by default
    return False


def get_fallback_strategy(error: Exception) -> Optional[str]:
    """
    Get recommended fallback strategy for an error

    Args:
        error: Exception to analyze

    Returns:
        str: Fallback strategy name, or None if no fallback
    """
    # OpenAI failures → fallback to Gemini
    if isinstance(error, OpenAIAPIError):
        if error.error_code in ["invalid_api_key", "insufficient_quota"]:
            return "use_gemini_fallback"
        elif error.error_code == "rate_limit_exceeded":
            return "exponential_backoff"

    # Gemini failures → fallback to Claude
    if isinstance(error, GeminiAPIError):
        if error.reason in ["API_KEY_INVALID", "QUOTA_EXCEEDED"]:
            return "use_claude_fallback"

    # Database connection failures → retry with backoff
    if isinstance(error, DatabaseConnectionError):
        return "exponential_backoff"

    # No specific fallback strategy
    return None


def format_error_for_user(error: Exception) -> str:
    """
    Format error message for user-friendly display

    Args:
        error: Exception to format

    Returns:
        str: User-friendly error message
    """
    if isinstance(error, OpenAIAPIError):
        if error.error_code == "invalid_api_key":
            return "OpenAI API key is invalid. Please check your API key configuration."
        elif error.error_code == "insufficient_quota":
            return "OpenAI API quota exceeded. Please check your billing plan."
        elif error.error_code == "rate_limit_exceeded":
            return "OpenAI API rate limit exceeded. Please wait a moment and try again."
        else:
            return f"OpenAI API error: {error.message}"

    elif isinstance(error, GeminiAPIError):
        if error.reason == "API_KEY_INVALID":
            return "Gemini API key is invalid. Please check your API key configuration."
        elif error.reason == "QUOTA_EXCEEDED":
            return "Gemini API quota exceeded. Please check your billing plan."
        else:
            return f"Gemini API error: {error.message}"

    elif isinstance(error, DatabaseConnectionError):
        return f"Database connection failed after {error.retry_count} retries. Please check database status."

    elif isinstance(error, UC1ValidationError):
        return f"Quality validation failed for {error.url} (score: {error.quality_score})"

    elif isinstance(error, UC2ConsensusError):
        return f"Self-healing consensus failed (score: {error.consensus_score}). Selector quality too low."

    elif isinstance(error, LoopDetectionError):
        return f"Workflow loop detected after {error.failure_count} failures. Please review site compatibility."

    elif isinstance(error, HTMLFetchError):
        return f"Failed to fetch {error.url} (HTTP {error.status_code})"

    elif isinstance(error, SelectorNotFoundError):
        return f"CSS selector '{error.selector}' not found in {error.url}"

    elif isinstance(error, MissingAPIKeyError):
        return f"Missing required API key: {error.key_name}. Please configure in .env file."

    else:
        return f"An unexpected error occurred: {str(error)}"


# ============================================================================
# Example Usage
# ============================================================================

"""
# In workflow code:

from src.exceptions import (
    OpenAIAPIError,
    DatabaseConnectionError,
    UC2ConsensusError,
    is_retryable_error,
    get_fallback_strategy,
    format_error_for_user
)

# Instead of:
try:
    result = call_openai(...)
except Exception as e:
    logger.error(f"Error: {e}")
    return {"error": str(e)}

# Use this:
try:
    result = call_openai(...)
except Exception as raw_error:
    # Convert to custom exception
    error = OpenAIAPIError.from_openai_error(raw_error)

    # Log with context
    logger.error(f"OpenAI API Error: {error.message}", extra={
        "status_code": error.status_code,
        "error_code": error.error_code,
        "details": error.details
    })

    # Check if retryable
    if is_retryable_error(error):
        strategy = get_fallback_strategy(error)
        if strategy == "use_gemini_fallback":
            logger.info("Falling back to Gemini...")
            result = call_gemini(...)
        elif strategy == "exponential_backoff":
            logger.info("Retrying with exponential backoff...")
            result = retry_with_backoff(call_openai, ...)
    else:
        # Not retryable, return user-friendly error
        user_message = format_error_for_user(error)
        return {"error_message": user_message, "technical_details": error.details}
"""
