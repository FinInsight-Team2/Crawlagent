"""
CrawlAgent - UC2 HITL (Human-in-the-Loop) Workflow
Created: 2025-11-05

LangGraph를 사용한 2-Agent CSS Selector 합의 시스템:
- GPT-4o-mini: CSS Selector 제안 (Proposer)
- Gemini-2.0-flash: Selector 검증 (Validator)
- Human: 최종 승인/거부 (Decision Maker)

용어:
- State: 그래프 내 노드들이 공유하는 데이터 (TypedDict)
- Node: 그래프 내 작업 단위 (함수)
- Edge: 노드 간 연결 (조건부 분기 가능)
- StateGraph: 노드와 엣지로 구성된 그래프

아키텍처 설명:
==================
UC2는 "Multi-Agent Consensus + HITL" 패턴을 사용합니다.

1. GPT Propose Node (gpt_propose_node):
   - HTML을 분석해서 title, body, date의 CSS Selector 제안
   - confidence score와 reasoning 포함
   - 출력: gpt_proposal 추가된 State

2. Gemini Validate Node (gemini_validate_node):
   - GPT 제안을 실제 HTML에 적용하여 테스트
   - BeautifulSoup으로 CSS Selector 추출 시도
   - 추출 결과를 Gemini LLM에게 검증 요청
   - 출력: gemini_validation 추가된 State

3. 합의 메커니즘:
   - 2/3 필드 이상 추출 성공 → is_valid: true → 합의 성공
   - 합의 실패 시 최대 3회 재시도
   - 3회 실패 시 Human Review 요청

4. State 불변성 (Immutability):
   - 모든 Node는 state를 직접 수정하지 않음
   - spread operator (**state)로 새로운 dict 반환
   - 예: return {**state, "gpt_proposal": proposal}
"""

from typing import TypedDict, Optional, Literal
from typing_extensions import Annotated


# ============================================================================
# State Definition (LangGraph 공식 용어)
# ============================================================================

class HITLState(TypedDict):
    """
    UC2 HITL 워크플로우의 State 정의

    LangGraph에서 State는 모든 노드가 읽고 쓸 수 있는 공유 데이터입니다.
    각 노드는 State의 일부를 업데이트하며, 다음 노드로 전달됩니다.
    """

    # === 입력 데이터 ===
    url: str
    """크롤링 대상 URL"""

    site_name: str
    """사이트 이름 (예: 'bbc', 'cnn')"""

    html_content: Optional[str]
    """fetch한 HTML 원본"""

    # === GPT Agent 출력 ===
    gpt_proposal: Optional[dict]
    """
    GPT가 제안한 CSS Selector
    {
        "title_selector": "h1.article-title",
        "body_selector": "div.article-body",
        "date_selector": "time.published",
        "confidence": 0.95,
        "reasoning": "..."
    }
    """

    # === Gemini Agent 출력 ===
    gemini_validation: Optional[dict]
    """
    Gemini의 검증 결과
    {
        "is_valid": true,
        "confidence": 0.90,
        "feedback": "...",
        "suggested_changes": {...}
    }
    """

    # === 합의 결과 ===
    consensus_reached: bool
    """두 Agent가 합의에 도달했는지 여부"""

    retry_count: int
    """재시도 횟수 (최대 3회)"""

    # === 최종 출력 ===
    final_selectors: Optional[dict]
    """최종 합의된 CSS Selector"""

    error_message: Optional[str]
    """에러 발생 시 메시지"""

    # === 워크플로우 제어 ===
    next_action: Optional[Literal["validate", "retry", "human_review", "end"]]
    """다음에 실행할 액션 (conditional edge에서 사용)"""


# ============================================================================
# Node Functions (LangGraph 공식 용어)
# ============================================================================

import json
import os
from loguru import logger
from openai import OpenAI


