"""
CrawlAgent Configuration Management

Centralized configuration using Pydantic Settings for type-safe environment variable management.
"""

import os
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # ========================================
    # Database Configuration
    # ========================================
    DATABASE_URL: str = Field(
        default="postgresql://crawlagent:password@localhost:5432/crawlagent",
        description="PostgreSQL database connection URL",
    )

    # ========================================
    # LLM Model Configuration
    # ========================================
    # UC2 Models (Self-Healing)
    UC2_PROPOSER_MODEL: str = Field(default="gpt-4o", description="UC2 Proposer model")
    UC2_VALIDATOR_MODEL: str = Field(default="gpt-4o", description="UC2 Validator model")

    # UC3 Models (New Site Discovery)
    UC3_DISCOVERER_MODEL: str = Field(
        default="claude-sonnet-4-5-20250929", description="UC3 Discoverer model (Claude)"
    )
    UC3_VALIDATOR_MODEL: str = Field(default="gpt-4o", description="UC3 Validator model")

    # Fallback Model
    FALLBACK_MODEL: str = Field(
        default="gpt-4o-mini", description="Fallback model when primary models fail"
    )

    # ========================================
    # API Keys
    # ========================================
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API key")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API key")

    # ========================================
    # Quality & Consensus Thresholds
    # ========================================
    UC1_QUALITY_THRESHOLD: float = Field(
        default=80.0,
        ge=0.0,
        le=100.0,
        description="Minimum quality score for UC1 validation (0-100)",
    )

    UC2_CONSENSUS_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum consensus score for UC2 (0.0-1.0)",
    )

    UC3_CONSENSUS_THRESHOLD: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum consensus score for UC3 (0.0-1.0)",
    )

    # Consensus Weights (must sum to 1.0)
    CONSENSUS_WEIGHT_AGENT1: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for first agent's confidence"
    )
    CONSENSUS_WEIGHT_AGENT2: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for second agent's confidence"
    )
    CONSENSUS_WEIGHT_QUALITY: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Weight for extraction quality"
    )

    # ========================================
    # Retry Configuration
    # ========================================
    MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    RETRY_DELAY: int = Field(default=2, ge=1, le=60, description="Delay between retries (seconds)")

    UC2_MAX_RETRIES: int = Field(
        default=3, ge=1, le=5, description="Maximum retries for UC2 consensus"
    )
    UC3_MAX_RETRIES: int = Field(
        default=3, ge=1, le=5, description="Maximum retries for UC3 consensus"
    )

    # ========================================
    # HTTP Client Configuration
    # ========================================
    REQUEST_TIMEOUT: int = Field(
        default=10, ge=5, le=60, description="HTTP request timeout (seconds)"
    )

    USER_AGENT: str = Field(
        default="Mozilla/5.0 (compatible; CrawlAgent/1.0; +https://github.com/your-org/crawlagent)",
        description="User-Agent header for HTTP requests",
    )

    # ========================================
    # Logging Configuration
    # ========================================
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    LOG_FILE_PATH: str = Field(
        default="logs/crawlagent.log", description="Log file path"
    )

    LOG_ROTATION: str = Field(default="1 day", description="Log rotation interval")

    LOG_RETENTION: str = Field(default="30 days", description="Log retention period")

    LOG_FORMAT: str = Field(
        default="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        description="Log format string",
    )

    # ========================================
    # Server Configuration
    # ========================================
    GRADIO_HOST: str = Field(
        default="0.0.0.0", description="Gradio server bind address"
    )

    GRADIO_PORT: int = Field(
        default=7860, ge=1024, le=65535, description="Gradio server port"
    )

    GRADIO_SHARE: bool = Field(
        default=False, description="Enable Gradio public sharing"
    )

    # ========================================
    # Performance Configuration
    # ========================================
    MAX_WORKERS: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum concurrent workers for parallel processing",
    )

    DB_POOL_SIZE: int = Field(
        default=10, ge=5, le=50, description="Database connection pool size"
    )

    DB_MAX_OVERFLOW: int = Field(
        default=20, ge=5, le=100, description="Maximum overflow connections"
    )

    # ========================================
    # Feature Flags
    # ========================================
    ENABLE_JSON_LD_OPTIMIZATION: bool = Field(
        default=True, description="Enable JSON-LD optimization for UC3"
    )

    ENABLE_DISTRIBUTED_SUPERVISOR: bool = Field(
        default=False, description="Enable 3-Model Voting Distributed Supervisor"
    )

    ENABLE_COST_TRACKING: bool = Field(
        default=True, description="Enable cost tracking and metrics"
    )

    # ========================================
    # Development/Debug
    # ========================================
    DEBUG: bool = Field(default=False, description="Enable debug mode")

    TESTING: bool = Field(default=False, description="Enable testing mode")

    class Config:
        """Pydantic configuration"""

        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"  # Ignore extra environment variables

    def validate_weights(self) -> None:
        """Validate that consensus weights sum to 1.0"""
        total = (
            self.CONSENSUS_WEIGHT_AGENT1
            + self.CONSENSUS_WEIGHT_AGENT2
            + self.CONSENSUS_WEIGHT_QUALITY
        )
        if not abs(total - 1.0) < 0.01:  # Allow small floating point errors
            raise ValueError(
                f"Consensus weights must sum to 1.0 (got {total:.2f}). "
                f"Agent1: {self.CONSENSUS_WEIGHT_AGENT1}, "
                f"Agent2: {self.CONSENSUS_WEIGHT_AGENT2}, "
                f"Quality: {self.CONSENSUS_WEIGHT_QUALITY}"
            )


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached Settings instance.

    This function uses lru_cache to ensure Settings is only instantiated once.
    Subsequent calls will return the same instance.

    Returns:
        Settings: Cached settings instance

    Example:
        >>> from src.config import get_settings
        >>> settings = get_settings()
        >>> print(settings.DATABASE_URL)
        postgresql://crawlagent:password@localhost:5432/crawlagent
    """
    settings = Settings()
    settings.validate_weights()
    return settings


# Convenience function for direct import
def load_env_vars() -> None:
    """
    Explicitly load environment variables from .env file.

    This is useful for scripts that need to ensure .env is loaded.
    """
    from dotenv import load_dotenv

    env_file = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_file):
        load_dotenv(env_file)


# For backward compatibility
settings = get_settings()
