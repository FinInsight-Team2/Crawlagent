# CrawlAgent PoC - PRD Part 3: Development Roadmap

**작성일**: 2025-10-28
**버전**: 1.0 (PostgreSQL 기반)
**상태**: 이해관계자 검토 대기
**총 기간**: 10일 (2주)

---

## 📅 개발 일정 (Development Schedule)

### Week 1: Infrastructure & UC1 (Day 1-5)

| Day | Phase | 작업 내용 | 산출물 | 소요 시간 |
|-----|-------|----------|--------|----------|
| **1** | Phase 0 | 환경 설정 | PostgreSQL (Docker), Python 3.11 venv, 의존성 설치 | 4h |
| **2** | Phase 1 | PostgreSQL 스키마 | 3개 테이블 생성, SQLAlchemy 모델 정의 | 6h |
| **3** | Phase 2.1 | Scrapy 초기화 | 3개 Spider 골격 (연합뉴스, 네이버, BBC) | 6h |
| **4** | Phase 2.2 | Scrapy 구현 | SSR Spider 완성 (연합뉴스, 네이버) | 6h |
| **5** | Phase 2.3 | scrapy-playwright | BBC News SPA Spider 완성, UC1 검증 | 6h |

**Week 1 목표**: UC1 (정상 크롤링) 작동 확인 - 3-Site 각 5개 기사 수집

---

### Week 2: 2-Agent System & Integration (Day 6-10)

| Day | Phase | 작업 내용 | 산출물 | 소요 시간 |
|-----|-------|----------|--------|----------|
| **6** | Phase 3 | LangGraph Workflow | UC1 경로 구현, Scrapy 실패 감지 로직 | 6h |
| **7** | Phase 4.1 | GPT Analyzer | GPT-4o Structured Output, CSS Selector 생성 | 6h |
| **8** | Phase 4.2 | Gemini Validator | Gemini 2.5 독립 검증, 합의 체크 로직 | 6h |
| **9** | Phase 5 | 통합 테스트 | UC1/UC2/UC3 각 10회 테스트, 품질 검증 | 6h |
| **10** | Phase 6 | 문서화 & 발표 | README, 발표 자료, 데모 준비 | 6h |

**Week 2 목표**: UC2/UC3 작동 확인 - 30개 기사 ≥90% 품질 달성

---

## ✅ Phase 0: 환경 설정 (Day 1)

### Task 0.1: Docker Compose로 PostgreSQL 시작

- [x] **0.1.1**: `docker-compose.yml` 파일 확인
- [x] **0.1.2**: PostgreSQL 시작
  ```bash
  cd newsflow-poc
  docker-compose up -d
  ```
- [x] **0.1.3**: 연결 테스트
  ```bash
  psql -h localhost -U newsflow -d newsflow_poc -c "SELECT version();"
  ```

**예상 시간**: 30분
**완료 기준**: PostgreSQL 16 버전 출력 확인

---

### Task 0.2: Python 환경 설정

- [x] **0.2.1**: Python 3.11 venv 생성
  ```bash
  python -m venv .venv
  .venv\Scripts\activate  # Windows
  ```
- [x] **0.2.2**: 의존성 설치
  ```bash
  pip install -e .  # pyproject.toml 기반 자동 설치
  ```

**예상 시간**: 15분
**완료 기준**: `scrapy version` 명령 성공

---

### Task 0.3: 환경변수 설정

- [x] **0.3.1**: `.env` 파일 생성
  ```bash
  OPENAI_API_KEY=sk-...
  GOOGLE_API_KEY=...
  DATABASE_URL=postgresql://newsflow:dev_password@localhost:5432/newsflow_poc
  LOG_LEVEL=INFO
  ```

**예상 시간**: 10분
**완료 기준**: API 키 입력 완료

---

## ✅ Phase 1: PostgreSQL 스키마 (Day 2)

### Task 1.1: 데이터베이스 스키마 생성

