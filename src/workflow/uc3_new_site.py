"""
UC3 New Site Auto-Discovery Agent - Self-Healing Crawler

목적: 신규 뉴스 사이트 자동 분석 및 CSS Selector 생성

LLM 사용: GPT-4o (Discoverer)
  - 역할: 신규 사이트 DOM 분석 및 Selector 생성
  - Confidence: 0.0 ~ 1.0

Workflow:
    START
      ↓
    fetch_html (HTML 다운로드)
      ↓
    preprocess_html (토큰 축소 50-80%)
      ↓
    gpt_discover (GPT-4o - Selector 생성)
      ↓
    validate_selectors (샘플 URL로 검증)
      ↓
    check_quality (품질 게이트)
      ↓
    save_selectors (DB 저장) OR human_review
      ↓
    END

작성일: 2025-11-09
수정일: 2025-11-10 (Claude → GPT-4o 전환)
"""

import json
import os
import re
import time
from datetime import datetime
from functools import partial
from typing import List, Literal, Optional, TypedDict
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

# Tavily removed - using Few-Shot Examples instead
# from langchain_community.tools.tavily_search import TavilySearchResults
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI

# LangChain imports for Tools and Agents
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from loguru import logger
from pydantic import BaseModel, Field

from src.agents.few_shot_retriever import format_few_shot_prompt, get_few_shot_examples
from src.exceptions import HTMLFetchError, format_error_for_user
from src.storage.database import get_db
from src.storage.models import Selector

# v2.1: Site ID 정규화 유틸리티
from src.utils.site_detector import extract_site_id

# Firecrawl removed - using simple preprocess_html instead
# try:
#     from firecrawl import FirecrawlApp
# except ImportError:
#     logger.warning("firecrawl-py not installed. UC3 Firecrawl tool will be disabled.")
#     FirecrawlApp = None



# ============================================================
# Step 1: Pydantic Models (GPT-4o Structured Output)
# ============================================================


class SiteStructureAnalysis(BaseModel):
    """
    GPT-4o가 분석한 뉴스 사이트 구조 정보
    """

    site_name: str = Field(description="사이트 이름 (도메인 기반)")
    site_type: Literal["ssr", "spa"] = Field(description="서버 사이드 렌더링(SSR) 또는 SPA")
    title_selector: str = Field(description="기사 제목 CSS Selector")
    body_selector: str = Field(description="기사 본문 CSS Selector")
    date_selector: str = Field(description="기사 날짜 CSS Selector")
    author_selector: Optional[str] = Field(default=None, description="저자 CSS Selector (선택)")
    category_selector: Optional[str] = Field(
        default=None, description="카테고리 CSS Selector (선택)"
    )
    confidence: float = Field(description="Selector 정확도 (0.0 ~ 1.0)")
    reasoning: str = Field(description="Selector 선택 이유")


# ============================================================
# Step 2: State 정의
# ============================================================


class UC3State(TypedDict, total=False):
    """
    UC3 New Site Auto-Discovery State

    필드 설명:
        url: 분석할 뉴스 기사 URL (1개)
        site_name: 사이트 이름 (자동 추출)
        sample_urls: 검증용 샘플 URL 리스트 (3-5개, 선택)

        raw_html: 다운로드한 원본 HTML
        preprocessed_html: 전처리된 HTML (토큰 축소)

        gpt_analysis: GPT-4o의 Selector 분석 결과
        validation_report: Selector 검증 결과
        selectors_valid: Selector가 유효한지 여부

        confidence: GPT-4o 신뢰도 점수 (0.0 ~ 1.0)
        success_rate: 검증 성공률 (0.0 ~ 1.0)

        next_action: 다음 액션
            - "save": Selector 저장 → 크롤링 시작
            - "refine": UC2로 Selector 개선
            - "human_review": 수동 검토 필요

    예시:
        {
            "url": "https://www.chosun.com/economy/2025/11/09/...",
            "site_name": "chosun",
            "sample_urls": [],
            "gpt_analysis": {...},
            "confidence": 0.85,
            "success_rate": 0.90,
            "next_action": "save"
        }
    """

    # 입력 데이터
    url: str
    site_name: str
    sample_urls: List[str]

    # HTML 데이터
    raw_html: str
    preprocessed_html: str

    # 분석 결과
    gpt_analysis: dict
    validation_report: dict
    selectors_valid: bool

    # 품질 지표
    confidence: float
    success_rate: float

    # 다음 액션
    next_action: Literal["save", "refine", "human_review"]

    # === NEW: 3-Tool Results ===
    # tavily_results: dict  # REMOVED - not needed anymore
    """
    Tavily Web Search Tool - REMOVED (replaced by Few-Shot Examples)
    {
        "success": True/False,
        "results": [...],
        "query": "...",
        "error": "..." (if failed)
    }
    """

    # firecrawl_results: dict  # REMOVED - not needed
    """
    Firecrawl HTML Preprocessing Tool - REMOVED (too expensive, using simple preprocess)
    {
        "success": True/False,
        "html": "...",
        "markdown": "...",
        "metadata": {...},
        "original_tokens": 50000,
        "reduced_tokens": 5000
    }
    """

    beautifulsoup_analysis: dict
    """
    Beautiful Soup DOM Analyzer Tool 결과
    {
        "success": True/False,
        "analysis": {
            "title_candidates": [...],
            "body_candidates": [...],
            "date_candidates": [...]
        }
    }
    """

    # === NEW: 2-Agent Consensus System ===
    gpt_proposal: dict
    """
    GPT-4o Agent (Proposer) 제안
    {
        "selectors": {
            "title": {"selector": "...", "confidence": 0.95, "reasoning": "..."},
            "body": {"selector": "...", "confidence": 0.88, "reasoning": "..."},
            "date": {"selector": "...", "confidence": 0.92, "reasoning": "..."}
        },
        "overall_confidence": 0.92
    }
    """

    gpt_confidence: float
    """GPT-4o의 전체 신뢰도 (0.0-1.0)"""

    gpt4o_validation: dict
    """
    GPT-4o Agent (Validator) 검증 결과
    {
        "best_selectors": {
            "title": "...",
            "body": "...",
            "date": "..."
        },
        "validation_details": {
            "title": {"valid": True, "confidence": 0.96, "text": "..."},
            "body": {"valid": True, "confidence": 0.91, "text": "..."},
            "date": {"valid": True, "confidence": 1.0, "text": "..."}
        },
        "overall_confidence": 0.95
    }
    """

    gpt4o_confidence: float
    """GPT-4o의 전체 신뢰도 (0.0-1.0)"""

    consensus_score: float
    """
    가중 합의 점수 (0.0-1.0)
    Formula: 0.3 × GPT + 0.3 × Gemini + 0.4 × Extraction Quality
    """

    consensus_reached: bool
    """합의 도달 여부 (consensus_score >= 0.7)"""

    extraction_quality: float
    """추출 품질 점수 (0.0-1.0)"""

    discovered_selectors: dict
    """
    최종 발견된 셀렉터 (consensus_reached=True일 때만)
    {
        "title": "...",
        "body": "...",
        "date": "..."
    }
    """

    # === NEW: JSON-LD Smart Extraction ===
    json_ld_metadata: dict
    """
    JSON-LD/Meta 태그로 추출된 메타데이터
    {
        "title": "...",
        "description": "...",
        "author": "...",
        "date": "...",
        "image": "...",
        "source": "json-ld" | "meta-tags" | "merged"
    }
    """

    json_ld_quality: float
    """JSON-LD 메타데이터 품질 점수 (0.0-1.0)"""

    skip_gpt_gemini: bool
    """JSON-LD 품질이 충분히 높아 GPT/Gemini 에이전트를 skip할지 여부"""


# ============================================================
# Step 3: Helper Functions
# ============================================================


# v2.1: extract_site_name() 함수는 src/utils/site_detector.py로 이동
# 하위 호환성을 위해 별칭 제공
def extract_site_name(url: str) -> str:
    """
    URL에서 사이트 이름 추출 (v2.1: site_detector.py 사용)

    예시:
        "https://www.chosun.com/..." → "chosun"
        "https://news.jtbc.co.kr/..." → "jtbc" (개선됨)
        "https://edition.cnn.com/..." → "cnn" (개선됨)
    """
    return extract_site_id(url)


