"""
UC1 Validation Agent - Self-Healing Crawler

목적: 크롤링 결과 품질 검증 및 다음 액션 결정

LLM 사용: 없음 (규칙 기반)
  - 품질 검증은 규칙 기반 로직으로 수행
  - LLM 호출 없이 빠른 실행 (~100ms)
  - UC2/UC3 연계 시에만 LLM 사용

Workflow:
    START
      ↓
    extract_fields (크롤링 결과 읽기)
      ↓
    calculate_quality (5W1H 점수 계산 - 규칙 기반)
      ↓
    decide_action (next_action 결정)
      ↓
    heal_or_discover (UC2/UC3 분기)
      ├─ UC2 Self-Healing (GPT-4o-mini + Gemini)
      └─ UC3 New Site Discovery (GPT-4o)
      ↓
    END (save / heal / new_site)

작성일: 2025-11-02
수정일: 2025-11-10 (LLM 역할 명확화 + Claude 제거)
"""

from typing import List, Literal, Optional, TypedDict

from langgraph.graph import END, START, StateGraph

# ============================================================
# Step 1: State 정의 (데이터 저장소)
# ============================================================


class ValidationState(TypedDict, total=False):
    """
    UC1 Validation Agent State (UC2 자동 연계 지원!)

    설명:
        크롤링 결과를 검증하고 다음 액션을 결정하는 State입니다.
        UC2 자동 복구 실행 시 UC2 관련 필드가 추가됩니다.

    필드 설명:
        url: 크롤링한 기사 URL
        site_name: 사이트 이름 ("yonhap", "naver" 등)
        title: 추출된 제목 (None이면 Selector 실패)
        body: 추출된 본문 (None이면 Selector 실패)
        date: 추출된 날짜 (None이면 Selector 실패)

        quality_score: 0-100 점수 (5W1H 기준)
        missing_fields: 누락된 필드 리스트 (["title", "body"])

        next_action: 다음 액션
            - "save": 정상 → DB 저장
            - "heal": DOM 변경 → UC2 실행 (기존 사이트)
            - "new_site": 신규 사이트 → UC2 실행 (Selector 생성)

        uc2_triggered: UC2 워크플로우 실행 여부 (NEW!)
        uc2_success: UC2 합의 성공 여부 (NEW!)

    예시:
        {
            "url": "https://www.yna.co.kr/view/AKR...",
            "site_name": "yonhap",
            "title": "한중 정상회담...",
            "body": "이재명 대통령과...",
            "date": "2025-11-02 14:30:00",
            "quality_score": 100,
            "missing_fields": [],
            "next_action": "save",
            "uc2_triggered": False,
            "uc2_success": False
        }
    """

    # 입력 데이터 (크롤링 결과)
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]

    # 검증 결과
    quality_score: int
    missing_fields: List[str]
    quality_passed: bool  # NEW: Supervisor가 확인하는 플래그

    # 다음 액션 결정
    next_action: Literal["save", "heal", "uc3"]  # "new_site" → "uc3"로 변경

    # UC1 전체 검증 결과 (Master State 호환)
    uc1_validation_result: Optional[dict]  # NEW: Supervisor에게 전달

    # UC2 자동 연계 (DEPRECATED - Supervisor가 라우팅)
    uc2_triggered: bool
    uc2_success: bool

    # Selector Health Check (NEW: UC2 트리거 개선)
    selector_health: Optional[dict]  # {"title_valid": bool, "body_valid": bool, "date_valid": bool}


# ============================================================
# Step 2: Node 함수 정의 (작업 단위)
# ============================================================


def extract_fields(state: ValidationState) -> dict:
    """
    Node 1: 크롤링 결과 필드 추출

    목적:
        State에서 필요한 필드를 읽어옵니다.
        (실제로는 이미 State에 있으므로 패스 가능)

    입력:
        state: ValidationState (전체)

    출력:
        {} (변경 없음 - 이미 State에 데이터 있음)

    설명 포인트:
        - "왜 이 Node가 필요한가?" → 명시적 단계 구분 (디버깅 편의)
        - "실제론 아무것도 안 하는데?" → 맞습니다! Graph 흐름 명확화용
    """
    # State에 이미 title, body, date가 있으므로 그대로 반환
    # 추후 확장: DB에서 추가 정보 조회 가능
    return {}