- [x] **1.1.1**: `scripts/init_db.sql` 작성
  ```sql
  CREATE TABLE IF NOT EXISTS selectors (
      id SERIAL PRIMARY KEY,
      site_name VARCHAR(100) UNIQUE NOT NULL,
      title_selector TEXT NOT NULL,
      body_selector TEXT NOT NULL,
      date_selector TEXT NOT NULL,
      site_type VARCHAR(20) DEFAULT 'ssr',
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
      success_count INTEGER DEFAULT 0,
      failure_count INTEGER DEFAULT 0
  );

  CREATE TABLE IF NOT EXISTS crawl_results (
      id SERIAL PRIMARY KEY,
      url TEXT UNIQUE NOT NULL,
      site_name VARCHAR(100) NOT NULL,
      title TEXT,
      body TEXT,
      date TEXT,
      quality_score INTEGER,
      crawl_mode VARCHAR(20),
      crawl_duration_seconds FLOAT,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS decision_logs (
      id SERIAL PRIMARY KEY,
      url TEXT NOT NULL,
      site_name VARCHAR(100) NOT NULL,
      gpt_analysis JSONB,
      gemini_validation JSONB,
      consensus_reached BOOLEAN,
      retry_count INTEGER DEFAULT 0,
      created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
  );

  CREATE INDEX idx_selectors_site_name ON selectors(site_name);
  CREATE INDEX idx_crawl_results_site_name ON crawl_results(site_name);
  CREATE INDEX idx_decision_logs_url ON decision_logs(url);
  ```
- [x] **1.1.2**: 스키마 실행
  ```bash
  docker exec -i newsflow-postgres psql -U newsflow -d newsflow_poc < scripts/init_db.sql
  ```

**예상 시간**: 1시간
**완료 기준**: `\dt` 명령으로 3개 테이블 확인

---

### Task 1.2: SQLAlchemy ORM 모델

- [x] **1.2.1**: `src/storage/models.py` 작성
  ```python
  from sqlalchemy import Column, Integer, String, Text, Boolean, Float, TIMESTAMP, JSON
  from sqlalchemy.ext.declarative import declarative_base

  Base = declarative_base()

  class Selector(Base):
      __tablename__ = 'selectors'
      id = Column(Integer, primary_key=True)
      site_name = Column(String(100), unique=True, nullable=False)
      title_selector = Column(Text, nullable=False)
      body_selector = Column(Text, nullable=False)
      date_selector = Column(Text, nullable=False)
      site_type = Column(String(20), default='ssr')
      success_count = Column(Integer, default=0)
      failure_count = Column(Integer, default=0)

  class CrawlResult(Base):
      __tablename__ = 'crawl_results'
      id = Column(Integer, primary_key=True)
      url = Column(Text, unique=True, nullable=False)
      site_name = Column(String(100), nullable=False)
      title = Column(Text)
      body = Column(Text)
      date = Column(Text)
      quality_score = Column(Integer)
      crawl_mode = Column(String(20))
  ```

**예상 시간**: 1시간
**완료 기준**: `python -c "from src.storage.models import Base; print(Base)"` 성공

---

### Task 1.3: 초기 Selector 데이터 삽입

- [x] **1.3.1**: 연합뉴스 Selector 삽입
  ```sql
  INSERT INTO selectors (site_name, title_selector, body_selector, date_selector, site_type)
  VALUES ('yonhap', 'article h1.tit', 'article div.article-txt', 'article time', 'ssr');
  ```
- [x] **1.3.2**: 네이버 경제 Selector (init_db.sql에 포함됨)
- [x] **1.3.3**: BBC News Selector (init_db.sql에 포함됨)

**예상 시간**: 2시간
**완료 기준**: `SELECT * FROM selectors;` 3개 사이트 확인

---

## ✅ Phase 2: Scrapy 구현 (Day 3-5)

### Task 2.1: Scrapy 프로젝트 초기화 (Day 3)

- [x] **2.1.1**: Scrapy 프로젝트 생성
  ```bash
  # src/crawlers/ 디렉토리 구조 생성
  # scrapy.cfg, settings.py 작성 완료
  ```
- [x] **2.1.2**: Spider 3개 생성
  ```bash
  # yonhap.py, naver.py, bbc.py 골격 작성 완료
  scrapy list  # → bbc, naver, yonhap
  ```

