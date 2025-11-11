"""
DB Migration Script: Create cost_metrics table
Creates the cost_metrics table for LLM API cost tracking

Usage:
    poetry run python scripts/migrate_cost_metrics.py
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.storage.database import engine
from src.storage.models import Base, CostMetric
from loguru import logger


def create_cost_metrics_table():
    """Create cost_metrics table if it doesn't exist"""

    logger.info("=" * 60)
    logger.info("Creating cost_metrics table...")
    logger.info("=" * 60)

    try:
        # Check if table already exists
        from sqlalchemy import inspect
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        if 'cost_metrics' in existing_tables:
            logger.warning("⚠️  Table 'cost_metrics' already exists. Skipping creation.")
            logger.info("   If you need to recreate it, drop it first:")
            logger.info("   DROP TABLE cost_metrics CASCADE;")
            return False

        # Create only the cost_metrics table
        CostMetric.__table__.create(engine, checkfirst=True)

        logger.success("✅ Table 'cost_metrics' created successfully!")
        logger.info("\nTable Schema:")
        logger.info("  - id (PRIMARY KEY)")
        logger.info("  - timestamp (TIMESTAMP, indexed)")
        logger.info("  - provider (openai/gemini/claude, indexed)")
        logger.info("  - model (gpt-4o-mini, gemini-2.5-pro, etc., indexed)")
        logger.info("  - use_case (uc1/uc2/uc3/other, indexed)")
        logger.info("  - input_tokens, output_tokens, total_tokens (INTEGER)")
        logger.info("  - input_cost, output_cost, total_cost (FLOAT)")
        logger.info("  - url, site_name, workflow_run_id (TEXT, indexed)")
        logger.info("  - extra_data (JSONB)")

        return True

    except Exception as e:
        logger.error(f"❌ Failed to create table: {e}")
        raise


def verify_table():
    """Verify table was created correctly"""

    logger.info("\n" + "=" * 60)
    logger.info("Verifying table creation...")
    logger.info("=" * 60)

    try:
        from sqlalchemy import inspect, text
        inspector = inspect(engine)

        # Check table exists
        if 'cost_metrics' not in inspector.get_table_names():
            logger.error("❌ Table 'cost_metrics' not found!")
            return False

        # Get columns
        columns = inspector.get_columns('cost_metrics')
        logger.info(f"\n✅ Table 'cost_metrics' exists with {len(columns)} columns:")
        for col in columns:
            logger.info(f"   - {col['name']}: {col['type']}")

        # Get indexes
        indexes = inspector.get_indexes('cost_metrics')
        logger.info(f"\n✅ Indexes ({len(indexes)}):")
        for idx in indexes:
            logger.info(f"   - {idx['name']}: {idx['column_names']}")

        # Test insert
        logger.info("\n" + "=" * 60)
        logger.info("Testing INSERT...")
        logger.info("=" * 60)

        with engine.connect() as conn:
            result = conn.execute(text("""
                INSERT INTO cost_metrics (
                    provider, model, use_case,
                    input_tokens, output_tokens, total_tokens,
                    input_cost, output_cost, total_cost,
                    site_name
                ) VALUES (
                    'openai', 'gpt-4o-mini', 'uc1',
                    1000, 200, 1200,
                    0.00015, 0.00012, 0.00027,
                    'test_site'
                )
                RETURNING id, provider, model, total_cost;
            """))
            conn.commit()

            row = result.fetchone()
            logger.success(f"✅ Test INSERT successful!")
            logger.info(f"   ID: {row[0]}")
            logger.info(f"   Provider: {row[1]}")
            logger.info(f"   Model: {row[2]}")
            logger.info(f"   Total Cost: ${row[3]:.6f}")

            # Clean up test data
            conn.execute(text(f"DELETE FROM cost_metrics WHERE id = {row[0]}"))
            conn.commit()
            logger.info("   (Test data cleaned up)")

        return True

    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")
        return False


def main():
    logger.info("🚀 CrawlAgent DB Migration: cost_metrics table")
    logger.info("")

    # Create table
    created = create_cost_metrics_table()

    if created:
        # Verify table
        verify_table()

        logger.info("\n" + "=" * 60)
        logger.success("🎉 Migration completed successfully!")
        logger.info("=" * 60)
        logger.info("Next steps:")
        logger.info("1. Use CostMetric model in workflow code")
        logger.info("2. Log LLM API costs after each call")
        logger.info("3. Query cost_metrics table for analytics")
    else:
        logger.info("\n" + "=" * 60)
        logger.info("Migration skipped (table already exists)")
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
