# CrawlAgent 사용자 경험 가이드

**작성일**: 2025-11-09
**대상**: 일반 사용자, 데모 체험자, 시스템 관리자

---

## 1. Executive Summary

### 핵심 질문: "사용자는 API 키를 신경 써야 하나요?"

**답변**: **아니요! 일반 사용자는 API 키를 몰라도 됩니다.**

- **일반 사용자**: Gradio UI로 완성된 크롤링 결과만 조회/검색 (API 키 불필요)
- **시스템 관리자**: 백그라운드 크롤링 + AI 복구 실행 (API 키 필요)

---

## 2. 현재 API 사용 현황

### 2.1. API 키가 필요한 기능 (백그라운드)

| API 제공자 | 사용 위치 | 목적 | 사용 빈도 |
|----------|---------|------|---------|
| **OpenAI GPT-4o-mini** | UC1 품질 검증<br>UC2 Selector 제안<br>NLP 검색 | 기사 품질 평가<br>Selector 자동 생성<br>자연어 쿼리 파싱 | 크롤링 시 매번<br>(1000건/일) |
| **Google Gemini 2.0** | UC2 Selector 검증 | GPT 제안 검증 (2-Agent 합의) | UC2 실행 시<br>(10건/일) |
| **Anthropic Claude Sonnet 4.5** | UC3 신규 사이트 분석 | 신규 사이트 Selector 자동 생성 | 신규 사이트 추가 시<br>(1-2건/월) |

**파일 위치**:
```python
# UC1 (품질 검증)
src/agents/uc1_quality_gate.py:25
  client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# UC2 (Selector 복구)
src/workflow/uc2_hitl.py:139
  client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))  # GPT 제안
src/workflow/uc2_hitl.py:410
  genai.configure(api_key=os.getenv("GEMINI_API_KEY"))   # Gemini 검증

# UC3 (신규 사이트)
src/workflow/uc3_new_site.py:296
  llm = ChatAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

# NLP 검색
src/agents/nlp_search.py:50
  api_key = os.getenv("OPENAI_API_KEY")
```

### 2.2. API 키가 불필요한 기능 (Gradio UI)

| 기능 | 설명 | 사용자 경험 |
|-----|------|-----------|
| **기사 검색** | 키워드, 카테고리, 날짜 검색 | 무료, 즉시 응답 |
| **기사 조회** | 제목, 본문, 품질 점수 확인 | 무료, DB 조회만 |
| **통계 대시보드** | 카테고리별 기사 수, 평균 품질 | 무료, 실시간 업데이트 |
| **CSV 다운로드** | 검색 결과 엑셀 다운로드 | 무료, 즉시 다운로드 |
| **LangGraph 시각화** | AI 워크플로우 다이어그램 | 무료, 정적 시각화 |

**파일 위치**:
```python
# Gradio UI (API 키 사용 안 함)
src/ui/app.py
  - search_articles()  # DB 조회만
  - download_csv()     # 로컬 파일 생성만
  - get_stats_summary()  # DB 집계만
```

---

## 3. 사용자 유형별 경험 시나리오

### 3.1. 일반 사용자 (뉴스 검색/조회)

**페르소나**: 김기자 (언론사 기자, 뉴스 데이터 분석가)

**사용 목적**:
- 과거 뉴스 기사 검색
- 카테고리별 트렌드 분석
- 엑셀 다운로드하여 보고서 작성

**사용 흐름**:
```
1. http://localhost:7860 접속
   ↓
2. Tab 1 "뉴스 검색" 클릭
   ↓
3. 키워드 입력 (예: "삼성전자 주가")
   ↓
4. 카테고리 선택 (예: "경제")
   ↓
5. 날짜 범위 선택 (예: 2025-11-01 ~ 2025-11-09)
   ↓
6. "검색" 버튼 클릭
   ↓
7. 결과 확인 (100건의 기사 테이블)
   ↓
8. "CSV 다운로드" 클릭
   ↓
9. 엑셀로 열어서 분석
```

