"""
CrawlAgent - Master Workflow (Multi-Agent Orchestration)
Created: 2025-11-09
Updated: 2025-11-10 (LLM 역할 명확화)

LangGraph Master Graph: UC1 → UC2 → UC3 통합 워크플로우

LLM 사용 전략 (2-Agent System):
=======================================
UC1 (Quality Validation): LLM 없음 (규칙 기반)
  - 실행 시간: ~100ms
  - 품질 검증만 수행

UC2 (Self-Healing): 2-Agent Consensus
  - Agent 1: GPT-4o-mini (Proposer) - CSS Selector 제안
  - Agent 2: Gemini-2.0-flash (Validator) - Selector 검증
  - Weighted Consensus: GPT 30% + Gemini 30% + Extraction 40%
  - Threshold: 0.6

UC3 (New Site Discovery): 1-Agent
  - Agent: GPT-4o (Discoverer) - DOM 분석 + Selector 생성
  - Confidence: 0.0 ~ 1.0

공식 LangGraph 패턴 사용:
=======================================
1. Agent Supervisor Pattern (LangGraph 공식)
   - Supervisor가 UC1/UC2/UC3를 조건부 라우팅
   - 각 Use Case별 전문 Agent 역할 분담

2. Conditional Edges (LangGraph 공식 API)
   - add_conditional_edges() 메서드 사용
   - State 기반 동적 라우팅

3. Command API (2025년 신규)
   - Command(update={...}, goto="next_node")
   - State 업데이트와 라우팅을 동시에 수행
   - 더 직관적인 멀티 에이전트 통신

아키텍처:
==========

    START
      ↓
  supervisor (UC1/UC2/UC3 라우팅 결정)
      ↓
    ┌─────────────────┐
    │  uc1_validation │ (Quality Check)
    │  uc2_self_heal  │ (2-Agent Consensus)
    │  uc3_new_site   │ (New Site Discovery)
    └─────────────────┘
      ↓
  supervisor (다음 액션 결정)
      ↓
    END


워크플로우 시나리오:
==================

시나리오 1: UC1 성공 (정상 크롤링)
  START → supervisor → uc1_validation (성공) → supervisor → END

시나리오 2: UC1 실패 → UC2 자동 트리거 (Self-Healing)
  START → supervisor → uc1_validation (3회 실패) → supervisor → uc2_self_heal → supervisor → END

시나리오 3: 새로운 사이트 발견 시 UC3 트리거
  START → supervisor → uc3_new_site → supervisor → END


PoC 범위:
=========
- LangGraph Multi-Agent 자동화 검증
- LangGraph Studio를 통한 워크플로우 시각화
- Gradio UI로 실행 결과 확인
- DB에 로그 기록 (DecisionLog, CrawlResult 등)

Production 범위 (PoC 제외):
==========================
- Slack 알림 연동
- FastAPI Webhook 서버
- 실시간 알림 시스템
"""

from typing import TypedDict, Optional, Literal
from typing_extensions import Annotated
from langgraph.graph import StateGraph, END
from langgraph.types import Command
from loguru import logger
import os
import json
from datetime import datetime

# LangChain imports for Supervisor LLM
from langchain_openai import ChatOpenAI


# ============================================================================
# Master State Definition
# ============================================================================

class MasterCrawlState(TypedDict):
    """
    Master Workflow의 State 정의

    모든 Use Case (UC1/UC2/UC3)에서 공통으로 사용하는 State
    각 UC는 자신의 State를 이 Master State의 서브셋으로 사용
    """

    # === 입력 데이터 ===
    url: str
    """크롤링 대상 URL"""

    site_name: str
    """사이트 이름 (예: 'yonhap', 'bbc', 'cnn')"""

    html_content: Optional[str]
    """fetch한 HTML 원본"""

    # === 워크플로우 제어 ===
    current_uc: Optional[Literal["uc1", "uc2", "uc3"]]
    """현재 실행 중인 Use Case"""

    next_action: Optional[Literal["uc1", "uc2", "uc3", "end"]]
    """다음에 실행할 Use Case"""

    failure_count: int
    """UC1 연속 실패 횟수 (3회 실패 시 UC2 트리거)"""

    # === UC1 결과 ===
    uc1_validation_result: Optional[dict]
    """
    UC1 Quality Validation 결과
    {
        "quality_passed": True/False,
        "gpt_analysis": {...},
        "extracted_data": {...}
    }
    """

    # === UC2 결과 ===
    uc2_consensus_result: Optional[dict]
    """
    UC2 Self-Healing 결과
    {
        "consensus_reached": True/False,
        "consensus_score": 0.85,
        "proposed_selectors": {...},
        "gpt_analysis": {...},
        "gemini_validation": {...}
    }
    """

    # === UC3 결과 ===
    uc3_discovery_result: Optional[dict]
    """
    UC3 New Site Discovery 결과
    {
        "selectors_discovered": {...},
        "confidence": 0.90,
        "claude_analysis": {...}
    }
    """

    # === 최종 출력 ===
    final_result: Optional[dict]
    """최종 크롤링 결과 (DB 저장용)"""

    error_message: Optional[str]
    """에러 발생 시 메시지"""

    workflow_history: list[str]
    """워크플로우 실행 히스토리 (디버깅/모니터링용)"""

    # === Supervisor LLM 관련 (NEW) ===
    supervisor_reasoning: Optional[str]
    """Supervisor의 라우팅 결정 이유 (GPT-4o-mini 추론 결과)"""

    supervisor_confidence: Optional[float]
    """Supervisor의 결정 신뢰도 (0.0-1.0)"""

    routing_context: Optional[dict]
    """
    라우팅 컨텍스트 (오류 패턴, 히스토리 분석 등)
    {
        "timestamp": "...",
        "decision": "uc1_validation" | "uc2_self_heal" | "uc3_new_site" | "END",
        "state_snapshot": {...}
    }
    """


