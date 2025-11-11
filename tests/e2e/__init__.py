"""
E2E (End-to-End) 테스트 패키지

이 디렉토리는 Master Workflow 전체 흐름을 테스트합니다.

테스트 시나리오:
    1. test_master_workflow.py: UC1 성공 → END
    2. test_uc1_to_uc2.py: UC1 실패 → UC2 트리거 → 성공
    3. test_uc3_discovery.py: 신규 사이트 → UC3 Discovery

실행 방법:
    # 모든 E2E 테스트 실행
    pytest tests/e2e/ -v

    # 특정 테스트만 실행
    pytest tests/e2e/test_master_workflow.py -v

    # Slow 테스트 제외
    pytest tests/e2e/ -v -m "not slow"

작성일: 2025-11-11
"""
