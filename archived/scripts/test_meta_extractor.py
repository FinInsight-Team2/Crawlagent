#!/usr/bin/env python3
"""
Meta Extractor 테스트 스크립트

JTBC 기사로 JSON-LD + Meta 태그 추출 검증

작성일: 2025-11-14
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests

from src.utils.meta_extractor import (
    extract_json_ld,
    extract_meta_tags,
    extract_metadata_smart,
    get_metadata_quality_score,
    validate_metadata,
)

# JTBC 테스트 URL (이전 테스트에서 Meta 태그 실패했던 케이스)
TEST_URL = "https://news.jtbc.co.kr/article/NB12270830"


def test_meta_extractor():
    """Meta 추출 테스트"""
    print(f"\n{'='*80}")
    print(f"Meta Extractor Test: JTBC")
    print(f"URL: {TEST_URL}")
    print(f"{'='*80}\n")

    # HTML 다운로드
    print("Downloading HTML...")
    response = requests.get(
        TEST_URL, headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"}
    )
    html = response.text
    print(f"✅ Downloaded: {len(html)} chars\n")

    # 1. JSON-LD 테스트
    print("=" * 80)
    print("1️⃣ JSON-LD Extraction")
    print("=" * 80)
    json_ld = extract_json_ld(html)
    if json_ld:
        print(f"✅ JSON-LD found:")
        print(f"   Title: {json_ld.get('title')}")
        print(f"   Description: {json_ld.get('description', 'N/A')[:80]}...")
        print(f"   Author: {json_ld.get('author', 'N/A')}")
        print(f"   Date: {json_ld.get('date', 'N/A')}")
        print(f"   Image: {json_ld.get('image', 'N/A')[:80]}...")
    else:
        print("❌ No JSON-LD found")

    # 2. Meta 태그 테스트
    print(f"\n{'='*80}")
    print("2️⃣ Meta Tags Extraction")
    print("=" * 80)
    meta = extract_meta_tags(html)
    if meta.get("title"):
        print(f"✅ Meta tags found:")
        print(f"   Title (og:title): {meta.get('title')}")
        print(f"   Description: {meta.get('description', 'N/A')[:80]}...")
        print(f"   Author: {meta.get('author', 'N/A')}")
        print(f"   Date: {meta.get('date', 'N/A')}")
        print(f"   Image: {meta.get('image', 'N/A')[:80]}...")
    else:
        print("❌ No meta tags found")

    # 3. Smart 추출 테스트
    print(f"\n{'='*80}")
    print("3️⃣ Smart Metadata Extraction (Priority: JSON-LD → Meta)")
    print("=" * 80)
    smart_data = extract_metadata_smart(html)
    print(f"Source: {smart_data.get('source')}")
    print(f"Title: {smart_data.get('title')}")
    print(f"Description: {smart_data.get('description', 'N/A')[:80]}...")
    print(f"Author: {smart_data.get('author', 'N/A')}")
    print(f"Date: {smart_data.get('date', 'N/A')}")

    # 4. 품질 점수
    print(f"\n{'='*80}")
    print("4️⃣ Metadata Quality Score")
    print("=" * 80)
    is_valid = validate_metadata(smart_data)
    quality_score = get_metadata_quality_score(smart_data)
    print(f"Valid: {is_valid}")
    print(f"Quality Score: {quality_score:.2f} / 1.00")

    # 5. 결과 요약
    print(f"\n{'='*80}")
    print("📊 Test Summary")
    print("=" * 80)
    print(f"JSON-LD: {'✅ Success' if json_ld else '❌ Failed'}")
    print(f"Meta Tags: {'✅ Success' if meta.get('title') else '❌ Failed'}")
    print(f"Smart Extraction: {'✅ Success' if smart_data.get('title') else '❌ Failed'}")
    print(f"Quality Score: {quality_score:.2f}")

    # 이전 CSS 셀렉터와 비교
    print(f"\n{'='*80}")
    print("🔍 Comparison with CSS Selector (Previous Test)")
    print("=" * 80)
    print(f"CSS selector 'meta[property=\"og:title\"]' (BeautifulSoup): ❌ Failed (empty)")
    print(f"New XPath-based extraction: {'✅ Success' if smart_data.get('title') else '❌ Failed'}")

    return smart_data.get("title") is not None


if __name__ == "__main__":
    success = test_meta_extractor()
    sys.exit(0 if success else 1)