# ============================================================================
# Supervisor Node (Agent Supervisor Pattern - 공식 LangGraph 패턴)
# ============================================================================

def supervisor_node(state: MasterCrawlState) -> Command[Literal["uc1_validation", "uc2_self_heal", "uc3_new_site", "__end__"]]:
    """
    Supervisor Agent: UC1/UC2/UC3 라우팅 결정

    공식 LangGraph Agent Supervisor Pattern 사용:
    - Supervisor가 현재 State를 분석하여 다음 Agent 결정
    - Command API로 State 업데이트 + 라우팅을 동시에 수행

    라우팅 로직:
    1. 최초 진입 시 → UC1 (Quality Validation)
    2. UC1 3회 연속 실패 → UC2 (Self-Healing)
    3. 새로운 사이트 발견 시 → UC3 (New Site Discovery)
    4. 모든 작업 완료 시 → END

    Args:
        state: MasterCrawlState

    Returns:
        Command: State 업데이트 + goto 라우팅
    """
    logger.info("[Supervisor] 🎯 Routing decision started")

    # 워크플로우 히스토리 추가
    history = state.get("workflow_history", [])
    current_uc = state.get("current_uc")
    next_action = state.get("next_action")
    failure_count = state.get("failure_count", 0)

    # 1. 최초 진입 시: UC1 시작
    if not current_uc:
        logger.info("[Supervisor] 📍 Initial entry → Routing to UC1 (Quality Validation)")
        return Command(
            update={
                "current_uc": "uc1",
                "next_action": "uc1",
                "workflow_history": history + ["supervisor → uc1_validation"]
            },
            goto="uc1_validation"
        )

    # 2. UC1 완료 후 판단 (Multi-Agent Orchestration 패턴)
    if current_uc == "uc1":
        uc1_result = state.get("uc1_validation_result")
        quality_passed = state.get("quality_passed", False)

        # UC1 성공 → 종료
        if quality_passed:
            quality_score = uc1_result.get("quality_score", 0) if uc1_result else 0
            logger.info(f"[Supervisor] ✅ UC1 passed (score={quality_score}) → Workflow END")
            return Command(
                update={
                    "next_action": "end",
                    "workflow_history": history + [f"supervisor → END (UC1 success, score={quality_score})"]
                },
                goto=END
            )

        # UC1 실패 → next_action 확인하여 UC2 또는 UC3로 라우팅
        if uc1_result:
            uc1_next_action = uc1_result.get("next_action")
            quality_score = uc1_result.get("quality_score", 0)

            # UC2 Self-Healing 라우팅
            if uc1_next_action == "heal":
                logger.info(
                    f"[Supervisor] 🔄 UC1 failed (score={quality_score}) → Routing to UC2 (Self-Healing)"
                )
                return Command(
                    update={
                        "current_uc": "uc2",
                        "next_action": "uc2",
                        "workflow_history": history + [f"supervisor → uc2_self_heal (UC1 score={quality_score})"]
                    },
                    goto="uc2_self_heal"
                )

            # UC3 Discovery 라우팅
            elif uc1_next_action == "uc3":
                logger.info(
                    f"[Supervisor] 🔍 UC1 failed (score={quality_score}) → Routing to UC3 (New Site Discovery)"
                )
                return Command(
                    update={
                        "current_uc": "uc3",
                        "next_action": "uc3",
                        "workflow_history": history + [f"supervisor → uc3_new_site (UC1 score={quality_score})"]
                    },
                    goto="uc3_new_site"
                )

            # next_action이 "save"인데 quality_passed=False인 경우 (비정상)
            else:
                logger.warning(
                    f"[Supervisor] ⚠️ UC1 result inconsistent (passed=False, action={uc1_next_action}) → END"
                )
                return Command(
                    update={
                        "next_action": "end",
                        "workflow_history": history + [f"supervisor → END (UC1 inconsistent)"]
                    },
                    goto=END
                )

        # uc1_result가 없는 경우 (비정상)
        logger.error("[Supervisor] ❌ UC1 completed but no result found → END")
        return Command(
            update={
                "next_action": "end",
                "workflow_history": history + ["supervisor → END (UC1 no result)"]
            },
            goto=END
        )

    # 3. UC2 완료 후 판단
    if current_uc == "uc2":
        uc2_result = state.get("uc2_consensus_result")

        # UC2 합의 성공 → UC1 복귀 (새로운 Selector로 재시도)
        if uc2_result and uc2_result.get("consensus_reached"):
            consensus_score = uc2_result.get("consensus_score", 0.0)
            logger.info(
                f"[Supervisor] ✅ UC2 consensus reached (score={consensus_score:.2f}) "
                f"→ Return to UC1 with new selectors"
            )
            return Command(
                update={
                    "current_uc": "uc1",
                    "next_action": "uc1",
                    "failure_count": 0,  # 실패 카운터 리셋
                    "workflow_history": history + [f"supervisor → uc1_validation (UC2 consensus {consensus_score:.2f})"]
                },
                goto="uc1_validation"
            )

        # UC2 합의 실패 → DecisionLog 생성 후 종료 (PoC: 관리자가 DB 확인)
        else:
            consensus_score = uc2_result.get("consensus_score", 0.0) if uc2_result else 0.0
            logger.warning(
                f"[Supervisor] ❌ UC2 consensus failed (score={consensus_score:.2f}) "
                f"→ Workflow END (DecisionLog created)"
            )
            return Command(
                update={
                    "next_action": "end",
                    "workflow_history": history + [f"supervisor → END (UC2 consensus failed {consensus_score:.2f})"]
                },
                goto=END
            )

    # 4. UC3 완료 후 판단
    if current_uc == "uc3":
        uc3_result = state.get("uc3_discovery_result")

        # UC3 성공 → 종료 (새로운 사이트 Selector가 DB에 저장됨)
        if uc3_result and uc3_result.get("selectors_discovered"):
            confidence = uc3_result.get("confidence", 0.0)
            logger.info(
                f"[Supervisor] ✅ UC3 new site discovered (confidence={confidence:.2f}) "
                f"→ Workflow END"
            )
            return Command(
                update={
                    "next_action": "end",
                    "workflow_history": history + [f"supervisor → END (UC3 success {confidence:.2f})"]
                },
                goto=END
            )

        # UC3 실패 → 종료
        else:
            logger.warning("[Supervisor] ❌ UC3 failed → Workflow END")
            return Command(
                update={
                    "next_action": "end",
                    "workflow_history": history + ["supervisor → END (UC3 failed)"]
                },
                goto=END
            )

    # 5. 명시적인 next_action이 있는 경우 (외부에서 지정)
    if next_action == "uc1":
        logger.info("[Supervisor] 📍 Explicit routing → UC1")
        return Command(
            update={
                "current_uc": "uc1",
                "workflow_history": history + ["supervisor → uc1_validation (explicit)"]
            },
            goto="uc1_validation"
        )
    elif next_action == "uc2":
        logger.info("[Supervisor] 📍 Explicit routing → UC2")
        return Command(
            update={
                "current_uc": "uc2",
                "workflow_history": history + ["supervisor → uc2_self_heal (explicit)"]
            },
            goto="uc2_self_heal"
        )
    elif next_action == "uc3":
        logger.info("[Supervisor] 📍 Explicit routing → UC3")
        return Command(
            update={
                "current_uc": "uc3",
                "workflow_history": history + ["supervisor → uc3_new_site (explicit)"]
            },
            goto="uc3_new_site"
        )
    elif next_action == "end":
        logger.info("[Supervisor] 📍 Explicit routing → END")
        return Command(
            update={
                "workflow_history": history + ["supervisor → END (explicit)"]
            },
            goto=END
        )

    # 6. 기본값: 종료
    logger.info("[Supervisor] 📍 Default routing → END")
    return Command(
        update={
            "next_action": "end",
            "workflow_history": history + ["supervisor → END (default)"]
        },
        goto=END
    )


