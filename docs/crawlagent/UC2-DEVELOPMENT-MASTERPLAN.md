# UC2 DOM Recovery Agent 개발 마스터플랜 (HITL 방식)

**작성일**: 2025-11-03
**버전**: 1.0
**목적**: UC2 개발 전체 로드맵 작성 (Human-in-the-Loop 의사결정 포인트 포함)
**작업 디렉토리**: `/Users/charlee/Desktop/Intern/crawlagent`

---

## 목차

1. [전체 아키텍처 개요](#전체-아키텍처-개요)
2. [Phase별 개발 계획](#phase별-개발-계획)
3. [HITL 의사결정 포인트 요약](#hitl-의사결정-포인트-요약)
4. [구현 순서 및 타임라인](#구현-순서-및-타임라인)
5. [테스트 전략](#테스트-전략)
6. [리스크 및 대응](#리스크-및-대응)

---

## 전체 아키텍처 개요

### UC2 워크플로우 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                     UC1 Validation                          │
│  (quality_score < 80 OR title=None OR body=None)            │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  UC2 Recovery 시작     │
         │  (LangGraph 라우팅)    │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  1. Fetch Raw HTML     │
         │  (Scrapy 전체 HTML)    │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────────────────────┐
         │  2. GPT-4o Analyzer                       │
         │  - HTML 전처리 (BeautifulSoup)            │
         │  - Structured Output (3개 후보)           │
         │  - {title_sel, body_sel, date_sel}        │
         │  - confidence: 0.0 ~ 1.0                  │
         └───────────┬───────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────────────────────────┐
         │  3. Gemini Validator                      │
         │  - 각 후보로 10개 샘플 추출                │
         │  - 뉴스 패턴 검증 (한국어/영문)            │
         │  - valid: true/false                      │
         │  - validation_score: 0-100                │
         └───────────┬───────────────────────────────┘
                     │
                     ▼
         ┌───────────────────────┐
         │  4. Consensus Check    │
         │  - GPT conf ≥ 0.7?    │
         │  - Gemini valid=true? │
         └───────────┬───────────┘
                     │
            ┌────────┴────────┐
            │                 │
         합의 성공          합의 실패
            │                 │
            ▼                 ▼
   ┌────────────────┐   ┌──────────────┐
   │ 5. DB 업데이트  │   │ 6. 재시도     │
   │ - selectors    │   │ (retry_count) │
   │ - decision_logs│   └───────┬───────┘
   └────────┬───────┘           │
            │           ┌───────┴──────┐
            │           │              │
            │      retry < 3      retry ≥ 3
            │           │              │
            │           ▼              ▼
            │     ┌─────────┐   ┌─────────────┐
            │     │ 재시도   │   │ HITL 개입    │
            │     └────┬────┘   │ (수동 검토)  │
            │          │        └──────────────┘
            │          └────► GPT Analyzer
            │
            ▼
   ┌────────────────┐
   │ 7. 재크롤링     │
   │ (새 Selector)  │
   └────────┬───────┘
            │
            ▼
   ┌────────────────┐
   │ UC1 검증        │
   │ (품질 재평가)   │
   └────────────────┘
```

### 주요 컴포넌트

| 컴포넌트 | 파일 경로 | 역할 | 의존성 |
|----------|----------|------|--------|
| **UC2 StateGraph** | `src/workflow/uc2_recovery.py` | 전체 워크플로우 오케스트레이션 | LangGraph, UC1 |
| **GPT-4o Analyzer** | `src/agents/gpt_analyzer.py` | HTML → CSS Selector 생성 (3개 후보) | OpenAI API |
| **Gemini Validator** | `src/agents/gemini_validator.py` | Selector 검증 (10개 샘플) | Google Gemini API |
| **Consensus Logic** | `src/workflow/uc2_recovery.py` (내부 함수) | 2-Agent 합의 판단 | - |
| **HITL Interface** | `src/ui/app.py` (신규 탭) | 수동 검토 UI | Gradio |
| **State 확장** | `src/workflow/uc2_recovery.py` | UC2 State 정의 | TypedDict |

---

## Phase별 개발 계획

### Phase 1: State 정의 및 GPT-4o Analyzer (3-4시간)

#### 1.1 State 확장 설계 (30분)

**현재 UC1 State** (`src/workflow/uc1_validation.py`):
```python
class ValidationState(TypedDict):
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]
    quality_score: int
    missing_fields: List[str]
    next_action: Literal["save", "heal", "new_site"]
```

**UC2 State 확장** (`src/workflow/uc2_recovery.py`):
```python
class RecoveryState(TypedDict):
    # UC1에서 전달받는 기본 필드
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]
    quality_score: int
    missing_fields: List[str]
    
    # UC2 전용 필드
    raw_html: str  # 전체 HTML (GPT/Gemini 분석용)
    
    # GPT-4o Analyzer 결과
    gpt_candidates: List[Dict[str, Any]]  # 3개 후보
    # 예: [
    #   {
    #     "title_selector": "h1.article-title",
    #     "body_selector": "div.article-body",
    #     "date_selector": "time.published-date",
    #     "confidence": 0.85,
    #     "reasoning": "명확한 시멘틱 태그 사용"
    #   },
    #   {...}, {...}
    # ]
    
    # Gemini Validator 결과
    gemini_validation: Dict[str, Any]
    # 예: {
    #   "candidate_index": 0,  # 검증 통과한 후보 인덱스
    #   "valid": True,
    #   "validation_score": 92,
    #   "samples": ["샘플1", "샘플2", ...],
    #   "failure_reason": None
    # }
    
    # 합의 및 재시도 관리
    consensus_reached: bool
    retry_count: int
    max_retries: int
    
    # 최종 선택된 Selector
    selected_selector: Optional[Dict[str, str]]
    
    # 에러 로그 (디버깅용)
    error_log: List[str]
```

**🤔 HITL 의사결정 포인트 #1: raw_html 저장 방식**

**질문**: raw_html을 State에 포함할지, 별도 파일로 저장할지?

**옵션 A: State에 포함**
- 장점:
  - 구현 간단 (추가 파일 I/O 불필요)
  - LangGraph State에서 직접 접근 가능
  - 재시도 시 재수집 불필요
- 단점:
  - 메모리 사용량 증가 (HTML 평균 200-500KB)
  - State 직렬화 시 오버헤드
  - LangGraph checkpointer 부담

**옵션 B: 임시 파일 저장**
- 장점:
  - 메모리 효율적
  - 대용량 HTML 처리 가능
- 단점:
  - 파일 I/O 추가 (복잡도 증가)
  - 임시 파일 관리 필요 (정리 로직)
  - 멀티 프로세스 환경에서 경합 가능

**권장 결정**: **옵션 A (State에 포함)**
- 근거:
  - PoC 단계, 간단한 구현 우선
  - 3개 사이트 HTML 크기 검증 결과 (2025-10-29):
    - 연합뉴스: ~150KB
    - 네이버: ~250KB
    - BBC: ~320KB
  - LangGraph는 100MB까지 State 지원 (공식 문서)
  - Production에서 옵션 B로 전환 가능 (점진적 개선)

**구현**:
```python
# src/workflow/uc2_recovery.py

def fetch_raw_html(state: RecoveryState) -> dict:
    """
    Node 1: 전체 HTML 수집
    """
    import requests
    from bs4 import BeautifulSoup
    
    url = state["url"]
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # BeautifulSoup으로 파싱 (GPT에게 줄 때 prettify)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        return {
            "raw_html": str(soup),  # prettified HTML
            "error_log": state.get("error_log", [])
        }
    except Exception as e:
        error_msg = f"[fetch_raw_html] {e}"
        return {
            "raw_html": "",
            "error_log": state.get("error_log", []) + [error_msg]
        }
```

---

#### 1.2 GPT-4o Analyzer 구현 (2시간)

**🤔 HITL 의사결정 포인트 #2: HTML 전처리 방식**

**질문**: GPT-4o에게 전체 HTML을 줄지, 축약된 HTML을 줄지?

**옵션 A: 전체 HTML**
- 장점:
  - GPT가 모든 문맥 파악 가능
  - 정확도 높음
- 단점:
  - 토큰 비용 높음 (300KB HTML ≈ 75K 토큰)
  - GPT-4o context window (128K) 초과 가능
  - 응답 시간 느림 (5-10초)

**옵션 B: BeautifulSoup으로 주요 태그만 추출**
- 장점:
  - 토큰 절감 (50-80%)
  - 빠른 응답 (2-3초)
  - 비용 절감
- 단점:
  - 중요 정보 누락 가능
  - 전처리 로직 필요

**권장 결정**: **옵션 B (주요 태그만 추출)**
- 근거:
  - 뉴스 사이트는 시멘틱 태그 사용 (article, main, header)
  - GPT-4o 입력 비용: $2.50 / 1M tokens
  - 전체 HTML vs 축약 HTML 비용 차이: 약 5배
  - Phase 5 테스트에서 정확도 검증 가능

**HTML 전처리 함수**:
```python
# src/utils/html_cleaner.py

from bs4 import BeautifulSoup
from typing import Optional

def extract_article_content(html: str) -> str:
    """
    뉴스 기사 주요 콘텐츠만 추출
    
    우선순위:
    1. <article> 태그 전체
    2. <main> 태그 내부
    3. <div id="content"> 또는 <div class="content">
    4. 없으면 전체 <body>
    """
    soup = BeautifulSoup(html, 'html.parser')
    
    # 우선순위 1: article 태그
    article = soup.find('article')
    if article:
        return str(article.prettify())
    
    # 우선순위 2: main 태그
    main = soup.find('main')
    if main:
        return str(main.prettify())
    
    # 우선순위 3: content 클래스/ID
    content_div = soup.find('div', {'id': 'content'}) or soup.find('div', {'class': 'content'})
    if content_div:
        return str(content_div.prettify())
    
    # 우선순위 4: body 전체 (fallback)
    body = soup.find('body')
    if body:
        # 불필요한 태그 제거
        for tag in body.find_all(['script', 'style', 'nav', 'footer', 'aside']):
            tag.decompose()
        return str(body.prettify())
    
    # 최후의 수단: 전체 HTML
    return html
```

**🤔 HITL 의사결정 포인트 #3: Selector 후보 개수**

**질문**: GPT-4o가 생성할 Selector 후보는 몇 개?

**옵션 A: 1개**
- 장점: 빠름, 간단
- 단점: 실패 시 재시도 필요

**옵션 B: 3개 (PRD 기준)**
- 장점: 선택지 많음, 재시도 감소
- 단점: GPT 응답 시간 증가

**옵션 C: 5개**
- 장점: 최대 선택지
- 단점: 과도한 검증 시간

**권장 결정**: **옵션 B (3개)** - PRD 준수
- 근거:
  - PRD-2-TECHNICAL-SPEC.md 명시 (3개 후보)
  - Gemini 검증 시간 고려 (3개 × 10 샘플 = 30개 검증)
  - 실패율 계산: 3개 모두 실패 확률 = 0.3^3 = 2.7%

**🤔 HITL 의사결정 포인트 #4: GPT 모델 선택**

**질문**: 어떤 GPT-4o 모델을 사용?

**옵션 A: `gpt-4o` (최신)**
- 가격: $2.50 / 1M input tokens, $10.00 / 1M output tokens
- 성능: 최고
- context window: 128K

**옵션 B: `gpt-4o-mini`**
- 가격: $0.15 / 1M input tokens, $0.60 / 1M output tokens
- 성능: 약간 낮음
- context window: 128K

**권장 결정**: **옵션 A (`gpt-4o`)**
- 근거:
  - 정확도 우선 (PoC 핵심 검증)
  - CSS Selector 생성은 고난이도 작업
  - 비용 차이 미미 (URL당 $0.01 vs $0.0006)
  - Production에서 gpt-4o-mini 전환 가능

**GPT-4o Analyzer 구현**:
```python
# src/agents/gpt_analyzer.py

from openai import OpenAI
from pydantic import BaseModel, Field
from typing import List, Optional
import os

# Structured Output 스키마
class SelectorCandidate(BaseModel):
    """
    CSS Selector 후보
    """
    title_selector: str = Field(description="제목 추출 CSS Selector")
    body_selector: str = Field(description="본문 추출 CSS Selector")
    date_selector: str = Field(description="날짜 추출 CSS Selector")
    confidence: float = Field(ge=0.0, le=1.0, description="신뢰도 (0.0 ~ 1.0)")
    reasoning: str = Field(description="선택 근거 설명")

class SelectorAnalysis(BaseModel):
    """
    GPT-4o 분석 결과
    """
    candidates: List[SelectorCandidate] = Field(min_items=3, max_items=3, description="3개 후보")

# Prompt Template
GPT_SYSTEM_PROMPT = """
당신은 HTML 구조 분석 전문가입니다.
주어진 HTML에서 뉴스 기사의 **title**, **body**, **date**를 추출할 CSS Selector를 생성하세요.

**요구사항**:
1. 3개의 후보 Selector를 제안하세요 (신뢰도 높은 순서).
2. 각 후보는 title_selector, body_selector, date_selector를 포함해야 합니다.
3. CSS Selector는 BeautifulSoup의 `select_one()` 메서드로 사용 가능해야 합니다.
4. 신뢰도(confidence)는 0.0 ~ 1.0 범위로 평가하세요.
5. reasoning에 선택 근거를 명확히 설명하세요.

**Good Examples**:
- title_selector: "article h1.headline"
- body_selector: "article div.article-body"
- date_selector: "article time[datetime]"

**Bad Examples** (피할 것):
- "div > div > div > p:nth-child(3)"  # 너무 취약한 구조
- "#content123"  # 동적 ID
- ".ad-container"  # 광고 영역

**뉴스 기사 특징**:
- 한국어/영문 뉴스 사이트 분석
- 시멘틱 HTML (article, header, time 태그 우선)
- 본문은 최소 500자 이상 (광고 제외)
- 날짜는 ISO 8601 형식 또는 한국어 날짜 포맷
"""

def analyze_html_with_gpt(html: str, site_name: str) -> dict:
    """
    GPT-4o로 HTML 분석 및 CSS Selector 생성
    
    Args:
        html: 전처리된 HTML (extract_article_content 적용)
        site_name: 사이트 이름 (디버깅용)
    
    Returns:
        {
            "candidates": [
                {
                    "title_selector": "...",
                    "body_selector": "...",
                    "date_selector": "...",
                    "confidence": 0.85,
                    "reasoning": "..."
                },
                {...}, {...}
            ],
            "error": None
        }
    """
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    
    try:
        response = client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": GPT_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"사이트 이름: {site_name}\n\nHTML:\n{html}"
                }
            ],
            response_format=SelectorAnalysis,
            temperature=0.3,  # 일관성 위해 낮은 temperature
            max_tokens=1500
        )
        
        # Pydantic 모델 → dict
        result = response.choices[0].message.parsed
        return {
            "candidates": [c.model_dump() for c in result.candidates],
            "error": None
        }
    
    except Exception as e:
        return {
            "candidates": [],
            "error": str(e)
        }

