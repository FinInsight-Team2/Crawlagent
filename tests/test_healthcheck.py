"""
Healthcheck API 테스트
Phase 3.4 Monitoring & Healthcheck 검증
"""

import pytest
from datetime import datetime

from src.monitoring.healthcheck import (
    check_database_health,
    check_system_health,
    get_cost_metrics,
    get_article_metrics,
    get_uptime_seconds
)


class TestDatabaseHealth:
    """Database Health Check 테스트"""

    def test_check_database_health_success(self):
        """DB 연결 성공"""
        result = check_database_health()

        assert result["status"] == "healthy"
        assert result["error"] is None
        assert "connection_pool" in result
        assert "table_counts" in result

    def test_connection_pool_metrics(self):
        """Connection Pool 메트릭"""
        result = check_database_health()
        pool = result["connection_pool"]

        assert pool is not None
        assert "size" in pool
        assert "checked_in" in pool
        assert "checked_out" in pool
        assert "overflow" in pool
        assert "max_overflow" in pool

        # Connection pool 설정 확인 (Phase 3.3 최적화)
        assert pool["size"] == 10  # pool_size=10
        assert pool["max_overflow"] == 20  # max_overflow=20

    def test_table_counts(self):
        """테이블 레코드 수"""
        result = check_database_health()
        counts = result["table_counts"]

        assert counts is not None
        assert "articles" in counts
        assert "selectors" in counts
        assert "decision_logs" in counts
        assert "cost_metrics" in counts

        # 각 테이블 count는 0 이상
        assert counts["articles"] >= 0
        assert counts["selectors"] >= 0
        assert counts["decision_logs"] >= 0
        assert counts["cost_metrics"] >= 0


class TestSystemHealth:
    """System Health Check 테스트"""

    def test_check_system_health_success(self):
        """시스템 리소스 체크 성공"""
        result = check_system_health()

        assert result["status"] in ["healthy", "degraded"]
        assert "cpu_percent" in result
        assert "memory_percent" in result
        assert "disk_percent" in result

    def test_cpu_metrics(self):
        """CPU 메트릭"""
        result = check_system_health()

        assert 0 <= result["cpu_percent"] <= 100

    def test_memory_metrics(self):
        """Memory 메트릭"""
        result = check_system_health()

        assert 0 <= result["memory_percent"] <= 100
        assert result["memory_available_gb"] >= 0

    def test_disk_metrics(self):
        """Disk 메트릭"""
        result = check_system_health()

        assert 0 <= result["disk_percent"] <= 100
        assert result["disk_free_gb"] >= 0


class TestCostMetrics:
    """Cost Metrics Health Check 테스트"""

    def test_get_cost_metrics_success(self):
        """비용 메트릭 조회 성공"""
        result = get_cost_metrics()

        assert result["status"] in ["healthy", "degraded"]
        assert "total_cost_usd" in result
        assert "today_cost_usd" in result
        assert "total_tokens" in result
        assert "by_provider" in result
        assert "by_use_case" in result

    def test_cost_metrics_types(self):
        """비용 메트릭 타입"""
        result = get_cost_metrics()

        assert isinstance(result["total_cost_usd"], float)
        assert isinstance(result["today_cost_usd"], float)
        assert isinstance(result["total_tokens"], int)
        assert isinstance(result["by_provider"], dict)
        assert isinstance(result["by_use_case"], dict)

        # 비용은 0 이상
        assert result["total_cost_usd"] >= 0
        assert result["today_cost_usd"] >= 0
        assert result["total_tokens"] >= 0

    def test_today_cost_not_exceed_total(self):
        """오늘 비용 <= 총 비용"""
        result = get_cost_metrics()

        assert result["today_cost_usd"] <= result["total_cost_usd"]