def supervisor_llm_node(state: MasterCrawlState) -> Command[Literal["uc1_validation", "uc2_self_heal", "uc3_new_site", "__end__"]]:
    """
    Supervisor Agent with LLM (GPT-4o-mini)

    목적:
        - 규칙 기반 if-else 대신 LLM으로 지능형 라우팅
        - 복잡한 edge case 처리
        - 컨텍스트 기반 판단
        - 자가 설명 (reasoning 제공)

    장점:
        - 유연한 판단 (예: UC1 실패 원인에 따라 UC2/UC3 선택)
        - 히스토리 분석 (반복 실패 패턴 인식)
        - 확장 가능 (새로운 UC 추가 시 코드 변경 최소화)

    Args:
        state: MasterCrawlState

    Returns:
        Command: State 업데이트 + goto 라우팅 (LLM 추론 결과 포함)
    """
    logger.info("[Supervisor LLM] 🧠 GPT-4o-mini intelligent routing started")

    # State 분석
    current_uc = state.get("current_uc")
    workflow_history = state.get("workflow_history", [])

    # LLM에 전달할 컨텍스트 구성
    context = {
        "current_uc": current_uc,
        "url": state.get("url", "unknown"),
        "site_name": state.get("site_name", "unknown"),
        "workflow_history": workflow_history[-5:] if len(workflow_history) > 5 else workflow_history,  # 최근 5개만
    }

    # UC별 결과 추가
    if current_uc == "uc1":
        uc1_result = state.get("uc1_validation_result")
        if uc1_result:
            context["uc1_result"] = {
                "quality_score": uc1_result.get("quality_score", 0),
                "quality_passed": state.get("quality_passed", False),
                "next_action": uc1_result.get("next_action", "unknown")
            }

    elif current_uc == "uc2":
        uc2_result = state.get("uc2_consensus_result")
        if uc2_result:
            context["uc2_result"] = {
                "consensus_reached": uc2_result.get("consensus_reached", False),
                "consensus_score": uc2_result.get("consensus_score", 0.0)
            }

    elif current_uc == "uc3":
        uc3_result = state.get("uc3_discovery_result")
        if uc3_result:
            context["uc3_result"] = {
                "selectors_discovered": uc3_result.get("selectors_discovered") is not None,
                "confidence": uc3_result.get("confidence", 0.0)
            }

    # 최초 진입 시 (current_uc 없음)
    if not current_uc:
        context["first_entry"] = True

    # GPT-4o-mini 호출
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

        prompt = f"""You are an intelligent Supervisor for a multi-agent web crawling system.

Your job is to analyze the current state and decide the next action.

**Current State**:
```json
{json.dumps(context, indent=2, ensure_ascii=False)}
```

**Available Actions**:
1. "uc1_validation" - Quality validation (rule-based, no LLM)
2. "uc2_self_heal" - Self-healing with 2-Agent consensus (GPT-4o-mini + Gemini)
3. "uc3_new_site" - New site discovery with 3-Tool + 2-Agent (GPT-4o + Gemini)
4. "END" - End workflow

**Decision Rules**:
- If first_entry=true: Start with "uc1_validation"
- If uc1 passed (quality_passed=true): "END"
- If uc1 failed AND next_action="heal": "uc2_self_heal"
- If uc1 failed AND next_action="uc3": "uc3_new_site"
- If uc2 consensus_reached=true: "uc1_validation" (retry with new selectors)
- If uc2 consensus_reached=false: "END" (human review needed)
- If uc3 success: "END"
- If uc3 failed: "END"

**Return JSON format**:
{{
    "next_action": "uc1_validation" | "uc2_self_heal" | "uc3_new_site" | "END",
    "reasoning": "Clear explanation of why this decision was made",
    "confidence": 0.0-1.0
}}

**IMPORTANT**: Be concise and follow the rules strictly. Return ONLY valid JSON.
"""

        response = llm.invoke([{"role": "user", "content": prompt}])

        # JSON 파싱
        try:
            decision = json.loads(response.content)
        except:
            # Fallback: extract JSON from markdown
            import re
            json_match = re.search(r'```json\n(.*?)\n```', response.content, re.DOTALL)
            if json_match:
                decision = json.loads(json_match.group(1))
            else:
                raise ValueError(f"Failed to parse LLM response: {response.content}")

        next_action = decision["next_action"]
        reasoning = decision.get("reasoning", "No reasoning provided")
        confidence = decision.get("confidence", 0.0)

        logger.info(f"[Supervisor LLM] 🎯 Decision: {next_action} (confidence={confidence:.2f})")
        logger.info(f"[Supervisor LLM] 💭 Reasoning: {reasoning}")

        # 라우팅 매핑
        routing_map = {
            "uc1_validation": "uc1_validation",
            "uc2_self_heal": "uc2_self_heal",
            "uc3_new_site": "uc3_new_site",
            "END": END
        }

        goto_target = routing_map.get(next_action, END)

        # State 업데이트
        update_dict = {
            "supervisor_reasoning": reasoning,
            "supervisor_confidence": confidence,
            "workflow_history": workflow_history + [f"supervisor_llm → {next_action} (LLM conf={confidence:.2f})"],
            "routing_context": {
                "timestamp": datetime.now().isoformat(),
                "decision": next_action,
                "llm_confidence": confidence,
                "state_snapshot": context
            }
        }

        # current_uc 업데이트 (END가 아닌 경우)
        if next_action != "END":
            uc_map = {
                "uc1_validation": "uc1",
                "uc2_self_heal": "uc2",
                "uc3_new_site": "uc3"
            }
            update_dict["current_uc"] = uc_map.get(next_action)
            update_dict["next_action"] = uc_map.get(next_action)
        else:
            update_dict["next_action"] = "end"

        return Command(
            update=update_dict,
            goto=goto_target
        )

    except Exception as e:
        logger.error(f"[Supervisor LLM] ❌ LLM routing failed: {e}")
        logger.warning("[Supervisor LLM] 🔄 Falling back to rule-based supervisor")

        # Fallback: 기존 rule-based supervisor 호출
        return supervisor_node(state)


