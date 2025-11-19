"""
API 미들웨어
Rate Limiting 및 보안 기능

Version: 1.0.0
Created: 2025-11-19
"""

import time
from datetime import datetime
from collections import defaultdict
from typing import Dict, Tuple

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse


# Rate Limit 저장소 (Production에서는 Redis 사용)
# Format: {api_key: (count, reset_timestamp)}
rate_limit_store: Dict[str, Tuple[int, float]] = defaultdict(lambda: (0, 0.0))


async def rate_limit_middleware(request: Request, call_next):
    """
    Rate Limiting 미들웨어

    - 시간당 요청 횟수 제한
    - API 키별로 독립적인 카운터

    Args:
        request: FastAPI Request 객체
        call_next: 다음 미들웨어/핸들러

    Returns:
        Response: 정상 응답 또는 429 에러
    """
    # Health check는 Rate Limit 제외
    if request.url.path == "/api/v1/health":
        return await call_next(request)

    # API 키 추출
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        # 인증 필요한 엔드포인트는 auth.py에서 처리
        return await call_next(request)

    # Rate Limit 확인
    current_time = time.time()
    count, reset_time = rate_limit_store[api_key]

    # 1시간 경과 시 리셋
    if current_time > reset_time:
        count = 0
        reset_time = current_time + 3600  # 1시간 후

    # Rate Limit (간단한 예시: 100/hour)
    limit = 100
    if count >= limit:
        retry_after = int(reset_time - current_time)
        return JSONResponse(
            status_code=429,
            content={
                "status": "error",
                "error": {
                    "code": "RATE_LIMIT_EXCEEDED",
                    "message": f"시간당 요청 제한 초과 ({count}/{limit})",
                    "retry_after_sec": retry_after
                },
                "meta": {
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            },
            headers={"Retry-After": str(retry_after)}
        )

    # 카운터 증가
    rate_limit_store[api_key] = (count + 1, reset_time)

    # 다음 핸들러 호출
    response = await call_next(request)

    # Rate Limit 헤더 추가
    response.headers["X-RateLimit-Limit"] = str(limit)
    response.headers["X-RateLimit-Remaining"] = str(limit - count - 1)
    response.headers["X-RateLimit-Reset"] = str(int(reset_time))

    return response
