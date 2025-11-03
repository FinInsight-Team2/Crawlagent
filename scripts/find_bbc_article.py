"""
BBC News 실제 기사 찾고 분석
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin


# BBC News 홈페이지에서 실제 기사 URL 찾기
homepage = "https://www.bbc.com/news"
headers = {'User-Agent': 'Mozilla/5.0'}

print("BBC News 홈페이지에서 기사 URL 찾기...\n")
response = requests.get(homepage, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# 실제 article URL 찾기 (/news/articles/ 패턴)
article_urls = []
for link in soup.find_all('a', href=True):
    href = link['href']
    # /articles/ 포함하는 것만 (실제 기사)
    if '/articles/' in href or ('/news/' in href and len(href.split('/')) > 4):
        if href.startswith('/'):
            full_url = f"https://www.bbc.com{href}"
        elif href.startswith('http'):
            full_url = href
        else:
            continue

        # 중복 제거, 실제 기사만
        if 'bbc.com' in full_url and full_url not in article_urls:
            # topic, live-reporting 등 제외
            if '/topics/' not in full_url and '/live/' not in full_url:
                article_urls.append(full_url)

print(f"발견된 기사 URL: {len(article_urls)}개\n")

if article_urls:
    print("처음 5개 URL:")
    for i, url in enumerate(article_urls[:5]):
        print(f"  {i+1}. {url}")

    # 첫 번째 기사 분석
    test_url = article_urls[0]
    print(f"\n\n분석할 기사 URL:\n{test_url}\n")

    response = requests.get(test_url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Title
    print("[Title Selector 테스트]")
    title_candidates = [
        'h1[data-component="headline-block"]',
        'h1#main-heading',
        'h1',
    ]

    for selector in title_candidates:
        elements = soup.select(selector)
        if elements:
            print(f"✓ {selector}: '{elements[0].get_text(strip=True)}'")
        else:
            print(f"✗ {selector}: 찾을 수 없음")

    # Body
    print("\n[Body Selector 테스트]")
    body_candidates = [
        'div[data-component="text-block"]',
        'article',
        'div.article__body-content',
        'main',
    ]

    for selector in body_candidates:
        elements = soup.select(selector)
        if elements:
            if selector == 'div[data-component="text-block"]':
                # 여러 개 합치기
                total_text = ' '.join([el.get_text(strip=True) for el in elements])
                print(f"✓ {selector}: {len(elements)}개 블록, 총 {len(total_text)} chars")
                print(f"  샘플: {total_text[:100]}...")
            else:
                text = elements[0].get_text(strip=True)
                print(f"✓ {selector}: {len(text)} chars")
                print(f"  샘플: {text[:100]}...")
        else:
            print(f"✗ {selector}: 찾을 수 없음")

    # Date
    print("\n[Date Selector 테스트]")
    date_candidates = [
        'time[datetime]',
        'time',
        'div[data-testid="timestamp"]',
        'span.date',
    ]

    for selector in date_candidates:
        elements = soup.select(selector)
        if elements:
            if elements[0].has_attr('datetime'):
                print(f"✓ {selector}: {elements[0]['datetime']} (text: {elements[0].get_text(strip=True)})")
            else:
                print(f"✓ {selector}: {elements[0].get_text(strip=True)}")
        else:
            print(f"✗ {selector}: 찾을 수 없음")

else:
    print("기사 URL을 찾지 못했습니다.")
