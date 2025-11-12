"""
빠른 데모 테스트 스크립트
Created: 2025-11-12

목적: 데모 시나리오 검증 (UC3 - CNN)
"""

import os
import sys
import requests
from loguru import logger
from dotenv import load_dotenv

# .env 파일 먼저 로드 (import 전에!)
load_dotenv(override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.workflow.uc3_new_site import create_uc3_agent, UC3State
from src.storage.database import get_db
from src.storage.models import Selector


def test_cnn_discovery():
    """
    UC3 - CNN 신규 사이트 자동 발견 테스트
    """
    print("\n" + "="*80)
    print("🧪 Quick Demo Test: CNN Discovery (UC3)")
    print("="*80)

    url = "https://www.cnn.com/2024/11/08/tech/openai-chatgpt-search/index.html"

    # DB에서 CNN 제거 (클린 테스트)
    db = next(get_db())
    existing = db.query(Selector).filter(Selector.site_name == "cnn").first()
    if existing:
        print(f"\n⚠️  CNN selector exists in DB, removing for clean test...")
        db.delete(existing)
        db.commit()

    # HTML 다운로드
    print(f"\n[1/4] Downloading HTML from CNN...")
    try:
        response = requests.get(url, timeout=15, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        html_content = response.text
        print(f"  ✅ Downloaded {len(html_content):,} bytes")
    except Exception as e:
        print(f"  ❌ Error downloading: {e}")
        return False

    # UC3 Agent 빌드
    print(f"\n[2/4] Building UC3 Agent...")
    try:
        uc3_agent = create_uc3_agent()
        print(f"  ✅ Agent compiled")
    except Exception as e:
        print(f"  ❌ Error building agent: {e}")
        return False

    # Initial State
    initial_state: UC3State = {
        "url": url,
        "site_name": "cnn",
        "raw_html": html_content,
        "tavily_results": None,
        "firecrawl_results": None,
        "beautifulsoup_analysis": None,
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "consensus_score": None,
        "final_selectors": None,
        "error_message": None
    }

    # 실행
    print(f"\n[3/4] Running UC3 workflow...")
    print(f"  (이 과정은 30-60초 소요됩니다 - GPT + Gemini 분석)")
    try:
        final_state = uc3_agent.invoke(initial_state)
    except Exception as e:
        print(f"  ❌ Error running workflow: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 결과 분석
    print(f"\n[4/4] Results:")
    print(f"  - Consensus Reached: {final_state.get('consensus_reached')}")
    print(f"  - Consensus Score: {final_state.get('consensus_score')}")

    if final_state.get("error_message"):
        print(f"  ❌ Error: {final_state['error_message']}")
        return False

    if final_state.get("consensus_reached"):
        final_selectors = final_state.get("final_selectors", {})
        print(f"\n  ✅ Success! Selectors discovered:")
        print(f"     Title: {final_selectors.get('title_selector') or final_selectors.get('title')}")
        print(f"     Body:  {final_selectors.get('body_selector') or final_selectors.get('body')}")
        print(f"     Date:  {final_selectors.get('date_selector') or final_selectors.get('date')}")

        # DB 확인
        db = next(get_db())
        cnn_selector = db.query(Selector).filter(Selector.site_name == "cnn").first()
        if cnn_selector:
            print(f"\n  ✅ CNN selector saved to DB!")
        else:
            print(f"\n  ⚠️  CNN selector NOT saved to DB (consensus may be < 0.55)")

        return True
    else:
        print(f"\n  ⚠️  Consensus NOT reached (score: {final_state.get('consensus_score')})")
        gpt = final_state.get("gpt_proposal", {})
        gemini = final_state.get("gemini_validation", {})
        print(f"     GPT confidence: {gpt.get('overall_confidence', 'N/A')}")
        print(f"     Gemini confidence: {gemini.get('overall_confidence', 'N/A')}")
        return False


if __name__ == "__main__":
    try:
        success = test_cnn_discovery()
        if success:
            print("\n" + "="*80)
            print("🎉 Demo test PASSED! Ready for live demo")
            print("="*80)
        else:
            print("\n" + "="*80)
            print("❌ Demo test FAILED - check logs above")
            print("="*80)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
