"""
LLM Fallback System for CrawlAgent

Provides automatic fallback from OpenAI to Gemini (or vice versa)
when API errors occur, ensuring system resilience.

Usage:
    from src.agents.llm_fallback import call_with_fallback

    response = call_with_fallback(
        primary="openai",
        fallback="gemini",
        prompt="Analyze this HTML...",
        model="gpt-4o"
    )
"""

import logging
import os
from typing import Any, Dict, Literal, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)

# Provider configurations
PROVIDER_CONFIGS = {
    "openai": {
        "models": {"gpt-4o": "gpt-4o", "gpt-4o-mini": "gpt-4o-mini", "default": "gpt-4o"},
        "env_key": "OPENAI_API_KEY",
    },
    "gemini": {
        "models": {
            "gemini-2.5-pro": "gemini-exp-1206",  # Gemini 2.5 Pro Experimental (최고 성능)
            "gemini-exp-1206": "gemini-exp-1206",
            "gemini-2.0-flash": "gemini-2.0-flash-exp",
            "default": "gemini-exp-1206",  # Default to highest performance model
        },
        "env_key": "GOOGLE_API_KEY",
    },
}


class LLMFallbackError(Exception):
    """Raised when both primary and fallback LLMs fail"""

    pass


def _get_llm_client(
    provider: Literal["openai", "gemini"], model: Optional[str] = None, temperature: float = 0.0
):
    """
    Get LLM client for specified provider

    Args:
        provider: "openai" or "gemini"
        model: Model name (uses default if None)
        temperature: Temperature setting (0.0-1.0)

    Returns:
        LangChain LLM client

    Raises:
        ValueError: If provider is invalid or API key is missing
    """

    if provider not in PROVIDER_CONFIGS:
        raise ValueError(f"Invalid provider: {provider}. Must be 'openai' or 'gemini'")

    config = PROVIDER_CONFIGS[provider]
    api_key = os.getenv(config["env_key"])

    # Try backup key if primary key is missing (Gemini/OpenAI)
    if not api_key and provider == "gemini":
        api_key = os.getenv("GOOGLE_API_KEY_BACKUP")
        if api_key:
            logger.info(f"Using GOOGLE_API_KEY_BACKUP for Gemini")
    elif not api_key and provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY_BACKUP_1")
        if api_key:
            logger.info(f"Using OPENAI_API_KEY_BACKUP_1")

    if not api_key:
        raise ValueError(f"{config['env_key']} environment variable not set")

    # Select model
    if model is None:
        model = config["models"]["default"]
    elif model in config["models"]:
        model = config["models"][model]

    # Create client
    if provider == "openai":
        return ChatOpenAI(model=model, temperature=temperature, api_key=api_key)
    elif provider == "gemini":
        return ChatGoogleGenerativeAI(model=model, temperature=temperature, google_api_key=api_key)


