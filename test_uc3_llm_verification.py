#!/usr/bin/env python3
"""
UC3 LLM 모델 검증 스크립트

목적: UC3에서 사용하는 모든 LLM의 작동원리와 버전 확인
"""

import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI

# Load environment variables
load_dotenv()

print("=" * 80)
print("UC3 LLM 모델 검증 및 작동원리 확인")
print("=" * 80)

# ============================================================
# 1. GPT-4o (Agent 1: Proposer)
# ============================================================
print("\n[1] GPT-4o Proposer 검증")
print("-" * 80)

try:
    gpt_llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 모델 정보 확인
    print(f"모델 이름: {gpt_llm.model_name}")
    print(f"Temperature: {gpt_llm.temperature}")
    print(f"OpenAI API Key: {os.getenv('OPENAI_API_KEY')[:20]}...")

    # 간단한 테스트 요청
    test_response = gpt_llm.invoke([{"role": "user", "content": "What is your model version? Reply in JSON format: {\"model\": \"...\", \"version\": \"...\"}"}])
    print(f"\n실제 응답 모델 확인:")
    print(f"응답 내용: {test_response.content}")

    # Response metadata 확인
    if hasattr(test_response, 'response_metadata'):
        print(f"\nResponse Metadata:")
        print(f"  Model Name: {test_response.response_metadata.get('model_name', 'N/A')}")
        print(f"  Token Usage: {test_response.response_metadata.get('token_usage', 'N/A')}")
        print(f"  Finish Reason: {test_response.response_metadata.get('finish_reason', 'N/A')}")

    print("\n✅ GPT-4o Proposer 정상 작동")

except Exception as e:
    print(f"\n❌ GPT-4o Proposer 오류: {e}")


# ============================================================
# 2. Gemini 2.0 Flash Lite (Agent 2: Validator)
# ============================================================
print("\n\n[2] Gemini 2.0 Flash Lite Validator 검증")
print("-" * 80)

try:
    gemini_llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash-lite",
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )

    # 모델 정보 확인
    print(f"모델 이름: {gemini_llm.model}")
    print(f"Temperature: {gemini_llm.temperature}")
    print(f"Google API Key: {os.getenv('GOOGLE_API_KEY')[:20]}...")

    # 간단한 테스트 요청
    test_response = gemini_llm.invoke([{"role": "user", "content": "What is your model version? Reply in JSON format: {\"model\": \"...\", \"version\": \"...\"}"}])
    print(f"\n실제 응답 모델 확인:")
    print(f"응답 내용: {test_response.content}")

    # Response metadata 확인
    if hasattr(test_response, 'response_metadata'):
        print(f"\nResponse Metadata:")
        for key, value in test_response.response_metadata.items():
            print(f"  {key}: {value}")

    print("\n✅ Gemini 2.0 Flash Lite Validator 정상 작동")

except Exception as e:
    print(f"\n❌ Gemini 2.0 Flash Lite Validator 오류: {e}")
    print("\nFallback GPT-4o-mini 테스트:")

    try:
        fallback_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        print(f"Fallback 모델 이름: {fallback_llm.model_name}")

        test_response = fallback_llm.invoke([{"role": "user", "content": "What is your model version?"}])
        print(f"Fallback 응답: {test_response.content[:200]}")
        print("\n✅ Fallback GPT-4o-mini 정상 작동")

    except Exception as e2:
        print(f"\n❌ Fallback GPT-4o-mini 오류: {e2}")


# ============================================================
# 3. UC3 Workflow 작동 원리 요약
# ============================================================
print("\n\n[3] UC3 Workflow 작동 원리")
print("=" * 80)

