#!/usr/bin/env python3
"""
UC3 Demo Script: Reset Donga Selector
동아일보 Selector를 삭제하여 UC3 Discovery 시연 준비
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from src.storage.models import Selector
from src.storage.database import engine
from loguru import logger

def reset_donga_selector():
    """
    동아일보 Selector 삭제
    UC3 Discovery 시연을 위한 준비
    """
    db = Session(engine)
    try:
        # Find Donga selector
        selector = db.query(Selector).filter(Selector.site_name == "donga").first()

        if not selector:
            logger.warning("❌ Donga selector not found in DB")
            return False

        logger.info(f"✅ Found Donga selector (ID: {selector.id})")
        logger.info(f"   Success count: {selector.success_count}")
        logger.info(f"   Failure count: {selector.failure_count}")

        # Delete selector
        db.delete(selector)
        db.commit()

        logger.success("🗑️  Donga selector deleted successfully")
        logger.info("🎬 Ready for UC3 Discovery demo!")

        return True

    except Exception as e:
        logger.error(f"❌ Error: {e}")
        db.rollback()
        return False
    finally:
        db.close()

if __name__ == "__main__":
    logger.info("="*80)
    logger.info("UC3 DEMO PREPARATION: Reset Donga Selector")
    logger.info("="*80)

    result = reset_donga_selector()

    if result:
        logger.info("\n" + "="*80)
        logger.info("NEXT STEPS:")
        logger.info("1. Open Gradio UI: http://localhost:7860")
        logger.info("2. Go to '실시간 크롤링' tab")
        logger.info("3. Enter URL: https://www.donga.com/news/Inter/article/all/20251114/130542865/1")
        logger.info("4. Select site: donga")
        logger.info("5. Click '크롤링 시작'")
        logger.info("6. Watch UC3 Discovery workflow:")
        logger.info("   → Site Not Found → UC3 Discovery")
        logger.info("   → Claude Proposer (0.93)")
        logger.info("   → GPT-4o Validator (1.00)")
        logger.info("   → JSON-LD (1.00)")
        logger.info("   → Consensus 0.98 ✅")
        logger.info("   → Selector INSERT")
        logger.info("   → UC1 Crawling Success")
        logger.info("="*80)
        sys.exit(0)
    else:
        sys.exit(1)
