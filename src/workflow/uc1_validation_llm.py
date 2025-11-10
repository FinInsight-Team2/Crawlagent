"""
UC1 Validation Agent (LLM-Based) - Comparative Analysis Version

목적: LLM 기반 품질 검증 (vs 규칙 기반 비교용)

LLM 사용: GPT-4o-mini (Quality Evaluator)
  - 역할: 뉴스 기사 품질 평가 (5W1H, 광고 구분, 완결성)
  - 입력: title, body, date, url
  - 출력: quality_score (0-100), missing_fields, next_action
  - 예상 시간: ~2-3초 (vs 규칙 기반 100ms)

비교 분석 포인트:
  1. 정확도: 광고/보도자료 구분 능력
  2. 속도: LLM API 호출 시간 (~2s vs ~100ms)
  3. 비용: GPT-4o-mini $0.0003/기사 (vs 규칙 기반 $0)
  4. 일관성: 동일 입력 재평가 시 점수 변동

작성일: 2025-11-10
"""

from typing import TypedDict, Optional, List, Literal
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from loguru import logger
import time
import json


# ============================================================
# State 정의 (규칙 기반과 동일)
# ============================================================

class ValidationStateLLM(TypedDict, total=False):
    """
    LLM 기반 UC1 Validation State

    규칙 기반과 동일한 State 구조를 유지하여
    공정한 비교를 가능하게 합니다.
    """
    # 입력 데이터
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]

    # 검증 결과
    quality_score: int
    missing_fields: List[str]

    # 다음 액션
    next_action: Literal["save", "heal", "new_site"]

    # LLM 분석 결과 (추가)
    llm_reasoning: str  # LLM이 점수를 매긴 이유
    llm_execution_time: float  # LLM 실행 시간 (ms)

    # UC2 연계
    uc2_triggered: bool
    uc2_success: bool


# ============================================================
# LLM 기반 품질 평가 Node
# ============================================================

def llm_evaluate_quality(state: ValidationStateLLM) -> dict:
    """
    Node 1: LLM 기반 품질 평가

    목적:
        GPT-4o-mini를 사용하여 뉴스 기사의 품질을 평가합니다.

    평가 기준:
        1. 5W1H 완결성 (Who, What, When, Where, Why, How)
        2. 광고/보도자료 여부
        3. 본문 길이 적정성
        4. 날짜 정보 존재
        5. 제목 명확성

    입력:
        state: ValidationStateLLM

    출력:
        {
            "quality_score": 85,
            "missing_fields": ["body_short"],
            "llm_reasoning": "제목과 본문이 명확하나 본문이 다소 짧음",
            "llm_execution_time": 2345.67
        }

    비교 포인트:
        - 규칙 기반: 단순 길이/존재 여부 체크
        - LLM 기반: 의미적 품질 평가 (광고 구분 가능)
    """
    start_time = time.time()

    title = state.get("title", "")
    body = state.get("body", "")
    date = state.get("date", "")
    url = state.get("url", "")

    # LLM 초기화
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0  # 일관성을 위해 0으로 설정
    )

    # Prompt 구성
    prompt = f"""당신은 뉴스 기사 품질 평가 전문가입니다.

다음 뉴스 기사를 평가하고 JSON 형식으로 응답하세요.

기사 정보:
- URL: {url}
- 제목: {title if title else "[누락]"}
- 본문: {body[:500] if body else "[누락]"}{'...' if body and len(body) > 500 else ''}
- 날짜: {date if date else "[누락]"}

평가 기준:
1. 5W1H 완결성 (누가, 무엇을, 언제, 어디서, 왜, 어떻게)
2. 광고/보도자료 여부 (광고면 -30점)
3. 본문 길이 적정성 (500자 이상 만점, 200-500자 중간, 200자 미만 낮음)
4. 날짜 정보 존재
5. 제목 명확성 (10자 이상, 의미 명확)

응답 형식 (JSON):
{{
  "quality_score": 85,
  "missing_fields": ["date"],
  "is_advertisement": false,
  "reasoning": "제목과 본문이 명확하며 5W1H가 잘 갖춰져 있으나 날짜 정보가 누락됨"
}}

quality_score: 0-100 (80점 이상이 정상)
missing_fields: 누락되거나 부족한 필드 리스트 (["title", "body", "body_short", "date"] 중)
is_advertisement: 광고 또는 보도자료 여부
reasoning: 점수를 매긴 이유 (1-2문장)

JSON만 응답하세요:"""

    try:
        # LLM 호출
        response = llm.invoke([HumanMessage(content=prompt)])
        execution_time = (time.time() - start_time) * 1000  # ms

        # JSON 파싱
        content = response.content.strip()

        # JSON 추출 (```json ... ``` 형식 처리)
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)

        quality_score = result.get("quality_score", 0)
        missing_fields = result.get("missing_fields", [])
        reasoning = result.get("reasoning", "LLM 평가 완료")

        logger.info(f"[UC1-LLM] Quality Score: {quality_score}, Time: {execution_time:.2f}ms")
        logger.info(f"[UC1-LLM] Reasoning: {reasoning}")

        return {
            "quality_score": quality_score,
            "missing_fields": missing_fields,
            "llm_reasoning": reasoning,
            "llm_execution_time": execution_time
        }

    except Exception as e:
        logger.error(f"[UC1-LLM] LLM 평가 실패: {e}")
        execution_time = (time.time() - start_time) * 1000

        # Fallback: 규칙 기반으로 대체
        logger.warning("[UC1-LLM] Fallback to rule-based evaluation")

        score = 0
        missing = []

        if title and len(title) >= 10:
            score += 20
        else:
            missing.append("title")

        if body:
            if len(body) >= 500:
                score += 60
            elif len(body) >= 200:
                score += 30
                missing.append("body_short")
            else:
                missing.append("body")
        else:
            missing.append("body")

        if date:
            score += 10
        else:
            missing.append("date")

        if url and url.startswith('http'):
            score += 10

        return {
            "quality_score": score,
            "missing_fields": missing,
            "llm_reasoning": f"LLM 실패 (Fallback to rule-based): {str(e)}",
            "llm_execution_time": execution_time
        }


