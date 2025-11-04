# UC2 DOM Recovery Agent - Quick Start Guide

**작성일**: 2025-11-03
**버전**: 1.0

---

## 개요

이 문서는 UC2 DOM Recovery Agent 개발을 시작하기 위한 빠른 가이드입니다.
상세한 내용은 [UC2-DEVELOPMENT-MASTERPLAN.md](./UC2-DEVELOPMENT-MASTERPLAN.md)를 참조하세요.

---

## 핵심 의사결정 요약

### 13개 HITL 의사결정 포인트

| # | 카테고리 | 결정 | 이유 |
|---|----------|------|------|
| 1 | State 설계 | raw_html을 State에 포함 | PoC 단계, 간단한 구현 |
| 2 | HTML 전처리 | 주요 태그만 추출 (article, main) | 토큰 50-80% 절감 |
| 3 | Selector 후보 | 3개 생성 | PRD 준수 |
| 4 | GPT 모델 | gpt-4o | 정확도 우선 |
| 5 | 검증 방식 | 샘플 추출 검증 | PRD 준수, 효율적 |
| 6 | 검증 기준 | 80% + 규칙 기반 | 정량+정성 조합 |
| 7 | Gemini 모델 | gemini-2.0-flash-exp | PRD 준수, 무료 |
| 8 | 합의 조건 | 순차 검증, 첫 통과 선택 | 효율적 |
| 9 | 재시도 개선 | 실패 이유 Prompt 추가 | 학습 효과 |
| 10 | 버전 관리 | 덮어쓰기 + decision_logs | 간단, 복구 가능 |
| 11 | 자동 재실행 | UC1 자동 재크롤링 | Self-Healing 목표 |
| 12 | HITL UI | Gradio 탭 추가 | 데모용, 기존 UI 확장 |
| 13 | 테스트 | 고의 손상 + 신규 사이트 | UC2, UC3 모두 검증 |

---

## 3일 개발 일정

### Day 1 (6-7시간): GPT + Gemini 구현

**오전**:
- State 정의 (`RecoveryState`)
- HTML 전처리 유틸 (`src/utils/html_cleaner.py`)
- GPT-4o Analyzer (`src/agents/gpt_analyzer.py`)
  - Structured Output (Pydantic)
  - 3개 후보 생성
  - confidence, reasoning 포함

**오후**:
- Gemini Validator (`src/agents/gemini_validator.py`)
  - 샘플 추출 (10개)
  - 규칙 기반 1차 검증 (80%)
  - Gemini 2차 검증

**완료 기준**:
- 연합뉴스 HTML → 3개 Selector 후보 생성
- 1개 이상 Gemini 검증 통과

---

### Day 2 (3-4시간): Consensus + DB 업데이트

**오전**:
- Consensus Logic
- 재시도 로직 (Exponential Backoff)
- Prompt 개선 (실패 이유 피드백)

**오후**:
- DB 업데이트 Node
- 재크롤링 Node
- UC2 StateGraph 통합

**완료 기준**:
- `src/workflow/uc2_recovery.py` 완성
- Graph 컴파일 성공
- Dry-run 테스트 통과

---

### Day 3 (3-4시간): HITL + 통합 테스트

**오전**:
- HITL Node
- Gradio UI 확장 (3개 탭)
  - Pending Reviews
  - Review Details
  - Approve Selector

**오후**:
- End-to-End 테스트
  - 연합뉴스 Selector 손상 → 복구
  - 네이버 UC2 테스트
  - BBC UC2 테스트
- HITL 시나리오 테스트

**완료 기준**:
- 3개 사이트 UC2 복구 성공
- HITL UI 동작 확인
- decision_logs 저장 확인

---

## 핵심 코드 스니펫

### 1. State 정의

```python
# src/workflow/uc2_recovery.py

from typing import TypedDict, Optional, List, Dict, Any

class RecoveryState(TypedDict):
    # UC1에서 전달
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]
    quality_score: int
    missing_fields: List[str]
    
    # UC2 전용
    raw_html: str
    gpt_candidates: List[Dict[str, Any]]  # 3개 후보
    gemini_validation: Dict[str, Any]
    consensus_reached: bool
    retry_count: int
    max_retries: int
    selected_selector: Optional[Dict[str, str]]
    error_log: List[str]
```

### 2. GPT-4o Analyzer