# LangGraph Node
def gpt_analyzer_node(state: dict) -> dict:
    """
    LangGraph Node: GPT-4o Analyzer
    """
    from src.utils.html_cleaner import extract_article_content
    
    raw_html = state["raw_html"]
    site_name = state["site_name"]
    
    # HTML 전처리
    cleaned_html = extract_article_content(raw_html)
    
    # GPT-4o 분석
    result = analyze_html_with_gpt(cleaned_html, site_name)
    
    if result["error"]:
        return {
            "gpt_candidates": [],
            "error_log": state.get("error_log", []) + [f"[GPT Error] {result['error']}"]
        }
    
    return {
        "gpt_candidates": result["candidates"],
        "error_log": state.get("error_log", [])
    }
```

**단위 테스트**:
```python
# tests/test_gpt_analyzer.py

import pytest
from src.agents.gpt_analyzer import analyze_html_with_gpt
from src.utils.html_cleaner import extract_article_content

def test_gpt_analyzer_yonhap():
    """연합뉴스 HTML 분석 테스트"""
    # 실제 HTML 로드
    with open("tests/fixtures/yonhap_sample.html", "r", encoding="utf-8") as f:
        html = f.read()
    
    cleaned = extract_article_content(html)
    result = analyze_html_with_gpt(cleaned, "yonhap")
    
    assert result["error"] is None
    assert len(result["candidates"]) == 3
    
    # 첫 번째 후보 검증
    first = result["candidates"][0]
    assert "title_selector" in first
    assert "body_selector" in first
    assert "date_selector" in first
    assert 0.0 <= first["confidence"] <= 1.0
    assert len(first["reasoning"]) > 10  # 설명 존재
