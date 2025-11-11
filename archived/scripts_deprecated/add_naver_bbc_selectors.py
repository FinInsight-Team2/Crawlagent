"""
Naver와 BBC Selector를 PostgreSQL DB에 추가
Created: 2025-11-02

목적:
    - Naver News selector 추가
    - BBC News selector 추가

실행:
    cd /Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc
    poetry run python scripts/add_naver_bbc_selectors.py
"""

import sys
sys.path.insert(0, '.')

from src.storage.database import get_db
from src.storage.models import Selector


def add_selectors():
    """Naver와 BBC Selector 추가"""
    print("=" * 70)
    print("Naver & BBC Selector 추가")
    print("=" * 70)

    db = next(get_db())

    try:
        # 1. Naver News Selector
        print("\n[1] Naver News Selector 추가")

        # 기존 확인
        existing_naver = db.query(Selector).filter_by(site_name="naver").first()

        if existing_naver:
            print(f"  ⚠️  'naver' selector already exists (ID={existing_naver.id})")
            print(f"     Updating selectors...")

            # 업데이트
            existing_naver.title_selector = "h2#title_area"
            existing_naver.body_selector = "article#dic_area"
            existing_naver.date_selector = "span.media_end_head_info_datestamp_time"
            existing_naver.site_type = "ssr"
            existing_naver.metadata = {
                "updated": "2025-11-02",
                "section_codes": {
                    "politics": "100",
                    "economy": "101",
                    "society": "102",
                    "culture": "103",
                    "world": "104",
                    "it": "105"
                }
            }

            print(f"  ✅ Updated 'naver' selector")

        else:
            # 신규 추가
            naver_selector = Selector(
                site_name="naver",
                title_selector="h2#title_area",
                body_selector="article#dic_area",
                date_selector="span.media_end_head_info_datestamp_time",
                site_type="ssr",
                metadata={
                    "created": "2025-11-02",
                    "section_codes": {
                        "politics": "100",
                        "economy": "101",
                        "society": "102",
                        "culture": "103",
                        "world": "104",
                        "it": "105"
                    }
                }
            )
            db.add(naver_selector)
            print(f"  ✅ Added new 'naver' selector")

        # 2. BBC News Selector
        print("\n[2] BBC News Selector 추가")

        # 기존 확인
        existing_bbc = db.query(Selector).filter_by(site_name="bbc").first()

        if existing_bbc:
            print(f"  ⚠️  'bbc' selector already exists (ID={existing_bbc.id})")
            print(f"     Updating selectors...")

            # 업데이트
            existing_bbc.title_selector = "h1"
            existing_bbc.body_selector = "div[data-component=\"text-block\"]"
            existing_bbc.date_selector = "time[datetime]"
            existing_bbc.site_type = "ssr"
            existing_bbc.metadata = {
                "updated": "2025-11-02",
                "note": "Body uses multiple text-block divs, need to join"
            }

            print(f"  ✅ Updated 'bbc' selector")

        else:
            # 신규 추가
            bbc_selector = Selector(
                site_name="bbc",
                title_selector="h1",
                body_selector="div[data-component=\"text-block\"]",
                date_selector="time[datetime]",
                site_type="ssr",
                metadata={
                    "created": "2025-11-02",
                    "note": "Body uses multiple text-block divs, need to join"
                }
            )
            db.add(bbc_selector)
            print(f"  ✅ Added new 'bbc' selector")

        # Commit
        db.commit()

        print("\n" + "=" * 70)
        print("Selector 추가 완료")
        print("=" * 70)

        # 최종 확인
        print("\n[DB 현황 확인]")
        all_selectors = db.query(Selector).all()
        for sel in all_selectors:
            print(f"  - {sel.site_name}: Title={sel.title_selector}, Body={sel.body_selector}")

        print(f"\n총 {len(all_selectors)}개 사이트 등록됨")
        print("\n다음 단계:")
        print("  1. Naver 크롤러 테스트: poetry run scrapy crawl naver -a section=economy -a max_articles=10")
        print("  2. BBC 크롤러 테스트: poetry run scrapy crawl bbc -a max_articles=10")

    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    add_selectors()
