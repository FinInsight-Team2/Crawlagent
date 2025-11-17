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

import json
import os
import time
from datetime import datetime
from typing import Literal, Optional, TypedDict

# LangChain imports for Supervisor LLM
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.types import Command
from loguru import logger
from typing_extensions import Annotated

# Phase 1 Safety: Loop detection (Rule-based Supervisor에서 직접 구현)
MAX_LOOP_REPEATS = 3  # 동일 UC 최대 반복 횟수


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
    quality_passed: Optional[bool]
    """UC1 품질 검증 통과 여부 (Supervisor가 확인하는 플래그)"""

    extracted_title: Optional[str]
    """UC1에서 추출한 제목 (전체, DB 저장용)"""

    extracted_body: Optional[str]
    """UC1에서 추출한 본문 (전체, DB 저장용)"""

    extracted_date: Optional[str]
    """UC1에서 추출한 날짜 (전체, DB 저장용)"""

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
        "gpt_validation": {...}
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


def supervisor_node(
    state: MasterCrawlState,
) -> Command[Literal["uc1_validation", "uc2_self_heal", "uc3_new_site", "__end__"]]:
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

    # Check if Distributed Supervisor is enabled (SPOF 해결)
    use_distributed = os.getenv("USE_DISTRIBUTED_SUPERVISOR", "false").lower() == "true"

    if use_distributed:
        # Distributed 3-Model Voting (GPT-4o + Claude + Gemini)
        from src.workflow.distributed_supervisor import distributed_supervisor_decision

        logger.info("[Supervisor] 🚀 Using Distributed 3-Model Voting (SPOF 해결)...")

        decision_result = distributed_supervisor_decision(state)

        next_uc = decision_result["next_uc"]
        confidence = decision_result["confidence"]
        reasoning = decision_result["reasoning"]
        fault_tolerance_used = decision_result["fault_tolerance_used"]

        logger.info(
            f"[Supervisor] ✅ Distributed decision: {next_uc} (conf={confidence:.2f}, FT={fault_tolerance_used})"
        )

        # Convert distributed decision to goto target
        goto_map = {
            "uc1": "uc1_validation",
            "uc2": "uc2_self_heal",
            "uc3": "uc3_new_site",
            "end": END,
        }

        history = state.get("workflow_history", [])
        return Command(
            update={
                "supervisor_reasoning": reasoning,
                "supervisor_confidence": confidence,
                "routing_context": {
                    "mode": "distributed",
                    "individual_votes": decision_result.get("individual_votes", []),
                    "fault_tolerance_used": fault_tolerance_used,
                },
                "workflow_history": history
                + [f"supervisor (distributed) → {next_uc} (conf={confidence:.2f})"],
            },
            goto=goto_map.get(next_uc, END),
        )

    # Rule-based routing (default)
    # 워크플로우 히스토리 추가
    history = state.get("workflow_history", [])
    current_uc = state.get("current_uc")
    next_action = state.get("next_action")
    failure_count = state.get("failure_count", 0)

    # 1. 최초 진입 시: HTML Fetch + UC1 시작
    if not current_uc:
        logger.info("[Supervisor] 📍 Initial entry → Fetching HTML → Routing to UC1")

        # HTML Download (UC3 로직 재사용)
        import requests

        from src.utils.site_detector import extract_site_name

        url = state["url"]
        html_content = None
        site_name = state.get("site_name")

        try:
            logger.info(f"[Supervisor] 🌐 Downloading HTML: {url}")

            # Enhanced headers to bypass bot detection (NYT, WSJ, etc.)
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9,ko;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Cache-Control": "max-age=0",
            }

            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            html_content = response.text

            # site_name이 없으면 URL에서 추출
            if not site_name:
                site_name = extract_site_name(url)

            logger.info(
                f"[Supervisor] ✅ HTML downloaded: {len(html_content)} chars, site={site_name}"
            )

        except Exception as e:
            logger.error(f"[Supervisor] ❌ HTML fetch failed: {e}")
            # HTML fetch 실패 시 UC3로 라우팅 (UC3는 자체 fetch 가능)
            return Command(
                update={
                    "current_uc": "uc3",
                    "next_action": "uc3",
                    "site_name": site_name,
                    "error_message": f"HTML fetch failed: {str(e)}",
                    "workflow_history": history
                    + [f"supervisor → uc3_discovery (HTML fetch error)"],
                },
                goto="uc3_discovery",
            )

        return Command(
            update={
                "current_uc": "uc1",
                "next_action": "uc1",
                "html_content": html_content,
                "site_name": site_name,
                "workflow_history": history + ["supervisor → uc1_validation (HTML fetched)"],
            },
            goto="uc1_validation",
        )

    # 2. UC1 완료 후 판단 (Multi-Agent Orchestration 패턴)
    if current_uc == "uc1":
        uc1_result = state.get("uc1_validation_result")
        quality_passed = state.get("quality_passed", False)

        logger.debug(
            f"[Supervisor] UC1 완료: quality_passed={quality_passed}, uc1_result={uc1_result is not None}"
        )

        # UC1 성공 → DB 저장 후 종료
        if quality_passed:
            quality_score = uc1_result.get("quality_score", 0) if uc1_result else 0
            logger.info(
                f"[Supervisor] ✅ UC1 passed (score={quality_score}) → Saving to DB → Workflow END"
            )

            # DB 저장 로직
            try:
                from datetime import datetime

                from src.storage.database import get_db
                from src.storage.models import CrawlResult

                db = next(get_db())

                # 추출된 데이터 가져오기 (Master State에서 직접 가져옴)
                title = state.get("extracted_title")
                body = state.get("extracted_body")
                date_str = state.get("extracted_date")

                # CrawlResult 생성
                crawl_result = CrawlResult(
                    url=state["url"],
                    site_name=state["site_name"],
                    category=None,  # Gradio에서는 카테고리 없음
                    category_kr=None,
                    title=title,
                    body=body,
                    date=date_str,
                    quality_score=quality_score,
                    crawl_mode="2-agent",  # Master Workflow는 2-agent 모드
                    crawl_duration_seconds=None,
                    content_type="news",
                    validation_status="verified",
                    validation_method="2-agent",
                    llm_reasoning=f"UC1 Quality Validation passed with score {quality_score}",
                )

                # DB에 저장 (중복 체크: URL이 unique key)
                existing = db.query(CrawlResult).filter(CrawlResult.url == state["url"]).first()
                if existing:
                    logger.warning(
                        f"[Supervisor] URL already exists in DB, updating: {state['url']}"
                    )
                    existing.title = title
                    existing.body = body
                    existing.date = date_str
                    existing.quality_score = quality_score
                    existing.validation_status = "verified"
                    existing.llm_reasoning = (
                        f"UC1 Quality Validation passed with score {quality_score}"
                    )
                else:
                    db.add(crawl_result)

                db.commit()
                logger.info(f"[Supervisor] 💾 CrawlResult saved to DB: {state['url']}")

                # Selector success_count 증가
                from src.storage.models import Selector

                selector = (
                    db.query(Selector).filter(Selector.site_name == state["site_name"]).first()
                )
                if selector:
                    selector.success_count += 1
                    db.commit()
                    logger.info(
                        f"[Supervisor] 📈 Selector success_count incremented: {state['site_name']}"
                    )

            except Exception as e:
                logger.error(f"[Supervisor] ❌ Failed to save CrawlResult to DB: {e}")
                # DB 저장 실패해도 워크플로우는 계속 진행 (나중에 재시도 가능)

            return Command(
                update={
                    "next_action": "end",
                    "final_result": {
                        "title": title,
                        "body": body,
                        "date": date_str,
                        "quality_score": quality_score,
                    },
                    "workflow_history": history
                    + [f"supervisor → DB_SAVED → END (UC1 success, score={quality_score})"],
                },
                goto=END,
            )

        # UC1 실패 → next_action 확인하여 UC2 또는 UC3로 라우팅
        if uc1_result:
            uc1_next_action = uc1_result.get("next_action")
            quality_score = uc1_result.get("quality_score", 0)
            current_failure_count = state.get("failure_count", 0)

            # Loop Detection: UC1 연속 실패 3회 초과 시 강제 종료
            if current_failure_count >= 3:
                logger.error(
                    f"[Supervisor] 🛑 Loop Detection: UC1 failed {current_failure_count} times → Force END"
                )
                return Command(
                    update={
                        "next_action": "end",
                        "error_message": f"Loop detected: UC1 failed {current_failure_count} consecutive times",
                        "workflow_history": history
                        + [f"supervisor → END (Loop Detection: {current_failure_count} failures)"],
                    },
                    goto=END,
                )

            # UC2 Self-Healing 라우팅
            if uc1_next_action == "heal":
                logger.info(
                    f"[Supervisor] 🔄 UC1 failed (score={quality_score}, failure={current_failure_count + 1}/3) → Routing to UC2 (Self-Healing)"
                )
                return Command(
                    update={
                        "current_uc": "uc2",
                        "next_action": "uc2",
                        "failure_count": current_failure_count + 1,  # 실패 카운터 증가
                        "workflow_history": history
                        + [
                            f"supervisor → uc2_self_heal (UC1 score={quality_score}, failures={current_failure_count + 1})"
                        ],
                    },
                    goto="uc2_self_heal",
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
                        "failure_count": current_failure_count + 1,  # 실패 카운터 증가
                        "workflow_history": history
                        + [
                            f"supervisor → uc3_new_site (UC1 score={quality_score}, failures={current_failure_count + 1})"
                        ],
                    },
                    goto="uc3_new_site",
                )

            # next_action이 "save"인데 quality_passed=False인 경우 (비정상)
            else:
                logger.warning(
                    f"[Supervisor] ⚠️ UC1 result inconsistent (passed=False, action={uc1_next_action}) → END"
                )
                return Command(
                    update={
                        "next_action": "end",
                        "error_message": f"UC1 inconsistent state: passed=False but action={uc1_next_action}",
                        "workflow_history": history + [f"supervisor → END (UC1 inconsistent)"],
                    },
                    goto=END,
                )

        # uc1_result가 없는 경우 (비정상)
        logger.error("[Supervisor] ❌ UC1 completed but no result found → END")
        return Command(
            update={
                "next_action": "end",
                "error_message": "UC1 completed but no result found (internal error)",
                "workflow_history": history + ["supervisor → END (UC1 no result)"],
            },
            goto=END,
        )

    # 3. UC2 완료 후 판단
    if current_uc == "uc2":
        uc2_result = state.get("uc2_consensus_result")

        # UC2 합의 성공 → Selector UPDATE + DecisionLog INSERT → UC1 복귀
        if uc2_result and uc2_result.get("consensus_reached"):
            consensus_score = uc2_result.get("consensus_score", 0.0)
            logger.info(
                f"[Supervisor] ✅ UC2 consensus reached (score={consensus_score:.2f}) "
                f"→ Updating Selector → Return to UC1"
            )

            # DB 저장 로직
            try:
                from datetime import datetime

                from src.storage.database import get_db
                from src.storage.models import DecisionLog, Selector

                db = next(get_db())

                # 1. Selector UPDATE
                proposed_selectors = uc2_result.get("proposed_selectors", {})
                if proposed_selectors:
                    selector = (
                        db.query(Selector).filter(Selector.site_name == state["site_name"]).first()
                    )
                    if selector:
                        # 기존 Selector 업데이트
                        selector.title_selector = proposed_selectors.get(
                            "title_selector", selector.title_selector
                        )
                        selector.body_selector = proposed_selectors.get(
                            "body_selector", selector.body_selector
                        )
                        selector.date_selector = proposed_selectors.get(
                            "date_selector", selector.date_selector
                        )
                        selector.updated_at = datetime.utcnow()
                        logger.info(f"[Supervisor] 📝 Selector updated for {state['site_name']}")
                    else:
                        # Selector가 없으면 새로 생성 (UC2가 실행되었다는 것은 selector가 있어야 하지만 방어 로직)
                        new_selector = Selector(
                            site_name=state["site_name"],
                            title_selector=proposed_selectors.get("title_selector", ""),
                            body_selector=proposed_selectors.get("body_selector", ""),
                            date_selector=proposed_selectors.get("date_selector", ""),
                            site_type="ssr",
                        )
                        db.add(new_selector)
                        logger.info(
                            f"[Supervisor] ➕ New Selector created for {state['site_name']}"
                        )

                # 2. DecisionLog INSERT
                decision_log = DecisionLog(
                    url=state["url"],
                    site_name=state["site_name"],
                    gpt_analysis=uc2_result.get("gpt_analysis"),
                    gpt4o_validation=uc2_result.get("gpt_validation"),
                    consensus_reached=True,
                    retry_count=uc2_result.get("retry_count", 0),
                    created_at=datetime.utcnow(),
                )
                db.add(decision_log)

                db.commit()
                logger.info(
                    f"[Supervisor] 💾 DecisionLog saved: UC2 consensus reached (score={consensus_score:.2f})"
                )

            except Exception as e:
                logger.error(f"[Supervisor] ❌ Failed to save UC2 results to DB: {e}")
                # DB 저장 실패해도 워크플로우는 계속 진행

            return Command(
                update={
                    "current_uc": "uc1",
                    "next_action": "uc1",
                    "failure_count": 0,  # 실패 카운터 리셋
                    "workflow_history": history
                    + [
                        f"supervisor → SELECTOR_UPDATED → uc1_validation (UC2 consensus {consensus_score:.2f})"
                    ],
                },
                goto="uc1_validation",
            )

        # UC2 합의 실패 → DecisionLog INSERT 후 종료 (관리자 수동 확인 필요)
        else:
            consensus_score = uc2_result.get("consensus_score", 0.0) if uc2_result else 0.0
            logger.warning(
                f"[Supervisor] ❌ UC2 consensus failed (score={consensus_score:.2f}) "
                f"→ Saving DecisionLog → Workflow END"
            )

            # DB 저장 로직 (실패 케이스도 기록)
            try:
                from datetime import datetime

                from src.storage.database import get_db
                from src.storage.models import DecisionLog, Selector

                db = next(get_db())

                # DecisionLog INSERT (실패 케이스)
                decision_log = DecisionLog(
                    url=state["url"],
                    site_name=state["site_name"],
                    gpt_analysis=uc2_result.get("gpt_analysis") if uc2_result else None,
                    gpt4o_validation=uc2_result.get("gpt_validation") if uc2_result else None,
                    consensus_reached=False,
                    retry_count=uc2_result.get("retry_count", 0) if uc2_result else 0,
                    created_at=datetime.utcnow(),
                )
                db.add(decision_log)

                # Selector failure_count 증가
                selector = (
                    db.query(Selector).filter(Selector.site_name == state["site_name"]).first()
                )
                if selector:
                    selector.failure_count += 1
                    logger.info(
                        f"[Supervisor] 📉 Selector failure_count incremented: {state['site_name']}"
                    )

                db.commit()
                logger.info(
                    f"[Supervisor] 💾 DecisionLog saved: UC2 consensus failed (score={consensus_score:.2f})"
                )

            except Exception as e:
                logger.error(f"[Supervisor] ❌ Failed to save UC2 failure to DB: {e}")

            return Command(
                update={
                    "next_action": "end",
                    "error_message": f"UC2 consensus failed (score={consensus_score:.2f})",
                    "workflow_history": history
                    + [
                        f"supervisor → DECISION_LOG_SAVED → END (UC2 consensus failed {consensus_score:.2f})"
                    ],
                },
                goto=END,
            )

    # 4. UC3 완료 후 판단
    if current_uc == "uc3":
        uc3_result = state.get("uc3_discovery_result")

        # UC3 성공 → Selector INSERT → 종료
        if uc3_result and uc3_result.get("selectors_discovered"):
            confidence = uc3_result.get("confidence", 0.0)
            logger.info(
                f"[Supervisor] ✅ UC3 new site discovered (confidence={confidence:.2f}) "
                f"→ Saving Selector to DB → Workflow END"
            )

            # DB 저장 로직
            try:
                from datetime import datetime

                from src.storage.database import get_db
                from src.storage.models import Selector

                db = next(get_db())

                # Selector INSERT
                discovered_selectors = uc3_result.get("selectors_discovered", {})
                if discovered_selectors:
                    # 기존 Selector가 있는지 확인 (중복 방지)
                    existing_selector = (
                        db.query(Selector).filter(Selector.site_name == state["site_name"]).first()
                    )
                    if existing_selector:
                        logger.warning(
                            f"[Supervisor] Selector already exists for {state['site_name']}, updating instead"
                        )
                        # UC3는 title/body/date 키로 반환, title_selector/body_selector/date_selector도 fallback 지원
                        existing_selector.title_selector = discovered_selectors.get(
                            "title", discovered_selectors.get("title_selector", "")
                        )
                        existing_selector.body_selector = discovered_selectors.get(
                            "body", discovered_selectors.get("body_selector", "")
                        )
                        existing_selector.date_selector = discovered_selectors.get(
                            "date", discovered_selectors.get("date_selector", "")
                        )
                        existing_selector.updated_at = datetime.utcnow()
                        logger.info(
                            f"[Supervisor] 📝 Existing Selector updated for {state['site_name']}"
                        )
                    else:
                        # 새로운 Selector 생성
                        # UC3는 title/body/date 키로 반환, title_selector/body_selector/date_selector도 fallback 지원
                        new_selector = Selector(
                            site_name=state["site_name"],
                            title_selector=discovered_selectors.get(
                                "title", discovered_selectors.get("title_selector", "")
                            ),
                            body_selector=discovered_selectors.get(
                                "body", discovered_selectors.get("body_selector", "")
                            ),
                            date_selector=discovered_selectors.get(
                                "date", discovered_selectors.get("date_selector", "")
                            ),
                            site_type="ssr",
                            success_count=0,
                            failure_count=0,
                        )
                        db.add(new_selector)
                        logger.info(
                            f"[Supervisor] ➕ New Selector created for {state['site_name']}"
                        )

                    db.commit()
                    logger.info(
                        f"[Supervisor] 💾 Selector saved: UC3 discovery (confidence={confidence:.2f})"
                    )

            except Exception as e:
                logger.error(f"[Supervisor] ❌ Failed to save UC3 Selector to DB: {e}")

            # UC3 완료 후 UC1 재실행하여 데이터 수집
            logger.info(
                f"[Supervisor] 🔄 UC3 Discovery completed → Routing to UC1 for data collection"
            )
            return Command(
                update={
                    "current_uc": "uc1",
                    "failure_count": 0,  # Reset failure count
                    "workflow_history": history
                    + [f"supervisor → SELECTOR_SAVED → uc1_validation (UC3 success {confidence:.2f})"],
                },
                goto="uc1_validation",
            )

        # UC3 실패 → 종료
        else:
            confidence = uc3_result.get("confidence", 0.0) if uc3_result else 0.0
            logger.warning(
                f"[Supervisor] ❌ UC3 failed (confidence={confidence:.2f}) → Workflow END"
            )
            return Command(
                update={
                    "next_action": "end",
                    "error_message": f"UC3 new site discovery failed (confidence={confidence:.2f} < 0.7)",
                    "workflow_history": history
                    + [f"supervisor → END (UC3 failed, confidence={confidence:.2f})"],
                },
                goto=END,
            )

    # 5. 명시적인 next_action이 있는 경우 (외부에서 지정)
    if next_action == "uc1":
        logger.info("[Supervisor] 📍 Explicit routing → UC1")
        return Command(
            update={
                "current_uc": "uc1",
                "workflow_history": history + ["supervisor → uc1_validation (explicit)"],
            },
            goto="uc1_validation",
        )
    elif next_action == "uc2":
        logger.info("[Supervisor] 📍 Explicit routing → UC2")
        return Command(
            update={
                "current_uc": "uc2",
                "workflow_history": history + ["supervisor → uc2_self_heal (explicit)"],
            },
            goto="uc2_self_heal",
        )
    elif next_action == "uc3":
        logger.info("[Supervisor] 📍 Explicit routing → UC3")
        return Command(
            update={
                "current_uc": "uc3",
                "workflow_history": history + ["supervisor → uc3_new_site (explicit)"],
            },
            goto="uc3_new_site",
        )
    elif next_action == "end":
        logger.info("[Supervisor] 📍 Explicit routing → END")
        return Command(
            update={"workflow_history": history + ["supervisor → END (explicit)"]}, goto=END
        )

    # 6. 기본값: 종료
    logger.info("[Supervisor] 📍 Default routing → END")
    return Command(
        update={"next_action": "end", "workflow_history": history + ["supervisor → END (default)"]},
        goto=END,
    )


