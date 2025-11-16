#!/usr/bin/env python3
"""
JTBC JSON-LD 통합 테스트

이전 실패 (confidence 0.22) → 개선 (JSON-LD/Meta 태그 추출)

작성일: 2025-11-14
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.utils.site_detector import extract_site_id
from src.workflow.master_crawl_workflow import MasterCrawlState, build_master_graph

TEST_URL = "https://news.jtbc.co.kr/article/NB12270830"


def test_jtbc():
    """JTBC 테스트 (이전 0.22 → 개선)"""
    print(f"\n{'='*80}")
    print(f"JTBC JSON-LD Integration Test")
    print(f"URL: {TEST_URL}")
    print(f"{'='*80}\n")

    # Build master graph
    print("Building Master Graph...")
    master_app = build_master_graph()
    print("✅ Graph built\n")

    # Extract site_id
    extracted_site_id = extract_site_id(TEST_URL)
    print(f"Site ID: {extracted_site_id}\n")

    # Run workflow
    print("Running workflow...")
    initial_state: MasterCrawlState = {
        "url": TEST_URL,
        "site_name": extracted_site_id,
        "html_content": None,
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "quality_passed": None,
        "extracted_title": None,
        "extracted_body": None,
        "extracted_date": None,
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

    final_state = master_app.invoke(initial_state)

    # Analyze results
    print(f"\n{'='*80}")
    print("Result Analysis")
    print(f"{'='*80}\n")

    uc3_result = final_state.get("uc3_discovery_result", {})
    confidence = uc3_result.get("confidence", 0.0)
    source = uc3_result.get("source", "unknown")
    gpt_skipped = uc3_result.get("gpt_skipped", False)
    workflow_history = final_state.get("workflow_history", [])

    print(f"Confidence: {confidence:.2f}")
    print(f"Source: {source}")
    print(f"GPT/Gemini Skipped: {gpt_skipped}")
    print(f"\nWorkflow History:")
    for step in workflow_history:
        print(f"  - {step}")

    # Success check
    print(f"\n{'='*80}")
    print("Success Comparison")
    print(f"{'='*80}\n")
    print(f"이전 (CSS only): confidence=0.22 ❌")
    print(f"현재 (JSON-LD/Meta): confidence={confidence:.2f} {'✅' if confidence >= 0.7 else '❌'}")

    if source == "json-ld" or source == "meta-tags":
        print(f"\n✅ SUCCESS: {source} extraction worked!")
        return True
    else:
        print(f"\n❌ FAILED: Still using {source}")
        return False


if __name__ == "__main__":
    success = test_jtbc()
    sys.exit(0 if success else 1)