def calculate_quality(state: ValidationState) -> dict:
    """
    Node 2: 품질 점수 계산 (5W1H 기준)

    목적:
        크롤링 결과의 품질을 0-100 점수로 계산합니다.

    점수 배분 (개선된 5W1H):
        - Title: 20점 (10자 이상)
        - Body: 60점 (500자 이상 만점, 200자 이상 30점)
        - Date: 10점 (존재 여부)
        - URL: 10점 (http로 시작)

    입력:
        state: ValidationState

    출력:
        {
            "quality_score": 90,
            "missing_fields": ["date"]
        }

    설명 포인트:
        - "왜 Body가 60점인가?" → 본문이 가장 중요, DOM 변경 시 가장 먼저 깨짐
        - "missing_fields는 뭐에 쓰나?" → UC2에서 어떤 Selector 복구할지 판단
    """
    title = state["title"]
    body = state["body"]
    date = state["date"]
    url = state["url"]

    score = 0
    missing = []

    # Title: 20점 (기존 25점에서 감소)
    if title and len(title) >= 10:
        score += 20
    else:
        missing.append("title")

    # Body: 60점 (기존 50점에서 증가!) ← 핵심 개선!
    if body:
        if len(body) >= 500:
            score += 60
        elif len(body) >= 200:
            score += 30  # 짧은 본문 (절반)
            missing.append("body_short")
        else:
            missing.append("body")
    else:
        missing.append("body")

    # Date: 10점 (기존 15점에서 감소)
    if date:
        score += 10
    else:
        missing.append("date")

    # URL: 10점 (유지)
    if url and url.startswith("http"):
        score += 10

    return {"quality_score": score, "missing_fields": missing}


def decide_action(state: ValidationState) -> dict:
    """
    Node 3: 다음 액션 결정 (Supervisor 복귀용)

    목적:
        quality_score와 Selector 존재 여부로 다음 액션을 결정합니다.
        **중요**: UC2/UC3를 직접 호출하지 않고, next_action만 설정하여 Supervisor로 복귀합니다.

    판정 로직:
        1. quality_score >= 80 → "save" (정상, DB 저장)
        2. quality_score < 80 + Selector 존재 → "heal" (UC2 DOM Recovery, Supervisor가 라우팅)
        3. quality_score < 80 + Selector 없음 → "uc3" (UC3 Discovery, Supervisor가 라우팅)

    입력:
        state: ValidationState

    출력:
        {
            "next_action": "save" | "heal" | "uc3",
            "quality_passed": True | False,
            "uc1_validation_result": {
                "quality_passed": bool,
                "quality_score": int,
                "missing_fields": list,
                "next_action": str
            }
        }

    변경 사항 (Multi-Agent Orchestration):
        - "new_site" → "uc3" (Supervisor가 이해하는 형식)
        - quality_passed 플래그 추가 (Supervisor 판단용)
        - uc1_validation_result 추가 (Master State 호환)
        - UC2/UC3 직접 호출 제거 (Supervisor가 라우팅)
    """
    from loguru import logger

    from src.storage.database import get_db
    from src.storage.models import Selector

    quality_score = state["quality_score"]
    missing_fields = state.get("missing_fields", [])
    site_name = state["site_name"]
    selector_health = state.get("selector_health", {})

    # 0. Selector Health Check (NEW: UC2 트리거 개선)
    # Selector가 2개 이상 손상되면 quality와 무관하게 UC2 트리거
    damage_count = sum(1 for v in selector_health.values() if not v)
    if damage_count >= 2:
        logger.warning(
            f"[UC1] ⚠️ Selector damaged ({damage_count}/3 invalid) "
            f"→ Triggering UC2 Self-Healing (quality={quality_score})"
        )
        logger.info(
            f"[UC1] Selector health: title_valid={selector_health.get('title_valid', False)}, "
            f"body_valid={selector_health.get('body_valid', False)}, "
            f"date_valid={selector_health.get('date_valid', False)}"
        )

        validation_result = {
            "quality_passed": False,  # Selector 손상으로 인한 실패
            "quality_score": quality_score,
            "missing_fields": missing_fields,
            "next_action": "heal",
            "selector_damage_count": damage_count,
        }

        return {
            "next_action": "heal",
            "quality_passed": False,
            "uc1_validation_result": validation_result,
        }

    # 1. 품질 검증 통과 (정상)
    if quality_score >= 80:
        logger.info(f"[UC1] ✅ Quality passed (score={quality_score} >= 80) → Supervisor will save")

        validation_result = {
            "quality_passed": True,
            "quality_score": quality_score,
            "missing_fields": missing_fields,
            "next_action": "save",
        }

        return {
            "next_action": "save",
            "quality_passed": True,
            "uc1_validation_result": validation_result,
        }

    # 2. 품질 실패 → Selector 존재 여부 확인
    try:
        db = next(get_db())
        try:
            selector = db.query(Selector).filter_by(site_name=site_name).first()

            if selector:
                # Selector 존재 → DOM 변경 (UC2 Recovery)
                logger.info(
                    f"[UC1] ❌ Quality failed (score={quality_score} < 80), Selector exists → Supervisor will route to UC2"
                )

                validation_result = {
                    "quality_passed": False,
                    "quality_score": quality_score,
                    "missing_fields": missing_fields,
                    "next_action": "heal",
                }

                return {
                    "next_action": "heal",
                    "quality_passed": False,
                    "uc1_validation_result": validation_result,
                }
            else:
                # Selector 없음 → 신규 사이트 (UC3 Discovery)
                logger.info(
                    f"[UC1] ❌ Quality failed (score={quality_score} < 80), Selector missing → Supervisor will route to UC3"
                )

                validation_result = {
                    "quality_passed": False,
                    "quality_score": quality_score,
                    "missing_fields": missing_fields,
                    "next_action": "uc3",
                }

                return {
                    "next_action": "uc3",
                    "quality_passed": False,
                    "uc1_validation_result": validation_result,
                }
        finally:
            db.close()
    except Exception as e:
        # DB 조회 실패 → 안전한 기본값 (uc3)
        logger.error(f"[UC1] DB query failed in decide_action: {e}")
        logger.warning(f"[UC1] Defaulting to 'uc3' (Discovery) for safety")

        validation_result = {
            "quality_passed": False,
            "quality_score": quality_score,
            "missing_fields": missing_fields,
            "next_action": "uc3",
        }

        return {
            "next_action": "uc3",
            "quality_passed": False,
            "uc1_validation_result": validation_result,
        }


