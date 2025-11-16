"""
LLM API Cost Tracking System
Wraps OpenAI, Gemini, Claude API calls with automatic token counting and cost logging

Created: 2025-11-11
Purpose: Track LLM API costs in real-time for ROI validation and budget management
"""

import time
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, Optional

from loguru import logger

from src.storage.database import get_db
from src.storage.models import CostMetric

# ============================================================================
# Pricing Tables (as of 2025-11-11)
# ============================================================================

PRICING = {
    "openai": {
        "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
        "gpt-4o-mini": {"input": 0.15 / 1_000_000, "output": 0.60 / 1_000_000},
        "gpt-4-turbo": {"input": 10.00 / 1_000_000, "output": 30.00 / 1_000_000},
        "gpt-4": {"input": 30.00 / 1_000_000, "output": 60.00 / 1_000_000},
    },
    "gemini": {
        "gemini-2.5-pro": {"input": 0.125 / 1_000_000, "output": 0.375 / 1_000_000},
        "gemini-2.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
        "gemini-2.0-flash-exp": {"input": 0.0, "output": 0.0},  # Free tier
        "gemini-1.5-pro": {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
    },
    "claude": {
        "claude-3-5-sonnet": {"input": 3.00 / 1_000_000, "output": 15.00 / 1_000_000},
        "claude-3-5-haiku": {"input": 0.25 / 1_000_000, "output": 1.25 / 1_000_000},
        "claude-3-opus": {"input": 15.00 / 1_000_000, "output": 75.00 / 1_000_000},
    },
}


# ============================================================================
# Core Functions
# ============================================================================


def calculate_cost(
    provider: str, model: str, input_tokens: int, output_tokens: int
) -> Dict[str, float]:
    """
    Calculate LLM API cost based on token usage

    Args:
        provider: API provider (openai, gemini, claude)
        model: Model name (gpt-4o-mini, gemini-2.5-pro, etc.)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens

    Returns:
        Dict with input_cost, output_cost, total_cost in USD
    """
    provider = provider.lower()

    # Get pricing
    if provider not in PRICING:
        logger.warning(f"Unknown provider '{provider}', using $0 cost")
        return {"input_cost": 0.0, "output_cost": 0.0, "total_cost": 0.0}

    if model not in PRICING[provider]:
        logger.warning(f"Unknown model '{model}' for {provider}, using $0 cost")
        return {"input_cost": 0.0, "output_cost": 0.0, "total_cost": 0.0}

    pricing = PRICING[provider][model]
    input_cost = input_tokens * pricing["input"]
    output_cost = output_tokens * pricing["output"]
    total_cost = input_cost + output_cost

    return {
        "input_cost": input_cost,
        "output_cost": output_cost,
        "total_cost": total_cost,
    }


def log_cost_to_db(
    provider: str,
    model: str,
    use_case: str,
    input_tokens: int,
    output_tokens: int,
    url: Optional[str] = None,
    site_name: Optional[str] = None,
    workflow_run_id: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """
    Log LLM API cost to database

    Args:
        provider: API provider (openai, gemini, claude)
        model: Model name
        use_case: Use case (uc1, uc2, uc3, other)
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        url: Associated URL (optional)
        site_name: Associated site name (optional)
        workflow_run_id: LangSmith run ID (optional)
        extra_data: Additional metadata (optional)

    Returns:
        Cost metric ID, or None if logging failed
    """
    try:
        # Calculate costs
        costs = calculate_cost(provider, model, input_tokens, output_tokens)
        total_tokens = input_tokens + output_tokens

        # Create cost metric
        db = next(get_db())
        try:
            metric = CostMetric(
                provider=provider.lower(),
                model=model,
                use_case=use_case,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                input_cost=costs["input_cost"],
                output_cost=costs["output_cost"],
                total_cost=costs["total_cost"],
                url=url,
                site_name=site_name,
                workflow_run_id=workflow_run_id,
                extra_data=extra_data,
            )

            db.add(metric)
            db.commit()
            db.refresh(metric)

            logger.info(
                f"💰 Cost logged: {provider}/{model} | "
                f"Tokens: {input_tokens}+{output_tokens}={total_tokens} | "
                f"Cost: ${costs['total_cost']:.6f} | "
                f"Use Case: {use_case}"
            )

            return metric.id

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to log cost to DB: {e}")
        return None


# ============================================================================
# Decorators
# ============================================================================


def track_openai_cost(use_case: str = "other"):
    """
    Decorator to track OpenAI API costs

    Usage:
        @track_openai_cost(use_case="uc1")
        def call_gpt(prompt: str) -> str:
            response = openai.ChatCompletion.create(...)
            return response

    The decorated function must return an OpenAI response object with usage stats
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Call original function
            result = func(*args, **kwargs)

            # Extract token usage from OpenAI response
            try:
                if hasattr(result, "usage"):
                    usage = result.usage
                    input_tokens = usage.prompt_tokens
                    output_tokens = usage.completion_tokens

                    # Extract model name
                    model = result.model if hasattr(result, "model") else "gpt-4o-mini"

                    # Extract URL from kwargs if available
                    url = kwargs.get("url") or kwargs.get("article_url")
                    site_name = kwargs.get("site_name")

                    # Log cost
                    elapsed_time = time.time() - start_time
                    log_cost_to_db(
                        provider="openai",
                        model=model,
                        use_case=use_case,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        url=url,
                        site_name=site_name,
                        extra_data={
                            "response_time_seconds": round(elapsed_time, 2),
                            "function": func.__name__,
                        },
                    )
                else:
                    logger.warning(f"OpenAI response from {func.__name__} has no usage stats")

            except Exception as e:
                logger.error(f"Failed to track OpenAI cost in {func.__name__}: {e}")

            return result

        return wrapper

    return decorator


def track_gemini_cost(use_case: str = "other", model: str = "gemini-2.5-pro"):
    """
    Decorator to track Gemini API costs

    Usage:
        @track_gemini_cost(use_case="uc2", model="gemini-2.5-pro")
        def call_gemini(prompt: str) -> str:
            response = model.generate_content(...)
            return response

    The decorated function must return a Gemini response object
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()

            # Call original function
            result = func(*args, **kwargs)

            # Extract token usage from Gemini response
            try:
                if hasattr(result, "usage_metadata"):
                    usage = result.usage_metadata
                    input_tokens = usage.prompt_token_count
                    output_tokens = usage.candidates_token_count

                    # Extract URL from kwargs if available
                    url = kwargs.get("url") or kwargs.get("article_url")
                    site_name = kwargs.get("site_name")

                    # Log cost
                    elapsed_time = time.time() - start_time
                    log_cost_to_db(
                        provider="gemini",
                        model=model,
                        use_case=use_case,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        url=url,
                        site_name=site_name,
                        extra_data={
                            "response_time_seconds": round(elapsed_time, 2),
                            "function": func.__name__,
                        },
                    )
                else:
                    logger.warning(f"Gemini response from {func.__name__} has no usage_metadata")

            except Exception as e:
                logger.error(f"Failed to track Gemini cost in {func.__name__}: {e}")

            return result

        return wrapper

    return decorator


# ============================================================================
# Analytics Functions
# ============================================================================


def get_total_cost(
    provider: Optional[str] = None,
    use_case: Optional[str] = None,
    site_name: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
) -> float:
    """
    Get total cost with optional filters

    Args:
        provider: Filter by provider (openai, gemini, claude)
        use_case: Filter by use case (uc1, uc2, uc3)
        site_name: Filter by site name
        start_date: Filter by start date
        end_date: Filter by end date

    Returns:
        Total cost in USD
    """
    try:
        from sqlalchemy import func

        db = next(get_db())
        try:
            query = db.query(func.sum(CostMetric.total_cost))

            # Apply filters
            if provider:
                query = query.filter(CostMetric.provider == provider.lower())
            if use_case:
                query = query.filter(CostMetric.use_case == use_case)
            if site_name:
                query = query.filter(CostMetric.site_name == site_name)
            if start_date:
                query = query.filter(CostMetric.timestamp >= start_date)
            if end_date:
                query = query.filter(CostMetric.timestamp <= end_date)

            total = query.scalar()
            return total or 0.0

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to get total cost: {e}")
        return 0.0


def get_cost_breakdown() -> Dict[str, Any]:
    """
    Get comprehensive cost breakdown

    Returns:
        Dict with total, by_provider, by_use_case, by_model
    """
    try:
        from sqlalchemy import func

        db = next(get_db())
        try:
            # Total cost
            total_cost = db.query(func.sum(CostMetric.total_cost)).scalar() or 0.0

            # Total tokens
            total_tokens = db.query(func.sum(CostMetric.total_tokens)).scalar() or 0

            # By provider
            by_provider = {}
            for row in db.query(CostMetric.provider, func.sum(CostMetric.total_cost)).group_by(
                CostMetric.provider
            ):
                by_provider[row[0]] = float(row[1])

            # By use case
            by_use_case = {}
            for row in db.query(CostMetric.use_case, func.sum(CostMetric.total_cost)).group_by(
                CostMetric.use_case
            ):
                by_use_case[row[0]] = float(row[1])

            # By model
            by_model = {}
            for row in db.query(CostMetric.model, func.sum(CostMetric.total_cost)).group_by(
                CostMetric.model
            ):
                by_model[row[0]] = float(row[1])

            # Recent costs (last 10)
            recent = []
            for metric in db.query(CostMetric).order_by(CostMetric.timestamp.desc()).limit(10):
                recent.append(
                    {
                        "timestamp": metric.timestamp.isoformat(),
                        "provider": metric.provider,
                        "model": metric.model,
                        "use_case": metric.use_case,
                        "total_cost": metric.total_cost,
                        "site_name": metric.site_name,
                    }
                )

            return {
                "total_cost": total_cost,
                "total_tokens": total_tokens,
                "by_provider": by_provider,
                "by_use_case": by_use_case,
                "by_model": by_model,
                "recent_costs": recent,
            }

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to get cost breakdown: {e}")
        return {
            "total_cost": 0.0,
            "total_tokens": 0,
            "by_provider": {},
            "by_use_case": {},
            "by_model": {},
            "recent_costs": [],
        }


# ============================================================================
# Example Usage
# ============================================================================

"""
# In workflow code (e.g., src/workflow/uc1_validation.py):

from src.monitoring.cost_tracker import track_openai_cost

@track_openai_cost(use_case="uc1")
def validate_with_gpt(article_url: str, html_content: str, site_name: str):
    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response

# Usage:
result = validate_with_gpt(
    article_url="https://example.com/article",
    html_content=html,
    site_name="example"
)
# Cost automatically logged to database!


# Get cost analytics:
from src.monitoring.cost_tracker import get_cost_breakdown, get_total_cost

# Total cost
total = get_total_cost()
print(f"Total cost: ${total:.2f}")

# Cost for UC1 only
uc1_cost = get_total_cost(use_case="uc1")
print(f"UC1 cost: ${uc1_cost:.2f}")

# Full breakdown
breakdown = get_cost_breakdown()
print(f"By provider: {breakdown['by_provider']}")
print(f"By use case: {breakdown['by_use_case']}")
"""
