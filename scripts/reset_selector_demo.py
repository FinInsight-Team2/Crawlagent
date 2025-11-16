"""
CrawlAgent PoC Demo - DB Selector Reset Script
Created: 2025-11-16

Purpose:
    시연용 DB Selector 초기화 스크립트

    - UC2 Demo: 연합뉴스 Selector를 잘못 수정하여 Self-Healing 트리거
    - UC3 Demo: 동아일보 Selector를 완전 삭제하여 Discovery 트리거
    - Restore: 원래 Selector로 복원

Usage:
    # UC2 시연 준비 (연합뉴스 Selector 잘못 수정)
    poetry run python scripts/reset_selector_demo.py --uc2-demo

    # UC3 시연 준비 (동아일보 Selector 삭제)
    poetry run python scripts/reset_selector_demo.py --uc3-demo

    # 원래 Selector로 복원
    poetry run python scripts/reset_selector_demo.py --restore

    # 모든 시연 준비 (UC2 + UC3)
    poetry run python scripts/reset_selector_demo.py --all-demo
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import argparse

from loguru import logger

from src.storage.database import get_db
from src.storage.models import Selector
from src.utils.db_utils import get_db_session

# 원래 Selector 백업 (복원용)
ORIGINAL_SELECTORS = {
    "yonhap": {
        "title_selector": "h1.tit01",
        "body_selector": "article.article-wrap01",
        "date_selector": "meta[property='article:published_time']",
        "site_type": "ssr",
    },
    "donga": {
        "title_selector": "section.head_group > h1",
        "body_selector": "div.view_body",
        "date_selector": "ul.news_info > li:nth-of-type(2) > button > span:nth-of-type(1)",
        "site_type": "ssr",
    },
}


def reset_yonhap_for_uc2_demo():
    """
    UC2 시연용: 연합뉴스 body_selector를 잘못 수정

    목적: UC1 품질 검증 실패 → UC2 Self-Healing 트리거
    """
    try:
        with get_db_session() as db:
            # 연합뉴스 Selector 조회
            selector = db.query(Selector).filter_by(site_name="yonhap").first()

            if not selector:
                logger.warning("연합뉴스 Selector가 DB에 없습니다. 먼저 생성하세요.")
                return False

            # 백업 (현재 값)
            logger.info(f"현재 body_selector: {selector.body_selector}")

            # 잘못된 Selector로 수정
            wrong_selector = "div.wrong-selector-intentional-error-for-uc2-demo"
            selector.body_selector = wrong_selector

            # Context manager will auto-commit

        logger.success(f"✅ UC2 시연 준비 완료!")
        logger.info(f"   - 연합뉴스 body_selector를 '{wrong_selector}'로 수정")
        logger.info(f"   - 이제 UC 테스트 탭에서 연합뉴스 URL 크롤링 시 UC2가 트리거됩니다.")

        return True

    except Exception as e:
        logger.error(f"❌ 실패: {e}")
        return False


def delete_donga_for_uc3_demo():
    """
    UC3 시연용: 동아일보 Selector 완전 삭제

    목적: Supervisor가 DB에 Selector 없음 감지 → UC3 Discovery 트리거
    """
    try:
        with get_db_session() as db:
            # 동아일보 Selector 조회
            selector = db.query(Selector).filter_by(site_name="donga").first()

            if not selector:
                logger.warning("동아일보 Selector가 이미 없습니다.")
                return True

            # 백업 (로그 출력)
            logger.info(f"삭제할 Selector:")
            logger.info(f"   - title_selector: {selector.title_selector}")
            logger.info(f"   - body_selector: {selector.body_selector}")
            logger.info(f"   - date_selector: {selector.date_selector}")

            # 완전 삭제
            db.delete(selector)
            # Context manager will auto-commit

        logger.success(f"✅ UC3 시연 준비 완료!")
        logger.info(f"   - 동아일보 Selector를 DB에서 완전 삭제")
        logger.info(f"   - 이제 UC 테스트 탭에서 동아일보 URL 크롤링 시 UC3가 트리거됩니다.")

        return True

    except Exception as e:
        logger.error(f"❌ 실패: {e}")
        return False


def restore_original_selectors():
    """
    원래 Selector로 복원

    목적: 시연 후 정상 상태로 되돌리기
    """
    try:
        with get_db_session() as db:
            restored_count = 0

            for site_name, selector_data in ORIGINAL_SELECTORS.items():
                selector = db.query(Selector).filter_by(site_name=site_name).first()

                if selector:
                    # UPDATE
                    selector.title_selector = selector_data["title_selector"]
                    selector.body_selector = selector_data["body_selector"]
                    selector.date_selector = selector_data["date_selector"]
                    selector.site_type = selector_data["site_type"]

                    logger.info(f"✅ {site_name} Selector 복원 완료 (UPDATE)")
                    restored_count += 1
                else:
                    # INSERT
                    new_selector = Selector(
                        site_name=site_name,
                        title_selector=selector_data["title_selector"],
                        body_selector=selector_data["body_selector"],
                        date_selector=selector_data["date_selector"],
                        site_type=selector_data["site_type"],
                    )
                    db.add(new_selector)

                    logger.info(f"✅ {site_name} Selector 복원 완료 (INSERT)")
                    restored_count += 1

            # Context manager will auto-commit

        logger.success(f"🎉 총 {restored_count}개 Selector 복원 완료!")

        return True

    except Exception as e:
        logger.error(f"❌ 복원 실패: {e}")
        return False


def show_current_selectors():
    """현재 DB에 저장된 Selector 확인"""
    from src.utils.db_utils import get_db_session_no_commit

    with get_db_session_no_commit() as db:
        selectors = db.query(Selector).filter(Selector.site_name.in_(["yonhap", "donga"])).all()

        logger.info("=" * 80)
        logger.info("현재 DB Selector 상태")
        logger.info("=" * 80)

        for selector in selectors:
            logger.info(f"\n사이트: {selector.site_name}")
            logger.info(f"  - title_selector: {selector.title_selector}")
            logger.info(f"  - body_selector: {selector.body_selector}")
            logger.info(f"  - date_selector: {selector.date_selector}")
            logger.info(f"  - site_type: {selector.site_type}")

        if len(selectors) == 0:
            logger.warning("연합뉴스 또는 동아일보 Selector가 DB에 없습니다.")

        logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(description="CrawlAgent PoC Demo - DB Selector Reset")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--uc2-demo", action="store_true", help="UC2 시연 준비: 연합뉴스 Selector 잘못 수정"
    )
    group.add_argument(
        "--uc3-demo", action="store_true", help="UC3 시연 준비: 동아일보 Selector 삭제"
    )
    group.add_argument("--all-demo", action="store_true", help="모든 시연 준비: UC2 + UC3")
    group.add_argument("--restore", action="store_true", help="원래 Selector로 복원")
    group.add_argument("--show", action="store_true", help="현재 Selector 상태 확인")

    args = parser.parse_args()

    if args.uc2_demo:
        logger.info("🔧 UC2 시연 준비 시작...")
        reset_yonhap_for_uc2_demo()

    elif args.uc3_demo:
        logger.info("🔍 UC3 시연 준비 시작...")
        delete_donga_for_uc3_demo()

    elif args.all_demo:
        logger.info("🚀 모든 시연 준비 시작...")
        reset_yonhap_for_uc2_demo()
        delete_donga_for_uc3_demo()

    elif args.restore:
        logger.info("♻️  Selector 복원 시작...")
        restore_original_selectors()

    elif args.show:
        show_current_selectors()


if __name__ == "__main__":
    main()
