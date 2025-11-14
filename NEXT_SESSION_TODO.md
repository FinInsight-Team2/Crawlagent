# 다음 세션 작업 인계 문서

**작성일**: 2025-11-13
**현재 진행률**: PRD v2.1 완료, Phase 1 준비 완료 (95% 완료)
**상태**: 🔴 DEPRECATED - 이 문서는 구버전입니다. [PROJECT_COMPLETION_PRD.md](PROJECT_COMPLETION_PRD.md) 참조

---

## 🎯 전체 목표

CrawlAgent PoC 완성 - 기존 Gradio UI (6탭) → 개선된 3탭 구조로 재구성
- **핵심 원칙**: 기존 코드 70% 재사용, Simple is Best
- **목표**: 실사용 신뢰성 + 발표 자료 통합

---

## ✅ 완료된 작업

### 1. 기존 UI 분석 완료
- 파일: `/Users/charlee/Desktop/Intern/crawlagent/src/ui/app.py`
- 크기: 28,768 tokens (매우 큼)
- 구조: 6개 탭 (콘텐츠 수집, AI 아키텍처, 데이터 조회, 비용 분석, 데이터 관리, 자동 스케줄)

### 2. 재사용 가능한 컴포넌트 식별
**100% 보존할 것:**
- Master Graph UC Test Demo (Tab 1) - 핵심 기능
- `search_articles()` 함수 (Tab 3)
- `refresh_cost_dashboard()` 함수 (Tab 4)
- Natural Language Search (Tab 3)

**제거할 것:**
- Single URL Crawling 섹션 (Line 295-720 추정)
- `run_single_crawl()` 함수 (중복)

---

## 🚧 현재 진행 중 작업

### Phase 1: Tab 1 개선 (10% 완료)

**위치 확인 완료:**
- Single URL Crawling 시작: Line 295-296
- 함수 정의: Line 347 `run_single_crawl()`
- UI 컴포넌트: Line 300-344

**다음 작업:**
1. Line 293-720 구간 정확히 파악 (섹션 끝 찾기)
2. 해당 구간 삭제
3. Master Graph Demo 정상 작동 확인

---

## 📋 남은 작업 (Phase 1-5)

### Phase 1: Tab 1 개선 (1시간 남음)
- [ ] Single URL Crawling 섹션 제거 (30분)
- [ ] Batch Notice 제거 (5분)
- [ ] 오류 처리 개선 (25분)
  - OpenAI API graceful fallback
  - User-Agent 로테이션
  - 재시도 로직 3회

### Phase 2: Tab 2 개선 (1.5시간)
- [ ] 기존 코드 보존 확인 (15분)
- [ ] JSON Export 추가 (20분)
- [ ] 기사 상세 Modal 변경 (30분)
- [ ] 시각화 추가 (25분)

### Phase 3: Tab 3 신규 구성 (1.5시간)
- [ ] Cost Dashboard 이동 (20분)
- [ ] Decision Log 이동 (15분)
- [ ] 발표 자료 Markdown 작성 (40분)
- [ ] 실시간 통계 추가 (15분)

### Phase 4: 실사용 테스트 (1시간)
- [ ] End-to-End 테스트 (30분) - **사용자 URL 2개 필요**
- [ ] 10개 URL 스트레스 테스트 (30분) - **사용자 URL 10개 필요**

### Phase 5: 문서화 및 정리 (1시간)
- [ ] README 업데이트 (30분)
- [ ] 불필요한 코드 제거 (30분)
  - `uc1_validation_llm.py` 삭제
  - Supervisor LLM toggle 제거

---

## 🔍 다음 세션 시작 방법

### 옵션 1: 이 파일 제시
다음 세션에서 이렇게 말하기:
```
"NEXT_SESSION_TODO.md 파일 읽고 작업 계속 진행해줘"
```

