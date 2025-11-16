"""
성능 개선 검증 스크립트
Created: 2025-11-12

목적:
    Few-Shot Examples 추가 후 UC2/UC3 성능 개선을 실제로 검증합니다.

테스트 케이스:
    1. UC2 - BBC (기존 selector 수정 필요)
    2. UC3 - CNN (영어 신규 사이트)
    3. UC3 - 조선일보 (한국 신규 사이트)
"""

import os
import sys

import requests
from dotenv import load_dotenv
from loguru import logger

# .env 로드
load_dotenv(override=True)

# 프로젝트 root 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.database import get_db
from src.storage.models import Selector
from src.workflow.uc2_hitl import HITLState, build_uc2_graph
from src.workflow.uc3_new_site import UC3State, build_uc3_graph


def test_uc2_bbc():
    """
    UC2 테스트: BBC 뉴스 (기존 selector 수정)

    예상: Few-Shot Examples로 성능 향상
    """
    print("\n" + "=" * 80)
    print("TEST 1: UC2 - BBC News (Self-Healing)")
    print("=" * 80)

    url = "https://www.bbc.com/news/articles/c0mzdy84dy7o"

    # HTML 다운로드
    print(f"\n[1/4] Downloading HTML from {url}...")
    response = requests.get(url, timeout=10)
    html_content = response.text
    print(f"  ✅ Downloaded {len(html_content)} bytes")

    # UC2 Graph 빌드
    print(f"\n[2/4] Building UC2 Graph...")
    uc2_graph = build_uc2_graph()
    print(f"  ✅ Graph compiled")

    # Initial State
    initial_state: HITLState = {
        "url": url,
        "site_name": "bbc",
        "html_content": html_content,
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "retry_count": 0,
        "final_selectors": None,
        "error_message": None,
        "next_action": None,
    }

    # 실행
    print(f"\n[3/4] Running UC2 workflow...")
    final_state = uc2_graph.invoke(initial_state)

    # 결과 분석
    print(f"\n[4/4] Results:")
    print(f"  - Consensus Reached: {final_state.get('consensus_reached')}")
    print(f"  - Retry Count: {final_state.get('retry_count')}")
    print(f"  - Next Action: {final_state.get('next_action')}")

    if final_state.get("error_message"):
        print(f"  ❌ Error: {final_state['error_message']}")
        return False

    if final_state.get("consensus_reached"):
        final_selectors = final_state.get("final_selectors", {})
        print(f"  ✅ Success!")
        print(f"     - Title: {final_selectors.get('title_selector')}")
        print(f"     - Body: {final_selectors.get('body_selector')}")
        print(f"     - Date: {final_selectors.get('date_selector')}")
        return True
    else:
        print(f"  ⚠️ Consensus NOT reached (threshold too strict or GPT/Gemini disagreed)")
        gpt = final_state.get("gpt_proposal", {})
        gemini = final_state.get("gemini_validation", {})
        print(f"     - GPT confidence: {gpt.get('confidence', 0)}")
        print(f"     - Gemini confidence: {gemini.get('confidence', 0)}")
        return False


def test_uc3_cnn():
    """
    UC3 테스트: CNN (영어 신규 사이트)

    예상: Few-Shot + raw_html로 성능 향상
    """
    print("\n" + "=" * 80)
    print("TEST 2: UC3 - CNN (New Site Discovery - English)")
    print("=" * 80)

    url = "https://www.cnn.com/2024/11/08/tech/openai-chatgpt-search/index.html"

    # DB에 CNN이 없는지 확인
    db = next(get_db())
    existing = db.query(Selector).filter(Selector.site_name == "cnn").first()
    if existing:
        print(f"  ⚠️ CNN selector already exists in DB. Deleting for clean test...")
        db.delete(existing)
        db.commit()

    # HTML 다운로드
    print(f"\n[1/4] Downloading HTML from {url}...")
    response = requests.get(url, timeout=10)
    html_content = response.text
    print(f"  ✅ Downloaded {len(html_content)} bytes")

    # UC3 Graph 빌드
    print(f"\n[2/4] Building UC3 Graph...")
    uc3_graph = build_uc3_graph()
    print(f"  ✅ Graph compiled")

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
        "error_message": None,
    }

    # 실행
    print(f"\n[3/4] Running UC3 workflow (this may take 30-60 seconds)...")
    final_state = uc3_graph.invoke(initial_state)

    # 결과 분석
    print(f"\n[4/4] Results:")
    print(f"  - Consensus Reached: {final_state.get('consensus_reached')}")
    print(f"  - Consensus Score: {final_state.get('consensus_score')}")

    if final_state.get("error_message"):
        print(f"  ❌ Error: {final_state['error_message']}")
        return False

    if final_state.get("consensus_reached"):
        final_selectors = final_state.get("final_selectors", {})
        print(f"  ✅ Success!")
        print(f"     - Title: {final_selectors.get('title_selector')}")
        print(f"     - Body: {final_selectors.get('body_selector')}")
        print(f"     - Date: {final_selectors.get('date_selector')}")
        return True
    else:
        print(f"  ⚠️ Consensus NOT reached")
        gpt = final_state.get("gpt_proposal", {})
        gemini = final_state.get("gemini_validation", {})
        print(f"     - GPT overall confidence: {gpt.get('overall_confidence', 0)}")
        print(f"     - Gemini overall confidence: {gemini.get('overall_confidence', 0)}")
        return False


