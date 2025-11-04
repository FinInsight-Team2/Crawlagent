-- CrawlAgent - DB Migration 002
-- Created: 2025-11-04
--
-- Phase 2 확장: Content-Type + 품질 검증 필드 추가
--
-- 변경 사항:
-- 1. content_type 컬럼 (news, blog, community)
-- 2. metadata JSONB (비정형 메타데이터)
-- 3. validation_status, validation_method, llm_reasoning (품질 검증 추적)

-- ============================================
-- 1. Content-Type 지원
-- ============================================

ALTER TABLE crawl_results
ADD COLUMN content_type VARCHAR(20) DEFAULT 'news'
    CHECK (content_type IN ('news', 'blog', 'community'));

CREATE INDEX idx_content_type ON crawl_results(content_type);

-- ============================================
-- 2. 비정형 메타데이터 (JSONB)
-- ============================================

ALTER TABLE crawl_results
ADD COLUMN metadata JSONB;

-- JSONB GIN 인덱스 (빠른 JSON 검색)
CREATE INDEX idx_metadata_gin ON crawl_results USING GIN (metadata);

-- ============================================
-- 3. 품질 검증 필드
-- ============================================

-- 검증 상태
ALTER TABLE crawl_results
ADD COLUMN validation_status VARCHAR(20) DEFAULT 'pending'
    CHECK (validation_status IN ('pending', 'verified', 'rejected'));

CREATE INDEX idx_validation_status ON crawl_results(validation_status);

-- 검증 방법
ALTER TABLE crawl_results
ADD COLUMN validation_method VARCHAR(20) DEFAULT 'llm'
    CHECK (validation_method IN ('rule', 'llm', '2-agent'));

-- LLM 판단 근거 (추적용)
ALTER TABLE crawl_results
ADD COLUMN llm_reasoning TEXT;

-- ============================================
-- 4. 복합 인덱스 (성능 최적화)
-- ============================================

-- 검증 완료된 데이터만 빠르게 조회
CREATE INDEX idx_validated_articles
ON crawl_results(content_type, validation_status, article_date)
WHERE validation_status = 'verified';

-- 카테고리별 검증 완료 데이터 조회
CREATE INDEX idx_category_validated
ON crawl_results(category, validation_status, article_date)
WHERE validation_status = 'verified';

-- ============================================
-- 5. 예시 데이터 (테스트용)
-- ============================================

-- News 예시
/*
INSERT INTO crawl_results (
    url, site_name, content_type, title, body, date,
    category, category_kr, quality_score,
    validation_status, validation_method, llm_reasoning,
    metadata
) VALUES (
    'https://yna.co.kr/view/AKR20251104...',
    'yonhap',
    'news',
    '삼성전자 3분기 실적 발표',
    '...',
    '2025-11-04T10:00:00Z',
    'economy',
    '경제',
    95,
    'verified',
    'llm',
    '5W1H 모두 포함, 광고 아님, 카테고리 적합',
    '{"author": "김기자", "section": "경제", "publisher": "연합뉴스"}'::jsonb
);
*/

-- Blog 예시
/*
INSERT INTO crawl_results (
    url, site_name, content_type, title, body, date,
    quality_score, validation_status, validation_method,
    metadata
) VALUES (
    'https://example.tistory.com/123',
    'tistory',
    'blog',
    '2025년 AI 트렌드 전망',
    '...',
    '2025-11-03',
    92,
    'verified',
    'llm',
    '{"author": "홍길동", "blog_name": "IT 트렌드", "views": 1234, "tags": ["AI", "트렌드"]}'::jsonb
);
*/

-- Community 예시
/*
INSERT INTO crawl_results (
    url, site_name, content_type, title, body, date,
    quality_score, validation_status, validation_method,
    metadata
) VALUES (
    'https://clien.net/service/board/park/12345',
    'clien',
    'community',
    '요즘 스타트업 취업 분위기',
    '...',
    '2025-11-04',
    88,
    'verified',
    'llm',
    '{"author": "닉네임", "board": "모두의공원", "views": 567, "upvotes": 89, "comment_count": 23}'::jsonb
);
*/

-- ============================================
-- 6. 유용한 쿼리 (분석용)
-- ============================================

-- 검증 완료된 데이터만 조회
-- SELECT * FROM crawl_results WHERE validation_status = 'verified';

-- Content-Type별 통계
-- SELECT content_type, COUNT(*), AVG(quality_score)
-- FROM crawl_results
-- WHERE validation_status = 'verified'
-- GROUP BY content_type;

-- 블로그 중 조회수 높은 순
-- SELECT title, (metadata->>'views')::int AS views
-- FROM crawl_results
-- WHERE content_type = 'blog' AND validation_status = 'verified'
-- ORDER BY (metadata->>'views')::int DESC
-- LIMIT 10;

-- 커뮤니티 중 추천 많은 순
-- SELECT title, (metadata->>'upvotes')::int AS upvotes
-- FROM crawl_results
-- WHERE content_type = 'community' AND validation_status = 'verified'
-- ORDER BY (metadata->>'upvotes')::int DESC
-- LIMIT 10;