# ============================================================================
# UC1 Node Wrapper (기존 UC1 워크플로우 호출)
# ============================================================================

from src.workflow.uc1_validation import create_uc1_validation_agent, ValidationState

def uc1_validation_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    """
    UC1 Quality Validation Node

    기존 UC1 LangGraph 워크플로우를 호출하여 품질 검증 수행

    Command API 사용:
    - 기존 UC1 워크플로우 실행
    - 결과를 Master State에 업데이트
    - supervisor로 다시 라우팅

    Args:
        state: MasterCrawlState

    Returns:
        Command: UC1 결과 업데이트 + supervisor로 라우팅
    """
    logger.info("[UC1 Node] 🔍 Quality Validation started")

    try:
        # 1. HTML에서 title, body, date 추출 (UC1은 추출된 데이터를 검증)
        from bs4 import BeautifulSoup
        import trafilatura
        from src.storage.database import get_db
        from src.storage.models import Selector

        html_content = state.get("html_content", "")
        site_name = state["site_name"]

        # DB에서 CSS Selector 가져오기
        db = next(get_db())
        selector_record = db.query(Selector).filter(Selector.site_name == site_name).first()

        # Selector가 없으면 빈 데이터로 UC1에 전달 (UC3 케이스)
        if not selector_record:
            logger.warning(f"[UC1 Node] No Selector found for {site_name} → Will extract empty data → UC1 will fail → UC3 Discovery")
            # UC1에 빈 데이터 전달
            uc1_state: ValidationState = {
                "url": state["url"],
                "site_name": state["site_name"],
                "title": None,
                "body": None,
                "date": None,
                "quality_score": 0,
                "missing_fields": [],
                "next_action": "save",
                "uc2_triggered": False,
                "uc2_success": False
            }

            uc1_graph = create_uc1_validation_agent()
            uc1_result = uc1_graph.invoke(uc1_state)

            quality_score = uc1_result.get("quality_score", 0)
            next_action = uc1_result.get("next_action", "uc3")
            quality_passed = uc1_result.get("quality_passed", False)
            uc1_validation_result = uc1_result.get("uc1_validation_result", {})

            logger.info(f"[UC1 Node] ✅ No Selector case: score={quality_score}, next_action={next_action} (expected: uc3)")

            return Command(
                update={
                    "quality_passed": False,
                    "uc1_validation_result": uc1_validation_result if uc1_validation_result else {
                        "quality_passed": False,
                        "quality_score": quality_score,
                        "next_action": next_action,
                        "missing_fields": ["title", "body", "date"],
                        "extracted_data": {
                            "title": None,
                            "body": None,
                            "date": None
                        }
                    },
                    "current_uc": "uc1",
                    "workflow_history": state.get("workflow_history", []) + [f"uc1_validation → supervisor (no selector, score={quality_score})"]
                },
                goto="supervisor"
            )

        soup = BeautifulSoup(html_content, 'html.parser')

        # Title 추출
        title = None
        if selector_record.title_selector:
            try:
                title_elem = soup.select_one(selector_record.title_selector)
                title = title_elem.get_text(strip=True) if title_elem else None
            except Exception as e:
                logger.warning(f"[UC1 Node] Title extraction failed: {e}")

        # Fallback: meta tag
        if not title:
            meta_title = soup.select_one('meta[property="og:title"]')
            title = meta_title.get('content') if meta_title else None

        # Date 추출
        date_str = None
        if selector_record.date_selector:
            try:
                date_elem = soup.select_one(selector_record.date_selector)
                date_str = date_elem.get_text(strip=True) if date_elem else None
            except Exception as e:
                logger.warning(f"[UC1 Node] Date extraction failed: {e}")

        # Fallback: meta tag
        if not date_str:
            meta_date = soup.select_one('meta[property="article:published_time"]')
            date_str = meta_date.get('content') if meta_date else None

        # Body 추출 (Trafilatura 우선)
        body = trafilatura.extract(
            html_content,
            include_comments=False,
            include_tables=False,
            no_fallback=False,
            favor_precision=True,
            favor_recall=False
        )

        # Fallback: CSS Selector
        if not body or len(body) < 100:
            if selector_record.body_selector:
                try:
                    body_elements = soup.select(selector_record.body_selector)
                    body = ' '.join([elem.get_text(strip=True) for elem in body_elements])
                except Exception as e:
                    logger.warning(f"[UC1 Node] Body extraction failed: {e}")
                    body = ""

        logger.info(f"[UC1 Node] Extracted: title={bool(title)}, body_len={len(body) if body else 0}, date={bool(date_str)}")

        # 2. UC1 Graph 빌드
        uc1_graph = create_uc1_validation_agent()

        # 3. Master State → UC1 State 변환 (추출된 데이터 전달)
        uc1_state: ValidationState = {
            "url": state["url"],
            "site_name": state["site_name"],
            "title": title,
            "body": body,
            "date": date_str,
            "quality_score": 0,
            "missing_fields": [],
            "next_action": "save",
            "uc2_triggered": False,
            "uc2_success": False
        }

        # 4. UC1 워크플로우 실행
        uc1_result = uc1_graph.invoke(uc1_state)

        # 5. 결과 분석 (UC1이 이미 quality_passed 계산)
        quality_score = uc1_result.get("quality_score", 0)
        next_action = uc1_result.get("next_action", "save")
        quality_passed = uc1_result.get("quality_passed", False)  # UC1에서 계산된 값 사용
        uc1_validation_result = uc1_result.get("uc1_validation_result", {})

        logger.info(f"[UC1 Node] ✅ Validation completed: quality_score={quality_score}, next_action={next_action}, passed={quality_passed}")

        # 6. Master State 업데이트 + supervisor로 라우팅
        return Command(
            update={
                "quality_passed": quality_passed,  # Supervisor가 확인하는 플래그
                "uc1_validation_result": uc1_validation_result if uc1_validation_result else {
                    "quality_passed": quality_passed,
                    "quality_score": quality_score,
                    "next_action": next_action,
                    "missing_fields": uc1_result.get("missing_fields", []),
                    "extracted_data": {
                        "title": title,
                        "body": body[:500] if body else "",  # 첫 500자만 저장
                        "date": date_str
                    }
                },
                "current_uc": "uc1",
                "workflow_history": state.get("workflow_history", []) + [f"uc1_validation → supervisor (score={quality_score}, passed={quality_passed})"]
            },
            goto="supervisor"
        )

    except Exception as e:
        logger.error(f"[UC1 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc1_validation_result": {
                    "quality_passed": False,
                    "error_message": str(e)
                },
                "error_message": f"UC1 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", []) + [f"uc1_validation → supervisor (ERROR: {str(e)})"]
            },
            goto="supervisor"
        )


