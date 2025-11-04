-- 증분 수집 필드 추가 (Incremental Crawling Support)
-- 작성일: 2025-11-03
-- 목적: 날짜 기반 증분 수집 및 향후 SNS/동적 콘텐츠 지원

-- ============================================
-- 필수 필드 (Phase 1 - PoC)
-- ============================================

ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,           -- 수집 날짜 (크롤러 실행 날짜)
ADD COLUMN article_date DATE,         -- 기사 발행 날짜 (article:published_time)
ADD COLUMN is_latest BOOLEAN DEFAULT true;  -- 최신 버전 여부 (동일 URL 여러 버전 관리)

-- 성능 최적화를 위한 인덱스 생성
CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);

-- 복합 인덱스: 날짜 범위 + 최신 버전 필터 쿼리 최적화
CREATE INDEX idx_article_date_is_latest ON crawl_results(article_date, is_latest);

-- ============================================
-- 선택 필드 (Phase 2 - SNS/블로그 확장 준비)
-- ============================================
-- 주석 처리: 필요 시 주석 해제하여 사용

-- ALTER TABLE crawl_results
-- ADD COLUMN content_type VARCHAR(50) DEFAULT 'news',  -- 'news', 'sns', 'blog', 'ecommerce'
-- ADD COLUMN metadata JSONB,                            -- SNS 메타데이터 (likes, comments, shares)
-- ADD COLUMN version INTEGER DEFAULT 1,                 -- 동일 URL 버전 번호
-- ADD COLUMN last_updated TIMESTAMP;                    -- 마지막 업데이트 시각

-- CREATE INDEX idx_content_type ON crawl_results(content_type);
-- CREATE INDEX idx_metadata ON crawl_results USING GIN (metadata);
-- CREATE INDEX idx_version ON crawl_results(url, version);

-- ============================================
-- 마이그레이션 검증
-- ============================================

-- 컬럼 추가 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'crawl_results'
  AND column_name IN ('crawl_date', 'article_date', 'is_latest')
ORDER BY ordinal_position;

-- 인덱스 생성 확인
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'crawl_results'
  AND indexname LIKE 'idx_%'
ORDER BY indexname;