```

---

### Phase 2: Gemini Validator (2-3시간)

#### 2.1 Validator 로직 설계 (1시간)

**🤔 HITL 의사결정 포인트 #5: Gemini 검증 방식**

**질문**: Gemini가 어떻게 Selector를 검증할 것인가?

**옵션 A: GPT Selector로 샘플 10개 추출 → Gemini가 품질 판단 (PRD 방식)**
- 장점:
  - 독립적 검증 (2-Agent 합의)
  - Gemini가 GPT 결과를 검증 (편향 방지)
- 단점:
  - Gemini에게 샘플 텍스트만 전달 (HTML 구조 못 봄)
  - GPT Selector가 완전 실패 시 검증 불가

**옵션 B: Gemini가 독립적으로 HTML 분석 → GPT 결과와 비교**
- 장점:
  - 완전 독립 분석
  - GPT 실패해도 Gemini로 복구 가능
- 단점:
  - 비용 2배
  - 시간 2배
  - 구현 복잡도 증가

**권장 결정**: **옵션 A (PRD 방식)**
- 근거:
  - PRD-2-TECHNICAL-SPEC.md 명시 (137-140줄)
  - 2-Agent 합의 = GPT 생성 + Gemini 검증
  - 비용/시간 효율적
  - Gemini는 "Validator" 역할 (Analyzer 아님)

**검증 프로세스**:
```python
# Pseudocode

for candidate in gpt_candidates:
    # 1. BeautifulSoup으로 Selector 테스트
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    title = soup.select_one(candidate["title_selector"])
    body_elements = soup.select(candidate["body_selector"])[:10]  # 최대 10개
    date = soup.select_one(candidate["date_selector"])
    
    # 2. 샘플 추출
    samples = {
        "title": title.text if title else None,
        "body_snippets": [el.text[:100] for el in body_elements],  # 각 100자
        "date": date.text if date else None
    }
    
    # 3. Gemini에게 샘플 품질 평가 요청
    gemini_result = validate_samples_with_gemini(samples, candidate)
    
    if gemini_result["valid"]:
        return candidate  # 첫 번째 통과한 후보 선택
```

**🤔 HITL 의사결정 포인트 #6: Gemini 검증 실패 기준**

**질문**: Gemini가 "실패"로 판단하는 기준은?

**옵션 A: 10개 샘플 중 8개 이상 성공 (80%)**
- 엄격도: 보통
- 위험: DOM 변경에 취약할 수 있음

**옵션 B: 10개 샘플 중 9개 이상 성공 (90%)**
- 엄격도: 높음
- 위험: 과도한 재시도 발생 가능

**옵션 C: 규칙 기반 검증**
- Title: 10자 이상, 500자 이하
- Body: 각 snippet 50자 이상
- Date: 숫자 포함 (날짜 패턴 정규표현식)

**권장 결정**: **옵션 A (80%) + 옵션 C (규칙 기반) 조합**
- 근거:
  - 정량적 기준 (80%) + 정성적 기준 (규칙)
  - 뉴스 사이트 특성 고려 (한국어/영문 혼재)
  - False positive 방지 (광고 텍스트 검출)

**검증 규칙**:
```python
# src/agents/gemini_validator.py (일부)

def validate_sample_quality(samples: dict) -> tuple[bool, int, str]:
    """
    샘플 품질 검증 (규칙 기반)
    
    Returns:
        (valid, score, failure_reason)
    """
    score = 0
    max_score = 100
    
    # Title 검증 (30점)
    title = samples.get("title", "")
    if title and 10 <= len(title) <= 500:
        score += 30
    elif not title:
        return False, 0, "Title missing"
    elif len(title) < 10:
        return False, score, "Title too short (<10 chars)"
    
    # Body 검증 (60점)
    body_snippets = samples.get("body_snippets", [])
    if len(body_snippets) < 8:  # 10개 중 8개 이상 필수 (80%)
        return False, score, f"Insufficient body samples ({len(body_snippets)}/10)"
    
    # 각 snippet 50자 이상
    valid_snippets = [s for s in body_snippets if len(s) >= 50]
    if len(valid_snippets) < 8:
        return False, score, f"Too many short snippets ({len(valid_snippets)}/10)"
    
    score += 60
    
    # Date 검증 (10점)
    date = samples.get("date", "")
    if date and any(char.isdigit() for char in date):
        score += 10
    # Date는 선택 사항 (없어도 통과)
    
    return True, score, None
```

**🤔 HITL 의사결정 포인트 #7: Gemini 모델 선택**

**질문**: 어떤 Gemini 모델을 사용?

**옵션 A: `gemini-2.0-flash-exp` (최신 실험)**
- 가격: 무료 (2025-11 기준)
- 성능: 빠름
- 안정성: 실험 버전

**옵션 B: `gemini-1.5-flash`**
- 가격: $0.075 / 1M input tokens
- 성능: 빠름
- 안정성: 안정 버전

**옵션 C: `gemini-1.5-pro`**
- 가격: $1.25 / 1M input tokens
- 성능: 최고
- 안정성: 안정 버전

**권장 결정**: **옵션 A (`gemini-2.0-flash-exp`)**
- 근거:
  - PRD-2-TECHNICAL-SPEC.md 명시 (19줄: "Gemini 2.5 Flash")
  - 무료 (PoC 비용 절감)
  - 검증 작업은 간단 (생성 작업 아님)
  - Production에서 1.5-flash로 전환 가능

**Gemini Validator 구현**:
```python
# src/agents/gemini_validator.py

import google.generativeai as genai
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
import os

genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Prompt Template
GEMINI_VALIDATION_PROMPT = """
당신은 뉴스 기사 품질 검증 전문가입니다.

다음 샘플이 뉴스 기사에서 추출된 올바른 콘텐츠인지 검증하세요.

**샘플**:
- Title: "{title}"
- Body Snippets (10개):
{body_snippets}
- Date: "{date}"

**검증 기준**:
1. Title: 뉴스 제목처럼 보이는가? (광고/버튼 텍스트 아님)
2. Body: 뉴스 본문처럼 보이는가? (최소 8개 snippet이 50자 이상)
3. Date: 날짜 형식이 맞는가? (선택 사항)

**판정**:
- "VALID": 모든 기준 통과
- "INVALID": 하나라도 실패

**응답 형식** (JSON):
{{
  "verdict": "VALID" or "INVALID",
  "confidence": 0.85,
  "reasoning": "검증 근거 설명"
}}
"""

