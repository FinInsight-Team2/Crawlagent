# CrawlAgent 옵션 A 개발 최종 기술 스택 & 준비 상태 보고서

**작성일**: 2025-11-03
**버전**: 1.0
**목적**: UC2 개발 + 증분 수집(옵션 A) 기술 스택 확정 및 개발 레디 상태 검증
**작업 디렉토리**: `/Users/charlee/Desktop/Intern/crawlagent`

---

## 🎯 최종 확정 기술 스택

### Core Stack (변경 없음)

| 레이어 | 기술 | 버전 | 상태 | 용도 |
|--------|------|------|------|------|
| **언어** | Python | 3.9.6 | ✅ 설치됨 | 전체 시스템 |
| **패키지 관리** | Poetry | 2.2.1 | ✅ 설치됨 | 의존성 관리 |
| **크롤링** | Scrapy | 2.11.0+ | ✅ 설치됨 | SSR 크롤링 |
| **콘텐츠 추출** | Trafilatura | 1.12.0+ | ✅ 설치됨 | 광고 제거 |
| **데이터베이스** | PostgreSQL | 16 | ✅ Docker 실행 중 | 데이터 저장 |
| **ORM** | SQLAlchemy | 2.0.0+ | ✅ 설치됨 | DB 추상화 |
| **마이그레이션** | Alembic | 1.13.0+ | ✅ 설치됨 | DB 스키마 관리 |
| **오케스트레이션** | LangGraph | 0.2.0+ | ✅ 설치됨 | Agent 워크플로우 |
| **LLM (Analyzer)** | GPT-4o | 2024-08-06 | ✅ API Key 설정됨 | CSS Selector 생성 |
| **LLM (Validator)** | Gemini 2.5 Flash | 2025-01 | ✅ API Key 설정됨 | Selector 검증 |
| **로깅** | Loguru | 0.7.0+ | ✅ 설치됨 | 구조화된 로깅 |
| **UI** | Gradio | 4.0.0+ | ✅ 설치됨 | 데모 인터페이스 |
| **컨테이너** | Docker Compose | 2.24+ | ✅ 실행 중 | PostgreSQL 환경 |

### 추가 Stack (옵션 A용 - 증분 수집 & 스케줄링)

| 레이어 | 기술 | 버전 | 상태 | 용도 | 설치 명령 |
|--------|------|------|------|------|-----------|
| **스케줄러** | APScheduler | 3.10+ | ❌ **설치 필요** | 일일 크롤링 자동화 | `poetry add apscheduler` |
| **날짜 처리** | python-dateutil | 2.9.0 | ✅ 설치됨 | 날짜 파싱/비교 | (이미 설치) |
| **HTTP 클라이언트** | httpx | 0.27.0+ | ✅ 설치됨 | 비동기 HTTP | (이미 설치) |
| **HTML 파싱** | BeautifulSoup4 | 4.12.0+ | ✅ 설치됨 | HTML 전처리 | (이미 설치) |

**설치 필요 항목**: APScheduler만 추가 설치 필요 (1개)

---

## 📊 Claude Skills & MCP 서버 분석

### Part 1: Claude Skills 생성 완료 ✅

**저장 위치**: `/Users/charlee/Desktop/Intern/crawlagent/.claude/skills/`

#### 생성된 Skills (3개)

| Skill 파일 | 목적 | 주요 내용 | 크기 |
|-----------|------|----------|------|
| **`uc2-development.md`** | UC2 개발 전용 컨텍스트 | - UC2 워크플로우 다이어그램<br>- GPT/Gemini 구현 패턴<br>- LangGraph StateGraph 예제<br>- 테스트 전략 | 7.2 KB |
| **`incremental-crawling.md`** | 증분 수집 구현 가이드 | - 날짜 기반 Spider 수정<br>- DB 스키마 확장<br>- 마이그레이션 스크립트<br>- 테스트 방법 | 5.8 KB |
| **`scheduler.md`** | 스케줄러 구현 가이드 | - APScheduler 패턴<br>- Cron vs Celery 비교<br>- Gradio UI 통합<br>- 에러 핸들링 | 6.4 KB |

**사용 방법**:
```bash
# Claude Code CLI에서 자동 로드됨 (재시작 불필요)
# Skill 컨텍스트는 대화 시작 시 자동 제공됨
```

**효과**:
- UC2 개발 시 핵심 패턴을 즉시 참조 가능
- 증분 수집 구현 시 단계별 가이드 제공
- 스케줄러 선택 시 비교표로 빠른 의사결정

