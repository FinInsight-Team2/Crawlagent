"""
Naver News 기사 페이지 상세 분석
Created: 2025-11-02

목적:
    실제 Naver News 기사 URL로 Body Selector 찾기
"""

import requests
from bs4 import BeautifulSoup


def analyze_naver_article(url):
    """Naver 기사 페이지 상세 분석"""
    print(f"분석 URL: {url}\n")

    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    response = requests.get(url, headers=headers, timeout=10)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Body 후보들 더 광범위하게 찾기
    body_candidates = [
        'div#dic_area',
        'div#articleBodyContents',
        'div.article_body',
        'article',
        'div#newsct_article',
        'div.news_end_body_1',
        'div[id*="article"]',
        'div[class*="article"]',
        'div[class*="body"]',
    ]

    print("[Body Selector 후보 탐색]")
    for selector in body_candidates:
        if '#' in selector:
            # ID selector
            element = soup.select(selector)
        else:
            # class or tag selector
            element = soup.select(selector)

        if element:
            text = element[0].get_text(strip=True)
            print(f"✓ {selector}: {len(text)} chars")
            print(f"  내용 샘플: {text[:100]}...\n")
        else:
            print(f"✗ {selector}: 찾을 수 없음")

    # 모든 div 중 텍스트가 가장 긴 것 찾기
    print("\n[가장 긴 텍스트를 가진 div 요소들]")
    all_divs = soup.find_all('div')
    div_lengths = []

    for div in all_divs:
        text = div.get_text(strip=True)
        if len(text) > 500:  # 500자 이상만
            div_id = div.get('id', '')
            div_class = ' '.join(div.get('class', []))
            div_lengths.append((len(text), div_id, div_class, text[:100]))

    div_lengths.sort(reverse=True)

    for i, (length, div_id, div_class, sample) in enumerate(div_lengths[:5]):
        print(f"\n{i+1}. 길이: {length} chars")
        if div_id:
            print(f"   ID: #{div_id}")
        if div_class:
            print(f"   Class: .{div_class}")
        print(f"   샘플: {sample}...")


if __name__ == "__main__":
    # 앞서 발견한 실제 기사 URL
    test_url = "https://n.news.naver.com/mnews/article/032/0003406033"
    analyze_naver_article(test_url)
