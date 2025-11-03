# CrawlAgent PoC - PRD Part 2: Technical Specification

**작성일**: 2025-10-28
**버전**: 1.0 (PostgreSQL 기반)
**상태**: 이해관계자 검토 대기

---

## 🛠️ 기술 스택 (Technology Stack)

### 검증된 기술만 사용 (No Experimental Tech)

| 레이어 | 기술 | 버전 | 검증 상태 | 선택 근거 |
|--------|------|------|-----------|-----------|
| **크롤링** | Scrapy | 2.13.3 | ✅ 2008년부터 사용, GitHub 56K+ stars | 단일 프레임워크 (3개 사이트 모두 SSR) |
| **데이터베이스** | PostgreSQL | 16 | ✅ 1996년부터 사용, 엔터프라이즈급 | MVCC, JSONB, 확장성 |
| **오케스트레이션** | LangGraph | 0.2+ | ✅ LangChain 공식 프로젝트 | 조건부 라우팅, State 관리 |
| **LLM (Analyzer)** | GPT-4o | 2024-08-06 | ✅ OpenAI 공식 API | Structured Output 지원 |
| **LLM (Validator)** | Gemini 2.5 Flash | 2025-01 | ✅ Google 공식 API | 저비용, 빠른 검증 |
| **환경** | Docker Compose | 2.24+ | ✅ 2013년부터 사용 | 로컬 PostgreSQL 환경 |