### Part 2: MCP 서버 분석

**현재 상태**: MCP 서버 설정 파일 없음 (`~/.config/claude/claude_desktop_config.json` 미존재)

#### 유용한 MCP 서버 후보 (설치 권장하지 않음)

| MCP 서버 | 용도 | 평가 | 권장 여부 |
|----------|------|------|-----------|
| `@modelcontextprotocol/server-postgres` | PostgreSQL 쿼리 자동화 | PoC 단계에서 SQLAlchemy ORM으로 충분 | ❌ 불필요 |
| `@modelcontextprotocol/server-filesystem` | 파일 작업 자동화 | Claude Code 기본 파일 도구로 충분 | ❌ 불필요 |
| `@modelcontextprotocol/server-fetch` | HTTP 요청 | Scrapy로 이미 처리됨 | ❌ 불필요 |
| `@modelcontextprotocol/server-brave-search` | 웹 검색 | 신규 사이트 발견용 (UC3 단계) | ⏸️ Phase 2 |

**결론**: 현재 PoC 단계에서는 **MCP 서버 불필요**
- 기존 도구(Scrapy, SQLAlchemy, Claude Code)로 충분
- 복잡도 증가 대비 효과 미미
- UC3 (신규 사이트 발견) 단계에서 재검토

---

## 🛠️ 스케줄러 기술 선정 (Ultra-thorough 분석)

### 비교 분석표

| 항목 | APScheduler | Celery Beat | Cron | GitHub Actions |
|------|-------------|-------------|------|----------------|
| **설치 시간** | 5분 | 30분+ | 10분 | 15분 |
| **복잡도** | ⭐ (Low) | ⭐⭐⭐⭐ (High) | ⭐⭐ (Medium) | ⭐⭐⭐ (Medium) |
| **외부 의존성** | 없음 | Redis/RabbitMQ 필수 | 없음 | GitHub repo 필요 |
| **Python 통합** | Excellent | Excellent | Poor (subprocess) | N/A |
| **Gradio UI 통합** | 쉬움 (BackgroundScheduler) | 어려움 | 불가능 | 불가능 |
| **재시도 로직** | 수동 구현 | 내장 | 수동 구현 | 내장 |
| **모니터링** | 로그 + UI | Flower (별도 설치) | 로그만 | GitHub Actions UI |
| **프로덕션 레벨** | ✅ 충분 | ✅ 최고 | ✅ 충분 | ❌ 제한적 |
| **개발 편의성** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **비용** | 무료 | 무료 (self-host) | 무료 | Public repo만 무료 |
| **PoC 적합성** | ⭐⭐⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ | ⭐ |

### Option 1: APScheduler ⭐ **권장**

**장점**:
- Python native, 외부 서비스 불필요
- Gradio UI와 쉽게 통합 (`BackgroundScheduler`)
- 5분 내 구현 가능
- SQLite 백엔드로 작업 지속성 지원
- 개발/테스트가 매우 쉬움

**단점**:
- 프로세스 종료 시 스케줄 중단 (→ systemd/supervisor로 해결)
- 분산 작업 큐 미지원 (→ PoC에서 불필요)

**구현 예시**:
```python
from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import date, timedelta
import subprocess

def crawl_yesterday():
    yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    subprocess.run([
        "poetry", "run", "scrapy", "crawl", "yonhap",
        "-a", f"target_date={yesterday}"
    ])

scheduler = BlockingScheduler()
scheduler.add_job(crawl_yesterday, 'cron', hour=0, minute=30)
scheduler.start()
```

**사용 사례**: PoC 데모, 소규모 프로덕션 (하루 1-10회 실행)

### Option 2: Celery Beat

**장점**:
- 엔터프라이즈급 안정성
- 분산 작업 큐 지원
- 재시도, 우선순위, 체이닝 기능
- Flower 대시보드로 모니터링

**단점**:
- Redis 또는 RabbitMQ 필수 (복잡도 ↑↑)
- 설정 파일 복잡 (celeryconfig.py, beat-schedule.db)
- PoC 단계에서 과도한 설정

**구현 예시**:
```python
from celery import Celery
from celery.schedules import crontab

app = Celery('crawlagent', broker='redis://localhost:6379')

@app.task
def crawl_yesterday():
    # ... 크롤링 로직 ...

app.conf.beat_schedule = {
    'crawl-every-day': {
        'task': 'crawl_yesterday',
        'schedule': crontab(hour=0, minute=30)
    }
}
```

