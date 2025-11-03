"""
뉴스 사이트 HTML 구조 분석 스크립트

사용법:
python scripts/analyze_html.py <url>
"""

import sys
import requests
from bs4 import BeautifulSoup


def analyze_html(url):
    """HTML 구조 분석"""
    print(f"\n{'='*80}")
    print(f"[INFO] Analyzing: {url}")
    print(f"{'='*80}\n")

    # HTML 가져오기
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    response.encoding = 'utf-8'  # UTF-8 인코딩 명시

    soup = BeautifulSoup(response.text, 'html.parser')

    # 기사 URL 목록 찾기 (리스트 페이지용)
    print("[ARTICLE URLs (for list pages)]")
    print("-" * 80)
    article_links = soup.find_all('a', href=True)
    article_urls = []
    for link in article_links:
        href = link['href']
        # 연합뉴스: /view/, 네이버: /read.nhn, BBC: /news/articles/
        if any(pattern in href for pattern in ['/view/', '/read', '/news/articles/']):
            full_url = href if href.startswith('http') else f"https://{url.split('/')[2]}{href}"
            article_urls.append(full_url)
            if len(article_urls) <= 10:  # 처음 10개만 출력
                print(f"{len(article_urls)}. {full_url}")

    if article_urls:
        print(f"\n[INFO] Found {len(article_urls)} article URLs")
    else:
        print("[INFO] No article URLs found (this might be a detail page)")

    # 제목 후보 찾기
    print(f"\n\n[TITLE CANDIDATES]")
    print("-" * 80)

    # h1 태그
    h1_tags = soup.find_all('h1')
    for i, h1 in enumerate(h1_tags, 1):
        classes = ' '.join(h1.get('class', []))
        print(f"{i}. <h1 class='{classes}'> : {h1.get_text(strip=True)[:100]}")

    # meta 태그 (og:title)
    meta_title = soup.find('meta', property='og:title')
    if meta_title:
        print(f"\n[META] og:title : {meta_title.get('content', '')[:100]}")

    # 본문 후보 찾기
    print(f"\n\n[BODY CANDIDATES]")
    print("-" * 80)

    # article 태그
    articles = soup.find_all('article')
    for i, article in enumerate(articles, 1):
        classes = ' '.join(article.get('class', []))
        text = article.get_text(strip=True)[:200]
        print(f"{i}. <article class='{classes}'> : {len(text)} chars")
        print(f"   Preview: {text[:100]}...")

    # div with 'article', 'content', 'body' in class
    content_divs = soup.find_all('div', class_=lambda x: x and any(
        keyword in ' '.join(x).lower()
        for keyword in ['article', 'content', 'body', 'text']
    ))
    for i, div in enumerate(content_divs[:5], 1):  # 최대 5개만
        classes = ' '.join(div.get('class', []))
        text = div.get_text(strip=True)
        print(f"\n{i}. <div class='{classes}'> : {len(text)} chars")
        print(f"   Preview: {text[:150]}...")

    # 날짜 후보 찾기
    print(f"\n\n[DATE CANDIDATES]")
    print("-" * 80)

    # time 태그
    time_tags = soup.find_all('time')
    for i, time_tag in enumerate(time_tags, 1):
        classes = ' '.join(time_tag.get('class', []))
        datetime = time_tag.get('datetime', '')
        text = time_tag.get_text(strip=True)
        print(f"{i}. <time class='{classes}' datetime='{datetime}'> : {text}")

    # meta 태그 (article:published_time)
    meta_date = soup.find('meta', property='article:published_time')
    if meta_date:
        print(f"\n[META] article:published_time : {meta_date.get('content', '')}")

    # span/div with 'date', 'time' in class
    date_elements = soup.find_all(['span', 'div'], class_=lambda x: x and any(
        keyword in ' '.join(x).lower()
        for keyword in ['date', 'time', 'published', 'update']
    ))
    for i, elem in enumerate(date_elements[:5], 1):  # 최대 5개만
        classes = ' '.join(elem.get('class', []))
        text = elem.get_text(strip=True)
        print(f"\n{i}. <{elem.name} class='{classes}'> : {text}")

    print(f"\n{'='*80}")
    print("[INFO] Analysis complete!")
    print(f"{'='*80}\n")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/analyze_html.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    analyze_html(url)
