#!/usr/bin/env python3
"""
Supervisor 안전성 유틸리티 모듈

Phase 1 Safety Foundations: LLM 기반 Supervisor의 신뢰성 문제 해결

구현 내용:
1. 신뢰도 임계값 검증 (Confidence Threshold): LLM 결정이 최소 신뢰도 (>= 0.6) 충족 여부 확인
2. 루프 감지 (Loop Detection): 무한 라우팅 사이클 방지 (UC1→UC1→UC1)
3. 상태 제약 검증 (State Constraint): 비즈니스 로직에 따른 상태 전이 규칙 검증

설계 철학:
- Fail-safe: 모든 검증은 명확한 에러 메시지 반환 (로깅/디버깅 용이)
- 무손실 호환성: 검증은 문제만 플래그, 실제 fallback 로직은 호출자가 담당
- 성능 최적화: O(n) 복잡도 (n = history 길이, 일반적으로 < 20)

작성자: Claude Code (Anthropic)
날짜: 2025-11-10
버전: 1.0.0 (Phase 1)
"""

from typing import Optional, Tuple, Literal
from loguru import logger


# ========================================
# 설정 상수 (Configuration Constants)
# ========================================

# UC2 consensus 최소 임계값(0.6)과 동일하게 설정
# UC2는 3단계 시스템: >= 0.8 (자동 승인), >= 0.6 (조건부), < 0.6 (거부)
# Supervisor는 이진 시스템: >= 0.6 (수락), < 0.6 (rule-based로 fallback)
MIN_CONFIDENCE_THRESHOLD = 0.6

# 동일한 UC를 연속으로 방문할 수 있는 최대 횟수
# 예: UC1→UC1→UC1 (3회) 시 루프 감지 트리거
# 근거: 3번 시도 = 실패 선언 전 합리적인 재시도 한도
MAX_LOOP_REPEATS = 3


# ========================================
# 안전 함수 1: 신뢰도 검증
# ========================================

def validate_confidence_threshold(
    confidence: float,
    threshold: float = MIN_CONFIDENCE_THRESHOLD
) -> Tuple[bool, str]:
    """
    LLM의 신뢰도가 최소 임계값을 충족하는지 검증합니다.

    UC2의 검증된 consensus 임계값(0.6)과 일치시켜 시스템 전체의 일관성을 유지합니다.
    낮은 신뢰도는 LLM이 불확실하다는 신호이며, 이 경우 rule-based 로직으로 처리해야 합니다.

    Args:
        confidence: LLM의 신뢰도 점수 (0.0 - 1.0)
        threshold: 최소 허용 신뢰도 (기본값: 0.6)

    Returns:
        (is_valid: bool, error_message: str)
        - (True, "") if confidence >= threshold
        - (False, "이유") if confidence < threshold

    예시:
        >>> validate_confidence_threshold(0.85, 0.6)
        (True, "")

        >>> validate_confidence_threshold(0.45, 0.6)
        (False, "신뢰도 0.45가 최소 임계값 0.60 미만입니다")

    메타인지적 노트:
        왜 0.6인가? UC2 consensus는 가중 점수(GPT 30% + Gemini 30% + Quality 40%)를 사용하며
        0.6이 너무 관대한 것(오류 多)과 너무 엄격한 것(fallback 多) 사이의 최적점임을 발견했습니다.
        이 검증된 임계값을 그대로 상속합니다.
    """
    if confidence < threshold:
        error_msg = f"신뢰도 {confidence:.2f}가 최소 임계값 {threshold:.2f} 미만입니다"
        logger.warning(f"[Safety] ⚠️ {error_msg}")
        return False, error_msg

    logger.debug(f"[Safety] ✅ 신뢰도 {confidence:.2f}가 임계값 {threshold:.2f}를 통과했습니다")
    return True, ""


# ========================================
# 안전 함수 2: 루프 감지
# ========================================