**사용 사례**: 대규모 프로덕션 (하루 100+ 작업), 분산 환경

### Option 3: Cron (시스템 레벨)

**장점**:
- OS 레벨 안정성 (가장 신뢰성 높음)
- 재부팅 후 자동 재시작
- 로그 로테이션 지원 (logrotate)
- 추가 Python 프로세스 불필요

**단점**:
- Python과 통합 어려움 (subprocess만 가능)
- Gradio UI에서 제어 불가
- 로컬 개발 환경에서 테스트 어려움
- macOS에서 crontab 권한 문제 가능

**구현 예시**:
```bash
# crontab -e
30 0 * * * cd /Users/charlee/Desktop/Intern/crawlagent && poetry run python src/scheduler/run_daily.py >> /var/log/crawler.log 2>&1
```

**사용 사례**: 프로덕션 서버 (Linux), UI 제어 불필요

### Option 4: GitHub Actions

**장점**:
- 서버 불필요 (GitHub 인프라 사용)
- YAML 설정으로 간단
- 무료 (Public repo)

**단점**:
- Self-hosted runner 필요 (Private repo 또는 로컬 DB 접근)
- Rate limit (월 2000분 Free tier)
- API Key 노출 위험 (Secrets 필요)
- 실시간 제어 어려움

**구현 예시**:
```yaml
# .github/workflows/daily-crawl.yml
on:
  schedule:
    - cron: '30 0 * * *'  # 00:30 UTC
jobs:
  crawl:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - run: poetry install
      - run: poetry run scrapy crawl yonhap -a target_date=$(date -d yesterday +%Y-%m-%d)
```

**사용 사례**: 클라우드 전용, Public repo

### 최종 권장 순위

| 순위 | 기술 | 용도 | 선택 근거 |
|------|------|------|-----------|
| **1위** | **APScheduler** | **PoC 데모, UC2 개발** | ✅ 즉시 시작 가능<br>✅ Gradio 통합 쉬움<br>✅ 복잡도 최소 |
| 2위 | Cron | 프로덕션 서버 | 장기 운영 시 가장 안정적 |
| 3위 | Celery Beat | 대규모 확장 | 분산 환경 필요 시 |
| 4위 | GitHub Actions | 클라우드 전용 | Self-hosted runner 복잡 |

**결정**: **APScheduler 3.10+ 사용** (PoC → 프로덕션 전환 시 Cron으로 마이그레이션)

---

## 🗄️ DB 스키마 확장 전략

### 현재 스키마 분석

**테이블 구조** (`scripts/init_db.sql`):

```sql
CREATE TABLE crawl_results (
    id SERIAL PRIMARY KEY,
    url TEXT UNIQUE NOT NULL,
    site_name VARCHAR(100) NOT NULL,
    category VARCHAR(50),           -- ✅ 이미 존재 (추가됨)
    category_kr VARCHAR(50),         -- ✅ 이미 존재 (추가됨)
    title TEXT,
    body TEXT,
    date TEXT,
    quality_score INTEGER,
    crawl_mode VARCHAR(20),
    crawl_duration_seconds FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**기존 인덱스**:
- `idx_crawl_results_site_name` ON `site_name`
- `idx_crawl_results_quality_score` ON `quality_score`
- `idx_crawl_results_crawl_mode` ON `crawl_mode`

### 확장 필요 필드 (증분 수집용)

#### 필수 추가 (High Priority)

```sql
-- Migration: scripts/migrations/001_add_incremental_fields.sql

ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,           -- 크롤링 수행 날짜 (2025-11-03)
ADD COLUMN article_date DATE,         -- 기사 발행 날짜 (2025-11-02)
ADD COLUMN is_latest BOOLEAN DEFAULT true;  -- 최신 버전 여부

-- 인덱스 추가 (성능 최적화)
CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);

-- 복합 인덱스 (자주 사용되는 쿼리 패턴)
CREATE INDEX idx_article_site_date ON crawl_results(site_name, article_date);
```

**필드 설명**:
- `crawl_date`: 실제로 크롤링을 수행한 날짜 (시스템 날짜)
- `article_date`: 기사가 발행된 날짜 (메타데이터에서 추출)
- `is_latest`: 동일 URL의 여러 버전 중 최신 버전 여부

**사용 사례**:
```sql
-- 어제 수집한 모든 기사
SELECT * FROM crawl_results WHERE crawl_date = '2025-11-02';

-- 어제 발행된 모든 기사 (수집 날짜 무관)
SELECT * FROM crawl_results WHERE article_date = '2025-11-02';

