"""
UC2 HITL - GPT Propose Node 간단 테스트
Created: 2025-11-05

목적: gpt_propose_node()가 정상 작동하는지 확인
"""

import os
import pytest
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, gpt_propose_node


@pytest.fixture(scope="module")
def test_html_content():
    """BBC 뉴스 HTML 가져오기 (모듈당 1회만)"""
    test_url = "https://www.bbc.com/news/articles/c0mzdy84dy7o"
    response = requests.get(test_url, timeout=10)
    return response.text


@pytest.fixture(scope="module")
def test_url():
    """테스트 URL"""
    return "https://www.bbc.com/news/articles/c0mzdy84dy7o"


@pytest.mark.integration
@pytest.mark.slow
def test_gpt_propose_node_success(test_url, test_html_content):
    """GPT Propose Node 정상 작동 테스트"""
    # .env 파일 로드 (override=True로 기존 환경변수 덮어쓰기)
    load_dotenv(override=True)

    # State 초기화
    initial_state: HITLState = {
        "url": test_url,
        "site_name": "bbc",
        "html_content": test_html_content,
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "retry_count": 0,
        "final_selectors": None,
        "error_message": None,
        "next_action": None
    }

    # GPT Propose Node 실행
    updated_state = gpt_propose_node(initial_state)

    # 결과 검증
    assert updated_state is not None, "Updated state should not be None"

    # Error가 발생한 경우
    if updated_state.get("error_message"):
        pytest.fail(f"GPT node failed with error: {updated_state['error_message']}")

    # 정상 케이스 검증
    assert updated_state.get("gpt_proposal") is not None, "GPT proposal should be generated"

    proposal = updated_state["gpt_proposal"]
    assert "title_selector" in proposal, "Proposal should contain title_selector"
    assert "body_selector" in proposal, "Proposal should contain body_selector"
    assert "date_selector" in proposal, "Proposal should contain date_selector"
    assert "confidence" in proposal, "Proposal should contain confidence"
    assert "reasoning" in proposal, "Proposal should contain reasoning"

    # Confidence는 0-100 범위
    assert 0 <= proposal["confidence"] <= 100, "Confidence should be between 0 and 100"

    # Selectors는 비어있지 않아야 함
    assert proposal["title_selector"], "Title selector should not be empty"
    assert proposal["body_selector"], "Body selector should not be empty"

    # Next action 확인
    assert updated_state.get("next_action") is not None, "Next action should be set"


@pytest.mark.integration
@pytest.mark.slow
def test_gpt_propose_node_structure(test_url, test_html_content):
    """GPT Propose Node 결과 구조 검증"""
    load_dotenv(override=True)

    initial_state: HITLState = {
        "url": test_url,
        "site_name": "bbc",
        "html_content": test_html_content,
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "retry_count": 0,
        "final_selectors": None,
        "error_message": None,
        "next_action": None
    }

    updated_state = gpt_propose_node(initial_state)

    # State 필드 존재 확인
    required_fields = [
        "url", "site_name", "html_content", "gpt_proposal",
        "gemini_validation", "consensus_reached", "retry_count",
        "final_selectors", "error_message", "next_action"
    ]

    for field in required_fields:
        assert field in updated_state, f"State should contain '{field}' field"

    # GPT proposal 구조 검증 (에러가 없는 경우만)
    if not updated_state.get("error_message"):
        proposal = updated_state["gpt_proposal"]
        assert isinstance(proposal, dict), "Proposal should be a dictionary"
        assert isinstance(proposal["confidence"], (int, float)), "Confidence should be numeric"
        assert isinstance(proposal["reasoning"], str), "Reasoning should be string"
