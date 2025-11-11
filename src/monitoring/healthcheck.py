"""
CrawlAgent Healthcheck API
Phase 3.4: Monitoring & Alerting

Purpose:
- Provide /health endpoint for system monitoring
- Check database connectivity
- Report system metrics (cost, articles, errors)
- Enable Prometheus/Grafana integration

Usage:
    poetry run python -m src.monitoring.healthcheck

    Then visit:
    - http://localhost:8000/health (JSON status)
    - http://localhost:8000/metrics (Prometheus format)
    - http://localhost:8000/docs (Swagger UI)
"""

from datetime import datetime, timedelta
from typing import Dict, Any
import psutil
import os

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel
from loguru import logger

from src.storage.database import engine, get_db
from src.storage.models import CrawlResult, Selector, DecisionLog, CostMetric
from src.monitoring.cost_tracker import get_cost_breakdown, get_total_cost


# ============================================================================
# FastAPI App Initialization
# ============================================================================

app = FastAPI(
    title="CrawlAgent Healthcheck API",
    description="Production-ready monitoring and healthcheck endpoints",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)


# ============================================================================
# Response Models
# ============================================================================

class HealthStatus(BaseModel):
    """Health check response model"""
    status: str  # "healthy" | "degraded" | "unhealthy"
    timestamp: str
    uptime_seconds: float
    database: Dict[str, Any]
    system: Dict[str, Any]
    metrics: Dict[str, Any]
    costs: Dict[str, Any]


class MetricsResponse(BaseModel):
    """Prometheus-compatible metrics response"""
    total_articles: int
    total_selectors: int
    total_decision_logs: int
    total_cost_usd: float
    database_connections: int
    system_cpu_percent: float
    system_memory_percent: float


# ============================================================================
# Startup Tracking
# ============================================================================

START_TIME = datetime.utcnow()


def get_uptime_seconds() -> float:
    """Calculate uptime in seconds"""
    return (datetime.utcnow() - START_TIME).total_seconds()


# ============================================================================
# Health Check Functions
# ============================================================================

def check_database_health() -> Dict[str, Any]:
    """
    Check database connectivity and metrics

    Returns:
        Dict with status, connection_pool, table_counts
    """
    try:
        # Test database connection
        with engine.connect() as conn:
            # Get connection pool stats
            pool = engine.pool
            pool_status = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "max_overflow": engine.pool._max_overflow,
            }

            # Get table counts
            db = next(get_db())
            try:
                table_counts = {
                    "articles": db.query(CrawlResult).count(),
                    "selectors": db.query(Selector).count(),
                    "decision_logs": db.query(DecisionLog).count(),
                    "cost_metrics": db.query(CostMetric).count(),
                }
            finally:
                db.close()

            return {
                "status": "healthy",
                "connection_pool": pool_status,
                "table_counts": table_counts,
                "error": None
            }

    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return {
            "status": "unhealthy",
            "connection_pool": None,
            "table_counts": None,
            "error": str(e)
        }