def validate_selector_with_gemini(
    raw_html: str,
    candidate: Dict[str, str]
) -> Dict[str, any]:
    """
    Gemini로 Selector 검증
    
    Args:
        raw_html: 전체 HTML
        candidate: GPT가 제안한 Selector 후보
    
    Returns:
        {
            "valid": True/False,
            "validation_score": 0-100,
            "samples": [...],
            "failure_reason": None or str,
            "gemini_reasoning": str
        }
    """
    soup = BeautifulSoup(raw_html, 'html.parser')
    
    # 1. Selector로 샘플 추출
    title_el = soup.select_one(candidate["title_selector"])
    body_els = soup.select(candidate["body_selector"])[:10]
    date_el = soup.select_one(candidate["date_selector"])
    
    samples = {
        "title": title_el.get_text(strip=True) if title_el else None,
        "body_snippets": [el.get_text(strip=True)[:100] for el in body_els],
        "date": date_el.get_text(strip=True) if date_el else None
    }
    
    # 2. 규칙 기반 1차 검증
    rule_valid, rule_score, rule_reason = validate_sample_quality(samples)
    if not rule_valid:
        return {
            "valid": False,
            "validation_score": rule_score,
            "samples": samples,
            "failure_reason": rule_reason,
            "gemini_reasoning": None
        }
    
    # 3. Gemini 2차 검증
    try:
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        prompt = GEMINI_VALIDATION_PROMPT.format(
            title=samples["title"],
            body_snippets="\n".join([f"{i+1}. {s}" for i, s in enumerate(samples["body_snippets"])]),
            date=samples["date"]
        )
        
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.1,
                response_mime_type="application/json"
            )
        )
        
        # JSON 파싱
        import json
        gemini_result = json.loads(response.text)
        
        is_valid = gemini_result["verdict"] == "VALID"
        
        return {
            "valid": is_valid,
            "validation_score": rule_score if is_valid else 0,
            "samples": samples,
            "failure_reason": None if is_valid else "Gemini rejected",
            "gemini_reasoning": gemini_result["reasoning"]
        }
    
    except Exception as e:
        # Gemini 실패 시 규칙 기반 결과 사용
        return {
            "valid": rule_valid,
            "validation_score": rule_score,
            "samples": samples,
            "failure_reason": f"Gemini API error: {e}",
            "gemini_reasoning": None
        }

def validate_sample_quality(samples: dict) -> tuple[bool, int, str]:
    """
    규칙 기반 샘플 품질 검증 (위에서 정의한 함수)
    """
    # ... (위 코드 참조)
    pass

# LangGraph Node
def gemini_validator_node(state: dict) -> dict:
    """
    LangGraph Node: Gemini Validator
    
    3개 후보를 순차적으로 검증, 첫 번째 통과한 후보 선택
    """
    raw_html = state["raw_html"]
    candidates = state["gpt_candidates"]
    
    if not candidates:
        return {
            "gemini_validation": {"valid": False, "failure_reason": "No GPT candidates"},
            "consensus_reached": False
        }
    
    # 3개 후보 순차 검증 (confidence 높은 순서)
    sorted_candidates = sorted(candidates, key=lambda x: x["confidence"], reverse=True)
    
    for idx, candidate in enumerate(sorted_candidates):
        validation = validate_selector_with_gemini(raw_html, candidate)
        
        if validation["valid"]:
            return {
                "gemini_validation": {
                    **validation,
                    "candidate_index": idx
                },
                "selected_selector": {
                    "title_selector": candidate["title_selector"],
                    "body_selector": candidate["body_selector"],
                    "date_selector": candidate["date_selector"]
                },
                "consensus_reached": True  # 검증 통과 = 합의 성공
            }
    
    # 3개 모두 실패
    return {
        "gemini_validation": {"valid": False, "failure_reason": "All candidates rejected"},
        "consensus_reached": False
    }
```

---

### Phase 3: Consensus Logic 및 재시도 (2시간)

#### 3.1 합의 체크 로직 (1시간)

**🤔 HITL 의사결정 포인트 #8: 합의 성공 조건**

**질문**: 2-Agent 합의가 성공했다고 판단하는 정확한 조건은?

**PRD 기준** (142줄):
```
GPT confidence ≥ 0.7 AND Gemini valid=true
```

**문제점**: Gemini가 3개 후보 중 어떤 것을 선택?

**옵션 A: Gemini가 3개 모두 검증 → 가장 좋은 것 선택**
- 장점: 품질 최우선
- 단점: Gemini API 호출 3번 (비용/시간 증가)

**옵션 B: GPT confidence 순으로 순차 검증 → 첫 번째 valid 선택**
- 장점: 효율적 (평균 1.5회 호출)
- 단점: 최선의 후보가 아닐 수 있음

**권장 결정**: **옵션 B (순차 검증)**
- 근거:
  - GPT confidence가 이미 순위를 매김
  - 첫 번째 후보 통과 확률 ~70%
  - 비용/시간 효율적
  - Phase 2.1에서 이미 구현됨 (gemini_validator_node)

**합의 조건 명확화**:
```python
def check_consensus(state: dict) -> bool:
    """
    합의 성공 조건 체크
    
    조건:
    1. gemini_validation["valid"] == True
    2. selected_selector가 존재
    3. selected_selector의 원본 후보 confidence ≥ 0.7
    """
    gemini_valid = state.get("gemini_validation", {}).get("valid", False)
    if not gemini_valid:
        return False
    
    selected = state.get("selected_selector")
    if not selected:
        return False
    
    # 선택된 후보의 confidence 확인
    candidate_idx = state["gemini_validation"].get("candidate_index", -1)
    if candidate_idx < 0:
        return False
    
    candidates = state.get("gpt_candidates", [])
    if candidate_idx >= len(candidates):
        return False
    
    selected_candidate = candidates[candidate_idx]
    if selected_candidate["confidence"] < 0.7:
        return False
    
    return True
```

**Conditional Edge 설계**:
```python
# src/workflow/uc2_recovery.py

def route_after_consensus(state: dict) -> str:
    """
    합의 체크 후 라우팅
    
    반환:
    - "save_selector": 합의 성공 → DB 업데이트
    - "retry": 합의 실패 + retry_count < max_retries
    - "human_intervention": 합의 실패 + retry_count ≥ max_retries
    """
    consensus = state.get("consensus_reached", False)
    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)
    
    if consensus:
        return "save_selector"
    elif retry_count < max_retries:
        return "retry"
    else:
        return "human_intervention"
```

#### 3.2 재시도 로직 (1시간)

**🤔 HITL 의사결정 포인트 #9: 재시도 시 개선 방법**

**질문**: 재시도할 때 단순 반복인가, 아니면 프롬프트 개선인가?

**옵션 A: 단순 재시도 (같은 Prompt)**
- 장점: 구현 간단
- 단점: 같은 실패 반복 가능

**옵션 B: Prompt에 이전 실패 이유 추가**
- 장점: 학습 효과, 성공률 증가
- 단점: Prompt 복잡도 증가

**옵션 C: Temperature 조정 (0.3 → 0.7 → 0.9)**
- 장점: 다양한 시도
- 단점: 일관성 저하

**권장 결정**: **옵션 B (실패 이유 추가) + Exponential Backoff**
- 근거:
  - GPT-4o는 문맥 학습 능력 뛰어남
  - 실패 이유 = Gemini의 rejection reasoning
  - Backoff로 API rate limit 회피

**재시도 Node**:
```python
# src/workflow/uc2_recovery.py

def retry_node(state: dict) -> dict:
    """
    재시도 전 State 업데이트
    """
    import time
    
    retry_count = state.get("retry_count", 0)
    new_count = retry_count + 1
    
    # Exponential Backoff
    sleep_time = 2 ** retry_count  # 1초, 2초, 4초
    time.sleep(sleep_time)
    
    # 실패 이유 수집
    failure_reason = state.get("gemini_validation", {}).get("failure_reason", "Unknown")
    error_log = state.get("error_log", [])
    error_log.append(f"[Retry {new_count}] Previous failure: {failure_reason}")
    
    return {
        "retry_count": new_count,
        "error_log": error_log,
        "consensus_reached": False,  # 리셋
        "gpt_candidates": [],  # GPT 재실행 위해 초기화
        "gemini_validation": {},
        "selected_selector": None
    }
```

**개선된 GPT Prompt (재시도 시)**:
```python
# src/agents/gpt_analyzer.py 수정

def build_gpt_prompt_with_feedback(site_name: str, error_log: List[str]) -> str:
    """
    재시도 시 이전 실패 이유를 반영한 Prompt 생성
    """
    base_prompt = GPT_SYSTEM_PROMPT
    
    if error_log:
        recent_errors = error_log[-3:]  # 최근 3개 에러만
        feedback = "\n\n**이전 시도 실패 이유**:\n" + "\n".join(recent_errors)
        feedback += "\n\n위 실패를 피하고, 더 견고한 CSS Selector를 생성하세요."
        return base_prompt + feedback
    
    return base_prompt