# ============================================================================
# UC1 Node Wrapper (기존 UC1 워크플로우 호출)
# ============================================================================

from src.workflow.uc1_validation import ValidationState, create_uc1_validation_agent


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
        import trafilatura
        from bs4 import BeautifulSoup

        from src.storage.database import get_db
        from src.storage.models import Selector

        html_content = state.get("html_content", "")
        site_name = state["site_name"]

        # DB에서 CSS Selector 가져오기
        db = next(get_db())
        selector_record = db.query(Selector).filter(Selector.site_name == site_name).first()

        # Selector가 없으면 빈 데이터로 UC1에 전달 (UC3 케이스)
        if not selector_record:
            logger.warning(
                f"[UC1 Node] No Selector found for {site_name} → Will extract empty data → UC1 will fail → UC3 Discovery"
            )
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
                "uc2_success": False,
            }

            uc1_graph = create_uc1_validation_agent()
            uc1_result = uc1_graph.invoke(uc1_state)

            quality_score = uc1_result.get("quality_score", 0)
            next_action = uc1_result.get("next_action", "uc3")
            quality_passed = uc1_result.get("quality_passed", False)
            uc1_validation_result = uc1_result.get("uc1_validation_result", {})

            logger.info(
                f"[UC1 Node] ✅ No Selector case: score={quality_score}, next_action={next_action} (expected: uc3)"
            )

            return Command(
                update={
                    "quality_passed": False,
                    "uc1_validation_result": (
                        uc1_validation_result
                        if uc1_validation_result
                        else {
                            "quality_passed": False,
                            "quality_score": quality_score,
                            "next_action": next_action,
                            "missing_fields": ["title", "body", "date"],
                            "extracted_data": {"title": None, "body": None, "date": None},
                        }
                    ),
                    "current_uc": "uc1",
                    "workflow_history": state.get("workflow_history", [])
                    + [f"uc1_validation → supervisor (no selector, score={quality_score})"],
                },
                goto="supervisor",
            )

        soup = BeautifulSoup(html_content, "html.parser")

        # Selector Health Check: CSS Selector가 실제로 요소를 찾는지 검증
        selector_health = {
            "title_valid": False,
            "body_valid": False,
            "date_valid": False,
        }

        # Title 추출 + Health Check
        title = None
        title_from_fallback = False
        if selector_record.title_selector:
            try:
                title_elem = soup.select_one(selector_record.title_selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    selector_health["title_valid"] = True  # Selector 유효
                else:
                    logger.warning(f"[UC1 Node] Title selector found no elements: {selector_record.title_selector}")
            except Exception as e:
                logger.warning(f"[UC1 Node] Title extraction failed: {e}")

        # Fallback: meta tag (UC2 Demo Mode에서는 비활성화)
        uc2_demo_mode = os.getenv("UC2_DEMO_MODE", "false").lower() == "true"
        if not title and not uc2_demo_mode:
            meta_title = soup.select_one('meta[property="og:title"]')
            title = meta_title.get("content") if meta_title else None
            if title:
                title_from_fallback = True
                logger.debug(f"[UC1 Node] Title fallback (meta tag) succeeded")

        # Date 추출 + Health Check
        date_str = None
        date_from_fallback = False
        if selector_record.date_selector:
            try:
                date_elem = soup.select_one(selector_record.date_selector)
                if date_elem:
                    date_str = date_elem.get_text(strip=True) if date_elem.name != "meta" else date_elem.get("content")
                    # Meta 태그는 항상 유효하다고 간주 (fallback이 아님)
                    if selector_record.date_selector.startswith("meta"):
                        selector_health["date_valid"] = True
                    else:
                        selector_health["date_valid"] = True
                else:
                    logger.warning(f"[UC1 Node] Date selector found no elements: {selector_record.date_selector}")
            except Exception as e:
                logger.warning(f"[UC1 Node] Date extraction failed: {e}")

        # Fallback: meta tag (UC2 Demo Mode에서는 비활성화)
        if not date_str and not uc2_demo_mode:
            meta_date = soup.select_one('meta[property="article:published_time"]')
            date_str = meta_date.get("content") if meta_date else None
            if date_str:
                date_from_fallback = True
                logger.debug(f"[UC1 Node] Date fallback (meta tag) succeeded")

        # Body 추출 + Health Check
        body = None
        body_from_fallback = False

        # 먼저 CSS Selector 시도 (Health Check용)
        if selector_record.body_selector:
            try:
                body_elements = soup.select(selector_record.body_selector)
                if body_elements:
                    body = " ".join([elem.get_text(strip=True) for elem in body_elements])
                    if len(body) >= 100:
                        selector_health["body_valid"] = True  # Selector 유효
                    else:
                        logger.warning(f"[UC1 Node] Body selector found elements but text too short: {len(body)} chars")
                else:
                    logger.warning(f"[UC1 Node] Body selector found no elements: {selector_record.body_selector}")
            except Exception as e:
                logger.warning(f"[UC1 Node] Body extraction failed: {e}")

        # Fallback: Trafilatura (UC2 Demo Mode에서는 비활성화)
        if (not body or len(body) < 100) and not uc2_demo_mode:
            body = trafilatura.extract(
                html_content,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
                favor_precision=True,
                favor_recall=False,
            )
            if body and len(body) >= 100:
                body_from_fallback = True
                logger.debug(f"[UC1 Node] Body fallback (Trafilatura) succeeded: {len(body)} chars")

        # Selector Health 로깅
        damage_count = sum(1 for v in selector_health.values() if not v)
        logger.info(
            f"[UC1 Node] Extracted: title={bool(title)}, body_len={len(body) if body else 0}, date={bool(date_str)}"
        )
        logger.info(
            f"[UC1 Node] Selector Health: title_valid={selector_health['title_valid']}, "
            f"body_valid={selector_health['body_valid']}, date_valid={selector_health['date_valid']} "
            f"(damage_count={damage_count}/3)"
        )

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
            "uc2_success": False,
            "selector_health": selector_health,  # Selector 유효성 정보 전달
        }

        # 4. UC1 워크플로우 실행
        uc1_result = uc1_graph.invoke(uc1_state)

        # 5. 결과 분석 (UC1이 이미 quality_passed 계산)
        quality_score = uc1_result.get("quality_score", 0)
        next_action = uc1_result.get("next_action", "save")
        quality_passed = uc1_result.get("quality_passed", False)  # UC1에서 계산된 값 사용
        uc1_validation_result = uc1_result.get("uc1_validation_result", {})

        logger.info(
            f"[UC1 Node] ✅ Validation completed: quality_score={quality_score}, next_action={next_action}, passed={quality_passed}"
        )

        # 6. Master State 업데이트 + supervisor로 라우팅
        return Command(
            update={
                "quality_passed": quality_passed,  # Supervisor가 확인하는 플래그
                "extracted_title": title,  # 전체 제목 (DB 저장용)
                "extracted_body": body,  # 전체 본문 (DB 저장용)
                "extracted_date": date_str,  # 전체 날짜 (DB 저장용)
                "uc1_validation_result": (
                    uc1_validation_result
                    if uc1_validation_result
                    else {
                        "quality_passed": quality_passed,
                        "quality_score": quality_score,
                        "next_action": next_action,
                        "missing_fields": uc1_result.get("missing_fields", []),
                        "extracted_data": {
                            "title": title,
                            "body": body[:500] if body else "",  # 첫 500자만 저장 (preview용)
                            "date": date_str,
                        },
                    }
                ),
                "current_uc": "uc1",
                "workflow_history": state.get("workflow_history", [])
                + [f"uc1_validation → supervisor (score={quality_score}, passed={quality_passed})"],
            },
            goto="supervisor",
        )

    except Exception as e:
        logger.error(f"[UC1 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc1_validation_result": {
                    "quality_passed": False,
                    "quality_score": 0,
                    "next_action": "uc3",  # UC1 에러 시 UC3로 라우팅
                    "error_message": str(e),
                },
                "quality_passed": False,
                "next_action": "uc3",  # 명시적으로 uc3 설정
                "error_message": f"UC1 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", [])
                + [f"uc1_validation → supervisor (ERROR: {str(e)}, next=uc3)"],
            },
            goto="supervisor",
        )


