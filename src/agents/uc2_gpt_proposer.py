"""
CrawlAgent - UC2 GPT-4o-mini CSS Selector Proposer (MVP)
Created: 2025-11-08 (Sprint 1)
Updated: 2025-11-12 (Few-Shot Examples 추가)

GPT-4o-mini가 HTML을 분석하여 CSS Selector를 제안하는 Agent
Lean Startup MVP: 최소 기능만 구현 → 즉시 검증
"""

import json
import os
import time
from typing import Dict, Optional

from loguru import logger
from openai import OpenAI

from src.agents.few_shot_retriever import format_few_shot_prompt, get_few_shot_examples

# OpenAI API 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def propose_selectors(
    url: str,
    html_content: str,
    site_name: str = "unknown",
    previous_selectors: Optional[Dict[str, str]] = None,
) -> Dict:
    """
    GPT-4o-mini에게 CSS Selector 제안 요청 (MVP)

    Args:
        url: 크롤링 대상 URL
        html_content: HTML 원문 (최대 50KB로 자동 제한)
        site_name: 사이트명 (yonhap, naver, bbc 등)
        previous_selectors: 이전 Selector (실패한 것) - Optional

    Returns:
        {
            "title_selector": "h1.tit",
            "body_selector": "div.article p",
            "date_selector": "span.date-time",
            "reasoning": "연합뉴스 표준 HTML 구조 기반",
            "confidence": 90  # 0-100
        }

    Example:
        >>> result = propose_selectors(
        ...     url="https://www.yna.co.kr/view/AKR...",
        ...     html_content="<html>...</html>",
        ...     site_name="yonhap"
        ... )
        >>> print(result['title_selector'])
        'h1.tit'
    """

    # HTML 크기 제한 (GPT 토큰 절약)
    MAX_HTML_SIZE = 50000  # 50KB
    if len(html_content) > MAX_HTML_SIZE:
        logger.warning(
            f"[GPT Proposer] HTML 크기 {len(html_content)} bytes → {MAX_HTML_SIZE} bytes로 제한"
        )
        html_content = html_content[:MAX_HTML_SIZE]

    # Few-Shot Examples 가져오기
    few_shot_examples = get_few_shot_examples(limit=5)

    # 프롬프트 생성
    prompt = _build_prompt(url, html_content, site_name, previous_selectors, few_shot_examples)

    # GPT-4o-mini 호출 (재시도 로직 포함)
    max_retries = 3
    retry_delay = 2  # 초

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a CSS selector expert specializing in web scraping. Always respond with valid JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,  # 일관된 결과를 위해 낮은 temperature
                response_format={"type": "json_object"},  # JSON mode 강제
            )

            # JSON 파싱
            result = json.loads(response.choices[0].message.content.strip())

            # 로깅
            confidence = result.get("confidence", 0)
            reasoning = result.get("reasoning", "")[:100]
            logger.success(f"[GPT Proposer] ✅ confidence={confidence}% - {reasoning}")

            return result

        except Exception as e:
            error_msg = str(e)

            # Rate Limit 감지
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[GPT Proposer] ⚠️ Rate Limit (시도 {attempt + 1}/{max_retries}). "
                        f"{retry_delay}초 대기 후 재시도..."
                    )
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                    continue
                else:
                    logger.error(f"[GPT Proposer] ❌ Rate Limit 재시도 실패")
            else:
                # 다른 에러
                logger.error(f"[GPT Proposer] ❌ 예외 발생: {e}")

            # 실패 응답 반환
            return {
                "title_selector": None,
                "body_selector": None,
                "date_selector": None,
                "reasoning": f"GPT 호출 실패: {error_msg[:100]}",
                "confidence": 0,
            }

    # 모든 재시도 실패 (안전망)
    return {
        "title_selector": None,
        "body_selector": None,
        "date_selector": None,
        "reasoning": "모든 재시도 실패",
        "confidence": 0,
    }


def _build_prompt(
    url: str,
    html_content: str,
    site_name: str,
    previous_selectors: Optional[Dict[str, str]],
    few_shot_examples: list = None,
) -> str:
    """GPT-4o-mini용 프롬프트 생성 (Few-Shot Examples 포함)"""

    # Few-Shot Examples 섹션
    few_shot_section = ""
    if few_shot_examples and len(few_shot_examples) > 0:
        few_shot_section = "## 참고: 성공한 뉴스 사이트 Selector 패턴\n\n"
        few_shot_section += format_few_shot_prompt(few_shot_examples, include_patterns=True)

    # 이전 Selector 정보 (있을 경우)
    prev_info = ""
    if previous_selectors:
        prev_info = f"""
## 이전 Selector (실패함 - 사용하지 마세요!)
- Title: {previous_selectors.get('title_selector', 'N/A')}
- Body: {previous_selectors.get('body_selector', 'N/A')}
- Date: {previous_selectors.get('date_selector', 'N/A')}
"""

    prompt = f"""
당신은 웹 크롤링 전문가입니다. HTML을 분석하여 뉴스 기사를 추출할 CSS Selector를 제안하세요.

{few_shot_section}

## 입력 정보
- **사이트**: {site_name}
- **URL**: {url}
{prev_info}

## HTML 샘플 (처음 20000자)
```html
{html_content[:20000]}
```

## 임무
다음 3가지 요소를 추출할 **CSS Selector**를 제안하세요:
1. **title**: 기사 제목 (보통 h1, h2 태그)
2. **body**: 기사 본문 전체 (여러 p 태그일 수 있음)
3. **date**: 발행일 (time, span 태그)

## 제약사항
- **CSS Selector만 사용** (XPath 금지)
- 가능한 **단순하고 안정적인** Selector 선호
- class, id 우선 사용 (nth-child 최소화)
- 본문은 **여러 요소**일 수 있음 (예: "div.article-body p")

## 출력 형식 (JSON만! 설명 금지)
{{
  "title_selector": "h1.article-title",
  "body_selector": "div.article-content p",
  "date_selector": "time.published-date",
  "reasoning": "왜 이 Selector를 선택했는지 1-2문장으로 설명",
  "confidence": 85
}}

**중요**:
- JSON 외의 텍스트 절대 출력 금지
- confidence는 0-100 (높을수록 확신)
- reasoning은 간결하게 (50자 이내)
"""

    return prompt


# 편의 함수: 간단한 테스트용
def propose_selectors_simple(url: str, html_content: str) -> Dict:
    """
    간단한 테스트용 함수 (site_name, previous_selectors 생략)

    Example:
        >>> result = propose_selectors_simple(url, html)
    """
    return propose_selectors(url, html_content, site_name="unknown", previous_selectors=None)
