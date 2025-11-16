"""
Error Classifier for CrawlAgent Diagnosis System

Categorizes failures into 5 main types:
1. HTTP/Network Errors
2. Parsing Errors
3. Consensus Failures
4. LLM API Errors
5. Quality Validation Failures
"""

from enum import Enum
from typing import Any, Dict, Optional


class FailureCategory(Enum):
    """Failure categories for diagnosis"""

    HTTP_ERROR = "http_error"
    PARSING_ERROR = "parsing_error"
    CONSENSUS_FAILURE = "consensus_failure"
    LLM_API_ERROR = "llm_api_error"
    QUALITY_FAILURE = "quality_failure"
    UNKNOWN = "unknown"


class ErrorClassifier:
    """
    Intelligent error classifier that analyzes exceptions and context
    to determine the root cause category of failures.
    """

    @staticmethod
    def classify(exception: Exception, context: Dict[str, Any]) -> FailureCategory:
        """
        Classify error into one of 5 failure categories

        Args:
            exception: The exception that was raised
            context: Additional context including:
                - http_status: HTTP status code (401, 403, 404, etc.)
                - consensus_score: Consensus score from UC2/UC3 (0.0-1.0)
                - quality_score: UC1 quality score (0-100)
                - extraction_result: Extracted data dict
                - exception: String representation of exception

        Returns:
            FailureCategory: The classified failure category

        Examples:
            >>> classifier = ErrorClassifier()
            >>> context = {"http_status": 401}
            >>> category = classifier.classify(exception, context)
            >>> print(category)  # FailureCategory.HTTP_ERROR
        """

        # Priority 1: HTTP/Network Errors
        if "http_status" in context and context["http_status"] is not None:
            status = context["http_status"]
            if status in [400, 401, 403, 404, 410, 429, 500, 502, 503, 504]:
                return FailureCategory.HTTP_ERROR

        # Priority 2: LLM API Errors (critical for UC2/UC3)
        exception_str = str(exception).lower()
        if any(
            keyword in exception_str
            for keyword in ["openai", "gemini", "anthropic", "api", "authentication"]
        ):
            if any(
                keyword in exception_str
                for keyword in ["401", "unauthorized", "invalid api key", "quota"]
            ):
                return FailureCategory.LLM_API_ERROR

        # Priority 3: Consensus Failures (UC2/UC3 specific)
        if "consensus_score" in context and context["consensus_score"] is not None:
            score = context["consensus_score"]
            # UC2 threshold: 0.5, UC3 threshold: 0.55
            if score < 0.55:
                return FailureCategory.CONSENSUS_FAILURE

        # Priority 4: Quality Validation Failures (UC1 specific)
        if "quality_score" in context and context["quality_score"] is not None:
            score = context["quality_score"]
            if score < 80:
                return FailureCategory.QUALITY_FAILURE

        # Priority 5: Parsing Errors
        if "extraction_result" in context and context["extraction_result"] is not None:
            result = context["extraction_result"]

            # Check for empty or missing fields
            if isinstance(result, dict):
                title = result.get("title", "")
                body = result.get("body", "")

                # If title or body is empty/too short, it's a parsing error
                if not title or len(title) < 5:
                    return FailureCategory.PARSING_ERROR
                if not body or len(body) < 10:
                    return FailureCategory.PARSING_ERROR

        # Fallback: Check exception message for parsing keywords
        if any(
            keyword in exception_str
            for keyword in ["selector", "beautifulsoup", "trafilatura", "parse", "extract"]
        ):
            return FailureCategory.PARSING_ERROR

        # Default: Unknown
        return FailureCategory.UNKNOWN

    @staticmethod
    def get_category_display_name(category: FailureCategory) -> str:
        """
        Get user-friendly display name for category

        Args:
            category: FailureCategory enum

        Returns:
            str: Display name in Korean

        Examples:
            >>> name = ErrorClassifier.get_category_display_name(FailureCategory.HTTP_ERROR)
            >>> print(name)  # "HTTP/네트워크 오류"
        """
        display_names = {
            FailureCategory.HTTP_ERROR: "HTTP/네트워크 오류",
            FailureCategory.PARSING_ERROR: "파싱 오류",
            FailureCategory.CONSENSUS_FAILURE: "Consensus 실패",
            FailureCategory.LLM_API_ERROR: "LLM API 오류",
            FailureCategory.QUALITY_FAILURE: "품질 검증 실패",
            FailureCategory.UNKNOWN: "알 수 없는 오류",
        }
        return display_names.get(category, "알 수 없는 오류")

    @staticmethod
    def get_category_icon(category: FailureCategory) -> str:
        """
        Get emoji icon for category

        Args:
            category: FailureCategory enum

        Returns:
            str: Emoji icon

        Examples:
            >>> icon = ErrorClassifier.get_category_icon(FailureCategory.HTTP_ERROR)
            >>> print(icon)  # "🌐"
        """
        icons = {
            FailureCategory.HTTP_ERROR: "🌐",
            FailureCategory.PARSING_ERROR: "🔍",
            FailureCategory.CONSENSUS_FAILURE: "🤖",
            FailureCategory.LLM_API_ERROR: "🔑",
            FailureCategory.QUALITY_FAILURE: "⭐",
            FailureCategory.UNKNOWN: "❓",
        }
        return icons.get(category, "❓")