def decide_action_llm(state: ValidationStateLLM) -> dict:
    """
    Node 2: 다음 액션 결정 (규칙 기반과 동일 로직)

    목적:
        quality_score를 기반으로 다음 액션을 결정합니다.

    판정 로직:
        1. quality_score >= 80 → "save"
        2. quality_score < 80 + Selector 존재 → "heal"
        3. quality_score < 80 + Selector 없음 → "new_site"
    """
    from src.storage.database import get_db
    from src.storage.models import Selector

    quality_score = state["quality_score"]
    site_name = state["site_name"]

    # 품질 검증 통과
    if quality_score >= 80:
        logger.info(f"[UC1-LLM] Quality passed ({quality_score} >= 80) → save")
        return {"next_action": "save"}

    # 품질 실패 → Selector 확인
    try:
        db = next(get_db())
        try:
            selector = db.query(Selector).filter_by(site_name=site_name).first()

            if selector:
                logger.info(f"[UC1-LLM] Quality failed, Selector exists → heal")
                return {"next_action": "heal"}
            else:
                logger.info(f"[UC1-LLM] Quality failed, Selector missing → new_site")
                return {"next_action": "new_site"}
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[UC1-LLM] DB error: {e}")
        return {"next_action": "new_site"}


def heal_or_discover_llm(state: ValidationStateLLM) -> dict:
    """
    Node 3: UC2/UC3 분기 처리 (규칙 기반과 동일)

    목적:
        next_action에 따라 UC2 또는 UC3를 트리거합니다.
    """
    next_action = state["next_action"]

    if next_action == "save":
        logger.info("[UC1-LLM] No healing needed, workflow complete")
        return {
            "uc2_triggered": False,
            "uc2_success": False
        }

    elif next_action in ["heal", "new_site"]:
        logger.info(f"[UC1-LLM] Triggering UC2 for {next_action}")

        # UC2 트리거 (실제 구현은 규칙 기반과 동일)
        from src.workflow.uc1_validation import _trigger_uc2

        uc2_result = _trigger_uc2(state)

        return {
            "uc2_triggered": True,
            "uc2_success": uc2_result.get("uc2_success", False),
            "quality_score": uc2_result.get("quality_score", state["quality_score"]),
            "next_action": uc2_result.get("next_action", "save")
        }

    return {}


# ============================================================
# LangGraph 구성
# ============================================================

def create_uc1_llm_agent() -> StateGraph:
    """
    LLM 기반 UC1 Validation Agent 생성

    Workflow:
        START → llm_evaluate_quality → decide_action_llm → heal_or_discover_llm → END

    비교:
        - 규칙 기반: extract → calculate → decide → heal_or_discover
        - LLM 기반: llm_evaluate → decide → heal_or_discover
    """
    graph = StateGraph(ValidationStateLLM)

    # 노드 추가
    graph.add_node("llm_evaluate_quality", llm_evaluate_quality)
    graph.add_node("decide_action_llm", decide_action_llm)
    graph.add_node("heal_or_discover_llm", heal_or_discover_llm)

    # 엣지 연결
    graph.add_edge(START, "llm_evaluate_quality")
    graph.add_edge("llm_evaluate_quality", "decide_action_llm")
    graph.add_edge("decide_action_llm", "heal_or_discover_llm")
    graph.add_edge("heal_or_discover_llm", END)

    return graph.compile()


# ============================================================
# 편의 함수
# ============================================================

def run_llm_validation(
    url: str,
    site_name: str,
    title: Optional[str],
    body: Optional[str],
    date: Optional[str]
) -> dict:
    """
    LLM 기반 검증 실행 (단순 인터페이스)

    사용 예시:
        result = run_llm_validation(
            url="https://...",
            site_name="yonhap",
            title="제목",
            body="본문...",
            date="2025-11-10"
        )

        print(f"Quality Score: {result['quality_score']}")
        print(f"LLM Reasoning: {result['llm_reasoning']}")
        print(f"Execution Time: {result['llm_execution_time']:.2f}ms")
    """
    graph = create_uc1_llm_agent()

    initial_state = {
        "url": url,
        "site_name": site_name,
        "title": title,
        "body": body,
        "date": date,
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
        "uc2_triggered": False,
        "uc2_success": False,
        "llm_reasoning": "",
        "llm_execution_time": 0.0
    }

    result = graph.invoke(initial_state)
    return result
