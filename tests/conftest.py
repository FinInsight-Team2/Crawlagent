"""
Pytest Fixtures for CrawlAgent E2E Testing

제공 Fixtures:
    - db_session: PostgreSQL Docker (트랜잭션 Rollback으로 격리)
    - mock_llm_responses: LLM API Mock 응답
    - test_article_data: 테스트용 기사 데이터
    - master_workflow_initial_state: Master Workflow 초기 State

전략:
    - 실제 환경과 동일한 PostgreSQL Docker 사용
    - 각 테스트마다 트랜잭션 Rollback으로 완전 격리
    - LLM API는 Mock으로 비용 절감 (선택적 실제 호출 가능)

작성일: 2025-11-11
"""

import pytest
import os
from typing import Dict, Any
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

# ============================================================
# 1. Database Fixtures (PostgreSQL Docker)
# ============================================================

@pytest.fixture(scope="function")
def db_engine():
    """PostgreSQL Docker 엔진 사용 (실제 환경과 동일)"""
    from src.storage.models import Base
    from src.storage.database import get_engine

    # 실제 PostgreSQL Docker 엔진 사용
    engine = get_engine()

    yield engine

    # Cleanup: 엔진은 재사용하므로 dispose 안 함
    # (각 테스트마다 트랜잭션 Rollback으로 격리)


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    DB Session Fixture (각 테스트마다 트랜잭션 격리)

    트랜잭션 Rollback 전략:
        1. 테스트 시작: BEGIN 트랜잭션
        2. 테스트 실행: 모든 DB 작업
        3. 테스트 종료: ROLLBACK (데이터 복구)

    장점:
        - 실제 PostgreSQL 사용 (SQLite 호환성 문제 없음)
        - 테스트 간 완전 격리 (다른 테스트 영향 없음)
        - 빠른 속도 (ROLLBACK이 DROP TABLE보다 빠름)
    """
    # Connection 생성
    connection = db_engine.connect()

    # 트랜잭션 시작
    transaction = connection.begin()

    # Session 생성 (트랜잭션에 바인딩)
    Session = sessionmaker(bind=connection)
    session = Session()

    yield session

    # Cleanup: 트랜잭션 Rollback (모든 변경 취소)
    session.close()
    transaction.rollback()
    connection.close()


@contextmanager
def get_test_db(db_session):
    """Context Manager for DB operations in tests"""
    try:
        yield db_session
    finally:
        db_session.rollback()


# ============================================================
# 2. LLM 실제 호출 설정 (Mock 없음!)
# ============================================================

@pytest.fixture
def use_real_llm(request):
    """
    실제 LLM API 호출 여부 설정

    기본값: True (실제 LLM 호출)
    비용 절감 필요 시: pytest -k "not slow" (slow 테스트 제외)

    사용법:
        @pytest.mark.unit  # Mock 사용 (빠름, 비용 0)
        @pytest.mark.e2e   # 실제 LLM 사용 (느림, 비용 발생)
    """
    # unit 테스트인 경우에만 Mock 허용
    if "unit" in request.keywords:
        return False  # Mock 사용 (비용 절감)
    else:
        return True  # 실제 LLM 호출 (진짜 테스트)


# ============================================================
# 3. Test Data Fixtures
# ============================================================

@pytest.fixture
def test_article_high_quality():
    """고품질 테스트 기사 데이터"""
    return {
        "url": "https://www.yna.co.kr/view/AKR20251111000001001",
        "site_name": "yonhap",
        "title": "한국 경제 2025년 2.8% 성장 전망, IMF 보고서 발표",
        "body": """
국제통화기금(IMF)은 11일 발표한 세계경제전망 보고서에서
한국 경제가 2025년 2.8% 성장할 것으로 예상했다.
이는 지난 10월 전망치 2.5%보다 0.3%포인트 상향 조정된 수치다.

IMF는 한국의 수출 회복과 내수 개선이 성장률 상승의 주요 원인이라고 분석했다.
특히 반도체와 자동차 수출이 증가하면서 전체 수출이 호조를 보이고 있으며,
정부의 재정정책과 통화정책이 내수 진작에 기여하고 있다고 평가했다.

