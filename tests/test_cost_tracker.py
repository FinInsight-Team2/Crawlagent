"""
Cost Tracker 테스트
Phase 3.2 Cost Tracking System 검증
"""

import pytest
from datetime import datetime, timedelta

from src.monitoring.cost_tracker import (
    calculate_cost,
    log_cost_to_db,
    get_total_cost,
    get_cost_breakdown,
    PRICING
)
from src.storage.database import get_db
from src.storage.models import CostMetric


class TestCostCalculation:
    """비용 계산 함수 테스트"""

    def test_calculate_cost_openai_gpt4o_mini(self):
        """OpenAI GPT-4o-mini 비용 계산"""
        result = calculate_cost("openai", "gpt-4o-mini", 1000, 200)

        assert result["input_cost"] == pytest.approx(1000 * 0.15 / 1_000_000, rel=1e-9)
        assert result["output_cost"] == pytest.approx(200 * 0.60 / 1_000_000, rel=1e-9)
        assert result["total_cost"] == pytest.approx(result["input_cost"] + result["output_cost"], rel=1e-9)
        assert result["total_cost"] == pytest.approx(0.00027, rel=1e-6)

    def test_calculate_cost_gemini_flash(self):
        """Gemini 2.0 Flash (Free) 비용 계산"""
        result = calculate_cost("gemini", "gemini-2.0-flash-exp", 5000, 1000)

        assert result["input_cost"] == 0.0
        assert result["output_cost"] == 0.0
        assert result["total_cost"] == 0.0

    def test_calculate_cost_unknown_provider(self):
        """Unknown provider 처리"""
        result = calculate_cost("unknown", "test-model", 1000, 200)

        assert result["input_cost"] == 0.0
        assert result["output_cost"] == 0.0
        assert result["total_cost"] == 0.0

    def test_calculate_cost_unknown_model(self):
        """Unknown model 처리"""
        result = calculate_cost("openai", "unknown-model", 1000, 200)

        assert result["input_cost"] == 0.0
        assert result["output_cost"] == 0.0
        assert result["total_cost"] == 0.0

    def test_calculate_cost_zero_tokens(self):
        """0 토큰 처리"""
        result = calculate_cost("openai", "gpt-4o-mini", 0, 0)

        assert result["total_cost"] == 0.0


class TestCostLogging:
    """비용 로깅 함수 테스트"""

    def test_log_cost_to_db_success(self):
        """DB 저장 성공"""
        metric_id = log_cost_to_db(
            provider="openai",
            model="gpt-4o-mini",
            use_case="uc1",
            input_tokens=500,
            output_tokens=100,
            url="https://test.com/article",
            site_name="test",
            extra_data={"test": True}
        )

        assert metric_id is not None
        assert isinstance(metric_id, int)

        # DB 확인
        db = next(get_db())
        try:
            metric = db.query(CostMetric).filter_by(id=metric_id).first()
            assert metric is not None
            assert metric.provider == "openai"
            assert metric.model == "gpt-4o-mini"
            assert metric.use_case == "uc1"
            assert metric.input_tokens == 500
            assert metric.output_tokens == 100
            assert metric.total_tokens == 600
            assert metric.url == "https://test.com/article"
            assert metric.site_name == "test"
            assert metric.extra_data == {"test": True}

            # Cleanup
            db.delete(metric)
            db.commit()
        finally:
            db.close()

    def test_log_cost_with_minimal_params(self):
        """최소 파라미터로 저장"""
        metric_id = log_cost_to_db(
            provider="gemini",
            model="gemini-2.5-pro",
            use_case="uc2",
            input_tokens=1000,
            output_tokens=200
        )

        assert metric_id is not None

        # Cleanup
        db = next(get_db())
        try:
            metric = db.query(CostMetric).filter_by(id=metric_id).first()
            db.delete(metric)
            db.commit()
        finally:
            db.close()


