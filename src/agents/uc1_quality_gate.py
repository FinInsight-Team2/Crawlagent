"""
CrawlAgent - UC1 LLM Quality Gate
Created: 2025-11-04
Updated: 2025-11-04 - Switched to GPT-4o-mini

GPT-4o-mini 기반 콘텐츠 품질 검증

핵심 기능:
- 모든 카테고리 뉴스 품질 검증 (정치, 경제, 사회, 국제 등)
- 광고/보도자료 자동 제외
- 카테고리 적합성 검증
- 99% 정확도 목표

비용: OpenAI GPT-4o-mini (빠르고 안정적)
"""

import json
import os
from typing import Dict, Literal

from openai import OpenAI
from loguru import logger

# OpenAI API 설정
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def validate_quality(
    content_type: Literal["news", "blog", "community"],
    title: str,
    body: str,
    date: str,
    category: str,
    category_kr: str,
    url: str,
) -> Dict:
    """
    LLM 기반 콘텐츠 품질 검증

    Args:
        content_type: 콘텐츠 타입 (news/blog/community)
        title: 제목
        body: 본문 (처음 1000자만 전달)
        date: 발행일
        category: 카테고리 (예: economy)
        category_kr: 한글 카테고리 (예: 경제)
        url: URL

    Returns:
        {
            "decision": "pass" | "reject" | "uncertain",
            "confidence": 95,  # 0-100
            "category_match": true/false,
            "content_type_detected": "news" | "ad" | "press_release",
            "body_complete": true/false,
            "date_present": true/false,
            "reasoning": "..."
        }
    """
    # Content-Type별 프롬프트 선택
    if content_type == "news":
        prompt = get_news_validation_prompt(
            title, body[:1000], date, category, category_kr, url
        )
    elif content_type == "blog":
        prompt = get_blog_validation_prompt(title, body[:1000], category_kr)
    elif content_type == "community":
        prompt = get_community_validation_prompt(title, body[:1000])
    else:
        raise ValueError(f"Unknown content_type: {content_type}")

    # GPT-4o-mini 호출 (재시도 로직 포함)
    max_retries = 3
    retry_delay = 2  # OpenAI는 Rate Limit이 넉넉하므로 2초로 단축
    import time

    for attempt in range(max_retries):
        try:
            # GPT-4o-mini 호출 (JSON mode)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a news quality validation expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,  # 일관된 결과를 위해 낮은 temperature
                response_format={"type": "json_object"}  # JSON mode 강제
            )

            # JSON 파싱
            response_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"[UC1 Quality Gate] JSON 파싱 실패: {e}")
                logger.error(f"[UC1 Quality Gate] Response: {response_text[:500]}")
                # JSON 파싱 실패 시 재시도 없이 uncertain 반환
                return {
                    "decision": "uncertain",
                    "confidence": 50,
                    "category_match": None,
                    "content_type_detected": "unknown",
                    "body_complete": None,
                    "date_present": bool(date),
                    "reasoning": f"JSON 파싱 실패: {str(e)}"
                }

            logger.info(
                f"[UC1 Quality Gate] {result['decision']} "
                f"(confidence: {result['confidence']}) - {title[:50]}..."
            )

            return result

        except Exception as e:
            error_msg = str(e)

            # Rate Limit 에러 감지 (OpenAI)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                if attempt < max_retries - 1:
                    logger.warning(
                        f"[UC1 Quality Gate] Rate Limit 발생 (시도 {attempt + 1}/{max_retries}). "
                        f"{retry_delay}초 대기 후 재시도..."
                    )
                    time.sleep(retry_delay)
                    continue
                else:
                    logger.error(f"[UC1 Quality Gate] Rate Limit 재시도 실패: {e}")
                    return {
                        "decision": "uncertain",
                        "confidence": 50,
                        "category_match": None,
                        "content_type_detected": "unknown",
                        "body_complete": None,
                        "date_present": bool(date),
                        "reasoning": f"Rate Limit 초과"
                    }
            else:
                # Rate Limit 아닌 다른 에러
                logger.error(f"[UC1 Quality Gate] 예외 발생: {e}")
                return {
                    "decision": "uncertain",
                    "confidence": 50,
                    "category_match": None,
                    "content_type_detected": "unknown",
                    "body_complete": None,
                    "date_present": bool(date),
                    "reasoning": f"예외 발생: {str(e)}"
                }

    # 모든 재시도 실패 (여기 도달하면 안 됨 - 안전망)
    return {
        "decision": "uncertain",
        "confidence": 50,
        "category_match": None,
        "content_type_detected": "unknown",
        "body_complete": None,
        "date_present": bool(date),
        "reasoning": "모든 재시도 실패"
    }


