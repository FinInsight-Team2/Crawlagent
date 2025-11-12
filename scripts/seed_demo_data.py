"""
데모용 초기 Selector 데이터 생성 스크립트
Created: 2025-11-12

목적:
    Few-Shot Learning이 작동하도록 검증된 Selector를 DB에 심기

검증된 사이트:
    1. 연합뉴스 (한국어, 뉴스)
    2. BBC (영어, 뉴스)
    3. 네이버뉴스 (한국어, 뉴스)
    4. Reuters (영어, 뉴스)
    5. 한국경제 (한국어, 뉴스)
"""

import os
import sys
from datetime import datetime

# 프로젝트 root 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.database import get_db
from src.storage.models import Selector
from loguru import logger


# 검증된 Selector 데이터
DEMO_SELECTORS = [
    {
        "site_name": "yonhap",
        "site_url": "https://www.yna.co.kr",
        "title_selector": "h1.tit",
        "body_selector": "article.story-news p",
        "date_selector": "p.update-time",
        "success_count": 15,
        "failure_count": 0,
        "notes": "연합뉴스 - 한국 대표 통신사"
    },
    {
        "site_name": "bbc",
        "site_url": "https://www.bbc.com/news",
        "title_selector": "h1#main-heading",
        "body_selector": "article div[data-component='text-block'] p",
        "date_selector": "time",
        "success_count": 12,
        "failure_count": 1,
        "notes": "BBC News - 영국 공영방송"
    },
    {
        "site_name": "naver_news",
        "site_url": "https://news.naver.com",
        "title_selector": "h2#title_area span",
        "body_selector": "article#dic_area",
        "date_selector": "span.media_end_head_info_datestamp_time",
        "success_count": 20,
        "failure_count": 0,
        "notes": "네이버뉴스 - 한국 최대 뉴스 포털"
    },
    {
        "site_name": "reuters",
        "site_url": "https://www.reuters.com",
        "title_selector": "h1[data-testid='Heading']",
        "body_selector": "div[data-testid='paragraph-0'] p",
        "date_selector": "time",
        "success_count": 8,
        "failure_count": 2,
        "notes": "Reuters - 국제 통신사"
    },
    {
        "site_name": "hankyung",
        "site_url": "https://www.hankyung.com",
        "title_selector": "h1.headline",
        "body_selector": "div.article-body p",
        "date_selector": "span.date-time",
        "success_count": 10,
        "failure_count": 1,
        "notes": "한국경제 - 경제 전문 언론"
    }
]


def seed_demo_selectors():
    """
    데모용 Selector 데이터를 DB에 삽입
    """
    db = next(get_db())

    try:
        logger.info("🌱 Starting demo data seeding...")

        for selector_data in DEMO_SELECTORS:
            site_name = selector_data["site_name"]

            # 기존 데이터 확인
            existing = db.query(Selector).filter(Selector.site_name == site_name).first()

            if existing:
                logger.info(f"  ⏭️  {site_name} already exists, skipping...")
                continue

            # 새 Selector 생성 (Selector 모델에 맞게 수정)
            new_selector = Selector(
                site_name=selector_data["site_name"],
                title_selector=selector_data["title_selector"],
                body_selector=selector_data["body_selector"],
                date_selector=selector_data["date_selector"],
                success_count=selector_data["success_count"],
                failure_count=selector_data["failure_count"],
                site_type="ssr",
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )

            db.add(new_selector)
            logger.info(f"  ✅ Added {site_name} (success: {selector_data['success_count']})")

        db.commit()
        logger.success(f"🎉 Demo data seeding completed! Added {len(DEMO_SELECTORS)} selectors")

        # 결과 확인
        total_count = db.query(Selector).count()
        logger.info(f"📊 Total selectors in DB: {total_count}")

        return True

    except Exception as e:
        logger.error(f"❌ Error seeding demo data: {e}")
        db.rollback()
        return False
    finally:
        db.close()


def verify_few_shot_retrieval():
    """
    Few-Shot Retriever가 제대로 작동하는지 확인
    """
    logger.info("\n🔍 Verifying Few-Shot Retriever...")

    try:
        from src.agents.few_shot_retriever import get_few_shot_examples, format_few_shot_prompt

        examples = get_few_shot_examples(limit=5)

        if not examples:
            logger.error("❌ Few-Shot retrieval returned no results!")
            return False

        logger.success(f"✅ Retrieved {len(examples)} Few-Shot examples:")
        for ex in examples:
            logger.info(f"  - {ex['site_name']}: {ex['title_selector']}")

        # Prompt 포맷 확인
        prompt = format_few_shot_prompt(examples)
        logger.info(f"\n📝 Few-Shot Prompt (length: {len(prompt)} chars):")
        logger.info(prompt[:500] + "...")

        return True

    except Exception as e:
        logger.error(f"❌ Few-Shot verification failed: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("🌱 Demo Data Seeding Script")
    print("="*80 + "\n")

    # 1. Seed demo data
    if seed_demo_selectors():
        print("\n✅ Step 1: Demo data seeded successfully")

        # 2. Verify Few-Shot retrieval
        if verify_few_shot_retrieval():
            print("\n✅ Step 2: Few-Shot retriever working correctly")
            print("\n" + "="*80)
            print("🎉 All checks passed! Ready for demo")
            print("="*80)
        else:
            print("\n❌ Step 2 failed: Few-Shot retriever not working")
    else:
        print("\n❌ Step 1 failed: Could not seed demo data")