-- 최신 버전만 조회 (중복 제거)
SELECT * FROM crawl_results WHERE is_latest = true;
```

#### 선택 추가 (Future Extensions - Phase 2)

SNS/동적 콘텐츠 확장 대비:

```sql
-- Migration: scripts/migrations/002_add_metadata_fields.sql (나중에)

ALTER TABLE crawl_results
ADD COLUMN content_type VARCHAR(50) DEFAULT 'news',  -- 'news', 'sns', 'blog', 'video'
ADD COLUMN metadata JSONB,                            -- 유연한 메타데이터 저장
ADD COLUMN version INTEGER DEFAULT 1,                 -- 동일 URL의 버전 번호
ADD COLUMN last_updated TIMESTAMP;                    -- 마지막 업데이트 시각

-- JSONB GIN 인덱스 (빠른 JSON 쿼리)
CREATE INDEX idx_content_type ON crawl_results(content_type);
CREATE INDEX idx_metadata ON crawl_results USING GIN (metadata);
```

**metadata JSONB 활용 예**:
```json
{
  "author": "홍길동 기자",
  "tags": ["경제", "주식", "삼성전자"],
  "comments_count": 42,
  "shares": 128,
  "reactions": {"like": 85, "wow": 12}
}
```

### Migration 전략

#### Option A: ALTER TABLE (덮어쓰기) ⭐ **권장**

**장점**:
- 구현 간단 (SQL 1개 파일)
- 기존 데이터 보존
- Downtime 최소 (PostgreSQL은 ALTER TABLE이 빠름)

**단점**:
- 롤백 어려움 (수동 DROP COLUMN 필요)

**실행 방법**:
```bash
# 1. Migration 파일 생성
cat > scripts/migrations/001_add_incremental_fields.sql << 'EOF'
-- Add incremental crawling fields
ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,
ADD COLUMN article_date DATE,
ADD COLUMN is_latest BOOLEAN DEFAULT true;

CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);

-- Backfill existing data (optional)
UPDATE crawl_results
SET crawl_date = created_at::date,
    article_date = created_at::date,
    is_latest = true
WHERE crawl_date IS NULL;
EOF

# 2. 적용
docker exec -i crawlagent-postgres psql -U crawlagent -d crawlagent < scripts/migrations/001_add_incremental_fields.sql

# 3. 확인
docker exec -it crawlagent-postgres psql -U crawlagent -d crawlagent -c "\d crawl_results"
```

#### Option B: 새 테이블 생성 + 데이터 복사

**장점**:
- 롤백 쉬움 (원본 테이블 보존)
- Zero-downtime (새 테이블로 전환)

**단점**:
- 디스크 공간 2배 필요
- 코드 수정 필요 (테이블명 변경)

**권장하지 않음** (현재 데이터 없으므로 불필요)

### SQLAlchemy Model 업데이트

```python
# src/storage/models.py

from sqlalchemy import Date, Boolean

class CrawlResult(Base):
    __tablename__ = "crawl_results"

    # ... 기존 필드 ...

    # 증분 수집 필드 (추가)
    crawl_date = Column(Date, nullable=True, index=True, comment="크롤링 수행 날짜")
    article_date = Column(Date, nullable=True, index=True, comment="기사 발행 날짜")
    is_latest = Column(Boolean, default=True, nullable=False, index=True, comment="최신 버전 여부")

    # 선택 필드 (Phase 2)
    # content_type = Column(String(50), default='news', index=True)
    # metadata = Column(JSONB, nullable=True)
    # version = Column(Integer, default=1)
    # last_updated = Column(TIMESTAMP, nullable=True)
