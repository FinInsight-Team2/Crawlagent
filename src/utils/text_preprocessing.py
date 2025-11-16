"""
텍스트 전처리 유틸리티
Created: 2025-11-04

목적:
- 크롤링된 텍스트를 ML/분석에 사용 가능하도록 정제
- HTML 태그 제거, 공백 정리, 날짜 정규화 등
"""

import re
from datetime import datetime
from typing import Any, Dict, Optional

from bs4 import BeautifulSoup


def clean_html_tags(text: str) -> str:
    """
    HTML 태그 완전 제거

    Args:
        text: HTML 태그가 포함된 텍스트

    Returns:
        순수 텍스트 (HTML 태그 제거됨)

    Examples:
        >>> clean_html_tags("<strong>제목</strong><br>본문")
        "제목\n본문"
    """
    if not text:
        return ""

    # BeautifulSoup로 HTML 파싱 후 텍스트만 추출
    soup = BeautifulSoup(text, "html.parser")

    # <br> 태그를 줄바꿈으로 변환 (제거 전)
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # 모든 HTML 태그 제거
    text = soup.get_text()

    return text


def normalize_whitespace(text: str) -> str:
    """
    공백 정규화

    처리:
    - 연속된 공백 → 단일 공백
    - 연속된 줄바꿈 (3개 이상) → 2개로 제한
    - 앞뒤 공백 제거

    Args:
        text: 정규화할 텍스트

    Returns:
        공백이 정리된 텍스트
    """
    if not text:
        return ""

    # 연속된 공백 → 단일 공백
    text = re.sub(r" +", " ", text)

    # 연속된 줄바꿈 (3개 이상) → 2개로 제한
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 앞뒤 공백 제거
    text = text.strip()

    return text


def remove_ad_patterns(text: str) -> str:
    """
    광고성 문구 패턴 제거

    제거 대상:
    - "관련기사", "이 시각 인기 기사"
    - "▶", "◀", "※" 등 특수 기호로 시작하는 줄
    - "클릭하면", "바로가기", "더보기" 등

    Args:
        text: 원본 텍스트

    Returns:
        광고 문구가 제거된 텍스트
    """
    if not text:
        return ""

    # 광고 패턴 정의
    ad_patterns = [
        r"▶.*?\n",  # ▶로 시작하는 줄
        r"◀.*?\n",  # ◀로 시작하는 줄
        r"※.*?\n",  # ※로 시작하는 줄
        r"관련[\s]*기사.*?\n",  # 관련기사
        r"이[\s]*시각[\s]*인기[\s]*기사.*?\n",  # 이 시각 인기 기사
        r"함께[\s]*보면[\s]*좋은.*?\n",  # 함께 보면 좋은
        r"\[.*?기자\]",  # [OOO 기자] (중복 서명)
        r"\(.*?@.*?\)",  # 이메일 주소
    ]

    for pattern in ad_patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text


def normalize_date_format(date_str: Optional[str]) -> Optional[str]:
    """
    날짜 형식 정규화

    입력 형식:
    - ISO 8601: "2025-11-04T15:30:00+09:00"
    - 또는 기타 형식

    출력 형식:
    - "2025-11-04 15:30"

    Args:
        date_str: 날짜 문자열

    Returns:
        정규화된 날짜 문자열 (YYYY-MM-DD HH:MM)
    """
    if not date_str:
        return None

    try:
        # ISO 8601 파싱
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # 파싱 실패 시 원본 반환
        return date_str


def extract_reporter_info(text: str) -> Dict[str, Optional[str]]:
    """
    기자 정보 추출

    패턴:
    - "홍길동 기자 (gildong@yna.co.kr)"
    - "[서울=홍길동 기자]"

    Args:
        text: 기사 본문

    Returns:
        {"reporter_name": "홍길동", "reporter_email": "gildong@yna.co.kr"}
    """
    result = {"reporter_name": None, "reporter_email": None}

    if not text:
        return result

    # 패턴 1: "홍길동 기자"
    match = re.search(r"([가-힣]{2,4})\s*기자", text)
    if match:
        result["reporter_name"] = match.group(1)

    # 패턴 2: 이메일
    match = re.search(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})", text)
    if match:
        result["reporter_email"] = match.group(1)

    return result


def preprocess_article(
    title: Optional[str], body: Optional[str], date: Optional[str]
) -> Dict[str, Any]:
    """
    기사 전체 전처리 (메인 함수)

    처리 순서:
    1. HTML 태그 제거
    2. 광고 패턴 제거
    3. 공백 정규화
    4. 날짜 정규화
    5. 기자 정보 추출

    Args:
        title: 원본 제목
        body: 원본 본문
        date: 원본 날짜

    Returns:
        {
            "title": "정제된 제목",
            "body": "정제된 본문",
            "date": "2025-11-04 15:30",
            "reporter_name": "홍길동",
            "reporter_email": "gildong@yna.co.kr",
            "word_count": 1234
        }
    """
    # Title 정제
    clean_title = ""
    if title:
        clean_title = clean_html_tags(title)
        clean_title = normalize_whitespace(clean_title)

    # Body 정제
    clean_body = ""
    word_count = 0
    reporter_info = {"reporter_name": None, "reporter_email": None}

    if body:
        # 기자 정보 추출 (제거 전)
        reporter_info = extract_reporter_info(body)

        # 정제 파이프라인
        clean_body = clean_html_tags(body)
        clean_body = remove_ad_patterns(clean_body)
        clean_body = normalize_whitespace(clean_body)

        # 단어 수 계산 (공백 기준)
        word_count = len(clean_body.split())

    # Date 정규화
    clean_date = normalize_date_format(date)

    return {
        "title": clean_title,
        "body": clean_body,
        "date": clean_date,
        "reporter_name": reporter_info["reporter_name"],
        "reporter_email": reporter_info["reporter_email"],
        "word_count": word_count,
    }


# 테스트 코드
if __name__ == "__main__":
    # 테스트 데이터
    test_html = """
    <strong>테스트 제목</strong><br><br>
    이것은 본문입니다.<br>
    ▶ 관련기사: 클릭하세요<br>
    실제 내용이 이어집니다.<br><br><br>
    홍길동 기자 (gildong@yna.co.kr)
    """

    result = preprocess_article(
        title="<h1>테스트</h1>", body=test_html, date="2025-11-04T15:30:00+09:00"
    )

    print("=== 전처리 결과 ===")
    for key, value in result.items():
        print(f"{key}: {value}")
