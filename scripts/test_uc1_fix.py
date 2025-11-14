#!/usr/bin/env python3
"""
Quick test to verify UC1 bug fix (inconsistent state error)

Tests 1 URL: 동아일보 (donga)
Expected: UC1 fails → routes to UC3 (not "inconsistent state" error)

작성일: 2025-11-14
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState
from src.utils.site_detector import extract_site_id

TEST_URL = "https://www.donga.com/news/Economy/article/all/20251113/132765807/1"


def test_uc1_fix():
    """Test UC1 bug fix"""
    print(f"\n{'='*80}")
    print(f"UC1 Bug Fix Test: 동아일보")
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

    next_action = final_state.get("next_action")
    error_message = final_state.get("error_message")
    workflow_history = final_state.get("workflow_history", [])

    print(f"Next Action: {next_action}")
    print(f"Error Message: {error_message}")
    print(f"Workflow History:")
    for step in workflow_history:
        print(f"  - {step}")

    # Check for bug
    if error_message and "inconsistent state" in error_message:
        print(f"\n❌ BUG STILL EXISTS: 'inconsistent state' error detected")
        return False
    elif next_action == "end" or final_state.get("current_uc"):
        print(f"\n✅ BUG FIXED: Workflow completed without 'inconsistent state' error")
        return True
    else:
        print(f"\n⚠️ UNKNOWN STATE: next_action={next_action}")
        return False


if __name__ == "__main__":
    success = test_uc1_fix()
    sys.exit(0 if success else 1)