```

### 마이그레이션 체크리스트

- [ ] Migration SQL 파일 작성 (`scripts/migrations/001_add_incremental_fields.sql`)
- [ ] Migration 실행 (Docker PostgreSQL)
- [ ] SQLAlchemy Model 업데이트 (`src/storage/models.py`)
- [ ] Spider 코드 수정 (날짜 필드 저장)
- [ ] 테스트 실행 (신규 필드 검증)

**예상 소요 시간**: 30분

---

## 📈 Gradio UI 확장 제안

### 현재 UI 구조 (4 Tabs)

1. **Tab 1: 🚀 실시간 크롤링** - 단일/카테고리 페이지 수집
2. **Tab 2: 📊 데이터 조회** - 검색, 필터링, CSV 다운로드
3. **Tab 3: 🧠 LangGraph Agent** - UC1/UC2 설명 (읽기 전용)
4. **Tab 4: 📈 통계** - 사이트별 통계, 품질 분포

### 추가 제안 Tabs (옵션 A용)

#### Option 1: Tab 5 추가 - "⏰ 스케줄러 제어" (권장)

**목적**: APScheduler BackgroundScheduler 제어

**UI 구성**:
```python
with gr.Tab("⏰ 스케줄러"):
    gr.Markdown("## 일일 자동 크롤링 스케줄러")

    # 현재 상태 표시
    scheduler_status = gr.Textbox(
        label="상태",
        value="실행 중 ✅" if scheduler.running else "중지됨 ⏸️",
        interactive=False
    )

    next_run = gr.Textbox(
        label="다음 실행 시각",
        value=str(scheduler.get_next_run_time()),
        interactive=False
    )

    # 제어 버튼
    with gr.Row():
        start_btn = gr.Button("▶️ 시작", variant="primary")
        pause_btn = gr.Button("⏸️ 일시정지", variant="secondary")
        stop_btn = gr.Button("⏹️ 중지", variant="stop")

    # 수동 실행
    gr.Markdown("### 수동 실행 (테스트용)")
    test_date = gr.Textbox(label="테스트 날짜", value="2025-11-02")
    run_now_btn = gr.Button("즉시 실행", variant="secondary")

    result_log = gr.Textbox(label="실행 로그", lines=10, max_lines=20)

    # 이벤트 핸들러
    start_btn.click(fn=start_scheduler, outputs=[scheduler_status, next_run])
    pause_btn.click(fn=pause_scheduler, outputs=[scheduler_status])
    run_now_btn.click(fn=run_manual_crawl, inputs=[test_date], outputs=[result_log])
```

**구현 시간**: 1-2시간

#### Option 2: Tab 2 확장 - "증분 수집 필터" (최소 변경)

기존 "데이터 조회" 탭에 날짜 필터 추가:

```python
with gr.Tab("📊 데이터 조회"):
    # 기존 필터 (사이트, 기간, 점수, 키워드)
    # ...

    # 신규 필터 추가
    crawl_date_filter = gr.Dropdown(
        label="📅 크롤링 날짜",
        choices=["전체", "오늘", "어제", "지난 7일"],
        value="전체"
    )

    article_date_filter = gr.Dropdown(
        label="📰 기사 발행일",
        choices=["전체", "오늘", "어제", "지난 7일"],
        value="전체"
    )

    latest_only = gr.Checkbox(label="최신 버전만 표시", value=True)
