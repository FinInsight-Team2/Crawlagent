"""
UC2 HITL - GPT + Gemini 통합 테스트
Created: 2025-11-05

목적: 2개 노드가 함께 작동하는지 확인 (StateGraph 없이)
"""

import os
import pytest
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, gpt_propose_node, gemini_validate_node


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


@pytest.fixture(scope="module")
def initial_state(test_url, test_html_content):
    """초기 State 생성"""
    return {
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


@pytest.mark.integration
@pytest.mark.slow
def test_gpt_gemini_integration_success(initial_state):
    """GPT + Gemini 통합 테스트 - 정상 플로우"""
    load_dotenv(override=True)

    # GPT Propose Node 실행
    state_after_gpt = gpt_propose_node(initial_state)

    # GPT 에러 체크
    if state_after_gpt.get("error_message"):
        pytest.fail(f"GPT node failed with error: {state_after_gpt['error_message']}")

    # GPT Proposal 검증
    assert state_after_gpt.get("gpt_proposal") is not None, "GPT proposal should be generated"
    gpt_proposal = state_after_gpt["gpt_proposal"]
    assert "title_selector" in gpt_proposal, "Should have title_selector"
    assert "body_selector" in gpt_proposal, "Should have body_selector"
    assert "date_selector" in gpt_proposal, "Should have date_selector"
    assert "confidence" in gpt_proposal, "Should have confidence"

    # Gemini Validate Node 실행
    final_state = gemini_validate_node(state_after_gpt)

    # Gemini 에러 체크
    if final_state.get("error_message"):
        pytest.fail(f"Gemini node failed with error: {final_state['error_message']}")

    # Gemini Validation 검증
    assert final_state.get("gemini_validation") is not None, "Gemini validation should exist"
    gemini_validation = final_state["gemini_validation"]
    assert "is_valid" in gemini_validation, "Should have is_valid"
    assert "confidence" in gemini_validation, "Should have confidence"
    assert "feedback" in gemini_validation, "Should have feedback"

    # 최종 상태 검증
    assert "consensus_reached" in final_state, "Should have consensus_reached field"
    assert "next_action" in final_state, "Should have next_action field"
    assert "retry_count" in final_state, "Should have retry_count field"

    # Consensus가 true면 final_selectors가 있어야 함
    if final_state["consensus_reached"]:
        assert final_state["final_selectors"] is not None, "Should have final_selectors when consensus reached"
        assert "title_selector" in final_state["final_selectors"]
        assert "body_selector" in final_state["final_selectors"]
        assert "date_selector" in final_state["final_selectors"]


@pytest.mark.integration
@pytest.mark.slow
def test_gpt_gemini_state_continuity(initial_state):
    """GPT → Gemini State 연속성 테스트"""
    load_dotenv(override=True)

    # GPT 실행
    state_after_gpt = gpt_propose_node(initial_state)

    if state_after_gpt.get("error_message"):
        pytest.skip(f"GPT node failed, skipping: {state_after_gpt['error_message']}")

    # State 필드 유지 확인
    assert state_after_gpt["url"] == initial_state["url"], "URL should be preserved"
    assert state_after_gpt["site_name"] == initial_state["site_name"], "Site name should be preserved"
    assert state_after_gpt["html_content"] == initial_state["html_content"], "HTML content should be preserved"

    # Gemini 실행
    final_state = gemini_validate_node(state_after_gpt)

    if final_state.get("error_message"):
        pytest.skip(f"Gemini node failed, skipping: {final_state['error_message']}")

    # GPT Proposal이 Gemini까지 전달되었는지 확인
    assert final_state["gpt_proposal"] == state_after_gpt["gpt_proposal"], "GPT proposal should be preserved"
    assert final_state["url"] == initial_state["url"], "URL should be preserved"
    assert final_state["site_name"] == initial_state["site_name"], "Site name should be preserved"


@pytest.mark.integration
@pytest.mark.slow
def test_consensus_logic(initial_state):
    """Consensus 도달 로직 테스트"""
    load_dotenv(override=True)

    # GPT 실행
    state_after_gpt = gpt_propose_node(initial_state)
    if state_after_gpt.get("error_message"):
        pytest.skip("GPT node failed, cannot test consensus")

    # Gemini 실행
    final_state = gemini_validate_node(state_after_gpt)
    if final_state.get("error_message"):
        pytest.skip("Gemini node failed, cannot test consensus")

    # Consensus 관련 필드 검증
    assert isinstance(final_state["consensus_reached"], bool), "consensus_reached should be boolean"
    assert final_state["next_action"] in ["retry", "end", "human_review", None], "next_action should be valid"
    assert isinstance(final_state["retry_count"], int), "retry_count should be integer"
    assert final_state["retry_count"] >= 0, "retry_count should be non-negative"

    # Consensus true인 경우
    if final_state["consensus_reached"]:
        assert final_state["final_selectors"] is not None, "Should have final_selectors"
        assert final_state["next_action"] == "end", "Should end when consensus reached"

    # Consensus false인 경우
    else:
        assert final_state["next_action"] in ["retry", "human_review"], "Should retry or request human review"
        if final_state["next_action"] == "retry":
            assert final_state["retry_count"] < 3, "Should retry only if count < 3"
        elif final_state["next_action"] == "human_review":
            assert final_state["retry_count"] >= 3, "Should request human review after 3 retries"


@pytest.mark.integration
@pytest.mark.slow
def test_error_handling(test_url):
    """에러 처리 테스트"""
    load_dotenv(override=True)

    # 잘못된 HTML로 State 생성
    invalid_state: HITLState = {
        "url": test_url,
        "site_name": "bbc",
        "html_content": "",  # 빈 HTML
        "gpt_proposal": None,
        "gemini_validation": None,
        "consensus_reached": False,
        "retry_count": 0,
        "final_selectors": None,
        "error_message": None,
        "next_action": None
    }

    # GPT 실행 (에러 발생 가능)
    state_after_gpt = gpt_propose_node(invalid_state)

    # 에러가 발생하면 error_message가 있어야 함
    if state_after_gpt.get("error_message"):
        assert isinstance(state_after_gpt["error_message"], str), "Error message should be string"
        assert len(state_after_gpt["error_message"]) > 0, "Error message should not be empty"
        # 에러 발생 시 next_action이 설정되어야 함
        assert state_after_gpt.get("next_action") is not None, "Should have next_action on error"
