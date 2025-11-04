"""
UC2 HITL - GPT + Gemini 통합 테스트
Created: 2025-11-05

목적: 2개 노드가 함께 작동하는지 확인 (StateGraph 없이)
"""

import os
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, gpt_propose_node, gemini_validate_node

# .env 파일 로드
load_dotenv()

# 테스트 URL (BBC 뉴스)
test_url = "https://www.bbc.com/news/articles/c0mzdy84dy7o"

print("=" * 80)
print("[UC2 Multi-Agent Test] GPT Proposer + Gemini Validator")
print("=" * 80)

# 1. HTML Fetch
print(f"\n[Step 1/3] Fetching HTML from {test_url}")
response = requests.get(test_url, timeout=10)
html_content = response.text
print(f"✅ HTML fetched: {len(html_content)} characters")

# 2. State 초기화
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

# 3. GPT Propose Node 실행
print("\n[Step 2/3] 🤖 GPT Proposing CSS Selectors...")
state_after_gpt = gpt_propose_node(initial_state)

if state_after_gpt.get("error_message"):
    print(f"❌ GPT Error: {state_after_gpt['error_message']}")
    exit(1)

gpt_proposal = state_after_gpt["gpt_proposal"]
print(f"✅ GPT Proposal Generated:")
print(f"   Title:  {gpt_proposal['title_selector']}")
print(f"   Body:   {gpt_proposal['body_selector']}")
print(f"   Date:   {gpt_proposal['date_selector']}")
print(f"   Confidence: {gpt_proposal['confidence']}")

# 4. Gemini Validate Node 실행
print("\n[Step 3/3] 🔍 Gemini Validating Selectors...")
final_state = gemini_validate_node(state_after_gpt)

if final_state.get("error_message"):
    print(f"❌ Gemini Error: {final_state['error_message']}")
    exit(1)

gemini_validation = final_state["gemini_validation"]
print(f"✅ Gemini Validation Complete:")
print(f"   Valid: {gemini_validation['is_valid']}")
print(f"   Confidence: {gemini_validation['confidence']}")
print(f"   Feedback: {gemini_validation['feedback']}")

# 5. 최종 결과
print("\n" + "=" * 80)
print("[Final Result]")
print("=" * 80)
print(f"Consensus Reached: {final_state['consensus_reached']}")
print(f"Next Action: {final_state['next_action']}")
print(f"Retry Count: {final_state['retry_count']}")

if final_state['consensus_reached']:
    print("\n✅ SUCCESS: Multi-Agent Consensus Reached!")
    print(f"\nFinal Selectors:")
    for key, value in final_state['final_selectors'].items():
        print(f"  {key}: {value}")
else:
    print(f"\n⚠️ RETRY NEEDED: {gemini_validation['feedback']}")
    if final_state['next_action'] == 'retry':
        print("   → Will retry with GPT again")
    elif final_state['next_action'] == 'human_review':
        print("   → Max retries reached, needs human review")

print("=" * 80)