def call_with_fallback(
    primary: Literal["openai", "gemini"],
    fallback: Literal["openai", "gemini"],
    prompt: str,
    system_prompt: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.0,
    response_format: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Call LLM with automatic fallback on failure

    Args:
        primary: Primary provider ("openai" or "gemini")
        fallback: Fallback provider ("openai" or "gemini")
        prompt: User prompt
        system_prompt: Optional system prompt
        model: Model name (provider-specific)
        temperature: Temperature (0.0-1.0)
        response_format: Optional response format (for structured output)

    Returns:
        Dict with:
            - content: Response content
            - provider: Which provider was used
            - model: Which model was used
            - fallback_used: Whether fallback was triggered

    Raises:
        LLMFallbackError: If both primary and fallback fail

    Examples:
        >>> response = call_with_fallback(
        ...     primary="openai",
        ...     fallback="gemini",
        ...     prompt="Analyze this HTML",
        ...     model="gpt-4o"
        ... )
        >>> print(response["provider"])  # "openai" or "gemini"
        >>> print(response["fallback_used"])  # True or False
    """

    # Check for GEMINI_ONLY mode
    if os.getenv("GEMINI_ONLY", "false").lower() == "true":
        logger.info("GEMINI_ONLY mode enabled, forcing Gemini provider")
        primary = "gemini"
        fallback = "gemini"

    # Try primary provider
    try:
        logger.info(f"Attempting primary provider: {primary} (model: {model or 'default'})")

        client = _get_llm_client(primary, model, temperature)

        # Construct messages
        messages = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        # Call LLM
        response = client.invoke(messages)

        logger.info(f"✅ Primary provider {primary} succeeded")

        return {
            "content": response.content,
            "provider": primary,
            "model": model or PROVIDER_CONFIGS[primary]["models"]["default"],
            "fallback_used": False,
        }

    except Exception as primary_error:
        logger.warning(f"⚠️ Primary provider {primary} failed: {str(primary_error)}")
        logger.info(f"Attempting fallback provider: {fallback}")

        # Try fallback provider
        try:
            # Use fallback-specific model (don't reuse primary model name)
            fallback_model = None  # Use default for fallback

            client = _get_llm_client(fallback, fallback_model, temperature)

            # Construct messages
            messages = []
            if system_prompt:
                messages.append(SystemMessage(content=system_prompt))
            messages.append(HumanMessage(content=prompt))

            # Call LLM
            response = client.invoke(messages)

            logger.info(f"✅ Fallback provider {fallback} succeeded")

            return {
                "content": response.content,
                "provider": fallback,
                "model": fallback_model or PROVIDER_CONFIGS[fallback]["models"]["default"],
                "fallback_used": True,
                "primary_error": str(primary_error),
            }

        except Exception as fallback_error:
            logger.error(f"❌ Fallback provider {fallback} also failed: {str(fallback_error)}")

            # Both failed - raise comprehensive error
            raise LLMFallbackError(
                f"Both primary ({primary}) and fallback ({fallback}) providers failed.\n"
                f"Primary error: {str(primary_error)}\n"
                f"Fallback error: {str(fallback_error)}"
            )


def check_provider_availability() -> Dict[str, bool]:
    """
    Check which LLM providers are available (have valid API keys)

    Returns:
        Dict: {"openai": bool, "gemini": bool}

    Examples:
        >>> availability = check_provider_availability()
        >>> print(availability)  # {"openai": True, "gemini": False}
    """

    availability = {}

    for provider, config in PROVIDER_CONFIGS.items():
        api_key = os.getenv(config["env_key"])
        availability[provider] = bool(api_key)

        if api_key:
            logger.info(f"✅ {provider} API key found")
        else:
            logger.warning(f"❌ {provider} API key NOT found ({config['env_key']})")

    return availability


def get_recommended_fallback(primary: str) -> Optional[str]:
    """
    Get recommended fallback provider for a primary provider

    Args:
        primary: Primary provider name

    Returns:
        Recommended fallback provider (or None if none available)

    Examples:
        >>> fallback = get_recommended_fallback("openai")
        >>> print(fallback)  # "gemini" (if available)
    """

    availability = check_provider_availability()

    # If primary is not available, return None
    if not availability.get(primary):
        return None

    # Recommend opposite provider
    if primary == "openai":
        return "gemini" if availability.get("gemini") else None
    elif primary == "gemini":
        return "openai" if availability.get("openai") else None

    return None


# Convenience functions for specific use cases


def call_openai_with_gemini_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gpt-4o",
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Call OpenAI GPT with Gemini fallback (most common UC2/UC3 pattern)

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        model: OpenAI model name
        temperature: Temperature

    Returns:
        Response dict with content and metadata

    Examples:
        >>> response = call_openai_with_gemini_fallback(
        ...     prompt="Propose CSS selectors for this HTML",
        ...     model="gpt-4o"
        ... )
    """

    return call_with_fallback(
        primary="openai",
        fallback="gemini",
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )


def call_gemini_with_openai_fallback(
    prompt: str,
    system_prompt: Optional[str] = None,
    model: str = "gemini-2.0-flash",
    temperature: float = 0.0,
) -> Dict[str, Any]:
    """
    Call Gemini with OpenAI fallback (for Gemini-first scenarios)

    Args:
        prompt: User prompt
        system_prompt: Optional system prompt
        model: Gemini model name
        temperature: Temperature

    Returns:
        Response dict with content and metadata

    Examples:
        >>> response = call_gemini_with_openai_fallback(
        ...     prompt="Validate these CSS selectors",
        ...     model="gemini-2.0-flash"
        ... )
    """

    return call_with_fallback(
        primary="gemini",
        fallback="openai",
        prompt=prompt,
        system_prompt=system_prompt,
        model=model,
        temperature=temperature,
    )
