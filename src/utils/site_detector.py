"""
Site ID Normalization Utility

URL에서 정규화된 site_id를 추출합니다.
다양한 도메인 패턴을 처리:
- 서브도메인 (news.jtbc.co.kr → jtbc)
- 지역 사이트 (edition.cnn.com → cnn)
- 다단계 도메인 (n.news.naver.com → naver)

작성일: 2025-11-13
버전: v2.1
"""

from urllib.parse import urlparse
from typing import Dict, List

# 도메인 매핑 규칙 (정확한 도메인 → 정규화된 site_id)
SITE_MAPPINGS: Dict[str, str] = {
    # 한국 뉴스 사이트
    "news.jtbc.co.kr": "jtbc",
    "jtbc.co.kr": "jtbc",
    "www.jtbc.co.kr": "jtbc",

    "news.kbs.co.kr": "kbs",
    "kbs.co.kr": "kbs",
    "www.kbs.co.kr": "kbs",

    "news.sbs.co.kr": "sbs",
    "sbs.co.kr": "sbs",
    "www.sbs.co.kr": "sbs",

    "n.news.naver.com": "naver",
    "news.naver.com": "naver",
    "naver.com": "naver",
    "www.naver.com": "naver",

    "www.donga.com": "donga",
    "donga.com": "donga",

    "www.chosun.com": "chosun",
    "chosun.com": "chosun",

    "www.hankyung.com": "hankyung",
    "hankyung.com": "hankyung",

    "www.mk.co.kr": "mk",
    "mk.co.kr": "mk",

    "www.joongang.co.kr": "joongang",
    "joongang.co.kr": "joongang",

    "www.edaily.co.kr": "edaily",
    "edaily.co.kr": "edaily",

    "www.yna.co.kr": "yonhap",
    "yna.co.kr": "yonhap",

    "yonhapnewstv.co.kr": "yonhapnewstv",
    "www.yonhapnewstv.co.kr": "yonhapnewstv",

    # 해외 뉴스 사이트
    "edition.cnn.com": "cnn",
    "www.cnn.com": "cnn",
    "cnn.com": "cnn",

    "www.bbc.com": "bbc",
    "bbc.com": "bbc",
    "www.bbc.co.uk": "bbc",
    "bbc.co.uk": "bbc",

    "www.reuters.com": "reuters",
    "reuters.com": "reuters",

    "www.theguardian.com": "guardian",
    "theguardian.com": "guardian",

    "apnews.com": "apnews",
    "www.apnews.com": "apnews",

    "www.nytimes.com": "nytimes",
    "nytimes.com": "nytimes",

    "www.axios.com": "axios",
    "axios.com": "axios",

    "www.politico.com": "politico",
    "politico.com": "politico",

    "www.lemonde.fr": "lemonde",
    "lemonde.fr": "lemonde",

    "www.spiegel.de": "spiegel",
    "spiegel.de": "spiegel",

    "www.asahi.com": "asahi",
    "asahi.com": "asahi",
}

# 2단계 TLD 패턴 (domain.tld 형식)
SECOND_LEVEL_TLDS: List[str] = [
    ".co.kr",  # 한국
    ".co.uk",  # 영국
    ".co.jp",  # 일본
    ".com",
    ".net",
    ".org",
    ".fr",
    ".de",
]


def extract_site_id(url: str) -> str:
    """
    URL에서 정규화된 site_id를 추출합니다.

    우선순위:
    1. SITE_MAPPINGS에서 정확한 도메인 매칭
    2. www. 제거 후 재시도
    3. 2단계 도메인 로직 (brand.co.kr → brand)
    4. Fallback: 첫 번째 세그먼트

    Args:
        url: 전체 URL (예: "https://news.jtbc.co.kr/article/...")

    Returns:
        site_id: 정규화된 사이트 식별자 (예: "jtbc")

    Examples:
        >>> extract_site_id("https://news.jtbc.co.kr/article/NB12270830")
        'jtbc'
        >>> extract_site_id("https://edition.cnn.com/2025/11/13/business/...")
        'cnn'
        >>> extract_site_id("https://n.news.naver.com/mnews/article/018/...")
        'naver'
        >>> extract_site_id("https://www.donga.com/news/Economy/article/...")
        'donga'
    """
    parsed = urlparse(url)
    domain = parsed.netloc.lower().strip()

    if not domain:
        # URL 파싱 실패 시 fallback
        return "unknown"

    # 1. SITE_MAPPINGS에서 정확한 매칭
    if domain in SITE_MAPPINGS:
        return SITE_MAPPINGS[domain]

    # 2. www. 제거 후 재시도
    domain_no_www = domain.replace("www.", "")
    if domain_no_www in SITE_MAPPINGS:
        return SITE_MAPPINGS[domain_no_www]

    # 3. 2단계 도메인 로직 (brand.co.kr → brand)
    for tld in SECOND_LEVEL_TLDS:
        if domain.endswith(tld):
            # TLD 제거 후 도메인 파트 추출
            domain_without_tld = domain.replace(tld, "")
            parts = domain_without_tld.split(".")

            if len(parts) >= 2:
                # news.jtbc.co.kr → ["news", "jtbc"] → "jtbc" (마지막 부분)
                return parts[-1]
            elif len(parts) == 1:
                # brand.co.kr → ["brand"] → "brand"
                return parts[0]

    # 4. Fallback: 첫 번째 세그먼트 (www. 제거 후)
    parts = domain_no_www.split(".")
    if parts:
        return parts[0]

    # 최악의 경우
    return domain_no_www if domain_no_www else "unknown"


def normalize_site_name(site_name: str) -> str:
    """
    site_name을 소문자 정규화 형식으로 변환합니다.

    Args:
        site_name: 원본 사이트 이름 (대소문자 혼합 가능)

    Returns:
        정규화된 site_id (소문자, 공백 없음)

    Examples:
        >>> normalize_site_name("BBC News")
        'bbc_news'
        >>> normalize_site_name("  JTBC  ")
        'jtbc'
    """
    return site_name.lower().strip().replace(" ", "_")


def add_site_mapping(domain: str, site_id: str) -> None:
    """
    새로운 도메인 매핑을 런타임에 추가합니다.

    Args:
        domain: 도메인 (예: "news.example.com")
        site_id: 정규화된 site_id (예: "example")

    Note:
        이 함수는 런타임 동안만 유효하며, 재시작 시 사라집니다.
        영구적으로 추가하려면 SITE_MAPPINGS 딕셔너리를 직접 수정하세요.
    """
    SITE_MAPPINGS[domain.lower().strip()] = site_id.lower().strip()


def get_all_mappings() -> Dict[str, str]:
    """
    현재 등록된 모든 도메인 매핑을 반환합니다.

    Returns:
        도메인 → site_id 매핑 딕셔너리
    """
    return SITE_MAPPINGS.copy()


# 하위 호환성을 위한 별칭
extract_site_name = extract_site_id