### 옵션 2: 컨텍스트 요약 제공
```
"CrawlAgent Gradio UI를 6탭에서 3탭으로 개선 중이야.
Phase 1에서 Single URL Crawling 섹션 제거하다가 멈췄어.
src/ui/app.py Line 293-720 구간 삭제 작업 계속해줘."
```

### 옵션 3: 구체적 지시
```
"src/ui/app.py에서 '### 1️⃣ 테스트 크롤링' 섹션부터
다음 '---' 구분선 전까지 삭제해줘.
Master Graph Demo는 절대 건드리지 마."
```

---

## 📁 중요 파일 경로

### 수정할 파일:
- `/Users/charlee/Desktop/Intern/crawlagent/src/ui/app.py` (메인 UI)

### 참고 문서:
- `/Users/charlee/Desktop/Intern/crawlagent/POC_SUCCESS_REPORT.md` (성공 지표)
- `/Users/charlee/Desktop/Intern/crawlagent/DEMO_GUIDE.md` (데모 가이드)
- `/Users/charlee/Desktop/Intern/crawlagent/docs/AI_WORKFLOW_ARCHITECTURE.md` (아키텍처)

### 삭제 예정:
- `/Users/charlee/Desktop/Intern/crawlagent/src/workflow/uc1_validation_llm.py` (Phase 5)

---

## 🎯 성공 기준

### Phase 1 완료 조건:
- ✅ Single URL Crawling 섹션 제거됨
- ✅ Master Graph Demo 정상 작동
- ✅ OpenAI API 오류 시 graceful fallback
- ✅ Gradio UI 실행 가능: `poetry run python -m src.ui.app`

### 전체 완료 조건:
- ✅ 3개 탭 모두 작동 (Run Crawl, View Data, Project Overview)
- ✅ 10개 실제 URL 테스트 80%+ 성공
- ✅ README 업데이트 완료
- ✅ 불필요한 코드 제거 완료

---

## ⚠️ 주의사항

### 절대 건드리지 말 것:
1. **Master Graph UC Test Demo** (Tab 1 핵심)
   - `run_quick_uc_test()` 함수
   - UC 결과 카드 HTML
   - Workflow History 표시

2. **데이터 조회 함수들** (Tab 3)
   - `search_articles()`
   - `handle_nl_search()`
   - `download_csv()`

3. **비용 대시보드** (Tab 4)
   - `refresh_cost_dashboard()`
   - HTML 차트 생성 로직

### Simple is Best 원칙:
- 기존 작동하는 코드는 최대한 보존
- 중복되는 기능만 제거
- 새 기능은 최소한으로

---

## 📞 사용자 협업 필요 시점

### Phase 4 시작 전:
1. **초기 테스트 URL 2개** 요청
   - UC1용: BBC, Reuters, 연합뉴스 등 (DB에 셀렉터 있는 사이트)
   - UC3용: The Guardian, AP News 등 (신규 사이트)

2. **스트레스 테스트 URL 10개** 요청
   - 다양한 언어 (영어, 한국어)
   - 다양한 사이트 (BBC, CNN, 연합뉴스, 한경 등)

---

## 🔄 롤백 방법

작업 중 문제 발생 시:
```bash
cd /Users/charlee/Desktop/Intern/crawlagent
git status  # 변경 사항 확인
git diff src/ui/app.py  # 변경 내용 확인
git restore src/ui/app.py  # 원복
```

---

## 📊 진행률 추적

- [x] 기존 UI 분석 (100%)
- [x] 재사용 컴포넌트 식별 (100%)
- [ ] Phase 1: Tab 1 개선 (10%)
- [ ] Phase 2: Tab 2 개선 (0%)
- [ ] Phase 3: Tab 3 구성 (0%)
- [ ] Phase 4: 실사용 테스트 (0%)
- [ ] Phase 5: 문서화 (0%)

**전체 진행률: 15%**

---

**다음 세션 첫 작업**: src/ui/app.py에서 Single URL Crawling 섹션 (Line 293-720) 찾아서 삭제