def check_system_health() -> Dict[str, Any]:
    """
    Check system resources (CPU, Memory, Disk)

    Returns:
        Dict with cpu_percent, memory_percent, disk_percent
    """
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "status": "healthy",
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
        }
    except Exception as e:
        logger.error(f"System health check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }


def get_cost_metrics() -> Dict[str, Any]:
    """
    Get cost tracking metrics

    Returns:
        Dict with total_cost, today_cost, breakdown
    """
    try:
        # Total cost
        total_cost = get_total_cost()

        # Today's cost
        today = datetime.utcnow().date()
        today_cost = get_total_cost(
            start_date=datetime.combine(today, datetime.min.time()),
            end_date=datetime.utcnow()
        )

        # Cost breakdown
        breakdown = get_cost_breakdown()

        return {
            "status": "healthy",
            "total_cost_usd": round(total_cost, 6),
            "today_cost_usd": round(today_cost, 6),
            "total_tokens": breakdown.get("total_tokens", 0),
            "by_provider": breakdown.get("by_provider", {}),
            "by_use_case": breakdown.get("by_use_case", {}),
        }
    except Exception as e:
        logger.error(f"Cost metrics check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }


def get_article_metrics() -> Dict[str, Any]:
    """
    Get article collection metrics

    Returns:
        Dict with total_articles, avg_quality, recent_counts
    """
    try:
        db = next(get_db())
        try:
            # Total articles
            total = db.query(CrawlResult).count()

            # Average quality
            if total > 0:
                scores = [r.quality_score for r in db.query(CrawlResult.quality_score).all() if r.quality_score]
                avg_quality = sum(scores) / len(scores) if scores else 0
            else:
                avg_quality = 0

            # Last 24 hours
            yesterday = datetime.utcnow() - timedelta(days=1)
            recent_count = db.query(CrawlResult).filter(
                CrawlResult.created_at >= yesterday
            ).count()

            return {
                "status": "healthy",
                "total_articles": total,
                "avg_quality_score": round(avg_quality, 1),
                "last_24h_count": recent_count,
            }
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Article metrics check failed: {e}")
        return {
            "status": "degraded",
            "error": str(e)
        }


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/", response_class=JSONResponse)
async def root():
    """Root endpoint - API information"""
    return {
        "service": "CrawlAgent Healthcheck API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "Health check (JSON)",
            "/metrics": "Prometheus metrics",
            "/docs": "Swagger UI documentation"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """
    Comprehensive health check endpoint

    Returns:
        HealthStatus: System health status with detailed metrics

    Status Codes:
        - 200: System is healthy
        - 503: System is unhealthy (database down, critical errors)
    """
    # Run all health checks
    db_health = check_database_health()
    system_health = check_system_health()
    cost_metrics = get_cost_metrics()
    article_metrics = get_article_metrics()

    # Determine overall status
    if db_health["status"] == "unhealthy":
        overall_status = "unhealthy"
        status_code = 503
    elif any(x["status"] == "degraded" for x in [system_health, cost_metrics, article_metrics]):
        overall_status = "degraded"
        status_code = 200
    else:
        overall_status = "healthy"
        status_code = 200

    response = {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": get_uptime_seconds(),
        "database": db_health,
        "system": system_health,
        "metrics": article_metrics,
        "costs": cost_metrics,
    }

    if overall_status == "unhealthy":
        return JSONResponse(content=response, status_code=status_code)
    else:
        return JSONResponse(content=response, status_code=status_code)


@app.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics():
    """
    Prometheus-compatible metrics endpoint

    Returns:
        Plain text metrics in Prometheus format

    Example:
        crawlagent_articles_total 1234
        crawlagent_cost_total_usd 0.045
        crawlagent_db_connections 5
    """
    try:
        # Get metrics
        db_health = check_database_health()
        system_health = check_system_health()
        cost_metrics = get_cost_metrics()
        article_metrics = get_article_metrics()

        # Format as Prometheus metrics
        metrics = []

        # Articles
        metrics.append(f'# HELP crawlagent_articles_total Total number of articles collected')
        metrics.append(f'# TYPE crawlagent_articles_total gauge')
        metrics.append(f'crawlagent_articles_total {article_metrics.get("total_articles", 0)}')

        metrics.append(f'# HELP crawlagent_articles_24h Articles collected in last 24 hours')
        metrics.append(f'# TYPE crawlagent_articles_24h gauge')
        metrics.append(f'crawlagent_articles_24h {article_metrics.get("last_24h_count", 0)}')

        # Quality
        metrics.append(f'# HELP crawlagent_quality_avg Average article quality score')
        metrics.append(f'# TYPE crawlagent_quality_avg gauge')
        metrics.append(f'crawlagent_quality_avg {article_metrics.get("avg_quality_score", 0)}')

        # Costs
        metrics.append(f'# HELP crawlagent_cost_total_usd Total LLM API cost (USD)')
        metrics.append(f'# TYPE crawlagent_cost_total_usd gauge')
        metrics.append(f'crawlagent_cost_total_usd {cost_metrics.get("total_cost_usd", 0)}')

        metrics.append(f'# HELP crawlagent_cost_today_usd Today\'s LLM API cost (USD)')
        metrics.append(f'# TYPE crawlagent_cost_today_usd gauge')
        metrics.append(f'crawlagent_cost_today_usd {cost_metrics.get("today_cost_usd", 0)}')

        metrics.append(f'# HELP crawlagent_tokens_total Total tokens used')
        metrics.append(f'# TYPE crawlagent_tokens_total gauge')
        metrics.append(f'crawlagent_tokens_total {cost_metrics.get("total_tokens", 0)}')

        # Database
        if db_health["connection_pool"]:
            pool = db_health["connection_pool"]
            metrics.append(f'# HELP crawlagent_db_connections Database connections in use')
            metrics.append(f'# TYPE crawlagent_db_connections gauge')
            metrics.append(f'crawlagent_db_connections {pool["checked_out"]}')

            metrics.append(f'# HELP crawlagent_db_pool_size Database connection pool size')
            metrics.append(f'# TYPE crawlagent_db_pool_size gauge')
            metrics.append(f'crawlagent_db_pool_size {pool["size"]}')

        # System
        metrics.append(f'# HELP crawlagent_cpu_percent CPU usage percentage')
        metrics.append(f'# TYPE crawlagent_cpu_percent gauge')
        metrics.append(f'crawlagent_cpu_percent {system_health.get("cpu_percent", 0)}')

        metrics.append(f'# HELP crawlagent_memory_percent Memory usage percentage')
        metrics.append(f'# TYPE crawlagent_memory_percent gauge')
        metrics.append(f'crawlagent_memory_percent {system_health.get("memory_percent", 0)}')

        # Uptime
        metrics.append(f'# HELP crawlagent_uptime_seconds Service uptime in seconds')
        metrics.append(f'# TYPE crawlagent_uptime_seconds gauge')
        metrics.append(f'crawlagent_uptime_seconds {get_uptime_seconds():.0f}')

        return PlainTextResponse(content='\n'.join(metrics) + '\n')

    except Exception as e:
        logger.error(f"Prometheus metrics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ping")
async def ping():
    """Simple ping endpoint for uptime monitoring"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ============================================================================
# Main (Development Server)
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    logger.info("=" * 60)
    logger.info("🚀 Starting CrawlAgent Healthcheck API")
    logger.info("=" * 60)
    logger.info("Endpoints:")
    logger.info("  - http://localhost:8000/health (Health check)")
    logger.info("  - http://localhost:8000/metrics (Prometheus metrics)")
    logger.info("  - http://localhost:8000/docs (Swagger UI)")
    logger.info("=" * 60)

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