# ============================================================================
# UC2 Node Wrapper (기존 UC2 워크플로우 호출)
# ============================================================================

from src.workflow.uc2_hitl import build_uc2_graph, HITLState

def uc2_self_heal_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    """
    UC2 Self-Healing Node (2-Agent Consensus)

    기존 UC2 LangGraph 워크플로우를 호출하여 CSS Selector 자동 복구 수행

    Multi-Agent Consensus:
    - GPT-4o-mini: CSS Selector 제안 (Proposer)
    - Gemini-2.0-flash: Selector 검증 (Validator)
    - Weighted Consensus: GPT 30% + Gemini 30% + Extraction Quality 40%

    Args:
        state: MasterCrawlState

    Returns:
        Command: UC2 결과 업데이트 + supervisor로 라우팅
    """
    logger.info("[UC2 Node] 🔧 Self-Healing started (2-Agent Consensus)")

    try:
        # 1. UC2 Graph 빌드
        uc2_graph = build_uc2_graph()

        # 2. Master State → UC2 State 변환
        uc2_state: HITLState = {
            "url": state["url"],
            "site_name": state["site_name"],
            "html_content": state.get("html_content"),
            "gpt_proposal": None,
            "gemini_validation": None,
            "consensus_reached": False,
            "retry_count": 0,
            "final_selectors": None,
            "error_message": None,
            "next_action": None
        }

        # 3. UC2 워크플로우 실행
        uc2_result = uc2_graph.invoke(uc2_state)

        # 4. 결과 분석
        consensus_reached = uc2_result.get("consensus_reached", False)
        final_selectors = uc2_result.get("final_selectors")

        # 합의 점수 계산 (UC2에서 계산한 값 사용)
        gpt_proposal = uc2_result.get("gpt_proposal", {})
        gemini_validation = uc2_result.get("gemini_validation", {})

        gpt_confidence = gpt_proposal.get("confidence", 0.0)
        gemini_confidence = gemini_validation.get("confidence", 0.0)

        # 간단한 합의 점수 (실제로는 uc2_hitl.py의 calculate_consensus_score 사용)
        consensus_score = (gpt_confidence * 0.3 + gemini_confidence * 0.3 + (1.0 if consensus_reached else 0.0) * 0.4)

        logger.info(
            f"[UC2 Node] ✅ Self-Healing completed: "
            f"consensus_reached={consensus_reached}, score={consensus_score:.2f}"
        )

        # 5. Master State 업데이트 + supervisor로 라우팅
        return Command(
            update={
                "uc2_consensus_result": {
                    "consensus_reached": consensus_reached,
                    "consensus_score": round(consensus_score, 2),
                    "proposed_selectors": final_selectors,
                    "gpt_analysis": gpt_proposal,
                    "gemini_validation": gemini_validation
                },
                "current_uc": "uc2",
                "workflow_history": state.get("workflow_history", []) + [
                    f"uc2_self_heal → supervisor (consensus={consensus_reached}, score={consensus_score:.2f})"
                ]
            },
            goto="supervisor"
        )

    except Exception as e:
        logger.error(f"[UC2 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc2_consensus_result": {
                    "consensus_reached": False,
                    "consensus_score": 0.0,
                    "error_message": str(e)
                },
                "error_message": f"UC2 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", []) + [f"uc2_self_heal → supervisor (ERROR: {str(e)})"]
            },
            goto="supervisor"
        )