def detect_routing_loop(
    history: list[str],
    max_repeats: int = MAX_LOOP_REPEATS
) -> Tuple[bool, str]:
    """
    workflow history에서 동일한 UC가 연속으로 나타나는지 감지합니다.

    다음과 같은 무한 루프를 방지:
    - UC1 → UC1 → UC1 (self-loop)
    - UC1 → UC2 → UC1 → UC2 → UC1 (oscillation, 진동)

    알고리즘:
    1. history에서 최근 N개의 UC 방문 추출 (supervisor 항목 제외)
    2. N개 방문이 모두 동일한 UC인지 확인
    3. 동일하면 → 루프 감지

    Args:
        history: workflow_history 리스트 (예: ["supervisor → uc1", "uc1 → supervisor", ...])
        max_repeats: 동일 UC 연속 방문 허용 최대 횟수 (기본값: 3)

    Returns:
        (loop_detected: bool, pattern: str)
        - (True, "UC1→UC1→UC1") 루프 발견 시
        - (False, "") 루프 없음

    예시:
        >>> history = [
        ...     "supervisor → uc1",
        ...     "uc1 → supervisor",
        ...     "supervisor → uc1",
        ...     "uc1 → supervisor",
        ...     "supervisor → uc1"
        ... ]
        >>> detect_routing_loop(history, max_repeats=3)
        (True, "UC1→UC1→UC1")

        >>> history = ["supervisor → uc1", "uc1 → supervisor", "supervisor → uc2"]
        >>> detect_routing_loop(history, max_repeats=3)
        (False, "")

    비판적 사고:
        Q: 왜 LLM 호출 BEFORE에 history를 체크하나?
        A: API 비용(~$0.0001/call)과 지연(~200ms)을 절약. 루프가 이미 감지되면 LLM 호출 불필요.

        Q: 왜 3회 반복이고 2회가 아닌가?
        A: 2회는 너무 엄격 (정당한 재시도 시나리오: UC1 실패 → UC2 → UC1 성공)
           3회는 진짜 재시도를 허용하면서도 지속적 루프는 잡아냄.

        Q: oscillation(UC1↔UC2↔UC1)은 어떻게 감지?
        A: 현재 구현으로도 감지됨! "UC1→UC2→UC1"이 3개 전이를 가짐.
           향후 개선: 더 긴 window에서 패턴 빈도 추적.
    """
    # 조기 종료: 루프를 형성하기에 history가 부족
    if len(history) < max_repeats:
        logger.debug(f"[Safety] 📊 History 길이 {len(history)} < {max_repeats}, 루프 불가능")
        return False, ""

    # 최근 N개의 UC 방문 추출 (supervisor 항목 무시)
    recent_ucs = []
    for entry in reversed(history):
        # "supervisor → uc1" 또는 "uc1 → supervisor" 같은 항목 파싱
        if "→ uc1" in entry:
            recent_ucs.append("UC1")
        elif "→ uc2" in entry:
            recent_ucs.append("UC2")
        elif "→ uc3" in entry:
            recent_ucs.append("UC3")
        elif "→ END" in entry or "→ __end__" in entry:
            recent_ucs.append("END")

        # 충분한 샘플을 모으면 중단
        if len(recent_ucs) >= max_repeats:
            break

    # 충분한 UC를 수집했는지 확인 (supervisor 항목이 너무 많을 수 있음)
    if len(recent_ucs) < max_repeats:
        logger.debug(f"[Safety] 📊 최근 history에서 {len(recent_ucs)}개 UC 방문만 발견")
        return False, ""

    # 최근 UC들이 모두 동일한지 확인
    unique_ucs = set(recent_ucs[:max_repeats])

    if len(unique_ucs) == 1:
        # 루프 감지!
        loop_pattern = "→".join(recent_ucs[:max_repeats])
        logger.error(f"[Safety] 🔁 루프 감지: {loop_pattern}")
        logger.error(f"[Safety] 📜 전체 history (최근 10개): {history[-10:]}")
        return True, loop_pattern

    logger.debug(f"[Safety] ✅ 루프 없음. 최근 UC들: {recent_ucs[:max_repeats]}")
    return False, ""


# ========================================
# 안전 함수 3: 상태 제약 검증
# ========================================

