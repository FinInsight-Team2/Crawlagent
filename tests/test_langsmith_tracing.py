#!/usr/bin/env python3
"""
LangSmith 트레이싱 테스트

URL: https://n.news.naver.com/mnews/article/277/0005676733
예상 워크플로우: UC3 (신규 사이트 Discovery)
"""

import os
import sys
sys.path.insert(0, '.')

from dotenv import load_dotenv
load_dotenv()

# LangSmith 설정 확인
print("=" * 60)
print("🔍 LangSmith 설정 확인")
print("=" * 60)
print(f"LANGCHAIN_TRACING_V2: {os.getenv('LANGCHAIN_TRACING_V2')}")
print(f"LANGCHAIN_PROJECT: {os.getenv('LANGCHAIN_PROJECT')}")
print(f"LANGCHAIN_API_KEY: {'✅ 설정됨' if os.getenv('LANGCHAIN_API_KEY') else '❌ 없음'}")
print()

import requests
from src.workflow.master_crawl_workflow import build_master_graph

url = 'https://n.news.naver.com/mnews/article/277/0005676733'
print("=" * 60)
print("🚀 Master Graph 실행 (LangSmith 트레이싱)")
print("=" * 60)
print(f"URL: {url}")
print()

# HTML 다운로드
print("📡 HTML 다운로드 중...")
response = requests.get(url, timeout=10)
html = response.text
print(f"✅ HTML: {len(html)} bytes")
print()

# Master Graph 실행
print("🎯 Master Graph 워크플로우 시작...")
print("   (LangSmith에서 실시간 추적 가능)")
print()

master_app = build_master_graph()

initial_state = {
    "url": url,
    "site_name": "naver",
    "html_content": html,
    "raw_html": html,
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

try:
    final_state = master_app.invoke(initial_state)

    print("=" * 60)
    print("✅ 워크플로우 완료!")
    print("=" * 60)

    # Workflow history
    history = final_state.get("workflow_history", [])
    print("\n📋 Workflow History:")
    for step in history:
        print(f"   {step}")

    # UC 결과
    uc1_result = final_state.get("uc1_validation_result")
    uc2_result = final_state.get("uc2_consensus_result")
    uc3_result = final_state.get("uc3_discovery_result")

    if uc1_result:
        print(f"\n🔍 UC1 품질 검증:")
        print(f"   - Quality Score: {uc1_result.get('quality_score', 0)}/100")
        print(f"   - Passed: {uc1_result.get('quality_passed', False)}")
        print(f"   - Next Action: {uc1_result.get('next_action', 'N/A')}")

    if uc2_result:
        print(f"\n🔧 UC2 자동 복구:")
        print(f"   - Consensus Reached: {uc2_result.get('consensus_reached', False)}")
        print(f"   - Consensus Score: {uc2_result.get('consensus_score', 0):.2f}")

    if uc3_result:
        print("\n🆕 UC3 Discovery 결과:")
        print(f"   - Consensus Reached: {uc3_result.get('consensus_reached', False)}")
        print(f"   - Consensus Score: {uc3_result.get('consensus_score', 0):.2f}")
        print(f"   - Threshold: 0.7")

        proposed = uc3_result.get("proposed_selectors", {})
        if proposed:
            print(f"\n   제안된 Selectors:")
            print(f"   - Title: {proposed.get('title_selector', 'N/A')}")
            print(f"   - Body: {proposed.get('body_selector', 'N/A')[:60]}...")
            print(f"   - Date: {proposed.get('date_selector', 'N/A')}")

    # Final result
    final_result = final_state.get("final_result")
    if final_result:
        print("\n📰 추출된 데이터:")
        title = final_result.get('title', 'N/A')
        body = final_result.get('body', '')
        print(f"   - 제목: {title[:60]}...")
        print(f"   - 본문: {len(body)} 글자")
        print(f"   - 날짜: {final_result.get('date', 'N/A')}")

    print("\n" + "=" * 60)
    print("🔍 LangSmith 트레이싱 확인:")
    print("=" * 60)
    print("URL: https://smith.langchain.com/")
    print(f"Project: {os.getenv('LANGCHAIN_PROJECT', 'crawlagent-poc')}")
    print("\n💡 LangSmith에서 확인 가능한 정보:")
    print("   - Supervisor 라우팅 결정")
    if uc3_result:
        print("   - UC3 3-Tool 실행 (Tavily, Firecrawl, BeautifulSoup)")
        print("   - GPT-4o Proposer 추론")
        print("   - Gemini 2.5 Flash Validator 검증")
        print("   - Consensus 계산 과정")
    if uc2_result:
        print("   - UC2 GPT-4o + Gemini 2.5 Consensus")
    print("=" * 60)

except Exception as e:
    print(f"\n❌ 에러 발생: {e}")
    import traceback
    traceback.print_exc()
