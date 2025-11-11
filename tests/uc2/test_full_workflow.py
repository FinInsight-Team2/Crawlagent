"""
UC2 HITL - LangGraph StateGraph 전체 워크플로우 테스트
Created: 2025-11-05

목적: build_uc2_graph()로 생성된 compiled app을 실제로 실행
"""

import os
import pytest
from dotenv import load_dotenv
import requests
from src.workflow.uc2_hitl import HITLState, build_uc2_graph


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
def compiled_app():
    """LangGraph StateGraph 빌드 (모듈당 1회만)"""
    return build_uc2_graph()


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
def test_langgraph_workflow_execution(compiled_app, initial_state):
    """LangGraph 전체 워크플로우 실행 테스트"""
    load_dotenv()

    # LangGraph 실행
    final_state = compiled_app.invoke(initial_state)

    # 결과 검증
    assert final_state is not None, "Final state should not be None"

    # 에러가 발생한 경우
    if final_state.get("error_message"):
        pytest.fail(f"Workflow failed with error: {final_state['error_message']}")

    # 필수 필드 확인
    assert "consensus_reached" in final_state, "Should have consensus_reached"
    assert "retry_count" in final_state, "Should have retry_count"
    assert "next_action" in final_state, "Should have next_action"

    # Retry count는 3 이하여야 함
    assert final_state["retry_count"] <= 3, "Retry count should not exceed 3"


@pytest.mark.integration
@pytest.mark.slow
def test_workflow_consensus_reached(compiled_app, initial_state):
    """Consensus 도달 케이스 검증"""
    load_dotenv()

    final_state = compiled_app.invoke(initial_state)

    if final_state.get("error_message"):
        pytest.skip(f"Workflow failed, skipping: {final_state['error_message']}")

    # Consensus가 도달된 경우
    if final_state["consensus_reached"]:
        # GPT Proposal 존재 확인
        assert final_state.get("gpt_proposal") is not None, "Should have GPT proposal"
        gpt = final_state["gpt_proposal"]
        assert "title_selector" in gpt, "GPT should have title_selector"
        assert "body_selector" in gpt, "GPT should have body_selector"
        assert "date_selector" in gpt, "GPT should have date_selector"
        assert "confidence" in gpt, "GPT should have confidence"

        # Gemini Validation 존재 확인
        assert final_state.get("gemini_validation") is not None, "Should have Gemini validation"
        gemini = final_state["gemini_validation"]
        assert "is_valid" in gemini, "Gemini should have is_valid"
        assert gemini["is_valid"] is True, "Gemini should validate as valid"
        assert "confidence" in gemini, "Gemini should have confidence"

        # Final Selectors 존재 확인
        assert final_state.get("final_selectors") is not None, "Should have final_selectors"
        final_selectors = final_state["final_selectors"]
        assert "title_selector" in final_selectors, "Should have title_selector"
        assert "body_selector" in final_selectors, "Should have body_selector"
        assert "date_selector" in final_selectors, "Should have date_selector"

        # Next action은 "end"여야 함
        assert final_state["next_action"] == "end", "Should end when consensus reached"


@pytest.mark.integration
@pytest.mark.slow
def test_workflow_retry_logic(compiled_app, initial_state):
    """Retry 로직 검증"""
    load_dotenv()

    final_state = compiled_app.invoke(initial_state)

    if final_state.get("error_message"):
        pytest.skip("Workflow failed, skipping retry logic test")

    # Consensus가 실패한 경우
    if not final_state["consensus_reached"]:
        # Retry count 확인
        assert final_state["retry_count"] >= 0, "Retry count should be non-negative"

        # Next action 확인
        if final_state["retry_count"] < 3:
            # 3회 미만이면 retry 가능
            assert final_state["next_action"] in ["retry", "human_review", "end"], "Should have valid next_action"
        else:
            # 3회 이상이면 human_review
            assert final_state["next_action"] == "human_review", "Should request human review after 3 retries"


@pytest.mark.integration
@pytest.mark.slow
def test_workflow_state_transitions(compiled_app, initial_state):
    """State 전환 검증"""
    load_dotenv()

    final_state = compiled_app.invoke(initial_state)

    if final_state.get("error_message"):
        pytest.skip("Workflow failed, skipping state transition test")

    # 초기 State 필드가 유지되는지 확인
    assert final_state["url"] == initial_state["url"], "URL should be preserved"
    assert final_state["site_name"] == initial_state["site_name"], "Site name should be preserved"
    assert final_state["html_content"] == initial_state["html_content"], "HTML content should be preserved"

    # Workflow가 State를 업데이트했는지 확인
    # (GPT proposal 또는 error_message 중 하나는 있어야 함)
    assert (
        final_state.get("gpt_proposal") is not None or
        final_state.get("error_message") is not None
    ), "Workflow should update state (GPT proposal or error)"


@pytest.mark.integration
@pytest.mark.slow
def test_workflow_result_structure(compiled_app, initial_state):
    """워크플로우 결과 구조 검증"""
    load_dotenv()

    final_state = compiled_app.invoke(initial_state)

    # 모든 HITLState 필드가 있어야 함
    required_fields = [
        "url", "site_name", "html_content",
        "gpt_proposal", "gemini_validation",
        "consensus_reached", "retry_count",
        "final_selectors", "error_message", "next_action"
    ]

    for field in required_fields:
        assert field in final_state, f"Final state should contain '{field}' field"

    # Boolean 타입 확인
    assert isinstance(final_state["consensus_reached"], bool), "consensus_reached should be boolean"

    # Integer 타입 확인
    assert isinstance(final_state["retry_count"], int), "retry_count should be integer"

    # String 타입 확인 (있는 경우)
    if final_state["next_action"] is not None:
        assert isinstance(final_state["next_action"], str), "next_action should be string"


@pytest.mark.integration
@pytest.mark.slow
def test_workflow_handles_api_errors_gracefully(compiled_app, test_url):
    """API 에러 처리 테스트"""
    load_dotenv()

    # 빈 HTML로 State 생성 (에러 유발 가능)
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

    # Workflow 실행 (에러가 발생해도 크래시하지 않아야 함)
    final_state = compiled_app.invoke(invalid_state)

    # 결과 검증
    assert final_state is not None, "Should return final_state even on error"

    # 에러가 발생했다면 error_message가 있어야 함
    if final_state.get("error_message"):
        assert isinstance(final_state["error_message"], str), "Error message should be string"
        assert len(final_state["error_message"]) > 0, "Error message should not be empty"

        # 에러 발생 시에도 next_action이 설정되어야 함
        assert final_state.get("next_action") is not None, "Should have next_action on error"