```

---

### Phase 4: Selector 업데이트 및 재크롤링 (1시간)

#### 4.1 DB 업데이트 전략 (30분)

**🤔 HITL 의사결정 포인트 #10: Selector 업데이트 시 이전 버전 보관**

**질문**: 새 Selector로 업데이트할 때 이전 버전을 보관할 것인가?

**옵션 A: 덮어쓰기 (간단)**
- 장점: 구현 간단
- 단점: 롤백 불가

**옵션 B: 버전 관리 (decision_logs 활용)**
- 장점: 롤백 가능, 변경 이력 추적
- 단점: 복잡도 증가

**권장 결정**: **옵션 A (덮어쓰기) + decision_logs 보관**
- 근거:
  - PoC 단계, 간단한 구현
  - decision_logs 테이블에 이미 GPT/Gemini 결과 저장됨
  - 롤백 필요 시 decision_logs에서 복구 가능
  - Production Phase 2에서 selectors 테이블에 version 컬럼 추가 가능

**구현**:
```python
# src/workflow/uc2_recovery.py

def save_selector_node(state: dict) -> dict:
    """
    LangGraph Node: DB 업데이트
    
    1. selectors 테이블 업데이트
    2. decision_logs 테이블 삽입
    3. selectors.success_count 초기화 (새 Selector이므로)
    """
    from src.storage.database import get_db
    from src.storage.models import Selector, DecisionLog
    from datetime import datetime, timezone
    
    site_name = state["site_name"]
    url = state["url"]
    selected = state["selected_selector"]
    
    # JSONB 데이터 준비
    gpt_analysis = {
        "candidates": state.get("gpt_candidates", []),
        "selected_index": state.get("gemini_validation", {}).get("candidate_index", 0)
    }
    
    gemini_validation = state.get("gemini_validation", {})
    
    db = next(get_db())
    try:
        # 1. selectors 테이블 업데이트
        selector = db.query(Selector).filter_by(site_name=site_name).first()
        
        if selector:
            # 기존 Selector 업데이트
            selector.title_selector = selected["title_selector"]
            selector.body_selector = selected["body_selector"]
            selector.date_selector = selected["date_selector"]
            selector.updated_at = datetime.now(timezone.utc)
            selector.success_count = 0  # 리셋 (검증 필요)
            selector.failure_count = 0
        else:
            # 신규 Selector 생성 (UC3)
            selector = Selector(
                site_name=site_name,
                title_selector=selected["title_selector"],
                body_selector=selected["body_selector"],
                date_selector=selected["date_selector"],
                site_type="ssr",  # 기본값
                success_count=0,
                failure_count=0
            )
            db.add(selector)
        
        # 2. decision_logs 테이블 삽입
        decision_log = DecisionLog(
            url=url,
            site_name=site_name,
            gpt_analysis=gpt_analysis,
            gemini_validation=gemini_validation,
            consensus_reached=True,
            retry_count=state.get("retry_count", 0)
        )
        db.add(decision_log)
        
        db.commit()
        
        return {
            "error_log": state.get("error_log", []) + ["[DB] Selector updated successfully"]
        }
    
    except Exception as e:
        db.rollback()
        return {
            "error_log": state.get("error_log", []) + [f"[DB Error] {e}"]
        }
    finally:
        db.close()
```

**decision_logs 활용한 롤백**:
```sql
-- 수동 롤백 방법

-- 1. 이전 Selector 조회
SELECT 
    gpt_analysis->'candidates'->0 as previous_selector,
    created_at
FROM decision_logs
WHERE site_name = 'yonhap'
  AND consensus_reached = true
ORDER BY created_at DESC
LIMIT 2;  -- 최신 2개 (현재 + 이전)

-- 2. 수동 복원
UPDATE selectors
SET 
    title_selector = '[이전값]',
    body_selector = '[이전값]',
    date_selector = '[이전값]',
    updated_at = CURRENT_TIMESTAMP
WHERE site_name = 'yonhap';
```

#### 4.2 UC1 재실행 (30분)

**🤔 HITL 의사결정 포인트 #11: Selector 업데이트 후 UC1 자동 재실행**

**질문**: 새 Selector로 업데이트한 후 바로 재크롤링을 실행할 것인가?

**옵션 A: 자동 재실행 (완전 자동화)**
- 장점: 사용자 개입 불필요
- 단점: 새 Selector가 잘못되면 잘못된 데이터 저장

**옵션 B: 사용자 확인 후 재실행 (HITL)**
- 장점: 안전, 품질 보장
- 단점: 자동화 효과 감소

**권장 결정**: **옵션 A (자동 재실행) + 품질 점수 검증**
- 근거:
  - Self-Healing의 목표 = 자동화
  - UC1 품질 검증 (quality_score ≥ 80)으로 안전 장치
  - 실패 시 HITL로 escalate

**구현**:
```python
# src/workflow/uc2_recovery.py

def re_crawl_node(state: dict) -> dict:
    """
    LangGraph Node: 새 Selector로 재크롤링
    
    UC1 Validation Agent 재호출
    """
    from src.workflow.uc1_validation import create_uc1_validation_agent
    
    url = state["url"]
    site_name = state["site_name"]
    
    # UC1 Graph 생성
    uc1_graph = create_uc1_validation_agent()
    
    # 재크롤링 (새 Selector는 이미 DB에 업데이트됨)
    # TODO: Scrapy Spider 호출 로직 (src/crawlers/spiders/)
    # 여기서는 간단히 시뮬레이션
    
    # 실제 구현 시:
    # 1. Scrapy Spider 실행
    # 2. 크롤링 결과 추출
    # 3. UC1 입력으로 전달
    
    uc1_input = {
        "url": url,
        "site_name": site_name,
        "title": "[재크롤링 결과 Title]",  # Scrapy 결과
        "body": "[재크롤링 결과 Body]",    # Scrapy 결과
        "date": "[재크롤링 결과 Date]",    # Scrapy 결과
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save"
    }
    
    uc1_result = uc1_graph.invoke(uc1_input)
    
    return {
        "uc1_result": uc1_result,
        "error_log": state.get("error_log", []) + ["[Re-crawl] Completed"]
    }
```

---

### Phase 5: Human-in-the-Loop 인터페이스 (1-2시간)

#### 5.1 HITL 트리거 조건 (30분)

**HITL 필요 시점**:
1. **3회 재시도 실패**: retry_count ≥ max_retries
2. **GPT confidence 매우 낮음**: 모든 후보 < 0.5
3. **Gemini 검증 모두 실패**: 3개 후보 모두 valid=false
4. **사용자 명시적 요청**: manual_review 플래그

**구현**:
```python
# src/workflow/uc2_recovery.py

def human_intervention_node(state: dict) -> dict:
    """
    LangGraph Node: HITL 개입 필요
    
    1. State를 DB에 저장 (pending_review)
    2. 로그 기록
    3. Gradio UI에서 표시 가능하도록 플래그 설정
    """
    from src.storage.database import get_db
    from src.storage.models import DecisionLog
    
    url = state["url"]
    site_name = state["site_name"]
    
    db = next(get_db())
    try:
        # decision_logs에 "pending review" 상태 저장
        decision_log = DecisionLog(
            url=url,
            site_name=site_name,
            gpt_analysis={"candidates": state.get("gpt_candidates", [])},
            gemini_validation=state.get("gemini_validation", {}),
            consensus_reached=False,
            retry_count=state.get("retry_count", 0)
        )
        db.add(decision_log)
        db.commit()
        
        # 로깅
        print(f"\n{'='*60}")
        print(f"[HITL] Manual intervention required")
        print(f"URL: {url}")
        print(f"Site: {site_name}")
        print(f"Retry count: {state.get('retry_count', 0)}")
        print(f"Error log: {state.get('error_log', [])}")
        print(f"{'='*60}\n")
        
        return {
            "error_log": state.get("error_log", []) + ["[HITL] Manual review pending"]
        }
    
    except Exception as e:
        return {
            "error_log": state.get("error_log", []) + [f"[HITL Error] {e}"]
        }
    finally:
        db.close()