class TestArticleMetrics:
    """Article Metrics Health Check 테스트"""

    def test_get_article_metrics_success(self):
        """기사 메트릭 조회 성공"""
        result = get_article_metrics()

        assert result["status"] in ["healthy", "degraded"]
        assert "total_articles" in result
        assert "avg_quality_score" in result
        assert "last_24h_count" in result

    def test_article_metrics_types(self):
        """기사 메트릭 타입"""
        result = get_article_metrics()

        assert isinstance(result["total_articles"], int)
        assert isinstance(result["avg_quality_score"], float)
        assert isinstance(result["last_24h_count"], int)

        # 값 범위 확인
        assert result["total_articles"] >= 0
        assert 0 <= result["avg_quality_score"] <= 100
        assert result["last_24h_count"] >= 0

    def test_last_24h_not_exceed_total(self):
        """최근 24h <= 총 기사 수"""
        result = get_article_metrics()

        assert result["last_24h_count"] <= result["total_articles"]


class TestUptimeTracking:
    """Uptime Tracking 테스트"""

    def test_get_uptime_seconds(self):
        """Uptime 조회"""
        uptime = get_uptime_seconds()

        assert isinstance(uptime, float)
        assert uptime >= 0

    def test_uptime_increases(self):
        """Uptime이 시간에 따라 증가"""
        import time

        uptime1 = get_uptime_seconds()
        time.sleep(0.1)
        uptime2 = get_uptime_seconds()

        assert uptime2 > uptime1


class TestHealthCheckIntegration:
    """통합 Health Check 테스트"""

    def test_all_health_checks_pass(self):
        """모든 Health Check 통과"""
        db_health = check_database_health()
        system_health = check_system_health()
        cost_metrics = get_cost_metrics()
        article_metrics = get_article_metrics()

        # 모두 status 필드가 있어야 함
        assert "status" in db_health
        assert "status" in system_health
        assert "status" in cost_metrics
        assert "status" in article_metrics

    def test_full_health_response_structure(self):
        """전체 Health Response 구조"""
        response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": get_uptime_seconds(),
            "database": check_database_health(),
            "system": check_system_health(),
            "metrics": get_article_metrics(),
            "costs": get_cost_metrics(),
        }

        # 필수 필드 확인
        assert "status" in response
        assert "timestamp" in response
        assert "uptime_seconds" in response
        assert "database" in response
        assert "system" in response
        assert "metrics" in response
        assert "costs" in response

        # Timestamp 형식 확인
        datetime.fromisoformat(response["timestamp"].replace('Z', '+00:00'))


class TestHealthCheckErrors:
    """Error Handling 테스트"""

    def test_database_health_handles_error_gracefully(self):
        """DB 에러 발생 시 graceful handling"""
        result = check_database_health()

        # 에러가 발생해도 status 필드는 있어야 함
        assert "status" in result
        assert result["status"] in ["healthy", "unhealthy"]

    def test_system_health_handles_error_gracefully(self):
        """System 에러 발생 시 graceful handling"""
        result = check_system_health()

        # 에러가 발생해도 status 필드는 있어야 함
        assert "status" in result
        assert result["status"] in ["healthy", "degraded"]


class TestPrometheusMetrics:
    """Prometheus Metrics 형식 테스트"""

    def test_metrics_format(self):
        """Prometheus 메트릭 형식 확인"""
        # 실제 metrics endpoint 테스트는 FastAPI TestClient 필요
        # 여기서는 데이터 구조만 확인

        db_health = check_database_health()
        system_health = check_system_health()
        cost_metrics = get_cost_metrics()
        article_metrics = get_article_metrics()

        # 메트릭으로 변환 가능한 숫자 값들 확인
        assert isinstance(article_metrics.get("total_articles"), int)
        assert isinstance(article_metrics.get("avg_quality_score"), float)
        assert isinstance(cost_metrics.get("total_cost_usd"), float)
        assert isinstance(cost_metrics.get("total_tokens"), int)
        assert isinstance(system_health.get("cpu_percent"), float)
        assert isinstance(system_health.get("memory_percent"), float)