```python
# src/agents/gpt_analyzer.py

from openai import OpenAI
from pydantic import BaseModel

class SelectorCandidate(BaseModel):
    title_selector: str
    body_selector: str
    date_selector: str
    confidence: float  # 0.0 ~ 1.0
    reasoning: str

class SelectorAnalysis(BaseModel):
    candidates: List[SelectorCandidate]  # 3개

def analyze_html_with_gpt(html: str, site_name: str) -> dict:
    client = OpenAI()
    response = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[...],
        response_format=SelectorAnalysis
    )
    return {"candidates": [...], "error": None}
```

### 3. Gemini Validator

```python
# src/agents/gemini_validator.py

import google.generativeai as genai

def validate_selector_with_gemini(raw_html: str, candidate: dict) -> dict:
    # 1. BeautifulSoup으로 샘플 추출
    soup = BeautifulSoup(raw_html, 'html.parser')
    title = soup.select_one(candidate["title_selector"])
    body_snippets = soup.select(candidate["body_selector"])[:10]
    
    # 2. 규칙 기반 1차 검증 (80% 기준)
    if len(body_snippets) < 8:
        return {"valid": False, "failure_reason": "Insufficient samples"}
    
    # 3. Gemini 2차 검증
    model = genai.GenerativeModel('gemini-2.0-flash-exp')
    response = model.generate_content(prompt)
    
    return {
        "valid": True/False,
        "validation_score": 0-100,
        "samples": [...],
        "gemini_reasoning": "..."
    }
```

### 4. StateGraph

```python
# src/workflow/uc2_recovery.py

def create_uc2_recovery_agent():
    builder = StateGraph(RecoveryState)
    
    builder.add_node("fetch_raw_html", fetch_raw_html)
    builder.add_node("gpt_analyzer", gpt_analyzer_node)
    builder.add_node("gemini_validator", gemini_validator_node)
    builder.add_node("save_selector", save_selector_node)
    builder.add_node("re_crawl", re_crawl_node)
    builder.add_node("retry", retry_node)
    builder.add_node("human_intervention", human_intervention_node)
    
    builder.add_edge(START, "fetch_raw_html")
    builder.add_edge("fetch_raw_html", "gpt_analyzer")
    builder.add_edge("gpt_analyzer", "gemini_validator")
    
    builder.add_conditional_edges(
        "gemini_validator",
        route_after_consensus,
        {
            "save_selector": "save_selector",
            "retry": "retry",
            "human_intervention": "human_intervention"
        }
    )
    
    return builder.compile()
```

---

## 테스트 명령어

```bash
# 1. 단위 테스트
pytest tests/test_gpt_analyzer.py -v
pytest tests/test_gemini_validator.py -v

# 2. 통합 테스트
pytest tests/test_uc2_integration.py -v

# 3. 수동 테스트 (Gradio UI)
python src/ui/app.py

# 4. End-to-End 테스트 (CLI)
python scripts/test_uc2_end_to_end.py
```

---

## 리스크 대응

### 비용 초과
- GPT-4o → gpt-4o-mini 전환
- HTML 전처리로 토큰 절감

### Gemini 장애
- Exponential Backoff
- 규칙 기반 Fallback

### 검증 실패율 높음
- 검증 기준 완화 (80% → 70%)
- GPT Prompt 개선

### GPT Hallucination
- Structured Output 강제
- Gemini 2차 검증
- HITL로 escalate

---

## 성공 기준

- [ ] GPT-4o로 3개 사이트 Selector 생성 성공
- [ ] Gemini 검증 통과율 ≥ 70%
- [ ] 연합뉴스 고의 손상 → 자동 복구 성공
- [ ] 신규 사이트 (UC3) Selector 생성 성공
- [ ] HITL UI 동작 확인
- [ ] decision_logs 저장 확인
- [ ] 재시도 로직 동작 확인 (3회 제한)
- [ ] End-to-End 테스트 통과

---

## 다음 단계

**Phase 1 시작**:
```bash
cd /Users/charlee/Desktop/Intern/crawlagent

# 1. 테스트 HTML 준비
curl https://www.yna.co.kr/view/AKR20251028095752073 > tests/fixtures/yonhap_sample.html

# 2. 파일 생성
touch src/utils/html_cleaner.py
touch src/agents/gpt_analyzer.py
touch tests/test_gpt_analyzer.py

# 3. API 키 확인
echo $OPENAI_API_KEY
echo $GOOGLE_API_KEY

# 4. 구현 시작!
```

**상세 가이드**: [UC2-DEVELOPMENT-MASTERPLAN.md](./UC2-DEVELOPMENT-MASTERPLAN.md)

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-11-03
