"""
Failure Analyzer for CrawlAgent Diagnosis System

Provides detailed analysis of failures with breakdowns and root cause identification.
"""

from typing import Dict, Optional, Any


class FailureAnalyzer:
    """
    Detailed failure analyzer that provides in-depth analysis
    of specific failure types with actionable insights.
    """

    @staticmethod
    def analyze_consensus_failure(
        gpt_confidence: float,
        gemini_confidence: float,
        extraction_quality: float,
        threshold: float,
        use_case: str = "UC2"
    ) -> Dict[str, Any]:
        """
        Analyze Consensus failure with detailed breakdown

        Args:
            gpt_confidence: GPT confidence score (0.0-1.0)
            gemini_confidence: Gemini confidence score (0.0-1.0)
            extraction_quality: Extraction quality score (0.0-1.0)
            threshold: Consensus threshold (0.5 for UC2, 0.55 for UC3)
            use_case: Which use case (UC2 or UC3)

        Returns:
            Dict with:
                - score: Final consensus score
                - threshold: Threshold that wasn't met
                - breakdown: Individual component contributions
                - root_cause: Primary reason for failure
                - explanation: Human-readable explanation
                - gap: How far from threshold

        Examples:
            >>> result = FailureAnalyzer.analyze_consensus_failure(
            ...     gpt_confidence=0.5,
            ...     gemini_confidence=0.3,
            ...     extraction_quality=0.4,
            ...     threshold=0.5
            ... )
            >>> print(result["score"])  # 0.42
            >>> print(result["root_cause"])  # "gemini_low"
        """

        # Calculate consensus score (weighted average)
        score = (
            gpt_confidence * 0.3 +
            gemini_confidence * 0.3 +
            extraction_quality * 0.4
        )

        # Individual contributions
        breakdown = {
            "gpt_contribution": round(gpt_confidence * 0.3, 3),
            "gemini_contribution": round(gemini_confidence * 0.3, 3),
            "extraction_contribution": round(extraction_quality * 0.4, 3),
            "gpt_confidence": round(gpt_confidence, 3),
            "gemini_confidence": round(gemini_confidence, 3),
            "extraction_quality": round(extraction_quality, 3)
        }

        # Identify root cause (lowest component)
        if gemini_confidence < 0.4:
            root_cause = "gemini_low"
            explanation = f"Gemini Validator가 GPT 제안을 검증하지 못했습니다 (신뢰도: {gemini_confidence:.2f})"
        elif gpt_confidence < 0.4:
            root_cause = "gpt_low"
            explanation = f"GPT Proposer가 낮은 신뢰도로 제안했습니다 (신뢰도: {gpt_confidence:.2f})"
        elif extraction_quality < 0.4:
            root_cause = "extraction_low"
            explanation = f"실제 추출 결과가 부정확합니다 (품질: {extraction_quality:.2f})"
        else:
            root_cause = "threshold_too_high"
            explanation = f"모든 요소가 양호하지만 임계값 {threshold}를 넘지 못했습니다"

        # Gap analysis
        gap = threshold - score

        return {
            "score": round(score, 3),
            "threshold": threshold,
            "breakdown": breakdown,
            "root_cause": root_cause,
            "explanation": explanation,
            "gap": round(gap, 3),
            "use_case": use_case,
            "passed": score >= threshold
        }

    @staticmethod
    def analyze_quality_failure(
        title: str,
        body: str,
        date: Optional[str],
        url: str,
        quality_score: int
    ) -> Dict[str, Any]:
        """
        Analyze UC1 quality validation failure

        Args:
            title: Extracted title
            body: Extracted body text
            date: Extracted date (or None)
            url: Article URL
            quality_score: Total quality score (0-100)

        Returns:
            Dict with:
                - quality_score: Total score
                - breakdown: Individual field scores
                - root_cause: Primary reason for low quality
                - explanation: Human-readable explanation

        Examples:
            >>> result = FailureAnalyzer.analyze_quality_failure(
            ...     title="삼성전자",
            ...     body="짧은 본문",
            ...     date=None,
            ...     url="https://example.com/news/123",
            ...     quality_score=45
            ... )
            >>> print(result["root_cause"])  # "body_too_short"
        """

        # Calculate individual field scores (5W1H logic from UC1)
        title_score = 20 if len(title) >= 5 else 0
        body_score = 60 if len(body) >= 100 else max(0, int(len(body) / 100 * 60))
        date_score = 10 if date else 0
        url_score = 10 if url and url.startswith("http") else 0

        breakdown = {
            "title_score": title_score,
            "body_score": body_score,
            "date_score": date_score,
            "url_score": url_score,
            "title_length": len(title),
            "body_length": len(body),
            "has_date": bool(date)
        }

        # Identify root cause (lowest score)
        if body_score < 60:
            root_cause = "body_too_short"
            explanation = f"본문이 너무 짧습니다 ({len(body)}자 < 100자 목표)"
        elif title_score == 0:
            root_cause = "title_missing_or_short"
            explanation = f"제목이 없거나 너무 짧습니다 ({len(title)}자 < 5자 목표)"
        elif date_score == 0:
            root_cause = "date_missing"
            explanation = "날짜 정보를 추출하지 못했습니다"
        elif url_score == 0:
            root_cause = "invalid_url"
            explanation = "유효하지 않은 URL입니다"
        else:
            root_cause = "overall_low"
            explanation = "전반적인 품질이 낮습니다"

        return {
            "quality_score": quality_score,
            "breakdown": breakdown,
            "root_cause": root_cause,
            "explanation": explanation,
            "threshold": 80,
            "gap": 80 - quality_score
        }

    @staticmethod
    def analyze_http_error(
        status_code: int,
        url: str,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze HTTP/Network error

        Args:
            status_code: HTTP status code
            url: Failed URL
            error_message: Optional error message

        Returns:
            Dict with:
                - status_code: HTTP status
                - category: Error category (client/server/auth)
                - explanation: Human-readable explanation
                - is_permanent: Whether error is permanent or transient

        Examples:
            >>> result = FailureAnalyzer.analyze_http_error(401, "https://example.com")
            >>> print(result["category"])  # "auth_error"
            >>> print(result["is_permanent"])  # True
        """

        # Categorize by status code
        if status_code in [401, 403]:
            category = "auth_error"
            explanation = f"인증 오류: 사이트가 접근을 차단했습니다 (HTTP {status_code})"
            is_permanent = True
        elif status_code == 404:
            category = "not_found"
            explanation = "페이지를 찾을 수 없습니다 (HTTP 404)"
            is_permanent = True
        elif status_code in [429]:
            category = "rate_limit"
            explanation = "요청 제한 초과: 너무 많은 요청을 보냈습니다 (HTTP 429)"
            is_permanent = False
        elif status_code in [500, 502, 503, 504]:
            category = "server_error"
            explanation = f"서버 오류: 사이트 서버에 문제가 있습니다 (HTTP {status_code})"
            is_permanent = False
        else:
            category = "unknown_http"
            explanation = f"HTTP 오류 {status_code}"
            is_permanent = False

        return {
            "status_code": status_code,
            "category": category,
            "explanation": explanation,
            "is_permanent": is_permanent,
            "url": url,
            "error_message": error_message or "N/A"
        }

    @staticmethod
    def analyze_parsing_error(
        extraction_result: Optional[Dict[str, Any]],
        html_length: int,
        selector_info: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Analyze parsing/extraction error

        Args:
            extraction_result: Extracted data (or None)
            html_length: Length of HTML content
            selector_info: CSS selectors used

        Returns:
            Dict with:
                - has_html: Whether HTML was fetched
                - extraction_result: What was extracted
                - root_cause: Primary parsing issue
                - explanation: Human-readable explanation

        Examples:
            >>> result = FailureAnalyzer.analyze_parsing_error(
            ...     extraction_result={"title": "", "body": ""},
            ...     html_length=45000
            ... )
            >>> print(result["root_cause"])  # "selector_mismatch"
        """

        has_html = html_length > 0

        if not has_html:
            root_cause = "no_html"
            explanation = "HTML을 다운로드하지 못했습니다"
        elif not extraction_result:
            root_cause = "extraction_failed"
            explanation = "데이터 추출이 완전히 실패했습니다"
        elif extraction_result.get("body", "") == "":
            root_cause = "body_extraction_failed"
            explanation = "본문 추출에 실패했습니다 (Trafilatura 또는 CSS Selector 오류)"
        elif extraction_result.get("title", "") == "":
            root_cause = "title_extraction_failed"
            explanation = "제목 추출에 실패했습니다 (CSS Selector 불일치)"
        else:
            root_cause = "selector_mismatch"
            explanation = "CSS Selector가 사이트 구조와 일치하지 않습니다"

        return {
            "has_html": has_html,
            "html_length": html_length,
            "extraction_result": extraction_result,
            "root_cause": root_cause,
            "explanation": explanation,
            "selector_info": selector_info or {}
        }
