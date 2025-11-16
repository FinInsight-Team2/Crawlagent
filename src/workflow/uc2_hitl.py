"""
CrawlAgent - UC2 HITL (Human-in-the-Loop) Workflow
Created: 2025-11-05
Updated: 2025-11-14 (Gemini → GPT-4o 변경, Gemini rate limit 대응)

LangGraph를 사용한 2-Agent CSS Selector 합의 시스템:
- GPT-4o-mini: CSS Selector 제안 (Proposer)
- GPT-4o: Selector 검증 (Validator) - 이전 Gemini, rate limit으로 변경
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
   - Few-Shot Examples 참조 (DB의 성공 패턴)
   - HTML을 분석해서 title, body, date의 CSS Selector 제안
   - confidence score와 reasoning 포함
   - 출력: gpt_proposal 추가된 State

2. GPT-4o Validate Node (gemini_validate_node):
   - GPT 제안을 실제 HTML에 적용하여 테스트
   - BeautifulSoup으로 CSS Selector 추출 시도
   - 추출 결과를 GPT-4o LLM에게 검증 요청 (이전 Gemini)
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

from typing import Literal, Optional, TypedDict

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
    GPT-4o-mini가 CSS Selector를 제안하는 Node (Few-Shot Examples 포함)

    LangGraph Node 규칙:
    1. 입력: state (HITLState)
    2. 출력: 업데이트된 state (HITLState)
    3. state를 직접 수정하지 않고, 새로운 dict를 반환

    동작:
    - Few-Shot Examples 참조 (DB의 성공 패턴)
    - HTML을 분석해서 title, body, date의 CSS Selector 제안
    - confidence score와 reasoning 포함
    """
    logger.info(f"[GPT Propose Node] Starting for {state['url']}")

    # Few-Shot Retriever import
    import time

    from src.agents.few_shot_retriever import format_few_shot_prompt, get_few_shot_examples
    from src.exceptions import OpenAIAPIError, format_error_for_user, is_retryable_error

    # HTML 샘플 추출 (20000자로 증가)
    html_sample = state.get("html_content", "")[:20000]

    # Few-Shot Examples 가져오기
    few_shot_examples = get_few_shot_examples(limit=5)
    few_shot_section = ""
    if few_shot_examples and len(few_shot_examples) > 0:
        few_shot_section = "## Few-Shot Examples (성공한 뉴스 사이트 패턴)\n\n"
        few_shot_section += format_few_shot_prompt(few_shot_examples, include_patterns=True)
        few_shot_section += "\n"

    # GPT 프롬프트 (Few-Shot 포함)
    prompt = f"""
You are an expert web scraper. Analyze the following HTML and propose CSS selectors.

{few_shot_section}

URL: {state['url']}
HTML Sample (first 20000 chars):
```html
{html_sample}
```

Task: Propose CSS selectors for:
1. Article title
2. Article body/content
3. Publication date

Refer to the Few-Shot examples above for successful patterns.

Return ONLY a JSON object with this structure:
{{
    "title_selector": "CSS selector",
    "body_selector": "CSS selector",
    "date_selector": "CSS selector",
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation"
}}
"""

    # OpenAI API keys (primary + backup)
    api_keys = [os.getenv("OPENAI_API_KEY"), os.getenv("OPENAI_API_KEY_BACKUP_1")]
    api_keys = [key for key in api_keys if key]  # None 제거

    # Retry logic with fallback
    max_retries = 3
    last_error = None

    for key_idx, api_key in enumerate(api_keys):
        for attempt in range(max_retries):
            try:
                # OpenAI 클라이언트 초기화 (timeout 30초)
                client = OpenAI(api_key=api_key, timeout=30.0)

                # GPT-4o 호출 (v2.1: gpt-4o-mini → gpt-4o 업그레이드)
                # 비용: ~$0.01/call 증가, 정확도: +8-12% 예상
                response = client.chat.completions.create(
                    model="gpt-4o",  # v2.1: Upgraded from gpt-4o-mini
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a CSS selector expert. Always return valid JSON.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"},
                )

                # 결과 파싱
                proposal_text = response.choices[0].message.content
                proposal = json.loads(proposal_text)

                logger.info(
                    f"[GPT Propose Node] ✅ Success (key={key_idx+1}, attempt={attempt+1}, confidence={proposal.get('confidence', 0)})"
                )

                # State 업데이트 (불변성 유지)
                return {**state, "gpt_proposal": proposal, "next_action": "validate"}

            except Exception as raw_error:
                last_error = raw_error
                error = OpenAIAPIError.from_openai_error(raw_error)

                # Retry 가능한 오류인가? (429 Rate Limit, 503/504 Server Error)
                if is_retryable_error(error) and attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"[GPT Propose Node] ⚠️ Retryable error, waiting {wait_time}s (attempt {attempt+1}/{max_retries}): {error}"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    # 재시도 불가능하거나 마지막 시도 실패
                    logger.error(
                        f"[GPT Propose Node] ❌ Attempt {attempt+1} failed (key={key_idx+1}): {error}"
                    )
                    break  # 다음 API 키로

    # 모든 API 키와 재시도 실패
    user_message = format_error_for_user(
        OpenAIAPIError.from_openai_error(last_error) if last_error else Exception("Unknown error")
    )
    logger.error(f"[GPT Propose Node] ❌ All API keys exhausted. Last error: {user_message}")

    return {
        **state,
        "gpt_proposal": None,
        "error_message": f"GPT proposal failed: {user_message}",
        "next_action": "end",
    }


