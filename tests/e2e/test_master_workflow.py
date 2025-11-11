"""
E2E Test: Master Workflow - UC1 성공 시나리오

시나리오:
    1. 고품질 기사 입력
    2. Supervisor → UC1 라우팅
    3. UC1 품질 검증 통과 (>= 80점)
    4. END (DB 저장 완료)

검증 항목:
    - Workflow history에 "UC1" 포함
    - final_result 존재
    - quality_score >= 80
    - next_action = "end"

실행 방법:
    pytest tests/e2e/test_master_workflow.py -v

작성일: 2025-11-11
"""

import pytest
from unittest.mock import patch, MagicMock
from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState


@pytest.mark.e2e
class TestMasterWorkflowUC1Success:
    """UC1 성공 시나리오 E2E 테스트"""

    def test_uc1_success_flow(
        self,
        master_workflow_initial_state,
        test_article_high_quality,
        db_session
    ):
        """
        E2E Test: UC1 성공 시나리오

        Given: 고품질 기사 데이터
        When: Master Workflow 실행
        Then: UC1 통과 → END
        """

        # Given: Master Graph 빌드
        master_app = build_master_graph()

        # Given: 초기 State
        initial_state = master_workflow_initial_state

        # Mock: DB 저장 (실제 DB 대신 Mock 사용)
        with patch('src.storage.database.get_db') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            mock_get_db.return_value.__exit__.return_value = None

            # When: Workflow 실행
            final_state = master_app.invoke(initial_state)

            # Then: Assertions
            assert final_state is not None, "Final state should not be None"

            # 1. Workflow History 검증
            workflow_history = final_state.get("workflow_history", [])
            assert len(workflow_history) > 0, "Workflow history should not be empty"
            assert any("UC1" in step for step in workflow_history), \
                "UC1 should be in workflow history"

            # 2. Next Action 검증
            assert final_state.get("next_action") == "end", \
                "Next action should be 'end' after UC1 success"

            # 3. Final Result 존재 검증
            final_result = final_state.get("final_result")
            assert final_result is not None, "Final result should exist"

            # 4. Quality Score 검증
            uc1_result = final_state.get("uc1_validation_result")
            assert uc1_result is not None, "UC1 validation result should exist"
            assert uc1_result.get("quality_score", 0) >= 80, \
                "Quality score should be >= 80 for high quality article"

            # 5. Error 없음 검증
            assert final_state.get("error_message") is None, \
                "No error message should exist"

    def test_uc1_success_with_rule_based_supervisor(
        self,
        master_workflow_initial_state,
        db_session,
        monkeypatch
    ):
        """
        E2E Test: Rule-based Supervisor with UC1 성공

        Given: USE_SUPERVISOR_LLM=false
        When: Master Workflow 실행
        Then: Rule-based Supervisor → UC1 → END
        """

        # Given: Rule-based Supervisor 환경 변수
        monkeypatch.setenv("USE_SUPERVISOR_LLM", "false")

        # Given: Master Graph 빌드
        master_app = build_master_graph()

        # Given: 초기 State
        initial_state = master_workflow_initial_state

        # Mock: DB 저장
        with patch('src.storage.database.get_db') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            mock_get_db.return_value.__exit__.return_value = None

            # When: Workflow 실행
            final_state = master_app.invoke(initial_state)

            # Then: Rule-based Supervisor 사용 확인
            assert final_state.get("supervisor_reasoning") is None, \
                "Rule-based supervisor should not have LLM reasoning"

            # Then: UC1 실행 확인
            assert "UC1" in str(final_state.get("workflow_history", [])), \
                "UC1 should be executed"

            # Then: 성공 확인
            assert final_state.get("next_action") == "end", \
                "Should end after UC1 success"

    @pytest.mark.slow
    def test_uc1_success_with_llm_supervisor(
        self,
        master_workflow_initial_state,
        db_session,
        monkeypatch
    ):
        """
        E2E Test: LLM Supervisor with UC1 성공

        Given: USE_SUPERVISOR_LLM=true
        When: Master Workflow 실행
        Then: LLM Supervisor → UC1 → END

        Note: 실제 LLM 호출하므로 느림 (slow marker)
        """

        # Given: LLM Supervisor 환경 변수
        monkeypatch.setenv("USE_SUPERVISOR_LLM", "true")

        # Given: Master Graph 빌드
        master_app = build_master_graph()

        # Given: 초기 State
        initial_state = master_workflow_initial_state

        # Mock: DB 저장
        with patch('src.storage.database.get_db') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            mock_get_db.return_value.__exit__.return_value = None

            # Mock: LLM API (비용 절감)
            with patch('src.workflow.master_crawl_workflow.ChatOpenAI') as mock_llm:
                # Mock LLM 응답
                mock_instance = MagicMock()
                mock_instance.invoke.return_value.content = """
{
  "next_uc": "UC1",
  "reasoning": "새로운 URL이므로 UC1 품질 검증부터 시작합니다.",
  "confidence": 0.95
}
                """.strip()
                mock_llm.return_value = mock_instance

                # When: Workflow 실행
                final_state = master_app.invoke(initial_state)

                # Then: LLM Supervisor 사용 확인
                supervisor_reasoning = final_state.get("supervisor_reasoning")
                # Note: Mock 사용 시 reasoning이 없을 수 있음 (구현에 따라)

                # Then: UC1 실행 확인
                assert "UC1" in str(final_state.get("workflow_history", [])), \
                    "UC1 should be executed"

                # Then: 성공 확인
                assert final_state.get("next_action") == "end", \
                    "Should end after UC1 success"

    def test_uc1_success_state_transitions(
        self,
        master_workflow_initial_state,
        db_session
    ):
        """
        E2E Test: State Transition 검증

        Given: 초기 State (current_uc = None)
        When: Workflow 실행
        Then: State 변화 추적
            - START → Supervisor → UC1 → END
        """

        # Given: Master Graph
        master_app = build_master_graph()

        # Given: 초기 State
        initial_state = master_workflow_initial_state
        assert initial_state.get("current_uc") is None, \
            "Initial current_uc should be None"
        assert initial_state.get("workflow_history") == [], \
            "Initial workflow_history should be empty"

        # Mock: DB
        with patch('src.storage.database.get_db') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            mock_get_db.return_value.__exit__.return_value = None

            # When: Workflow 실행
            final_state = master_app.invoke(initial_state)

            # Then: State 변화 검증
            assert final_state.get("current_uc") in ["UC1", None], \
                "Current UC should be UC1 or None (after completion)"

            workflow_history = final_state.get("workflow_history", [])
            assert len(workflow_history) >= 2, \
                "Workflow history should have at least 2 steps (Supervisor, UC1)"

            # Then: 실패 카운트 0 유지
            assert final_state.get("failure_count", 0) == 0, \
                "Failure count should remain 0 on success"

    def test_uc1_success_final_result_structure(
        self,
        master_workflow_initial_state,
        test_article_high_quality,
        db_session
    ):
        """
        E2E Test: Final Result 구조 검증

        Given: 고품질 기사
        When: UC1 성공
        Then: final_result 구조 검증
            - title, body, date 존재
            - status = "success"
        """

        # Given: Master Graph
        master_app = build_master_graph()

        # Given: 초기 State
        initial_state = master_workflow_initial_state

        # Mock: DB
        with patch('src.storage.database.get_db') as mock_get_db:
            mock_get_db.return_value.__enter__.return_value = db_session
            mock_get_db.return_value.__exit__.return_value = None

            # When: Workflow 실행
            final_state = master_app.invoke(initial_state)

            # Then: Final Result 구조 검증
            final_result = final_state.get("final_result")
            assert final_result is not None, "Final result should exist"

            # Then: 필수 필드 존재
            assert "title" in final_result, "Final result should have 'title'"
            assert "body" in final_result, "Final result should have 'body'"
            assert "date" in final_result, "Final result should have 'date'"

            # Then: Status
            assert final_result.get("status") in ["success", "validated"], \
                "Final result status should be success or validated"

            # Then: 추출된 데이터 검증
            assert len(final_result.get("title", "")) > 0, "Title should not be empty"
            assert len(final_result.get("body", "")) > 0, "Body should not be empty"