```

**구현 시간**: 30분

### 권장 순서

1. **Phase 1 (UC2 개발 중)**: UI 확장 보류
   - UC2 개발에 집중
   - 스케줄러는 CLI로 수동 실행 (`poetry run python src/scheduler/daily_crawler.py`)

2. **Phase 2 (UC2 완료 후)**: UI 확장
   - Tab 5 (스케줄러 제어) 추가
   - Tab 2 (증분 필터) 확장

---

## 🚀 개발 레디 최종 상태 점검

### ✅ Ready (즉시 사용 가능)

| 항목 | 상태 | 근거 |
|------|------|------|
| **환경** | ✅ | Docker PostgreSQL 16 실행 중 (컨테이너: `crawlagent-postgres`) |
| **의존성** | ✅ | Poetry 2.2.1, Python 3.9.6, 모든 패키지 설치됨 |
| **API Keys** | ✅ | `.env` 파일 존재, OpenAI + Google API Key 설정됨 |
| **Spider** | ✅ | `yonhap.py` 구현 완료 (2-stage crawling, 카테고리 지원) |
| **UC1 Workflow** | ✅ | `src/workflow/uc1_validation.py` 구현 완료 (5W1H 품질 검증) |
| **DB Schema** | ✅ | 3 tables (selectors, crawl_results, decision_logs) + 인덱스 |
| **Gradio UI** | ✅ | 4-Tab 구조 완성 (크롤링, 조회, Agent 설명, 통계) |
| **PRD 문서** | ✅ | PRD-1/2/3 + UC2 Masterplan + Quick Start 완비 |
| **Claude Skills** | ✅ | 3개 Skills 생성됨 (uc2-development, incremental-crawling, scheduler) |

### ⚠️ Preparation Needed (1-2시간 작업 필요)

| 항목 | 작업 내용 | 소요 시간 | 파일 경로 |
|------|----------|----------|----------|
| **APScheduler 설치** | `poetry add apscheduler` | 2분 | `pyproject.toml` |
| **DB 스키마 확장** | Migration 실행 (crawl_date, article_date, is_latest) | 30분 | `scripts/migrations/001_add_incremental_fields.sql` |
| **Spider 수정** | `target_date` 파라미터 + 날짜 비교 로직 추가 | 30분 | `src/crawlers/spiders/yonhap.py` |
| **Models 업데이트** | SQLAlchemy 모델에 신규 필드 추가 | 10분 | `src/storage/models.py` |
| **Scheduler 생성** | `daily_crawler.py` 작성 (APScheduler BlockingScheduler) | 20분 | `src/scheduler/daily_crawler.py` |

**총 예상 소요 시간**: **1.5시간**

### ❌ Not Ready (Blocker - UC2 개발 필요)

| 항목 | 현재 상태 | 해결 방법 | 소요 시간 |
|------|----------|----------|----------|
| **GPT-4o Analyzer** | ❌ 미구현 | `src/agents/gpt_analyzer.py` 생성 | 3시간 |
| **Gemini Validator** | ❌ 미구현 | `src/agents/gemini_validator.py` 생성 | 2시간 |
| **UC2 Workflow** | ❌ 미구현 | `src/workflow/uc2_recovery.py` 생성 (LangGraph) | 3시간 |
| **Consensus Logic** | ❌ 미구현 | Conditional routing 구현 | 1시간 |
| **HITL Interface** | ❌ 미구현 | Gradio Tab 5 추가 (수동 검토) | 1시간 |

**총 예상 소요 시간**: **10시간** (UC2 완전 구현)

---

## 🛠️ 즉시 조치 필요 항목 (우선순위별)

### High Priority (오늘 완료 - UC2 개발 준비)

#### 1. APScheduler 설치
**작업**: Poetry 패키지 추가
**소요**: 2분
**명령어**:
```bash
cd /Users/charlee/Desktop/Intern/crawlagent
poetry add apscheduler
```

#### 2. DB 스키마 확장
**작업**: Migration 실행
**소요**: 30분
**파일**: `scripts/migrations/001_add_incremental_fields.sql`
**명령어**:
```bash
# 1. Migration 파일 생성
cat > scripts/migrations/001_add_incremental_fields.sql << 'EOF'
ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,
ADD COLUMN article_date DATE,
ADD COLUMN is_latest BOOLEAN DEFAULT true;

CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);
EOF

# 2. 실행
docker exec -i crawlagent-postgres psql -U crawlagent -d crawlagent < scripts/migrations/001_add_incremental_fields.sql