# ============================================================================
# Helper Functions for Quality Assessment (NEW! - Sprint 1)
# ============================================================================


def calculate_extraction_quality(extracted_data: dict, extraction_success: dict) -> float:
    """
    추출된 데이터의 실제 품질을 0.0~1.0 점수로 계산

    목적:
        단순 "성공/실패"가 아니라 "얼마나 좋은 데이터인지" 정량적으로 평가

    계산 방법:
        - title_quality * 0.3: 제목 품질 (10자 이상이면 1.0)
        - body_quality * 0.5: 본문 품질 (500자 이상이면 1.0, 100~500자면 0.6)
        - date_quality * 0.2: 날짜 품질 (추출 성공하면 1.0)

    Args:
        extracted_data: {"title": "...", "body": "...", "date": "..."}
        extraction_success: {"title": True, "body": True, "date": False}

    Returns:
        float: 0.0 ~ 1.0 (0.8 이상이면 고품질)

    Example:
        >>> extracted = {"title": "삼성전자 주가 급등", "body": "..."*600, "date": "2025-11-09"}
        >>> success = {"title": True, "body": True, "date": True}
        >>> calculate_extraction_quality(extracted, success)
        1.0  # 모든 필드가 고품질

        >>> extracted_poor = {"title": "짧음", "body": "너무 짧은 본문", "date": None}
        >>> success_poor = {"title": True, "body": True, "date": False}
        >>> calculate_extraction_quality(extracted_poor, success_poor)
        0.38  # 품질이 낮음
    """
    # 1. Title 품질 (0.0 ~ 1.0)
    title = extracted_data.get("title", "")
    title_success = extraction_success.get("title", False)

    if not title_success or not title:
        title_quality = 0.0
    elif len(title) >= 10:
        title_quality = 1.0  # 충분한 길이
    elif len(title) >= 5:
        title_quality = 0.7  # 짧지만 있음
    else:
        title_quality = 0.3  # 너무 짧음

    # 2. Body 품질 (0.0 ~ 1.0)
    body = extracted_data.get("body", "")
    body_success = extraction_success.get("body", False)

    if not body_success or not body:
        body_quality = 0.0
    elif len(body) >= 100:  # v2.1: 200 → 100자로 완화 (SPA/짧은 기사 지원)
        body_quality = 1.0  # 충분한 본문
    elif len(body) >= 50:  # v2.1: 0.4 → 0.6으로 상향 (부분 점수 개선)
        body_quality = 0.6  # 중간 길이 (이전 0.4)
    elif len(body) >= 20:  # v2.1: 새로 추가 (최소한의 본문)
        body_quality = 0.3  # 짧은 본문
    else:
        body_quality = 0.1  # 너무 짧음 (거의 실패)

    # 3. Date 품질 (0.0 ~ 1.0)
    date = extracted_data.get("date", "")
    date_success = extraction_success.get("date", False)

    if not date_success or not date:
        date_quality = 0.0
    else:
        # 날짜 형식 검증 (간단한 휴리스틱)
        # "2025-11-09", "2025.11.09", "11/09/2025" 등
        import re

        if re.search(r"\d{4}", date) and re.search(r"\d{1,2}", date):
            date_quality = 1.0  # 연도와 숫자가 포함되어 있으면 OK
        else:
            date_quality = 0.5  # 날짜 같지만 확실하지 않음

    # 4. Valid fields 카운트 (v2.1: 부분 성공 처리용)
    valid_fields = sum(
        [
            1 if title_quality >= 0.3 else 0,  # Title이 최소 기준 충족
            1 if body_quality >= 0.3 else 0,  # Body가 최소 기준 충족
            1 if date_quality >= 0.5 else 0,  # Date가 최소 기준 충족
        ]
    )

    # 5. 가중치 합산
    extraction_quality = title_quality * 0.3 + body_quality * 0.5 + date_quality * 0.2

    # v2.1: 부분 성공 보너스 (2/3 필드 성공 시 +0.05)
    if valid_fields == 2:
        extraction_quality = min(1.0, extraction_quality + 0.05)
        logger.info(f"[Extraction Quality] Partial success bonus: 2/3 fields valid (+0.05)")

    logger.debug(
        f"[Extraction Quality] title={title_quality:.2f}, "
        f"body={body_quality:.2f}, date={date_quality:.2f}, "
        f"valid_fields={valid_fields}/3 → total={extraction_quality:.2f}"
    )

    return round(extraction_quality, 2)


