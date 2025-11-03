"""
실제 분석 결과로 PostgreSQL selectors 테이블 업데이트

사용법:
python scripts/update_selectors.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.database import get_db
from src.storage.models import Selector


def update_selectors():
    """실제 분석 결과로 Selector 업데이트"""
    db = next(get_db())

    print("\n" + "="*80)
    print("[INFO] Updating selectors with actual analysis results...")
    print("="*80 + "\n")

    # 연합뉴스 업데이트
    yonhap = db.query(Selector).filter_by(site_name="yonhap").first()
    if yonhap:
        print("[BEFORE] yonhap:")
        print(f"  title: {yonhap.title_selector}")
        print(f"  body: {yonhap.body_selector}")
        print(f"  date: {yonhap.date_selector}")

        yonhap.title_selector = "h1.tit01"
        yonhap.body_selector = "article.article-wrap01"
        yonhap.date_selector = 'meta[property="article:published_time"]'
        yonhap.site_type = "ssr"

        print("\n[AFTER] yonhap:")
        print(f"  title: {yonhap.title_selector}")
        print(f"  body: {yonhap.body_selector}")
        print(f"  date: {yonhap.date_selector}")
        print(f"  type: {yonhap.site_type}")

    # 네이버 경제 업데이트
    naver = db.query(Selector).filter_by(site_name="naver_economy").first()
    if naver:
        print("\n" + "-"*80)
        print("[BEFORE] naver_economy:")
        print(f"  title: {naver.title_selector}")
        print(f"  body: {naver.body_selector}")
        print(f"  date: {naver.date_selector}")

        naver.title_selector = 'meta[property="og:title"]'
        naver.body_selector = "article.go_trans._article_content"
        naver.date_selector = "span.media_end_head_info_datestamp_time"  # 임시 (추가 분석 필요)
        naver.site_type = "ssr"

        print("\n[AFTER] naver_economy:")
        print(f"  title: {naver.title_selector}")
        print(f"  body: {naver.body_selector}")
        print(f"  date: {naver.date_selector}")
        print(f"  type: {naver.site_type}")

    # BBC는 일단 유지 (Playwright 필요)
    bbc = db.query(Selector).filter_by(site_name="bbc").first()
    if bbc:
        print("\n" + "-"*80)
        print("[INFO] bbc: Keeping existing selectors (requires Playwright)")
        print(f"  title: {bbc.title_selector}")
        print(f"  body: {bbc.body_selector}")
        print(f"  date: {bbc.date_selector}")
        print(f"  type: {bbc.site_type}")

    # DB에 커밋
    db.commit()
    print("\n" + "="*80)
    print("[SUCCESS] Selectors updated!")
    print("="*80 + "\n")


if __name__ == "__main__":
    update_selectors()