# ============================================================
# Step 4: Graph 구성 (State + Nodes + Edges 조합)
# ============================================================


def create_uc1_validation_agent():
    """
    UC1 Validation Agent Graph 생성 (Multi-Agent Orchestration 패턴)

    목적:
        품질 검증을 수행하고 next_action을 설정하여 Supervisor로 복귀합니다.
        **중요**: UC2/UC3를 직접 호출하지 않고, Supervisor에게 라우팅을 위임합니다.

    반환:
        compiled_graph (실행 가능한 Graph 객체)

    사용법:
        # 1. Graph 생성
        graph = create_uc1_validation_agent()

        # 2. 입력 데이터 준비
        inputs = {
            "url": "https://www.yna.co.kr/view/...",
            "site_name": "yonhap",
            "title": "제목",
            "body": "본문...",
            "date": "2025-11-02"
        }

        # 3. 실행
        result = graph.invoke(inputs)

        # 4. 결과 확인
        print(result["next_action"])  # "save", "heal", "uc3"
        print(result["quality_passed"])  # True/False
        print(result["uc1_validation_result"])  # 전체 검증 결과

    Multi-Agent Orchestration 패턴:
        - Graph 구조: START → extract → calculate → decide → END
        - decide_action이 next_action 설정
        - Supervisor가 next_action 읽고 UC2/UC3 라우팅
        - LangSmith Trace에서 Supervisor → UC1 → Supervisor → UC2 경로 확인 가능

    변경 사항:
        - heal_or_discover 노드 제거 (더 이상 불필요)
        - Conditional Edge 제거 (단순한 선형 흐름)
        - decide_action → END 직행 (Supervisor 복귀)
    """
    # Graph 빌더 생성
    builder = StateGraph(ValidationState)

    # Nodes 추가 (단순화된 구조)
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("calculate_quality", calculate_quality)
    builder.add_node("decide_action", decide_action)

    # Edges 연결 (선형 흐름)
    builder.add_edge(START, "extract_fields")
    builder.add_edge("extract_fields", "calculate_quality")
    builder.add_edge("calculate_quality", "decide_action")
    builder.add_edge("decide_action", END)  # Supervisor로 즉시 복귀

    # Graph 컴파일
    return builder.compile()


