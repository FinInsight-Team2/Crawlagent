"""
CrawlAgent - SQLAlchemy ORM Models
Created: 2025-10-28
Updated: 2025-11-06

PostgreSQL 16 테이블에 대한 ORM 모델 정의:
- Selector: CSS Selector 저장 (Multi-Site Support)
- CrawlResult: 크롤링 결과 저장
- DecisionLog: Multi-Agent 합의 로그 (JSONB)
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    Float,
    Integer,
    String,
    Text,
    TIMESTAMP,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import validates

Base = declarative_base()


class Selector(Base):
    """
    CSS Selector 저장 테이블

    각 뉴스 사이트의 title, body, date를 추출하는 CSS Selector를 저장합니다.
    - yonhap: 연합뉴스 (SSR)
    - naver_economy: 네이버 경제 (SSR)
    - bbc: BBC News (SSR - 2025-10-29 검증 완료)
    """

    __tablename__ = "selectors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    site_name = Column(String(100), unique=True, nullable=False, index=True)
    title_selector = Column(Text, nullable=False)
    body_selector = Column(Text, nullable=False)
    date_selector = Column(Text, nullable=False)
    site_type = Column(
        String(20),
        CheckConstraint("site_type IN ('ssr', 'spa')"),
        default="ssr",
        nullable=False,
    )
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    success_count = Column(Integer, default=0, nullable=False)
    failure_count = Column(Integer, default=0, nullable=False)

    @validates("site_type")
    def validate_site_type(self, key: str, value: str) -> str:
        """site_type은 'ssr' 또는 'spa'만 허용"""
        if value not in ("ssr", "spa"):
            raise ValueError(f"site_type must be 'ssr' or 'spa', got '{value}'")
        return value

    def __repr__(self) -> str:
        return (
            f"<Selector(site_name='{self.site_name}', "
            f"type='{self.site_type}', "
            f"success={self.success_count}, "
            f"failure={self.failure_count})>"
        )


class CrawlResult(Base):
    """
    크롤링 결과 저장 테이블

    UC1/UC2/UC3 모든 크롤링 결과를 저장합니다.
    - quality_score: 5W1H 기반 품질 점수 (0-100)
    - crawl_mode: 'scrapy' (UC1) 또는 '2-agent' (UC2/UC3)
    """

    __tablename__ = "crawl_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, unique=True, nullable=False)
    site_name = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=True, index=True)
    category_kr = Column(String(50), nullable=True)
    title = Column(Text, nullable=True)
    body = Column(Text, nullable=True)
    date = Column(Text, nullable=True)
    quality_score = Column(
        Integer,
        CheckConstraint("quality_score >= 0 AND quality_score <= 100"),
        nullable=True,
        index=True,
    )
    crawl_mode = Column(
        String(20),
        CheckConstraint("crawl_mode IN ('scrapy', '2-agent')"),
        nullable=True,
        index=True,
    )
    crawl_duration_seconds = Column(Float, nullable=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    # 증분 수집 필드 (Incremental Crawling Support)
    crawl_date = Column(Date, nullable=True, index=True, comment="수집 날짜 (크롤러 실행일)")
    article_date = Column(Date, nullable=True, index=True, comment="기사 발행 날짜")
    is_latest = Column(Boolean, default=True, nullable=False, index=True, comment="최신 버전 여부")

    # Phase 2: Content-Type 및 품질 검증 필드
    content_type = Column(
        String(20),
        CheckConstraint("content_type IN ('news', 'blog', 'community')"),
        default='news',
        nullable=False,
        index=True,
        comment="콘텐츠 타입 (news/blog/community)"
    )
    meta_data = Column(JSONB, nullable=True, comment="비정형 메타데이터 (조회수, 추천수 등)")

    # URL 카테고리 힌트 필드 (Phase 1.2)
    url_category_confidence = Column(
        Float,
        CheckConstraint("url_category_confidence >= 0.0 AND url_category_confidence <= 1.0"),
        default=0.0,
        nullable=False,
        comment="URL에서 추출한 카테고리 신뢰도 (0.0~1.0)"
    )

    validation_status = Column(
        String(20),
        CheckConstraint("validation_status IN ('pending', 'verified', 'rejected')"),
        default='pending',
        nullable=False,
        index=True,
        comment="검증 상태 (pending/verified/rejected)"
    )
    validation_method = Column(
        String(20),
        CheckConstraint("validation_method IN ('rule', 'llm', '2-agent')"),
        default='llm',
        nullable=True,
        comment="검증 방법 (rule/llm/2-agent)"
    )
    llm_reasoning = Column(Text, nullable=True, comment="LLM 판단 근거")

    @validates("quality_score")
    def validate_quality_score(self, key: str, value: Optional[int]) -> Optional[int]:
        """quality_score는 0-100 범위만 허용"""
        if value is not None and not (0 <= value <= 100):
            raise ValueError(f"quality_score must be 0-100, got {value}")
        return value

    @validates("crawl_mode")
    def validate_crawl_mode(self, key: str, value: Optional[str]) -> Optional[str]:
        """crawl_mode는 'scrapy' 또는 '2-agent'만 허용"""
        if value is not None and value not in ("scrapy", "2-agent"):
            raise ValueError(f"crawl_mode must be 'scrapy' or '2-agent', got '{value}'")
        return value

    def __repr__(self) -> str:
        return (
            f"<CrawlResult(url='{self.url[:50]}...', "
            f"site='{self.site_name}', "
            f"quality={self.quality_score}, "
            f"mode='{self.crawl_mode}')>"
        )


class DecisionLog(Base):
    """
    2-Agent 합의 로그 테이블

    GPT-4o와 Gemini 2.5의 분석 결과를 JSONB로 저장합니다.
    - gpt_analysis: GPT-4o의 CSS Selector 제안 (JSONB)
    - gemini_validation: Gemini 2.5의 검증 결과 (JSONB)
    - consensus_reached: 합의 성공 여부
    """

    __tablename__ = "decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(Text, nullable=False, index=True)
    site_name = Column(String(100), nullable=False)
    gpt_analysis = Column(JSONB, nullable=True)  # GIN 인덱스 적용됨
    gemini_validation = Column(JSONB, nullable=True)  # GIN 인덱스 적용됨
    consensus_reached = Column(Boolean, default=False, nullable=False, index=True)
    retry_count = Column(Integer, default=0, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return (
            f"<DecisionLog(url='{self.url[:50]}...', "
            f"consensus={self.consensus_reached}, "
            f"retries={self.retry_count})>"
        )


class CostMetric(Base):
    """
    LLM API 비용 추적 테이블

    OpenAI, Gemini, Claude 등 LLM API 호출 비용을 실시간으로 추적합니다.
    - UC1/UC2/UC3 각각의 비용을 분리 추적
    - 토큰 사용량 + 비용 계산
    - 일일/월간 집계 지원
    """

    __tablename__ = "cost_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(TIMESTAMP, default=datetime.utcnow, nullable=False, index=True)

    # API Provider (openai, gemini, claude)
    provider = Column(
        String(20),
        CheckConstraint("provider IN ('openai', 'gemini', 'claude')"),
        nullable=False,
        index=True
    )

    # Model Name (gpt-4o-mini, gemini-2.5-pro, claude-3-5-sonnet)
    model = Column(String(50), nullable=False, index=True)

    # Use Case (uc1, uc2, uc3)
    use_case = Column(
        String(10),
        CheckConstraint("use_case IN ('uc1', 'uc2', 'uc3', 'other')"),
        nullable=False,
        index=True
    )

    # Token Usage
    input_tokens = Column(Integer, default=0, nullable=False)
    output_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)

    # Cost (USD)
    input_cost = Column(Float, default=0.0, nullable=False)  # Input cost in USD
    output_cost = Column(Float, default=0.0, nullable=False)  # Output cost in USD
    total_cost = Column(Float, default=0.0, nullable=False)  # Total cost in USD

    # Context (optional metadata)
    url = Column(Text, nullable=True)  # Associated URL (if applicable)
    site_name = Column(String(100), nullable=True, index=True)  # Associated site
    workflow_run_id = Column(String(50), nullable=True, index=True)  # LangSmith run ID

    # Extra context (JSONB for flexible storage - 'metadata' is reserved in SQLAlchemy)
    extra_data = Column(JSONB, nullable=True, comment="Additional context (prompt length, response time, etc.)")

    def __repr__(self) -> str:
        return (
            f"<CostMetric(provider='{self.provider}', "
            f"model='{self.model}', "
            f"use_case='{self.use_case}', "
            f"cost=${self.total_cost:.6f})>"
        )


# 모든 모델을 외부에서 import할 수 있도록 export
__all__ = ["Base", "Selector", "CrawlResult", "DecisionLog", "CostMetric"]