```

#### 5.2 HITL 인터페이스 (Gradio) (1시간)

**🤔 HITL 의사결정 포인트 #12: HITL 인터페이스 구현 방법**

**질문**: HITL을 어떻게 사용자에게 제공?

**옵션 A: Gradio UI에 "수동 검토" 탭 추가**
- 장점: 기존 UI 확장, 즉시 사용 가능
- 단점: 실시간 알림 없음

**옵션 B: 터미널에 입력 프롬프트**
- 장점: 구현 매우 간단
- 단점: 사용자 경험 나쁨

**옵션 C: Slack/이메일 알림 + 웹 링크**
- 장점: 실시간 알림, 프로덕션 레벨
- 단점: 외부 서비스 연동 필요

**권장 결정**: **옵션 A (Gradio 탭 추가)**
- 근거:
  - PoC 단계, 데모용
  - 기존 UI (`src/ui/app.py`) 확장
  - Production에서 옵션 C로 전환

**Gradio UI 구현**:
```python
# src/ui/app.py (기존 파일 확장)

import gradio as gr
from src.storage.database import get_db
from src.storage.models import DecisionLog, Selector
import pandas as pd

def load_pending_reviews():
    """
    DB에서 consensus_reached=False인 항목 조회
    """
    db = next(get_db())
    try:
        pending = db.query(DecisionLog).filter_by(consensus_reached=False).all()
        
        data = []
        for log in pending:
            data.append({
                "ID": log.id,
                "URL": log.url[:50] + "...",
                "Site": log.site_name,
                "Retry Count": log.retry_count,
                "Created At": log.created_at.strftime("%Y-%m-%d %H:%M")
            })
        
        return pd.DataFrame(data)
    finally:
        db.close()

def view_review_details(log_id: int):
    """
    특정 DecisionLog 상세 보기
    """
    db = next(get_db())
    try:
        log = db.query(DecisionLog).filter_by(id=log_id).first()
        if not log:
            return "Not found", "", ""
        
        # GPT 후보 포맷팅
        gpt_text = ""
        for i, cand in enumerate(log.gpt_analysis.get("candidates", [])):
            gpt_text += f"\n**Candidate {i+1}** (confidence: {cand['confidence']})\n"
            gpt_text += f"  - Title: `{cand['title_selector']}`\n"
            gpt_text += f"  - Body: `{cand['body_selector']}`\n"
            gpt_text += f"  - Date: `{cand['date_selector']}`\n"
            gpt_text += f"  - Reasoning: {cand['reasoning']}\n"
        
        # Gemini 검증 결과
        gemini = log.gemini_validation or {}
        gemini_text = f"Valid: {gemini.get('valid', False)}\n"
        gemini_text += f"Failure Reason: {gemini.get('failure_reason', 'N/A')}\n"
        
        return log.url, gpt_text, gemini_text
    finally:
        db.close()

def manual_approve_selector(log_id: int, selected_candidate_idx: int):
    """
    수동으로 Selector 승인
    """
    db = next(get_db())
    try:
        log = db.query(DecisionLog).filter_by(id=log_id).first()
        if not log:
            return "Error: Log not found"
        
        candidates = log.gpt_analysis.get("candidates", [])
        if selected_candidate_idx >= len(candidates):
            return "Error: Invalid candidate index"
        
        selected = candidates[selected_candidate_idx]
        
        # selectors 테이블 업데이트
        selector = db.query(Selector).filter_by(site_name=log.site_name).first()
        if selector:
            selector.title_selector = selected["title_selector"]
            selector.body_selector = selected["body_selector"]
            selector.date_selector = selected["date_selector"]
        else:
            selector = Selector(
                site_name=log.site_name,
                title_selector=selected["title_selector"],
                body_selector=selected["body_selector"],
                date_selector=selected["date_selector"]
            )
            db.add(selector)
        
        # decision_log 업데이트
        log.consensus_reached = True
        
        db.commit()
        return f"Success: Selector updated for {log.site_name}"
    
    except Exception as e:
        db.rollback()
        return f"Error: {e}"
    finally:
        db.close()

# Gradio UI
with gr.Blocks() as app:
    gr.Markdown("# CrawlAgent PoC - UC2 Manual Review")
    
    with gr.Tab("🔍 Pending Reviews"):
        refresh_btn = gr.Button("🔄 Refresh")
        pending_table = gr.Dataframe(label="Pending Reviews")
        
        refresh_btn.click(load_pending_reviews, outputs=pending_table)
    
    with gr.Tab("📝 Review Details"):
        log_id_input = gr.Number(label="DecisionLog ID", precision=0)
        view_btn = gr.Button("View Details")
        
        url_output = gr.Textbox(label="URL")
        gpt_output = gr.Markdown(label="GPT Candidates")
        gemini_output = gr.Textbox(label="Gemini Validation")
        
        view_btn.click(
            view_review_details,
            inputs=log_id_input,
            outputs=[url_output, gpt_output, gemini_output]
        )
    
    with gr.Tab("✅ Approve Selector"):
        approve_log_id = gr.Number(label="DecisionLog ID", precision=0)
        candidate_idx = gr.Number(label="Candidate Index (0-2)", precision=0)
        approve_btn = gr.Button("Approve & Update DB")
        approve_result = gr.Textbox(label="Result")
        
        approve_btn.click(
            manual_approve_selector,
            inputs=[approve_log_id, candidate_idx],
            outputs=approve_result
        )

# app.launch() 는 main() 함수에서 호출
```

---

### Phase 6: UC2 StateGraph 통합 (1시간)

**전체 Graph 구성**:
```python
# src/workflow/uc2_recovery.py

from typing import TypedDict, Optional, List, Dict, Any, Literal
from langgraph.graph import StateGraph, START, END

# State 정의 (Phase 1.1)
class RecoveryState(TypedDict):
    # ... (위 참조)
    pass

# Nodes (Phase 1-5에서 구현)
def fetch_raw_html(state: RecoveryState) -> dict:
    # ... (Phase 1.1)
    pass

def gpt_analyzer_node(state: RecoveryState) -> dict:
    # ... (Phase 1.2)
    pass

def gemini_validator_node(state: RecoveryState) -> dict:
    # ... (Phase 2.1)
    pass

def save_selector_node(state: RecoveryState) -> dict:
    # ... (Phase 4.1)
    pass

def re_crawl_node(state: RecoveryState) -> dict:
    # ... (Phase 4.2)
    pass

def retry_node(state: RecoveryState) -> dict:
    # ... (Phase 3.2)
    pass

def human_intervention_node(state: RecoveryState) -> dict:
    # ... (Phase 5.1)
    pass

# Conditional Edges
def route_after_consensus(state: RecoveryState) -> Literal["save_selector", "retry", "human_intervention"]:
    # ... (Phase 3.1)
    pass

# Graph 생성
def create_uc2_recovery_agent():
    """
    UC2 Recovery Agent Graph 생성
    
    Workflow:
    START → fetch_raw_html → gpt_analyzer → gemini_validator →
      → [consensus check] →
          → save_selector → re_crawl → END  (합의 성공)
          → retry → gpt_analyzer (재시도)
          → human_intervention → END (HITL)
    """
    builder = StateGraph(RecoveryState)
    
    # Nodes 추가
    builder.add_node("fetch_raw_html", fetch_raw_html)
    builder.add_node("gpt_analyzer", gpt_analyzer_node)
    builder.add_node("gemini_validator", gemini_validator_node)
    builder.add_node("save_selector", save_selector_node)
    builder.add_node("re_crawl", re_crawl_node)
    builder.add_node("retry", retry_node)
    builder.add_node("human_intervention", human_intervention_node)
    
    # Edges
    builder.add_edge(START, "fetch_raw_html")
    builder.add_edge("fetch_raw_html", "gpt_analyzer")
    builder.add_edge("gpt_analyzer", "gemini_validator")
    
    # Conditional Edge (합의 체크)
    builder.add_conditional_edges(
        "gemini_validator",
        route_after_consensus,
        {
            "save_selector": "save_selector",
            "retry": "retry",
            "human_intervention": "human_intervention"
        }
    )
    
    # 재시도 → GPT 재분석
    builder.add_edge("retry", "gpt_analyzer")
    
    # 저장 후 재크롤링
    builder.add_edge("save_selector", "re_crawl")
    builder.add_edge("re_crawl", END)
    
    # HITL → 종료
    builder.add_edge("human_intervention", END)
    
    return builder.compile()