def calculate_consensus_score(
    gpt_confidence: float, gemini_confidence: float, extraction_quality: float
) -> float:
    """
    3가지 요소를 가중치 합산하여 최종 합의 점수 계산

    목적:
        GPT 제안 품질 + Gemini 검증 품질 + 실제 추출 결과를 모두 고려하여
        종합적인 합의 점수를 계산

    가중치:
        - gpt_confidence: 30% (GPT가 제안에 대해 얼마나 확신하는지)
        - gemini_confidence: 30% (Gemini가 검증에 대해 얼마나 확신하는지)
        - extraction_quality: 40% (실제 추출 결과가 얼마나 좋은지)

    판단 기준:
        - >= 0.8: 자동 승인 (High confidence)
        - >= 0.6: 조건부 승인 (Medium confidence, 경고 로그)
        - < 0.6: Human Review 필요 (Low confidence)

    Args:
        gpt_confidence: 0.0 ~ 1.0 (GPT 제안 신뢰도)
        gemini_confidence: 0.0 ~ 1.0 (Gemini 검증 신뢰도)
        extraction_quality: 0.0 ~ 1.0 (실제 추출 품질)

    Returns:
        float: 0.0 ~ 1.0 (최종 합의 점수)

    Example:
        >>> calculate_consensus_score(0.95, 0.90, 1.0)
        0.95  # 자동 승인 (모든 지표가 높음)

        >>> calculate_consensus_score(0.80, 0.70, 0.60)
        0.69  # 조건부 승인 (중간 품질)

        >>> calculate_consensus_score(0.60, 0.50, 0.30)
        0.43  # Human Review (품질 낮음)
    """
    consensus_score = gpt_confidence * 0.3 + gemini_confidence * 0.3 + extraction_quality * 0.4

    logger.info(
        f"[Consensus Score] GPT={gpt_confidence:.2f}(30%) + "
        f"Gemini={gemini_confidence:.2f}(30%) + "
        f"Extraction={extraction_quality:.2f}(40%) "
        f"= {consensus_score:.2f}"
    )

    return round(consensus_score, 2)


# ============================================================================
# Gemini Validator Node
# ============================================================================

import google.generativeai as genai
from bs4 import BeautifulSoup


