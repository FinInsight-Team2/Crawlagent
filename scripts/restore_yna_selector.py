#!/usr/bin/env python3
"""
yna Selector 복구 스크립트 (UC2 데모 후)
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine
from loguru import logger

def restore_yna_selector():
    """yna Selector 복구"""
    db = Session(engine)
    try:
        selector = db.query(Selector).filter(Selector.site_name == "yna").first()

        if not selector:
            logger.warning("❌ yna selector not found in DB")
            return False

        logger.info(f"현재 yna Selector (ID={selector.id}):")
        logger.info(f"  title: {selector.title_selector}")
        logger.info(f"  failure_count: {selector.failure_count}")

        # 복구
        selector.title_selector = "h1.title-type017 > span.tit01"
        selector.body_selector = "div.content03"
        selector.date_selector = "meta[property='article:published_time']"
        selector.failure_count = 0

        db.commit()

        logger.success("✅ yna Selector 복구 완료!")
        logger.info(f"  title: {selector.title_selector}")
        logger.info(f"  failure_count: {selector.failure_count}")
        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("="*80)
    logger.info("UC2 DEMO CLEANUP: Restore yna Selector")
    logger.info("="*80)

    result = restore_yna_selector()
    sys.exit(0 if result else 1)
