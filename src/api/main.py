"""
CrawlAgent Master Crawl API
FastAPI-based RESTful API for self-healing web crawling

Version: 1.0.0
Created: 2025-11-19
"""

from datetime import datetime
from typing import Optional, List
import logging

from fastapi import FastAPI, HTTPException, Header, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, HttpUrl, Field

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState
from src.storage.database import get_db
from src.storage.models import Selector, CrawlResult
from src.api.auth import verify_api_key, APIKeyData
from src.api.middleware import rate_limit_middleware

# Logger 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI 인스턴스
app = FastAPI(
    title="CrawlAgent Master Crawl API",
    description="Self-Healing Web Crawling API with UC1/UC2/UC3 Auto-Routing",
    version="1.0.0",
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Rate Limiting 미들웨어
app.middleware("http")(rate_limit_middleware)

# ========================================
# Pydantic Models (Request/Response)
# ========================================

class CrawlRequest(BaseModel):
    """크롤링 요청 모델"""
    url: HttpUrl = Field(..., description="크롤링할 URL")
    site_name: str = Field(..., description="사이트 이름 (예: yonhap, bbc)")
    category: Optional[str] = Field(None, description="카테고리 (예: politics, economy)")

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://www.yonhapnewstv.co.kr/category/news/politics/all/20231",
                "site_name": "yonhap",
                "category": "politics"
            }
        }


class AsyncCrawlRequest(CrawlRequest):
    """비동기 크롤링 요청 모델"""
    webhook_url: Optional[HttpUrl] = Field(None, description="완료 시 호출할 Webhook URL")
    webhook_headers: Optional[dict] = Field(None, description="Webhook 헤더")


class BatchCrawlRequest(BaseModel):
    """배치 크롤링 요청 모델"""
    urls: List[CrawlRequest] = Field(..., max_items=100, description="크롤링할 URL 목록 (최대 100개)")
    webhook_url: Optional[HttpUrl] = Field(None, description="완료 시 호출할 Webhook URL")


class CrawlResponse(BaseModel):
    """크롤링 응답 모델"""
    status: str = Field("success", description="응답 상태 (success/error)")
    data: dict = Field(..., description="크롤링 결과 데이터")
    meta: dict = Field(..., description="메타데이터")


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    status: str = Field("error", description="에러 상태")
    error: dict = Field(..., description="에러 정보")
    meta: dict = Field(..., description="메타데이터")


# ========================================
# 헬스체크 엔드포인트
# ========================================

@app.get("/api/v1/health", tags=["System"])
async def health_check():
    """
    API 서버 상태 확인 (인증 불필요)

    Returns:
        dict: 서버 상태 정보
    """
    try:
        # Database 연결 확인
        db = next(get_db())
        db.execute("SELECT 1")
        db_status = "healthy"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        db_status = "unhealthy"

    return {
        "status": "healthy" if db_status == "healthy" else "degraded",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "checks": {
            "database": db_status,
        }
    }


# ========================================
# 크롤링 엔드포인트
# ========================================

@app.post("/api/v1/crawl", response_model=CrawlResponse, tags=["Crawling"])
async def crawl_sync(
    request: CrawlRequest,
    api_key_data: APIKeyData = Depends(verify_api_key)
):
    """
    단일 URL 크롤링 (동기)

    - UC1/UC2/UC3 자동 라우팅
    - Self-Healing 자동 적용
    - 응답 시간: 3-60초

    Args:
        request: 크롤링 요청
        api_key_data: API 키 검증 데이터

    Returns:
        CrawlResponse: 크롤링 결과

    Raises:
        HTTPException: 크롤링 실패 시
    """
    start_time = datetime.utcnow()
    logger.info(f"Crawl request: {request.url} (user: {api_key_data.user_id})")

    try:
        # Master Workflow 실행
        graph = build_master_graph()

        initial_state = MasterCrawlState(
            url=str(request.url),
            site_name=request.site_name,
            category=request.category or "general",
            messages=[],
        )

        result = graph.invoke(initial_state)

        # 결과 파싱
        use_case = result.get("final_use_case", "UC1")
        extracted_data = result.get("extracted_data", {})
        quality_score = result.get("quality_score", 0.0)

        # 성공 응답
        processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000

        return CrawlResponse(
            status="success",
            data={
                "crawl_id": f"cr_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
                "use_case": use_case,
                "title": extracted_data.get("title", ""),
                "body": extracted_data.get("body", ""),
                "date": extracted_data.get("date", ""),
                "quality_score": quality_score,
                "url": str(request.url),
                "processing_time_ms": int(processing_time),
            },
            meta={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "version": "1.0.0",
            }
        )

    except Exception as e:
        logger.error(f"Crawl failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "code": "INTERNAL_ERROR",
                "message": str(e),
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )


@app.post("/api/v1/crawl/async", tags=["Crawling"])
async def crawl_async(
    request: AsyncCrawlRequest,
    background_tasks: BackgroundTasks,
    api_key_data: APIKeyData = Depends(verify_api_key)
):
    """
    단일 URL 크롤링 (비동기)

    - Webhook 콜백 지원
    - 백그라운드 처리
    - 즉시 task_id 반환

    Args:
        request: 비동기 크롤링 요청
        background_tasks: FastAPI 백그라운드 태스크
        api_key_data: API 키 검증 데이터

    Returns:
        dict: task_id 및 상태 URL
    """
    task_id = f"task_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"

    # 백그라운드 태스크 추가
    background_tasks.add_task(
        run_crawl_background,
        task_id=task_id,
        url=str(request.url),
        site_name=request.site_name,
        category=request.category,
        webhook_url=str(request.webhook_url) if request.webhook_url else None,
        webhook_headers=request.webhook_headers,
    )

    return {
        "status": "accepted",
        "data": {
            "task_id": task_id,
            "estimated_time_sec": 45,
            "status_url": f"/api/v1/tasks/{task_id}"
        }
    }


# ========================================
# Selector 관리 엔드포인트
# ========================================

@app.get("/api/v1/selectors", tags=["Selectors"])
async def list_selectors(
    site_name: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    api_key_data: APIKeyData = Depends(verify_api_key)
):
    """
    Selector 목록 조회

    Args:
        site_name: 사이트 필터 (optional)
        page: 페이지 번호 (default: 1)
        limit: 페이지 크기 (default: 20, max: 100)
        api_key_data: API 키 검증 데이터

    Returns:
        dict: Selector 목록 및 페이지네이션 정보
    """
    if limit > 100:
        limit = 100

    try:
        db = next(get_db())

        # 쿼리 빌드
        query = db.query(Selector)
        if site_name:
            query = query.filter(Selector.site_name == site_name)

        # 총 개수
        total = query.count()

        # 페이지네이션
        offset = (page - 1) * limit
        selectors = query.offset(offset).limit(limit).all()

        return {
            "status": "success",
            "data": {
                "selectors": [
                    {
                        "id": s.id,
                        "site_name": s.site_name,
                        "title_selector": s.title_selector,
                        "body_selector": s.body_selector,
                        "date_selector": s.date_selector,
                        "created_at": s.created_at.isoformat() + "Z" if s.created_at else None,
                    }
                    for s in selectors
                ],
                "pagination": {
                    "page": page,
                    "limit": limit,
                    "total": total,
                    "pages": (total + limit - 1) // limit,
                }
            }
        }

    except Exception as e:
        logger.error(f"List selectors failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 통계 엔드포인트
# ========================================

@app.get("/api/v1/stats", tags=["Statistics"])
async def get_stats(
    period: str = "today",
    api_key_data: APIKeyData = Depends(verify_api_key)
):
    """
    크롤링 통계 조회

    Args:
        period: today | week | month (default: today)
        api_key_data: API 키 검증 데이터

    Returns:
        dict: 크롤링 통계
    """
    try:
        db = next(get_db())

        # 기간 필터 (간단한 예시)
        from sqlalchemy import func

        total_crawls = db.query(CrawlResult).count()
        success_crawls = db.query(CrawlResult).filter(CrawlResult.quality_score >= 80).count()
        avg_quality = db.query(func.avg(CrawlResult.quality_score)).scalar() or 0.0

        return {
            "status": "success",
            "data": {
                "period": period,
                "total_crawls": total_crawls,
                "success_rate": success_crawls / total_crawls if total_crawls > 0 else 0,
                "avg_quality_score": round(avg_quality, 2),
            }
        }

    except Exception as e:
        logger.error(f"Get stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========================================
# 백그라운드 태스크
# ========================================

async def run_crawl_background(
    task_id: str,
    url: str,
    site_name: str,
    category: Optional[str],
    webhook_url: Optional[str],
    webhook_headers: Optional[dict]
):
    """
    백그라운드에서 크롤링 실행

    Args:
        task_id: 태스크 ID
        url: 크롤링 URL
        site_name: 사이트 이름
        category: 카테고리
        webhook_url: Webhook URL
        webhook_headers: Webhook 헤더
    """
    try:
        logger.info(f"Background task started: {task_id}")

        # Master Workflow 실행
        graph = build_master_graph()

        initial_state = MasterCrawlState(
            url=url,
            site_name=site_name,
            category=category or "general",
            messages=[],
        )

        result = graph.invoke(initial_state)

        # Webhook 콜백 (TODO: 구현)
        if webhook_url:
            logger.info(f"Sending webhook to: {webhook_url}")
            # requests.post(webhook_url, json=result, headers=webhook_headers)

        logger.info(f"Background task completed: {task_id}")

    except Exception as e:
        logger.error(f"Background task failed: {task_id}, error: {e}", exc_info=True)


# ========================================
# 서버 실행
# ========================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
