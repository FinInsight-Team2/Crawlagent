"""
CrawlAgent - Database Connection
Created: 2025-10-28

PostgreSQL 연결 및 세션 관리
"""

import os
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.storage.models import Base

# .env 파일 로드
load_dotenv()

# 환경변수에서 DATABASE_URL 가져오기
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://crawlagent:dev_password@localhost:5432/crawlagent"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=False,  # SQL 쿼리 로그 출력 (개발 시 True로 변경 가능)
    pool_size=5,  # 연결 풀 크기
    max_overflow=10,  # 최대 추가 연결 수
    pool_pre_ping=True,  # 연결 유효성 사전 확인
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    데이터베이스 세션을 반환하는 제너레이터

    Usage:
        with get_db() as db:
            selector = db.query(Selector).filter_by(site_name='yonhap').first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    데이터베이스 초기화 (테이블 생성)

    주의: 이 함수는 테스트 환경에서만 사용하세요.
    프로덕션에서는 Alembic 마이그레이션을 사용하세요.
    """
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """
    모든 테이블 삭제

    주의: 이 함수는 테스트 환경에서만 사용하세요!
    """
    Base.metadata.drop_all(bind=engine)


# 모듈 import 시 자동으로 연결 테스트
try:
    with engine.connect() as conn:
        pass  # 연결만 확인
except Exception as e:
    print(f"⚠️ PostgreSQL 연결 실패: {e}")
    print(f"DATABASE_URL: {DATABASE_URL}")