# ============================================================================
# UC3 Node Wrapper (기존 UC3 워크플로우 호출)
# ============================================================================

from src.workflow.uc3_new_site import create_uc3_agent, UC3State

def uc3_new_site_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    """
    UC3 New Site Discovery Node

    기존 UC3 LangGraph 워크플로우를 호출하여 새로운 사이트 CSS Selector 발견

    GPT-4o 사용:
    - DOM 구조 분석
    - Semantic HTML 이해
    - CSS Selector 자동 생성
    - Confidence: 0.0 ~ 1.0

    Args:
        state: MasterCrawlState

    Returns:
        Command: UC3 결과 업데이트 + supervisor로 라우팅
    """
    logger.info("[UC3 Node] 🆕 New Site Discovery started")

    try:
        # 1. UC3 Graph 빌드
        uc3_graph = create_uc3_agent()

        # 2. Master State → UC3 State 변환
        uc3_state: UC3State = {
            "url": state["url"],
            "site_name": state["site_name"],
            "html_content": state.get("html_content"),
            "claude_analysis": None,
            "discovered_selectors": None,
            "confidence": 0.0,
            "error_message": None
        }

        # 3. UC3 워크플로우 실행
        uc3_result = uc3_graph.invoke(uc3_state)

        # 4. 결과 분석
        discovered_selectors = uc3_result.get("discovered_selectors")
        confidence = uc3_result.get("confidence", 0.0)

        logger.info(
            f"[UC3 Node] ✅ Discovery completed: "
            f"selectors_found={bool(discovered_selectors)}, confidence={confidence:.2f}"
        )

        # 5. Master State 업데이트 + supervisor로 라우팅
        return Command(
            update={
                "uc3_discovery_result": {
                    "selectors_discovered": discovered_selectors,
                    "confidence": confidence,
                    "claude_analysis": uc3_result.get("claude_analysis")
                },
                "current_uc": "uc3",
                "workflow_history": state.get("workflow_history", []) + [
                    f"uc3_new_site → supervisor (confidence={confidence:.2f})"
                ]
            },
            goto="supervisor"
        )

    except Exception as e:
        logger.error(f"[UC3 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc3_discovery_result": {
                    "selectors_discovered": None,
                    "confidence": 0.0,
                    "error_message": str(e)
                },
                "error_message": f"UC3 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", []) + [f"uc3_new_site → supervisor (ERROR: {str(e)})"]
            },
            goto="supervisor"
        )