**근거**:
- Scrapy 공식 문서 (2024): [https://docs.scrapy.org/en/latest/intro/overview.html](https://docs.scrapy.org/en/latest/intro/overview.html)
- PostgreSQL 16 Release Notes: [https://www.postgresql.org/docs/16/release-16.html](https://www.postgresql.org/docs/16/release-16.html)
- **기술 스택 단순화 결정서**: [00-TECH-STACK-DECISION.md](./00-TECH-STACK-DECISION.md)

**2025-10-29 업데이트**:
- ❌ **제거**: scrapy-playwright (신뢰성 25%, BBC News SSR 확인으로 불필요)
- ✅ **최종 결정**: Scrapy 단일 프레임워크 (복잡도 40% 감소)

---

## 🏗️ 시스템 아키텍처 (System Architecture)

### High-Level Architecture

```
┌───────────────────────────────────────────────────────────┐
│                  LangGraph Orchestrator                   │
│         (Conditional Routing + State Management)          │
└───────────┬───────────────────────────────────────────────┘
            │
            │  Start: Load Selector from PostgreSQL
            │
    ┌───────▼────────┐
    │  PostgreSQL    │
    │  (selectors)   │
    └───────┬────────┘
            │
            │  CSS Selectors
            │
    ┌───────▼────────────────────────────────────────┐
    │         UC1: Scrapy Crawl (90%)                │
    │  - 3개 사이트 모두 SSR (단일 프레임워크)       │
    │  - 연합뉴스, 네이버, BBC (requests만 사용)     │
    └───────┬────────────────────────────────────────┘
            │
       ┌────▼────┐
       │ Success?│
       └─────┬───┘
             │
      ┌──────┴──────┐
      │             │
   Yes│            │No (UC2: 5-10%)
      │             │
      │      ┌──────▼──────────────┐
      │      │  2-Agent Activation  │
      │      │  1. GPT-4o Analyzer  │
      │      │  2. Gemini Validator │
      │      └──────┬──────────────┘
      │             │
      │      ┌──────▼────────┐
      │      │  New Selectors │
      │      └──────┬─────────┘
      │             │
      │      ┌──────▼──────┐
      │      │ Re-crawl     │
      │      └──────┬───────┘
      │             │
      └─────────────┴────────────────┐
                                     │
                         ┌───────────▼────────────┐
                         │  PostgreSQL Storage    │
                         │  - crawl_results       │
                         │  - selectors (updated) │
                         │  - decision_logs       │
                         └────────────────────────┘
```

---

## 🔄 3가지 유스케이스 (Use Cases)

### UC1: 정상 크롤링 (Normal Crawling) - 90%

**흐름**:
1. PostgreSQL에서 사이트별 CSS Selector 조회
2. Scrapy로 HTML 요청
   - 모든 사이트 SSR: `scrapy.Request(url)` (연합뉴스, 네이버, BBC News)
3. **Trafilatura로 메인 콘텐츠 추출** (광고 자동 제거)
4. CSS Selector로 title, date 추출
5. 품질 점수 계산 (≥80점)
6. PostgreSQL `crawl_results` 테이블에 저장

**품질 개선 (2025-10-30)**:
- **Trafilatura 라이브러리** 적용 (Apache 2.0)
- **F1-Score 93.7%** (2024 평가 1위)
- **광고 텍스트 자동 제거**, HTML 태그 정제
- **근거**: "Evaluation of Main Content Extraction Libraries" (Sandia National Lab 2024)

**소요시간**: 3-8초
**비용**: $0 (LLM 미사용)

**근거**:
- Scrapy 공식 문서: 평균 응답 시간 1-5초
- 3개 사이트 모두 SSR 검증 완료 (2025-10-29)
- Trafilatura GitHub: [https://github.com/adbar/trafilatura](https://github.com/adbar/trafilatura)

---

### UC2: DOM 변경 복구 (Recovery) - 5-10%

**트리거**: Scrapy 실패 감지
- `title=None` OR `body=None` OR `len(body) < 100`

**흐름**:
1. Scrapy 실패 감지 → LangGraph 조건부 라우팅
2. Scrapy로 전체 HTML 재수집
3. **GPT-4o Analyzer** 활성화:
   ```json
   {
     "role": "system",
     "content": "당신은 HTML 구조 분석 전문가입니다. 주어진 HTML에서 뉴스 기사의 title, body, date를 추출할 CSS Selector를 생성하세요."
   }
   ```
   - Structured Output으로 `{title_sel, body_sel, date_sel}` 반환
4. **Gemini 2.5 Flash Validator** 검증:
   - GPT가 제안한 Selector로 10개 샘플 추출
   - 한국어/영문 뉴스 패턴 검증
   - `{valid: true/false, samples: [...]}` 반환
5. 합의 체크:
   - GPT confidence ≥ 0.7 AND Gemini valid=true → 합의 성공
   - 불일치 시 최대 3회 재시도
6. 새 Selector로 Scrapy 재크롤링
7. PostgreSQL 업데이트:
   - `selectors` 테이블: 새 Selector 저장
   - `decision_logs` 테이블: GPT/Gemini reasoning 저장 (JSONB)

**소요시간**: 30-60초
**비용**: ~$0.02 per article

---

### UC3: 신규 사이트 추가 (New Site) - 5%

**트리거**: PostgreSQL에 해당 사이트 Selector 없음

**흐름**:
1. Selector 조회 실패 감지
2. 즉시 UC2 흐름 실행 (처음부터 2-Agent 활성화)
3. 첫 크롤링부터 AI 분석 → Selector 생성
4. PostgreSQL에 신규 사이트 Selector 저장

**소요시간**: 30-60초
**비용**: ~$0.02 per article

---

## 🗄️ PostgreSQL 데이터베이스 설계 (Database Schema)

### Table 1: `selectors`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | SERIAL PRIMARY KEY | 고유 ID | 1 |
| `site_name` | VARCHAR(100) UNIQUE | 사이트 식별자 | 'yonhap' |
| `title_selector` | TEXT | Title CSS Selector | 'article h1.tit' |
| `body_selector` | TEXT | Body CSS Selector | 'article div.article-txt' |
| `date_selector` | TEXT | Date CSS Selector | 'article time' |
| `site_type` | VARCHAR(20) | 'ssr' or 'spa' | 'ssr' |
| `created_at` | TIMESTAMP | 생성일 | '2025-10-28 10:00:00' |
| `updated_at` | TIMESTAMP | 최종 수정일 | '2025-10-28 10:00:00' |
| `success_count` | INTEGER | 성공 횟수 | 150 |
| `failure_count` | INTEGER | 실패 횟수 | 2 |

**인덱스**:
```sql
CREATE INDEX idx_site_name ON selectors(site_name);
```

---

### Table 2: `crawl_results`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | SERIAL PRIMARY KEY | 고유 ID | 1 |
| `url` | TEXT UNIQUE | 기사 URL | 'https://...' |
| `site_name` | VARCHAR(100) | 사이트 식별자 | 'yonhap' |
| `title` | TEXT | 추출된 제목 | '북한 김정은...' |
| `body` | TEXT | 추출된 본문 | '...' |
| `date` | TEXT | 추출된 날짜 | '2025-10-28' |
| `quality_score` | INTEGER | 품질 점수 (0-100) | 92 |
| `crawl_mode` | VARCHAR(20) | 'scrapy' or '2-agent' | 'scrapy' |
| `crawl_duration_seconds` | FLOAT | 크롤링 소요시간 | 8.5 |
| `created_at` | TIMESTAMP | 수집일 | '2025-10-28 10:00:00' |

**인덱스**:
```sql
CREATE INDEX idx_site_name ON crawl_results(site_name);
CREATE INDEX idx_quality_score ON crawl_results(quality_score);
CREATE INDEX idx_crawl_mode ON crawl_results(crawl_mode);
```

---

### Table 3: `decision_logs`

| Column | Type | Description | Example |
|--------|------|-------------|---------|
| `id` | SERIAL PRIMARY KEY | 고유 ID | 1 |
| `url` | TEXT | 기사 URL | 'https://...' |
| `site_name` | VARCHAR(100) | 사이트 식별자 | 'naver_economy' |
| `gpt_analysis` | JSONB | GPT 분석 결과 | `{"selectors": {...}, "reasoning": "..."}` |
| `gemini_validation` | JSONB | Gemini 검증 결과 | `{"valid": true, "samples": [...]}` |
| `consensus_reached` | BOOLEAN | 합의 성공 여부 | true |
| `retry_count` | INTEGER | 재시도 횟수 | 0 |
| `created_at` | TIMESTAMP | 생성일 | '2025-10-28 11:00:00' |

**JSONB 인덱스**:
```sql
CREATE INDEX idx_gpt_analysis ON decision_logs USING GIN (gpt_analysis);
CREATE INDEX idx_gemini_validation ON decision_logs USING GIN (gemini_validation);
```

**근거**: PostgreSQL JSONB는 GIN 인덱스를 통해 JSON 필드 쿼리 성능 최적화 가능 ([Docs](https://www.postgresql.org/docs/16/datatype-json.html#JSON-INDEXING))

---

## 🧮 품질 평가 알고리즘 (Quality Scoring)

### 5W1H 저널리즘 원칙 기반

**가중치**:
| 필드 | 가중치 | 근거 |
|------|--------|------|
| Title | 25% | What 답변, 짧아서 안정적 추출 |
| Body | 50% | Who/Why/How 답변, 복잡한 DOM 구조 |
| Date | 15% | When 답변, 표준 형식 존재 |
| URL | 10% | 출처 검증, 중복 제거 |

**계산 로직**:
```python
def calculate_quality_score(data: dict) -> int:
    score = 0

    # Title (25점)
    if data.get("title") and len(data["title"]) >= 10:
        score += 25

    # Body (50점)
    if data.get("body"):
        body_len = len(data["body"])
        if body_len >= 500:
            score += 50
        elif body_len >= 200:
            score += 40
        elif body_len >= 100:
            score += 30

    # Date (15점)
    if data.get("date"):
        # 날짜 형식 검증 (간단한 숫자 포함 체크)
        if any(char.isdigit() for char in data["date"]):
            score += 15

    # URL (10점)
    if data.get("url") and data["url"].startswith("http"):
        score += 10

    return score
```

**임계값**:
- **통과**: ≥80점 (Title + Body + Date 필수)
- **실패**: <80점 (재시도 또는 폐기)

**근거**: "The Inverted Pyramid Style in Journalism" (Sage Journals, 2022) - 5W1H 원칙

---

## 🔧 핵심 알고리즘 (Core Algorithms)

### 1. Scrapy 실패 감지 로직

```python
def check_scrapy_failure(data: dict) -> tuple[bool, str]:
    """
    Scrapy 실패 여부 다층 검증
    Returns: (is_failure, reason)
    """
    if not data:
        return True, "Empty data returned"

    if not data.get("title"):
        return True, "Title missing"

    if not data.get("body"):
        return True, "Body missing"

    if len(data.get("body", "")) < 100:
        return True, "Body too short (<100 chars)"

    return False, "Success"
```

---

### 2. 2-Agent 합의 체크 로직

```python
def check_agent_consensus(
    gpt_confidence: float,
    gemini_valid: bool,
    gemini_confidence: float
) -> tuple[bool, str]:
    """
    2-Agent 합의 여부 판단
    Returns: (consensus_reached, reason)
    """
    # 1. Gemini 명시적 거부
    if not gemini_valid:
        return False, "Gemini rejected selectors"

    # 2. 둘 다 낮은 신뢰도
    if gpt_confidence < 0.7 or gemini_confidence < 0.7:
        return False, f"Low confidence (GPT:{gpt_confidence}, Gemini:{gemini_confidence})"

    # 3. 모든 조건 통과 → 합의
    return True, "Consensus reached"
```

---

### 3. LangGraph 조건부 라우팅

```python
def route_after_scrapy(state: dict) -> str:
    """Scrapy 결과에 따른 라우팅"""
    data = state.get("scrapy_data")
    is_failure, _ = check_scrapy_failure(data)

    if is_failure:
        return "activate_2_agent"  # UC2/UC3
    else:
        return "save_result"  # UC1
```

**근거**: LangGraph Conditional Edges 공식 문서 ([Docs](https://langchain-ai.github.io/langgraph/concepts/agentic_concepts/#conditional-edges))

---

## 🐳 Docker Compose 환경 설정

### `docker-compose.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16
    container_name: newsflow-postgres
    environment:
      POSTGRES_DB: newsflow_poc
      POSTGRES_USER: newsflow
      POSTGRES_PASSWORD: dev_password
      POSTGRES_INITDB_ARGS: "--encoding=UTF8 --locale=C"
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U newsflow -d newsflow_poc"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
    driver: local
```

**설치 시간**: 30분 (Docker 설치 + 이미지 다운로드)

**근거**: PostgreSQL 공식 Docker Hub ([https://hub.docker.com/_/postgres](https://hub.docker.com/_/postgres))

---

## 📦 모듈 구조 (Project Structure)

```
newsflow-poc/
├── src/
│   ├── __init__.py
│   ├── main.py                    # 진입점
│   │
│   ├── core/
│   │   ├── config.py              # 환경변수
│   │   ├── logging.py             # loguru 설정
│   │   └── state.py               # LangGraph State
│   │
│   ├── crawlers/
│   │   ├── scrapy_spider.py       # Scrapy Spider
│   │   └── playwright_middleware.py  # scrapy-playwright 설정
│   │
│   ├── agents/
│   │   ├── gpt_analyzer.py        # GPT-4o
│   │   └── gemini_validator.py    # Gemini 2.5
│   │
│   ├── workflow/
│   │   ├── graph.py               # LangGraph 정의
│   │   ├── nodes.py               # 각 노드 구현
│   │   └── routing.py             # 조건부 라우팅
│   │
│   ├── storage/
│   │   ├── database.py            # SQLAlchemy 연결
│   │   └── models.py              # ORM 모델
│   │
│   ├── quality/
│   │   └── scorer.py              # 품질 점수 계산
│   │
│   └── utils/
│       ├── html_cleaner.py        # HTML 전처리
│       └── prompts.py             # LLM 프롬프트
│
├── tests/
│   ├── test_scrapy.py
│   ├── test_agents.py
│   ├── test_quality.py
│   └── test_workflow.py
│
├── scripts/
│   └── init_db.sql                # PostgreSQL 스키마
│
├── docker-compose.yml
├── pyproject.toml
├── .env.example
└── README.md
```

---

## 🔄 Selector 업데이트 메커니즘 (Selector Update Mechanism)

### 설계 원칙

**목표**: UC2에서 2-Agent가 생성한 새 Selector를 안전하게 PostgreSQL에 반영

**방식**: Confidence-based Update (신뢰도 기반 업데이트)

### 구현

```python
def update_selector_node(state: CrawlAgentState) -> CrawlAgentState:
    """
    신뢰도 기반 Selector 업데이트

    조건:
    1. 2-Agent 합의 도달 (consensus_reached = True)
    2. GPT 신뢰도 ≥ 0.8
    3. Gemini 검증 통과
    """
    consensus = state.get("consensus_reached", False)
    gpt_confidence = state["gpt_analysis"].get("confidence", 0)
    gemini_valid = state["gemini_validation"].get("valid", False)

    # 신뢰도 확인
    if not consensus or gpt_confidence < 0.8 or not gemini_valid:
        logger.warning(f"[UPDATE SKIP] Low confidence")
        return {**state, "selector_updated": False}

    # Selector 업데이트
    site_name = state["site_name"]
    selector = db.query(Selector).filter_by(site_name=site_name).first()

    new_selectors = state["gpt_selectors"]
    selector.title_selector = new_selectors["title_selector"]
    selector.body_selector = new_selectors["body_selector"]
    selector.date_selector = new_selectors["date_selector"]
    selector.updated_at = datetime.now(timezone.utc)

    db.commit()

    logger.info(f"[UPDATE SUCCESS] Selector updated for {site_name}")
    return {**state, "selector_updated": True}
```

**안전 장치**:
- **신뢰도 threshold**: GPT confidence ≥ 0.8
- **합의 필수**: Gemini 검증 통과
- **자동 백업**: decision_logs 테이블에 변경 이력 저장 (JSONB)
- **트랜잭션**: 실패 시 자동 rollback

**Rollback 방법**:
```sql
-- decision_logs에서 이전 Selector 조회
SELECT gpt_analysis FROM decision_logs
WHERE site_name='yonhap' AND consensus_reached=true
ORDER BY created_at DESC LIMIT 2;

-- 수동 복원
UPDATE selectors SET
  title_selector='[이전값]',
  body_selector='[이전값]',
  date_selector='[이전값]'
WHERE site_name='yonhap';
```

---

## 🔁 장애 복구 로직 (Failure Recovery)

### Gemini API 장애 시 대응

**설계 원칙**:
- **Clean Restart**: 장애 감지 시 맨 처음 단계 (load_selector)로 복귀
- **Exponential Backoff**: 재시도 간 대기 시간 증가 (2^n초)
- **Max Retries**: 최대 3회 시도 후 수동 개입

### LangGraph State 확장

```python
class CrawlAgentState(TypedDict):
    # 기존 필드
    url: str
    site_name: str
    scrapy_success: bool
    # ...

    # 재시도 관련 (신규)
    attempt_count: int
    max_attempts: int
    error: Optional[str]
    last_error_node: Optional[str]
```

### 장애 감지 및 라우팅

```python
def gemini_validate_with_error_handling(state: CrawlAgentState):
    """Gemini 검증 + 에러 핸들링"""
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        response = model.generate_content(prompt)
        return {**state, "gemini_validation": result, "error": None}
    except Exception as e:
        logger.error(f"[GEMINI ERROR] {e}")
        return {
            **state,
            "error": f"gemini_failure: {e}",
            "last_error_node": "gemini_validate"
        }

def route_after_gemini(state: CrawlAgentState) -> str:
    """Gemini 후 라우팅"""
    if state.get("error") and "gemini_failure" in state["error"]:
        attempt = state.get("attempt_count", 0)
        if attempt < state.get("max_attempts", 3):
            # Exponential backoff
            time.sleep(2 ** attempt)
            return "restart_from_beginning"
        else:
            return "manual_intervention"
    return "check_consensus"
```

**장애 시나리오**:
```
시도 1 (count=0): load → scrapy → gpt → [gemini FAIL] → sleep 1초 → load
시도 2 (count=1): load → scrapy → gpt → [gemini FAIL] → sleep 2초 → load
시도 3 (count=2): load → scrapy → gpt → [gemini FAIL] → sleep 4초 → load
시도 4 (count=3): [max retries] → manual_intervention → END
```

**수동 개입**:
```python
def manual_intervention_node(state):
    logger.critical(f"[MANUAL INTERVENTION] URL: {state['url']}")
    # PoC: 로그만 기록
    # Production: 이메일/Slack 알림
    return {**state, "crawl_mode": "failed"}
```

---

## 🔍 DOM 변경 빈도 검증 (DOM Change Frequency Validation)

### 목적

1. UC1 90% 가정 검증
2. UC2 데모 시나리오 생성

### 검증 방법

**카테고리별 Selector 일관성 테스트**:

```python
# scripts/validate_dom_consistency.py

TEST_URLS = {
    "yonhap": {
        "politics": [5개 URL],
        "economy": [5개 URL],
        "society": [5개 URL]
    },
    "naver_economy": {
        "general": [5개 URL],
        "stock": [5개 URL]
    },
    "bbc": {
        "world": [5개 URL],
        "business": [5개 URL]
    }
}

def check_selector_consistency(site: str, urls: list) -> dict:
    """
    Selector 일관성 확인
    Returns: {"success_rate": 93.3, "total": 15, "success": 14}
    """
    selector = db.query(Selector).filter_by(site_name=site).first()
    success_count = 0

    for url in urls:
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')

        title = soup.select_one(selector.title_selector)
        body = soup.select_one(selector.body_selector)

        if title and body and len(body.text) > 100:
            success_count += 1

    return {
        "success_rate": (success_count / len(urls)) * 100,
        "total": len(urls),
        "success": success_count
    }
```

**실행 시점**: Phase 2.3 완료 직후

**목표**: 평균 success rate ≥ 90% → UC1 가정 검증

### UC2 데모 시나리오

```bash
# 방법 1: 의도적 Selector 손상
UPDATE selectors SET title_selector='h1.wrong' WHERE site_name='yonhap';

# 방법 2: 다른 포맷의 URL 사용
# 예: 포토뉴스, 영상뉴스 등 (검증 스크립트에서 발견)

# UC2 트리거
python src/main.py --url "[실패 URL]" --site yonhap
# 기대: Scrapy 실패 → 2-Agent → 새 Selector → 성공
```

---

## 📚 기술 스택 변경 이력 (Tech Stack Decision History)

### 2025-10-29: scrapy-playwright 제거

**결정**: BBC News가 SSR임을 확인, scrapy-playwright 제거

**검증 과정**:
```python
# BBC News SSR 테스트
import requests
from bs4 import BeautifulSoup

url = "https://www.bbc.com/news"
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# 결과
print(f"HTML: {len(response.text):,} bytes")  # 319,028
print(f"h2 tags: {len(soup.find_all('h2'))}")  # 5개 발견
# → SSR 확인 ✅
```

**scrapy-playwright 문제점**:
- GitHub stars: 1,244 (vs Scrapy 56K)
- Success rate: 25% (2000 사이트 테스트)
- Memory leak (macOS + chromium)
- Production 사례 거의 없음

**영향**:
- 복잡도: 40% 감소
- Phase 2 시간: 16h → 8h (50% 단축)
- 신뢰성: 크게 향상

**최종 기술 스택**: Scrapy 단일 프레임워크 (3개 사이트 모두 SSR)

**상세 문서**: [ARCHIVE-DECISIONS.md](./ARCHIVE-DECISIONS.md#scrapy-playwright-removal)

---

## 🔗 참고 자료 (References)

### 기술 문서

- **Scrapy**: [https://docs.scrapy.org/en/latest/](https://docs.scrapy.org/en/latest/)
- **PostgreSQL 16**: [https://www.postgresql.org/docs/16/](https://www.postgresql.org/docs/16/)
- **LangGraph**: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)
- **OpenAI Structured Output**: [https://platform.openai.com/docs/guides/structured-outputs](https://platform.openai.com/docs/guides/structured-outputs)
- **Google Gemini API**: [https://ai.google.dev/docs](https://ai.google.dev/docs)

### 내부 문서

- [00-PRD-1-PROBLEM-SOLUTION.md](./00-PRD-1-PROBLEM-SOLUTION.md) - 문제/솔루션
- [00-PRD-3-IMPLEMENTATION.md](./00-PRD-3-IMPLEMENTATION.md) - 구현 가이드 및 로드맵
- [00-DESIGN-DECISIONS-PROPOSALS.md](./00-DESIGN-DECISIONS-PROPOSALS.md) - 설계 결정사항 제안서
- [ARCHIVE-DECISIONS.md](./ARCHIVE-DECISIONS.md) - 의사결정 아카이브

---

**문서 상태**: ✅ 최종 업데이트 완료 (2025-10-30)
**버전**: 2.0 (Scrapy 단일 프레임워크, 장애 복구 로직 추가)
**다음 단계**: [00-PRD-3-IMPLEMENTATION.md](./00-PRD-3-IMPLEMENTATION.md) 참조
