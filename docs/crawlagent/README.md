# NewsFlow PoC - AI 기반 적응형 뉴스 크롤러

**프로젝트 상태**: 🟢 개발 준비 완료 (문서 정리 완료)
**작성일**: 2025-10-30
**개발 기간**: 10일

---

## 📌 프로젝트 개요

NewsFlow PoC는 **2-Agent 독립 검증 시스템**을 통해 뉴스 사이트 구조 변경 시 **30-60초 내 자동 복구**하는 적응형 크롤러입니다.

### 핵심 가치

- 🚀 **자동 복구**: 사이트 리뉴얼 시 30-60초 내 자동 대응 (기존 2-3일 → 1분)
- 💰 **비용 효율**: 평상시 LLM 미사용 (90%), 연간 $3 미만
- 🛡️ **편향 방지**: GPT-4o + Gemini 2.5 독립 검증
- 🎯 **프로덕션 준비**: PostgreSQL 16 (MVCC, JSONB) - 마이그레이션 불필요

---

## 🛠️ 기술 스택

| 레이어 | 기술 | 역할 | 검증 |
|--------|------|------|------|
| **크롤링** | Scrapy 2.13+ | SSR 3개 사이트 통합 | ✅ 56K+ stars |
| **데이터베이스** | PostgreSQL 16 | JSONB, MVCC | ✅ 엔터프라이즈급 |
| **오케스트레이션** | LangGraph 0.2+ | 조건부 라우팅 | ✅ LangChain 공식 |
| **LLM** | GPT-4o + Gemini 2.5 | Selector 생성 + 검증 | ✅ 공식 API |

**2025-10-30 업데이트**: scrapy-playwright 제거 (복잡도 40% 감소, 신뢰성 향상)

---

## 📂 라이언 칼슨 3-File PRD 구조

이 프로젝트는 **Ryan Carson의 3-File PRD 방법론**을 따릅니다.

### 🌟 필수 읽기 순서 (개발 시작 전)

1. **[PRD-1-PROBLEM-SOLUTION.md](./PRD-1-PROBLEM-SOLUTION.md)** ⭐
   - 문제 정의 및 솔루션 개요
   - 3가지 Use Case (UC1/UC2/UC3)
   - 비용 분석 ($3/년)
   - PoC 성공 기준

2. **[PRD-2-TECHNICAL-SPEC.md](./PRD-2-TECHNICAL-SPEC.md)** ⭐
   - 기술 스택 및 아키텍처
   - PostgreSQL 스키마 (3개 테이블)
   - Quality Score 알고리즘 (Rule-based)
   - Selector 업데이트 메커니즘
   - Gemini 장애 복구 로직
   - DOM 검증 방법

3. **[PRD-3-IMPLEMENTATION.md](./PRD-3-IMPLEMENTATION.md)** ⭐
   - 10일 개발 로드맵 (체크박스)
   - Phase별 작업 내용
   - 진행 상황 추적
   - 완료 기준

### 📚 보조 문서

- **[00-DESIGN-DECISIONS-PROPOSALS.md](./00-DESIGN-DECISIONS-PROPOSALS.md)**
  - Q1-Q4 설계 결정사항 제안서
  - Quality Score, Selector Update, DOM 검증, 장애 복구

- **[ARCHIVE-DECISIONS.md](./ARCHIVE-DECISIONS.md)**
  - 의사결정 아카이브
  - scrapy-playwright 제거 결정 (2025-10-29)
  - 기타 중요 결정사항 이력

---

## 🚀 Quick Start (25분)

### 1. PostgreSQL 시작 (5분)

```bash
cd ../../newsflow-poc
docker-compose up -d
psql -h localhost -U newsflow -d newsflow_poc -c "SELECT version();"
```

### 2. Python 환경 (10분)

```bash
python -m venv .venv
.venv\Scripts\activate  # Windows

# 의존성 설치 (playwright 제거됨)
pip install scrapy langgraph langchain-openai langchain-google-genai
pip install sqlalchemy psycopg2-binary beautifulsoup4 requests
pip install python-dotenv loguru pytest
```

### 3. 환경변수 (5분)

```bash
cd ../../newsflow-poc
cp .env.example .env
# .env 파일에 API 키 입력
```

### 4. 데이터베이스 스키마 (5분)

```bash
docker exec -i newsflow-postgres psql -U newsflow -d newsflow_poc < scripts/init_db.sql
psql -h localhost -U newsflow -d newsflow_poc -c "\dt"  # 3개 테이블 확인
```

