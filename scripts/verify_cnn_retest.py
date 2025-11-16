"""
CNN 재테스트 검증 스크립트
Created: 2025-11-12

목적: CNN URL 재테스트 후 결과 확인
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector


def main():
    print("\n" + "=" * 80)
    print("🔍 CNN 재테스트 검증")
    print("=" * 80 + "\n")

    db = next(get_db())

    # 1. Selector 확인
    print("1️⃣  Selector 상태:")
    cnn = db.query(Selector).filter(Selector.site_name == "edition").first()

    if cnn:
        print(f"  Site: {cnn.site_name}")
        print(f"  Title: {cnn.title_selector}")
        print(f"  Body: {cnn.body_selector}")
        print(f"  Date: {cnn.date_selector}")
        print(f"  Success: {cnn.success_count}, Failure: {cnn.failure_count}")
        print(f"  Updated: {cnn.updated_at}")
    else:
        print("  ❌ CNN selector not found")
        return

    # 2. CrawlResult 확인
    print("\n2️⃣  크롤링 결과:")
    cnn_url = "https://edition.cnn.com/2025/11/11/cars/tesla-china-sales-fall-intl-hnk"

    article = db.query(CrawlResult).filter(CrawlResult.url == cnn_url).first()

    if article:
        print(f"  ✅ Article found in DB!")
        print(f"  Title: {article.title[:60] if article.title else 'N/A'}...")
        print(f"  Quality: {article.quality_score}/100")
        print(f"  Mode: {article.crawl_mode}")
        print(f"  Date: {article.created_at}")

        if article.quality_score >= 95:
            print(f"\n  🎉 UC1 성공! (Quality ≥ 95)")
        elif article.quality_score >= 70:
            print(f"\n  ⚠️  UC2 트리거됨 (Quality 70-94)")
        else:
            print(f"\n  ❌ UC1 실패 (Quality < 70)")
    else:
        print(f"  ℹ️  Article not found yet (재테스트 안 했거나 진행 중)")

    # 3. 전체 통계
    print("\n3️⃣  전체 통계:")
    total_selectors = db.query(Selector).count()
    total_articles = db.query(CrawlResult).count()
    high_quality = db.query(CrawlResult).filter(CrawlResult.quality_score >= 95).count()

    print(f"  Selectors: {total_selectors}")
    print(f"  Articles: {total_articles}")
    print(f"  High Quality (≥95): {high_quality}")

    if total_articles > 0:
        rate = high_quality / total_articles * 100
        print(f"  Quality Rate: {rate:.1f}%")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    main()
