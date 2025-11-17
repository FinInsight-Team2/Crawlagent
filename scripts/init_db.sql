-- NewsFlow PoC - PostgreSQL Schema
-- Created: 2025-10-28
-- Description: 3 tables for selectors, crawl results, and decision logs

-- Table 1: selectors
CREATE TABLE IF NOT EXISTS selectors (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) UNIQUE NOT NULL,
    title_selector TEXT NOT NULL,
    body_selector TEXT NOT NULL,
    date_selector TEXT NOT NULL,
    site_type VARCHAR(20) DEFAULT 'ssr' CHECK (site_type IN ('ssr', 'spa')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0
);

-- Table 2: crawl_results
CREATE TABLE IF NOT EXISTS crawl_results (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    title TEXT,
    body TEXT,
    date TEXT,
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
    crawl_mode VARCHAR(20) CHECK (crawl_mode IN ('scrapy', '2-agent')),
    crawl_duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table 3: decision_logs
CREATE TABLE IF NOT EXISTS decision_logs (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    gpt_analysis JSONB,
    gpt4o_validation JSONB,
    consensus_reached BOOLEAN DEFAULT FALSE,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_selectors_site_name ON selectors(site_name);
CREATE INDEX IF NOT EXISTS idx_crawl_results_site_name ON crawl_results(site_name);
CREATE INDEX IF NOT EXISTS idx_crawl_results_quality_score ON crawl_results(quality_score);
CREATE INDEX IF NOT EXISTS idx_crawl_results_crawl_mode ON crawl_results(crawl_mode);
CREATE INDEX IF NOT EXISTS idx_decision_logs_url ON decision_logs(url);
CREATE INDEX IF NOT EXISTS idx_decision_logs_consensus ON decision_logs(consensus_reached);

-- JSONB indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_gpt_analysis ON decision_logs USING GIN (gpt_analysis);
CREATE INDEX IF NOT EXISTS idx_gpt4o_validation ON decision_logs USING GIN (gpt4o_validation);

-- Initial selector data (optional - can be inserted manually)
-- 2025-10-29 업데이트: 모든 사이트 SSR 검증 완료
INSERT INTO selectors (site_name, title_selector, body_selector, date_selector, site_type)
VALUES
    ('yonhap', 'article h1.tit', 'article div.article-txt', 'article time', 'ssr'),
    ('naver_economy', 'h2#title_area', 'div#dic_area', 'span.media_end_head_info_datestamp_time', 'ssr'),
    ('bbc', 'h1[data-component="headline-block"]', 'div[data-component="text-block"]', 'time', 'ssr')
ON CONFLICT (site_name) DO NOTHING;

-- Verification
SELECT 'Database schema created successfully!' AS status;
SELECT 'Total tables: ' || COUNT(*) AS table_count FROM information_schema.tables WHERE table_schema = 'public';
