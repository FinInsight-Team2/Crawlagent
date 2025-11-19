# CrawlAgent Database Schema

**Version**: 1.0
**Last Updated**: 2025-11-19
**Database**: PostgreSQL 16
**ORM**: SQLAlchemy 2.0

This document describes the database schema for CrawlAgent's persistent storage.

---

## Table of Contents

1. [Overview](#overview)
2. [Entity Relationship Diagram](#entity-relationship-diagram)
3. [Table Definitions](#table-definitions)
4. [Common Queries](#common-queries)
5. [Indexes & Performance](#indexes--performance)
6. [Data Retention](#data-retention)
7. [Migrations](#migrations)

---

## Overview

### Database Configuration

**Connection String** (from `.env`):
```bash
DATABASE_URL=postgresql://crawlagent:password@localhost:5432/crawlagent
```

**Key Features**:
- PostgreSQL 16 (JSON/JSONB support)
- SQLAlchemy ORM for type-safe queries
- GIN indexes for JSONB queries
- Automatic timestamps
- Check constraints for data integrity

### Tables Summary

| Table | Purpose | Row Count (Phase 1) |
|-------|---------|---------------------|
| `selectors` | CSS Selectors for each site | 8 sites |
| `crawl_results` | Crawled article data | 459 articles |
| `decision_logs` | 2-Agent consensus logs | ~50 logs |
| `cost_metrics` | LLM API cost tracking | ~100 calls |

---

## Entity Relationship Diagram

```
┌──────────────────┐
│   selectors      │
├──────────────────┤
│ id (PK)          │
│ site_name (UK)   │◄─────────┐
│ title_selector   │          │ References site_name
│ body_selector    │          │
│ date_selector    │          │
│ success_count    │          │
│ failure_count    │          │
└──────────────────┘          │
                              │
┌──────────────────┐          │
│ crawl_results    │          │
├──────────────────┤          │
│ id (PK)          │          │
│ url (UK)         │          │
│ site_name (FK)   │──────────┘
│ title            │
│ body             │
│ quality_score    │
│ crawl_mode       │
│ created_at       │
└──────────────────┘
          │
          │ Referenced by url
          │
┌──────────────────┐
│ decision_logs    │
├──────────────────┤
│ id (PK)          │
│ url (FK)         │──────────┐
│ site_name        │          │ Relates to crawl_results.url
│ gpt_analysis     │          │
│ gpt4o_validation │          │
│ consensus_reached│          │
│ retry_count      │          │
└──────────────────┘          │
                              │
┌──────────────────┐          │
│ cost_metrics     │          │
├──────────────────┤          │
│ id (PK)          │          │ Tracks costs per crawl
│ timestamp        │          │
│ provider         │          │
│ model            │          │
│ use_case         │          │
│ total_cost       │          │
└──────────────────┘          │
```

**Relationships**:
- `crawl_results.site_name` → `selectors.site_name` (logical FK, not enforced)
- `decision_logs.url` → `crawl_results.url` (logical FK, not enforced)
- No foreign key constraints for flexibility

---

## Table Definitions

### 1. `selectors` Table

Stores CSS selectors for each news site.

#### Schema

```sql
CREATE TABLE selectors (
    id SERIAL PRIMARY KEY,
    site_name VARCHAR(100) UNIQUE NOT NULL,
    title_selector TEXT NOT NULL,
    body_selector TEXT NOT NULL,
    date_selector TEXT NOT NULL,
    site_type VARCHAR(20) DEFAULT 'ssr' CHECK (site_type IN ('ssr', 'spa')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    success_count INTEGER DEFAULT 0 NOT NULL,
    failure_count INTEGER DEFAULT 0 NOT NULL
);

CREATE INDEX idx_selectors_site_name ON selectors(site_name);
```

#### Columns

| Column | Type | Constraint | Description |
|--------|------|------------|-------------|
| `id` | INTEGER | PK, AUTO_INCREMENT | Primary key |
| `site_name` | VARCHAR(100) | UNIQUE, NOT NULL | Site identifier (e.g., 'yonhap', 'bbc') |
| `title_selector` | TEXT | NOT NULL | CSS selector for article title |
| `body_selector` | TEXT | NOT NULL | CSS selector for article body |
| `date_selector` | TEXT | NOT NULL | CSS selector for publish date |
| `site_type` | VARCHAR(20) | CHECK ('ssr', 'spa') | Rendering type (default: 'ssr') |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp |
| `success_count` | INTEGER | DEFAULT 0 | Successful crawls using this selector |
| `failure_count` | INTEGER | DEFAULT 0 | Failed crawls using this selector |

#### Example Row

```sql
INSERT INTO selectors (site_name, title_selector, body_selector, date_selector)
VALUES (
    'yonhap',
    'h1.tit01',
    'div.content03',
    'meta[property="article:published_time"]'
);
```

#### SQLAlchemy Model

```python
from src.storage.models import Selector

# Query selector
selector = session.query(Selector).filter_by(site_name='yonhap').first()

# Update success count
selector.success_count += 1
session.commit()
```

---

### 2. `crawl_results` Table

Stores crawled article data and quality metrics.

#### Schema

```sql
CREATE TABLE crawl_results (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    category_kr VARCHAR(50),
    title TEXT,
    body TEXT,
    date TEXT,
    quality_score INTEGER CHECK (quality_score >= 0 AND quality_score <= 100),
    crawl_mode VARCHAR(20) CHECK (crawl_mode IN ('scrapy', '2-agent')),
    crawl_duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,

    -- Incremental crawling
    crawl_date DATE,
    article_date DATE,
    is_latest BOOLEAN DEFAULT TRUE NOT NULL,

    -- Content validation
    content_type VARCHAR(20) DEFAULT 'news' CHECK (content_type IN ('news', 'blog', 'community')),
    meta_data JSONB,
    url_category_confidence FLOAT DEFAULT 0.0 CHECK (url_category_confidence >= 0.0 AND url_category_confidence <= 1.0),
    validation_status VARCHAR(20) DEFAULT 'pending' CHECK (validation_status IN ('pending', 'verified', 'rejected')),
    validation_method VARCHAR(20) CHECK (validation_method IN ('rule', 'llm', '2-agent')),
    llm_reasoning TEXT
);

CREATE INDEX idx_crawl_results_site_name ON crawl_results(site_name);
CREATE INDEX idx_crawl_results_category ON crawl_results(category);
CREATE INDEX idx_crawl_results_quality_score ON crawl_results(quality_score);
CREATE INDEX idx_crawl_results_crawl_mode ON crawl_results(crawl_mode);
CREATE INDEX idx_crawl_results_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_crawl_results_article_date ON crawl_results(article_date);
CREATE INDEX idx_crawl_results_is_latest ON crawl_results(is_latest);
CREATE INDEX idx_crawl_results_content_type ON crawl_results(content_type);
CREATE INDEX idx_crawl_results_validation_status ON crawl_results(validation_status);
```

#### Key Columns

| Column | Type | Description |
|--------|------|-------------|
| `url` | TEXT | Unique article URL (primary identifier) |
| `site_name` | VARCHAR(100) | Site name (yonhap, bbc, etc.) |
| `title` | TEXT | Article title (extracted) |
| `body` | TEXT | Article body text (extracted) |
| `quality_score` | INTEGER (0-100) | 5W1H quality score |
| `crawl_mode` | VARCHAR | 'scrapy' (UC1) or '2-agent' (UC2/UC3) |
| `is_latest` | BOOLEAN | Latest version flag (for incremental) |
| `meta_data` | JSONB | Additional metadata (views, likes, etc.) |

#### Example Row

```sql
INSERT INTO crawl_results (
    url, site_name, title, body, date, quality_score, crawl_mode
) VALUES (
    'https://www.yna.co.kr/view/AKR20251119001',
    'yonhap',
    '삼성전자 주가 상승',
    '삼성전자 주가가 오늘 5% 상승했습니다...',
    '2025-11-19',
    97,
    'scrapy'
);
```

#### SQLAlchemy Model

```python
from src.storage.models import CrawlResult

# Insert article
article = CrawlResult(
    url="https://example.com/article/123",
    site_name="yonhap",
    title="Test Article",
    body="Article body",
    quality_score=95,
    crawl_mode="scrapy"
)
session.add(article)
session.commit()

# Query high-quality articles
high_quality = session.query(CrawlResult).filter(
    CrawlResult.quality_score >= 90
).all()
```

---

### 3. `decision_logs` Table

Stores 2-Agent consensus logs (UC2/UC3).

#### Schema

```sql
CREATE TABLE decision_logs (
    id SERIAL PRIMARY KEY,
    url TEXT NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    gpt_analysis JSONB,
    gpt4o_validation JSONB,
    consensus_reached BOOLEAN DEFAULT FALSE NOT NULL,
    retry_count INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL
);

CREATE INDEX idx_decision_logs_url ON decision_logs(url);
CREATE INDEX idx_decision_logs_consensus_reached ON decision_logs(consensus_reached);
CREATE INDEX idx_decision_logs_gpt_analysis_gin ON decision_logs USING GIN(gpt_analysis);
CREATE INDEX idx_decision_logs_gpt4o_validation_gin ON decision_logs USING GIN(gpt4o_validation);
```

#### JSONB Structure

**`gpt_analysis`** (Claude Sonnet 4.5 Proposer):
```json
{
  "title_selector": "h1.article-title",
  "body_selector": "div.article-body",
  "date_selector": "time.published",
  "confidence": 0.95,
  "reasoning": "Title selector matches h1 with class 'article-title'"
}
```

**`gpt4o_validation`** (GPT-4o Validator):
```json
{
  "is_valid": true,
  "confidence": 0.92,
  "feedback": "Selectors extract correct data",
  "extracted_samples": {
    "title": "Sample Title",
    "body": "Sample body text...",
    "date": "2025-11-19"
  }
}
```

#### Example Row

```sql
INSERT INTO decision_logs (
    url, site_name, gpt_analysis, gpt4o_validation, consensus_reached
) VALUES (
    'https://www.yna.co.kr/view/AKR20251119001',
    'yonhap',
    '{"title_selector": "h1.tit01", "confidence": 0.95}'::jsonb,
    '{"is_valid": true, "confidence": 0.92}'::jsonb,
    true
);
```

#### JSONB Queries

```sql
-- Find high-confidence proposals
SELECT * FROM decision_logs
WHERE (gpt_analysis->>'confidence')::float > 0.9;

-- Find successful consensus
SELECT * FROM decision_logs
WHERE consensus_reached = true
  AND (gpt4o_validation->>'is_valid')::boolean = true;
```

---

### 4. `cost_metrics` Table

Tracks LLM API costs.

#### Schema

```sql
CREATE TABLE cost_metrics (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    provider VARCHAR(20) CHECK (provider IN ('openai', 'gemini', 'claude')) NOT NULL,
    model VARCHAR(50) NOT NULL,
    use_case VARCHAR(10) CHECK (use_case IN ('uc1', 'uc2', 'uc3', 'other')) NOT NULL,
    input_tokens INTEGER DEFAULT 0 NOT NULL,
    output_tokens INTEGER DEFAULT 0 NOT NULL,
    total_tokens INTEGER DEFAULT 0 NOT NULL,
    input_cost FLOAT DEFAULT 0.0 NOT NULL,
    output_cost FLOAT DEFAULT 0.0 NOT NULL,
    total_cost FLOAT DEFAULT 0.0 NOT NULL,
    url TEXT
);

CREATE INDEX idx_cost_metrics_timestamp ON cost_metrics(timestamp);
CREATE INDEX idx_cost_metrics_provider ON cost_metrics(provider);
CREATE INDEX idx_cost_metrics_model ON cost_metrics(model);
CREATE INDEX idx_cost_metrics_use_case ON cost_metrics(use_case);
```

#### Example Row

```sql
INSERT INTO cost_metrics (
    provider, model, use_case, total_tokens, total_cost, url
) VALUES (
    'claude',
    'claude-sonnet-4-5-20250929',
    'uc2',
    1500,
    0.0037,
    'https://www.yna.co.kr/view/AKR20251119001'
);
```

#### Cost Aggregation Queries

```sql
-- Total cost by provider
SELECT provider, SUM(total_cost) as total_cost
FROM cost_metrics
GROUP BY provider;

-- Daily cost by use case
SELECT DATE(timestamp) as date, use_case, SUM(total_cost) as cost
FROM cost_metrics
GROUP BY DATE(timestamp), use_case
ORDER BY date DESC;
```

---

## Common Queries

### Get Selector for Site

```sql
SELECT * FROM selectors WHERE site_name = 'yonhap';
```

```python
from src.storage.models import Selector

selector = session.query(Selector).filter_by(site_name='yonhap').first()
print(f"Title: {selector.title_selector}")
```

---

### Find High-Quality Articles

```sql
SELECT url, title, quality_score
FROM crawl_results
WHERE quality_score >= 90
ORDER BY created_at DESC
LIMIT 10;
```

```python
from src.storage.models import CrawlResult

articles = (
    session.query(CrawlResult)
    .filter(CrawlResult.quality_score >= 90)
    .order_by(CrawlResult.created_at.desc())
    .limit(10)
    .all()
)
```

---

### Check Consensus Success Rate

```sql
SELECT
    site_name,
    COUNT(*) as total_attempts,
    SUM(CASE WHEN consensus_reached THEN 1 ELSE 0 END) as successful,
    ROUND(100.0 * SUM(CASE WHEN consensus_reached THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM decision_logs
GROUP BY site_name;
```

---

### Calculate Total API Costs

```sql
-- Total cost (all time)
SELECT SUM(total_cost) as total_cost FROM cost_metrics;

-- Cost by model
SELECT model, SUM(total_cost) as cost
FROM cost_metrics
GROUP BY model
ORDER BY cost DESC;

-- Cost savings (UC1 vs UC2/UC3)
SELECT
    CASE
        WHEN crawl_mode = 'scrapy' THEN 'UC1 (Free)'
        WHEN crawl_mode = '2-agent' THEN 'UC2/UC3 (Paid)'
    END as mode,
    COUNT(*) as count,
    COALESCE(SUM(cm.total_cost), 0) as total_cost
FROM crawl_results cr
LEFT JOIN cost_metrics cm ON cr.url = cm.url
GROUP BY crawl_mode;
```

---

### Get Latest Articles Per Site

```sql
SELECT DISTINCT ON (site_name) *
FROM crawl_results
WHERE is_latest = true
ORDER BY site_name, created_at DESC;
```

---

## Indexes & Performance

### Existing Indexes

| Table | Index | Type | Purpose |
|-------|-------|------|---------|
| `selectors` | `idx_selectors_site_name` | B-Tree | Fast site lookup |
| `crawl_results` | `idx_crawl_results_site_name` | B-Tree | Site filtering |
| `crawl_results` | `idx_crawl_results_quality_score` | B-Tree | Quality filtering |
| `decision_logs` | `idx_decision_logs_gpt_analysis_gin` | GIN | JSONB queries |
| `cost_metrics` | `idx_cost_metrics_timestamp` | B-Tree | Time-series queries |

### Query Optimization Tips

1. **Use indexes**:
   ```sql
   -- Good: Uses index
   SELECT * FROM crawl_results WHERE site_name = 'yonhap';

   -- Bad: Full table scan
   SELECT * FROM crawl_results WHERE LOWER(site_name) = 'yonhap';
   ```

2. **JSONB queries**:
   ```sql
   -- Use GIN index
   SELECT * FROM decision_logs
   WHERE gpt_analysis @> '{"confidence": 0.95}';
   ```

3. **Limit results**:
   ```sql
   -- Always use LIMIT for pagination
   SELECT * FROM crawl_results
   ORDER BY created_at DESC
   LIMIT 100 OFFSET 0;
   ```

---

## Data Retention

### Current Strategy

- **`crawl_results`**: Keep all (no automatic deletion)
- **`decision_logs`**: Keep all (debugging historical data)
- **`cost_metrics`**: Keep all (cost analysis)
- **`selectors`**: Keep all (active selectors)

### Future Cleanup (Phase 2)

```sql
-- Delete old decision logs (>90 days)
DELETE FROM decision_logs
WHERE created_at < NOW() - INTERVAL '90 days';

-- Archive old articles (>1 year)
UPDATE crawl_results
SET is_latest = false
WHERE created_at < NOW() - INTERVAL '1 year';
```

---

## Migrations

### Migration Scripts

Located in: `scripts/migrations/`

1. **`001_add_incremental_fields.sql`**
   - Adds `crawl_date`, `article_date`, `is_latest`
   - For incremental crawling support

2. **`002_add_validation_and_content_types.sql`**
   - Adds `content_type`, `validation_status`, `meta_data`
   - For content validation

### Apply Migrations

```bash
# Run all migrations
cd scripts/migrations/
psql postgresql://crawlagent:password@localhost:5432/crawlagent < 001_add_incremental_fields.sql
psql postgresql://crawlagent:password@localhost:5432/crawlagent < 002_add_validation_and_content_types.sql
```

### Create New Migration

```bash
# Create new SQL file
cat > scripts/migrations/003_my_new_migration.sql << 'EOF'
-- Migration: Add new field
ALTER TABLE crawl_results ADD COLUMN my_field TEXT;

-- Create index
CREATE INDEX idx_crawl_results_my_field ON crawl_results(my_field);
EOF

# Apply
psql $DATABASE_URL < scripts/migrations/003_my_new_migration.sql
```

---

## Backup & Restore

### Backup Database

```bash
# Full backup
pg_dump postgresql://crawlagent:password@localhost:5432/crawlagent > backup.sql

# Backup single table
pg_dump -t selectors postgresql://crawlagent:password@localhost:5432/crawlagent > selectors_backup.sql

# Compressed backup
pg_dump postgresql://crawlagent:password@localhost:5432/crawlagent | gzip > backup.sql.gz
```

### Restore Database

```bash
# Restore from backup
psql postgresql://crawlagent:password@localhost:5432/crawlagent < backup.sql

# Restore compressed
gunzip -c backup.sql.gz | psql postgresql://crawlagent:password@localhost:5432/crawlagent
```

---

## Sample Data

### Insert Test Data

```sql
-- Insert test selector
INSERT INTO selectors (site_name, title_selector, body_selector, date_selector)
VALUES ('test_site', 'h1', 'div.body', 'time');

-- Insert test article
INSERT INTO crawl_results (url, site_name, title, body, quality_score, crawl_mode)
VALUES (
    'https://example.com/test',
    'test_site',
    'Test Article',
    'Test body content',
    95,
    'scrapy'
);

-- Insert test decision log
INSERT INTO decision_logs (url, site_name, consensus_reached)
VALUES ('https://example.com/test', 'test_site', true);
```

---

## Troubleshooting

### Connection Issues

```bash
# Test connection
psql postgresql://crawlagent:password@localhost:5432/crawlagent -c "SELECT 1;"

# Check if database exists
psql -U crawlagent -l | grep crawlagent

# Create database if missing
createdb -U crawlagent crawlagent
```

### Performance Issues

```sql
-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Check index usage
SELECT
    schemaname, tablename, indexname,
    idx_scan as index_scans
FROM pg_stat_user_indexes
ORDER BY idx_scan ASC;

-- Find slow queries
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

## Resources

- **PostgreSQL Docs**: https://www.postgresql.org/docs/16/
- **SQLAlchemy ORM**: https://docs.sqlalchemy.org/
- **JSONB Guide**: https://www.postgresql.org/docs/16/datatype-json.html
- **GIN Indexes**: https://www.postgresql.org/docs/16/gin-intro.html

---

**Document Version**: 1.0
**Generated**: 2025-11-19
**Database**: PostgreSQL 16
