"""
사이트 구조 분석 스크립트
Created: 2025-11-02

목적:
    Naver News와 BBC News의 HTML 구조를 분석하여
    CSS Selector를 찾아냅니다.

실행:
    cd /Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc
    poetry run python scripts/analyze_site_structure.py
"""

import sys
sys.path.insert(0, '.')

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


def analyze_naver_news():
    """
    Naver News 구조 분석 (경제 섹션)

    목표:
        - 기사 목록 URL 패턴
        - 개별 기사 페이지 selectors
    """
    print("=" * 70)
    print("Naver News 구조 분석")
    print("=" * 70)

    # 1단계: 섹션 페이지 분석 (기사 목록)
    section_url = "https://news.naver.com/section/101"  # 경제
    print(f"\n[1단계] 섹션 페이지 분석: {section_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(section_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 기사 링크 찾기 (여러 패턴 시도)
        article_links = []

        # 패턴 1: a 태그에서 /article/ 포함된 것
        for link in soup.find_all('a', href=True):
            if '/article/' in link['href']:
                full_url = urljoin(section_url, link['href'])
                if full_url not in article_links:
                    article_links.append(full_url)

        print(f"  발견된 기사 링크: {len(article_links)}개")

        if article_links:
            print(f"\n  샘플 URL (처음 3개):")
            for url in article_links[:3]:
                print(f"    - {url}")

            # 2단계: 개별 기사 페이지 분석
            print(f"\n[2단계] 개별 기사 페이지 분석")
            test_url = article_links[0]
            print(f"  테스트 URL: {test_url}")

            article_response = requests.get(test_url, headers=headers, timeout=10)
            article_response.raise_for_status()
            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            # Title 찾기
            title_candidates = [
                ('h2#title_area', article_soup.select('h2#title_area')),
                ('h1.title', article_soup.select('h1.title')),
                ('h2.media_end_head_headline', article_soup.select('h2.media_end_head_headline')),
            ]

            print("\n  [Title Selector 후보]")
            for selector, elements in title_candidates:
                if elements:
                    print(f"    ✓ {selector}: '{elements[0].get_text(strip=True)[:50]}...'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # Body 찾기
            body_candidates = [
                ('div#dic_area', article_soup.select('div#dic_area')),
                ('div#articleBodyContents', article_soup.select('div#articleBodyContents')),
                ('div.article_body', article_soup.select('div.article_body')),
            ]

            print("\n  [Body Selector 후보]")
            for selector, elements in body_candidates:
                if elements:
                    text = elements[0].get_text(strip=True)
                    print(f"    ✓ {selector}: {len(text)} chars - '{text[:50]}...'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # Date 찾기
            date_candidates = [
                ('span.media_end_head_info_datestamp_time', article_soup.select('span.media_end_head_info_datestamp_time')),
                ('span.t11', article_soup.select('span.t11')),
                ('time', article_soup.select('time')),
            ]

            print("\n  [Date Selector 후보]")
            for selector, elements in date_candidates:
                if elements:
                    date_text = elements[0].get_text(strip=True)
                    print(f"    ✓ {selector}: '{date_text}'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # 권장 Selector 출력
            print("\n" + "=" * 70)
            print("권장 Naver News Selector 설정")
            print("=" * 70)

            # 실제 발견된 selector 중 첫 번째 것 사용
            title_selector = None
            body_selector = None
            date_selector = None

            for selector, elements in title_candidates:
                if elements:
                    title_selector = selector
                    break

            for selector, elements in body_candidates:
                if elements:
                    body_selector = selector
                    break

            for selector, elements in date_candidates:
                if elements:
                    date_selector = selector
                    break

            print(f"  site_name: 'naver_economy'")
            print(f"  title_selector: '{title_selector}'")
            print(f"  body_selector: '{body_selector}'")
            print(f"  date_selector: '{date_selector}'")
            print(f"  site_type: 'ssr'")

            return {
                'site_name': 'naver_economy',
                'title_selector': title_selector,
                'body_selector': body_selector,
                'date_selector': date_selector,
                'sample_url': test_url
            }

        else:
            print("  ❌ 기사 링크를 찾을 수 없습니다.")
            print("  페이지 구조가 변경되었을 수 있습니다.")
            return None

    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        return None


def analyze_bbc_news():
    """
    BBC News 구조 분석

    목표:
        - 기사 목록 URL 패턴
        - 개별 기사 페이지 selectors
    """
    print("\n" + "=" * 70)
    print("BBC News 구조 분석")
    print("=" * 70)

    # 1단계: 홈페이지 분석
    homepage_url = "https://www.bbc.com/news"
    print(f"\n[1단계] 홈페이지 분석: {homepage_url}")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        response = requests.get(homepage_url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')

        # 기사 링크 찾기
        article_links = []

        # 패턴: /news/articles/ 포함된 것
        for link in soup.find_all('a', href=True):
            href = link['href']
            if '/articles/' in href or '/news/' in href:
                # 상대 경로를 절대 경로로 변환
                if href.startswith('/'):
                    full_url = f"https://www.bbc.com{href}"
                elif href.startswith('http'):
                    full_url = href
                else:
                    continue

                # 중복 제거, 유효한 기사 URL만
                if 'bbc.com/news/' in full_url and full_url not in article_links:
                    article_links.append(full_url)

        print(f"  발견된 기사 링크: {len(article_links)}개")

        if article_links:
            print(f"\n  샘플 URL (처음 3개):")
            for url in article_links[:3]:
                print(f"    - {url}")

            # 2단계: 개별 기사 페이지 분석
            print(f"\n[2단계] 개별 기사 페이지 분석")
            test_url = article_links[0]
            print(f"  테스트 URL: {test_url}")

            article_response = requests.get(test_url, headers=headers, timeout=10)
            article_response.raise_for_status()
            article_soup = BeautifulSoup(article_response.text, 'html.parser')

            # Title 찾기
            title_candidates = [
                ('h1[data-component="headline-block"]', article_soup.select('h1[data-component="headline-block"]')),
                ('h1#main-heading', article_soup.select('h1#main-heading')),
                ('h1', article_soup.select('h1')),
            ]

            print("\n  [Title Selector 후보]")
            for selector, elements in title_candidates:
                if elements:
                    print(f"    ✓ {selector}: '{elements[0].get_text(strip=True)[:50]}...'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # Body 찾기
            body_candidates = [
                ('div[data-component="text-block"]', article_soup.select('div[data-component="text-block"]')),
                ('article', article_soup.select('article')),
                ('div.article-body', article_soup.select('div.article-body')),
            ]

            print("\n  [Body Selector 후보]")
            for selector, elements in body_candidates:
                if elements:
                    # text-block은 여러 개일 수 있으므로 모두 합침
                    if selector == 'div[data-component="text-block"]':
                        text = ' '.join([el.get_text(strip=True) for el in elements])
                    else:
                        text = elements[0].get_text(strip=True)
                    print(f"    ✓ {selector}: {len(text)} chars - '{text[:50]}...'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # Date 찾기
            date_candidates = [
                ('time', article_soup.select('time')),
                ('span[data-testid="timestamp"]', article_soup.select('span[data-testid="timestamp"]')),
                ('div.date', article_soup.select('div.date')),
            ]

            print("\n  [Date Selector 후보]")
            for selector, elements in date_candidates:
                if elements:
                    # time 태그는 datetime 속성도 확인
                    if elements[0].has_attr('datetime'):
                        date_text = f"{elements[0].get_text(strip=True)} (datetime={elements[0]['datetime']})"
                    else:
                        date_text = elements[0].get_text(strip=True)
                    print(f"    ✓ {selector}: '{date_text}'")
                else:
                    print(f"    ✗ {selector}: 찾을 수 없음")

            # 권장 Selector 출력
            print("\n" + "=" * 70)
            print("권장 BBC News Selector 설정")
            print("=" * 70)

            title_selector = None
            body_selector = None
            date_selector = None

            for selector, elements in title_candidates:
                if elements:
                    title_selector = selector
                    break

            for selector, elements in body_candidates:
                if elements:
                    body_selector = selector
                    break

            for selector, elements in date_candidates:
                if elements:
                    date_selector = selector
                    break

            print(f"  site_name: 'bbc'")
            print(f"  title_selector: '{title_selector}'")
            print(f"  body_selector: '{body_selector}'")
            print(f"  date_selector: '{date_selector}'")
            print(f"  site_type: 'ssr'")

            return {
                'site_name': 'bbc',
                'title_selector': title_selector,
                'body_selector': body_selector,
                'date_selector': date_selector,
                'sample_url': test_url
            }

        else:
            print("  ❌ 기사 링크를 찾을 수 없습니다.")
            return None

    except Exception as e:
        print(f"  ❌ 오류 발생: {e}")
        return None


def main():
    """
    메인 실행 함수
    """
    print("=" * 70)
    print("사이트 구조 분석 스크립트")
    print("=" * 70)
    print(f"\n날짜: 2025-11-02")
    print(f"목적: Naver News 및 BBC News CSS Selector 찾기")

    # Naver News 분석
    naver_result = analyze_naver_news()

    # BBC News 분석
    bbc_result = analyze_bbc_news()

    # 결과 요약
    print("\n" + "=" * 70)
    print("분석 결과 요약")
    print("=" * 70)

    results = []

    if naver_result:
        results.append(("Naver News", naver_result))
        print(f"\n✅ Naver News 분석 성공")
        print(f"   Sample URL: {naver_result['sample_url']}")
    else:
        print(f"\n❌ Naver News 분석 실패")

    if bbc_result:
        results.append(("BBC News", bbc_result))
        print(f"\n✅ BBC News 분석 성공")
        print(f"   Sample URL: {bbc_result['sample_url']}")
    else:
        print(f"\n❌ BBC News 분석 실패")

    # SQL 생성 (DB에 추가할 때 사용)
    if results:
        print("\n" + "=" * 70)
        print("DB 추가용 SQL (참고용)")
        print("=" * 70)

        for site_name, result in results:
            print(f"\n-- {site_name}")
            print(f"INSERT INTO selectors (site_name, title_selector, body_selector, date_selector, site_type)")
            print(f"VALUES (")
            print(f"    '{result['site_name']}',")
            print(f"    '{result['title_selector']}',")
            print(f"    '{result['body_selector']}',")
            print(f"    '{result['date_selector']}',")
            print(f"    'ssr'")
            print(f");")

    print("\n" + "=" * 70)
    print("분석 완료")
    print("=" * 70)
    print("\n다음 단계:")
    print("  1. 위 Selector를 확인하여 Spider 구현")
    print("  2. 실제 크롤링 테스트 (10개 기사)")
    print("  3. UC1 Validation 연동")


if __name__ == "__main__":
    main()
