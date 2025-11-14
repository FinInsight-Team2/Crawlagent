"""
Site Detector Unit Tests

10개 실제 URL로 site_id 추출 로직 검증

작성일: 2025-11-13
"""

import pytest
from src.utils.site_detector import (
    extract_site_id,
    normalize_site_name,
    add_site_mapping,
    get_all_mappings
)


class TestExtractSiteId:
    """extract_site_id() 함수 테스트"""

    def test_10_real_urls(self):
        """Phase 1 테스트 URL 10개 검증"""
        test_cases = [
            # Korean news sites
            ("https://www.donga.com/news/Economy/article/all/20251113/132765807/1", "donga"),
            ("https://news.jtbc.co.kr/article/NB12270830", "jtbc"),
            ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8407074", "kbs"),
            ("https://news.sbs.co.kr/news/endPage.do?news_id=N1008329074", "sbs"),
            ("https://www.chosun.com/economy/money/2025/11/13/52MHLOUGURGTFOF5Y3TXN3WVIA/", "chosun"),
            ("https://www.hankyung.com/article/2025111326861", "hankyung"),

            # International news sites
            ("https://www.bbc.com/news/articles/c891nvwvg2zo", "bbc"),
            ("https://yonhapnewstv.co.kr/news/AKR202511131509545Wu", "yonhapnewstv"),
            ("https://edition.cnn.com/2025/11/13/business/coffee-prices-not-coming-down", "cnn"),
            ("https://n.news.naver.com/mnews/article/018/0006163369", "naver"),
        ]

        for url, expected_site_id in test_cases:
            actual_site_id = extract_site_id(url)
            assert actual_site_id == expected_site_id, \
                f"URL: {url}\nExpected: {expected_site_id}\nGot: {actual_site_id}"

    def test_existing_sites_from_db(self):
        """DB에 이미 있던 사이트들 검증"""
        test_cases = [
            ("https://www.yna.co.kr/view/AKR...", "yonhap"),
            ("https://www.reuters.com/world/...", "reuters"),
            ("https://www.mk.co.kr/news/...", "mk"),
            ("https://www.joongang.co.kr/article/...", "joongang"),
            ("https://www.edaily.co.kr/news/...", "edaily"),
        ]

        for url, expected_site_id in test_cases:
            actual_site_id = extract_site_id(url)
            assert actual_site_id == expected_site_id, \
                f"URL: {url}\nExpected: {expected_site_id}\nGot: {actual_site_id}"

    def test_subdomain_handling(self):
        """서브도메인 처리 검증"""
        # news.* 패턴
        assert extract_site_id("https://news.jtbc.co.kr/article/test") == "jtbc"
        assert extract_site_id("https://news.kbs.co.kr/news/test") == "kbs"
        assert extract_site_id("https://news.sbs.co.kr/news/test") == "sbs"

        # n.* 패턴
        assert extract_site_id("https://n.news.naver.com/mnews/article/test") == "naver"

        # edition.* 패턴
        assert extract_site_id("https://edition.cnn.com/2025/test") == "cnn"

    def test_www_removal(self):
        """www. 제거 처리 검증"""
        assert extract_site_id("https://www.donga.com/news/test") == "donga"
        assert extract_site_id("https://donga.com/news/test") == "donga"

        assert extract_site_id("https://www.bbc.com/news/test") == "bbc"
        assert extract_site_id("https://bbc.com/news/test") == "bbc"

    def test_case_insensitive(self):
        """대소문자 무관 처리 검증"""
        assert extract_site_id("https://WWW.DONGA.COM/news/test") == "donga"
        assert extract_site_id("https://NEWS.JTBC.CO.KR/article/test") == "jtbc"

    def test_edge_cases(self):
        """엣지 케이스 처리"""
        # 빈 URL
        assert extract_site_id("") == "unknown"

        # 잘못된 URL
        assert extract_site_id("not-a-url") == "unknown"

        # 프로토콜 없는 URL (urlparse가 netloc로 인식하지 못함)
        # 실제 사용 시나리오에서는 항상 http/https 프로토콜이 포함됨
        result = extract_site_id("www.donga.com/news/test")
        assert result == "unknown"  # 프로토콜 없으면 unknown 반환


class TestNormalizeSiteName:
    """normalize_site_name() 함수 테스트"""

    def test_lowercase_conversion(self):
        """소문자 변환 검증"""
        assert normalize_site_name("BBC News") == "bbc_news"
        assert normalize_site_name("JTBC") == "jtbc"
        assert normalize_site_name("Chosun") == "chosun"

    def test_space_replacement(self):
        """공백 처리 검증"""
        assert normalize_site_name("BBC News") == "bbc_news"
        assert normalize_site_name("New York Times") == "new_york_times"

    def test_whitespace_trimming(self):
        """공백 제거 검증"""
        assert normalize_site_name("  JTBC  ") == "jtbc"
        assert normalize_site_name("\tBBC\n") == "bbc"


class TestDynamicMappings:
    """동적 매핑 추가 테스트"""

    def test_add_site_mapping(self):
        """런타임 매핑 추가 검증"""
        # 새로운 매핑 추가
        add_site_mapping("news.example.com", "example")

        # 추가된 매핑 확인
        assert extract_site_id("https://news.example.com/article/123") == "example"

    def test_get_all_mappings(self):
        """전체 매핑 조회 검증"""
        mappings = get_all_mappings()

        # 기본 매핑들이 있는지 확인
        assert "news.jtbc.co.kr" in mappings
        assert "edition.cnn.com" in mappings
        assert "www.bbc.com" in mappings

        # 딕셔너리 복사본인지 확인 (원본 수정 방지)
        mappings["test.com"] = "test"
        assert "test.com" not in get_all_mappings()


class TestBackwardCompatibility:
    """하위 호환성 테스트"""

    def test_extract_site_name_alias(self):
        """extract_site_name 별칭 검증 (UC3 workflow 호환성)"""
        from src.utils.site_detector import extract_site_name

        # extract_site_name은 extract_site_id의 별칭
        assert extract_site_name("https://news.jtbc.co.kr/article/test") == "jtbc"
        assert extract_site_name("https://edition.cnn.com/2025/test") == "cnn"


# pytest 실행 시 상세 정보 출력
if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
