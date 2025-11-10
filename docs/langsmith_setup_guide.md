# LangSmith 설정 가이드 - CrawlAgent 워크플로우 시각화

**작성일**: 2025-11-09
**목적**: LangSmith로 Master Workflow를 GUI에서 시각화하기

---

## 📌 LangSmith란?

**LangSmith**는 LangChain 공식 모니터링/디버깅 플랫폼입니다.

### 핵심 기능:
- ✅ **워크플로우 시각화**: LangGraph의 모든 노드 실행을 GUI로 확인
- ✅ **실시간 트레이싱**: supervisor → uc1 → uc2 → uc3 경로 추적
- ✅ **State 변화 추적**: 각 노드에서 State가 어떻게 변하는지 확인
- ✅ **LLM 호출 모니터링**: GPT/Gemini/Claude 호출 로그
- ✅ **성능 메트릭**: Latency, Cost, Token 사용량
- ✅ **에러 디버깅**: 어디서 실패했는지 즉시 확인

### 왜 LangSmith인가?

**LangGraph Studio Desktop이 중단된 이유**:
- 2025년 10월부터 LangGraph Platform → **"LangSmith Deployment"**로 통합
- Desktop App보다 클라우드 기반 LangSmith가 더 강력
- Production 환경에서 표준으로 사용

**현업 개발자들이 사용하는 방법**:
1. 개발 중: LangSmith로 실시간 트레이싱
2. 디버깅: LangSmith에서 각 노드 실행 결과 확인
3. Production: LangSmith Deployment로 모니터링

---

## 🚀 LangSmith 설정 (5분)

### Step 1: LangSmith 계정 생성 (무료)

1. https://smith.langchain.com 접속
2. **Sign Up** 클릭
   - GitHub 계정으로 로그인 (추천)
   - 또는 Email로 가입
3. 무료 플랜 선택 (Beta 기간 동안 무료)

### Step 2: API Key 생성

1. LangSmith 로그인 후 **Settings** 클릭
2. **API Keys** 탭 선택
3. **Create API Key** 클릭
4. Key 이름 입력 (예: `crawlagent-dev`)
5. **Create** 클릭
6. 생성된 API Key 복사 (⚠️ 다시 볼 수 없으니 저장!)

### Step 3: .env 파일에 API Key 설정

`/Users/charlee/Desktop/Intern/crawlagent/.env` 파일 열기:

```bash
# LangSmith Tracing (워크플로우 시각화)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2_pt_xxxxxxxxxxxxxxxx  # 여기에 복사한 API Key 입력
LANGCHAIN_PROJECT=crawlagent-poc
```

**설명**:
- `LANGCHAIN_TRACING_V2=true`: Tracing 활성화
- `LANGCHAIN_API_KEY`: LangSmith API Key
- `LANGCHAIN_PROJECT`: 프로젝트 이름 (LangSmith UI에서 구분용)

### Step 4: 환경 변수 로드 확인

```bash
cd /Users/charlee/Desktop/Intern/crawlagent
poetry run python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('LangSmith:', os.getenv('LANGCHAIN_API_KEY')[:10])"
```

출력 예시:
```
LangSmith: lsv2_pt_xx
```

---

## 🎯 Master Workflow 실행 및 시각화

### 방법 1: Python 스크립트로 실행 (추천)

```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/test_master_workflow.py
```

**자동으로 LangSmith에 트레이싱됩니다!**

### 방법 2: Scrapy Spider 실행

```bash
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run scrapy crawl yonhap -a target_date=2025-11-07 -a category=economy
```

UC1 → UC2 자동 트리거가 발생하면 LangSmith에서 확인 가능!

---

## 🖥️ LangSmith UI에서 워크플로우 확인

### 1. LangSmith 접속

https://smith.langchain.com 접속 후 로그인

### 2. 프로젝트 선택

왼쪽 사이드바에서 **Projects** → `crawlagent-poc` 선택

### 3. Traces 확인

**Traces** 탭에서 최근 실행 목록 확인:

```
master_crawl_workflow
  ├─ supervisor_node
  ├─ uc1_validation_node
  │   └─ create_uc1_validation_agent
  │       └─ GPT-4o-mini (LLM Call)
  ├─ supervisor_node
  └─ END
```

### 4. 각 Trace 클릭하여 상세 확인

**볼 수 있는 정보**:

#### 📊 Trace Overview
- 전체 실행 시간
- 사용한 Token 수
- 비용 ($)
- Success/Failure 상태