def gemini_validate_node(state: HITLState) -> HITLState:
    """
    GPT-4o가 GPT-4o-mini 제안을 검증하는 Node
    (원래 Gemini였으나 rate limit으로 GPT-4o로 변경)

    LangGraph Node 규칙:
    1. 입력: state (HITLState) - gpt_proposal 포함
    2. 출력: 업데이트된 state (HITLState) - gemini_validation 추가
    3. state를 직접 수정하지 않고, 새로운 dict를 반환

    검증 방법:
    1. GPT가 제안한 CSS Selector를 실제 HTML에 적용
    2. 데이터 추출 성공 여부 확인
    3. 추출된 데이터의 품질 평가
    4. GPT-4o LLM으로 최종 판단
    """
    logger.info(f"[GPT-4o Validate Node] Starting validation for {state['url']}")

    try:
        # 1. GPT 제안 가져오기
        gpt_proposal = state.get("gpt_proposal")
        if not gpt_proposal:
            raise ValueError("No GPT proposal found in state")

        # 2. CSS Selector로 실제 데이터 추출 시도
        html_content = state.get("html_content", "")
        soup = BeautifulSoup(html_content, "html.parser")

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

        # 3. GPT-4o에게 검증 요청 (Gemini rate limit 대응)
        from langchain_openai import ChatOpenAI

        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not set")

        gpt_validator = ChatOpenAI(
            model="gpt-4o", temperature=0.2, api_key=openai_key, max_tokens=2048, timeout=30.0
        )

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

        # GPT-4o 호출
        response = gpt_validator.invoke([{"role": "user", "content": validation_prompt}])

        # JSON 파싱
        try:
            validation = json.loads(response.content)
        except Exception as e:
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response.content, re.DOTALL)
            if json_match:
                validation = json.loads(json_match.group(1))
            else:
                raise ValueError("Failed to parse GPT-4o JSON response")

        logger.info(
            f"[GPT-4o Validate Node] Validation: {validation.get('is_valid')} (confidence: {validation.get('confidence')})"
        )

        # 4. 합의 여부 결정 (NEW! Weighted Consensus Algorithm - Sprint 1)
        # 기존: validation.get("is_valid") 단순 사용
        # 개선: GPT confidence + Gemini confidence + Extraction quality 종합 평가

        # 4-1. 추출 품질 계산
        extraction_quality = calculate_extraction_quality(extracted_data, extraction_success)

        # 4-2. 합의 점수 계산 (0.0 ~ 1.0)
        gpt_confidence = gpt_proposal.get("confidence", 0.0)
        gemini_confidence = validation.get("confidence", 0.0)
        consensus_score = calculate_consensus_score(
            gpt_confidence, gemini_confidence, extraction_quality
        )

        # 4-3. 합의 여부 판단 (3-tier system, 완화됨)
        if consensus_score >= 0.7:
            consensus_reached = True
            logger.info(f"[Consensus] ✅ AUTO-APPROVED (score={consensus_score:.2f} >= 0.7)")
        elif consensus_score >= 0.5:
            consensus_reached = True
            logger.warning(
                f"[Consensus] ⚠️ CONDITIONAL APPROVAL (score={consensus_score:.2f} >= 0.5) "
                f"- Medium confidence, monitoring recommended"
            )
        else:
            consensus_reached = False
            logger.warning(
                f"[Consensus] ❌ REJECTED (score={consensus_score:.2f} < 0.5) - Human Review needed"
            )

        # 5. next_action 결정
        # FIX Bug #1: retry_count를 if 블록 밖에서 초기화
        retry_count = state.get("retry_count", 0)

        if consensus_reached:
            next_action = "end"  # 합의 성공 → 종료
        else:
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
            "next_action": next_action,
        }

    except Exception as gpt_error:
        logger.error(f"[GPT-4o Validate Node] ❌ GPT-4o validation failed: {gpt_error}")
        logger.warning("[GPT-4o Validate Node] 🔄 Falling back to GPT-4o-mini for validation")

        # Fallback: GPT-4o-mini로 검증 시도
        try:
            import time

            from langchain_openai import ChatOpenAI

            from src.exceptions import OpenAIAPIError, format_error_for_user

            # GPT 제안 가져오기
            gpt_proposal = state.get("gpt_proposal")
            if not gpt_proposal:
                raise ValueError("No GPT proposal found in state")

            # CSS Selector로 실제 데이터 추출 시도 (Gemini에서 했던 것과 동일)
            html_content = state.get("html_content", "")
            soup = BeautifulSoup(html_content, "html.parser")

            extracted_data = {}
            extraction_success = {}

            for field in ["title", "body", "date"]:
                selector_key = f"{field}_selector"
                selector = gpt_proposal.get(selector_key, "")

                try:
                    elements = soup.select(selector)
                    if elements:
                        text = elements[0].get_text(strip=True)
                        extracted_data[field] = text[:200]
                        extraction_success[field] = True
                    else:
                        extracted_data[field] = None
                        extraction_success[field] = False
                except Exception as e:
                    logger.warning(f"[Fallback Validate] Extraction failed for {field}: {e}")
                    extracted_data[field] = None
                    extraction_success[field] = False

            # GPT-4o-mini 검증 요청
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

            # GPT-4o-mini 호출 (최대 2회 재시도)
            for attempt in range(2):
                try:
                    fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2, timeout=30.0)
                    response = fallback_llm.invoke([{"role": "user", "content": validation_prompt}])
                    fallback_output = json.loads(response.content)

                    logger.info(
                        f"[Fallback Validate] ✅ GPT-4o-mini validation succeeded (attempt {attempt+1})"
                    )

                    # Consensus 계산
                    extraction_quality = calculate_extraction_quality(
                        extracted_data, extraction_success
                    )
                    gpt_confidence = gpt_proposal.get("confidence", 0.0)
                    gemini_confidence = fallback_output.get("confidence", 0.0)  # GPT-4o-mini가 대체
                    consensus_score = calculate_consensus_score(
                        gpt_confidence, gemini_confidence, extraction_quality
                    )

                    # Consensus 판단
                    if consensus_score >= 0.7:
                        consensus_reached = True
                        logger.info(
                            f"[Consensus Fallback] ✅ AUTO-APPROVED (score={consensus_score:.2f})"
                        )
                    elif consensus_score >= 0.5:
                        consensus_reached = True
                        logger.warning(
                            f"[Consensus Fallback] ⚠️ CONDITIONAL APPROVAL (score={consensus_score:.2f})"
                        )
                    else:
                        consensus_reached = False
                        logger.warning(
                            f"[Consensus Fallback] ❌ REJECTED (score={consensus_score:.2f})"
                        )

                    # next_action 결정
                    if consensus_reached:
                        next_action = "end"
                    else:
                        retry_count = state.get("retry_count", 0)
                        if retry_count < 3:
                            next_action = "retry"
                        else:
                            next_action = "human_review"

                    return {
                        **state,
                        "gemini_validation": fallback_output,
                        "consensus_reached": consensus_reached,
                        "retry_count": retry_count + (0 if consensus_reached else 1),
                        "final_selectors": gpt_proposal if consensus_reached else None,
                        "next_action": next_action,
                        "fallback_used": "gpt-4o-mini",  # 메타데이터
                    }

                except Exception as retry_error:
                    if attempt < 1:  # 1회 더 시도
                        wait_time = 2**attempt
                        logger.warning(
                            f"[Fallback Validate] ⚠️ Retry after {wait_time}s: {retry_error}"
                        )
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(
                            f"[Fallback Validate] ❌ GPT-4o-mini also failed: {retry_error}"
                        )
                        raise

        except Exception as fallback_error:
            # GPT-4o와 GPT-4o-mini 모두 실패
            logger.error(f"[GPT-4o Validate Node] ❌ Both GPT-4o and fallback failed")
            logger.error(f"  - GPT-4o error: {gpt_error}")
            logger.error(f"  - Fallback error: {fallback_error}")

            from src.exceptions import OpenAIAPIError, format_error_for_user

            user_message = format_error_for_user(OpenAIAPIError(str(gpt_error)))

            # FIX Bug #2 & #3: None 대신 빈 validation dict 반환
            retry_count = state.get("retry_count", 0)

            return {
                **state,
                "error_message": f"Validation failed: {user_message} (Fallback also failed)",
                "gemini_validation": {
                    "is_valid": False,
                    "confidence": 0.0,
                    "feedback": "Both GPT-4o and GPT-4o-mini validation failed",
                    "suggested_changes": {},
                },  # 빈 dict 대신 유효한 validation object
                "consensus_reached": False,
                "consensus_score": 0.0,
                "retry_count": retry_count + 1,
                "next_action": "human_review" if retry_count < 3 else "end",
            }