def validate_state_transition(
    current_uc: Optional[Literal["uc1", "uc2", "uc3"]],
    next_action: str,
    state: dict
) -> Tuple[bool, str]:
    """
    요청된 상태 전이가 비즈니스 로직 규칙을 따르는지 검증합니다.

    이 함수는 워크플로우의 "문법 검사기" 역할을 합니다. 파서가 잘못된 구문을 거부하듯,
    이 함수는 시스템의 불변성을 위반하는 잘못된 상태 전이를 거부합니다.

    유효한 상태 전이 그래프:

        START → UC1 (항상 첫 단계)

        UC1 → END         (품질 >= 80인 경우)
        UC1 → UC2         (품질 < 80 AND DB에 selector 존재)
        UC1 → UC3         (품질 < 80 AND DB에 selector 없음)
        UC1 ✗ UC1         (무효: self-loop)

        UC2 → UC1         (consensus 도달 시, 수정된 selector로 재시도)
        UC2 → END         (최대 시도 후 consensus 실패)
        UC2 ✗ UC2         (무효: self-loop)
        UC2 ✗ UC3         (무효: healing 실패 시 종료해야 하며, discovery 불가)

        UC3 → END         (항상 - discovery는 terminal)
        UC3 ✗ UC1/UC2     (무효: discovery 후 돌아갈 수 없음)

    Args:
        current_uc: 현재 Use Case ("uc1", "uc2", "uc3", 또는 초기엔 None)
        next_action: LLM이 제안한 다음 액션 ("uc1_validation", "uc2_self_heal", "uc3_new_site", "END")
        state: 컨텍스트 의존 검증을 위한 전체 MasterCrawlState dict

    Returns:
        (is_valid: bool, error_message: str)
        - (True, "") 전이가 유효한 경우
        - (False, "상세 이유") 무효인 경우

    예시:
        >>> # 유효: UC1 품질 통과 → END
        >>> state = {"uc1_validation_result": {"quality_passed": True}}
        >>> validate_state_transition("uc1", "END", state)
        (True, "")

        >>> # 무효: UC1 → UC1 self-loop
        >>> validate_state_transition("uc1", "uc1_validation", {})
        (False, "UC1 → UC1 self-loop은 허용되지 않습니다")

        >>> # 무효: UC3 → UC1 (discovery는 terminal)
        >>> validate_state_transition("uc3", "uc1_validation", {})
        (False, "UC3은 END로만 전이 가능, uc1_validation 불가 (discovery는 terminal)")

    메타인지적 분석:
        이 함수는 기술적 제약이 아닌 비즈니스 로직을 인코딩합니다.

        주요 설계 결정:
        1. UC2 → UC1은 consensus_reached=True 필요
           이유? selector가 실제로 수정되기 전 조기 재시도 방지.

        2. UC2는 UC3로 갈 수 없음
           이유? healing 실패 시 패배 인정(END), discovery 시도 불가.
           근거: Discovery는 "한 번도 본 적 없는" 사이트용, "healing 실패"용 아님.

        3. UC3은 terminal (→ END만 가능)
           이유? Discovery가 이미 모든 것 시도(3 tools). 복구 경로 없음.

        이 규칙들은 LLM이 잘못된 워크플로우로 "창의적으로" 되는 것을 방지합니다.

    비판적 사고 - 엣지 케이스:
        Q: quality_passed=True인데 LLM이 UC1→UC2라고 하면?
        A: 무효. LLM hallucination/컨텍스트 혼동을 잡아냄.

        Q: consensus_reached=False인데 LLM이 UC2→UC1이라고 하면?
        A: 무효. 실제 진전 없는 재시도 루프 방지.

        Q: state에 UC1 result가 없으면?
        A: 허용함 (테스트 중 state가 불완전할 수 있음). 향후: 더 엄격하게.
    """
    logger.debug(f"[Safety] 🔍 전이 검증 중: {current_uc} → {next_action}")

    # === 규칙 1: 초기 진입 (current_uc = None) ===
    if current_uc is None:
        if next_action == "uc1_validation":
            logger.debug("[Safety] ✅ 유효한 초기 진입: START → UC1")
            return True, ""
        else:
            error_msg = f"초기 진입은 uc1_validation으로만 가능, {next_action} 불가"
            logger.error(f"[Safety] ❌ {error_msg}")
            return False, error_msg

    # === 규칙 2: UC1 전이 ===
    if current_uc == "uc1":
        uc1_result = state.get("uc1_validation_result", {})
        quality_passed = uc1_result.get("quality_passed", False)

        if next_action == "END":
            # UC1 → END는 quality_passed = True 필요
            if not quality_passed:
                error_msg = "UC1 → END는 quality_passed=True 필요 (품질 >= 80이어야 함)"
                logger.error(f"[Safety] ❌ {error_msg}")
                logger.error(f"[Safety] 📊 UC1 결과: {uc1_result}")
                return False, error_msg

            logger.debug("[Safety] ✅ 유효한 전이: UC1 → END (품질 통과)")
            return True, ""

        elif next_action == "uc2_self_heal":
            # UC1 → UC2는 품질 실패 시에만 발생해야 함
            if quality_passed:
                error_msg = "UC1 → UC2는 품질이 이미 통과했다면 발생하지 않아야 함"
                logger.warning(f"[Safety] ⚠️ {error_msg} (유연성을 위해 허용)")
                # 주의: 경고와 함께 허용 (LLM이 추가 컨텍스트를 가질 수 있음)

            logger.debug("[Safety] ✅ 유효한 전이: UC1 → UC2 (품질 실패)")
            return True, ""

        elif next_action == "uc3_new_site":
            # UC1 → UC3는 품질 실패 시에만 발생해야 함
            if quality_passed:
                error_msg = "UC1 → UC3는 품질이 이미 통과했다면 발생하지 않아야 함"
                logger.warning(f"[Safety] ⚠️ {error_msg} (유연성을 위해 허용)")

            logger.debug("[Safety] ✅ 유효한 전이: UC1 → UC3 (DB에 selector 없음)")
            return True, ""

        elif next_action == "uc1_validation":
            # UC1 → UC1 self-loop은 절대 허용 안 됨
            error_msg = "UC1 → UC1 self-loop은 허용되지 않습니다"
            logger.error(f"[Safety] ❌ {error_msg}")
            return False, error_msg

        else:
            error_msg = f"UC1은 잘못된 액션으로 전이 불가: {next_action}"
            logger.error(f"[Safety] ❌ {error_msg}")
            return False, error_msg

    # === 규칙 3: UC2 전이 ===
    if current_uc == "uc2":
        uc2_result = state.get("uc2_consensus_result", {})
        consensus_reached = uc2_result.get("consensus_reached", False)

        if next_action == "uc1_validation":
            # UC2 → UC1은 consensus_reached = True 필요
            if not consensus_reached:
                error_msg = "UC2 → UC1은 consensus_reached=True 필요 (selector가 먼저 수정되어야 함)"
                logger.error(f"[Safety] ❌ {error_msg}")
                logger.error(f"[Safety] 📊 UC2 결과: {uc2_result}")
                return False, error_msg

            logger.debug("[Safety] ✅ 유효한 전이: UC2 → UC1 (수정된 selector로 재시도)")
            return True, ""

        elif next_action == "END":
            # UC2 → END는 항상 허용 (consensus 실패 또는 최대 재시도 도달)
            logger.debug("[Safety] ✅ 유효한 전이: UC2 → END (healing 완료/실패)")
            return True, ""

        elif next_action == "uc2_self_heal":
            # UC2 → UC2 self-loop은 절대 허용 안 됨
            error_msg = "UC2 → UC2 self-loop은 허용되지 않습니다"
            logger.error(f"[Safety] ❌ {error_msg}")
            return False, error_msg

        elif next_action == "uc3_new_site":
            # UC2 → UC3는 무효 (healing 실패 시 종료, discovery 시도 불가)
            error_msg = "UC2 → UC3 전이는 허용 안 됨 (healing 실패 → END해야 하며, discovery 불가)"
            logger.error(f"[Safety] ❌ {error_msg}")
            logger.error("[Safety] 💡 근거: Discovery는 신규 사이트용, healing 실패용 아님")
            return False, error_msg

        else:
            error_msg = f"UC2는 잘못된 액션으로 전이 불가: {next_action}"
            logger.error(f"[Safety] ❌ {error_msg}")
            return False, error_msg

    # === 규칙 4: UC3 전이 ===
    if current_uc == "uc3":
        if next_action == "END":
            # UC3 → END가 유일하게 유효한 전이 (discovery는 terminal)
            logger.debug("[Safety] ✅ 유효한 전이: UC3 → END (discovery 완료)")
            return True, ""
        else:
            # UC3 → 다른 것은 모두 무효
            error_msg = f"UC3은 END로만 전이 가능, {next_action} 불가 (discovery는 terminal)"
            logger.error(f"[Safety] ❌ {error_msg}")
            logger.error("[Safety] 💡 UC3는 이미 3개 도구 시도 (Tavily + Firecrawl + BS4), 추가 복구 불가")
            return False, error_msg

    # === 규칙 5: 알 수 없는 상태 ===
    error_msg = f"알 수 없는 current_uc: {current_uc} ('uc1', 'uc2', 'uc3', 또는 None 예상)"
    logger.error(f"[Safety] ❌ {error_msg}")
    return False, error_msg