#### 🔍 Step-by-Step Execution
- 각 노드의 Input/Output
- State 변화 과정
- LLM Prompt & Response
- 각 단계별 실행 시간

#### 🌲 Execution Tree (가장 중요!)
```
master_crawl_workflow (2.5s)
├─ supervisor_node (0.1s)
│   Input: {current_uc: null, ...}
│   Output: Command(goto="uc1_validation")
│
├─ uc1_validation_node (2.0s)
│   ├─ create_uc1_validation_agent (1.8s)
│   │   └─ gpt_quality_check (1.5s)
│   │       ├─ Prompt: "Analyze the following..."
│   │       └─ Response: {...}
│   │
│   Input: {url: "...", html_content: "..."}
│   Output: Command({uc1_result: {...}}, goto="supervisor")
│
├─ supervisor_node (0.1s)
│   Input: {uc1_result: {quality_passed: true}}
│   Output: Command(goto=END)
│
└─ END
```

#### 📈 Metrics
- Latency: 각 노드별 실행 시간
- Token Usage: GPT/Gemini/Claude 사용량
- Cost: 총 비용 ($)

---

## 🎨 LangSmith UI 주요 기능

### 1. Trace Timeline

시간 순서대로 모든 실행 단계 표시:

```
0.0s  → supervisor_node started
0.1s  → uc1_validation_node started
1.9s  → GPT-4o-mini called
2.0s  → uc1_validation_node completed
2.1s  → supervisor_node started
2.2s  → END
```

### 2. State Viewer

각 노드의 Input/Output State를 JSON 형태로 표시:

```json
{
  "url": "https://...",
  "current_uc": "uc1",
  "uc1_validation_result": {
    "quality_passed": true,
    "gpt_analysis": {...}
  },
  "workflow_history": [
    "supervisor → uc1_validation",
    "uc1_validation → supervisor (passed=True)",
    "supervisor → END"
  ]
}
```

### 3. LLM Call Viewer

GPT/Gemini/Claude 호출 상세 정보:

```
Model: gpt-4o-mini
Temperature: 0.3
Max Tokens: 2000

Prompt:
  You are a quality validation expert...
  [HTML Sample]

Response:
  {
    "quality_passed": true,
    "reasoning": "..."
  }

Tokens: 1500 input + 200 output = 1700 total
Cost: $0.0017
Latency: 1.2s
```

### 4. Error Debugging

실패한 Trace는 빨간색으로 표시:

```
❌ master_crawl_workflow (FAILED)
├─ supervisor_node ✅
├─ uc1_validation_node ✅
├─ supervisor_node ✅
└─ uc2_self_heal_node ❌
    └─ Error: GEMINI_API_KEY not found
        File: uc2_hitl.py:411
        Line: genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
```

---

## 🔧 고급 기능

### 1. Filtering

Trace 목록에서 필터링:

- **Status**: Success / Error / Pending
- **Model**: gpt-4o-mini / gemini-2.0-flash / claude-sonnet-4.5
- **Duration**: > 2s / < 1s
- **Date Range**: Last 24h / Last 7 days

### 2. Comparison

여러 Trace를 비교:

```
Run 1 (UC1 성공):     2.5s, $0.003, 1700 tokens
Run 2 (UC1→UC2):      8.2s, $0.012, 5200 tokens
Run 3 (UC2 합의 실패): 12.1s, $0.018, 7800 tokens
```

### 3. Annotations

Trace에 메모 추가:

```
💬 "이 실행에서 UC2 합의 점수가 0.75였음.
   임계값을 0.7로 낮추면 자동 승인 가능할 듯."
```

### 4. Sharing

Trace URL 공유:

```
https://smith.langchain.com/o/abc123/projects/p/def456/r/ghi789
```

팀원에게 공유하여 디버깅 협업 가능!

---

## 📊 Dashboard & Analytics

### 1. Overview Dashboard

프로젝트 전체 통계:

- **Total Runs**: 152
- **Success Rate**: 87%
- **Avg Latency**: 3.2s
- **Total Cost**: $2.45

### 2. Time Series Graph

시간별 실행 추이:

```
Runs per Hour:
12pm  ████████ 8
1pm   ████████████ 12
2pm   ████ 4
3pm   ████████████████ 16
```

### 3. Model Usage

LLM 모델별 사용량:

```
gpt-4o-mini:       120 calls (79%)
gemini-2.0-flash:  30 calls (20%)
claude-sonnet-4.5: 2 calls (1%)
```

### 4. Error Analysis

에러 유형별 분류:

```
GEMINI_API_KEY not found:  8 errors
Timeout exceeded:          3 errors
Rate limit exceeded:       1 error
```

---

## 🎯 PoC에서 LangSmith 활용 방법

### 시나리오 1: UC1 성공 확인

1. `test_master_workflow.py` 실행
2. LangSmith에서 `crawlagent-poc` 프로젝트 열기
3. 최신 Trace 클릭
4. Execution Tree에서 확인:
   ```
   supervisor → uc1_validation (✅) → supervisor → END
   ```

### 시나리오 2: UC1→UC2 자동 트리거 확인

1. `failure_count=3`으로 테스트 실행
2. LangSmith에서 Trace 확인:
   ```
   supervisor → uc1_validation (❌) → supervisor → uc2_self_heal
     ├─ gpt_propose_node
     ├─ gemini_validate_node
     └─ consensus_score: 0.85 (✅ Auto-approved)
   ```

### 시나리오 3: UC2 합의 실패 디버깅

1. LangSmith에서 실패한 UC2 Trace 찾기
2. `gemini_validate_node` 클릭
3. Gemini의 validation 결과 확인:
   ```json
   {
     "is_valid": false,
     "confidence": 0.45,
     "feedback": "CSS Selector가 너무 구체적임"
   }
   ```
4. GPT 제안과 비교하여 개선점 파악

---

## 🌐 현업 사용 사례

### Case 1: 스타트업 (5명)

**사용 방식**:
- 개발 중: LangSmith Tracing으로 실시간 디버깅
- 주간 회의: Dashboard로 성능 리뷰
- 비용 관리: Model별 사용량 모니터링

**효과**:
- 디버깅 시간 70% 감소
- LLM 비용 30% 절감 (불필요한 호출 발견)

### Case 2: 중견 기업 (50명)

**사용 방식**:
- Production: LangSmith Deployment로 24/7 모니터링
- Alert: Error rate > 5% 시 Slack 알림
- A/B Testing: Trace Comparison으로 성능 비교

**효과**:
- Production 장애 조기 발견
- A/B 테스트로 최적 프롬프트 발견

### Case 3: 대기업 (500명)

**사용 방식**:
- Self-hosted: AWS VPC 내부에 LangSmith 설치
- 팀별 프로젝트: 각 팀이 독립적으로 관리
- 통합 Dashboard: 전사 LLM 사용량 모니터링

**효과**:
- 데이터 보안 준수
- 전사 LLM 비용 최적화

---

## 🔐 보안 고려사항

### 1. API Key 관리

- ⚠️ `.env` 파일은 `.gitignore`에 추가
- 🔒 API Key는 절대 GitHub에 커밋 금지
- 👥 팀원별로 개별 API Key 발급

### 2. Sensitive Data

LangSmith에 업로드되는 데이터:

- ✅ 업로드됨: LLM Prompt, Response, State
- ✅ 업로드됨: 실행 시간, Token 사용량
- ⚠️ 주의: HTML 내용도 업로드됨

**민감 정보가 있다면**:
- Self-hosted LangSmith 사용 (AWS VPC)
- 또는 Tracing 비활성화 (`LANGCHAIN_TRACING_V2=false`)

---

## 📚 참고 자료

- **LangSmith 공식 문서**: https://docs.smith.langchain.com
- **LangGraph Tracing**: https://docs.langchain.com/langsmith/trace-with-langgraph
- **LangSmith Deployment**: https://docs.smith.langchain.com/langgraph_cloud
- **가격**: https://www.langchain.com/pricing (Beta 기간 무료)

---

## 🎓 요약

### LangSmith가 제공하는 것:

1. ✅ **워크플로우 GUI 시각화** (LangGraph Studio Desktop 대체)
2. ✅ **실시간 트레이싱** (각 노드 실행 추적)
3. ✅ **State 변화 확인** (디버깅 필수)
4. ✅ **LLM 호출 모니터링** (비용 최적화)
5. ✅ **Production 모니터링** (현업 표준)

### 설정 방법 (5분):

1. https://smith.langchain.com 계정 생성
2. API Key 복사
3. `.env`에 `LANGCHAIN_API_KEY` 설정
4. 워크플로우 실행
5. LangSmith UI에서 Trace 확인

### 현업에서 사용하는 이유:

- 개발: 실시간 디버깅
- 테스트: 성능 비교
- Production: 24/7 모니터링
- 협업: Trace 공유로 팀 디버깅

**이제 LangGraph Studio Desktop 없이도 완벽하게 워크플로우를 시각화할 수 있습니다!** 🎉