# ============================================================================
# Master Graph 구성 (Conditional Edges 사용)
# ============================================================================

def build_master_graph():
    """
    Master Crawl Workflow Graph 생성

    공식 LangGraph 패턴 통합:

    1. Agent Supervisor Pattern:
       - supervisor_node가 UC1/UC2/UC3를 조건부 라우팅
       - 각 UC는 전문화된 Agent 역할

    2. Conditional Edges:
       - add_conditional_edges() 메서드 사용 (이미 UC2에서 사용 중)

    3. Command API:
       - Command(update={...}, goto="node_name")
       - State 업데이트 + 라우팅을 동시에 수행

    Phase 4 Enhancement:
       - USE_SUPERVISOR_LLM 환경변수로 LLM vs Rule-based 선택
       - LLM: GPT-4o-mini intelligent routing with reasoning
       - Rule-based: 안정적인 if-else 로직 (기본값)

    Returns:
        Compiled LangGraph app

    그래프 구조:

        START
          ↓
       supervisor ←─────────┐
       (LLM or Rule-based)  │
          ↓                 │
        ┌─────────────────┐ │
        │ uc1_validation  │─┤
        │ uc2_self_heal   │─┤
        │ uc3_new_site    │─┘
        └─────────────────┘
          ↓
        END
    """
    logger.info("[build_master_graph] 🏗️  Building Master LangGraph StateGraph...")

    # Phase 4: Supervisor 선택 로직
    use_llm_supervisor = os.getenv("USE_SUPERVISOR_LLM", "false").lower() == "true"

    if use_llm_supervisor:
        supervisor_func = supervisor_llm_node
        logger.info("[build_master_graph] 🧠 Using LLM Supervisor (GPT-4o-mini)")
    else:
        supervisor_func = supervisor_node
        logger.info("[build_master_graph] 📋 Using Rule-based Supervisor (if-else)")

    # 1. StateGraph 생성
    workflow = StateGraph(MasterCrawlState)

    # 2. Node 추가
    workflow.add_node("supervisor", supervisor_func)
    workflow.add_node("uc1_validation", uc1_validation_node)
    workflow.add_node("uc2_self_heal", uc2_self_heal_node)
    workflow.add_node("uc3_new_site", uc3_new_site_node)

    # 3. Entry Point 설정
    workflow.set_entry_point("supervisor")

    # 4. Edge 추가
    # Command API를 사용하므로 각 노드가 자체적으로 라우팅 결정
    # supervisor → UC1/UC2/UC3/END (Command.goto로 결정)
    # UC1/UC2/UC3 → supervisor (항상 supervisor로 복귀)

    # Note: Command API를 사용하면 add_edge가 불필요함
    # 각 노드의 Command.goto가 자동으로 라우팅 처리

    # 5. Compile
    app = workflow.compile()

    logger.info("[build_master_graph] ✅ Master StateGraph compiled successfully")

    return app


