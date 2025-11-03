"""
PostgreSQL 데이터베이스 구조 및 데이터 확인 스크립트

사용법:
python scripts/view_db.py
"""

import sys
import os

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.database import get_db
from src.storage.models import Selector, CrawlResult, DecisionLog
from sqlalchemy import inspect, text


def print_separator(title):
    """구분선 출력"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80)


def view_table_structure(db, table_name, model):
    """테이블 구조 확인"""
    print_separator(f"TABLE: {table_name}")

    # 테이블 컬럼 정보
    inspector = inspect(db.bind)
    columns = inspector.get_columns(table_name)

    print("\n[COLUMNS]")
    print(f"{'Column Name':<30} {'Type':<20} {'Nullable':<10} {'Default':<20}")
    print("-"*80)
    for col in columns:
        col_name = col['name']
        col_type = str(col['type'])
        nullable = "YES" if col.get('nullable', True) else "NO"
        default = str(col.get('default', 'NULL'))[:20]
        print(f"{col_name:<30} {col_type:<20} {nullable:<10} {default:<20}")

    # 인덱스 정보
    indexes = inspector.get_indexes(table_name)
    if indexes:
        print("\n[INDEXES]")
        for idx in indexes:
            idx_name = idx['name']
            idx_cols = ', '.join(idx['column_names'])
            unique = "UNIQUE" if idx.get('unique', False) else ""
            print(f"  - {idx_name}: ({idx_cols}) {unique}")

    # PRIMARY KEY 정보
    pk = inspector.get_pk_constraint(table_name)
    if pk and pk.get('constrained_columns'):
        print(f"\n[PRIMARY KEY]: {', '.join(pk['constrained_columns'])}")

    # 데이터 개수
    count = db.query(model).count()
    print(f"\n[RECORD COUNT]: {count} rows")


def view_selectors(db):
    """selectors 테이블 데이터 확인"""
    print_separator("DATA: selectors")

    selectors = db.query(Selector).all()

    if not selectors:
        print("\n[INFO] No data found")
        return

    print(f"\n[INFO] Found {len(selectors)} selectors\n")

    for selector in selectors:
        print(f"ID: {selector.id}")
        print(f"  Site Name: {selector.site_name}")
        print(f"  Site Type: {selector.site_type}")
        print(f"  Title Selector: {selector.title_selector}")
        print(f"  Body Selector: {selector.body_selector}")
        print(f"  Date Selector: {selector.date_selector}")
        print(f"  Success Count: {selector.success_count}")
        print(f"  Failure Count: {selector.failure_count}")
        print(f"  Created At: {selector.created_at}")
        print(f"  Updated At: {selector.updated_at}")
        print("-"*80)


def view_crawl_results(db):
    """crawl_results 테이블 데이터 확인"""
    print_separator("DATA: crawl_results")

    results = db.query(CrawlResult).all()

    if not results:
        print("\n[INFO] No data found")
        return

    print(f"\n[INFO] Found {len(results)} crawl results\n")

    for result in results:
        print(f"ID: {result.id}")
        print(f"  URL: {result.url}")
        print(f"  Site Name: {result.site_name}")
        print(f"  Title: {result.title[:100] if result.title else 'NULL'}...")
        print(f"  Body Length: {len(result.body) if result.body else 0} characters")
        print(f"  Date: {result.date}")
        print(f"  Quality Score: {result.quality_score}")
        print(f"  Crawl Mode: {result.crawl_mode}")
        print(f"  Crawl Duration: {result.crawl_duration_seconds}s")
        print(f"  Created At: {result.created_at}")
        print("-"*80)


def view_decision_logs(db):
    """decision_logs 테이블 데이터 확인"""
    print_separator("DATA: decision_logs")

    logs = db.query(DecisionLog).all()

    if not logs:
        print("\n[INFO] No data found")
        return

    print(f"\n[INFO] Found {len(logs)} decision logs\n")

    for log in logs:
        print(f"ID: {log.id}")
        print(f"  URL: {log.url}")
        print(f"  Site Name: {log.site_name}")
        print(f"  GPT Analysis: {str(log.gpt_analysis)[:100] if log.gpt_analysis else 'NULL'}...")
        print(f"  Gemini Validation: {str(log.gemini_validation)[:100] if log.gemini_validation else 'NULL'}...")
        print(f"  Consensus Reached: {log.consensus_reached}")
        print(f"  New Selector Generated: {log.new_selector_generated}")
        print(f"  Created At: {log.created_at}")
        print("-"*80)


def view_summary(db):
    """전체 요약"""
    print_separator("DATABASE SUMMARY")

    selector_count = db.query(Selector).count()
    crawl_result_count = db.query(CrawlResult).count()
    decision_log_count = db.query(DecisionLog).count()

    print(f"""
[TABLE COUNTS]
  - selectors: {selector_count} rows
  - crawl_results: {crawl_result_count} rows
  - decision_logs: {decision_log_count} rows

[DATABASE INFO]
  - Database: newsflow_poc
  - User: newsflow
  - Host: localhost:5432
  - Tables: 3
    """)


def main():
    """메인 함수"""
    db = next(get_db())

    try:
        # 요약 정보
        view_summary(db)

        # 테이블 구조
        view_table_structure(db, "selectors", Selector)
        view_table_structure(db, "crawl_results", CrawlResult)
        view_table_structure(db, "decision_logs", DecisionLog)

        # 테이블 데이터
        view_selectors(db)
        view_crawl_results(db)
        view_decision_logs(db)

        print("\n" + "="*80)
        print("  View complete!")
        print("="*80 + "\n")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