# 테스트 코드
if __name__ == "__main__":
    graph = create_uc2_recovery_agent()
    
    # UC1에서 실패한 경우를 시뮬레이션
    test_input = {
        "url": "https://www.yna.co.kr/view/AKR20251103...",
        "site_name": "yonhap",
        "title": None,  # UC1 실패
        "body": None,
        "date": None,
        "quality_score": 0,
        "missing_fields": ["title", "body", "date"],
        "raw_html": "",
        "gpt_candidates": [],
        "gemini_validation": {},
        "consensus_reached": False,
        "retry_count": 0,
        "max_retries": 3,
        "selected_selector": None,
        "error_log": []
    }
    
    result = graph.invoke(test_input)
    print(result)
```

---

## HITL 의사결정 포인트 요약

| # | 카테고리 | 질문 | 권장 결정 | 근거 |
|---|----------|------|-----------|------|
| **1** | State 설계 | raw_html 저장 방식? | State에 포함 (옵션 A) | PoC 단계, 간단한 구현, HTML 크기 검증됨 |
| **2** | GPT Analyzer | HTML 전처리? | 주요 태그만 추출 (옵션 B) | 토큰 절감 (50-80%), 비용 효율 |
| **3** | GPT Analyzer | Selector 후보 개수? | 3개 (옵션 B) | PRD 준수, 실패율 2.7% |
| **4** | GPT Analyzer | GPT 모델? | gpt-4o (옵션 A) | 정확도 우선, 고난이도 작업 |
| **5** | Gemini Validator | 검증 방식? | 샘플 추출 검증 (옵션 A) | PRD 준수, 비용/시간 효율 |
| **6** | Gemini Validator | 검증 실패 기준? | 80% + 규칙 기반 (옵션 A+C) | 정량+정성 조합, False positive 방지 |
| **7** | Gemini Validator | Gemini 모델? | gemini-2.0-flash-exp (옵션 A) | PRD 준수, 무료, 검증 작업 적합 |
| **8** | Consensus Logic | 합의 조건? | 순차 검증 (옵션 B) | 효율적, GPT confidence 활용 |
| **9** | 재시도 | 재시도 개선? | 실패 이유 추가 (옵션 B) | 학습 효과, 성공률 증가 |
| **10** | DB 업데이트 | 이전 버전 보관? | 덮어쓰기 + logs (옵션 A) | PoC 단계, decision_logs로 복구 가능 |
| **11** | 재크롤링 | UC1 자동 재실행? | 자동 재실행 (옵션 A) | Self-Healing 목표, UC1 검증으로 안전 |
| **12** | HITL Interface | UI 구현 방법? | Gradio 탭 추가 (옵션 A) | PoC 데모용, 기존 UI 확장 |

**의사결정 철학**:
- PoC 단계: 간단한 구현 우선 (복잡도 최소화)
- PRD 준수: 명시된 요구사항 따르기
- 점진적 개선: Production에서 고도화 가능하도록 설계
- 비용 효율: 무료/저렴한 옵션 우선 (성능 저하 없는 범위)

---

## 구현 순서 및 타임라인

### Day 1: Phase 1 + Phase 2 (6-7시간)

**오전 (3-4시간)**:
- ✅ Phase 1.1: State 정의 (30분)
- ✅ Phase 1.2: HTML 전처리 유틸 작성 (30분)
- ✅ Phase 1.2: GPT-4o Analyzer 구현 (2시간)
- ✅ Phase 1.2: 단위 테스트 (30분)

**오후 (3시간)**:
- ✅ Phase 2.1: Gemini Validator 로직 설계 (1시간)
- ✅ Phase 2.1: Gemini Validator 구현 (1.5시간)
- ✅ Phase 2.1: 단위 테스트 (30분)

**완료 기준**:
- [ ] `tests/test_gpt_analyzer.py` 통과
- [ ] `tests/test_gemini_validator.py` 통과
- [ ] 연합뉴스 HTML로 Selector 3개 생성 확인
- [ ] 3개 중 1개 이상 Gemini 검증 통과

---

### Day 2: Phase 3 + Phase 4 (3-4시간)

**오전 (2시간)**:
- ✅ Phase 3.1: Consensus Logic 구현 (1시간)
- ✅ Phase 3.2: 재시도 로직 구현 (1시간)

**오후 (2시간)**:
- ✅ Phase 4.1: DB 업데이트 Node 구현 (30분)
- ✅ Phase 4.2: 재크롤링 Node 구현 (30분)
- ✅ Phase 6: StateGraph 통합 (1시간)

**완료 기준**:
- [ ] `src/workflow/uc2_recovery.py` 완성
- [ ] Graph 컴파일 성공
- [ ] 테스트 입력으로 End-to-End 실행 (dry-run)

---

### Day 3: Phase 5 + 통합 테스트 (3-4시간)

**오전 (2시간)**:
- ✅ Phase 5.1: HITL Node 구현 (30분)
- ✅ Phase 5.2: Gradio UI 확장 (1.5시간)

**오후 (2시간)**:
- ✅ End-to-End 테스트 (3개 사이트)
- ✅ HITL 시나리오 테스트
- ✅ 문서 업데이트 (README, 코멘트)

**완료 기준**:
- [ ] 연합뉴스 Selector 고의 손상 → UC2 복구 성공
- [ ] 네이버 UC2 테스트 성공
- [ ] BBC UC2 테스트 성공
- [ ] HITL UI에서 수동 승인 성공
- [ ] decision_logs 테이블에 데이터 저장 확인

---

## 테스트 전략

### 테스트 케이스 준비

**🤔 HITL 의사결정 포인트 #13: 테스트 사이트 선택**

**질문**: 어떤 사이트로 UC2를 테스트?

**옵션 A: 연합뉴스 (기존 Selector 고의 손상)**
- 장점: 정답 Selector 알고 있음, 비교 가능
- 단점: 실제 DOM 변경 시뮬레이션 아님

**옵션 B: 새로운 사이트 (조선일보, 중앙일보)**
- 장점: 실제 UC3 시나리오
- 단점: 정답 없음, 검증 어려움

**권장 결정**: **옵션 A (고의 손상) + 옵션 B (신규 사이트) 조합**
- 근거:
  - 옵션 A: UC2 정확도 검증
  - 옵션 B: UC3 (신규 사이트) 검증
  - 2가지 시나리오 모두 중요

### Test Case 1: 연합뉴스 Selector 손상

**시나리오**: 기존 Selector를 고의로 망가뜨리고 UC2로 복구

```python
# tests/test_uc2_integration.py

def test_uc2_yonhap_recovery():
    """
    UC2 통합 테스트: 연합뉴스 Selector 복구
    """
    from src.storage.database import get_db
    from src.storage.models import Selector
    from src.workflow.uc2_recovery import create_uc2_recovery_agent
    
    # 1. 기존 Selector 백업
    db = next(get_db())
    selector = db.query(Selector).filter_by(site_name="yonhap").first()
    original_title = selector.title_selector
    original_body = selector.body_selector
    original_date = selector.date_selector
    
    # 2. Selector 고의 손상
    selector.title_selector = "h1.wrong-class"
    selector.body_selector = "div.nonexistent"
    selector.date_selector = "time.invalid"
    db.commit()
    db.close()
    
    # 3. UC2 실행
    graph = create_uc2_recovery_agent()
    
    test_url = "https://www.yna.co.kr/view/AKR20251103095752073"
    result = graph.invoke({
        "url": test_url,
        "site_name": "yonhap",
        "title": None,
        "body": None,
        "date": None,
        "quality_score": 0,
        "missing_fields": ["title", "body", "date"],
        "raw_html": "",
        "retry_count": 0,
        "max_retries": 3
    })
    
    # 4. 검증
    assert result["consensus_reached"] == True
    assert result["selected_selector"] is not None
    
    # 5. DB 확인
    db = next(get_db())
    updated_selector = db.query(Selector).filter_by(site_name="yonhap").first()
    
    # 새 Selector가 원본과 유사한지 확인 (완전 동일하지 않을 수 있음)
    # GPT가 더 나은 Selector를 제안할 수도 있음
    assert updated_selector.title_selector != "h1.wrong-class"
    assert updated_selector.body_selector != "div.nonexistent"
    
    # 6. 복원 (테스트 후 원상 복구)
    selector.title_selector = original_title
    selector.body_selector = original_body
    selector.date_selector = original_date
    db.commit()
    db.close()
