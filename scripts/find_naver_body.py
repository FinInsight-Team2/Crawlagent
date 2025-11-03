"""
Naver News Body Selector 정확히 찾기
"""

import requests
from bs4 import BeautifulSoup


url = "https://n.news.naver.com/mnews/article/032/0003406033"
headers = {'User-Agent': 'Mozilla/5.0'}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, 'html.parser')

# newsct_article 하위 구조 확인
article_div = soup.select_one('div#newsct_article')

if article_div:
    print("div#newsct_article 하위 요소들:\n")

    # 직접 자식 요소들 확인
    for i, child in enumerate(article_div.find_all(recursive=False)):
        print(f"\n{i+1}. 태그: {child.name}")
        if child.get('id'):
            print(f"   ID: {child['id']}")
        if child.get('class'):
            print(f"   Class: {child['class']}")

        text = child.get_text(strip=True)
        if len(text) > 100:
            print(f"   텍스트: {len(text)} chars - {text[:100]}...")
        else:
            print(f"   텍스트: {len(text)} chars - {text}")

    # article 태그 내부 확인
    article_tag = soup.select_one('article')
    if article_tag:
        print("\n\n<article> 태그 하위 구조:")
        for i, child in enumerate(article_tag.find_all(recursive=False)):
            print(f"\n{i+1}. 태그: {child.name}")
            if child.get('id'):
                print(f"   ID: {child['id']}")
            if child.get('class'):
                print(f"   Class: {' '.join(child['class'])}")

            text = child.get_text(strip=True)
            print(f"   텍스트: {len(text)} chars")
            if 500 < len(text) < 2000:  # 본문일 가능성 높음
                print(f"   샘플: {text[:150]}...")

    # 가능한 본문 selector들
    print("\n\n[추천 Body Selector 테스트]")
    candidates = [
        'article div.newsct_article',
        'article > div',
        'div#newsct_article article',
        'article div:not([class])',  # class 없는 div
    ]

    for selector in candidates:
        elements = soup.select(selector)
        if elements:
            for i, el in enumerate(elements):
                text = el.get_text(strip=True)
                if len(text) > 500:
                    print(f"\n✓ {selector} [{i}]: {len(text)} chars")
                    print(f"  샘플: {text[:100]}...")
