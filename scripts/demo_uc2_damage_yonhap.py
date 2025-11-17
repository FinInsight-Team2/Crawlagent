#!/usr/bin/env python3
"""
UC2 Demo Script: Damage Yonhap Selector
연합뉴스 Selector를 의도적으로 손상시켜 UC2 Self-Healing 시연 준비
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine
from loguru import logger

def damage_yonhap_selector():
    """
    연합뉴스 Selector 손상
    UC2 Self-Healing 시연을 위한 준비
    """
    db = Session(engine)
    try:
        # Find Yonhap selector
        selector = db.query(Selector).filter(Selector.site_name == "yonhap").first()

        if not selector:
            logger.warning("❌ Yonhap selector not found in DB")
            return False

        logger.info(f"✅ Found Yonhap selector (ID: {selector.id})")
        logger.info(f"   Original title_selector: {selector.title_selector}")
        logger.info(f"   Success count: {selector.success_count}")
        logger.info(f"   Failure count: {selector.failure_count}")

        # Backup original selector
        original_title = selector.title_selector
        original_body = selector.body_selector

        # Damage selector (intentionally wrong)
        selector.title_selector = ".wrong-title-selector"
        selector.body_selector = ".wrong-body-selector"

        db.commit()

        logger.success("🔧 Yonhap selector damaged successfully")
        logger.info(f"   New title_selector: {selector.title_selector}")
        logger.info(f"   New body_selector: {selector.body_selector}")
        logger.info("🎬 Ready for UC2 Self-Healing demo!")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def restore_yonhap_selector():
    """
    연합뉴스 Selector 복구 (데모 종료 후)
    """
    db = Session(engine)
    try:
        selector = db.query(Selector).filter(Selector.site_name == "yonhap").first()

        if not selector:
            logger.warning("❌ Yonhap selector not found in DB")
            return False

        # Restore original selector
        selector.title_selector = "h1.title-type017 > span.tit01"
        selector.body_selector = "div.content03"
        selector.date_selector = "meta[property='article:published_time']"
        selector.failure_count = 0

        db.commit()

        logger.success("✅ Yonhap selector restored")
        logger.info(f"   title: {selector.title_selector}")
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

    parser = argparse.ArgumentParser(description="UC2 Demo: Damage/Restore Yonhap Selector")
    parser.add_argument("--restore", action="store_true", help="Restore selector (after demo)")
    args = parser.parse_args()

    logger.info("="*80)

    if args.restore:
        logger.info("UC2 DEMO CLEANUP: Restore Yonhap Selector")
        logger.info("="*80)
        result = restore_yonhap_selector()
    else:
        logger.info("UC2 DEMO PREPARATION: Damage Yonhap Selector")
        logger.info("="*80)
        result = damage_yonhap_selector()

        if result:
            logger.info("\n" + "="*80)
            logger.info("NEXT STEPS:")
            logger.info("1. Open Gradio UI: http://localhost:7860")
            logger.info("2. Go to '실시간 크롤링' tab")
            logger.info("3. Enter URL: https://www.yna.co.kr/view/AKR20251116034800504")
            logger.info("4. Select site: yonhap")
            logger.info("5. Click '크롤링 시작'")
            logger.info("6. Watch UC2 Self-Healing workflow:")
            logger.info("   → UC1 → FAIL (quality 20)")
            logger.info("   → UC1 → FAIL (quality 20)")
            logger.info("   → UC1 → FAIL (quality 20) [3회 실패]")
            logger.info("   → UC2 Self-Healing")
            logger.info("   → Claude Proposer (0.92)")
            logger.info("   → GPT-4o Validator (0.98)")
            logger.info("   → Consensus 0.75 ✅")
            logger.info("   → Selector UPDATE")
            logger.info("   → UC1 Retry → SUCCESS (quality 100)")
            logger.info("\n7. Test UC1 routing after healing:")
            logger.info("   → Enter another Yonhap URL")
            logger.info("   → Should go directly to UC1 (no UC2)")
            logger.info("   → $0 cost ✅")
            logger.info("\n8. After demo, restore selector:")
            logger.info("   python scripts/demo_uc2_damage_yonhap.py --restore")
            logger.info("="*80)

    sys.exit(0 if result else 1)