IMF 관계자는 "한국 경제의 펀더멘털이 견고하며, 글로벌 경기 회복과 함께
성장세가 지속될 것"이라고 전망했다.
        """.strip(),
        "date": "2025-11-11",
        "category": "economy",
        "html_content": "<html><body><h1>한국 경제 2025년 2.8% 성장 전망</h1><div>기사 본문...</div></body></html>"
    }


@pytest.fixture
def test_article_low_quality():
    """저품질 테스트 기사 데이터 (광고/보도자료)"""
    return {
        "url": "https://www.example.com/ad/12345",
        "site_name": "test_site",
        "title": "[특가] 최신 스마트폰 50% 할인 이벤트",
        "body": "지금 바로 구매하세요! 선착순 100명 한정! 무료 배송!",
        "date": "2025-11-11",
        "category": "advertisement",
        "html_content": "<html><body><h1>광고</h1></body></html>"
    }


@pytest.fixture
def test_article_incomplete():
    """불완전한 테스트 기사 데이터 (필드 누락)"""
    return {
        "url": "https://www.example.com/incomplete/12345",
        "site_name": "test_site",
        "title": "제목만 있는 기사",
        "body": "",  # 본문 없음
        "date": None,  # 날짜 없음
        "category": "unknown",
        "html_content": "<html><body><h1>제목만</h1></body></html>"
    }


@pytest.fixture
def test_html_sample():
    """테스트용 HTML 샘플 (UC2, UC3에서 사용)"""
    return """
<!DOCTYPE html>
<html>
<head>
    <title>테스트 뉴스 사이트</title>
</head>
<body>
    <article>
        <h1 class="article-title">테스트 기사 제목</h1>
        <time class="publish-date" datetime="2025-11-11">2025년 11월 11일</time>
        <div class="article-content">
            <p>첫 번째 문단입니다.</p>
            <p>두 번째 문단입니다.</p>
            <p>세 번째 문단입니다.</p>
        </div>
    </article>
</body>
</html>
    """.strip()


# ============================================================
# 4. Master Workflow Fixtures
# ============================================================

@pytest.fixture
def master_workflow_initial_state(test_article_high_quality):
    """Master Workflow 초기 State"""
    from src.workflow.master_crawl_workflow import MasterCrawlState

    state: MasterCrawlState = {
        "url": test_article_high_quality["url"],
        "site_name": test_article_high_quality["site_name"],
        "html_content": test_article_high_quality["html_content"],
        "raw_html": test_article_high_quality["html_content"],
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": [],
        "supervisor_reasoning": None,
        "supervisor_confidence": None,
        "routing_context": None,
    }

    return state


# ============================================================
# 5. Environment Fixtures
# ============================================================

@pytest.fixture(autouse=True)
def test_env_vars():
    """테스트용 환경 변수 설정 (모든 테스트에 자동 적용)"""
    original_env = os.environ.copy()

    # 테스트용 환경 변수
    os.environ["USE_SUPERVISOR_LLM"] = "false"  # Rule-based Supervisor 사용
    os.environ["OPENAI_API_KEY"] = "test-key-openai"
    os.environ["GOOGLE_API_KEY"] = "test-key-google"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"

    yield

    # Cleanup: 원래 환경 변수 복원
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================
# 6. Pytest Configuration
# ============================================================

def pytest_configure(config):
    """Pytest 초기 설정"""
    # Custom markers 등록
    config.addinivalue_line(
        "markers", "e2e: E2E 통합 테스트 (느림, 실제 LLM 호출 가능)"
    )
    config.addinivalue_line(
        "markers", "unit: 단위 테스트 (빠름, Mock 사용)"
    )
    config.addinivalue_line(
        "markers", "slow: 느린 테스트 (10초 이상)"
    )


def pytest_collection_modifyitems(config, items):
    """테스트 수집 후 메타데이터 수정"""
    for item in items:
        # E2E 테스트에 자동으로 slow marker 추가
        if "e2e" in item.nodeid:
            item.add_marker(pytest.mark.slow)
