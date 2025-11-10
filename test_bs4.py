#!/usr/bin/env python3
"""BeautifulSoup 로직 테스트"""

import re
import requests
from bs4 import BeautifulSoup

def generate_css_selector(tag):
    """간단한 CSS 셀렉터 생성"""
    parts = []
    if tag.name:
        parts.append(tag.name)
    if tag.get('id'):
        parts.append(f"#{tag.get('id')}")
    if tag.get('class'):
        classes = tag.get('class')
        if isinstance(classes, list):
            parts.append('.' + '.'.join(classes[:2]))
    return ''.join(parts)

# 1. HTML 다운로드
url = "https://n.news.naver.com/mnews/article/009/0005587223"
print(f"Fetching: {url}")
response = requests.get(url)
html = response.text
print(f"HTML length: {len(html)}")

soup = BeautifulSoup(html, 'html.parser')

# 2. 제목 찾기
print("\n=== 제목 후보 ===")
title_candidates = []
for tag in soup.find_all(['h1', 'h2', 'h3']):
    span = tag.find('span')
    text = span.get_text(strip=True) if span else tag.get_text(strip=True)

    if 10 <= len(text) <= 200:
        selector = generate_css_selector(tag)

        has_id = tag.get('id') is not None
        has_title_class = any(cls in tag.get('class', []) for cls in ['title', 'headline', 'head'])

        confidence = 0.9 if tag.name == 'h1' else (0.8 if tag.name == 'h2' else 0.6)
        if has_id or has_title_class:
            confidence += 0.1

        title_candidates.append({
            "selector": selector,
            "text_preview": text[:50],
            "tag_name": tag.name,
            "confidence": min(1.0, confidence)
        })

        print(f"  [{tag.name}] {selector}")
        print(f"    Text: {text[:100]}")
        print(f"    Confidence: {min(1.0, confidence)}")

print(f"\nTotal title candidates: {len(title_candidates)}")

# 3. 날짜 찾기
print("\n=== 날짜 후보 ===")
date_candidates = []
date_pattern = r'\d{4}[-/.년]\s*\d{1,2}[-/.월]\s*\d{1,2}'

for tag in soup.find_all(['time', 'span', 'div']):
    text = tag.get_text(strip=True)
    has_date_attr = tag.get('data-date-time') or tag.get('datetime') or tag.get('data-date')

    if re.search(date_pattern, text) or has_date_attr:
        selector = generate_css_selector(tag)

        confidence = 1.0 if tag.name == 'time' else 0.7
        if has_date_attr:
            confidence = 1.0

        date_candidates.append({
            "selector": selector,
            "text_preview": text[:50] if text else str(has_date_attr)[:50],
            "tag_name": tag.name,
            "confidence": confidence
        })

        if len(date_candidates) <= 10:  # 처음 10개만 출력
            print(f"  [{tag.name}] {selector}")
            print(f"    Text: {text[:100] if text else has_date_attr}")
            print(f"    Confidence: {confidence}")

print(f"\nTotal date candidates: {len(date_candidates)}")

# 4. 본문 찾기
print("\n=== 본문 후보 (Top 3) ===")
body_candidates = []
for tag in soup.find_all(['article', 'div', 'section']):
    text = tag.get_text(strip=True)
    if len(text) >= 300:
        selector = generate_css_selector(tag)

        has_article_id = tag.get('id') is not None
        has_article_class = any(cls in tag.get('class', []) for cls in ['article', 'content', 'body', '_article'])

        confidence = min(1.0, len(text) / 2000)
        if tag.name == 'article':
            confidence += 0.2
        if has_article_id or has_article_class:
            confidence += 0.1

        body_candidates.append({
            "selector": selector,
            "text_length": len(text),
            "text_preview": text[:100],
            "tag_name": tag.name,
            "confidence": min(1.0, confidence)
        })

body_candidates_sorted = sorted(body_candidates, key=lambda x: x['text_length'], reverse=True)[:3]
for b in body_candidates_sorted:
    print(f"  [{b['tag_name']}] {b['selector']}")
    print(f"    Length: {b['text_length']}, Confidence: {b['confidence']}")
    print(f"    Preview: {b['text_preview']}")