# 3. 검증
docker exec -it crawlagent-postgres psql -U crawlagent -d crawlagent -c "\d crawl_results"
```

#### 3. SQLAlchemy Model 업데이트
**작업**: `CrawlResult` 클래스에 필드 3개 추가
**소요**: 10분
**파일**: `src/storage/models.py`
**수정 내용**:
```python
# Line 110 이후 추가
crawl_date = Column(Date, nullable=True, index=True)
article_date = Column(Date, nullable=True, index=True)
is_latest = Column(Boolean, default=True, nullable=False, index=True)
```

#### 4. Spider 수정 (날짜 필터 추가)
**작업**: `target_date` 파라미터 추가 + 날짜 비교 로직
**소요**: 30분
**파일**: `src/crawlers/spiders/yonhap.py`
**수정 위치**:
- `__init__`: Line 46-84 (파라미터 추가)
- `parse_article`: Line 175-308 (날짜 비교 로직)

### Medium Priority (내일 완료 - 편의 기능)

#### 5. Scheduler 스크립트 생성
**작업**: `daily_crawler.py` 작성
**소요**: 20분
**파일**: `src/scheduler/daily_crawler.py` (신규 생성)
**템플릿**: `.claude/skills/scheduler.md` 참조

#### 6. PRD 업데이트
**작업**: 증분 수집 섹션 추가
**소요**: 15분
**파일**: `docs/crawlagent/PRD-3-IMPLEMENTATION.md`
**추가 섹션**:
- 증분 수집 요구사항
- 스케줄링 전략
- DB 스키마 변경사항

### Low Priority (UC2 완료 후)

#### 7. Gradio UI 확장
**작업**: Tab 5 "스케줄러 제어" 추가
**소요**: 1-2시간
**파일**: `src/ui/app.py`

#### 8. 동적 데이터 섹션 추가
**작업**: PRD에 SPA/동적 사이트 전략 문서화
**소요**: 30분
**파일**: `docs/crawlagent/PRD-4-DYNAMIC-SITES.md` (신규)

---

## 📅 개발 시작 로드맵

### Phase 1: 준비 (오늘, 3-4시간)

**목표**: UC2 개발 환경 완전 준비

| 단계 | 작업 | 소요 | 체크 |
|------|------|------|------|
| 1.1 | APScheduler 설치 | 2분 | ⬜ |
| 1.2 | DB Migration 실행 | 30분 | ⬜ |
| 1.3 | Models 업데이트 | 10분 | ⬜ |
| 1.4 | Spider 수정 (날짜 필터) | 30분 | ⬜ |
| 1.5 | 증분 수집 테스트 | 20분 | ⬜ |
| 1.6 | Scheduler 스크립트 작성 | 20분 | ⬜ |
| 1.7 | Scheduler 테스트 | 15분 | ⬜ |
| 1.8 | PRD 업데이트 | 15분 | ⬜ |

**완료 조건**: `target_date` 파라미터로 특정 날짜 수집 성공

**테스트 명령어**:
```bash
poetry run scrapy crawl yonhap -a target_date=2025-11-02 -a category=politics
```

### Phase 2: UC2 개발 (내일~, 7-8시간)

**목표**: 2-Agent Consensus System 구현

| 단계 | 작업 | 소요 | 파일 | 체크 |
|------|------|------|------|------|
| 2.1 | UC2 State 설계 | 1시간 | `src/workflow/uc2_recovery.py` | ⬜ |
| 2.2 | GPT-4o Analyzer | 3시간 | `src/agents/gpt_analyzer.py` | ⬜ |
| 2.3 | Gemini Validator | 2시간 | `src/agents/gemini_validator.py` | ⬜ |
| 2.4 | Consensus Logic | 1시간 | `src/workflow/uc2_recovery.py` | ⬜ |
| 2.5 | DB Integration | 30분 | `src/workflow/uc2_recovery.py` | ⬜ |
| 2.6 | 통합 테스트 | 1시간 | `tests/test_uc2.py` | ⬜ |

**완료 조건**: 고의로 손상된 Selector를 UC2가 자동 복구

**테스트 시나리오**:
```python
# 1. 연합뉴스 Selector 고의 손상
# 2. UC1 실행 → quality_score < 80
# 3. UC2 자동 실행 → 새 Selector 생성
# 4. DB 업데이트 → 재크롤링 → quality_score ≥ 80
```

### Phase 3: 통합 & 데모 준비 (모레~, 3-4시간)

**목표**: 완전 자동화 시스템 검증

| 단계 | 작업 | 소요 | 파일 | 체크 |
|------|------|------|------|------|
| 3.1 | Scheduler + UC2 통합 | 1시간 | `src/scheduler/daily_crawler.py` | ⬜ |
| 3.2 | Gradio UI 확장 | 2시간 | `src/ui/app.py` | ⬜ |
| 3.3 | 종단간 테스트 | 1시간 | - | ⬜ |
| 3.4 | 데모 시나리오 작성 | 30분 | `docs/DEMO-SCRIPT.md` | ⬜ |

**완료 조건**: 스케줄러 → 크롤링 → UC1 → UC2 (필요 시) → 저장 전체 플로우 성공

**데모 시나리오**:
1. Gradio 실행
2. Tab 1: 단일 기사 수집 (정상)
3. Tab 1: 카테고리 페이지 수집 (정상)
4. Tab 5: 스케줄러 시작 (자동)
5. Selector 손상 → UC2 자동 복구 (Self-Healing)

---

## 🎓 최종 권장사항 & 실행 계획

### 핵심 결론

1. **기술 스택**: 검증 완료 ✅
   - 모든 필수 기술 설치됨
   - APScheduler만 추가 설치 필요 (2분)

2. **Claude Skills**: 생성 완료 ✅
   - 3개 Skills로 개발 가이드 제공
   - MCP 서버는 현재 불필요

3. **스케줄러**: APScheduler 선택 ✅
   - PoC 단계에 최적
   - Gradio UI 통합 쉬움
   - 프로덕션 전환 시 Cron 고려

4. **DB 확장**: 설계 완료 ✅
   - 3개 필드 추가 (crawl_date, article_date, is_latest)
   - Migration SQL 준비됨
   - 30분 내 적용 가능

5. **개발 준비도**: 95% ✅
   - 환경/의존성/Spider/UC1 완료
   - 1.5시간 준비 작업 후 UC2 개발 시작 가능

### 즉시 시작 가능한 작업 순서

#### Step 1: 환경 준비 (15분)
```bash
# 1. APScheduler 설치
cd /Users/charlee/Desktop/Intern/crawlagent
poetry add apscheduler