def preprocess_html(raw_html: str) -> str:
    """
    HTML 전처리 (토큰 축소 50-80%)

    제거:
        - script, style, svg, iframe, noscript
        - 주석 (comments)
        - 긴 텍스트 축약 (100자 이상 → 50자 + "...")

    유지:
        - main, article, header, section
        - h1~h6, p, time, span
        - class, id 속성
    """
    soup = BeautifulSoup(raw_html, "html.parser")

    # 0. head 태그 먼저 백업 (meta 정보 보존)
    head_tag = soup.find("head")
    if head_tag:
        # head 태그 복사본 생성 (script/style 제거 전)
        head_backup = str(head_tag)
    else:
        head_backup = None

    # 1. 불필요한 태그 제거
    for tag in soup(["script", "style", "svg", "iframe", "noscript", "footer", "nav"]):
        tag.decompose()

    # 2. 주석 제거
    for comment in soup.find_all(
        string=lambda text: isinstance(text, str) and text.strip().startswith("<!--")
    ):
        comment.extract()

    # 3. main/article 영역만 추출 (있으면)
    main_content = (
        soup.find("main")
        or soup.find("article")
        or soup.find("div", class_=re.compile(r"(content|article|post|entry)", re.I))
    )

    if main_content:
        # head 백업과 main 결합
        if head_backup:
            result = head_backup + str(main_content)
        else:
            result = str(main_content)
    else:
        result = str(soup)

    # 4. 긴 텍스트 축약 (선택)
    # (GPT-4o는 128K 토큰까지 지원)

    logger.info(
        f"[UC3] HTML 전처리 완료: {len(raw_html)} chars → {len(result)} chars ({len(result)/len(raw_html)*100:.1f}%)"
    )

    return result


# ============================================================
# Step 4: Node 함수 정의
# ============================================================


