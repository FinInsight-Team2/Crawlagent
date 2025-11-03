"""
연합뉴스 DOM 구조 테스트 스크립트
Phase 2.0 - Selector 검증용
"""

import requests
from bs4 import BeautifulSoup

url = "https://www.yna.co.kr/view/AKR20251030124600071"

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

print("=" * 80)
print(f"[INFO] Fetching: {url}")
print("=" * 80)

response = requests.get(url, headers=headers)
response.encoding = 'utf-8'
soup = BeautifulSoup(response.text, 'html.parser')

# Title 확인
print("\n[TITLE ANALYSIS]")
print("-" * 80)
h1_tag = soup.find('h1', class_='tit01')
if h1_tag:
    print(f"[OK] Found: <h1 class='tit01'>")
    print(f"Text: {h1_tag.get_text(strip=True)}")
else:
    print("[ERR] h1.tit01 not found")

meta_title = soup.find('meta', property='og:title')
if meta_title:
    print(f"\n[OK] Meta title: {meta_title.get('content')}")

# Body 확인
print("\n\n[BODY ANALYSIS]")
print("-" * 80)

# article.article-wrap01 확인
article = soup.find('article', class_='article-wrap01')
if article:
    text = article.get_text(strip=True)
    print(f"[OK] Found: <article class='article-wrap01'>")
    print(f"Length: {len(text)} chars")
    print(f"Preview: {text[:200]}...")
else:
    print("[ERR] article.article-wrap01 not found")

# div.article-txt 확인 (init_db.sql selector)
article_txt = soup.find('article')
if article_txt:
    div_txt = article_txt.find('div', class_='article-txt')
    if div_txt:
        print(f"\n[OK] Found: <article> <div class='article-txt'>")
        print(f"Length: {len(div_txt.get_text(strip=True))} chars")
    else:
        print(f"\n[WARN] <article> found but no <div class='article-txt'>")
        # 다른 본문 컨테이너 찾기
        content_divs = article_txt.find_all('div')
        print(f"   Found {len(content_divs)} divs in article")
        for idx, div in enumerate(content_divs[:5], 1):
            classes = div.get('class', [])
            text_len = len(div.get_text(strip=True))
            if text_len > 100:
                print(f"   {idx}. <div class='{' '.join(classes)}'> : {text_len} chars")

# Date 확인
print("\n\n[DATE ANALYSIS]")
print("-" * 80)

# time 태그 확인
time_tag = soup.find('time')
if time_tag:
    print(f"[OK] Found: <time> tag")
    print(f"datetime attr: {time_tag.get('datetime')}")
    print(f"Text: {time_tag.get_text(strip=True)}")
    print(f"Classes: {time_tag.get('class')}")
else:
    print("[ERR] <time> tag not found")

# meta 태그 확인
meta_date = soup.find('meta', property='article:published_time')
if meta_date:
    print(f"\n[OK] Meta date: {meta_date.get('content')}")

# 추가 메타데이터 확인
print("\n\n[ADDITIONAL METADATA]")
print("-" * 80)

# Author
author_span = soup.find('span', class_='byline-p')
if author_span:
    print(f"[OK] Author: <span class='byline-p'> : {author_span.get_text(strip=True)}")

# Category
category = soup.find('span', class_='category')
if category:
    print(f"[OK] Category: {category.get_text(strip=True)}")

print("\n" + "=" * 80)
print("[INFO] Analysis complete!")
print("=" * 80)