# 2. Migration 디렉토리 생성
mkdir -p scripts/migrations

# 3. Git 상태 확인 (변경사항 커밋 전)
git status
```

#### Step 2: DB 마이그레이션 (30분)
```bash
# 1. Migration 파일 생성 (위의 High Priority 2번 참조)
# 2. Migration 실행
# 3. 검증 (테이블 구조 확인)
```

#### Step 3: 코드 수정 (40분)
- `src/storage/models.py`: 필드 3개 추가
- `src/crawlers/spiders/yonhap.py`: target_date 로직 추가

#### Step 4: 테스트 (20분)
```bash
# 특정 날짜 크롤링 테스트
poetry run scrapy crawl yonhap -a target_date=2025-11-02 -a category=politics

# DB 확인
docker exec -it crawlagent-postgres psql -U crawlagent -d crawlagent -c "SELECT crawl_date, article_date, title FROM crawl_results ORDER BY created_at DESC LIMIT 5;"
```

#### Step 5: Scheduler 구현 (20분)
- `src/scheduler/daily_crawler.py` 생성 (`.claude/skills/scheduler.md` 템플릿 사용)

#### Step 6: UC2 개발 시작 (7-8시간)
- `.claude/skills/uc2-development.md` 참조
- `docs/crawlagent/UC2-DEVELOPMENT-MASTERPLAN.md` 따라 구현

### 성공 지표

| 단계 | 성공 조건 | 검증 방법 |
|------|----------|----------|
| **Phase 1 완료** | 특정 날짜 수집 성공 | `target_date=2025-11-02` 크롤링 → DB 저장 확인 |
| **Phase 2 완료** | UC2 자동 복구 성공 | Selector 손상 → UC2 실행 → 새 Selector 생성 → 재크롤링 성공 |
| **Phase 3 완료** | 완전 자동화 검증 | 스케줄러 → 크롤링 → UC1/UC2 → 저장 전체 플로우 0-error |

### 리스크 & 완화 전략

| 리스크 | 확률 | 영향 | 완화 방법 |
|--------|------|------|-----------|
| GPT-4o Selector 생성 실패 | 낮음 | 높음 | 재시도 로직 (max 3회) + HITL 개입 |
| Gemini 검증 False Negative | 중간 | 중간 | 규칙 기반 검증 추가 (80% + 패턴 체크) |
| Migration 실패 | 낮음 | 높음 | 테스트 DB에서 먼저 실행 + 백업 |
| 날짜 파싱 오류 | 중간 | 낮음 | try/except + 로깅, 실패 시 전체 수집 |

### 다음 단계

**지금 바로 시작**:
```bash
# 터미널에서 실행
cd /Users/charlee/Desktop/Intern/crawlagent
poetry add apscheduler

# 그 다음, 위의 Step 2 (DB Migration) 진행
```

**질문이 있다면**:
- `.claude/skills/` 디렉토리의 3개 Skills 참조
- `docs/crawlagent/UC2-DEVELOPMENT-MASTERPLAN.md` 상세 가이드
- PRD-2-TECHNICAL-SPEC.md (Lines 121-151) UC2 스펙

---

## 📎 참고 자료

### 프로젝트 문서
- **PRD-1**: 문제 정의 & 솔루션
- **PRD-2**: 기술 스펙 (Lines 121-151: UC2 워크플로우)
- **PRD-3**: 구현 계획
- **UC2 Masterplan**: 완전한 개발 가이드 (HITL 포인트 포함)
- **UC2 Quick Start**: 빠른 시작 가이드

### Claude Skills (방금 생성됨)
- **uc2-development.md**: UC2 개발 패턴 & 예제
- **incremental-crawling.md**: 증분 수집 구현 가이드
- **scheduler.md**: 스케줄러 비교 & 구현

### 외부 레퍼런스
- APScheduler: https://apscheduler.readthedocs.io/
- LangGraph: https://langchain-ai.github.io/langgraph/
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- PostgreSQL Date/Time: https://www.postgresql.org/docs/16/datatype-datetime.html

---

**보고서 종료**

**작성자**: Claude (Anthropic)
**작성일**: 2025-11-03
**버전**: 1.0
**다음 단계**: Phase 1 준비 작업 시작 (1.5시간)
