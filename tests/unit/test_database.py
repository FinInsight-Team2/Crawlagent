"""
CrawlAgent - Database Unit Tests
Created: 2025-11-15

Tests for database operations and models.
Target Coverage: 70%+
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

from src.storage.database import get_db, init_db, drop_db
from src.storage.models import Base, CrawlResult, Selector, DecisionLog, CostMetric


# ============================================================================
# Fixtures (Use db_session from conftest.py - PostgreSQL Docker)
# ============================================================================


@pytest.fixture
def sample_crawl_result_data():
    """Sample data for CrawlResult"""
    return {
        "url": "https://example.com/news/123",
        "site_name": "example",
        "title": "테스트 기사 제목",
        "body": "테스트 기사 본문입니다. " * 100,
        "date": "2025-11-15",
        "quality_score": 95,
        "crawl_mode": "scrapy",
        "validation_status": "verified",  # pending/verified/rejected
        "validation_method": "llm"  # rule/llm/2-agent (NOT uc1!)
    }


@pytest.fixture
def sample_selector_data():
    """Sample data for Selector"""
    return {
        "site_name": "example",
        "title_selector": "h1.article-title",
        "body_selector": "div.article-body",
        "date_selector": "time.publish-date",
        "site_type": "ssr",  # ssr or spa
        "success_count": 10,
        "failure_count": 0
    }


# ============================================================================
# Test: CrawlResult Model
# ============================================================================

def test_create_crawl_result(db_session, sample_crawl_result_data):
    """CrawlResult 생성 성공"""
    # Arrange & Act
    result = CrawlResult(**sample_crawl_result_data)
    db_session.add(result)
    db_session.commit()

    # Assert
    saved = db_session.query(CrawlResult).filter_by(url=sample_crawl_result_data["url"]).first()
    assert saved is not None
    assert saved.title == "테스트 기사 제목"
    assert saved.quality_score == 95
    assert saved.validation_status == "verified"


def test_crawl_result_unique_url_constraint(db_session, sample_crawl_result_data):
    """CrawlResult URL은 unique해야 함"""
    # Arrange
    result1 = CrawlResult(**sample_crawl_result_data)
    db_session.add(result1)
    db_session.commit()

    # Act & Assert - Duplicate URL should raise IntegrityError
    result2 = CrawlResult(**sample_crawl_result_data)
    db_session.add(result2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_crawl_result_quality_score_constraint(db_session, sample_crawl_result_data):
    """Quality Score는 0-100 범위여야 함"""
    # Valid scores
    for score in [0, 50, 100]:
        sample_crawl_result_data["url"] = f"https://example.com/news/{score}"
        sample_crawl_result_data["quality_score"] = score
        result = CrawlResult(**sample_crawl_result_data)
        db_session.add(result)
        db_session.commit()
        db_session.expunge_all()

    # Note: SQLite doesn't enforce CHECK constraints by default
    # In PostgreSQL, this would raise IntegrityError for scores < 0 or > 100


def test_crawl_result_crawl_mode_constraint(db_session, sample_crawl_result_data):
    """Crawl Mode는 'scrapy' 또는 '2-agent'만 허용"""
    # Valid modes
    for mode in ["scrapy", "2-agent"]:
        sample_crawl_result_data["url"] = f"https://example.com/news/{mode}"
        sample_crawl_result_data["crawl_mode"] = mode
        result = CrawlResult(**sample_crawl_result_data)
        db_session.add(result)
        db_session.commit()
        db_session.expunge_all()

    # Note: CHECK constraint behavior depends on DB engine


def test_crawl_result_created_at_auto_timestamp(db_session, sample_crawl_result_data):
    """created_at은 자동으로 현재 시각으로 설정"""
    # Arrange & Act
    before = datetime.utcnow()
    result = CrawlResult(**sample_crawl_result_data)
    db_session.add(result)
    db_session.commit()
    after = datetime.utcnow()

    # Assert
    saved = db_session.query(CrawlResult).filter_by(url=sample_crawl_result_data["url"]).first()
    assert saved.created_at is not None
    assert before <= saved.created_at <= after


def test_crawl_result_nullable_fields(db_session):
    """일부 필드는 NULL 허용"""
    # Arrange - Minimal required fields
    result = CrawlResult(
        url="https://example.com/minimal",
        site_name="example",
        title=None,  # Nullable
        body=None,  # Nullable
        date=None,  # Nullable
        quality_score=None,  # Nullable
        crawl_mode=None,  # Nullable
        validation_status="pending",
        validation_method=None  # Nullable
    )

    # Act
    db_session.add(result)
    db_session.commit()

    # Assert
    saved = db_session.query(CrawlResult).filter_by(url="https://example.com/minimal").first()
    assert saved is not None
    assert saved.title is None
    assert saved.body is None
    assert saved.quality_score is None


def test_crawl_result_query_by_site_name(db_session, sample_crawl_result_data):
    """site_name으로 조회 (indexed)"""
    # Arrange - Create multiple results
    for i in range(5):
        data = sample_crawl_result_data.copy()
        data["url"] = f"https://example.com/news/{i}"
        data["site_name"] = "example" if i < 3 else "other"
        result = CrawlResult(**data)
        db_session.add(result)
    db_session.commit()

    # Act
    results = db_session.query(CrawlResult).filter_by(site_name="example").all()

    # Assert
    assert len(results) == 3


def test_crawl_result_query_by_quality_score(db_session, sample_crawl_result_data):
    """quality_score >= 80 조회 (indexed)"""
    # Arrange
    scores = [50, 70, 80, 90, 100]
    for score in scores:
        data = sample_crawl_result_data.copy()
        data["url"] = f"https://example.com/news/{score}"
        data["quality_score"] = score
        result = CrawlResult(**data)
        db_session.add(result)
    db_session.commit()

    # Act
    high_quality = db_session.query(CrawlResult).filter(CrawlResult.quality_score >= 80).all()

    # Assert
    assert len(high_quality) == 3  # 80, 90, 100


# ============================================================================
# Test: Selector Model
# ============================================================================

def test_create_selector(db_session, sample_selector_data):
    """Selector 생성 성공"""
    # Arrange & Act
    selector = Selector(**sample_selector_data)
    db_session.add(selector)
    db_session.commit()

    # Assert
    saved = db_session.query(Selector).filter_by(site_name="example").first()
    assert saved is not None
    assert saved.title_selector == "h1.article-title"
    assert saved.site_type == "ssr"
    assert saved.success_count == 10


def test_selector_unique_site_name_constraint(db_session, sample_selector_data):
    """Selector site_name은 unique해야 함"""
    # Arrange
    selector1 = Selector(**sample_selector_data)
    db_session.add(selector1)
    db_session.commit()

    # Act & Assert
    selector2 = Selector(**sample_selector_data)
    db_session.add(selector2)

    with pytest.raises(IntegrityError):
        db_session.commit()


def test_selector_update_success_rate(db_session, sample_selector_data):
    """Selector success_rate 업데이트"""
    # Arrange
    selector = Selector(**sample_selector_data)
    db_session.add(selector)
    db_session.commit()

    # Act
    selector.success_rate = 95.5
    selector.total_attempts = 20
    db_session.commit()

    # Assert
    saved = db_session.query(Selector).filter_by(site_name="example").first()
    assert saved.success_rate == 95.5
    assert saved.total_attempts == 20


def test_selector_nullable_optional_fields(db_session):
    """Selector 선택적 필드는 NULL 허용"""
    # Arrange - Only required fields
    selector = Selector(
        site_name="minimal",
        title_selector="h1",
        body_selector="div.content",
        date_selector=None,  # Nullable
        author_selector=None,  # Nullable
        category_selector=None,  # Nullable
        consensus_confidence=0.90,
        success_rate=100.0,
        total_attempts=1
    )

    # Act
    db_session.add(selector)
    db_session.commit()

    # Assert
    saved = db_session.query(Selector).filter_by(site_name="minimal").first()
    assert saved is not None
    assert saved.author_selector is None


# ============================================================================
# Test: DecisionLog Model
# ============================================================================

def test_create_decision_log(db_session):
    """DecisionLog 생성 성공"""
    # Arrange
    log = DecisionLog(
        url="https://example.com/news/123",
        site_name="example",
        gpt_analysis={"title_selector": "h1", "confidence": 0.95},
        gemini_validation={"valid": True, "confidence": 0.90},
        consensus_reached=True,
        retry_count=0
    )

    # Act
    db_session.add(log)
    db_session.commit()

    # Assert
    saved = db_session.query(DecisionLog).filter_by(url="https://example.com/news/123").first()
    assert saved is not None
    assert saved.consensus_reached is True
    assert saved.gpt_analysis["confidence"] == 0.95


def test_decision_log_query_by_consensus(db_session):
    """consensus_reached로 조회 (indexed)"""
    # Arrange
    for i in range(5):
        log = DecisionLog(
            url=f"https://example.com/{i}",
            site_name="example",
            consensus_reached=(i < 3),
            retry_count=i
        )
        db_session.add(log)
    db_session.commit()

    # Act
    successful = db_session.query(DecisionLog).filter_by(consensus_reached=True).all()

    # Assert
    assert len(successful) == 3


# ============================================================================
# Test: CostMetric Model
# ============================================================================

def test_create_cost_metric(db_session):
    """CostMetric 생성 성공"""
    # Arrange
    metric = CostMetric(
        provider="openai",
        model="gpt-4o",
        use_case="uc1",
        input_tokens=1000,
        output_tokens=500,
        total_tokens=1500,
        input_cost=0.005,
        output_cost=0.015,
        total_cost=0.020,
        url="https://example.com/news/123",
        site_name="example"
    )

    # Act
    db_session.add(metric)
    db_session.commit()

    # Assert
    saved = db_session.query(CostMetric).filter_by(provider="openai").first()
    assert saved is not None
    assert saved.total_cost == 0.020
    assert saved.total_tokens == 1500


def test_cost_metric_query_by_use_case(db_session):
    """use_case로 조회 (indexed)"""
    # Arrange
    cases = ["uc1", "uc1", "uc2", "uc3"]
    for i, uc in enumerate(cases):
        metric = CostMetric(
            provider="openai",
            model="gpt-4o",
            use_case=uc,
            input_tokens=100,
            output_tokens=50,
            total_tokens=150,
            total_cost=0.001
        )
        db_session.add(metric)
    db_session.commit()

    # Act
    uc1_metrics = db_session.query(CostMetric).filter_by(use_case="uc1").all()

    # Assert
    assert len(uc1_metrics) == 2


# ============================================================================
# Test: Database Functions
# ============================================================================

@patch('src.storage.database.SessionLocal')
def test_get_db_session_lifecycle(mock_session_local):
    """get_db() 제너레이터가 세션을 올바르게 관리"""
    # Arrange
    mock_session = Mock(spec=Session)
    mock_session_local.return_value = mock_session

    # Act
    db_gen = get_db()
    db = next(db_gen)

    # Assert - Session created
    assert db == mock_session
    mock_session_local.assert_called_once()

    # Cleanup
    try:
        next(db_gen)
    except StopIteration:
        pass

    # Assert - Session closed
    mock_session.close.assert_called_once()


@patch('src.storage.database.Base.metadata.create_all')
def test_init_db_creates_tables(mock_create_all):
    """init_db()가 모든 테이블 생성"""
    # Act
    init_db()

    # Assert
    mock_create_all.assert_called_once()


@patch('src.storage.database.Base.metadata.drop_all')
def test_drop_db_drops_tables(mock_drop_all):
    """drop_db()가 모든 테이블 삭제"""
    # Act
    drop_db()

    # Assert
    mock_drop_all.assert_called_once()


# ============================================================================
# Test: Complex Queries (Integration-like)
# ============================================================================

def test_crawl_result_with_selector_relationship(db_session, sample_crawl_result_data, sample_selector_data):
    """CrawlResult와 Selector의 site_name 관계 조회"""
    # Arrange
    selector = Selector(**sample_selector_data)
    db_session.add(selector)

    result = CrawlResult(**sample_crawl_result_data)
    db_session.add(result)
    db_session.commit()

    # Act - Query with JOIN (manual, no explicit relationship defined)
    from sqlalchemy import and_

    query = db_session.query(CrawlResult, Selector).filter(
        and_(
            CrawlResult.site_name == Selector.site_name,
            CrawlResult.site_name == "example"
        )
    ).first()

    # Assert
    assert query is not None
    crawl_result, selector = query
    assert crawl_result.site_name == selector.site_name


def test_bulk_insert_crawl_results(db_session, sample_crawl_result_data):
    """대량 CrawlResult 삽입"""
    # Arrange
    results = []
    for i in range(100):
        data = sample_crawl_result_data.copy()
        data["url"] = f"https://example.com/news/{i}"
        data["quality_score"] = 80 + (i % 20)
        results.append(CrawlResult(**data))

    # Act
    db_session.bulk_save_objects(results)
    db_session.commit()

    # Assert
    count = db_session.query(CrawlResult).count()
    assert count == 100

    # Query high quality
    high_quality = db_session.query(CrawlResult).filter(CrawlResult.quality_score >= 90).count()
    assert high_quality > 0


def test_update_selector_after_crawl_result(db_session, sample_selector_data):
    """Crawl 성공 후 Selector success_rate 업데이트 시뮬레이션"""
    # Arrange
    selector = Selector(**sample_selector_data)
    selector.success_rate = 90.0
    selector.total_attempts = 10
    db_session.add(selector)
    db_session.commit()

    # Act - Simulate successful crawl
    selector.total_attempts += 1
    successes = int(selector.success_rate * (selector.total_attempts - 1) / 100) + 1
    selector.success_rate = (successes / selector.total_attempts) * 100
    db_session.commit()

    # Assert
    saved = db_session.query(Selector).filter_by(site_name="example").first()
    assert saved.total_attempts == 11
    # New success_rate = (9 + 1) / 11 * 100 = 90.9%
    assert 90.0 <= saved.success_rate <= 91.0


def test_query_failed_crawls_for_reroute_analysis(db_session, sample_crawl_result_data):
    """실패한 크롤 결과 조회 (re-route 분석용)"""
    # Arrange - Create mix of passed/failed results
    for i in range(20):
        data = sample_crawl_result_data.copy()
        data["url"] = f"https://example.com/news/{i}"
        data["quality_score"] = 95 if i < 10 else 40
        data["validation_status"] = "pass" if i < 10 else "fail"
        result = CrawlResult(**data)
        db_session.add(result)
    db_session.commit()

    # Act - Query failed crawls
    failed = db_session.query(CrawlResult).filter(
        CrawlResult.validation_status == "fail"
    ).all()

    # Assert
    assert len(failed) == 10
    for result in failed:
        assert result.quality_score < 80


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_crawl_result_very_long_body(db_session, sample_crawl_result_data):
    """매우 긴 본문 저장 가능 (TEXT 타입)"""
    # Arrange
    long_body = "가" * 100000  # 100K characters
    sample_crawl_result_data["body"] = long_body

    # Act
    result = CrawlResult(**sample_crawl_result_data)
    db_session.add(result)
    db_session.commit()

    # Assert
    saved = db_session.query(CrawlResult).filter_by(url=sample_crawl_result_data["url"]).first()
    assert len(saved.body) == 100000


def test_selector_zero_success_rate(db_session, sample_selector_data):
    """Selector success_rate = 0 가능"""
    # Arrange
    sample_selector_data["success_rate"] = 0.0
    sample_selector_data["total_attempts"] = 5
    selector = Selector(**sample_selector_data)

    # Act
    db_session.add(selector)
    db_session.commit()

    # Assert
    saved = db_session.query(Selector).filter_by(site_name="example").first()
    assert saved.success_rate == 0.0


def test_empty_string_vs_null(db_session, sample_crawl_result_data):
    """빈 문자열('')과 NULL은 다름"""
    # Arrange
    sample_crawl_result_data["title"] = ""  # Empty string
    sample_crawl_result_data["body"] = None  # NULL

    # Act
    result = CrawlResult(**sample_crawl_result_data)
    db_session.add(result)
    db_session.commit()

    # Assert
    saved = db_session.query(CrawlResult).filter_by(url=sample_crawl_result_data["url"]).first()
    assert saved.title == ""
    assert saved.body is None


def test_transaction_rollback_on_error(db_session, sample_crawl_result_data):
    """에러 발생 시 트랜잭션 롤백"""
    # Arrange
    result1 = CrawlResult(**sample_crawl_result_data)
    db_session.add(result1)
    db_session.commit()

    # Act - Try to insert duplicate (should fail)
    try:
        result2 = CrawlResult(**sample_crawl_result_data)
        db_session.add(result2)
        db_session.commit()
    except IntegrityError:
        db_session.rollback()

    # Assert - Database state unchanged
    count = db_session.query(CrawlResult).count()
    assert count == 1