# ============================================================
# Step 5: 테스트 코드 (실제 사용 예시)
# ============================================================

if __name__ == "__main__":
    """
    UC1 Validation Agent 테스트

    실행 방법:
        cd /Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc
        PYTHONPATH=/Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc \
        poetry run python src/workflow/uc1_validation.py
    """

    print("=" * 60)
    print("UC1 Validation Agent 테스트")
    print("=" * 60)

    # Graph 생성
    graph = create_uc1_validation_agent()

    # 테스트 케이스 1: 정상 기사
    print("\n[TEST 1] 정상 기사 (모든 필드 존재)")
    inputs1 = {
        "url": "https://www.yna.co.kr/view/AKR20251102043351001",
        "site_name": "yonhap",
        "title": "한중정상회담 첫 대좌…관계회복 논의",
        "body": "이재명 대통령과 시진핑 중국 국가주席이 1일 오후 경주 힐튼호텔에서 첫 대면 정상회담을 가졌다..."
        * 20,  # 긴 본문
        "date": "2025-11-02 14:30:00",
        "quality_score": 0,  # 초기값
        "missing_fields": [],  # 초기값
        "next_action": "save",  # 초기값 (덮어써짐)
    }

    result1 = graph.invoke(inputs1)
    print(f"  URL: {result1['url'][:50]}...")
    print(f"  Quality Score: {result1['quality_score']}")
    print(f"  Missing Fields: {result1['missing_fields']}")
    print(f"  Next Action: {result1['next_action']}")
    print(f"  → 예상: quality_score=100, next_action='save'")

    # 테스트 케이스 2: Title 누락 (DOM 변경 시뮬레이션)
    print("\n[TEST 2] Title Selector 실패 (DOM 변경)")
    inputs2 = {
        "url": "https://www.yna.co.kr/view/AKR20251102043351002",
        "site_name": "yonhap",
        "title": None,  # ← Selector 실패!
        "body": "본문 내용..." * 50,
        "date": "2025-11-02",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
    }

    result2 = graph.invoke(inputs2)
    print(f"  URL: {result2['url'][:50]}...")
    print(f"  Quality Score: {result2['quality_score']}")
    print(f"  Missing Fields: {result2['missing_fields']}")
    print(f"  Next Action: {result2['next_action']}")
    print(f"  → 예상: quality_score=80 (Title 0 + Body 60 + Date 10 + URL 10)")
    print(f"  → 예상: next_action='save' (경계선!)")

    # 테스트 케이스 3: Body 누락 (확실한 DOM 변경)
    print("\n[TEST 3] Body Selector 실패 (확실한 DOM 변경)")
    inputs3 = {
        "url": "https://www.yna.co.kr/view/AKR20251102043351003",
        "site_name": "yonhap",
        "title": "제목",
        "body": None,  # ← Selector 실패!
        "date": "2025-11-02",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
    }

    result3 = graph.invoke(inputs3)
    print(f"  URL: {result3['url'][:50]}...")
    print(f"  Quality Score: {result3['quality_score']}")
    print(f"  Missing Fields: {result3['missing_fields']}")
    print(f"  Next Action: {result3['next_action']}")
    print(f"  → 예상: quality_score=40 (Title 20 + Body 0 + Date 10 + URL 10)")
    print(f"  → 예상: next_action='heal' (yonhap Selector 존재)")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

    # Human-in-the-Loop 예시 (주석 처리)
    """
    # HITL이 필요하다면 이렇게:

    from langgraph.checkpoint.memory import MemorySaver

    memory = MemorySaver()
    graph_with_hitl = builder.compile(
        checkpointer=memory,
        interrupt_before=["decide_action"]  # decide_action 전에 멈춤
    )

    config = {"configurable": {"thread_id": "test_001"}}

    # 1. 실행 (중단점까지)
    for event in graph_with_hitl.stream(inputs1, config):
        print(event)
    # → calculate_quality까지 실행 후 멈춤

    # 2. State 확인
    state = graph_with_hitl.get_state(config)
    print("Current quality_score:", state.values["quality_score"])

    # 3. 필요 시 State 수정
    if state.values["quality_score"] == 80:
        graph_with_hitl.update_state(config, {"quality_score": 85})

    # 4. 계속 진행
    graph_with_hitl.stream(None, config)
    """
