#!/usr/bin/env python3
"""
UC2 강력 손상 스크립트: Meta 태그 Fallback도 무력화
Trafilatura를 회피하기 위해 body도 완전히 잘못된 selector 사용
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine
from loguru import logger

def strong_damage_yonhap():
    """
    연합뉴스 Selector 강력 손상
    - Meta 태그와 충돌하지 않는 완전히 잘못된 selector
    - failure_count를 2로 설정 (다음 실패 시 UC2 트리거)
    """
    db = Session(engine)
    try:
        selector = db.query(Selector).filter(Selector.site_name == "yonhap").first()

        if not selector:
            logger.warning("❌ Yonhap selector not found in DB")
            return False

        logger.info(f"✅ Found Yonhap selector (ID: {selector.id})")
        logger.info(f"   Current title_selector: {selector.title_selector}")
        logger.info(f"   Current success_count: {selector.success_count}")
        logger.info(f"   Current failure_count: {selector.failure_count}")

        # 강력 손상: 존재하지 않는 class/id 사용
        selector.title_selector = "div.nonexistent-title-class-12345"
        selector.body_selector = "article.nonexistent-body-class-67890"
        selector.date_selector = "span.nonexistent-date-class-99999"
        selector.failure_count = 2  # 다음 실패 시 UC2 트리거

        db.commit()

        logger.success("🔧 Yonhap selector STRONGLY damaged!")
        logger.info(f"   New title_selector: {selector.title_selector}")
        logger.info(f"   New body_selector: {selector.body_selector}")
        logger.info(f"   New date_selector: {selector.date_selector}")
        logger.info(f"   failure_count: {selector.failure_count}")
        logger.info("")
        logger.info("⚠️  주의: Trafilatura가 body를 자동 추출할 수 있으므로")
        logger.info("   Title/Date가 추출되지 않으면 quality_score가 낮아져 UC2 트리거됩니다.")
        logger.info("")
        logger.info("🎬 다음 크롤링 실패 시 UC2 Self-Healing이 트리거됩니다!")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def restore_yonhap():
    """연합뉴스 Selector 복구"""
    db = Session(engine)
    try:
        selector = db.query(Selector).filter(Selector.site_name == "yonhap").first()

        if not selector:
            logger.warning("❌ Yonhap selector not found in DB")
            return False

        # 정상 Selector로 복구
        selector.title_selector = "h1.title-type017 > span.tit01"
        selector.body_selector = "div.content03"
        selector.date_selector = "meta[property='article:published_time']"
        selector.failure_count = 0

        db.commit()

        logger.success("✅ Yonhap selector restored to original!")
        logger.info(f"   title_selector: {selector.title_selector}")
        logger.info(f"   failure_count: {selector.failure_count}")
        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="UC2 Demo: Strong Damage/Restore Yonhap Selector")
    parser.add_argument("--restore", action="store_true", help="Restore selector (after demo)")
    args = parser.parse_args()

    logger.info("="*80)

    if args.restore:
        logger.info("UC2 DEMO CLEANUP: Restore Yonhap Selector")
        logger.info("="*80)
        result = restore_yonhap()
    else:
        logger.info("UC2 DEMO PREPARATION: Strong Damage Yonhap Selector")
        logger.info("="*80)
        result = strong_damage_yonhap()

        if result:
            logger.info("\n" + "="*80)
            logger.info("NEXT STEPS:")
            logger.info("1. Open Gradio UI: http://localhost:7860")
            logger.info("2. Go to '실시간 크롤링' tab")
            logger.info("3. Enter URL: https://www.yna.co.kr/view/AKR20251117142000030")
            logger.info("4. Click '크롤링 시작'")
            logger.info("5. Watch UC2 Self-Healing workflow")
            logger.info("\n6. After demo, restore selector:")
            logger.info("   python scripts/uc2_strong_damage.py --restore")
            logger.info("="*80)

    sys.exit(0 if result else 1)