**API 키 필요 여부**: ❌ 불필요
**비용**: 무료
**응답 속도**: 0.1초 (DB 조회만)

---

### 3.2. 시스템 관리자 (크롤링 실행)

**페르소나**: 박개발 (CrawlAgent 운영자, DevOps 엔지니어)

**사용 목적**:
- 매일 자정 뉴스 크롤링 실행
- 사이트 변경 시 자동 복구 (UC2)
- 신규 사이트 추가 (UC3)

**사용 흐름**:
```
1. .env 파일 설정 (최초 1회만)
   OPENAI_API_KEY=sk-proj-...
   GEMINI_API_KEY=AIza...
   ANTHROPIC_API_KEY=sk-ant-...
   ↓
2. 크롤링 실행 (Cron 또는 수동)
   poetry run scrapy crawl yonhap -a target_date=2025-11-09
   ↓
3. UC1 자동 실행 (품질 검증)
   - OpenAI GPT-4o-mini API 호출
   - 품질 점수 < 80이면 UC2 트리거
   ↓
4. UC2 자동 실행 (Selector 복구)
   - OpenAI GPT-4o-mini: Selector 제안
   - Google Gemini 2.0: Selector 검증
   - 합의 점수 >= 0.8이면 자동 승인
   ↓
5. 결과 DB 저장
   ↓
6. (선택) Slack 알림 (Sprint 3)
```

**API 키 필요 여부**: ✅ 필요
**비용**: 월 $5~$10 (1000건 크롤링 기준)
**응답 속도**: 3~5초/기사 (AI 분석 포함)

---

### 3.3. 데모 체험자 (PoC 시연)

**페르소나**: 최투자 (VC 투자자, 기술 검증 중)

**사용 목적**:
- CrawlAgent의 자동화 능력 확인
- AI 복구 기능 데모 체험
- ROI 분석 (수동 vs 자동)

**사용 흐름**:
```
1. http://localhost:7860 접속 (관리자가 미리 실행)
   ↓
2. Tab 1: 뉴스 검색
   - 이미 수집된 1000건의 기사 조회
   - API 키 불필요, 즉시 검색 가능
   ↓
3. Tab 2: 통계 대시보드
   - 카테고리별 분포, 평균 품질 확인
   - API 키 불필요
   ↓
4. Tab 5: LangGraph 워크플로우
   - UC1 → UC2 자동 복구 플로우 시각화
   - API 키 불필요, 정적 다이어그램
   ↓
5. Tab 6: 자동 복구 (개발자 전용)
   - DecisionLog 조회 (GPT + Gemini 합의 결과)
   - API 키 불필요, DB 조회만
   ↓
6. (선택) 관리자가 라이브 크롤링 시연
   - Tab 3: 크롤링 실행
   - API 키 필요 (관리자가 미리 설정)
```

**API 키 필요 여부**: ❌ 불필요 (기존 데이터만 보는 경우)
**비용**: 무료
**추천 시나리오**: 관리자가 미리 1000건 크롤링 → 데모 체험자는 조회만

---

## 4. API 키 관리 전략

### 4.1. 현재 방식 (개발자 친화적, 보안 강화)

**장점**:
- ✅ API 키가 `.env` 파일에 중앙 집중
- ✅ 버전 관리에서 제외 (`.gitignore`)
- ✅ 서버 환경변수로 관리 가능

**단점**:
- ❌ 일반 사용자가 Gradio UI만으로 크롤링 실행 불가
- ❌ 데모 시연 시 관리자가 미리 `.env` 설정 필요

**적합한 사용 사례**:
- 사내 뉴스 모니터링 시스템 (관리자 1명 + 사용자 10명)
- 클라우드 배포 (AWS/GCP 환경변수로 관리)

---

### 4.2. 대안 1: Gradio UI에 API 키 입력란 추가