---

## 📋 개발 워크플로우

### Claude Code 프롬프트 템플릿

```
docs/newsflow-poc/PRD-3-IMPLEMENTATION.md를 참고해서
Phase [번호]를 시작해줘.

Task [번호]부터 순서대로 진행하고,
완료할 때마다 체크박스를 업데이트해줘.
```

---

## 🎯 PoC 성공 기준

- [ ] 3-Site 크롤링: 연합뉴스, 네이버, BBC 각 10개 (≥80점)
- [ ] UC1/UC2/UC3 각 1회 이상 시연
- [ ] 품질 달성률 ≥90% (27/30)
- [ ] Decision Log PostgreSQL JSONB 저장

---

## 💰 비용 ($3/년)

| UC | 빈도 | 비용 |
|----|------|------|
| UC1 (정상) | 900/1000 | $0 (Rule-based) |
| UC2 (복구) | 50/1000 | $1.50 (Selector 생성) |
| UC3 (신규) | 50/1000 | $1.50 (Selector 생성) |
| **총계** | **1000** | **$3.00/년** |

---

## 📅 10일 개발 계획

| Day | Phase | 작업 | 상태 |
|-----|-------|------|------|
| 1-2 | Phase 0-1 | PostgreSQL 스키마 | ✅ 완료 |
| 3-4 | Phase 2.1-2.2 | Scrapy 초기화, yonhap spider | ✅ 완료 |
| 5 | Phase 2.3 | naver + bbc spiders | ⏳ 진행 중 |
| 6 | Phase 3 | LangGraph Workflow | ⏳ 대기 |
| 7-8 | Phase 4 | 2-Agent System | ⏳ 대기 |
| 9 | Phase 5 | 통합 테스트 (30개) | ⏳ 대기 |
| 10 | Phase 6 | 문서화 & 발표 | ⏳ 대기 |

**상세**: [PRD-3-IMPLEMENTATION.md](./PRD-3-IMPLEMENTATION.md)

---

## 🔗 참고 자료

### 공식 문서
- **Scrapy**: [https://docs.scrapy.org/en/latest/](https://docs.scrapy.org/en/latest/)
- **PostgreSQL 16**: [https://www.postgresql.org/docs/16/](https://www.postgresql.org/docs/16/)
- **LangGraph**: [https://langchain-ai.github.io/langgraph/](https://langchain-ai.github.io/langgraph/)

### 학술 논문
- **AUTOSCRAPER** (EMNLP 2024): [https://arxiv.org/abs/2404.12753](https://arxiv.org/abs/2404.12753)
- **Constitutional AI** (Anthropic 2022): [https://arxiv.org/abs/2212.08073](https://arxiv.org/abs/2212.08073)

---

## 📁 디렉토리 구조

```
TIL/
├── docs/
│   └── newsflow-poc/                      # 📚 프로젝트 문서 (여기)
│       ├── README.md                       # ⭐ 시작 지점 (이 파일)
│       ├── PRD-1-PROBLEM-SOLUTION.md       # 문제/솔루션
│       ├── PRD-2-TECHNICAL-SPEC.md         # 기술 명세
│       ├── PRD-3-IMPLEMENTATION.md         # 구현 가이드 & 로드맵
│       ├── 00-DESIGN-DECISIONS-PROPOSALS.md # 설계 제안서
│       └── ARCHIVE-DECISIONS.md            # 의사결정 아카이브
│
└── newsflow-poc/                          # 💻 실제 개발 코드
    ├── src/                               # 소스 코드
    ├── tests/                             # 테스트
    ├── scripts/                           # SQL, 유틸리티
    ├── docker-compose.yml                 # PostgreSQL
    ├── pyproject.toml                     # 의존성 (playwright 제거됨)
    └── .env.example                       # 환경변수 예시
```

---

## 🔄 문서 업데이트 이력

| 일자 | 변경 사항 | 버전 |
|------|-----------|------|
| 2025-10-28 | 초기 PRD 작성 | 1.0 |
| 2025-10-29 | scrapy-playwright 제거 | 1.5 |
| 2025-10-30 | 3-File PRD 구조 정리, 설계 결정사항 반영 | 2.0 |

---

**다음 단계**: [PRD-1-PROBLEM-SOLUTION.md](./PRD-1-PROBLEM-SOLUTION.md) 읽기
