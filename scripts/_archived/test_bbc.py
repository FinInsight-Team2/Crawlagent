"""
BBC News 구조 분석 스크립트
SSR vs SPA 확인 및 CSS Selector 테스트
"""

import requests
from bs4 import BeautifulSoup

def test_bbc_structure():
    """BBC News 기사 페이지 구조 분석"""

    # 최신 BBC News 기사 URL (2024년 기사)
    urls = [
        "https://www.bbc.com/news/world-us-canada-68087177",
        "https://www.bbc.com/news/world-europe-68086234",
        "https://www.bbc.com/news/business-68084567"
    ]

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    print("=" * 80)
    print("BBC News 구조 분석")
    print("=" * 80)

    for i, url in enumerate(urls, 1):
        print(f"\n[Test {i}] URL: {url}")
        try:
            response = requests.get(url, headers=headers, timeout=10)
            print(f"  Status: {response.status_code}")
            print(f"  HTML Length: {len(response.text):,} bytes")

            if response.status_code == 404:
                print("  ❌ 404 Not Found - URL 오래됨")
                continue

            soup = BeautifulSoup(response.text, 'html.parser')

            # h1 태그 확인
            h1_tags = soup.find_all('h1')
            print(f"\n  [h1 tags]: {len(h1_tags)}")
            if h1_tags:
                h1 = h1_tags[0]
                print(f"    Text: {h1.get_text(strip=True)[:100]}")
                print(f"    Classes: {h1.get('class')}")
                print(f"    ID: {h1.get('id')}")

            # article 태그 확인
            article_tags = soup.find_all('article')
            print(f"\n  [article tags]: {len(article_tags)}")
            if article_tags:
                article = article_tags[0]
                text = article.get_text(strip=True)
                print(f"    Content length: {len(text):,} chars")
                print(f"    Preview: {text[:150]}...")

            # time 태그 확인
            time_tags = soup.find_all('time')
            print(f"\n  [time tags]: {len(time_tags)}")
            if time_tags:
                for time_tag in time_tags[:2]:
                    print(f"    datetime: {time_tag.get('datetime')}")
                    print(f"    text: {time_tag.get_text(strip=True)}")

            # data-component 속성 확인
            data_components = soup.find_all(attrs={'data-component': True})
            print(f"\n  [data-component elements]: {len(data_components)}")
            unique_components = set([el.get('data-component') for el in data_components[:20]])
            print(f"    Unique components: {list(unique_components)[:10]}")

            # 본문 후보 찾기
            print(f"\n  [Body candidates]:")
            body_candidates = [
                soup.find('div', {'data-component': 'text-block'}),
                soup.find('div', class_='story-body'),
                soup.find('div', class_='article-body'),
                soup.find('main')
            ]
            for j, candidate in enumerate(body_candidates, 1):
                if candidate:
                    text = candidate.get_text(strip=True)
                    print(f"    Candidate {j}: {len(text)} chars - {str(candidate)[:100]}...")

            print(f"\n  ✅ SSR 확인: HTML에 컨텐츠 존재!")

        except requests.RequestException as e:
            print(f"  ❌ Error: {e}")
        except Exception as e:
            print(f"  ❌ Parsing Error: {e}")

    print("\n" + "=" * 80)
    print("분석 완료")
    print("=" * 80)

if __name__ == "__main__":
    test_bbc_structure()