**예상 시간**: 1시간

---

### Task 2.2: SSR Spider 구현 (Day 4) ✅

- [x] **2.2.1**: `yonhap_spider.py` 작성
  - PostgreSQL에서 Selector 동적 로드
  - CSS Selector로 title, body, date 추출
  - PostgreSQL `crawl_results` 테이블에 저장
  - 실제 크롤링 테스트 성공 (2개 기사)

- [x] **2.2.2**: HTML 구조 분석
  - 연합뉴스: `h1.tit01`, `article.article-wrap01`, `meta[property="article:published_time"]`
  - 네이버: `meta[property="og:title"]`, `article.go_trans._article_content`
  - PostgreSQL selectors 테이블 업데이트

- [x] **2.2.3**: 수동 테스트 성공
  ```bash
  scrapy crawl yonhap -a url="https://www.yna.co.kr/view/AKR20251028095752073"
  # [SUCCESS] Saved to PostgreSQL: Ʈ����, �Ϻ��� ������ ����...
  ```

**실제 소요 시간**: 4시간
**완료 기준**: ✅ 연합뉴스 기사 2개 PostgreSQL 저장 성공

---

### Task 2.3: 네이버 + BBC Spider 구현 (Day 5) ✅ 단순화!

- [ ] **2.3.1**: `naver.py` Spider 작성
  - yonhap Spider 패턴 복사 (SSR)
  - site_name="naver_economy"로 변경
  - PostgreSQL에서 Selector 로드

- [ ] **2.3.2**: `bbc.py` Spider 작성
  - **BBC News SSR 확인!** (2025-10-29 검증)
  - yonhap Spider 패턴 복사 (SSR)
  - site_name="bbc"로 변경

- [ ] **2.3.3**: 테스트
  - 네이버 기사 1개 크롤링 성공
  - BBC 기사 1개 크롤링 성공

**예상 시간**: 2시간 (원래 6시간 → **4시간 단축!**)
**완료 기준**: 네이버 + BBC 각 1개 기사 PostgreSQL 저장
**변경 사항**: scrapy-playwright 제거 (BBC도 SSR, 불필요)

---

## ✅ Phase 3: LangGraph Workflow (Day 6)

### Task 3.1: LangGraph State 정의

- [ ] **3.1.1**: `src/workflow/state.py` 작성
  ```python
  from typing import TypedDict, Literal, Optional

  class CrawlAgentState(TypedDict):
      url: str
      site_name: Literal["yonhap", "naver_economy", "bbc"]
      scrapy_success: bool
      scrapy_data: Optional[dict]
      gpt_selectors: Optional[dict]
      gemini_valid: bool
      final_data: Optional[dict]
      quality_score: int
  ```

**예상 시간**: 30분

---

### Task 3.2: LangGraph 노드 구현

- [ ] **3.2.1**: `src/workflow/nodes.py` 작성
  ```python
  def load_selector(state: CrawlAgentState) -> CrawlAgentState:
      # PostgreSQL에서 Selector 조회
      pass

  def run_scrapy(state: CrawlAgentState) -> CrawlAgentState:
      # Scrapy Spider 실행
      pass

  def check_scrapy_success(state: CrawlAgentState) -> CrawlAgentState:
      # title, body 검증
      pass
  ```

**예상 시간**: 2시간

---

### Task 3.3: 조건부 라우팅

- [ ] **3.3.1**: `src/workflow/routing.py` 작성
  ```python
  def route_after_scrapy(state: CrawlAgentState) -> str:
      if state["scrapy_success"]:
          return "save_result"
      else:
          return "activate_2_agent"
  ```

**예상 시간**: 1시간

---

### Task 3.4: LangGraph 빌드

- [ ] **3.4.1**: `src/workflow/graph.py` 작성
  ```python
  from langgraph.graph import StateGraph, END

  def build_newsflow_graph():
      workflow = StateGraph(CrawlAgentState)
      workflow.add_node("load_selector", load_selector)
      workflow.add_node("run_scrapy", run_scrapy)
      workflow.add_conditional_edges(
          "run_scrapy",
          route_after_scrapy,
          {"save_result": END, "activate_2_agent": "gpt_analyze"}
      )
      return workflow.compile()
  ```

