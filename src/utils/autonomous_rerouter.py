"""
Autonomous Re-routing Module

Layer 3: Worker들이 스스로 실패를 감지하고 다음 UC로 자동 전환
Supervisor 의존도 최소화 → SPOF 제거

핵심 철학: "Workers know best when they fail"
"""

from typing import Dict, Literal, Optional

from loguru import logger

# Fallback chain configuration
FALLBACK_CHAIN = {
    "uc1": "uc2",  # UC1 실패 → UC2로
    "uc2": "uc3",  # UC2 실패 → UC3로
    "uc3": None,  # UC3가 마지막
}

# Quality thresholds for each UC
QUALITY_THRESHOLDS = {
    "uc1": 0.7,  # UC1은 높은 품질 요구
    "uc2": 0.6,  # UC2는 중간 품질
    "uc3": 0.5,  # UC3는 낮은 품질 (신규 사이트)
}


def should_reroute(
    current_uc: Literal["uc1", "uc2", "uc3"], quality_score: float, confidence: float = None
) -> tuple[bool, Optional[str], str]:
    """
    Worker 결과의 품질을 평가하여 재라우팅 필요 여부 판단

    Args:
        current_uc: 현재 UC ("uc1", "uc2", "uc3")
        quality_score: 품질 점수 (0.0-1.0)
        confidence: 신뢰도 점수 (0.0-1.0, optional)

    Returns:
        (should_reroute: bool, next_uc: str|None, reason: str)

    Examples:
        >>> should_reroute("uc1", 0.4)
        (True, "uc2", "UC1 quality too low (0.40 < 0.70)")

        >>> should_reroute("uc3", 0.6)
        (False, None, "UC3 quality acceptable (0.60 >= 0.50)")
    """

    threshold = QUALITY_THRESHOLDS.get(current_uc, 0.7)

    # Quality check
    if quality_score < threshold:
        next_uc = FALLBACK_CHAIN.get(current_uc)

        if next_uc:
            reason = f"{current_uc.upper()} quality too low ({quality_score:.2f} < {threshold:.2f})"
            logger.warning(
                f"[Autonomous Re-router] ⚠️ {reason} → Suggest re-route to {next_uc.upper()}"
            )
            return True, next_uc, reason
        else:
            reason = f"{current_uc.upper()} quality low ({quality_score:.2f} < {threshold:.2f}) but no fallback available"
            logger.error(f"[Autonomous Re-router] ❌ {reason}")
            return False, None, reason

    # Confidence check (if provided)
    if confidence is not None and confidence < 0.5:
        next_uc = FALLBACK_CHAIN.get(current_uc)

        if next_uc:
            reason = f"{current_uc.upper()} confidence too low ({confidence:.2f} < 0.50)"
            logger.warning(
                f"[Autonomous Re-router] ⚠️ {reason} → Suggest re-route to {next_uc.upper()}"
            )
            return True, next_uc, reason

    # Pass
    reason = f"{current_uc.upper()} quality acceptable ({quality_score:.2f} >= {threshold:.2f})"
    logger.info(f"[Autonomous Re-router] ✅ {reason}")
    return False, None, reason


def create_reroute_recommendation(
    current_uc: str, quality_score: float, confidence: float = None, error_message: str = None
) -> Dict:
    """
    Worker가 Supervisor에게 보낼 재라우팅 추천 생성

    Returns:
        {
            "should_reroute": bool,
            "recommended_uc": str|None,
            "reason": str,
            "current_quality": float,
            "fallback_available": bool
        }
    """

    should_route, next_uc, reason = should_reroute(current_uc, quality_score, confidence)

    recommendation = {
        "should_reroute": should_route,
        "recommended_uc": next_uc,
        "reason": reason,
        "current_quality": quality_score,
        "current_confidence": confidence,
        "fallback_available": next_uc is not None,
        "error_message": error_message,
    }

    if should_route:
        logger.info(
            f"[Autonomous Re-router] 📤 Recommendation: {current_uc.upper()} → {next_uc.upper() if next_uc else 'NONE'}"
        )

    return recommendation


def get_conservative_route(state: Dict) -> str:
    """
    보수적 라우팅: 불확실할 때는 가장 안전한 UC3로

    Used by Supervisor when workers disagree or quality is uncertain
    """

    current_uc = state.get("current_uc")
    failure_count = state.get("failure_count", 0)

    # 3회 이상 실패 → 강제로 UC3
    if failure_count >= 3:
        logger.warning(
            f"[Autonomous Re-router] 🚨 {failure_count} failures → Conservative route to UC3"
        )
        return "uc3"

    # 현재 UC가 없으면 UC1부터 시작
    if not current_uc:
        return "uc1"

    # Fallback chain 따라가기
    next_uc = FALLBACK_CHAIN.get(current_uc)
    if next_uc:
        logger.info(
            f"[Autonomous Re-router] 🔄 Conservative fallback: {current_uc.upper()} → {next_uc.upper()}"
        )
        return next_uc

    # UC3가 마지막이면 종료
    return "end"


# Auto-retry with exponential backoff
def should_retry(current_uc: str, attempt: int, max_retries: int = 2) -> tuple[bool, float]:
    """
    재시도 여부 및 대기 시간 계산

    Returns:
        (should_retry: bool, wait_seconds: float)
    """

    if attempt >= max_retries:
        logger.info(f"[Autonomous Re-router] ⛔ Max retries reached ({attempt}/{max_retries})")
        return False, 0.0

    # Exponential backoff: 2^attempt seconds
    wait_time = 2**attempt
    logger.info(f"[Autonomous Re-router] 🔁 Retry {attempt + 1}/{max_retries} after {wait_time}s")

    return True, wait_time
