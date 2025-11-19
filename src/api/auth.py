"""
API 인증 및 권한 관리
API Key 기반 인증 시스템

Version: 1.0.0
Created: 2025-11-19
"""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from fastapi import Header, HTTPException
from pydantic import BaseModel


class APIKeyData(BaseModel):
    """API 키 데이터 모델"""
    user_id: str
    api_key: str
    tier: str  # free, pro, enterprise
    rate_limit: int  # requests per hour


# 간단한 API 키 저장소 (Production에서는 Database 사용)
API_KEYS_DB = {
    "crawl_live_demo123": APIKeyData(
        user_id="demo_user",
        api_key="crawl_live_demo123",
        tier="free",
        rate_limit=100
    ),
    "crawl_live_pro456": APIKeyData(
        user_id="pro_user",
        api_key="crawl_live_pro456",
        tier="pro",
        rate_limit=1000
    ),
}


async def verify_api_key(x_api_key: str = Header(...)) -> APIKeyData:
    """
    API 키 검증

    Args:
        x_api_key: HTTP 헤더의 X-API-Key 값

    Returns:
        APIKeyData: 검증된 API 키 데이터

    Raises:
        HTTPException: API 키가 유효하지 않은 경우 (401)
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_API_KEY",
                "message": "API 키가 제공되지 않았습니다",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    # API 키 조회
    api_key_data = API_KEYS_DB.get(x_api_key)

    if not api_key_data:
        raise HTTPException(
            status_code=401,
            detail={
                "code": "INVALID_API_KEY",
                "message": "유효하지 않은 API 키입니다",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

    return api_key_data


def generate_api_key(prefix: str = "crawl_live") -> str:
    """
    새로운 API 키 생성

    Args:
        prefix: API 키 접두사 (default: crawl_live)

    Returns:
        str: 생성된 API 키 (예: crawl_live_abc123def456...)
    """
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}_{random_part}"


def hash_api_key(api_key: str) -> str:
    """
    API 키 해시 (저장용)

    Args:
        api_key: API 키

    Returns:
        str: SHA256 해시
    """
    return hashlib.sha256(api_key.encode()).hexdigest()