def test_uc3_chosun():
    """
    UC3 테스트: 조선일보 (한국 신규 사이트)

    예상: Few-Shot + raw_html로 한국 사이트도 인식
    """
    print("\n" + "=" * 80)
    print("TEST 3: UC3 - 조선일보 (New Site Discovery - Korean)")
    print("=" * 80)

    url = "https://www.chosun.com/politics/politics_general/2024/11/08/OGRTUUMV5FGZTDUZKPPVCKWQWI/"

    # DB에 조선일보가 없는지 확인
    db = next(get_db())
    existing = db.query(Selector).filter(Selector.site_name == "chosun").first()
    if existing:
        print(f"  ⚠️ Chosun selector already exists in DB. Deleting for clean test...")
        db.delete(existing)
        db.commit()

    # HTML 다운로드
    print(f"\n[1/4] Downloading HTML from {url}...")
    response = requests.get(url, timeout=10)
    html_content = response.text
    print(f"  ✅ Downloaded {len(html_content)} bytes")

    # UC3 Graph 빌드
    print(f"\n[2/4] Building UC3 Graph...")
    uc3_graph = build_uc3_graph()
    print(f"  ✅ Graph compiled")

    # Initial State
    initial_state: UC3State = {
        "url": url,
        "site_name": "chosun",
        "raw_html": html_content,
        "tavily_results": None,
        "firecrawl_results": None,
        "beautifulsoup_analysis": None,
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "consensus_score": None,
        "final_selectors": None,
        "error_message": None,
    }

    # 실행
    print(f"\n[3/4] Running UC3 workflow (this may take 30-60 seconds)...")
    final_state = uc3_graph.invoke(initial_state)

    # 결과 분석
    print(f"\n[4/4] Results:")
    print(f"  - Consensus Reached: {final_state.get('consensus_reached')}")
    print(f"  - Consensus Score: {final_state.get('consensus_score')}")

    if final_state.get("error_message"):
        print(f"  ❌ Error: {final_state['error_message']}")
        return False

    if final_state.get("consensus_reached"):
        final_selectors = final_state.get("final_selectors", {})
        print(f"  ✅ Success!")
        print(f"     - Title: {final_selectors.get('title_selector')}")
        print(f"     - Body: {final_selectors.get('body_selector')}")
        print(f"     - Date: {final_selectors.get('date_selector')}")
        return True
    else:
        print(f"  ⚠️ Consensus NOT reached")
        gpt = final_state.get("gpt_proposal", {})
        gemini = final_state.get("gemini_validation", {})
        print(f"     - GPT overall confidence: {gpt.get('overall_confidence', 0)}")
        print(f"     - Gemini overall confidence: {gemini.get('overall_confidence', 0)}")
        return False


if __name__ == "__main__":
    print("\n" + "🚀" * 40)
    print("Few-Shot Examples 성능 개선 검증 시작")
    print("🚀" * 40)

    results = {}

    # Test 1: UC2 - BBC
    try:
        results["uc2_bbc"] = test_uc2_bbc()
    except Exception as e:
        print(f"\n❌ UC2 BBC Test FAILED with exception: {e}")
        results["uc2_bbc"] = False

    # Test 2: UC3 - CNN
    try:
        results["uc3_cnn"] = test_uc3_cnn()
    except Exception as e:
        print(f"\n❌ UC3 CNN Test FAILED with exception: {e}")
        results["uc3_cnn"] = False

    # Test 3: UC3 - 조선일보
    try:
        results["uc3_chosun"] = test_uc3_chosun()
    except Exception as e:
        print(f"\n❌ UC3 Chosun Test FAILED with exception: {e}")
        results["uc3_chosun"] = False

    # 최종 결과
    print("\n" + "=" * 80)
    print("📊 최종 검증 결과")
    print("=" * 80)
    print(f"UC2 - BBC (Self-Healing):          {'✅ PASS' if results['uc2_bbc'] else '❌ FAIL'}")
    print(f"UC3 - CNN (New Site - English):    {'✅ PASS' if results['uc3_cnn'] else '❌ FAIL'}")
    print(
        f"UC3 - 조선일보 (New Site - Korean):  {'✅ PASS' if results['uc3_chosun'] else '❌ FAIL'}"
    )
    print(f"\n성공률: {sum(results.values())}/3 = {sum(results.values())/3*100:.1f}%")
    print("=" * 80)