**예상 시간**: 2시간
**완료 기준**: UC1 경로 (Scrapy 성공) 작동 확인

---

## ✅ Phase 4: 2-Agent System (Day 7-8)

### Task 4.1: GPT-4o Analyzer (Day 7)

- [ ] **4.1.1**: `src/utils/prompts.py` 작성
  ```python
  GPT_SYSTEM_PROMPT = """
  당신은 HTML 구조 분석 전문가입니다.
  주어진 HTML에서 뉴스 기사의 title, body, date를 추출할 CSS Selector를 생성하세요.

  **출력 형식** (JSON):
  {
    "title_selector": "CSS Selector",
    "body_selector": "CSS Selector",
    "date_selector": "CSS Selector",
    "confidence": 0.85
  }
  """
  ```
- [ ] **4.1.2**: `src/agents/gpt_analyzer.py` 작성
  ```python
  from openai import OpenAI

  def analyze_html(html: str) -> dict:
      client = OpenAI()
      response = client.chat.completions.create(
          model="gpt-4o-2024-08-06",
          messages=[
              {"role": "system", "content": GPT_SYSTEM_PROMPT},
              {"role": "user", "content": html}
          ],
          response_format={"type": "json_object"}
      )
      return response.choices[0].message.content
  ```

**예상 시간**: 3시간
**완료 기준**: 테스트 HTML로 Selector 생성 확인

---

### Task 4.2: Gemini 2.5 Validator (Day 8)

- [ ] **4.2.1**: `src/agents/gemini_validator.py` 작성
  ```python
  import google.generativeai as genai

  def validate_selectors(html: str, selectors: dict) -> dict:
      model = genai.GenerativeModel('gemini-2.0-flash-exp')
      prompt = f"다음 CSS Selector가 올바른지 10개 샘플을 추출하여 검증하세요: {selectors}"
      response = model.generate_content([html, prompt])
      return {"valid": True, "samples": [...]}
  ```

**예상 시간**: 3시간
**완료 기준**: GPT Selector 검증 성공

---

### Task 4.3: 합의 로직 통합

- [ ] **4.3.1**: `src/workflow/nodes.py`에 2-Agent 노드 추가
  ```python
  def gpt_analyze_node(state: CrawlAgentState) -> CrawlAgentState:
      # GPT 분석
      pass

  def gemini_validate_node(state: CrawlAgentState) -> CrawlAgentState:
      # Gemini 검증
      pass

  def check_consensus_node(state: CrawlAgentState) -> CrawlAgentState:
      # 합의 체크
      pass
  ```

**예상 시간**: 2시간
**완료 기준**: UC2 경로 (2-Agent 복구) 작동 확인

---

## ✅ Phase 5: 통합 테스트 (Day 9)

### Task 5.1: 3-Site 크롤링 테스트

- [ ] **5.1.1**: 연합뉴스 10개 URL 수집
- [ ] **5.1.2**: LangGraph 실행
  ```bash
  python src/main.py --site yonhap --urls urls_yonhap.txt
  ```
- [ ] **5.1.3**: 품질 점수 확인
  ```sql
  SELECT site_name, AVG(quality_score) FROM crawl_results GROUP BY site_name;
  ```

**목표**: 연합뉴스 9/10 이상 ≥80점

- [ ] **5.1.4**: 네이버 경제 10개 테스트
- [ ] **5.1.5**: BBC News 10개 테스트

**예상 시간**: 4시간
**완료 기준**: 30개 중 27개 이상 ≥80점

---

### Task 5.2: UC2 시연

- [ ] **5.2.1**: 연합뉴스 Selector 의도적으로 변경 (잘못된 Selector 입력)
- [ ] **5.2.2**: Scrapy 실패 감지 확인
- [ ] **5.2.3**: 2-Agent 활성화 확인
- [ ] **5.2.4**: 새 Selector 생성 및 재크롤링 성공 확인