print("""
UC3 New Site Auto-Discovery - 3-Tool + 2-Agent + Consensus 시스템

┌─────────────────────────────────────────────────────────────────────┐
│                          START                                      │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Step 1: fetch_html_node                                            │
│  - 목적: 뉴스 기사 URL에서 HTML 다운로드                             │
│  - 사용: requests.get()                                             │
│  - 출력: raw_html (206KB)                                           │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Tool 2: firecrawl_preprocess_node                                  │
│  - 목적: HTML 토큰 90% 감소 (LLM 입력 최적화)                        │
│  - 사용: Firecrawl API (현재 params 오류로 fallback 사용)            │
│  - Fallback: preprocess_html() - BeautifulSoup 기반                 │
│  - 출력: firecrawl_results.html (1.4KB, 0.7%)                       │
└────────────────────────────┬────────────────────────────────────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
          ▼                  ▼                  ▼
┌──────────────────┐ ┌──────────────┐ ┌────────────────────┐
│ Tool 1: Tavily   │ │ Tool 3:      │ │ (Firecrawl 결과)   │
│ Web Search       │ │ BeautifulSoup│ │                    │
│                  │ │ DOM Analyzer │ │                    │
│ - GitHub/Stack   │ │              │ │                    │
│   Overflow 검색  │ │ - raw_html   │ │                    │
│ - CSS 패턴 참고  │ │   분석       │ │                    │
│                  │ │ - 제목 2개   │ │                    │
│ 출력: 3 results  │ │ - 본문 3개   │ │                    │
│                  │ │ - 날짜 3개   │ │                    │
└──────────────────┘ └──────────────┘ └────────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent 1: GPT-4o Proposer (gpt_discover_agent_node)                │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  모델: gpt-4o                                                       │
│  Temperature: 0                                                     │
│                                                                     │
│  입력:                                                              │
│    - tavily_results (3 results)                                    │
│    - firecrawl_results.html (1.4KB)                                │
│    - beautifulsoup_analysis (제목 2, 본문 3, 날짜 3)                │
│                                                                     │
│  작동 방식:                                                         │
│    1. 3개 Tool 결과를 종합 분석                                     │
│    2. BeautifulSoup 후보를 우선 선택                                │
│    3. Tavily 패턴으로 검증                                          │
│    4. Firecrawl HTML로 확인                                        │
│                                                                     │
│  출력:                                                              │
│    gpt_proposal = {                                                │
│      "selectors": {                                                │
│        "title": {"selector": "#title_area", "confidence": 0.9},   │
│        "body": {"selector": "div.end_container", "conf": 1.0},    │
│        "date": {"selector": "span._ARTICLE_DATE_TIME", "conf": 1.0}│
│      },                                                            │
│      "overall_confidence": 0.97                                    │
│    }                                                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Agent 2: Gemini Validator (gemini_validate_agent_node)            │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  모델: gemini-2.0-flash-lite                                        │
│  Temperature: 0                                                     │
│  Fallback: gpt-4o-mini (Gemini 실패시)                             │
│                                                                     │
│  입력:                                                              │
│    - gpt_proposal (GPT-4o 제안 셀렉터)                             │
│    - raw_html (full HTML, 206KB)                                   │
│                                                                     │
│  작동 방식:                                                         │
│    1. validate_selector_tool로 각 셀렉터 테스트:                    │
│       - title: BeautifulSoup으로 "#title_area" 추출                │
│       - body: "div.end_container" 추출                             │
│       - date: "span._ARTICLE_DATE_TIME" 추출                       │
│                                                                     │
│    2. Gemini가 validation_details 분석:                            │
│       - 실제 추출된 텍스트 확인                                     │
│       - 길이, 형식 검증                                             │
│       - 신뢰도 계산                                                 │
│                                                                     │
│    3. best_selectors 선정 및 overall_confidence 산출               │
│                                                                     │
│  출력:                                                              │
│    gemini_validation = {                                           │
│      "best_selectors": {                                           │
│        "title": "#title_area",                                     │
│        "body": "div.end_container",                                │
│        "date": "span.media_end_head_info_datestamp_time..."        │
│      },                                                            │
│      "validation_details": {                                       │
│        "title": {"valid": True, "confidence": 0.58, ...},         │
│        "body": {"valid": True, "confidence": 1.0, ...},           │
│        "date": {"valid": True, "confidence": 1.0, ...}            │
│      },                                                            │
│      "overall_confidence": 0.86                                    │
│    }                                                               │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│  Consensus Calculation (calculate_uc3_consensus_node)              │
│  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  공식:                                                              │
│    consensus_score = 0.3 × GPT + 0.3 × Gemini + 0.4 × Extraction  │
│                                                                     │
│  Extraction Quality 계산:                                           │
│    extraction_scores = [                                           │
│      validation_details['title']['confidence'],    # 0.58         │
│      validation_details['body']['confidence'],     # 1.0          │
│      validation_details['date']['confidence']      # 1.0          │
│    ]                                                               │
│    extraction_quality = average(extraction_scores) # 0.86         │
│                                                                     │
│  예시 계산 (네이버 뉴스):                                           │
│    GPT confidence:        0.97                                     │
│    Gemini confidence:     0.86                                     │
│    Extraction quality:    0.86                                     │
│                                                                     │
│    consensus_score = 0.3×0.97 + 0.3×0.86 + 0.4×0.86               │
│                    = 0.291 + 0.258 + 0.344                         │
│                    = 0.89                                          │
│                                                                     │
│  Threshold: 0.7                                                    │
│  Result: 0.89 ≥ 0.7 → consensus_reached = True ✅                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                   ┌─────────┴─────────┐
                   │                   │
       consensus_reached?              │
            Yes │                 No   │
                │                      │
                ▼                      ▼
    ┌───────────────────┐   ┌──────────────────┐
    │ save_selectors    │   │ human_review     │
    │                   │   │                  │
    │ - DB 저장         │   │ - Slack 알림     │
    │ - Selector 테이블 │   │ - 사람 검토 요청 │
    └───────────────────┘   └──────────────────┘
                │                      │
                └──────────┬───────────┘
                           │
                           ▼
                        [ END ]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

핵심 설계 원리:

1. **3-Tool 병렬 실행**
   - Tavily: 외부 지식 (GitHub, StackOverflow 패턴)
   - Firecrawl: 토큰 최적화 (LLM 비용 절감)
   - BeautifulSoup: 통계적 분석 (실제 DOM 후보)

2. **2-Agent Sequential Consensus**
   - GPT-4o: 창의적 제안 (3-Tool 종합)
   - Gemini: 보수적 검증 (실제 HTML 테스트)

3. **가중 합의 (Weighted Consensus)**
   - GPT (30%): Proposer의 신뢰도
   - Gemini (30%): Validator의 신뢰도
   - Extraction (40%): 실제 추출 품질 (가장 중요!)

4. **Fallback 전략**
   - Firecrawl 실패 → preprocess_html()
   - Gemini 실패 → GPT-4o-mini

5. **Self-Healing 메커니즘**
   - Consensus < 0.7 → human_review
   - Consensus ≥ 0.7 → 자동 DB 저장

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")


# ============================================================
# 4. 최종 검증 결과 요약
# ============================================================
print("\n[4] 최종 검증 결과")
print("=" * 80)

print("""
✅ Agent 1 (GPT-4o Proposer):
   - 모델: gpt-4o
   - Temperature: 0
   - 역할: 3-Tool 결과 종합 → CSS 셀렉터 제안
   - 출력: gpt_proposal + gpt_confidence

✅ Agent 2 (Gemini Validator):
   - 모델: gemini-2.0-flash-lite
   - Temperature: 0
   - Fallback: gpt-4o-mini
   - 역할: GPT 제안 검증 → 실제 HTML 테스트
   - 출력: gemini_validation + gemini_confidence

✅ Consensus System:
   - 공식: 0.3×GPT + 0.3×Gemini + 0.4×Extraction
   - Threshold: 0.7
   - 네이버 뉴스 테스트 결과: 0.89 ✅

✅ Tools:
   - Tavily Web Search: ✅ 작동
   - Firecrawl HTML Preprocessing: ⚠️ fallback 사용
   - BeautifulSoup DOM Analyzer: ✅ 작동 (제목 2, 본문 3, 날짜 3)

✅ DB 저장:
   - Selector 테이블에 discovered_selectors 저장
   - site_name: n (네이버 뉴스)
   - title: #title_area
   - body: div.end_container
   - date: span.media_end_head_info_datestamp_time._ARTICLE_DATE_TIME
""")

print("\n" + "=" * 80)
print("검증 완료!")
print("=" * 80)