def gpt_propose_node(state: HITLState) -> HITLState:
    """
    GPT-4o-mini가 CSS Selector를 제안하는 Node

    LangGraph Node 규칙:
    1. 입력: state (HITLState)
    2. 출력: 업데이트된 state (HITLState)
    3. state를 직접 수정하지 않고, 새로운 dict를 반환

    동작:
    - HTML을 분석해서 title, body, date의 CSS Selector 제안
    - confidence score와 reasoning 포함
    """
    logger.info(f"[GPT Propose Node] Starting for {state['url']}")

    try:
        # OpenAI 클라이언트 초기화
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

        # HTML 샘플 추출 (처음 5000자만 사용 - 토큰 절약)
        html_sample = state.get("html_content", "")[:5000]

        # GPT 프롬프트
        prompt = f"""
You are an expert web scraper. Analyze the following HTML and propose CSS selectors.

URL: {state['url']}
HTML Sample (first 5000 chars):
```html
{html_sample}
```

Task: Propose CSS selectors for:
1. Article title
2. Article body/content
3. Publication date

Return ONLY a JSON object with this structure:
{{
    "title_selector": "CSS selector",
    "body_selector": "CSS selector",
    "date_selector": "CSS selector",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""

        # GPT-4o-mini 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a CSS selector expert. Always return valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )

        # 결과 파싱
        proposal_text = response.choices[0].message.content
        proposal = json.loads(proposal_text)

        logger.info(f"[GPT Propose Node] Proposal generated with confidence {proposal.get('confidence', 0)}")

        # State 업데이트 (불변성 유지)
        return {
            **state,
            "gpt_proposal": proposal,
            "next_action": "validate"
        }

    except Exception as e:
        logger.error(f"[GPT Propose Node] Error: {e}")
        return {
            **state,
            "error_message": f"GPT proposal failed: {str(e)}",
            "next_action": "end"
        }


# ============================================================================
# Gemini Validator Node
# ============================================================================

import google.generativeai as genai
from bs4 import BeautifulSoup


def gemini_validate_node(state: HITLState) -> HITLState:
    """
    Gemini-2.0-flash가 GPT 제안을 검증하는 Node

    LangGraph Node 규칙:
    1. 입력: state (HITLState) - gpt_proposal 포함
    2. 출력: 업데이트된 state (HITLState) - gemini_validation 추가
    3. state를 직접 수정하지 않고, 새로운 dict를 반환

    검증 방법:
    1. GPT가 제안한 CSS Selector를 실제 HTML에 적용
    2. 데이터 추출 성공 여부 확인
    3. 추출된 데이터의 품질 평가
    4. Gemini LLM으로 최종 판단
    """
    logger.info(f"[Gemini Validate Node] Starting validation for {state['url']}")

    try:
        # 1. GPT 제안 가져오기
        gpt_proposal = state.get("gpt_proposal")
        if not gpt_proposal:
            raise ValueError("No GPT proposal found in state")

        # 2. CSS Selector로 실제 데이터 추출 시도
        html_content = state.get("html_content", "")
        soup = BeautifulSoup(html_content, 'html.parser')

        extracted_data = {}
        extraction_success = {}

        for field in ["title", "body", "date"]:
            selector_key = f"{field}_selector"
            selector = gpt_proposal.get(selector_key, "")

            try:
                # CSS Selector 적용
                elements = soup.select(selector)
                if elements:
                    # 첫 번째 요소의 텍스트 추출
                    text = elements[0].get_text(strip=True)
                    extracted_data[field] = text[:200]  # 처음 200자만
                    extraction_success[field] = True
                else:
                    extracted_data[field] = None
                    extraction_success[field] = False
            except Exception as e:
                logger.warning(f"[Gemini Validate] Extraction failed for {field}: {e}")
                extracted_data[field] = None
                extraction_success[field] = False

        # 3. Gemini에게 검증 요청
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel("gemini-2.0-flash-exp")

        validation_prompt = f"""
You are a web scraping validator. Evaluate the following CSS selector proposal.

URL: {state['url']}

GPT Proposal:
- Title Selector: {gpt_proposal.get('title_selector')}
- Body Selector: {gpt_proposal.get('body_selector')}
- Date Selector: {gpt_proposal.get('date_selector')}
- GPT Confidence: {gpt_proposal.get('confidence')}

Extraction Results:
- Title: {"SUCCESS" if extraction_success.get('title') else "FAILED"}
  Extracted: {(extracted_data.get('title') or 'N/A')[:100]}
- Body: {"SUCCESS" if extraction_success.get('body') else "FAILED"}
  Extracted: {(extracted_data.get('body') or 'N/A')[:100]}
- Date: {"SUCCESS" if extraction_success.get('date') else "FAILED"}
  Extracted: {(extracted_data.get('date') or 'N/A')[:100]}

Task: Validate whether these selectors are good quality.

Return ONLY a JSON object:
{{
    "is_valid": true/false,
    "confidence": 0.0-1.0,
    "feedback": "brief explanation",
    "suggested_changes": {{"field": "new selector or null"}}
}}

Criteria:
- is_valid: true if at least 2/3 fields extracted successfully
- confidence: based on extraction quality
- feedback: explain validation result
"""

        # Gemini 호출
        response = model.generate_content(
            validation_prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                response_mime_type="application/json"
            )
        )

        validation = json.loads(response.text)
        logger.info(f"[Gemini Validate Node] Validation: {validation.get('is_valid')} (confidence: {validation.get('confidence')})")

        # 4. 합의 여부 결정
        consensus_reached = validation.get("is_valid", False)

        # 5. next_action 결정
        if consensus_reached:
            next_action = "end"  # 합의 성공 → 종료
        else:
            retry_count = state.get("retry_count", 0)
            if retry_count < 3:
                next_action = "retry"  # 재시도
            else:
                next_action = "human_review"  # 사람 개입

        # 6. State 업데이트
        return {
            **state,
            "gemini_validation": validation,
            "consensus_reached": consensus_reached,
            "retry_count": retry_count + (0 if consensus_reached else 1),
            "final_selectors": gpt_proposal if consensus_reached else None,
            "next_action": next_action
        }

    except Exception as e:
        logger.error(f"[Gemini Validate Node] Error: {e}")
        return {
            **state,
            "error_message": f"Gemini validation failed: {str(e)}",
            "next_action": "end"
        }


# ============================================================================
# 다음 단계: StateGraph 구성
# ============================================================================

# TODO: build_uc2_graph() - StateGraph 생성 및 compile
# TODO: 테스트 스크립트 작성