**예상 시간**: 1시간

---

### Task 5.3: Decision Log 검증

- [ ] **5.3.1**: PostgreSQL 쿼리
  ```sql
  SELECT * FROM decision_logs WHERE consensus_reached = true LIMIT 5;
  ```
- [ ] **5.3.2**: JSONB 데이터 확인 (GPT reasoning, Gemini samples)

**예상 시간**: 30분

---

## ✅ Phase 6: 문서화 & 발표 (Day 10)

### Task 6.1: README 업데이트

- [ ] **6.1.1**: 설치 가이드 작성
- [ ] **6.1.2**: 실행 방법 작성
- [ ] **6.1.3**: 예시 출력 스크린샷 추가

**예상 시간**: 1시간

---

### Task 6.2: 발표 자료 작성

- [ ] **6.2.1**: 슬라이드 작성 (문제/솔루션/결과)
- [ ] **6.2.2**: 데모 시나리오 준비 (UC1/UC2/UC3)
- [ ] **6.2.3**: 품질 통계 정리
  - 총 30개 기사 수집
  - ≥80점 달성: 28개 (93%)
  - 평균 품질: 87점
  - 2-Agent 활성화: 3회 (UC2 2회, UC3 1회)

**예상 시간**: 2시간

---

### Task 6.3: 코드 정리

- [ ] **6.3.1**: 미사용 import 제거
- [ ] **6.3.2**: Type hints 추가
- [ ] **6.3.3**: Docstrings 작성

**예상 시간**: 1시간

---

## 📊 진행 현황 대시보드

### Week 1 체크포인트 (Day 5 종료 시)

- [ ] PostgreSQL 3개 테이블 생성 완료
- [ ] Scrapy 3개 Spider 작동 (연합뉴스, 네이버, BBC)
- [ ] UC1 경로 작동 (각 사이트 5개 기사 수집)
- [ ] 품질 점수 계산 로직 작동

---

### Week 2 체크포인트 (Day 10 종료 시)

- [ ] LangGraph Workflow 완성 (UC1/UC2/UC3)
- [ ] 2-Agent 시스템 작동 (GPT + Gemini)
- [ ] 30개 기사 수집 (≥90% 품질)
- [ ] Decision Log PostgreSQL 저장 확인
- [ ] 발표 자료 완성

---

## 🚨 리스크 및 대응 계획

### Risk 1: scrapy-playwright 설치 실패

**대응**: Playwright 수동 설치 가이드 준비
```bash
playwright install --with-deps chromium
```

---

### Risk 2: API 비용 초과

**대응**: 일일 호출 제한 (10회/일)
```python
if daily_api_calls > 10:
    raise Exception("Daily API limit exceeded")
```

---

### Risk 3: PostgreSQL 연결 실패

**대응**: Docker 재시작, 포트 충돌 확인
```bash
docker-compose down && docker-compose up -d
```

---

## 📈 예상 성과 (Expected Outcomes)

### 정량적 성과

- **크롤링 성공률**: ≥90% (27/30)
- **품질 점수**: 평균 85점 이상
- **자동 복구 시간**: 30-60초
- **비용**: PoC $0.06, 연간 $2.00

---

### 정성적 성과

- PostgreSQL 기반 프로덕션 준비 완료 (마이그레이션 불필요)
- 2-Agent 시스템 검증 (편향 방지)
- 3가지 유스케이스 명확화 (UC1/UC2/UC3)
- LangGraph 조건부 라우팅 실전 적용

---

## 🔗 참고 문서

- [00-PRD-1-PROBLEM-SOLUTION.md](./00-PRD-1-PROBLEM-SOLUTION.md) - 문제/솔루션
- [00-PRD-2-TECHNICAL-SPEC.md](./00-PRD-2-TECHNICAL-SPEC.md) - 기술 명세
- [README.md](./README.md) - 프로젝트 개요

---

**문서 상태**: ✅ 검증 완료 (10일 개발 계획)
**개발 시작 조건**: 이해관계자 승인 후 즉시 착수 가능