# ============================================================================
# UC2 Node Wrapper (기존 UC2 워크플로우 호출)
# ============================================================================

from src.workflow.uc2_hitl import HITLState, build_uc2_graph


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
            "gpt_validation": None,
            "consensus_reached": False,
            "retry_count": 0,
            "final_selectors": None,
            "error_message": None,
            "next_action": None,
        }

        # 3. UC2 워크플로우 실행
        uc2_result = uc2_graph.invoke(uc2_state)

        # 4. 결과 분석
        # FIX Bug #3: uc2_result가 None일 수 있으므로 defensive coding
        if uc2_result is None:
            raise ValueError("UC2 workflow returned None instead of valid dict")

        consensus_reached = uc2_result.get("consensus_reached", False)
        final_selectors = uc2_result.get("final_selectors")

        # 합의 점수 계산 (UC2에서 계산한 값 사용)
        gpt_proposal = uc2_result.get("gpt_proposal", {})
        gpt_validation = uc2_result.get("gpt_validation", {})

        gpt_confidence = gpt_proposal.get("confidence", 0.0) if gpt_proposal else 0.0
        gpt4o_confidence = gpt_validation.get("confidence", 0.0) if gpt_validation else 0.0

        # 간단한 합의 점수 (실제로는 uc2_hitl.py의 calculate_consensus_score 사용)
        consensus_score = (
            gpt_confidence * 0.3
            + gpt4o_confidence * 0.3
            + (1.0 if consensus_reached else 0.0) * 0.4
        )

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
                    "gpt_validation": gpt_validation,
                },
                "current_uc": "uc2",
                "workflow_history": state.get("workflow_history", [])
                + [
                    f"uc2_self_heal → supervisor (consensus={consensus_reached}, score={consensus_score:.2f})"
                ],
            },
            goto="supervisor",
        )

    except Exception as e:
        logger.error(f"[UC2 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc2_consensus_result": {
                    "consensus_reached": False,
                    "consensus_score": 0.0,
                    "error_message": str(e),
                },
                "error_message": f"UC2 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", [])
                + [f"uc2_self_heal → supervisor (ERROR: {str(e)})"],
            },
            goto="supervisor",
        )