def get_news_validation_prompt(
    title: str,
    body_preview: str,
    date: str,
    category: str,
    category_kr: str,
    url: str
) -> str:
    """
    뉴스 기사 검증을 위한 GPT 프롬프트 생성 (모든 카테고리 대응)

    이 프롬프트는 GPT-4o-mini가 뉴스 기사의 품질을 엄격하게 검증하도록 설계되었습니다.
    4가지 검증 기준을 명시하여 일관된 품질 관리를 보장합니다:
    1. 카테고리 적합성: 목표 카테고리와 정확히 일치하는가
    2. 콘텐츠 유형: 순수 뉴스인가 (광고/보도자료 제외)
    3. 본문 완전성: 5W1H 포함 여부, 500자 이상
    4. 발행일 존재: 날짜 정보가 있는가

    Args:
        title: 기사 제목
        body_preview: 본문 처음 1000자
        date: 발행일 (ISO 8601 형식)
        category: 카테고리 영문명 (예: economy)
        category_kr: 카테고리 한글명 (예: 경제)
        url: 기사 URL

    Returns:
        str: GPT-4o-mini에게 전달할 프롬프트 텍스트
    """
    return f"""
당신은 뉴스 크롤링 품질 검증 전문가입니다.

## 임무
추출된 뉴스 기사가 수집 기준에 적합한지 **엄격하게** 검증하세요.

## 입력 데이터
- **목표 카테고리**: {category_kr} ({category})
- **제목**: {title}
- **본문** (처음 1000자): {body_preview}
- **발행일**: {date}
- **URL**: {url}

## 검증 기준 (모두 통과해야 함!)

### 1. 카테고리 적합성 (Category Match)
**기준**: 기사 내용이 목표 카테고리와 **정확히** 일치하는가?

**카테고리별 예시**:

**경제 (economy)**:
✓ 삼성전자 실적, 코스피 지수, 금리 정책, 부동산 시장, 환율, 기업 인수합병
✗ BTS 신곡 발매, 축구 경기 결과, 정치인 발언 (경제 정책 제외)

**정치 (politics)**:
✓ 국회 법안, 대통령 발언, 정당 활동, 선거, 정부 정책
✗ 주식 시장 동향, 연예인 사생활, 스포츠 경기

**사회 (society)**:
✓ 범죄, 사건사고, 교육, 복지, 환경, 재난, 지역 뉴스
✗ 정치 법안, 경제 지표, 해외 뉴스 (국내 사회 영향 제외)

**국제 (international)**:
✓ 해외 정치, 국제 분쟁, 외교, 글로벌 경제, 해외 사건
✗ 국내 정치, 국내 기업 뉴스 (해외 진출 제외)

**IT/과학 (tech/science)**:
✓ 기술 혁신, 신제품, AI, 우주, 의학, 과학 연구
✗ 기업 실적만 다룬 기사 (기술 내용 없음)

**판단**:
- 제목과 본문 모두 목표 카테고리에 속해야 함
- 카테고리가 애매하면 본문 내용의 **주된 초점**으로 판단
- 카테고리가 명확히 다르면 **무조건 reject**

### 2. 콘텐츠 유형 검증 (Content Type)
**기준**: 순수한 뉴스 기사인가? (광고/보도자료/홍보성 아님)

**Reject 대상** (무조건 reject):
❌ 광고: "지금 바로 구매", "할인 이벤트", "특가 세일"
❌ 보도자료: 기업 홍보만 (예: "~회사가 ~제품을 출시했다고 밝혔다" - 분석/영향 없음)
❌ 홍보성: "~강좌 모집", "~행사 안내", "~채용 공고"
❌ 목록형: "오늘의 날씨", "환율 정보", "부고" (본문 없음)
❌ 단순 발표문: 정부/기업 발표문 그대로 복사 (기자 코멘트 없음)

**Accept 대상** (pass):
✓ 5W1H 뉴스: "누가, 언제, 어디서, 무엇을, 왜, 어떻게" 명확
✓ 심층 분석: "~에 대한 전망", "~의 영향", "전문가 의견"
✓ 인터뷰: "~는 ~라고 말했다" + 기자 코멘트
✓ 팩트 중심: 객관적 사실 + 배경 설명

### 3. 본문 완전성 (Body Completeness)
**기준**: 본문이 완전히 추출되었는가?

**확인 사항**:
✓ 길이: 500자 이상 (짧은 속보는 200자 허용)
✓ 5W1H 포함 여부
✓ 문장 완결성: 중간에 끊기지 않음
✓ 광고 혼입 여부: "관련 기사", "이 시각 인기 기사", "추천 상품" 등 제외

### 4. 발행일 존재 (Date Present)
**기준**: 발행일이 명확히 존재하는가?

**확인**:
✓ 발행일 형식: ISO 8601 또는 "YYYY-MM-DD"
✗ 발행일이 없으면 → reject (뉴스가 아닐 가능성)

## 출력 형식 (JSON만! 다른 텍스트 출력 금지)

{{
  "category_match": true,
  "content_type_detected": "news",
  "body_complete": true,
  "date_present": true,
  "confidence": 95,
  "decision": "pass",
  "reasoning": "경제 카테고리 적합 (삼성전자 실적 분석), 5W1H 포함, 본문 완전, 광고 아님"
}}

## Decision 규칙
- **pass**: 모든 기준 통과 + confidence >= 95
- **reject**: 하나라도 실패 (광고, 다른 카테고리, 본문 불완전)
- **uncertain**: 애매한 경우 (70 <= confidence < 95) → UC2 발동

## 중요!
- **엄격하게** 평가하세요. 의심스러우면 reject.
- 광고/보도자료/홍보성은 **무조건 reject**.
- 카테고리가 다르면 **무조건 reject**.
- 본문이 500자 미만이면 내용 확인 후 판단.
- JSON 외의 텍스트 출력 금지 (설명 불필요)
"""


