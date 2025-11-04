"""
NewsFlow PoC - ORM Test Script
Created: 2025-10-28

SQLAlchemy ORM model test
- PostgreSQL connection check
- Query 3 selectors
- Verify ORM models work correctly
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.storage import Selector, get_db


def test_orm_connection():
    """Test ORM connection and data query"""

    print("=" * 60)
    print("NewsFlow PoC - ORM Test")
    print("=" * 60)

    try:
        # Create database session
        with next(get_db()) as db:
            print("\n[OK] PostgreSQL connection successful\n")

            # 1. Query all selectors
            selectors = db.query(Selector).all()
            print(f"[INFO] Selector count: {len(selectors)}\n")

            # 2. Print each selector
            for selector in selectors:
                print(f"[SELECTOR] {selector.site_name}")
                print(f"   - Title: {selector.title_selector}")
                print(f"   - Body:  {selector.body_selector}")
                print(f"   - Date:  {selector.date_selector}")
                print(f"   - Type:  {selector.site_type}")
                print(f"   - Success: {selector.success_count}, Failure: {selector.failure_count}")
                print()

            # 3. Query specific site (yonhap)
            yonhap = db.query(Selector).filter_by(site_name="yonhap").first()
            if yonhap:
                print(f"[OK] Yonhap selector found:")
                print(f"   {yonhap}")
                print()

            # 4. Query SPA sites only
            spa_sites = db.query(Selector).filter_by(site_type="spa").all()
            print(f"[INFO] SPA site count: {len(spa_sites)}")
            for site in spa_sites:
                print(f"   - {site.site_name}")
            print()

            print("=" * 60)
            print("[SUCCESS] ORM test completed!")
            print("=" * 60)

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    test_orm_connection()