# ============================================================================
# UC3 Node Wrapper (기존 UC3 워크플로우 호출)
# ============================================================================

from src.workflow.uc3_new_site import UC3State, create_uc3_agent

# meta_extractor import removed - JSON-LD handled inside UC3 StateGraph now


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
        # JSON-LD extraction is now handled inside UC3 StateGraph (extract_json_ld_node)
        # Removed redundant code from master workflow (line 986-1021)

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
            "error_message": None,
        }

        # 3. UC3 워크플로우 실행
        uc3_result = uc3_graph.invoke(uc3_state)

        # 4. 결과 분석
        discovered_selectors = uc3_result.get("discovered_selectors")
        # UC3는 consensus_score를 반환, confidence도 fallback 지원
        confidence = uc3_result.get("consensus_score", uc3_result.get("confidence", 0.0))

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
                    "claude_analysis": uc3_result.get("claude_analysis"),
                },
                "current_uc": "uc3",
                "workflow_history": state.get("workflow_history", [])
                + [f"uc3_new_site → supervisor (confidence={confidence:.2f})"],
            },
            goto="supervisor",
        )

    except Exception as e:
        logger.error(f"[UC3 Node] ❌ Error: {e}")

        return Command(
            update={
                "uc3_discovery_result": {
                    "selectors_discovered": None,
                    "confidence": 0.0,
                    "error_message": str(e),
                },
                "error_message": f"UC3 failed: {str(e)}",
                "workflow_history": state.get("workflow_history", [])
                + [f"uc3_new_site → supervisor (ERROR: {str(e)})"],
            },
            goto="supervisor",
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

    # Check if Distributed Supervisor is enabled
    use_distributed_supervisor = os.getenv("USE_DISTRIBUTED_SUPERVISOR", "false").lower() == "true"

    if use_distributed_supervisor:
        logger.info("[build_master_graph] 🚀 Using Distributed 3-Model Supervisor (SPOF 해결)")
    else:
        logger.info("[build_master_graph] 📋 Using Rule-based Supervisor")

    # 1. StateGraph 생성
    workflow = StateGraph(MasterCrawlState)

    # 2. Node 추가
    workflow.add_node("supervisor", supervisor_node)
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

    # HTTP retry logic with exponential backoff
    permanent_status_codes = {400, 401, 403, 404, 410}
    transient_status_codes = {429, 500, 502, 503, 504}
    max_retries = 3
    html_content = None
    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                test_url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()
            html_content = response.text
            logger.info(f"[Test] ✅ HTML fetched successfully (attempt={attempt+1})")
            break

        except requests.exceptions.HTTPError as http_error:
            last_error = http_error
            status_code = http_error.response.status_code if http_error.response else None

            # Permanent errors - do not retry
            if status_code in permanent_status_codes:
                logger.error(f"[Test] ❌ Permanent HTTP error {status_code}, aborting")
                raise

            # Transient errors - retry with exponential backoff
            elif status_code in transient_status_codes:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1
                    logger.warning(
                        f"[Test] ⚠️ Transient HTTP error {status_code} (attempt={attempt+1}), retrying after {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[Test] ❌ Max retries reached for HTTP {status_code}")
                    raise

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_error:
            last_error = conn_error
            if attempt < max_retries - 1:
                wait_time = (2**attempt) * 1
                logger.warning(
                    f"[Test] ⚠️ Network error (attempt={attempt+1}), retrying after {wait_time}s"
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[Test] ❌ Max retries reached for network error")
                raise

    if html_content is None:
        raise Exception(f"Failed to fetch HTML after {max_retries} attempts: {last_error}")

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
        "workflow_history": [],
    }

    # 4. Master Graph 실행
    logger.info("[Test] 🚀 Running Master Graph...")
    final_state = master_app.invoke(initial_state)

    # 5. 결과 출력
    logger.info("\n" + "=" * 80)
    logger.info("[Test] 📊 Master Graph Execution Result")
    logger.info("=" * 80)
    logger.info(f"Workflow History: {final_state.get('workflow_history')}")
    logger.info(f"UC1 Result: {final_state.get('uc1_validation_result')}")
    logger.info(f"UC2 Result: {final_state.get('uc2_consensus_result')}")
    logger.info(f"UC3 Result: {final_state.get('uc3_discovery_result')}")
    logger.info(f"Error: {final_state.get('error_message')}")
    logger.info("=" * 80)
