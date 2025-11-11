#!/usr/bin/env python3
"""
Phase 4 테스트 (UC3): LLM Supervisor with UC3 New Site Discovery

목적:
- UC3는 Gemini를 사용하지 않으므로 quota 문제 없음
- LLM Supervisor가 UC3로 라우팅하는지 검증
- LangSmith 트레이싱에서 reasoning 확인
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState


def test_uc3_with_llm_supervisor():
    """UC3 Discovery with LLM Supervisor"""

    logger.info("=" * 80)
    logger.info("Phase 4 Test: UC3 New Site Discovery with LLM Supervisor")
    logger.info("=" * 80)

    # 환경변수: LLM Supervisor 활성화
    os.environ["USE_SUPERVISOR_LLM"] = "true"

    # Master Graph 빌드
    master_app = build_master_graph()

    # 테스트 URL: 신규 사이트 (DB에 selector 없음)
    test_url = "https://example-new-site.com/article/12345"

    # 초기 State (UC3 시뮬레이션: selector 없음)
    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "example_new_site",
        "html_content": "<html><head><title>Test Article</title></head><body><h1>Example Title</h1><p>Article content here</p></body></html>",
        "raw_html": "<html><head><title>Test Article</title></head><body><h1>Example Title</h1><p>Article content here</p></body></html>",
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": [],
        "supervisor_reasoning": None,
        "supervisor_confidence": None,
        "routing_context": None,

        # UC3 트리거 조건: DB에 selector 없음 시뮬레이션
        # (실제로는 DB 쿼리 결과가 None이지만, 여기서는 State로 흉내)
        "selectors": None,  # DB에 selector 없음을 의미
    }

    logger.info("[TEST] 🚀 Starting Master Crawl Workflow...")
    logger.info(f"[TEST] URL: {test_url}")
    logger.info("[TEST] Expected flow: supervisor → UC1 → (selector 없음) → UC3")

    try:
        # 워크플로우 실행
        # 주의: UC1에서 selector가 없으면 next_action='discover'로 설정됨
        # Supervisor는 이를 감지하고 UC3로 라우팅해야 함

        final_state = master_app.invoke(initial_state)

        logger.info("[TEST] ✅ Workflow completed")
        logger.info(f"[TEST] Workflow history: {final_state.get('workflow_history', [])}")

        # LLM Supervisor 결과 출력
        logger.info("\n" + "=" * 80)
        logger.info("🧠 LLM Supervisor Reasoning Log")
        logger.info("=" * 80)

        if final_state.get('supervisor_reasoning'):
            logger.info(f"Final Reasoning: {final_state.get('supervisor_reasoning')}")
            logger.info(f"Final Confidence: {final_state.get('supervisor_confidence')}")
            logger.info(f"Routing Context: {final_state.get('routing_context')}")
        else:
            logger.warning("No supervisor reasoning found in final state")

        # UC3 결과 확인
        uc3_result = final_state.get('uc3_discovery_result')
        if uc3_result:
            logger.info("\n" + "=" * 80)
            logger.info("🔍 UC3 Discovery Result")
            logger.info("=" * 80)
            logger.info(f"Consensus Reached: {uc3_result.get('consensus_reached', False)}")
            logger.info(f"Consensus Score: {uc3_result.get('consensus_score', 0.0)}")
            logger.info(f"Proposed Selectors: {uc3_result.get('proposed_selectors', {})}")

        logger.info("\n" + "=" * 80)
        logger.info("✅ Phase 4 Test Completed Successfully")
        logger.info("=" * 80)
        logger.info("🔍 Check LangSmith Trace:")
        logger.info("   URL: https://smith.langchain.com/")
        logger.info("   Project: crawlagent-poc")
        logger.info("   Look for: supervisor_llm node with reasoning outputs")
        logger.info("=" * 80)

        return final_state

    except Exception as e:
        logger.error(f"[TEST] ❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    # UC3 테스트는 실제 HTML을 사용하므로 Naver News로 테스트
    logger.info("🔄 Switching to real UC3 scenario with Naver News...")

    import requests

    # 환경변수: LLM Supervisor 활성화
    os.environ["USE_SUPERVISOR_LLM"] = "true"

    master_app = build_master_graph()

    # Naver News: UC3 시나리오 (신규 사이트로 가정)
    test_url = "https://n.news.naver.com/mnews/article/009/0005587223"

    logger.info(f"Fetching HTML from {test_url}")
    response = requests.get(test_url, timeout=10)
    html_content = response.text

    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "naver_news_new",  # 신규 사이트로 가정
        "html_content": html_content,
        "raw_html": html_content,
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": [],
        "supervisor_reasoning": None,
        "supervisor_confidence": None,
        "routing_context": None,
    }

    logger.info("🚀 Starting workflow with LLM Supervisor...")
    logger.info("Expected: UC1 → (DB no selector) → Supervisor → UC3")

    final_state = master_app.invoke(initial_state)

    logger.info("\n" + "=" * 80)
    logger.info("📊 Final Results")
    logger.info("=" * 80)
    logger.info(f"Workflow History:\n{chr(10).join(final_state.get('workflow_history', []))}")
    logger.info(f"\nFinal Supervisor Reasoning: {final_state.get('supervisor_reasoning', 'N/A')}")
    logger.info(f"Final Supervisor Confidence: {final_state.get('supervisor_confidence', 'N/A')}")
    logger.info("=" * 80)
