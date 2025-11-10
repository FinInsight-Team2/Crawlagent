"""
CrawlAgent - 자연어 검색 쿼리 파서
Created: 2025-11-08
Updated: 2025-11-08

GPT-4o-mini를 사용하여 자연어 검색 쿼리를 SQL WHERE 조건으로 변환
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Optional

import openai


def parse_natural_query(query: str) -> Dict:
    """
    자연어 검색 쿼리를 SQL WHERE 조건으로 변환

    Args:
        query: 자연어 검색 쿼리
            예: "경제 뉴스 중 삼성 관련 최근 1주일"
            예: "11월 7일 연합뉴스 정치 기사"

    Returns:
        Dict: 검색 조건
            {
                "keyword": "삼성",  # 제목/본문 검색어
                "category": "economy",  # politics, economy, society, international
                "site_name": "yonhap",  # yonhap, ...
                "date_from": "2025-11-01",  # YYYY-MM-DD
                "date_to": "2025-11-08",  # YYYY-MM-DD
                "min_quality": 90,  # 0-100
                "reasoning": "..."  # 파싱 근거
            }

    Examples:
        >>> parse_natural_query("경제 뉴스 중 삼성 관련 최근 1주일")
        {
            "keyword": "삼성",
            "category": "economy",
            "date_from": "2025-11-01",
            "date_to": "2025-11-08",
            "reasoning": "..."
        }
    """

    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다")

    client = openai.OpenAI(api_key=api_key)

    # 현재 날짜 (검색 기준)
    today = datetime.now().date()

    prompt = f"""
당신은 뉴스 검색 쿼리 파서입니다.

## 임무
사용자의 자연어 검색 쿼리를 SQL WHERE 조건으로 변환하세요.

## 입력
사용자 쿼리: "{query}"
현재 날짜: {today.strftime("%Y-%m-%d")} ({today.strftime("%Y년 %m월 %d일")})

## 출력 형식 (JSON)
{{
  "keyword": "검색어 또는 null",
  "category": "카테고리 또는 null",
  "site_name": "사이트 이름 또는 null",
  "date_from": "YYYY-MM-DD 또는 null",
  "date_to": "YYYY-MM-DD 또는 null",
  "min_quality": 점수(0-100) 또는 null,
  "reasoning": "파싱 근거"
}}

## 파싱 규칙

### 1. 키워드 추출
- 고유명사, 회사명, 인물명 등을 추출
- 예: "삼성", "대통령", "코스피", "BTS"
- 일반적인 단어는 제외 ("뉴스", "기사", "관련", "최근")

### 2. 카테고리 매핑
- **경제**: "경제", "재계", "증시", "주식", "기업", "산업", "금융"
- **정치**: "정치", "국회", "대통령", "정부", "선거", "여당", "야당"
- **사회**: "사회", "사건", "사고", "교육", "복지", "환경", "재난"
- **국제**: "국제", "해외", "외교", "글로벌", "미국", "중국", "일본"

### 3. 사이트 매핑
- **연합뉴스**: "연합", "연합뉴스", "yonhap"
- 다른 사이트는 null

### 4. 날짜 파싱
**상대 날짜**:
- "오늘", "today" → date_from={today}, date_to={today}
- "어제" → 하루 전
- "최근 3일", "지난 3일" → 3일 전부터 오늘까지
- "이번 주", "최근 1주일" → 7일 전부터 오늘까지
- "이번 달", "최근 1달" → 30일 전부터 오늘까지

**절대 날짜**:
- "11월 7일", "11/7", "2025-11-07" → 해당 날짜 (연도 생략 시 현재 연도)
- "11월 1일부터 11월 7일까지" → 범위 지정

**날짜 미지정**: null (전체 기간)

### 5. 품질 점수
- "고품질", "높은 품질" → min_quality=90
- "중간 품질" → min_quality=70
- 미지정 → null (전체)

## 예시

**입력**: "경제 뉴스 중 삼성 관련 최근 1주일"
**출력**:
{{
  "keyword": "삼성",
  "category": "economy",
  "site_name": null,
  "date_from": "{(today - timedelta(days=7)).strftime('%Y-%m-%d')}",
  "date_to": "{today.strftime('%Y-%m-%d')}",
  "min_quality": null,
  "reasoning": "카테고리=경제 (경제 뉴스), 키워드=삼성, 날짜=최근 1주일(7일 전~오늘)"
}}

**입력**: "11월 7일 연합뉴스 정치 기사"
**출력**:
{{
  "keyword": null,
  "category": "politics",
  "site_name": "yonhap",
  "date_from": "2025-11-07",
  "date_to": "2025-11-07",
  "min_quality": null,
  "reasoning": "카테고리=정치, 사이트=연합뉴스, 날짜=2025-11-07"
}}

**입력**: "대통령 발언 관련 기사"
**출력**:
{{
  "keyword": "대통령",
  "category": "politics",
  "site_name": null,
  "date_from": null,
  "date_to": null,
  "min_quality": null,
  "reasoning": "키워드=대통령, 카테고리=정치 (대통령 = 정치 관련)"
}}

## 주의사항
- JSON 외의 텍스트 출력 금지
- 확실하지 않은 정보는 null 처리
- reasoning에 파싱 근거 명확히 작성
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a news search query parser. Output only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )

        result_text = response.choices[0].message.content.strip()

        # JSON 파싱 (```json ... ``` 제거)
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()

        parsed = json.loads(result_text)

        # null 값을 빈 문자열 또는 0으로 변환 (Gradio 호환)
        return {
            "keyword": parsed.get("keyword") or "",
            "category": parsed.get("category") or "all",
            "site_name": parsed.get("site_name") or "",
            "date_from": parsed.get("date_from") or "",
            "date_to": parsed.get("date_to") or "",
            "min_quality": parsed.get("min_quality") or 0,
            "reasoning": parsed.get("reasoning", "자연어 쿼리 파싱 완료")
        }

    except json.JSONDecodeError as e:
        raise ValueError(f"GPT 응답을 JSON으로 파싱할 수 없습니다: {e}\n응답: {result_text}")
    except Exception as e:
        raise ValueError(f"자연어 쿼리 파싱 실패: {e}")


# 테스트 코드
if __name__ == "__main__":
    # 테스트 쿼리들
    test_queries = [
        "경제 뉴스 중 삼성 관련 최근 1주일",
        "11월 7일 연합뉴스 정치 기사",
        "대통령 발언 관련 기사",
        "오늘 경제 뉴스",
        "최근 3일 사회 카테고리"
    ]

    for query in test_queries:
        print(f"\n쿼리: {query}")
        try:
            result = parse_natural_query(query)
            print(f"결과: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except Exception as e:
            print(f"에러: {e}")
