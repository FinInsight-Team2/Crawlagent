"""
UC1 Validation Agent - Integration Test with Real Database Data
Created: 2025-11-02

Purpose:
    Test UC1 Validation Agent against actual Yonhap crawler data from the database.
    Validate quality_score calculations, decide_action routing, and edge cases.

Execution:
    cd /Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc
    PYTHONPATH=/Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc \
    poetry run python scripts/test_uc1_integration.py
"""

import sys
sys.path.insert(0, '.')

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector
from src.workflow.uc1_validation import create_uc1_validation_agent


def main():
    """
    Integration test workflow:
    1. Load actual crawl_results from database
    2. Run each through UC1 Validation Agent
    3. Compare quality_score with expectations
    4. Analyze decide_action routing patterns
    5. Report statistics and edge cases
    """

    print("=" * 70)
    print("UC1 Validation Agent - Integration Test")
    print("=" * 70)

    # Initialize UC1 graph
    graph = create_uc1_validation_agent()
    print("\n[OK] UC1 Validation Agent loaded")

    # Connect to database
    db = next(get_db())

    try:
        # Fetch all Yonhap crawl results
        print("\n[*] Loading crawl results from database...")
        results = db.query(CrawlResult).filter_by(site_name="yonhap").all()
        print(f"    Found {len(results)} Yonhap articles")

        if len(results) == 0:
            print("\n[WARN] No crawl results found. Run Yonhap crawler first:")
            print("    PYTHONPATH=/Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc \\")
            print("    poetry run scrapy crawl yonhap")
            return

        # Check if selector exists
        selector = db.query(Selector).filter_by(site_name="yonhap").first()
        print(f"[*] Yonhap selector exists: {'YES' if selector else 'NO'}")

        # Statistics tracking
        stats = {
            "total": len(results),
            "save": 0,
            "heal": 0,
            "new_site": 0,
            "score_distribution": {
                "100": 0,
                "90-99": 0,
                "80-89": 0,
                "70-79": 0,
                "60-69": 0,
                "50-59": 0,
                "below_50": 0
            },
            "missing_fields": {
                "title": 0,
                "body": 0,
                "body_short": 0,
                "date": 0
            }
        }

        # Process each article
        print("\n" + "=" * 70)
        print("Processing articles...")
        print("=" * 70)

        for idx, result in enumerate(results, 1):
            # Prepare input for UC1 agent
            uc1_input = {
                "url": result.url,
                "site_name": result.site_name,
                "title": result.title,
                "body": result.body,
                "date": result.date,
                "quality_score": 0,  # Will be calculated
                "missing_fields": [],  # Will be calculated
                "next_action": "save"  # Will be determined
            }

            # Run through UC1 graph
            uc1_result = graph.invoke(uc1_input)

            # Update statistics
            score = uc1_result["quality_score"]
            action = uc1_result["next_action"]
            missing = uc1_result["missing_fields"]

            stats[action] += 1

            if score == 100:
                stats["score_distribution"]["100"] += 1
            elif score >= 90:
                stats["score_distribution"]["90-99"] += 1
            elif score >= 80:
                stats["score_distribution"]["80-89"] += 1
            elif score >= 70:
                stats["score_distribution"]["70-79"] += 1
            elif score >= 60:
                stats["score_distribution"]["60-69"] += 1
            elif score >= 50:
                stats["score_distribution"]["50-59"] += 1
            else:
                stats["score_distribution"]["below_50"] += 1

            for field in missing:
                if field in stats["missing_fields"]:
                    stats["missing_fields"][field] += 1

            # Print details for first 5 and any problematic articles
            if idx <= 5 or score < 80:
                print(f"\n[{idx}/{len(results)}] Article Analysis")
                print(f"  URL: {result.url[:60]}...")
                print(f"  Title: {result.title[:50] if result.title else 'None'}...")
                print(f"  Body length: {len(result.body) if result.body else 0} chars")
                print(f"  Date: {result.date}")
                print(f"  Quality Score: {score}/100")
                print(f"  Missing Fields: {missing if missing else 'None'}")
                print(f"  Next Action: {action}")

                # Flag unexpected results
                if score < 80:
                    print(f"  [WARN] Low quality score detected!")

        # Print summary statistics
        print("\n" + "=" * 70)
        print("SUMMARY STATISTICS")
        print("=" * 70)

        print(f"\nTotal Articles: {stats['total']}")
        print(f"\nNext Action Distribution:")
        print(f"  save:     {stats['save']:3d} ({stats['save']/stats['total']*100:.1f}%)")
        print(f"  heal:     {stats['heal']:3d} ({stats['heal']/stats['total']*100:.1f}%)")
        print(f"  new_site: {stats['new_site']:3d} ({stats['new_site']/stats['total']*100:.1f}%)")

        print(f"\nQuality Score Distribution:")
        for range_name, count in stats["score_distribution"].items():
            if count > 0:
                print(f"  {range_name:8s}: {count:3d} ({count/stats['total']*100:.1f}%)")

        print(f"\nMissing Fields (Total occurrences):")
        for field, count in stats["missing_fields"].items():
            if count > 0:
                print(f"  {field:12s}: {count:3d} ({count/stats['total']*100:.1f}%)")

        # Validation checks
        print("\n" + "=" * 70)
        print("VALIDATION CHECKS")
        print("=" * 70)

        # Check 1: Expected behavior for normal crawl
        if stats['save'] == stats['total']:
            print("\n[OK] All articles passed validation (score >= 80)")
        else:
            print(f"\n[WARN] {stats['heal'] + stats['new_site']} articles failed validation")
            print("       This may indicate DOM changes or quality issues")

        # Check 2: Score consistency with database
        db_avg_score = db.query(CrawlResult.quality_score).filter(
            CrawlResult.site_name == "yonhap",
            CrawlResult.quality_score.isnot(None)
        ).all()

        if db_avg_score:
            db_scores = [s[0] for s in db_avg_score if s[0] is not None]
            if db_scores:
                avg_db = sum(db_scores) / len(db_scores)
                print(f"\n[INFO] Database average quality_score: {avg_db:.1f}")
                print(f"       (from previous crawl, may use old scoring)")

        # Check 3: Body weight improvement validation
        short_body_count = sum(1 for r in results if r.body and 200 <= len(r.body) < 500)
        if short_body_count > 0:
            print(f"\n[INFO] {short_body_count} articles have body length 200-500 chars")
            print("       These should score 30 points (partial credit)")

        print("\n" + "=" * 70)
        print("INTEGRATION TEST COMPLETE")
        print("=" * 70)

        # Next steps recommendation
        print("\nNext Steps:")
        if stats['save'] == stats['total']:
            print("  1. UC1 validation working correctly on real data")
            print("  2. Ready to integrate with Scrapy pipeline")
            print("  3. Begin UC2 DOM Recovery Agent design")
        else:
            print("  1. Investigate articles with score < 80")
            print("  2. Verify DOM structure hasn't changed")
            print("  3. Consider adjusting quality thresholds if needed")

    finally:
        db.close()


if __name__ == "__main__":
    main()
