"""
UC2 HITL - GPT Propose Node 간단 테스트
Created: 2025-11-05

목적: gpt_propose_node()가 정상 작동하는지 확인
"""

import os
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, gpt_propose_node

# .env 파일 로드
load_dotenv()

# 테스트 URL (BBC 뉴스)
test_url = "https://www.bbc.com/news/articles/c0mzdy84dy7o"

print("=" * 80)
print("[UC2 GPT Node Test] Starting...")
print("=" * 80)

# 1. HTML Fetch
print(f"\n[Step 1] Fetching HTML from {test_url}")
response = requests.get(test_url, timeout=10)
html_content = response.text
print(f"[Step 1] HTML fetched: {len(html_content)} characters")

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

print("\n[Step 2] Calling gpt_propose_node()...")
updated_state = gpt_propose_node(initial_state)

# 3. 결과 출력
print("\n" + "=" * 80)
print("[Result] GPT Proposal:")
print("=" * 80)
if updated_state.get("gpt_proposal"):
    proposal = updated_state["gpt_proposal"]
    print(f"Title Selector:  {proposal.get('title_selector')}")
    print(f"Body Selector:   {proposal.get('body_selector')}")
    print(f"Date Selector:   {proposal.get('date_selector')}")
    print(f"Confidence:      {proposal.get('confidence')}")
    print(f"Reasoning:       {proposal.get('reasoning')}")
    print(f"\nNext Action:     {updated_state.get('next_action')}")
    print("\n✅ Test PASSED")
else:
    print(f"❌ Error: {updated_state.get('error_message')}")
    print(f"Next Action: {updated_state.get('next_action')}")

print("=" * 80)
