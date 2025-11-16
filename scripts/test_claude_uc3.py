#!/usr/bin/env python3
"""
Claude Sonnet 4.5 + GPT-4o 2-Agent UC3 테스트
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env file
from dotenv import load_dotenv

load_dotenv(project_root / ".env")

from loguru import logger

from src.workflow.uc3_new_site import UC3State, create_uc3_agent


def test_donga():
    """동아일보 테스트 - JSON-LD가 있어서 빠름"""
    print("\n" + "=" * 80)
    print("🧪 UC3 Test: GPT-4o + Claude Sonnet 4.5 2-Agent Consensus")
    print("=" * 80)
    print("\nTest URL: 동아일보")
    print("Expected: High confidence (JSON-LD available)")
    print("=" * 80 + "\n")

    url = "https://www.donga.com/news/Economy/article/all/20251113/132765807/1"

    # UC3 Graph 빌드
    uc3_graph = create_uc3_agent()

    initial_state: UC3State = {
        "url": url,
        "site_name": "donga",
        "sample_urls": [],
        "raw_html": None,
        "preprocessed_html": None,
        "gpt_proposal": None,
        "gpt_confidence": None,
        "gemini_validation": None,  # Now holds Claude output
        "gemini_confidence": None,  # Now holds Claude confidence
        "final_selectors": None,
        "final_confidence": None,
        "error_message": None,
        "workflow_history": [],
        "json_ld_metadata": {},
        "json_ld_quality": 0.0,
        "skip_gpt_gemini": False,
    }

    try:
        final_state = uc3_graph.invoke(initial_state)

        print("\n" + "=" * 80)
        print("📊 Test Results")
        print("=" * 80)

        print(f"\n✅ Final Confidence: {final_state.get('final_confidence', 0.0):.2f}")
        print(f"✅ JSON-LD Quality: {final_state.get('json_ld_quality', 0.0):.2f}")
        print(f"✅ Skip GPT/Claude: {final_state.get('skip_gpt_gemini', False)}")

        final_selectors = final_state.get("final_selectors", {})
        if final_selectors:
            print(f"\n📋 Final Selectors:")
            print(f"  Title: {final_selectors.get('title', 'N/A')}")
            print(f"  Body: {final_selectors.get('body', 'N/A')}")
            print(f"  Date: {final_selectors.get('date', 'N/A')}")

        error = final_state.get("error_message")
        if error:
            print(f"\n❌ Error: {error}")
        else:
            print(f"\n🎉 Test PASSED!")

        return final_state

    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback

        traceback.print_exc()
        return None


if __name__ == "__main__":
    result = test_donga()