def get_blog_validation_prompt(title: str, body_preview: str, category_kr: str) -> str:
    """
    블로그 검증 프롬프트 (Phase 2용 - 미리 준비)
    """
    return f"""
블로그 콘텐츠 품질 검증 (재테크/투자/데이터 분석 중심)

입력:
- 제목: {title}
- 본문: {body_preview}
- 목표 분야: {category_kr}

검증 기준:
1. 콘텐츠 유형: 분석/의견/튜토리얼 (광고 아님)
2. 전문성: 구체적 사례/데이터 포함
3. 가독성: 1000자 이상, 명확한 구조
4. 분야 적합성: 재테크/투자/데이터 관련

출력 (JSON):
{{
  "content_type_detected": "analysis" | "tutorial" | "ad",
  "expertise_level": 4,
  "readability": 5,
  "category_match": true,
  "confidence": 92,
  "decision": "pass",
  "reasoning": "..."
}}
"""


def get_community_validation_prompt(title: str, body_preview: str) -> str:
    """
    커뮤니티 검증 프롬프트 (Phase 2용 - 미리 준비)
    """
    return f"""
커뮤니티 게시글 품질 검증 (금융/경제 중심)

입력:
- 제목: {title}
- 본문: {body_preview}

검증 기준:
1. 인사이트 가치: 독특한 관점/정보
2. 스팸 여부: 홍보/낚시성 제외
3. 토론 가치: 의미 있는 의견

출력 (JSON):
{{
  "has_insight": true,
  "is_spam": false,
  "discussion_value": 4,
  "confidence": 88,
  "decision": "pass",
  "reasoning": "..."
}}
"""
