#!/usr/bin/env python3
"""
Phase 4 테스트: Supervisor LLM vs Rule-based 비교

테스트 시나리오:
1. Rule-based Supervisor (USE_SUPERVISOR_LLM=false)
   - UC1 → Quality Pass → END
   - UC1 → Quality Fail → UC2 → Success → END
   - UC1 → UC2 Fail → UC3 → Success → END

2. LLM Supervisor (USE_SUPERVISOR_LLM=true)
   - 동일한 시나리오 반복
   - LLM reasoning 로그 확인
   - LangSmith trace 검증
"""

import os
import sys
import requests
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

# Load environment
load_dotenv()

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState


def run_test_scenario(scenario_name: str, url: str, site_name: str, use_llm: bool):
    """단일 시나리오 테스트"""

    logger.info("=" * 80)
    logger.info(f"[TEST] Scenario: {scenario_name}")
    logger.info(f"[TEST] Supervisor Mode: {'LLM (GPT-4o-mini)' if use_llm else 'Rule-based (if-else)'}")
    logger.info(f"[TEST] URL: {url}")
    logger.info("=" * 80)

    # 환경변수 설정
    os.environ["USE_SUPERVISOR_LLM"] = "true" if use_llm else "false"

    # Master Graph 빌드
    master_app = build_master_graph()

    # HTML 다운로드
    logger.info(f"[TEST] Fetching HTML from {url}")
    try:
        response = requests.get(url, timeout=10)
        html_content = response.text
        logger.info(f"[TEST] HTML fetched: {len(html_content)} bytes")
    except Exception as e:
        logger.error(f"[TEST] Failed to fetch HTML: {e}")
        return None

    # 초기 State
    initial_state: MasterCrawlState = {
        "url": url,
        "site_name": site_name,
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

    # 워크플로우 실행
    logger.info("[TEST] 🚀 Starting Master Crawl Workflow...")

    try:
        final_state = master_app.invoke(initial_state)

        logger.info("[TEST] ✅ Workflow completed successfully")
        logger.info(f"[TEST] Workflow history: {final_state.get('workflow_history', [])}")

        # LLM Supervisor 결과 출력
        if use_llm:
            logger.info("[TEST] 🧠 LLM Supervisor Results:")
            logger.info(f"  - Reasoning: {final_state.get('supervisor_reasoning', 'N/A')}")
            logger.info(f"  - Confidence: {final_state.get('supervisor_confidence', 'N/A')}")
            logger.info(f"  - Routing Context: {final_state.get('routing_context', 'N/A')}")

        # 최종 결과
        final_result = final_state.get('final_result')
        if final_result:
            logger.info(f"[TEST] 📊 Final Result:")
            logger.info(f"  - Status: {final_result.get('status', 'unknown')}")
            logger.info(f"  - Title: {final_result.get('title', 'N/A')[:50]}")
            logger.info(f"  - Body Length: {len(final_result.get('body', ''))}")

        return final_state

    except Exception as e:
        logger.error(f"[TEST] ❌ Workflow failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def main():
    """Phase 4 통합 테스트"""

    logger.info("=" * 80)
    logger.info("Phase 4: Supervisor LLM Integration Test")
    logger.info("=" * 80)

    # 테스트 시나리오
    scenarios = [
        {
            "name": "UC1 Success (Yonhap News)",
            "url": "https://www.yonhapnewstv.co.kr/news/MYH20251107014400038",
            "site_name": "yonhap",
            "expected": "UC1 → Quality Pass → END"
        },
        # {
        #     "name": "UC1 → UC2 (Naver News with pattern change)",
        #     "url": "https://n.news.naver.com/mnews/article/009/0005587223",
        #     "site_name": "naver",
        #     "expected": "UC1 → Fail → UC2 → Success → END"
        # },
    ]

    results = []

    # 1. Rule-based Supervisor 테스트
    logger.info("\n" + "=" * 80)
    logger.info("🔹 PHASE 1: Rule-based Supervisor Test")
    logger.info("=" * 80 + "\n")

    for scenario in scenarios:
        result = run_test_scenario(
            scenario_name=scenario["name"],
            url=scenario["url"],
            site_name=scenario["site_name"],
            use_llm=False
        )
        results.append(("Rule-based", scenario["name"], result))
        logger.info("\n" + "-" * 80 + "\n")

    # 2. LLM Supervisor 테스트
    logger.info("\n" + "=" * 80)
    logger.info("🔹 PHASE 2: LLM Supervisor Test (GPT-4o-mini)")
    logger.info("=" * 80 + "\n")

    for scenario in scenarios:
        result = run_test_scenario(
            scenario_name=scenario["name"],
            url=scenario["url"],
            site_name=scenario["site_name"],
            use_llm=True
        )
        results.append(("LLM", scenario["name"], result))
        logger.info("\n" + "-" * 80 + "\n")

    # 3. 결과 비교
    logger.info("\n" + "=" * 80)
    logger.info("📊 Test Results Summary")
    logger.info("=" * 80)

    for mode, name, result in results:
        status = "✅ SUCCESS" if result and result.get('final_result') else "❌ FAILED"
        logger.info(f"[{mode:12}] {name:40} → {status}")

    logger.info("=" * 80)
    logger.info("🔍 LangSmith Trace: https://smith.langchain.com/")
    logger.info("   Project: crawlagent-poc")
    logger.info("=" * 80)


if __name__ == "__main__":
    main()
