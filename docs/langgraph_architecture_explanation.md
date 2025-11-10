# CrawlAgent - LangGraph Multi-Agent Architecture 설명서

**작성일**: 2025-11-09
**목적**: LangGraph 공식 패턴 기반 Master Workflow 구현 설명

---

## 📋 목차

1. [개요](#개요)
2. [사용된 공식 LangGraph 패턴](#사용된-공식-langgraph-패턴)
3. [Master Graph 아키텍처](#master-graph-아키텍처)
4. [워크플로우 시나리오](#워크플로우-시나리오)
5. [LangGraph Studio 사용 방법](#langgraph-studio-사용-방법)
6. [코드 설명](#코드-설명)

---

## 개요

CrawlAgent는 **LangGraph Multi-Agent Orchestration** 패턴을 사용하여 웹 크롤러의 자동 복구(Self-Healing) 기능을 구현한 PoC 프로젝트입니다.

### 핵심 Use Cases

| Use Case | 설명 | LLM | 패턴 |
|----------|------|-----|------|
| **UC1: Quality Validation** | 크롤링 데이터 품질 검증 | GPT-4o-mini | Single Agent |
| **UC2: Self-Healing** | 2-Agent Consensus로 CSS Selector 자동 복구 | GPT + Gemini | Multi-Agent Consensus |
| **UC3: New Site Discovery** | 새로운 사이트 DOM 구조 분석 | Claude Sonnet 4.5 | Single Agent |

### PoC 범위

- LangGraph Multi-Agent 자동화 검증
- LangGraph Studio를 통한 워크플로우 시각화
- Gradio UI로 실행 결과 확인
- PostgreSQL DB에 로그 기록 (DecisionLog, CrawlResult 등)

**Production 범위 (PoC 제외)**:
- Slack 알림 연동
- FastAPI Webhook 서버
- 실시간 알림 시스템

---

## 사용된 공식 LangGraph 패턴

CrawlAgent는 3가지 **공식 LangGraph 패턴**을 사용하여 구현되었습니다.

### 1. Agent Supervisor Pattern (공식 패턴)

**출처**: [LangGraph Official Documentation - Agent Supervisor](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)

**설명**:
- Supervisor Agent가 여러 전문화된 Agent들에게 작업을 라우팅
- 조건부 분기(Conditional Branching)를 통한 동적 워크플로우 제어
- CrawlAgent에서는 `supervisor_node`가 UC1/UC2/UC3로 라우팅

**코드 예시**:
```python
def supervisor_node(state: MasterCrawlState) -> Command[...]:
    """
    Supervisor Agent: UC1/UC2/UC3 라우팅 결정
    """
    if not current_uc:
        # 최초 진입 → UC1
        return Command(goto="uc1_validation")

    if current_uc == "uc1" and failure_count >= 3:
        # UC1 3회 실패 → UC2 Self-Healing
        return Command(goto="uc2_self_heal")

    # ...
```

---

### 2. Conditional Edges (공식 API)

**출처**: [LangGraph Official API - add_conditional_edges](https://langchain-ai.github.io/langgraph/reference/graphs/#langgraph.graph.StateGraph.add_conditional_edges)

**설명**:
- `add_conditional_edges()` 메서드로 State 기반 동적 라우팅
- UC2에서 이미 사용 중: 합의 점수에 따라 END/retry/human_review로 분기
- State의 `next_action` 값을 기반으로 다음 노드 결정

**코드 예시** (UC2):
```python
workflow.add_conditional_edges(
    "gemini_validate",
    route_after_validation,  # 라우팅 함수
    {
        "end": END,                    # 합의 성공 → 종료
        "retry": "gpt_propose",        # 재시도 → GPT 다시 실행
        "human_review": "human_review" # HITL 발동
    }
)
```

---

### 3. Command API (2025년 신규)

**출처**: [LangGraph Command API Documentation](https://langchain-ai.github.io/langgraph/how-tos/command/)

**설명**:
- **가장 최신 패턴** (2025년 1월 출시)
- `Command(update={...}, goto="node_name")` 객체로 State 업데이트 + 라우팅을 **동시에 수행**
- 기존 방식보다 더 직관적이고 명확한 멀티 에이전트 통신
- Master Graph에서 모든 노드가 Command API 사용

**코드 예시**:
```python
def supervisor_node(state: MasterCrawlState) -> Command[Literal["uc1_validation", "uc2_self_heal", "uc3_new_site", "__end__"]]:
    # State 업데이트 + 라우팅을 동시에 수행
    return Command(
        update={
            "current_uc": "uc2",
            "next_action": "uc2",
            "workflow_history": history + ["supervisor → uc2_self_heal"]
        },
        goto="uc2_self_heal"  # 다음 노드 명시
    )
```

**Command API의 장점**:
1. **Atomic Operation**: State 업데이트와 라우팅이 하나의 단위로 실행
2. **Type Safety**: `Literal` 타입으로 잘못된 노드 이름 방지
3. **명확성**: 다음 노드가 코드에서 명시적으로 보임

---

## Master Graph 아키텍처

### 그래프 구조

```
    START
      ↓
  supervisor (UC1/UC2/UC3 라우팅 결정)
      ↓
    ┌─────────────────┐
    │ uc1_validation  │ (Quality Check)
    │ uc2_self_heal   │ (2-Agent Consensus)
    │ uc3_new_site    │ (New Site Discovery)
    └─────────────────┘
      ↓
  supervisor (다음 액션 결정)
      ↓
    END
```

### State 정의

Master Graph는 `MasterCrawlState`를 사용하여 모든 UC의 결과를 통합 관리합니다.

```python
class MasterCrawlState(TypedDict):
    # 입력 데이터
    url: str
    site_name: str
    html_content: Optional[str]

    # 워크플로우 제어
    current_uc: Optional[Literal["uc1", "uc2", "uc3"]]
    next_action: Optional[Literal["uc1", "uc2", "uc3", "end"]]
    failure_count: int

    # UC1/UC2/UC3 결과
    uc1_validation_result: Optional[dict]
    uc2_consensus_result: Optional[dict]
    uc3_discovery_result: Optional[dict]

    # 최종 출력
    final_result: Optional[dict]
    error_message: Optional[str]
    workflow_history: list[str]  # 디버깅/모니터링용
```

---

## 워크플로우 시나리오

### 시나리오 1: UC1 성공 (정상 크롤링)

```
START
  → supervisor
  → uc1_validation (품질 검증 성공)
  → supervisor
  → END
```

**설명**:
- URL에서 HTML 크롤링 후 UC1 Quality Validation 실행
- GPT-4o-mini가 품질 검증 통과 (`quality_passed=True`)
- supervisor가 성공 확인 후 워크플로우 종료

---

### 시나리오 2: UC1 실패 → UC2 자동 트리거 (Self-Healing)

```
START
  → supervisor
  → uc1_validation (3회 연속 실패)
  → supervisor
  → uc2_self_heal (2-Agent Consensus)
  → supervisor
  → END
```

**설명**:
- UC1이 3회 연속 실패 (`failure_count >= 3`)
- supervisor가 UC2 Self-Healing 트리거
- **2-Agent Consensus** (GPT + Gemini)로 새로운 CSS Selector 제안
- 합의 성공 시 DB 저장 후 UC1 복귀
- 합의 실패 시 DecisionLog 생성 (PoC: 관리자가 DB 확인)

**UC2 내부 워크플로우** (Conditional Edges 사용):
```
gpt_propose (GPT-4o-mini)
  ↓
gemini_validate (Gemini-2.0-flash)
  ↓
┌───────────────────┐
│ Consensus Score   │
│ (Weighted 0-1.0)  │
└───────────────────┘
  ↓
  ├─ ≥0.8: END (자동 승인)
  ├─ ≥0.6: retry (조건부 승인)
  └─ <0.6: human_review (사람 검토 필요)
```

**Weighted Consensus Algorithm**:
```
consensus_score = (
    gpt_confidence * 0.3 +       # GPT 제안 신뢰도
    gemini_confidence * 0.3 +    # Gemini 검증 신뢰도
    extraction_quality * 0.4     # 실제 추출 품질
)
```

---

### 시나리오 3: 새로운 사이트 발견 시 UC3 트리거

```
START
  → supervisor
  → uc3_new_site (Claude Sonnet 4.5)
  → supervisor
  → END
```

**설명**:
- 새로운 사이트 URL 입력 시
- Claude Sonnet 4.5가 DOM 구조 분석하여 CSS Selector 자동 생성
- 신뢰도(`confidence`)가 높으면 DB에 저장

---

## LangGraph Studio 사용 방법

### 1. LangGraph Studio 실행

```bash
cd /Users/charlee/Desktop/Intern/crawlagent

# LangGraph Studio 실행 (Dev 모드)
poetry run langgraph dev
```

**실행 후 접속**:
- URL: http://localhost:8123
- LangGraph Studio UI가 브라우저에서 열립니다

---

### 2. 워크플로우 시각화 확인

LangGraph Studio에서 다음 4개의 그래프를 확인할 수 있습니다:

| Graph Name | 파일 경로 | 설명 |
|-----------|----------|------|
| `master_crawl` | `src/workflow/master_crawl_workflow.py` | **Master Graph** (UC1→UC2→UC3 통합) |
| `uc1_validation` | `src/workflow/uc1_validation.py` | UC1 Quality Validation |
| `uc2_self_heal` | `src/workflow/uc2_hitl.py` | UC2 Self-Healing (2-Agent Consensus) |
| `uc3_new_site` | `src/workflow/uc3_new_site.py` | UC3 New Site Discovery |

---

### 3. Master Graph 테스트 실행

LangGraph Studio UI에서:

1. **Graph 선택**: `master_crawl` 선택
2. **Input State 입력**:
```json
{
  "url": "https://www.yonhapnewstv.co.kr/news/MYH20251107014400038",
  "site_name": "yonhap",
  "html_content": null,
  "current_uc": null,
  "next_action": null,
  "failure_count": 0,
  "uc1_validation_result": null,
  "uc2_consensus_result": null,
  "uc3_discovery_result": null,
  "final_result": null,
  "error_message": null,
  "workflow_history": []
}
```
3. **Run** 버튼 클릭
4. **워크플로우 실행 과정 시각화**:
   - 각 노드의 실행 순서
   - State 변화 과정
   - supervisor의 라우팅 결정 과정

---

### 4. 워크플로우 히스토리 확인

실행 후 `workflow_history` 필드에서 전체 워크플로우 경로 확인:

```python
[
  "supervisor → uc1_validation",
  "uc1_validation → supervisor (passed=False)",
  "supervisor → uc2_self_heal (UC1 failed 3x)",
  "uc2_self_heal → supervisor (consensus=True, score=0.85)",
  "supervisor → uc1_validation (UC2 consensus 0.85)",
  "uc1_validation → supervisor (passed=True)",
  "supervisor → END (UC1 success)"
]
```

---

## 코드 설명

### supervisor_node (Agent Supervisor Pattern)

**역할**: UC1/UC2/UC3로 라우팅 결정

**라우팅 로직**:

```python
def supervisor_node(state: MasterCrawlState) -> Command[...]:
    # 1. 최초 진입 → UC1
    if not current_uc:
        return Command(update={...}, goto="uc1_validation")

    # 2. UC1 완료 후 판단
    if current_uc == "uc1":
        if uc1_result.get("quality_passed"):
            return Command(update={...}, goto=END)  # 성공
        elif failure_count >= 3:
            return Command(update={...}, goto="uc2_self_heal")  # UC2 트리거

    # 3. UC2 완료 후 판단
    if current_uc == "uc2":
        if uc2_result.get("consensus_reached"):
            return Command(update={...}, goto="uc1_validation")  # UC1 복귀
        else:
            return Command(update={...}, goto=END)  # 합의 실패 종료

    # 4. UC3 완료 후 → 종료
    if current_uc == "uc3":
        return Command(update={...}, goto=END)
```

---

### uc1_validation_node (Wrapper Node)

**역할**: 기존 UC1 워크플로우를 호출하여 품질 검증 수행

**패턴**: Command API로 결과 반환

```python
def uc1_validation_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    # 1. UC1 Graph 빌드
    uc1_graph = create_uc1_validation_agent()

    # 2. Master State → UC1 State 변환
    uc1_state: ValidationState = {
        "url": state["url"],
        "site_name": state["site_name"],
        "html_content": state.get("html_content"),
        # ...
    }

    # 3. UC1 워크플로우 실행
    uc1_result = uc1_graph.invoke(uc1_state)

    # 4. Command API로 결과 반환
    return Command(
        update={
            "uc1_validation_result": {
                "quality_passed": uc1_result.get("quality_passed"),
                "gpt_analysis": uc1_result.get("gpt_analysis"),
                # ...
            },
            "workflow_history": history + ["uc1_validation → supervisor"]
        },
        goto="supervisor"  # 항상 supervisor로 복귀
    )
```

---

### uc2_self_heal_node (2-Agent Consensus)

**역할**: GPT + Gemini의 2-Agent Consensus로 CSS Selector 자동 복구

**패턴**: Command API로 결과 반환

```python
def uc2_self_heal_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    # 1. UC2 Graph 빌드
    uc2_graph = build_uc2_graph()

    # 2. UC2 워크플로우 실행
    uc2_result = uc2_graph.invoke(uc2_state)

    # 3. Consensus Score 계산
    consensus_score = calculate_consensus_score(
        gpt_confidence,
        gemini_confidence,
        extraction_quality
    )

    # 4. Command API로 결과 반환
    return Command(
        update={
            "uc2_consensus_result": {
                "consensus_reached": consensus_reached,
                "consensus_score": consensus_score,
                # ...
            },
            "workflow_history": history + [f"uc2_self_heal → supervisor (score={consensus_score})"]
        },
        goto="supervisor"
    )
```

---

### build_master_graph (Graph 구성)

**패턴**: Agent Supervisor Pattern + Command API

```python
def build_master_graph():
    # 1. StateGraph 생성
    workflow = StateGraph(MasterCrawlState)

    # 2. Node 추가
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("uc1_validation", uc1_validation_node)
    workflow.add_node("uc2_self_heal", uc2_self_heal_node)
    workflow.add_node("uc3_new_site", uc3_new_site_node)

    # 3. Entry Point 설정
    workflow.set_entry_point("supervisor")

    # 4. Compile (Command API 사용 시 add_edge 불필요)
    app = workflow.compile()

    return app
```

**중요**: Command API를 사용하면 `add_edge()`가 불필요합니다.
각 노드의 `Command.goto`가 자동으로 라우팅을 처리합니다.

---

## 정리

### CrawlAgent가 사용하는 공식 LangGraph 패턴

| 패턴 | 사용 위치 | 역할 |
|------|----------|------|
| **Agent Supervisor Pattern** | Master Graph | Supervisor가 UC1/UC2/UC3 라우팅 |
| **Conditional Edges** | UC2 Graph | 합의 점수에 따라 END/retry/human_review 분기 |
| **Command API (2025 신규)** | Master Graph 모든 노드 | State 업데이트 + 라우팅 동시 수행 |

### 워크플로우 시각화

- **LangGraph Studio**: http://localhost:8123
- **Gradio UI**: 크롤링 결과 및 통계 확인
- **PostgreSQL DB**: 모든 로그 기록 (CrawlResult, DecisionLog, Selector 등)

### PoC vs Production

**PoC 범위 (현재 구현)**:
- LangGraph Multi-Agent 자동화 검증
- LangGraph Studio 워크플로우 시각화
- Gradio UI 결과 확인
- DB 로그 기록

**Production 범위 (PoC 제외)**:
- Slack 알림 연동
- FastAPI Webhook 서버
- 실시간 알림 시스템

---

## 참고 자료

- [LangGraph Official Documentation](https://langchain-ai.github.io/langgraph/)
- [Agent Supervisor Pattern](https://langchain-ai.github.io/langgraph/tutorials/multi_agent/agent_supervisor/)
- [Command API Documentation](https://langchain-ai.github.io/langgraph/how-tos/command/)
- [LangGraph GitHub Examples](https://github.com/langchain-ai/langgraph/tree/main/examples/multi_agent)