**변경 사항**:
```python
# src/ui/app.py
with gr.Tab("⚙️ 설정"):
    openai_key = gr.Textbox(label="OpenAI API Key", type="password")
    gemini_key = gr.Textbox(label="Gemini API Key", type="password")
    anthropic_key = gr.Textbox(label="Anthropic API Key (선택)", type="password")

    save_btn = gr.Button("저장")

    def save_api_keys(openai, gemini, anthropic):
        os.environ["OPENAI_API_KEY"] = openai
        os.environ["GEMINI_API_KEY"] = gemini
        os.environ["ANTHROPIC_API_KEY"] = anthropic
        return "✅ API 키 저장 완료"
```

**장점**:
- ✅ 사용자가 UI에서 직접 API 키 입력 가능
- ✅ 데모 체험 시 즉시 크롤링 실행 가능

**단점**:
- ❌ 보안 위험 (브라우저에 API 키 노출)
- ❌ 여러 사용자 동시 접속 시 API 키 충돌

**적합한 사용 사례**:
- 로컬 데모 환경 (1명만 사용)
- 개인 프로젝트

---

### 4.3. 대안 2: 관리자/사용자 역할 분리 (추천)

**아키텍처**:
```
[관리자 전용 서버]
  - .env 파일로 API 키 관리
  - Cron으로 매일 크롤링 실행
  - UC2/UC3 자동 복구 실행
  - 결과를 PostgreSQL DB에 저장

      ↓ (DB 연결)

[사용자 전용 Gradio UI]
  - API 키 불필요 (DB 조회만)
  - 뉴스 검색, 통계, CSV 다운로드
  - 공개 URL 배포 가능 (https://...)
```

**장점**:
- ✅ 보안 안전 (API 키 노출 없음)
- ✅ 다중 사용자 동시 접속 가능
- ✅ 비용 관리 용이 (관리자만 API 키 보유)

**단점**:
- ❌ 2개 서버 운영 필요 (관리자 + 사용자)

**적합한 사용 사례**:
- 프로덕션 환경
- 다중 사용자 서비스
- VC 데모 시연 (사용자는 조회만)

---

### 4.4. 대안 3: API 키 공유 풀 (비용 절감)

**아키텍처**:
```python
# src/config/api_pool.py
API_KEY_POOL = {
    "openai": [
        "sk-proj-key1",  # 월 $10 한도
        "sk-proj-key2",  # 월 $10 한도
        "sk-proj-key3"   # 월 $10 한도
    ],
    "gemini": [
        "AIza-key1",
        "AIza-key2"
    ]
}

def get_available_key(provider: str) -> str:
    """
    사용 가능한 API 키를 순환 반환 (Round-robin)
    """
    keys = API_KEY_POOL[provider]
    # 사용량 체크 후 가장 여유 있는 키 반환
    return keys[0]
```

**장점**:
- ✅ 여러 API 키로 부하 분산
- ✅ 한 키가 한도 초과해도 자동 전환

**단점**:
- ❌ 키 관리 복잡도 증가
- ❌ 보안 위험 (여러 키 노출)

**적합한 사용 사례**:
- 대량 크롤링 (10,000건/일 이상)
- 24/7 운영 환경

---

## 5. 추천 구성 (현실적인 배포 시나리오)

### 5.1. 로컬 데모 환경 (현재 PoC)

**구성**:
```
1. .env 파일에 API 키 설정 (관리자가 1회만)
2. 매일 자정 Cron으로 크롤링 실행
3. Gradio UI는 localhost:7860으로 실행
4. 사용자는 브라우저로 접속하여 조회만
```

**사용자 경험**:
- ✅ API 키 불필요 (관리자가 이미 설정)
- ✅ 검색/조회/다운로드 모두 무료
- ✅ 응답 속도 빠름 (DB 조회만)

**명령어**:
```bash
# 관리자 (최초 1회)
echo "OPENAI_API_KEY=sk-proj-..." >> .env
echo "GEMINI_API_KEY=AIza..." >> .env

# 크롤링 실행 (매일 자정 Cron)
poetry run scrapy crawl yonhap -a target_date=2025-11-09

# Gradio UI 실행
poetry run python src/ui/app.py

# 사용자 접속
# http://localhost:7860
```