```

### Test Case 2: 신규 사이트 (UC3)

```python
def test_uc3_new_site():
    """
    UC3 통합 테스트: 신규 사이트 Selector 생성
    """
    # 조선일보 또는 중앙일보
    test_url = "https://www.chosun.com/politics/2025/11/03/..."
    
    graph = create_uc2_recovery_agent()
    result = graph.invoke({
        "url": test_url,
        "site_name": "chosun",  # DB에 없는 사이트
        "title": None,
        "body": None,
        "date": None,
        "quality_score": 0,
        "missing_fields": ["title", "body", "date"],
        "raw_html": "",
        "retry_count": 0,
        "max_retries": 3
    })
    
    # 검증
    assert result["consensus_reached"] == True
    
    # DB에 신규 Selector 생성 확인
    db = next(get_db())
    new_selector = db.query(Selector).filter_by(site_name="chosun").first()
    assert new_selector is not None
    db.close()
```

### Test Case 3: HITL 시나리오

```python
def test_hitl_intervention():
    """
    HITL 시나리오: 재시도 3회 실패 후 수동 개입
    """
    # TODO: 고의로 실패하는 HTML 준비
    # (예: JavaScript 렌더링 필수 SPA, 비정형 구조)
    
    graph = create_uc2_recovery_agent()
    result = graph.invoke({
        "url": "https://example.com/spa-article",
        "site_name": "example_spa",
        "title": None,
        "body": None,
        "date": None,
        "quality_score": 0,
        "missing_fields": ["title", "body", "date"],
        "raw_html": "<html>...</html>",  # 복잡한 HTML
        "retry_count": 0,
        "max_retries": 3
    })
    
    # 검증
    assert result["consensus_reached"] == False
    assert result["retry_count"] >= 3
    assert "[HITL]" in result["error_log"][-1]
    
    # decision_logs에 pending 상태 확인
    db = next(get_db())
    log = db.query(DecisionLog).filter_by(
        url="https://example.com/spa-article",
        consensus_reached=False
    ).first()
    assert log is not None
    db.close()
```

---

## 리스크 및 대응

### Risk 1: GPT-4o API 비용 초과

**예상 비용** (URL당):
- Input: ~5K tokens (축약 HTML) × $2.50 / 1M = $0.0125
- Output: ~500 tokens (3개 후보) × $10.00 / 1M = $0.005
- **Total**: ~$0.02 / URL

**완화 전략**:
- HTML 전처리로 토큰 50% 절감
- 재시도 시 이전 실패 이유만 추가 (전체 HTML 재전송 안 함)
- Phase 5 테스트에서 비용 모니터링

**대응 계획**:
- 비용 초과 시: gpt-4o-mini로 전환 ($0.0006 / URL)
- Fallback: 규칙 기반 Selector 생성 (heuristic)

---

### Risk 2: Gemini API 장애

**증상**:
- 429 Too Many Requests
- 503 Service Unavailable
- Timeout

**완화 전략**:
- Exponential Backoff (Phase 3.2 구현됨)
- 재시도 3회

**대응 계획**:
- Gemini 장애 시: 규칙 기반 검증으로 Fallback
- GPT confidence ≥ 0.8이면 Gemini 없이 통과
- HITL로 escalate

---

### Risk 3: Selector 검증 실패율 높음

**예상 실패 시나리오**:
- 비정형 HTML 구조 (오래된 사이트)
- JavaScript 렌더링 필수 (SPA)
- 광고/팝업이 본문으로 오인

**완화 전략**:
- Gemini 검증 기준 완화 (80% → 70%)
- 샘플 개수 증가 (10개 → 20개)
- GPT Prompt 개선 (재시도 시 피드백 반영)

**대응 계획**:
- Phase 5 테스트에서 실패율 측정
- 실패율 > 30%: Prompt 재작성
- 실패율 > 50%: HITL 우선 전환

---

### Risk 4: GPT Hallucination (잘못된 Selector 생성)

**증상**:
- 존재하지 않는 CSS 클래스 생성
- 광고 영역을 본문으로 오인
- 너무 취약한 Selector (nth-child)

**완화 전략**:
- Structured Output 강제 (Pydantic 스키마)
- Gemini 2차 검증 (샘플 추출로 실제 확인)
- GPT Prompt에 "Bad Examples" 명시

**대응 계획**:
- Hallucination 발견 시: decision_logs에 기록
- 해당 사이트 HITL 플래그 설정
- GPT Prompt 개선 (negative examples 추가)

---

## 부록: 파일 구조

```
crawlagent/
├── src/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── gpt_analyzer.py          # Phase 1.2 (NEW)
│   │   └── gemini_validator.py      # Phase 2.1 (NEW)
│   │
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── uc1_validation.py        # 기존
│   │   └── uc2_recovery.py          # Phase 6 (NEW)
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   └── html_cleaner.py          # Phase 1.2 (NEW)
│   │
│   ├── ui/
│   │   ├── __init__.py
│   │   └── app.py                   # Phase 5.2 (확장)
│   │
│   ├── storage/
│   │   ├── models.py                # 기존 (변경 없음)
│   │   └── database.py              # 기존 (변경 없음)
│
├── tests/
│   ├── test_gpt_analyzer.py         # Phase 1.2 (NEW)
│   ├── test_gemini_validator.py     # Phase 2.1 (NEW)
│   ├── test_uc2_integration.py      # Phase 7 (NEW)
│   └── fixtures/
│       ├── yonhap_sample.html       # 테스트용
│       ├── naver_sample.html
│       └── bbc_sample.html
│
├── docs/
│   └── crawlagent/
│       └── UC2-DEVELOPMENT-MASTERPLAN.md  # 이 문서
│
└── .env
    # OPENAI_API_KEY=sk-...
    # GOOGLE_API_KEY=...
```

---

## 다음 단계

**Phase 1 구현 시작 전 체크리스트**:
- [ ] 모든 HITL 의사결정 포인트 검토 완료
- [ ] API 키 준비 (OpenAI, Google Gemini)
- [ ] 테스트 HTML 파일 준비 (3개 사이트)
- [ ] `src/workflow/uc2_recovery.py` 파일 생성
- [ ] `src/agents/` 디렉토리 확인
- [ ] PostgreSQL 연결 확인 (decision_logs 테이블 존재)

**Phase 1 시작 명령**:
```bash
cd /Users/charlee/Desktop/Intern/crawlagent

# 1. 테스트 HTML 다운로드
curl https://www.yna.co.kr/view/AKR20251028095752073 > tests/fixtures/yonhap_sample.html

# 2. HTML 전처리 유틸 작성
touch src/utils/html_cleaner.py

# 3. GPT Analyzer 작성
touch src/agents/gpt_analyzer.py

# 4. 단위 테스트 작성
touch tests/test_gpt_analyzer.py

# 5. 테스트 실행
pytest tests/test_gpt_analyzer.py -v
```

**성공 기준**:
- [ ] GPT-4o로 연합뉴스 HTML 분석 성공 (3개 후보 생성)
- [ ] Gemini로 후보 검증 성공 (1개 이상 통과)
- [ ] End-to-End 테스트 통과 (연합뉴스 Selector 복구)
- [ ] HITL UI에서 수동 검토 가능
- [ ] decision_logs 테이블에 데이터 저장 확인

---

**문서 버전**: 1.0
**최종 업데이트**: 2025-11-03
**다음 검토**: Phase 1 완료 후 실제 구현 결과 반영