# ============================================================================
# Human Review Node (HITL)
# ============================================================================


def human_review_node(state: HITLState) -> HITLState:
    """
    완전 자동화 Node (Human Review 제거)

    3회 재시도 후에도 합의 실패 시, **이전 Selector 유지** (사람 개입 X)

    동작:
    1. 합의 실패 기록 (DecisionLog)
    2. 이전 Selector 유지 (DB 업데이트 안 함)
    3. 워크플로우 종료 (next_action = "end")

    PoC 핵심: 완전 자동화 - Agent가 자율적으로 결정, 사람 개입 없음
    """
    logger.warning(
        f"[Auto-Decision Node] 3회 재시도 실패 → 이전 Selector 유지 (URL: {state['url']})"
    )

    gpt_proposal = state.get("gpt_proposal")
    gemini_validation = state.get("gemini_validation")

    # Consensus 실패 정보 기록
    logger.info(
        f"[Auto-Decision] GPT proposal: {gpt_proposal}\n"
        f"[Auto-Decision] Gemini validation: {gemini_validation}\n"
        f"[Auto-Decision] Decision: 이전 Selector 유지 (변경 없음)"
    )

    return {
        **state,
        "consensus_reached": False,  # 합의 실패 명시
        "final_selectors": None,  # Selector 업데이트 안 함
        "error_message": "3회 재시도 실패 - 이전 Selector 유지",
        "next_action": "end",
    }


