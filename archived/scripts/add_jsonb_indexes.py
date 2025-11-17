"""
DB Optimization Script: Add JSONB GIN Indexes
Phase 3.3: Database Performance Optimization

Purpose:
- Add GIN indexes to JSONB columns for faster JSON queries
- Optimize decision_logs.extra_data searches
- Optimize cost_metrics.extra_data searches

Usage:
    poetry run python scripts/add_jsonb_indexes.py
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from loguru import logger
from sqlalchemy import text

from src.storage.database import engine


def create_jsonb_indexes():
    """
    Create GIN indexes on JSONB columns for performance optimization

    GIN (Generalized Inverted Index):
    - Optimized for JSONB data type
    - Enables fast containment queries (@>, ?, ?&, ?|)
    - Speeds up JSON field searches
    """

    logger.info("=" * 60)
    logger.info("Phase 3.3: Adding JSONB GIN Indexes")
    logger.info("=" * 60)

    try:
        with engine.connect() as conn:

            # 1. Check existing indexes
            logger.info("\n📋 Checking existing indexes...")
            result = conn.execute(
                text(
                    """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename IN ('decision_logs', 'cost_metrics')
                ORDER BY tablename, indexname;
            """
                )
            )

            existing_indexes = result.fetchall()
            logger.info(f"Found {len(existing_indexes)} existing indexes:")
            for idx in existing_indexes:
                logger.info(f"  - {idx[2]} on {idx[1]}")

            # 2. Add GIN indexes to decision_logs JSONB columns
            logger.info("\n🔨 Creating GIN index on decision_logs.gpt_analysis...")

            try:
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_decision_logs_gpt_analysis_gin
                    ON decision_logs USING GIN (gpt_analysis);
                """
                    )
                )
                conn.commit()
                logger.success("✅ GIN index created: idx_decision_logs_gpt_analysis_gin")
            except Exception as e:
                if "already exists" in str(e):
                    logger.warning("⚠️  Index already exists: idx_decision_logs_gpt_analysis_gin")
                else:
                    raise

            logger.info("\n🔨 Creating GIN index on decision_logs.gemini_validation...")

            try:
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_decision_logs_gemini_validation_gin
                    ON decision_logs USING GIN (gemini_validation);
                """
                    )
                )
                conn.commit()
                logger.success("✅ GIN index created: idx_decision_logs_gemini_validation_gin")
            except Exception as e:
                if "already exists" in str(e):
                    logger.warning(
                        "⚠️  Index already exists: idx_decision_logs_gemini_validation_gin"
                    )
                else:
                    raise

            # 3. Add GIN index to cost_metrics.extra_data
            logger.info("\n🔨 Creating GIN index on cost_metrics.extra_data...")

            try:
                conn.execute(
                    text(
                        """
                    CREATE INDEX IF NOT EXISTS idx_cost_metrics_extra_data_gin
                    ON cost_metrics USING GIN (extra_data);
                """
                    )
                )
                conn.commit()
                logger.success("✅ GIN index created: idx_cost_metrics_extra_data_gin")
            except Exception as e:
                if "already exists" in str(e):
                    logger.warning("⚠️  Index already exists: idx_cost_metrics_extra_data_gin")
                else:
                    raise

            # 4. Verify indexes were created
            logger.info("\n✅ Verifying indexes...")
            result = conn.execute(
                text(
                    """
                SELECT
                    tablename,
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE indexname IN (
                    'idx_decision_logs_gpt_analysis_gin',
                    'idx_decision_logs_gemini_validation_gin',
                    'idx_cost_metrics_extra_data_gin'
                )
                ORDER BY tablename;
            """
                )
            )

            new_indexes = result.fetchall()
            if new_indexes:
                logger.success(f"\n✅ Successfully created {len(new_indexes)} GIN indexes:")
                for idx in new_indexes:
                    logger.info(f"  - {idx[1]} on {idx[0]}")
                    logger.info(f"    Definition: {idx[2]}")
            else:
                logger.warning("⚠️  No new indexes found. They may already exist.")

            # 5. Display usage examples
            logger.info("\n" + "=" * 60)
            logger.info("📚 JSONB Query Examples (Now Optimized with GIN)")
            logger.info("=" * 60)
            logger.info(
                """
Examples of queries that will benefit from these indexes:

1. Containment queries (@>) - decision_logs:
   SELECT * FROM decision_logs
   WHERE gpt_analysis @> '{"selectors": {"title": "h1.title"}}';

2. Key existence (?) - cost_metrics:
   SELECT * FROM cost_metrics
   WHERE extra_data ? 'response_time_seconds';

3. Any key exists (?|) - cost_metrics:
   SELECT * FROM cost_metrics
   WHERE extra_data ?| array['function', 'workflow_run_id'];

4. All keys exist (?&) - decision_logs:
   SELECT * FROM decision_logs
   WHERE gemini_validation ?& array['extraction_success', 'quality_score'];

5. JSON field extraction (->) - cost_metrics:
   SELECT
       url,
       extra_data->'response_time_seconds' as response_time
   FROM cost_metrics
   WHERE (extra_data->>'response_time_seconds')::float > 2.0;

6. Nested JSON queries - decision_logs:
   SELECT * FROM decision_logs
   WHERE gpt_analysis->'selectors'->>'title' = 'h1.article-title';

Performance Impact:
- Before: Full table scan (SLOW)
- After: GIN index scan (FAST - 10-100x faster for large tables)
            """
            )

            logger.info("\n" + "=" * 60)
            logger.success("🎉 JSONB GIN Indexes Created Successfully!")
            logger.info("=" * 60)

    except Exception as e:
        logger.error(f"❌ Failed to create indexes: {e}")
        import traceback

        logger.error(traceback.format_exc())
        raise


def analyze_index_usage():
    """
    Analyze index usage statistics (optional)
    """
    logger.info("\n" + "=" * 60)
    logger.info("📊 Index Usage Statistics")
    logger.info("=" * 60)

    try:
        with engine.connect() as conn:
            result = conn.execute(
                text(
                    """
                SELECT
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan as index_scans,
                    idx_tup_read as tuples_read,
                    idx_tup_fetch as tuples_fetched
                FROM pg_stat_user_indexes
                WHERE tablename IN ('decision_logs', 'cost_metrics')
                ORDER BY idx_scan DESC;
            """
                )
            )

            stats = result.fetchall()
            if stats:
                logger.info("\nIndex usage statistics:")
                for stat in stats:
                    logger.info(
                        f"  - {stat[2]} ({stat[1]}): {stat[3]} scans, {stat[4]} tuples read"
                    )
            else:
                logger.info("No index usage statistics available yet (indexes just created)")

    except Exception as e:
        logger.warning(f"Could not fetch index statistics: {e}")


if __name__ == "__main__":
    create_jsonb_indexes()
    analyze_index_usage()

    logger.info("\n" + "=" * 60)
    logger.info("Next Steps:")
    logger.info("=" * 60)
    logger.info("1. ✅ JSONB GIN indexes created")
    logger.info("2. ✅ Connection pool optimized (pool_size=10, max_overflow=20)")
    logger.info("3. 📊 Monitor index usage with: SELECT * FROM pg_stat_user_indexes;")
    logger.info("4. 🚀 Run queries and verify performance improvements")