class TestCostAnalytics:
    """비용 분석 함수 테스트"""

    @pytest.fixture(autouse=True)
    def setup_test_data(self):
        """테스트 데이터 생성"""
        # 테스트 비용 데이터 3개 생성
        self.test_ids = []

        # OpenAI UC1
        id1 = log_cost_to_db(
            provider="openai",
            model="gpt-4o-mini",
            use_case="uc1",
            input_tokens=1000,
            output_tokens=200,
            site_name="test_site_1"
        )
        self.test_ids.append(id1)

        # Gemini UC2
        id2 = log_cost_to_db(
            provider="gemini",
            model="gemini-2.5-pro",
            use_case="uc2",
            input_tokens=1500,
            output_tokens=300,
            site_name="test_site_2"
        )
        self.test_ids.append(id2)

        # OpenAI UC3
        id3 = log_cost_to_db(
            provider="openai",
            model="gpt-4o",
            use_case="uc3",
            input_tokens=2000,
            output_tokens=500,
            site_name="test_site_1"
        )
        self.test_ids.append(id3)

        yield

        # Cleanup
        db = next(get_db())
        try:
            for test_id in self.test_ids:
                metric = db.query(CostMetric).filter_by(id=test_id).first()
                if metric:
                    db.delete(metric)
            db.commit()
        finally:
            db.close()

    def test_get_total_cost(self):
        """총 비용 조회"""
        total = get_total_cost()
        assert total >= 0

    def test_get_total_cost_by_provider(self):
        """Provider별 비용 조회"""
        openai_cost = get_total_cost(provider="openai")
        gemini_cost = get_total_cost(provider="gemini")

        assert openai_cost >= 0
        assert gemini_cost >= 0

    def test_get_total_cost_by_use_case(self):
        """Use Case별 비용 조회"""
        uc1_cost = get_total_cost(use_case="uc1")
        uc2_cost = get_total_cost(use_case="uc2")
        uc3_cost = get_total_cost(use_case="uc3")

        assert uc1_cost >= 0
        assert uc2_cost >= 0
        assert uc3_cost >= 0

    def test_get_total_cost_by_site(self):
        """Site별 비용 조회"""
        site1_cost = get_total_cost(site_name="test_site_1")
        site2_cost = get_total_cost(site_name="test_site_2")

        assert site1_cost >= 0
        assert site2_cost >= 0

    def test_get_total_cost_with_date_filter(self):
        """날짜 필터링"""
        today = datetime.utcnow().date()
        yesterday = today - timedelta(days=1)

        today_cost = get_total_cost(
            start_date=datetime.combine(today, datetime.min.time())
        )
        assert today_cost >= 0

    def test_get_cost_breakdown(self):
        """비용 분석 breakdown"""
        breakdown = get_cost_breakdown()

        assert "total_cost" in breakdown
        assert "total_tokens" in breakdown
        assert "by_provider" in breakdown
        assert "by_use_case" in breakdown
        assert "by_model" in breakdown
        assert "recent_costs" in breakdown

        assert isinstance(breakdown["total_cost"], float)
        assert isinstance(breakdown["total_tokens"], int)
        assert isinstance(breakdown["by_provider"], dict)
        assert isinstance(breakdown["by_use_case"], dict)
        assert isinstance(breakdown["by_model"], dict)
        assert isinstance(breakdown["recent_costs"], list)

        # Provider breakdown
        assert breakdown["total_cost"] >= 0
        assert breakdown["total_tokens"] >= 0


class TestPricingTable:
    """Pricing 테이블 검증"""

    def test_pricing_table_structure(self):
        """Pricing 테이블 구조 확인"""
        assert "openai" in PRICING
        assert "gemini" in PRICING
        assert "claude" in PRICING

    def test_openai_pricing(self):
        """OpenAI 가격 확인"""
        assert "gpt-4o-mini" in PRICING["openai"]
        assert "gpt-4o" in PRICING["openai"]

        gpt4o_mini = PRICING["openai"]["gpt-4o-mini"]
        assert "input" in gpt4o_mini
        assert "output" in gpt4o_mini
        assert gpt4o_mini["input"] > 0
        assert gpt4o_mini["output"] > 0

    def test_gemini_pricing(self):
        """Gemini 가격 확인"""
        assert "gemini-2.5-pro" in PRICING["gemini"]
        assert "gemini-2.0-flash-exp" in PRICING["gemini"]

        flash_exp = PRICING["gemini"]["gemini-2.0-flash-exp"]
        assert flash_exp["input"] == 0.0  # Free tier
        assert flash_exp["output"] == 0.0


class TestEdgeCases:
    """엣지 케이스 테스트"""

    def test_large_token_count(self):
        """매우 큰 토큰 수"""
        result = calculate_cost("openai", "gpt-4o-mini", 1_000_000, 500_000)
        assert result["total_cost"] > 0
        assert result["total_cost"] == pytest.approx(0.45, rel=1e-2)  # $0.15 + $0.30

    def test_case_insensitive_provider(self):
        """대소문자 구분 없는 provider"""
        result1 = calculate_cost("OpenAI", "gpt-4o-mini", 1000, 200)
        result2 = calculate_cost("OPENAI", "gpt-4o-mini", 1000, 200)
        result3 = calculate_cost("openai", "gpt-4o-mini", 1000, 200)

        assert result1["total_cost"] == result2["total_cost"]
        assert result2["total_cost"] == result3["total_cost"]