---

### 5.2. 클라우드 배포 환경 (프로덕션)

**구성**:
```
[AWS EC2 또는 GCP Compute Engine]
  - 환경변수로 API 키 관리 (AWS Secrets Manager)
  - Docker 컨테이너로 배포
  - Nginx로 리버스 프록시
  - PostgreSQL RDS 사용
  - Gradio UI를 https://crawlagent.example.com으로 공개
```

**사용자 경험**:
- ✅ 공개 URL 접속 가능
- ✅ API 키 불필요
- ✅ 모바일에서도 접속 가능

**배포 명령어**:
```bash
# Docker 빌드
docker build -t crawlagent:latest .

# 환경변수 전달
docker run -d \
  -e OPENAI_API_KEY=$OPENAI_KEY \
  -e GEMINI_API_KEY=$GEMINI_KEY \
  -p 7860:7860 \
  crawlagent:latest
```

---

## 6. 비용 분석 (월간)

### 6.1. API 비용 (1000건 크롤링 기준)

| API | 모델 | 호출 횟수 | 단가 | 월 비용 |
|-----|------|---------|------|--------|
| OpenAI | gpt-4o-mini | 1000 (UC1) + 10 (UC2) | $0.15/1M tokens | **$3** |
| Google | gemini-2.0-flash | 10 (UC2) | 무료 (60 RPM) | **$0** |
| Anthropic | claude-sonnet-4.5 | 2 (UC3) | $3/1M input tokens | **$1** |
| **합계** | | | | **$4/월** |

### 6.2. 인프라 비용

| 항목 | 사양 | 월 비용 |
|-----|------|--------|
| EC2 t3.small | 2 vCPU, 2GB RAM | $15/월 |
| PostgreSQL RDS | db.t3.micro | $15/월 |
| CloudWatch 로그 | 5GB/월 | $2/월 |
| **합계** | | **$32/월** |

### 6.3. 총 운영 비용

**월 $36** = API $4 + 인프라 $32

**ROI 분석**:
- 수동 뉴스 수집: 3명 × 8시간/일 × 30일 = 720시간/월
- CrawlAgent 자동화: 2시간/월 (설정 + 모니터링)
- **시간 절감**: 99.7%

---

## 7. 결론: 사용자는 어떻게 경험하나요?

### 일반 사용자 (뉴스 검색/조회)

**경험**:
```
1. http://localhost:7860 접속
2. "뉴스 검색" 탭 클릭
3. 키워드 입력 (예: "삼성전자")
4. 결과 확인 (100건)
5. CSV 다운로드
```

**API 키 필요 여부**: ❌ 불필요
**비용**: 무료
**체감 속도**: 즉시 (0.1초)

**UI/UX 특징**:
- ✅ 깔끔한 다크 테마
- ✅ 모바일 반응형
- ✅ 실시간 통계 차트
- ✅ 엑셀 다운로드 지원

---

### 시스템 관리자 (크롤링 실행)

**경험**:
```
1. .env 파일 설정 (최초 1회)
2. Cron으로 자동 크롤링 설정
3. Slack 알림으로 결과 확인 (Sprint 3)
4. 오류 발생 시 Gradio UI에서 Human Review
```

**API 키 필요 여부**: ✅ 필요
**비용**: 월 $4 (1000건 기준)
**체감 속도**: 백그라운드 실행 (사용자는 모름)

---

### 최종 답변

**"사용자는 API 키를 신경 써야 하나요?"**

**아니요!** CrawlAgent는 다음과 같이 설계되었습니다:

1. **백그라운드 크롤링** (관리자만 API 키 설정)
   - 매일 자동 실행
   - UC1 → UC2 자동 복구
   - 결과를 DB에 저장

2. **프론트엔드 UI** (사용자는 API 키 불필요)
   - DB 조회만
   - 검색, 통계, 다운로드
   - 모든 기능 무료

