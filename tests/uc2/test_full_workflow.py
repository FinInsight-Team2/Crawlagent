"""
UC2 HITL - LangGraph StateGraph 전체 워크플로우 테스트
Created: 2025-11-05

목적: build_uc2_graph()로 생성된 compiled app을 실제로 실행
"""

import os
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, build_uc2_graph

# .env 파일 로드
load_dotenv()

# 테스트 URL (BBC 뉴스)
test_url = "https://www.bbc.com/news/articles/c0mzdy84dy7o"

print("=" * 80)
print("[UC2 Full Workflow Test] LangGraph StateGraph Execution")
print("=" * 80)

# 1. HTML Fetch
print(f"\n[Step 1/4] Fetching HTML from {test_url}")
response = requests.get(test_url, timeout=10)
html_content = response.text
print(f"✅ HTML fetched: {len(html_content)} characters")

# 2. StateGraph 빌드
print("\n[Step 2/4] Building LangGraph StateGraph...")
app = build_uc2_graph()
print("✅ StateGraph compiled successfully")

# 3. Initial State 준비
initial_state: HITLState = {
    "url": test_url,
    "site_name": "bbc",
    "html_content": html_content,
    "gpt_proposal": None,
    "gemini_validation": None,
    "consensus_reached": False,
    "retry_count": 0,
    "final_selectors": None,
    "error_message": None,
    "next_action": None
}

# 4. LangGraph 실행 (invoke)
print("\n[Step 3/4] 🚀 Running LangGraph Workflow...")
print("   → GPT Propose")
print("   → Gemini Validate")
print("   → Conditional Routing (retry/end/human_review)")

final_state = app.invoke(initial_state)

# 5. 결과 출력
print("\n[Step 4/4] 📊 Final Results")
print("=" * 80)

if final_state.get("error_message"):
    print(f"❌ Error: {final_state['error_message']}")
    exit(1)

print(f"Consensus Reached: {final_state['consensus_reached']}")
print(f"Retry Count: {final_state['retry_count']}")
print(f"Next Action: {final_state['next_action']}")

if final_state['consensus_reached']:
    print("\n✅ SUCCESS: Multi-Agent Consensus Reached!")

    print("\n📋 GPT Proposal:")
    gpt = final_state.get("gpt_proposal", {})
    print(f"   Title:  {gpt.get('title_selector')}")
    print(f"   Body:   {gpt.get('body_selector')}")
    print(f"   Date:   {gpt.get('date_selector')}")
    print(f"   GPT Confidence: {gpt.get('confidence')}")
    print(f"   Reasoning: {gpt.get('reasoning', 'N/A')[:100]}...")

    print("\n🔍 Gemini Validation:")
    gemini = final_state.get("gemini_validation", {})
    print(f"   Valid: {gemini.get('is_valid')}")
    print(f"   Gemini Confidence: {gemini.get('confidence')}")
    print(f"   Feedback: {gemini.get('feedback', 'N/A')[:100]}...")

    print("\n✨ Final Selectors (Agreed):")
    for key, value in final_state['final_selectors'].items():
        print(f"   {key}: {value}")
else:
    print("\n⚠️ CONSENSUS FAILED")

    gemini = final_state.get("gemini_validation", {})
    print(f"   Gemini Feedback: {gemini.get('feedback', 'N/A')}")

    if final_state['next_action'] == 'retry':
        print(f"   → Retry count: {final_state['retry_count']}/3")
        print("   → Will retry with GPT again (in real workflow)")
    elif final_state['next_action'] == 'human_review':
        print("   → Max retries (3) reached")
        print("   → Human Review Node triggered")

print("\n" + "=" * 80)
print("[LangGraph Workflow Complete]")
print("=" * 80)
