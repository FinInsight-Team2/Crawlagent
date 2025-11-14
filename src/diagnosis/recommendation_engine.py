"""
Recommendation Engine for CrawlAgent Diagnosis System

Provides actionable recommendations based on failure categories and analysis.
"""

from typing import List, Dict, Any
from src.diagnosis.error_classifier import FailureCategory


class RecommendationEngine:
    """
    Intelligent recommendation engine that suggests actionable solutions
    based on failure category and detailed analysis.
    """

    @staticmethod
    def get_recommendations(
        category: FailureCategory,
        context: Dict[str, Any]
    ) -> List[str]:
        """
        Get actionable recommendations for a failure category

        Args:
            category: FailureCategory enum
            context: Additional context including:
                - http_status: HTTP status code
                - consensus_score: Consensus score
                - quality_score: Quality score
                - threshold: Consensus threshold
                - gap: Gap from threshold
                - root_cause: Root cause identified by analyzer

        Returns:
            List[str]: List of actionable recommendations

        Examples:
            >>> engine = RecommendationEngine()
            >>> recs = engine.get_recommendations(
            ...     FailureCategory.CONSENSUS_FAILURE,
            ...     {"consensus_score": 0.45, "threshold": 0.5, "gap": 0.05}
            ... )
            >>> print(recs[0])  # "임계값을 0.05 낮추기 (0.50 → 0.45)"
        """

        if category == FailureCategory.HTTP_ERROR:
            return RecommendationEngine._recommend_http_error(context)

        elif category == FailureCategory.CONSENSUS_FAILURE:
            return RecommendationEngine._recommend_consensus_failure(context)

        elif category == FailureCategory.LLM_API_ERROR:
            return RecommendationEngine._recommend_llm_api_error(context)

        elif category == FailureCategory.QUALITY_FAILURE:
            return RecommendationEngine._recommend_quality_failure(context)

        elif category == FailureCategory.PARSING_ERROR:
            return RecommendationEngine._recommend_parsing_error(context)

        else:
            return [
                "상세 로그를 확인하세요",
                "LangSmith 추적에서 워크플로우를 검토하세요",
                "수동 검토가 필요합니다"
            ]

    @staticmethod
    def _recommend_http_error(context: Dict[str, Any]) -> List[str]:
        """Recommendations for HTTP errors"""
        status = context.get("http_status", 0)

        if status in [401, 403]:
            return [
                "User-Agent를 브라우저로 변경 (현재 차단됨)",
                "다른 기사 URL로 시도하세요",
                "수동으로 HTML을 다운로드 후 테스트하세요",
                "해당 사이트는 스크레이퍼를 차단하고 있을 수 있습니다"
            ]
        elif status == 404:
            return [
                "URL이 유효한지 확인하세요",
                "사이트의 다른 기사 URL로 시도하세요",
                "URL이 만료되었을 수 있습니다"
            ]
        elif status == 429:
            return [
                "잠시 후 다시 시도하세요 (Rate Limit)",
                "요청 간격을 늘리세요",
                "여러 URL을 동시에 요청하지 마세요"
            ]
        elif status in [500, 502, 503, 504]:
            return [
                "사이트 서버에 일시적 문제가 있습니다",
                "몇 분 후 다시 시도하세요",
                "다른 뉴스 사이트를 시도하세요"
            ]
        else:
            return [
                f"HTTP {status} 오류가 발생했습니다",
                "네트워크 연결을 확인하세요",
                "다른 URL로 시도하세요"
            ]

    @staticmethod
    def _recommend_consensus_failure(context: Dict[str, Any]) -> List[str]:
        """Recommendations for Consensus failures"""
        score = context.get("consensus_score", 0.0)
        threshold = context.get("threshold", 0.5)
        gap = context.get("gap", 0.0)
        root_cause = context.get("root_cause", "unknown")

        recommendations = []

        # If close to threshold, suggest lowering it
        if gap > 0 and gap <= 0.10:
            recommendations.append(
                f"임계값을 {gap:.2f} 낮추기 ({threshold:.2f} → {threshold - gap:.2f})"
            )

        # Root cause specific recommendations
        if root_cause == "gemini_low":
            recommendations.extend([
                "Gemini 모델을 더 강력한 버전으로 변경 (2.0-flash → 2.5-pro)",
                "Gemini Validator 프롬프트를 개선하세요",
                "Few-Shot Examples를 더 추가하세요 (현재 5개)"
            ])
        elif root_cause == "gpt_low":
            recommendations.extend([
                "GPT 모델을 업그레이드 (gpt-4o-mini → gpt-4o)",
                "GPT Proposer 프롬프트에 더 많은 컨텍스트 제공",
                "Few-Shot Examples의 품질을 검토하세요"
            ])
        elif root_cause == "extraction_low":
            recommendations.extend([
                "제안된 CSS Selector가 실제로 작동하지 않습니다",
                "UC3 Discovery로 전환하여 처음부터 학습하세요",
                "사이트 HTML 구조를 수동으로 확인하세요"
            ])

        # General recommendations
        recommendations.extend([
            "UC3 Discovery 모드로 전환 (신규 사이트 학습)",
            "LangSmith에서 GPT/Gemini 응답을 확인하세요",
            "수동으로 CSS Selector를 확인 및 수정하세요"
        ])

        return recommendations

    @staticmethod
    def _recommend_llm_api_error(context: Dict[str, Any]) -> List[str]:
        """Recommendations for LLM API errors"""
        exception_str = str(context.get("exception", "")).lower()

        if "openai" in exception_str:
            return [
                "환경변수 OPENAI_API_KEY를 확인하세요",
                "OpenAI API 키를 재발급하세요 (https://platform.openai.com/api-keys)",
                "API 할당량을 확인하세요",
                "Gemini 단독 모드를 활성화하세요 (GEMINI_ONLY=true)",
                "OpenAI 계정 상태를 확인하세요"
            ]
        elif "gemini" in exception_str:
            return [
                "환경변수 GOOGLE_API_KEY를 확인하세요",
                "Google AI Studio에서 API 키를 확인하세요",
                "Gemini API Rate Limit을 확인하세요",
                "OpenAI 단독 모드로 전환하세요 (임시 해결)"
            ]
        else:
            return [
                "LLM API 키 설정을 확인하세요 (.env 파일)",
                "인터넷 연결을 확인하세요",
                "API 서비스 상태를 확인하세요",
                "상세 로그에서 오류 메시지를 확인하세요"
            ]

    @staticmethod
    def _recommend_quality_failure(context: Dict[str, Any]) -> List[str]:
        """Recommendations for Quality validation failures"""
        quality_score = context.get("quality_score", 0)
        root_cause = context.get("root_cause", "unknown")

        recommendations = []

        if root_cause == "body_too_short":
            recommendations.extend([
                "본문이 너무 짧습니다 → UC2 Self-Healing 트리거됨",
                "CSS Selector가 본문 전체를 선택하지 못했을 수 있습니다",
                "Trafilatura 본문 추출 실패 가능성이 있습니다"
            ])
        elif root_cause == "title_missing_or_short":
            recommendations.extend([
                "제목 CSS Selector를 확인하세요",
                "UC2 Self-Healing이 자동으로 수정을 시도합니다"
            ])
        elif root_cause == "date_missing":
            recommendations.extend([
                "날짜 CSS Selector를 확인하세요",
                "날짜 형식이 정규식과 일치하지 않을 수 있습니다",
                "Meta 태그에서 날짜를 추출하는 fallback을 추가하세요"
            ])

        recommendations.extend([
            "UC2 Self-Healing이 자동으로 실행되어 문제를 해결합니다",
            "품질 점수 임계값(80점)을 조정할 수 있습니다",
            "LangSmith에서 추출 결과를 확인하세요"
        ])

        return recommendations

    @staticmethod
    def _recommend_parsing_error(context: Dict[str, Any]) -> List[str]:
        """Recommendations for Parsing errors"""
        root_cause = context.get("root_cause", "unknown")

        if root_cause == "no_html":
            return [
                "HTML 다운로드에 실패했습니다",
                "네트워크 연결을 확인하세요",
                "URL이 유효한지 확인하세요",
                "사이트가 접근을 차단했을 수 있습니다"
            ]
        elif root_cause == "body_extraction_failed":
            return [
                "Trafilatura 본문 추출이 실패했습니다",
                "Meta description fallback을 사용하세요",
                "CSS Selector로 본문을 직접 추출하세요",
                "UC2 Self-Healing이 자동으로 수정을 시도합니다"
            ]
        elif root_cause == "selector_mismatch":
            return [
                "CSS Selector가 사이트 구조와 일치하지 않습니다",
                "사이트가 HTML 구조를 변경했을 가능성이 있습니다",
                "UC2 Self-Healing으로 자동 복구를 시도하세요",
                "수동으로 DevTools에서 Selector를 확인하세요"
            ]
        else:
            return [
                "파싱 오류가 발생했습니다",
                "HTML 구조를 확인하세요",
                "CSS Selector를 검증하세요",
                "UC2 Self-Healing을 시도하세요"
            ]

    @staticmethod
    def format_recommendations_html(
        recommendations: List[str],
        title: str = "💡 해결 방법"
    ) -> str:
        """
        Format recommendations as HTML for Gradio display

        Args:
            recommendations: List of recommendation strings
            title: Section title

        Returns:
            str: Formatted HTML string

        Examples:
            >>> html = RecommendationEngine.format_recommendations_html(
            ...     ["Recommendation 1", "Recommendation 2"]
            ... )
            >>> print(html)  # <div class='...'><h4>💡 해결 방법</h4><ul>...</ul></div>
        """

        if not recommendations:
            return ""

        html = f"""
        <div style='background: rgba(59, 130, 246, 0.1); padding: 20px; border-radius: 8px;
                    border-left: 4px solid #3b82f6; margin-top: 15px;'>
            <h4 style='margin: 0 0 15px 0; color: #3b82f6;'>{title}</h4>
            <ul style='margin: 0; padding-left: 20px; line-height: 1.8;'>
        """

        for rec in recommendations:
            html += f"<li style='margin-bottom: 8px;'>{rec}</li>"

        html += """
            </ul>
        </div>
        """

        return html