# ============================================================================
# Routing Function (조건부 Edge를 위한 라우팅)
# ============================================================================


def route_after_validation(state: HITLState) -> str:
    """
    Gemini Validate Node 이후의 라우팅 결정

    반환값:
    - "end": 합의 성공 → 워크플로우 종료
    - "retry": 재시도 필요 → GPT Propose로 돌아감
    - "human_review": HITL 발동 → Human Review Node로 이동
    """
    next_action = state.get("next_action", "end")

    logger.info(f"[Router] After validation, next_action: {next_action}")

    return next_action


# ============================================================================
# StateGraph 구성
# ============================================================================

from langgraph.graph import END, StateGraph


def build_uc2_graph():
    """
    UC2 HITL 워크플로우의 StateGraph를 생성하고 compile

    반환값: Compiled LangGraph app

    그래프 구조:

        START
          ↓
      gpt_propose (GPT-4o-mini)
          ↓
      gemini_validate (Gemini-2.0-flash)
          ↓
      ┌───────────────┐
      │ route_after_  │
      │  validation   │
      └───────────────┘
         ↓    ↓    ↓
       END  retry  human_review
              ↓         ↓
        gpt_propose   END
    """
    logger.info("[build_uc2_graph] Building LangGraph StateGraph...")

    # 1. StateGraph 생성
    workflow = StateGraph(HITLState)

    # 2. Node 추가
    workflow.add_node("gpt_propose", gpt_propose_node)
    workflow.add_node("gemini_validate", gemini_validate_node)
    workflow.add_node("human_review", human_review_node)

    # 3. Entry Point 설정
    workflow.set_entry_point("gpt_propose")

    # 4. Edge 추가
    # GPT → Gemini (항상 실행)
    workflow.add_edge("gpt_propose", "gemini_validate")

    # Gemini → 조건부 분기
    workflow.add_conditional_edges(
        "gemini_validate",
        route_after_validation,
        {
            "end": END,  # 합의 성공 → 종료
            "retry": "gpt_propose",  # 재시도 → GPT 다시 실행
            "human_review": "human_review",  # HITL 발동
        },
    )

    # Human Review → 종료 (항상)
    workflow.add_edge("human_review", END)

    # 5. Compile
    app = workflow.compile()

    logger.info("[build_uc2_graph] StateGraph compiled successfully")

    return app


# ============================================================================
# 다음 단계: 테스트 스크립트 작성
# ============================================================================

# TODO: 테스트 스크립트 작성 (test_uc2_hitl.py)