**사용자 친화적인 이유**:
- ✅ Gradio UI는 직관적 (검색 창만 있으면 됨)
- ✅ 응답 속도 빠름 (DB 조회만)
- ✅ API 키 관리 불필요 (관리자가 처리)
- ✅ 모바일 접속 가능
- ✅ CSV 다운로드로 엑셀 분석 가능

**PoC 데모 시나리오**:
1. 관리자가 미리 1000건 크롤링 실행
2. 데모 체험자는 http://localhost:7860 접속
3. 키워드 검색, 통계 확인, CSV 다운로드
4. API 키 전혀 몰라도 됨!

---

## 8. Phase 2: UI Redesign 계획 (Tab 6 삭제)

### 8.1. 현재 문제점

**Tab 6 "자동 복구 (개발자)" 탭의 문제**:
- ❌ 사용자가 Gradio UI를 계속 모니터링해야 함
- ❌ DecisionLog 조회 후 수동으로 승인/거부 클릭 필요
- ❌ Human-in-the-Loop 불편 (실시간 알림 없음)
- ❌ 6개 탭이 너무 많음 (사용자 혼란)

**현재 워크플로우** (불편):
```
UC2 합의 실패 (consensus_reached=False)
         ↓
DecisionLog DB에 저장
         ↓
[문제] 사용자가 모름 (알림 없음)
         ↓
사용자가 Gradio Tab 6 접속
         ↓
"새로고침" 버튼 클릭
         ↓
Pending List 확인
         ↓
"승인" 또는 "거부" 클릭
         ↓
Selector 업데이트 또는 무시
```

### 8.2. Phase 2 개선 방안

**목표**: Tab 6 삭제 + Slack 알림으로 대체

**새로운 워크플로우** (편리):
```
UC2 합의 실패 (consensus_reached=False)
         ↓
DecisionLog DB에 저장
         ↓
Slack 알림 발송 (즉시)
  - 메시지: "UC2 합의 실패! 사이트: yonhap, URL: ..."
  - 버튼: [✅ 승인] [❌ 거부] [📊 상세보기]
         ↓
관리자가 Slack에서 버튼 클릭
         ↓
Webhook으로 승인/거부 처리
         ↓
Selector 자동 업데이트 또는 무시
         ↓
Slack 알림: "✅ 승인 완료! Selector 업데이트됨"
```

**장점**:
- ✅ 실시간 알림 (모바일에서도 확인 가능)
- ✅ Gradio UI 모니터링 불필요
- ✅ Slack에서 바로 승인/거부 (1 클릭)
- ✅ UI 단순화 (6탭 → 4탭)

### 8.3. 새로운 UI 구조

**Phase 2 이후** (4개 탭):
1. **Tab 1**: 🔍 뉴스 검색
   - 키워드, 카테고리, 날짜 검색
   - CSV 다운로드

2. **Tab 2**: 📊 통계 대시보드
   - 카테고리별 분포, 평균 품질
   - 차트 시각화

3. **Tab 3**: 🚀 크롤링 실행 (개발자용)
   - 사이트 선택, 날짜 설정
   - 실행 버튼

4. **Tab 4**: 🌐 LangGraph 워크플로우
   - UC1 → UC2 플로우 시각화
   - 상태 다이어그램

~~Tab 5, Tab 6 삭제~~

### 8.4. Sprint 3: Notification 시스템 구현

**작업 내역** (예정):
1. Slack Webhook 통합 (`src/notifications/slack_notifier.py`)
2. UC2 합의 실패 시 알림 발송
3. Slack Interactive Button 구현
4. Webhook 엔드포인트 구현 (승인/거부 처리)
5. Gradio Tab 6 삭제
6. 테스트 (`tests/test_slack_notifications.py`)

**예상 일정**: Sprint 3 (1일)

---

**문서 작성일**: 2025-11-09
**다음 업데이트**: Sprint 3 완료 후 (Tab 6 삭제 적용)