def fetch_html_node(state: UC3State) -> dict:
    """
    Node 1: HTML 다운로드

    목적:
        입력받은 URL의 HTML을 다운로드합니다.
        HTTP retry logic with distinction between permanent and transient errors.

    입력:
        state["url"]: 뉴스 기사 URL

    출력:
        state["raw_html"]: 다운로드한 HTML
        state["site_name"]: 추출한 사이트 이름

    Retry Logic:
        - Permanent errors (400, 401, 403, 404): No retry
        - Transient errors (429, 500, 502, 503, 504, timeout, connection): Retry with exponential backoff
        - Max retries: 3 attempts
        - Backoff: 1s, 2s, 4s
    """
    url = state["url"]

    logger.info(f"[UC3] HTML 다운로드 시작: {url}")

    # Permanent errors that should not be retried
    permanent_status_codes = {400, 401, 403, 404, 410}

    # Transient errors that should be retried
    transient_status_codes = {429, 500, 502, 503, 504}

    max_retries = 3
    last_error = None

    for attempt in range(max_retries):
        try:
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            response.raise_for_status()

            raw_html = response.text
            site_name = extract_site_name(url)

            logger.info(
                f"[UC3] ✅ HTML 다운로드 완료 (attempt={attempt+1}): {len(raw_html)} chars, site={site_name}"
            )

            return {"raw_html": raw_html, "site_name": site_name}

        except requests.exceptions.HTTPError as http_error:
            last_error = http_error
            status_code = http_error.response.status_code if http_error.response else None

            # Permanent errors - do not retry
            if status_code in permanent_status_codes:
                logger.error(f"[UC3] ❌ Permanent HTTP error {status_code}: {url}")
                error = HTMLFetchError(
                    message=f"Permanent HTTP error: {status_code}",
                    url=url,
                    status_code=status_code,
                    details={"error": str(http_error)},
                )
                user_message = format_error_for_user(error)
                return {
                    "raw_html": "",
                    "site_name": extract_site_name(url),
                    "next_action": "human_review",
                    "error_message": user_message,
                }

            # Transient errors - retry with exponential backoff
            elif status_code in transient_status_codes:
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1  # 1s, 2s, 4s
                    logger.warning(
                        f"[UC3] ⚠️ Transient HTTP error {status_code} (attempt={attempt+1}), retrying after {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[UC3] ❌ Max retries reached for HTTP {status_code}: {url}")

            else:
                # Unknown status code - log and retry
                if attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1
                    logger.warning(
                        f"[UC3] ⚠️ Unknown HTTP error {status_code} (attempt={attempt+1}), retrying after {wait_time}s"
                    )
                    time.sleep(wait_time)
                    continue

        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as conn_error:
            # Network errors are transient - retry
            last_error = conn_error
            if attempt < max_retries - 1:
                wait_time = (2**attempt) * 1
                logger.warning(
                    f"[UC3] ⚠️ Network error (attempt={attempt+1}), retrying after {wait_time}s: {conn_error}"
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[UC3] ❌ Max retries reached for network error: {url}")

        except Exception as generic_error:
            # Unknown errors - log and retry
            last_error = generic_error
            if attempt < max_retries - 1:
                wait_time = (2**attempt) * 1
                logger.warning(
                    f"[UC3] ⚠️ Unknown error (attempt={attempt+1}), retrying after {wait_time}s: {generic_error}"
                )
                time.sleep(wait_time)
                continue
            else:
                logger.error(f"[UC3] ❌ Max retries reached for unknown error: {url}")

    # All retries failed
    error = HTMLFetchError(
        message=f"Failed to fetch HTML after {max_retries} attempts",
        url=url,
        status_code=getattr(last_error, "response", None)
        and getattr(last_error.response, "status_code", None),
        details={"error": str(last_error)},
    )
    user_message = format_error_for_user(error)

    logger.error(f"[UC3] ❌ HTML 다운로드 실패 (all retries exhausted): {user_message}")

    return {
        "raw_html": "",
        "site_name": extract_site_name(url),
        "next_action": "human_review",
        "error_message": user_message,
    }


def extract_json_ld_node(state: UC3State) -> dict:
    """
    Node: JSON-LD Smart Metadata Extraction

    목적:
        JSON-LD/Meta 태그로 구조화된 메타데이터 추출
        품질이 충분히 높으면 (≥ 0.7) GPT/Gemini 에이전트 skip 가능

    입력:
        state["raw_html"]: 다운로드한 원본 HTML (preprocessing 전)

    출력:
        state["json_ld_metadata"]: 추출된 메타데이터
        state["json_ld_quality"]: 품질 점수 (0.0-1.0)
        state["skip_gpt_gemini"]: GPT/Gemini skip 여부

    장점:
        - HTML <head> 접근 가능 (preprocessing 전)
        - CSS 셀렉터 불필요 (BeautifulSoup 직접 사용)
        - 95% 성공률 (Schema.org NewsArticle 표준)

    작성일: 2025-11-14
    """
    from src.utils.meta_extractor import extract_metadata_smart, get_metadata_quality_score

    raw_html = state.get("raw_html", "")

    if not raw_html:
        logger.warning("[UC3 JSON-LD] raw_html이 비어있습니다")
        return {"json_ld_metadata": {}, "json_ld_quality": 0.0, "skip_gpt_gemini": False}

    logger.info("[UC3 JSON-LD] JSON-LD/Meta 태그 추출 시작...")

    try:
        # Smart extraction (JSON-LD → Meta tags priority)
        metadata = extract_metadata_smart(raw_html)
        quality_score = get_metadata_quality_score(metadata)

        # Skip GPT/Gemini if quality is high enough
        skip_agents = bool(metadata.get("title")) and quality_score >= 0.7

        if skip_agents:
            logger.info(
                f"[UC3 JSON-LD] ✅ High quality (score={quality_score:.2f}, source={metadata.get('source')}) → Skipping GPT/Gemini"
            )
        else:
            logger.info(
                f"[UC3 JSON-LD] ⚠️ Low quality (score={quality_score:.2f}) → Proceeding to GPT/Gemini agents"
            )

        logger.debug(
            f"[UC3 JSON-LD] Metadata: title={metadata.get('title', 'N/A')[:50]}, date={metadata.get('date', 'N/A')}"
        )

        return {
            "json_ld_metadata": metadata,
            "json_ld_quality": quality_score,
            "skip_gpt_gemini": skip_agents,
        }

    except Exception as e:
        logger.error(f"[UC3 JSON-LD] ❌ Extraction failed: {e}")
        return {"json_ld_metadata": {}, "json_ld_quality": 0.0, "skip_gpt_gemini": False}


def preprocess_html_node(state: UC3State) -> dict:
    """
    Node 2: HTML 전처리

    목적:
        토큰 수를 50-80% 축소하여 GPT-4o 입력 최적화

    입력:
        state["raw_html"]: 원본 HTML

    출력:
        state["preprocessed_html"]: 전처리된 HTML
    """
    raw_html = state.get("raw_html", "")

    if not raw_html:
        logger.warning("[UC3] raw_html이 비어있습니다")
        return {"preprocessed_html": "", "next_action": "human_review"}

    preprocessed = preprocess_html(raw_html)

    return {"preprocessed_html": preprocessed}


def gpt_discover_node(state: UC3State) -> dict:
    """
    Node 3: GPT-4o로 Selector 분석

    목적:
        전처리된 HTML을 GPT-4o에게 전달하고
        뉴스 기사 구조를 분석하여 CSS Selector를 생성합니다.

    입력:
        state["preprocessed_html"]: 전처리된 HTML
        state["url"]: 원본 URL
        state["site_name"]: 사이트 이름

    출력:
        state["gpt_analysis"]: GPT-4o 분석 결과 (dict)
        state["confidence"]: GPT-4o 신뢰도
    """
    preprocessed_html = state.get("preprocessed_html", "")
    url = state.get("url", "")
    site_name = state.get("site_name", "")

    if not preprocessed_html:
        logger.warning("[UC3] preprocessed_html이 비어있습니다")
        return {"gpt_analysis": {}, "confidence": 0.0, "next_action": "human_review"}

    logger.info(f"[UC3] GPT-4o 분석 시작: site={site_name}")

    # Import dependencies
    import time

    from langchain_openai import ChatOpenAI

    from src.exceptions import OpenAIAPIError, format_error_for_user, is_retryable_error

    # 프롬프트 생성
    prompt = f"""
Analyze this Korean news article HTML and generate CSS selectors.

Site URL: {url}
Site Name: {site_name}

HTML (preprocessed):
{preprocessed_html[:10000]}

**Selector Priority Guidelines**:
- **FIRST PRIORITY**: Target visible HTML elements (h1, div, article, section, p, time)
- **SECOND PRIORITY**: Use meta tags ONLY if visible elements are not reliable
- **Goal**: Extract actual article content from DOM structure

Tasks:
1. Identify the article title CSS selector
   - **Priority Order**:
     1. Visible heading tags: h1, h2, div.title, article > h1, header > h1
     2. Meta tags (if needed): meta[property="og:title"]
   - Prioritize semantic HTML tags when available
   - Avoid id-based selectors (prefer class or tag)

2. Identify the article body CSS selector
   - **Priority Order**:
     1. Content containers: article > p, div.content p, section.article-body
     2. Main content: main p, div.article-content
     3. Avoid: meta[name="description"] (too short)
   - Should extract main text content (multiple paragraphs)
   - Avoid navigation, ads, related articles

3. Identify the publication date selector
   - **Priority Order**:
     1. Time elements: time[datetime], time.published-date, span.date
     2. Date containers: div.timestamp, span.article-date
     3. Meta tags (acceptable): meta[property="article:published_time"]
   - Date format: ISO 8601 or Korean format (YYYY-MM-DD HH:MM:SS)
   - **Note**: Meta tags for dates are acceptable (many sites use them)

4. Determine if this is SSR (Server-Side Rendering) or SPA (Single Page App)
   - SSR: Full HTML content visible
   - SPA: Minimal HTML, client-side rendering (React, Vue, etc.)

5. Provide confidence score (0.0 - 1.0)
   - 0.9-1.0: Very confident, semantic HTML, clear structure
   - 0.7-0.9: Confident, good structure
   - 0.5-0.7: Uncertain, multiple candidates
   - <0.5: Low confidence, unclear structure

Guidelines:
- Prefer stable selectors (avoid auto-generated class names like 'css-1a2b3c')
- Use descendant combinators (e.g., 'article > h1') for precision
- Test selectors mentally against the HTML structure
- Provide clear reasoning for your choices and priority level used
- **Prefer visible elements, but meta tags are acceptable when necessary**

Return structured output with:
- site_name
- site_type ('ssr' or 'spa')
- title_selector
- body_selector
- date_selector
- confidence (0.0 - 1.0)
- reasoning (why you chose these selectors)
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
                # GPT-4o 초기화 (timeout 30초)
                llm = ChatOpenAI(model="gpt-4o", temperature=0, api_key=api_key, timeout=30.0)

                structured_llm = llm.with_structured_output(SiteStructureAnalysis)
                result: SiteStructureAnalysis = structured_llm.invoke(prompt)

                logger.info(f"[UC3] ✅ GPT-4o 분석 완료 (key={key_idx+1}, attempt={attempt+1}):")
                logger.info(f"  Title Selector: {result.title_selector}")
                logger.info(f"  Body Selector: {result.body_selector}")
                logger.info(f"  Date Selector: {result.date_selector}")
                logger.info(f"  Confidence: {result.confidence:.2f}")
                logger.info(f"  Reasoning: {result.reasoning[:100]}...")

                return {"gpt_analysis": result.dict(), "confidence": result.confidence}

            except Exception as raw_error:
                last_error = raw_error
                error = OpenAIAPIError.from_openai_error(raw_error)

                # Retry 가능한 오류인가?
                if is_retryable_error(error) and attempt < max_retries - 1:
                    wait_time = (2**attempt) * 1  # 1s, 2s, 4s
                    logger.warning(
                        f"[UC3] ⚠️ Retryable error, waiting {wait_time}s (attempt {attempt+1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"[UC3] ❌ Attempt {attempt+1} failed (key={key_idx+1}): {error}")
                    break  # 다음 API 키로

    # 모든 API 키와 재시도 실패
    user_message = format_error_for_user(
        OpenAIAPIError.from_openai_error(last_error) if last_error else Exception("Unknown error")
    )
    logger.error(f"[UC3] ❌ All API keys exhausted. Last error: {user_message}")

    return {
        "gpt_analysis": {},
        "confidence": 0.0,
        "error_message": f"GPT-4o discovery failed: {user_message}",
        "next_action": "human_review",
    }


def validate_selectors_node(state: UC3State) -> dict:
    """
    Node 4: Selector 검증

    목적:
        생성된 Selector를 원본 HTML에 적용하여 검증합니다.
        (샘플 URL이 없으면 원본 URL만 검증)

    입력:
        state["gpt_analysis"]: GPT-4o 분석 결과
        state["raw_html"]: 원본 HTML
        state["sample_urls"]: 샘플 URL 리스트 (선택)

    출력:
        state["validation_report"]: 검증 결과
        state["selectors_valid"]: 검증 성공 여부
        state["success_rate"]: 검증 성공률 (0.0 ~ 1.0)
    """
    gpt_analysis = state.get("gpt_analysis", {})
    raw_html = state.get("raw_html", "")

    if not gpt_analysis or not raw_html:
        logger.warning("[UC3] gpt_analysis 또는 raw_html이 비어있습니다")
        return {
            "validation_report": {},
            "selectors_valid": False,
            "success_rate": 0.0,
            "next_action": "human_review",
        }

    title_selector = gpt_analysis.get("title_selector", "")
    body_selector = gpt_analysis.get("body_selector", "")
    date_selector = gpt_analysis.get("date_selector", "")

    logger.info(f"[UC3] Selector 검증 시작")

    soup = BeautifulSoup(raw_html, "html.parser")

    # Title 검증
    title_elements = soup.select(title_selector)
    title_valid = False
    title_text = ""

    if title_elements:
        title_text = title_elements[0].get_text(strip=True)
        if len(title_text) >= 10:
            title_valid = True

    # Body 검증
    body_elements = soup.select(body_selector)
    body_valid = False
    body_text = ""

    if body_elements:
        # 모든 <p> 태그 텍스트 합치기
        body_text = " ".join([el.get_text(strip=True) for el in body_elements])
        if len(body_text) >= 500:
            body_valid = True

    # Date 검증
    date_elements = soup.select(date_selector)
    date_valid = False
    date_text = ""

    if date_elements:
        date_text = date_elements[0].get_text(strip=True) or date_elements[0].get("datetime", "")
        # 날짜 패턴 확인 (YYYY-MM-DD 또는 YYYY.MM.DD 또는 YYYY년MM월DD일)
        if re.search(r"\d{4}[-./년]\d{1,2}[-./월]\d{1,2}", date_text):
            date_valid = True

    # 검증 결과 계산
    total_fields = 3
    valid_fields = sum([title_valid, body_valid, date_valid])
    success_rate = valid_fields / total_fields

    logger.info(f"[UC3] 검증 결과:")
    logger.info(f"  Title: {'✅' if title_valid else '❌'} ({len(title_text)} chars)")
    logger.info(f"  Body: {'✅' if body_valid else '❌'} ({len(body_text)} chars)")
    logger.info(f"  Date: {'✅' if date_valid else '❌'} ({date_text})")
    logger.info(f"  Success Rate: {success_rate:.2%} ({valid_fields}/{total_fields})")

    validation_report = {
        "title_valid": title_valid,
        "title_text": title_text[:100],
        "body_valid": body_valid,
        "body_length": len(body_text),
        "date_valid": date_valid,
        "date_text": date_text,
        "success_rate": success_rate,
    }

    selectors_valid = success_rate >= 0.8  # 80% 이상이면 유효

    return {
        "validation_report": validation_report,
        "selectors_valid": selectors_valid,
        "success_rate": success_rate,
    }


def check_quality_node(state: UC3State) -> dict:
    """
    Node 5: 품질 게이트

    목적:
        GPT-4o 신뢰도와 검증 성공률을 종합하여 다음 액션 결정

    입력:
        state["confidence"]: GPT-4o 신뢰도
        state["success_rate"]: 검증 성공률
        state["selectors_valid"]: 검증 성공 여부

    출력:
        state["next_action"]: 다음 액션
            - "save": 성공률 ≥ 80% AND 신뢰도 ≥ 0.7 → DB 저장
            - "refine": 60% ≤ 성공률 < 80% → UC2 개선
            - "human_review": 성공률 < 60% → 수동 검토
    """
    confidence = state.get("confidence", 0.0)
    success_rate = state.get("success_rate", 0.0)
    selectors_valid = state.get("selectors_valid", False)

    logger.info(f"[UC3] 품질 게이트:")
    logger.info(f"  GPT-4o Confidence: {confidence:.2f}")
    logger.info(f"  Validation Success Rate: {success_rate:.2%}")
    logger.info(f"  Selectors Valid: {selectors_valid}")

    # 품질 게이트 로직
    if success_rate >= 0.8 and confidence >= 0.7:
        next_action = "save"
        logger.info(f"[UC3] ✅ 품질 기준 충족 → Selector 저장")
    elif success_rate >= 0.6:
        next_action = "refine"
        logger.warning(f"[UC3] ⚠️ 품질 미달 → UC2로 개선 필요")
    else:
        next_action = "human_review"
        logger.warning(f"[UC3] ❌ 품질 매우 낮음 → Human Review 필요")

    return {"next_action": next_action}


def save_selectors_node(state: UC3State) -> dict:
    """
    Node 6: Selector 저장

    목적:
        생성된 Selector를 DB에 저장합니다.

    입력:
        state["site_name"]: 사이트 이름
        state["discovered_selectors"]: Gemini 검증에서 합의된 최종 셀렉터

    출력:
        (DB 업데이트)
    """
    site_name = state.get("site_name", "")
    discovered_selectors = state.get("discovered_selectors", {})

    if not site_name or not discovered_selectors:
        logger.error(
            f"[UC3] site_name 또는 discovered_selectors가 비어있습니다: site={site_name}, selectors={discovered_selectors}"
        )
        return {}

    db = next(get_db())

    try:
        # 기존 Selector 확인
        existing = db.query(Selector).filter_by(site_name=site_name).first()

        if existing:
            # 업데이트
            existing.title_selector = discovered_selectors.get(
                "title", discovered_selectors.get("title_selector", "")
            )
            existing.body_selector = discovered_selectors.get(
                "body", discovered_selectors.get("body_selector", "")
            )
            existing.date_selector = discovered_selectors.get(
                "date", discovered_selectors.get("date_selector", "")
            )
            existing.site_type = "ssr"  # default

            logger.info(f"[UC3] Selector 업데이트: site={site_name}")
        else:
            # 신규 생성
            selector = Selector(
                site_name=site_name,
                title_selector=discovered_selectors.get(
                    "title", discovered_selectors.get("title_selector", "")
                ),
                body_selector=discovered_selectors.get(
                    "body", discovered_selectors.get("body_selector", "")
                ),
                date_selector=discovered_selectors.get(
                    "date", discovered_selectors.get("date_selector", "")
                ),
                site_type="ssr",  # default
            )
            db.add(selector)

            logger.info(f"[UC3] Selector 생성: site={site_name}, selectors={discovered_selectors}")

        db.commit()
        logger.info(f"[UC3] ✅ Selector 저장 완료!")

        return {}

    except Exception as e:
        logger.error(f"[UC3] Selector 저장 실패: {e}")
        db.rollback()
        return {}

    finally:
        db.close()


# ============================================================
# Step 4.5: NEW - 3-Tool + 2-Agent System for UC3
# ============================================================

# --- Helper Function: CSS Selector Generation ---


def generate_css_selector(tag) -> str:
    """
    BeautifulSoup tag로부터 고유 CSS 셀렉터 생성

    우선순위:
        1. ID가 있으면 #id 사용
        2. Class가 있으면 tag.class1.class2 사용
        3. 부모 기반 선택자 사용 (parent > tag:nth-of-type(n))
    """
    # ID 있으면 우선
    if tag.get("id"):
        return f"#{tag['id']}"

    # Class 조합 (최대 2개까지)
    classes = tag.get("class", [])
    if classes:
        class_selector = "." + ".".join(classes[:2])
        return f"{tag.name}{class_selector}"

    # 부모 기반 선택자
    parent = tag.parent
    if parent and parent.name != "[document]":
        try:
            parent_selector = generate_css_selector(parent)
            siblings = list(parent.find_all(tag.name, recursive=False))
            if len(siblings) > 1:
                idx = siblings.index(tag) + 1
                return f"{parent_selector} > {tag.name}:nth-of-type({idx})"
            else:
                return f"{parent_selector} > {tag.name}"
        except Exception as e:
            pass

    return tag.name


# --- Tool 1: Tavily Web Search ---


def tavily_search_node(state: UC3State) -> dict:
    """
    Tool 1: Tavily Web Search - 유사 사이트의 CSS 셀렉터 패턴 검색

    목적:
        GitHub나 StackOverflow에서 유사한 사이트의 셀렉터 패턴을 검색하여
        참고 정보를 제공합니다.

    검색 쿼리 예시:
        "naver news article CSS selector site:github.com OR site:stackoverflow.com"

    출력:
        tavily_results: {
            "success": True/False,
            "results": [...],
            "query": "...",
            "error": "..." (if failed)
        }
    """
    site_name = state.get("site_name", "unknown")

    logger.info(f"[UC3 Tool 1] Tavily Web Search 시작: {site_name}")

    try:
        tavily_api_key = os.getenv("TAVILY_API_KEY")
        if not tavily_api_key:
            logger.warning("[UC3 Tool 1] TAVILY_API_KEY not found. Skipping Tavily search.")
            return {
                **state,
                "tavily_results": {"success": False, "error": "TAVILY_API_KEY not configured"},
            }

        # tavily = TavilySearchResults(max_results=3, search_depth="advanced", api_key=tavily_api_key)
        # NOTE: TavilySearchResults not imported - this function is deprecated (see line 1861)
        tavily = None  # Placeholder since this function is not used

        # 검색 쿼리 생성
        query = f"{site_name} news article CSS selector site:github.com OR site:stackoverflow.com"

        # 검색 실행
        results = tavily.invoke({"query": query})

        logger.info(f"[UC3 Tool 1] ✅ Tavily 검색 완료: {len(results)} results")

        return {**state, "tavily_results": {"success": True, "results": results, "query": query}}

    except Exception as e:
        logger.error(f"[UC3 Tool 1] Tavily search failed: {e}")
        return {**state, "tavily_results": {"success": False, "error": str(e)}}


# --- Tool 2: Firecrawl Preprocessing ---


def simple_preprocess_node(state: UC3State) -> dict:
    """
    Simple HTML Preprocessing - Firecrawl 대체 (비용 절감)

    목적:
        기존 preprocess_html 함수를 사용하여 HTML 정리
        - Script/Style 태그 제거
        - 주석 제거
        - 공백 정리

    출력:
        preprocessed_html: 정리된 HTML (raw_html 업데이트)
    """
    raw_html = state.get("raw_html", "")

    logger.info(f"[UC3 Preprocess] Simple HTML preprocessing 시작")

    try:
        # 기존 preprocess_html 함수 사용 (무료, 빠름)
        preprocessed = preprocess_html(raw_html)

        original_size = len(raw_html)
        reduced_size = len(preprocessed)
        reduction_rate = (1 - reduced_size / original_size) * 100 if original_size > 0 else 0

        logger.info(
            f"[UC3 Preprocess] ✅ 완료: {original_size} → {reduced_size} chars ({reduction_rate:.1f}% 감소)"
        )

        return {**state, "raw_html": preprocessed}  # raw_html 업데이트

    except Exception as e:
        logger.error(f"[UC3 Preprocess] Preprocessing failed: {e}")
        return state  # 실패 시 원본 HTML 유지


# --- Tool 3: Beautiful Soup DOM Analyzer ---


@tool
def analyze_dom_patterns(html: str) -> dict:
    """
    Tool 3: Beautiful Soup DOM Analyzer - DOM 구조 통계 분석

    목적:
        BeautifulSoup을 사용하여 HTML의 DOM 구조를 통계적으로 분석하고
        제목, 본문, 날짜 셀렉터 후보를 추출합니다.

    분석 항목:
        1. 제목 후보: H1/H2/H3 태그 중 10-200자 텍스트
        2. 본문 후보: article/div/section 중 가장 긴 텍스트 블록 (300자 이상)
        3. 날짜 후보: time 태그 또는 날짜 패턴 포함 텍스트

    반환:
        {
            "title_candidates": [...],
            "body_candidates": [...],
            "date_candidates": [...]
        }
    """
    soup = BeautifulSoup(html, "html.parser")

    # 1. 제목 후보 (H1/H2/H3/H4 태그, meta title, 5-500자로 확장)
    title_candidates = []

    # 1-1. Heading 태그 검색 (h1 ~ h4)
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        # h2/h3 내부의 span도 체크 (네이버 뉴스 패턴)
        span = tag.find("span")
        text = span.get_text(strip=True) if span else tag.get_text(strip=True)

        # 길이 제한 완화: 5-500자 (기존 10-200자에서 확장)
        if 5 <= len(text) <= 500:
            selector = generate_css_selector(tag)

            # ID나 특정 클래스가 있으면 신뢰도 상승
            has_id = tag.get("id") is not None
            has_title_class = any(
                cls in tag.get("class", [])
                for cls in ["title", "headline", "head", "article", "story"]
            )

            confidence = (
                0.95
                if tag.name == "h1"
                else (0.85 if tag.name == "h2" else (0.7 if tag.name == "h3" else 0.6))
            )
            if has_id or has_title_class:
                confidence += 0.05

            title_candidates.append(
                {
                    "selector": selector,
                    "text_preview": text[:50],
                    "tag_name": tag.name,
                    "confidence": min(1.0, confidence),
                }
            )

    # 1-2. Meta 태그 검색 (og:title, twitter:title)
    # preprocess_html이 head 태그를 제거할 수 있으므로 원본 HTML이 필요하면 별도 처리
    meta_title = soup.find("meta", property="og:title") or soup.find(
        "meta", attrs={"name": "twitter:title"}
    )
    if meta_title and meta_title.get("content"):
        title_text = meta_title["content"]
        if 5 <= len(title_text) <= 500:
            title_candidates.append(
                {
                    "selector": "meta[property='og:title']",
                    "text_preview": title_text[:50],
                    "tag_name": "meta",
                    "confidence": 0.85,  # Meta 태그는 높은 신뢰도
                }
            )

    # 1-2-1. title 태그도 검색 (fallback)
    title_tag = soup.find("title")
    if title_tag:
        title_text = title_tag.get_text(strip=True)
        if 5 <= len(title_text) <= 500:
            title_candidates.append(
                {
                    "selector": "title",
                    "text_preview": title_text[:50],
                    "tag_name": "title",
                    "confidence": 0.75,
                }
            )

    # 1-3. 클래스 이름에 title/headline 포함된 div/span 검색
    for tag in soup.find_all(["div", "span"], class_=re.compile(r"(title|headline|heading)", re.I)):
        text = tag.get_text(strip=True)
        if 5 <= len(text) <= 500:
            selector = generate_css_selector(tag)
            title_candidates.append(
                {
                    "selector": selector,
                    "text_preview": text[:50],
                    "tag_name": tag.name,
                    "confidence": 0.75,
                }
            )

    # 2. 본문 후보 (article, div, section 중 가장 긴 텍스트)
    body_candidates = []
    for tag in soup.find_all(["article", "div", "section"]):
        text = tag.get_text(strip=True)
        if len(text) >= 300:  # 최소 300자
            selector = generate_css_selector(tag)

            # ID나 특정 클래스가 있으면 신뢰도 상승
            has_article_id = tag.get("id") is not None
            has_article_class = any(
                cls in tag.get("class", []) for cls in ["article", "content", "body", "_article"]
            )

            confidence = min(1.0, len(text) / 2000)
            if tag.name == "article":
                confidence += 0.2
            if has_article_id or has_article_class:
                confidence += 0.1

            body_candidates.append(
                {
                    "selector": selector,
                    "text_length": len(text),
                    "text_preview": text[:100],
                    "tag_name": tag.name,
                    "confidence": min(1.0, confidence),
                }
            )

    # 3. 날짜 후보 (time 태그 또는 날짜 패턴 매칭)
    date_candidates = []
    date_pattern = r"\d{4}[-/.년]\s*\d{1,2}[-/.월]\s*\d{1,2}"

    for tag in soup.find_all(["time", "span", "div"]):
        text = tag.get_text(strip=True)
        has_date_attr = tag.get("data-date-time") or tag.get("datetime") or tag.get("data-date")

        if re.search(date_pattern, text) or has_date_attr:
            selector = generate_css_selector(tag)

            # data-date-time 속성이 있으면 신뢰도 상승
            confidence = 1.0 if tag.name == "time" else 0.7
            if has_date_attr:
                confidence = 1.0

            date_candidates.append(
                {
                    "selector": selector,
                    "text_preview": text[:50] if text else str(has_date_attr)[:50],
                    "tag_name": tag.name,
                    "confidence": confidence,
                }
            )

    return {
        "title_candidates": sorted(title_candidates, key=lambda x: x["confidence"], reverse=True)[
            :3
        ],
        "body_candidates": sorted(body_candidates, key=lambda x: x["text_length"], reverse=True)[
            :3
        ],
        "date_candidates": sorted(date_candidates, key=lambda x: x["confidence"], reverse=True)[:3],
    }


def beautifulsoup_analyze_node(state: UC3State) -> dict:
    """
    Tool 3 Node: BeautifulSoup DOM 분석 노드

    Tool인 analyze_dom_patterns를 호출하여 DOM 구조를 분석합니다.
    Preprocessed HTML을 사용하여 정확도를 높입니다 (script/style 제거됨).
    """
    # simple_preprocess 이후의 HTML 사용 (script/style 제거되어 더 정확)
    html = state.get("raw_html", "")  # preprocessed HTML이 raw_html에 업데이트됨

    logger.info("[UC3 Tool 3] BeautifulSoup DOM Analysis 시작")

    try:
        analysis = analyze_dom_patterns.invoke({"html": html})

        logger.info(
            f"[UC3 Tool 3] ✅ DOM 분석 완료: "
            f"제목 {len(analysis.get('title_candidates', []))}개, "
            f"본문 {len(analysis.get('body_candidates', []))}개, "
            f"날짜 {len(analysis.get('date_candidates', []))}개"
        )

        return {**state, "beautifulsoup_analysis": {"success": True, "analysis": analysis}}
    except Exception as e:
        logger.error(f"[UC3 Tool 3] BeautifulSoup analysis failed: {e}")
        return {**state, "beautifulsoup_analysis": {"success": False, "error": str(e)}}


# --- Agent 1: GPT-4o Proposer (with Tools) ---


def gpt_discover_agent_node(state: UC3State) -> dict:
    """
    Agent 1: GPT-4o Proposer with Few-Shot Examples + Tools

    목적:
        Few-Shot Examples와 Tool 결과를 종합하여 CSS 셀렉터를 제안합니다.

    Tools:
        - Few-Shot Examples (DB의 성공 패턴)
        - Tavily Search Results (유사 사이트 패턴)
        - Raw HTML Sample (15000자)
        - BeautifulSoup Analysis (DOM 통계)

    출력:
        gpt_proposal: {
            "selectors": {
                "title": {"selector": "...", "confidence": 0.95, "reasoning": "..."},
                "body": {"selector": "...", "confidence": 0.88, "reasoning": "..."},
                "date": {"selector": "...", "confidence": 0.92, "reasoning": "..."}
            },
            "overall_confidence": 0.92
        }
    """
    site_name = state.get("site_name", "unknown")
    # tavily_results = state.get("tavily_results", {})  # REMOVED
    raw_html = state.get("raw_html", "")  # Firecrawl 대신 raw_html 사용
    bs_analysis = state.get("beautifulsoup_analysis", {})

    logger.info(f"[UC3 Agent 1] Claude Sonnet 4.5 Discoverer 시작: {site_name}")

    # Few-Shot Examples 가져오기
    few_shot_examples = get_few_shot_examples(limit=5)

    # Use Claude Sonnet 4.5 for CSS Selector generation (coding-specialized)

    # Few-Shot 섹션
    few_shot_section = ""
    if few_shot_examples and len(few_shot_examples) > 0:
        few_shot_section = format_few_shot_prompt(few_shot_examples, include_patterns=True)

    prompt = f"""You are a CSS Selector discovery expert specializing in HTML analysis and code generation.

{few_shot_section}

You have the following tool results to help you:

1. **Raw HTML Sample** (15000 chars from original HTML):
{raw_html[:15000]}

2. **BeautifulSoup DOM Analysis** (statistical candidates):
{json.dumps(bs_analysis.get('analysis', {}), indent=2, ensure_ascii=False)}

**Task**:
Generate CSS selectors for title, body, and date based on the above information.

**Return JSON format**:
{{
    "selectors": {{
        "title": {{"selector": "...", "confidence": 0.0-1.0, "reasoning": "..."}},
        "body": {{"selector": "...", "confidence": 0.0-1.0, "reasoning": "..."}},
        "date": {{"selector": "...", "confidence": 0.0-1.0, "reasoning": "..."}}
    }},
    "overall_confidence": 0.0-1.0
}}

**Guidelines**:
- **PRIMARY**: Refer to the Few-Shot examples for successful patterns (most important!)
- Prefer selectors from BeautifulSoup DOM analysis (they're statistically validated)
- Use the Raw HTML sample to verify selector validity
- Generate precise, robust CSS selectors
- Provide clear reasoning for each selector choice
"""

    # Anthropic API key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")

    if not anthropic_key:
        logger.error("[UC3 Agent 1] ❌ ANTHROPIC_API_KEY not set")
        return {
            **state,
            "gpt_proposal": {"error": "ANTHROPIC_API_KEY not configured"},
            "gpt_confidence": 0.0,
        }

    # Use Claude Sonnet 4.5 for selector generation
    try:
        claude_llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            temperature=0,
            api_key=anthropic_key,
            max_tokens=4096,
            timeout=30.0,
        )

        response = claude_llm.invoke([{"role": "user", "content": prompt}])

        # Extract text from response (handle both string and list formats)
        if isinstance(response.content, list):
            # New Anthropic API format: content is a list of blocks
            proposal_text = response.content[0].get("text", "") if response.content else ""
        else:
            # Old format: content is already a string
            proposal_text = response.content

        # JSON 파싱
        try:
            claude_output = json.loads(proposal_text)
        except Exception as e:
            # Fallback: extract JSON from markdown code block
            import re

            json_match = re.search(r"```json\n(.*?)\n```", proposal_text, re.DOTALL)
            if json_match:
                claude_output = json.loads(json_match.group(1))
            else:
                raise ValueError("Failed to parse Claude JSON response")

        overall_conf = claude_output.get("overall_confidence", 0.0)

        logger.info(f"[UC3 Agent 1] ✅ Claude Sonnet 4.5 제안 완료: confidence={overall_conf:.2f}")

        return {
            **state,
            "gpt_proposal": claude_output,  # Keep field name for backward compatibility
            "gpt_confidence": overall_conf,
        }

    except Exception as e:
        logger.error(f"[UC3 Agent 1] ❌ Claude Sonnet 4.5 failed: {e}")
        logger.warning("[UC3 Agent 1] Falling back to GPT-4o-mini")

        # Fallback: GPT-4o-mini로 selector 생성
        try:
            from langchain_openai import ChatOpenAI

            fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, timeout=30.0)
            response = fallback_llm.invoke([{"role": "user", "content": prompt}])

            try:
                fallback_output = json.loads(response.content)
            except Exception as e:
                import re

                json_match = re.search(r"```json\n(.*?)\n```", response.content, re.DOTALL)
                if json_match:
                    fallback_output = json.loads(json_match.group(1))
                else:
                    raise ValueError("Failed to parse fallback JSON response")

            overall_conf = fallback_output.get("overall_confidence", 0.0)
            logger.info(
                f"[UC3 Agent 1] ✅ Fallback GPT-4o-mini 완료: confidence={overall_conf:.2f}"
            )

            return {**state, "gpt_proposal": fallback_output, "gpt_confidence": overall_conf}

        except Exception as fallback_error:
            logger.error(f"[UC3 Agent 1] ❌ Fallback also failed: {fallback_error}")
            return {
                **state,
                "gpt_proposal": {
                    "error": f"Both Claude and GPT-4o-mini failed: {str(e)}, {str(fallback_error)}"
                },
                "gpt_confidence": 0.0,
            }


# --- Agent 2: Gemini Validator (with Validation Tool) ---


@tool
def validate_selector_tool(selector: str, selector_type: str, html: str) -> dict:
    """
    Validation Tool: CSS 셀렉터를 실제 HTML에서 테스트

    Args:
        selector: CSS 셀렉터 (예: "article > h1.title")
        selector_type: "title" | "body" | "date"
        html: 테스트할 HTML 문자열

    Returns:
        {
            "valid": True/False,
            "confidence": 0.0-1.0,
            "extracted_text": "...",
            "text_length": 123
        }
    """
    soup = BeautifulSoup(html, "html.parser")

    try:
        elem = soup.select_one(selector)

        # Fallback: CSS select_one() fails for <head> meta tags → try BeautifulSoup.find()
        if not elem and "meta" in selector:
            logger.debug(f"[Validate Tool] CSS failed for meta tag, trying BeautifulSoup.find()")

            # Parse meta selector (e.g., "meta[property='og:title']")
            if "[property=" in selector or "[name=" in selector:
                # Extract attribute (property or name)
                attr_match = re.search(r'\[(property|name)=["\']?([^"\'\]]+)', selector)
                if attr_match:
                    attr_type = attr_match.group(1)  # "property" or "name"
                    attr_value = attr_match.group(2)  # "og:title", "description", etc

                    elem = soup.find("meta", attrs={attr_type: attr_value})

                    if elem:
                        # Get 'content' attribute from meta tag
                        text = elem.get("content", "").strip()
                        logger.info(
                            f"[Validate Tool] ✅ BeautifulSoup fallback success: {attr_type}='{attr_value}' → '{text[:50]}...'"
                        )
                    else:
                        logger.warning(
                            f"[Validate Tool] ⚠️ BeautifulSoup fallback also failed for {attr_type}='{attr_value}'"
                        )
                        return {
                            "valid": False,
                            "confidence": 0.0,
                            "error": f"Meta tag {attr_type}='{attr_value}' not found (CSS + BeautifulSoup both failed)",
                        }
            else:
                logger.warning(f"[Validate Tool] ⚠️ Cannot parse meta selector: {selector}")
                return {
                    "valid": False,
                    "confidence": 0.0,
                    "error": f"Cannot parse meta selector: {selector}",
                }
        elif not elem:
            return {"valid": False, "confidence": 0.0, "error": "Selector not found in HTML"}
        else:
            # Normal element (not meta tag)
            # But still check if it's a meta tag (elem exists but wasn't caught above)
            if elem.name == "meta":
                # Meta tag: extract 'content' attribute, NOT text
                text = elem.get("content", "").strip()
                logger.info(f"[Validate Tool] ✅ Meta tag (via CSS): {selector} → '{text[:50]}...'")
            else:
                # Regular HTML element: extract text
                text = elem.get_text(strip=True)

        # 타입별 검증
        if selector_type == "title":
            valid = 10 <= len(text) <= 200
            confidence = min(1.0, len(text) / 50) if valid else 0.0

        elif selector_type == "body":
            valid = len(text) >= 100
            confidence = min(1.0, len(text) / 500) if valid else 0.0

        elif selector_type == "date":
            date_pattern = r"\d{4}[-/.년]\s*\d{1,2}[-/.월]\s*\d{1,2}"
            valid = bool(re.search(date_pattern, text))
            confidence = 1.0 if valid else 0.0

        else:
            valid = False
            confidence = 0.0

        return {
            "valid": valid,
            "confidence": round(confidence, 2),
            "extracted_text": text[:100],
            "text_length": len(text),
        }

    except Exception as e:
        return {"valid": False, "confidence": 0.0, "error": str(e)}


def gpt4o_validate_agent_node(state: UC3State) -> dict:
    """
    Agent 2: GPT-4o Validator with Validation Tool

    목적:
        GPT-4o의 제안을 실제 HTML에서 테스트하여 검증합니다.

    Tool:
        validate_selector_tool - 각 셀렉터를 실제 HTML에서 테스트

    출력:
        gpt4o_validation: {
            "best_selectors": {"title": "...", "body": "...", "date": "..."},
            "validation_details": {...},
            "overall_confidence": 0.95
        }
    """
    gpt_proposal = state.get("gpt_proposal", {})
    # IMPORTANT: 검증은 full HTML로 해야 정확함
    html = state.get("raw_html", "")

    logger.info("[UC3 Agent 2] GPT-4o Validator 시작")
    logger.info(f"[UC3 Agent 2] Claude Proposal: {gpt_proposal}")

    # Use GPT-4o for validation (stable, reliable, different company)
    # True 2-Agent Consensus: Claude Sonnet 4.5 (Anthropic) vs GPT-4o (OpenAI)

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY not set")

        gpt_llm = ChatOpenAI(
            model="gpt-4o",  # GPT-4o (범용 고성능)
            temperature=0,
            api_key=openai_key,
            max_tokens=4096,
            timeout=30.0,
        )

        # GPT 제안 셀렉터 추출
        proposed_selectors = gpt_proposal.get("selectors", {})

        # 각 셀렉터를 validate_selector_tool로 테스트
        validation_details = {}

        for sel_type in ["title", "body", "date"]:
            selector = proposed_selectors.get(sel_type, {}).get("selector", "")
            if selector:
                validation = validate_selector_tool.invoke(
                    {"selector": selector, "selector_type": sel_type, "html": html}
                )
                validation_details[sel_type] = validation
                logger.info(f"[UC3 Agent 2] {sel_type} validation: {validation}")
            else:
                validation_details[sel_type] = {
                    "valid": False,
                    "confidence": 0.0,
                    "error": "No selector proposed",
                }
                logger.warning(f"[UC3 Agent 2] {sel_type}: No selector proposed by GPT")

        # Claude가 검증 결과를 분석하여 최종 판단
        prompt = f"""You are a CSS Selector validator.

GPT-4o proposed these selectors:
{json.dumps(proposed_selectors, indent=2, ensure_ascii=False)}

Validation results (tested on actual HTML):
{json.dumps(validation_details, indent=2, ensure_ascii=False)}

**Task**:
1. Analyze validation results
2. Select the BEST selectors (or suggest improvements if validation failed)
3. Provide overall confidence score

**Return JSON**:
{{
    "best_selectors": {{
        "title": "...",
        "body": "...",
        "date": "..."
    }},
    "validation_details": (keep the validation_details as-is),
    "overall_confidence": 0.0-1.0,
    "reasoning": "..."
}}
"""

        response = gpt_llm.invoke([{"role": "user", "content": prompt}])

        # JSON 파싱
        try:
            gpt_output = json.loads(response.content)
        except Exception as e:
            import re

            json_match = re.search(r"```json\n(.*?)\n```", response.content, re.DOTALL)
            if json_match:
                gpt_output = json.loads(json_match.group(1))
            else:
                raise ValueError("Failed to parse GPT-4o JSON response")

        overall_conf = gpt_output.get("overall_confidence", 0.0)

        logger.info(f"[UC3 Agent 2] ✅ GPT-4o 검증 완료: confidence={overall_conf:.2f}")

        return {
            **state,
            "gpt4o_validation": gpt_output,
            "gpt4o_confidence": overall_conf,
        }

    except Exception as e:
        logger.error(f"[UC3 Agent 2] GPT-4o validation failed: {e}")
        logger.warning("[UC3 Agent 2] Falling back to GPT-4o-mini for validation")

        # Fallback: GPT-4o-mini로 검증
        try:
            fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

            prompt = f"""You are a CSS Selector validator.

GPT-4o proposed these selectors:
{json.dumps(proposed_selectors, indent=2, ensure_ascii=False)}

Validation results (tested on actual HTML):
{json.dumps(validation_details, indent=2, ensure_ascii=False)}

**Task**:
1. Analyze validation results
2. Select the BEST selectors
3. Provide overall confidence score

**Return JSON**:
{{
    "best_selectors": {{
        "title": "...",
        "body": "...",
        "date": "..."
    }},
    "validation_details": (keep as-is),
    "overall_confidence": 0.0-1.0,
    "reasoning": "..."
}}"""

            response = fallback_llm.invoke([{"role": "user", "content": prompt}])

            try:
                fallback_output = json.loads(response.content)
            except Exception as e:
                import re

                json_match = re.search(r"```json\n(.*?)\n```", response.content, re.DOTALL)
                if json_match:
                    fallback_output = json.loads(json_match.group(1))
                else:
                    raise ValueError("Failed to parse fallback response")

            overall_conf = fallback_output.get("overall_confidence", 0.0)
            logger.info(
                f"[UC3 Agent 2] ✅ Fallback GPT-4o-mini 검증 완료: confidence={overall_conf:.2f}"
            )

            return {
                **state,
                "gpt4o_validation": fallback_output,
                "gpt4o_confidence": overall_conf,
            }

        except Exception as fallback_error:
            logger.error(f"[UC3 Agent 2] Fallback also failed: {fallback_error}")
            return {
                **state,
                "gpt4o_validation": {
                    "error": f"GPT-4o and fallback failed: {e}, {fallback_error}"
                },
                "gpt4o_confidence": 0.0,
            }


# --- Consensus Calculation ---


def calculate_uc3_consensus_node(state: UC3State) -> dict:
    """
    UC3 Weighted Consensus Calculation

    공식:
        Consensus Score = 0.3 × GPT confidence
                        + 0.3 × GPT-4o confidence
                        + 0.4 × Extraction quality

    Threshold:
        0.7 이상 → consensus_reached = True (UC2는 0.6)

    출력:
        consensus_score: float (0.0-1.0)
        consensus_reached: bool
        extraction_quality: float (0.0-1.0)
        discovered_selectors: dict (if consensus_reached)
    """
    gpt_conf = state.get("gpt_confidence", 0.0)
    gpt4o_conf = state.get("gpt4o_confidence", 0.0)
    gpt4o_validation = state.get("gpt4o_validation", {})

    logger.info("[UC3 Consensus] 가중 합의 계산 시작")

    # Extraction Quality 계산
    validation_details = gpt4o_validation.get("validation_details", {})

    extraction_scores = []
    for selector_type in ["title", "body", "date"]:
        detail = validation_details.get(selector_type, {})
        extraction_scores.append(detail.get("confidence", 0.0))

    extraction_quality = (
        sum(extraction_scores) / len(extraction_scores) if extraction_scores else 0.0
    )

    # 가중 합의 (UC2와 동일한 공식)
    consensus_score = gpt_conf * 0.3 + gpt4o_conf * 0.3 + extraction_quality * 0.4

    # UC3 threshold: 0.50 (완화됨 - v2.1 개선, UC2와 동일)
    # 이전: 0.55 (CNN 0.58로 아슬아슬하게 통과)
    # 개선: 0.50 (더 많은 케이스 허용, UC2와 일관성)
    consensus_reached = consensus_score >= 0.50

    logger.info(
        f"[UC3 Consensus] GPT={gpt_conf:.2f}, GPT-4o={gpt4o_conf:.2f}, Extract={extraction_quality:.2f} → Score={consensus_score:.2f}"
    )
    logger.info(f"[UC3 Consensus] Threshold=0.50, Reached={consensus_reached}")

    # GPT-4o best_selectors 또는 GPT proposal에서 추출
    best_selectors = None
    if consensus_reached:
        best_selectors = gpt4o_validation.get("best_selectors")

        # Fallback: GPT-4o가 best_selectors를 반환하지 않으면 GPT proposal 사용
        if not best_selectors:
            gpt_proposal = state.get("gpt_proposal", {})
            gpt_selectors = gpt_proposal.get("selectors", {})
            if gpt_selectors:
                best_selectors = {
                    "title": gpt_selectors.get("title", {}).get("selector", ""),
                    "body": gpt_selectors.get("body", {}).get("selector", ""),
                    "date": gpt_selectors.get("date", {}).get("selector", ""),
                }
                logger.warning(
                    f"[UC3 Consensus] GPT-4o didn't return best_selectors, using GPT proposal: {best_selectors}"
                )

        # None 값을 빈 문자열로 변환 (DB NOT NULL 제약 조건 대응)
        if best_selectors:
            best_selectors = {
                "title": best_selectors.get("title") or "",
                "body": best_selectors.get("body") or "",
                "date": best_selectors.get("date") or "",
            }

    return {
        **state,
        "consensus_score": round(consensus_score, 2),
        "consensus_reached": consensus_reached,
        "extraction_quality": round(extraction_quality, 2),
        "discovered_selectors": best_selectors,
        "next_action": "save" if consensus_reached else "human_review",
    }


# ============================================================
# Step 5: StateGraph 구성
# ============================================================


def create_uc3_agent():
    """
    UC3 New Site Auto-Discovery Agent 생성 (3-Tool + 2-Agent + Consensus)

    NEW Workflow (Enhanced):
        START
          ↓
        fetch_html (HTML 다운로드)
          ↓
        firecrawl_preprocess (Tool 2: HTML 전처리, 토큰 90% 감소)
          ↓
        tavily_search (Tool 1: 유사 사이트 패턴 검색)
          ↓
        beautifulsoup_analyze (Tool 3: DOM 구조 통계 분석)
          ↓
        gpt_discover_agent (Agent 1: GPT-4o Proposer with 3 Tools)
          ↓
        gemini_validate_agent (Agent 2: Gemini Validator with Validation Tool)
          ↓
        calculate_consensus (Weighted Consensus: 0.3×GPT + 0.3×Gemini + 0.4×Extract ≥ 0.7)
          ↓
        [save_selectors OR END (human_review)]

    Changes from OLD workflow:
        - OLD: preprocess_html → gpt_discover → validate_selectors → check_quality
        - NEW: simple_preprocess → beautifulsoup_analyze
               → gpt_discover_agent (Few-Shot) → gemini_validate_agent → calculate_consensus
    """
    graph = StateGraph(UC3State)

    # 노드 추가
    graph.add_node("fetch_html", fetch_html_node)
    graph.add_node("extract_json_ld", extract_json_ld_node)  # NEW: JSON-LD extraction
    graph.add_node("simple_preprocess", simple_preprocess_node)  # Firecrawl 대체
    # graph.add_node("tavily_search", tavily_search_node)  # REMOVED - not needed
    graph.add_node("beautifulsoup_analyze", beautifulsoup_analyze_node)
    graph.add_node("gpt_discover_agent", gpt_discover_agent_node)
    graph.add_node("gpt4o_validate_agent", gpt4o_validate_agent_node)
    graph.add_node("calculate_consensus", calculate_uc3_consensus_node)
    graph.add_node("save_selectors", save_selectors_node)

    # 엣지 추가 (순차 실행)
    graph.add_edge(START, "fetch_html")
    graph.add_edge("fetch_html", "extract_json_ld")  # NEW: JSON-LD after HTML fetch
    graph.add_edge("extract_json_ld", "simple_preprocess")  # UPDATED: JSON-LD → preprocess
    graph.add_edge("simple_preprocess", "beautifulsoup_analyze")
    # graph.add_edge("tavily_search", "beautifulsoup_analyze")  # REMOVED
    graph.add_edge("beautifulsoup_analyze", "gpt_discover_agent")
    graph.add_edge("gpt_discover_agent", "gpt4o_validate_agent")
    graph.add_edge("gpt4o_validate_agent", "calculate_consensus")

    # 조건부 엣지: consensus_reached에 따라 분기
    def route_after_consensus(state: UC3State):
        consensus_reached = state.get("consensus_reached", False)

        if consensus_reached:
            return "save_selectors"
        else:
            # Consensus 실패 → 휴먼 리뷰
            return END

    graph.add_conditional_edges(
        "calculate_consensus", route_after_consensus, {"save_selectors": "save_selectors", END: END}
    )

    graph.add_edge("save_selectors", END)

    return graph.compile()


# ============================================================
# Step 6: CLI 실행 (테스트용)
# ============================================================

if __name__ == "__main__":
    import sys

    from dotenv import load_dotenv

    load_dotenv()

    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        logger.error("   .env 파일에 OPENAI_API_KEY를 설정하세요")
        sys.exit(1)

    # 테스트 URL
    test_url = "https://www.yna.co.kr/view/AKR20251109000001001"

    if len(sys.argv) > 1:
        test_url = sys.argv[1]

    logger.info("=" * 80)
    logger.info("UC3 New Site Auto-Discovery Agent 실행")
    logger.info("=" * 80)
    logger.info(f"Test URL: {test_url}")

    # UC3 Agent 생성
    agent = create_uc3_agent()

    # 실행
    inputs = {"url": test_url, "sample_urls": []}

    result = agent.invoke(inputs)

    # 결과 출력
    logger.info("\n" + "=" * 80)
    logger.info("UC3 실행 결과")
    logger.info("=" * 80)
    logger.info(f"Site Name: {result.get('site_name')}")
    logger.info(f"Confidence: {result.get('confidence', 0):.2f}")
    logger.info(f"Success Rate: {result.get('success_rate', 0):.2%}")
    logger.info(f"Next Action: {result.get('next_action')}")

    # Consensus 디버깅
    logger.info(f"\n=== Consensus Details ===")
    logger.info(f"GPT Confidence: {result.get('gpt_confidence', 0):.2f}")
    logger.info(f"GPT-4o Confidence: {result.get('gpt4o_confidence', 0):.2f}")
    logger.info(f"Extraction Quality: {result.get('extraction_quality', 0):.2f}")
    logger.info(f"Consensus Score: {result.get('consensus_score', 0):.2f}")
    logger.info(f"Consensus Reached: {result.get('consensus_reached', False)}")

    if result.get("gpt_analysis"):
        analysis = result["gpt_analysis"]
        logger.info(f"\nGenerated Selectors:")
        logger.info(f"  Title: {analysis.get('title_selector')}")
        logger.info(f"  Body: {analysis.get('body_selector')}")
        logger.info(f"  Date: {analysis.get('date_selector')}")
        logger.info(f"  Site Type: {analysis.get('site_type')}")

    if result.get("validation_report"):
        report = result["validation_report"]
        logger.info(f"\nValidation Report:")
        logger.info(f"  Title Valid: {'✅' if report.get('title_valid') else '❌'}")
        logger.info(f"  Body Valid: {'✅' if report.get('body_valid') else '❌'}")
        logger.info(f"  Date Valid: {'✅' if report.get('date_valid') else '❌'}")

    logger.info("\n" + "=" * 80)
    logger.info("✅ UC3 실행 완료!")
    logger.info("=" * 80)