# ============================================================================
# 사용 예시 (테스트용)
# ============================================================================

if __name__ == "__main__":
    """
    Master Graph 테스트 실행

    Usage:
        PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/workflow/master_crawl_workflow.py
    """
    import requests

    # 1. Master Graph 빌드
    master_app = build_master_graph()

    # 2. 테스트 입력
    test_url = "https://www.yonhapnewstv.co.kr/news/MYH20251107014400038"

    logger.info(f"[Test] Fetching HTML from {test_url}")
    response = requests.get(test_url, timeout=10)
    html_content = response.text

    # 3. 초기 State
    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "yonhap",
        "html_content": html_content,
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": []
    }

    # 4. Master Graph 실행
    logger.info("[Test] 🚀 Running Master Graph...")
    final_state = master_app.invoke(initial_state)

    # 5. 결과 출력
    logger.info("\n" + "="*80)
    logger.info("[Test] 📊 Master Graph Execution Result")
    logger.info("="*80)
    logger.info(f"Workflow History: {final_state.get('workflow_history')}")
    logger.info(f"UC1 Result: {final_state.get('uc1_validation_result')}")
    logger.info(f"UC2 Result: {final_state.get('uc2_consensus_result')}")
    logger.info(f"UC3 Result: {final_state.get('uc3_discovery_result')}")
    logger.info(f"Error: {final_state.get('error_message')}")
    logger.info("="*80)