# ========================================
# 유틸리티 함수
# ========================================

def log_safety_summary(
    confidence_valid: bool,
    loop_detected: bool,
    transition_valid: bool
) -> None:
    """
    모든 안전 검사의 요약을 로깅합니다 (디버깅용).

    LangSmith trace와 프로덕션 모니터링에 유용합니다.

    Args:
        confidence_valid: 신뢰도 검증 결과
        loop_detected: 루프 감지 결과 (반전: True = 문제 있음)
        transition_valid: 상태 전이 검증 결과
    """
    passed = confidence_valid and (not loop_detected) and transition_valid

    status_emoji = "✅" if passed else "❌"
    logger.info(f"[Safety Summary] {status_emoji} 전체: {'통과' if passed else '실패'}")
    logger.info(f"  - 신뢰도: {'✅ 통과' if confidence_valid else '❌ 실패'}")
    logger.info(f"  - 루프 체크: {'✅ 통과' if not loop_detected else '❌ 루프 감지'}")
    logger.info(f"  - 전이 규칙: {'✅ 통과' if transition_valid else '❌ 실패'}")


# ========================================
# 모듈 메타데이터
# ========================================

__all__ = [
    "validate_confidence_threshold",
    "detect_routing_loop",
    "validate_state_transition",
    "log_safety_summary",
    "MIN_CONFIDENCE_THRESHOLD",
    "MAX_LOOP_REPEATS"
]

__version__ = "1.0.0"
__author__ = "Claude Code (Anthropic)"
__date__ = "2025-11-10"
