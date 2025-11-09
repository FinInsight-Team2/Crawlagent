# CrawlAgent - LangGraph Multi-Agent Self-Healing Web Crawler

> **이전 명칭**: NewsFlow PoC (제안서/보고서용)
> **공식 명칭**: CrawlAgent (pyproject.toml)
> **업데이트**: 2025-11-06

범용 Self-Healing Multi-Agent 데이터 수집 시스템 - 뉴스, SNS, 블로그 등 다양한 웹 소스의 HTML 구조 변경에 자동으로 대응하는 지능형 크롤러

---

## 🚀 빠른 시작

### 1. Gradio UI 실행

```bash
cd /Users/charlee/Desktop/Intern/crawlagent
poetry run python src/ui/app.py
```

→ 브라우저에서 http://127.0.0.1:7860 열기

### 2. LangGraph Studio 실행 (개발자용)

```bash
cd /Users/charlee/Desktop/Intern/crawlagent
poetry run langgraph dev --tunnel
```

→ Cloudflare Tunnel URL 확인

---

## 📖 사용 방법

### Tab 1: 🚀 실시간 크롤링 (메인 기능!)

**목적**: URL을 입력하면 즉시 크롤링하고 DB에 저장

**사용법**:
1. 기사 URL 입력
2. 사이트 선택 (yonhap, naver, bbc)
3. "▶️ 지금 크롤링 시작" 클릭
4. 3-5초 후 결과 확인

**테스트 URL**:
```
연합뉴스: https://www.yna.co.kr/view/AKR20251103...
네이버: https://n.news.naver.com/mnews/article/...
BBC: https://www.bbc.com/news/articles/...
```

---

### Tab 2: 📊 데이터 조회

**목적**: 수집된 데이터 검색, 필터링, CSV 다운로드

**사용법**:
1. 필터 설정 (사이트/기간/점수/키워드)
2. "🔍 검색" 클릭
3. 결과 확인
4. "📥 CSV 다운로드" 클릭 (Excel에서 열기)

**활용 사례**:
- 마케팅팀: 특정 키워드 관련 기사 수집
- 분석팀: 최근 30일 데이터 다운로드
- 관리팀: 품질 점수 80점 이상만 필터링

---

### Tab 3: 🔧 수동 검증 (QA/개발자용)

**목적**: UC1 검증 로직 테스트

**사용법**:
1. 임의 데이터 입력 (URL, 제목, 본문, 날짜)
2. "🚀 UC1 검증 실행" 클릭
3. 점수 및 액션 확인

**테스트 시나리오**:
- Body 500자 이상 → 100점 (save)
- Body 200자 이하 → 40점 미만 (heal/new_site)

---

### Tab 4: 📈 통계 (관리자용)

**목적**: 전체 시스템 상태 및 통계 확인

**내용**:
- 총 수집 기사 수
- 사이트별 통계 (개수, 평균 점수)
- 품질 분포 (90점 이상, 80-90점, 80점 미만)
- 등록된 Selector 목록

---

## 🏗️ 시스템 구조

```
┌─────────────────────────────────────┐
│    Gradio UI (내부 직원용 도구)      │
│  - URL 입력 → 실시간 크롤링         │
│  - 데이터 검색 및 다운로드            │
└────────────┬────────────────────────┘
             │
    ┌────────▼────────┐
    │  UC1 Validation │
    │  (LangGraph)    │
    └────────┬────────┘
             │
      ┌──────▼──────┐
      │   Scrapy    │
      │  Crawlers   │
      └──────┬──────┘
             │
    ┌────────▼─────────┐
    │   PostgreSQL DB  │
    │  - crawl_results │
    │  - selectors     │
    └──────────────────┘
```

---

## 💡 핵심 기능

### 1. 실시간 크롤링
- URL 입력 → 즉시 수집
- 3-5초 내 완료
- 품질 자동 검증 (5W1H 기준)

### 2. 데이터 관리
- 검색 및 필터링
- CSV 다운로드 (Excel 호환)
- 키워드 검색

### 3. 품질 보장
- 5W1H 저널리즘 기준 (100점 만점)
  - Title: 20점
  - Body: 60점
  - Date: 10점
  - URL: 10점
- 80점 이상만 DB 저장

### 4. Self-Healing (UC2, 개발 예정)
- 사이트 구조 변경 자동 감지
- AI 기반 Selector 자동 복구
- GPT-4o + Gemini 2-Agent 합의

---

## 🎯 데모 시나리오 (5분)

### [1분] Tab 1: 실시간 크롤링
1. URL 입력
2. 크롤링 시작
3. 결과 확인 (제목, 본문, 점수)

**핵심 메시지**: "URL 넣으면 바로 작동합니다"

### [2분] Tab 2: 데이터 조회
1. 필터 설정 (오늘 수집, 80점 이상)
2. 검색 실행
3. 표 확인
4. CSV 다운로드

**핵심 메시지**: "다른 부서에서 바로 사용 가능합니다"

### [1분 30초] Tab 3: Self-Healing 증명
1. Body를 None으로 설정
2. UC1 실행
3. "heal" 트리거 확인

**핵심 메시지**: "UC1이 자동으로 감지하고 UC2를 트리거합니다"

### [30초] Tab 4: 통계
1. 새로고침 클릭
2. 전체 통계 확인

**핵심 메시지**: "92개 기사, 평균 99.0점"

---

## 🔧 개발 정보

### 기술 스택
- **UI**: Gradio 5.9+
- **Backend**: Python 3.11+
- **Crawler**: Scrapy 2.13+
- **Agent**: LangGraph 0.2+
- **DB**: PostgreSQL 16
- **AI**: GPT-4o, Gemini 2.5 Flash (UC2)

### 프로젝트 구조
```
newsflow-poc/
├── src/
│   ├── ui/
│   │   └── app.py           ← Gradio UI (실용적인 도구)
│   ├── spiders/
│   │   ├── yonhap_spider.py
│   │   ├── naver_spider.py
│   │   └── bbc_spider.py
│   ├── workflow/
│   │   └── uc1_validation.py
│   └── storage/
│       ├── database.py
│       └── models.py
├── tests/
├── docs/
│   └── newsflow-poc/        ← PRD 문서
└── README.md                ← 이 파일
```

### 테스트
```bash
# UC1 Validation Agent 테스트
poetry run pytest tests/test_uc1_validation.py -v

# 크롤러 테스트
poetry run scrapy crawl yonhap -a max_articles=3
```

---

## 📞 문의

- **개발팀**: Claude + Charlee
- **버전**: 1.0 (UC1 완료)
- **다음 업데이트**: UC2 Self-Healing (7-8시간 예상)

---

**Last Updated**: 2025-11-03
