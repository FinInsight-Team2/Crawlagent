"""
CrawlAgent - F1-Score 계산 스크립트
Created: 2025-11-14

Phase 1 PoC 성능 평가:
- Precision: 추출한 데이터의 정확도
- Recall: 필요한 데이터를 얼마나 추출했는지
- F1-Score: Precision과 Recall의 조화 평균

평가 기준:
- Title: 10자 이상 → Correct
- Body: 500자 이상 → Correct
- Date: 존재 → Correct
- Quality Score: 80+ → Success
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import func

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector


def calculate_precision_recall(results: List[CrawlResult]) -> Dict[str, float]:
    """
    Precision & Recall 계산

    Precision = TP / (TP + FP)
    - TP (True Positive): 추출 성공 & 품질 80+
    - FP (False Positive): 추출했지만 품질 80 미만

    Recall = TP / (TP + FN)
    - TP (True Positive): 추출 성공 & 품질 80+
    - FN (False Negative): 추출 실패 (품질 80 미만)

    F1-Score = 2 * (Precision * Recall) / (Precision + Recall)
    """
    total = len(results)

    if total == 0:
        return {
            "total": 0,
            "tp": 0,
            "fp": 0,
            "fn": 0,
            "precision": 0.0,
            "recall": 0.0,
            "f1_score": 0.0,
        }

    # Quality Score 기준: 80+ = Success
    tp = len([r for r in results if r.quality_score >= 80])  # True Positive
    fp = len(
        [r for r in results if r.quality_score < 80 and r.quality_score >= 50]
    )  # False Positive (부분 성공)
    fn = len([r for r in results if r.quality_score < 50])  # False Negative (실패)

    # Precision & Recall
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0

    # F1-Score
    f1_score = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "total": total,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": precision,
        "recall": recall,
        "f1_score": f1_score,
    }


def calculate_field_accuracy(results: List[CrawlResult]) -> Dict[str, float]:
    """
    필드별 정확도 계산

    - Title Accuracy: 10자 이상 추출 비율
    - Body Accuracy: 500자 이상 추출 비율
    - Date Accuracy: 날짜 추출 비율
    """
    total = len(results)

    if total == 0:
        return {
            "title_accuracy": 0.0,
            "body_accuracy": 0.0,
            "date_accuracy": 0.0,
            "overall_accuracy": 0.0,
        }

    title_correct = len([r for r in results if r.title and len(r.title) >= 10])
    body_correct = len([r for r in results if r.body and len(r.body) >= 500])
    date_correct = len([r for r in results if r.date])

    title_accuracy = title_correct / total
    body_accuracy = body_correct / total
    date_accuracy = date_correct / total
    overall_accuracy = (title_accuracy + body_accuracy + date_accuracy) / 3

    return {
        "title_accuracy": title_accuracy,
        "body_accuracy": body_accuracy,
        "date_accuracy": date_accuracy,
        "overall_accuracy": overall_accuracy,
    }


def calculate_uc_performance(results: List[CrawlResult]) -> Dict[str, Dict]:
    """
    UC별 성능 계산 (UC1, UC2, UC3)
    """
    uc_stats = {"scrapy": [], "2-agent": []}

    for result in results:
        if result.crawl_mode:
            uc_stats[result.crawl_mode].append(result)

    performance = {}

    for mode, mode_results in uc_stats.items():
        if len(mode_results) == 0:
            continue

        metrics = calculate_precision_recall(mode_results)
        field_acc = calculate_field_accuracy(mode_results)

        avg_quality = sum([r.quality_score for r in mode_results if r.quality_score]) / len(
            mode_results
        )

        performance[mode] = {
            "count": len(mode_results),
            "avg_quality": avg_quality,
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1_score": metrics["f1_score"],
            "title_accuracy": field_acc["title_accuracy"],
            "body_accuracy": field_acc["body_accuracy"],
            "date_accuracy": field_acc["date_accuracy"],
        }

    return performance


def calculate_site_performance(results: List[CrawlResult]) -> Dict[str, Dict]:
    """
    사이트별 성능 계산
    """
    site_stats = {}

    for result in results:
        if result.site_name not in site_stats:
            site_stats[result.site_name] = []
        site_stats[result.site_name].append(result)

    performance = {}

    for site, site_results in site_stats.items():
        metrics = calculate_precision_recall(site_results)
        field_acc = calculate_field_accuracy(site_results)

        avg_quality = sum([r.quality_score for r in site_results if r.quality_score]) / len(
            site_results
        )

        performance[site] = {
            "count": len(site_results),
            "avg_quality": avg_quality,
            "f1_score": metrics["f1_score"],
            "title_accuracy": field_acc["title_accuracy"],
            "body_accuracy": field_acc["body_accuracy"],
            "date_accuracy": field_acc["date_accuracy"],
        }

    return performance


def main():
    """
    메인 실행 함수
    """
    print("=" * 80)
    print("CrawlAgent Phase 1 PoC - F1-Score 평가")
    print("=" * 80)
    print()

    # DB 연결
    db_gen = get_db()
    db = next(db_gen)

    try:
        # 모든 크롤링 결과 조회
        all_results = db.query(CrawlResult).all()

        print(f"📊 전체 크롤링 결과: {len(all_results)}개")
        print()

        # 1. 전체 성능 평가
        print("=" * 80)
        print("1️⃣  전체 성능 평가")
        print("=" * 80)

        overall_metrics = calculate_precision_recall(all_results)
        overall_field_acc = calculate_field_accuracy(all_results)

        print(f"✓ Total Results: {overall_metrics['total']}")
        print(f"✓ True Positive (Quality 80+): {overall_metrics['tp']}")
        print(f"✓ False Positive (Quality 50-79): {overall_metrics['fp']}")
        print(f"✓ False Negative (Quality <50): {overall_metrics['fn']}")
        print()
        print(f"📈 Precision: {overall_metrics['precision']:.2%}")
        print(f"📈 Recall: {overall_metrics['recall']:.2%}")
        print(f"🎯 F1-Score: {overall_metrics['f1_score']:.2%}")
        print()
        print(f"✓ Title Accuracy (10+ chars): {overall_field_acc['title_accuracy']:.2%}")
        print(f"✓ Body Accuracy (500+ chars): {overall_field_acc['body_accuracy']:.2%}")
        print(f"✓ Date Accuracy: {overall_field_acc['date_accuracy']:.2%}")
        print(f"✓ Overall Accuracy: {overall_field_acc['overall_accuracy']:.2%}")
        print()

        # 2. UC별 성능 평가
        print("=" * 80)
        print("2️⃣  UC별 성능 평가 (Crawl Mode)")
        print("=" * 80)

        uc_performance = calculate_uc_performance(all_results)

        for mode, perf in uc_performance.items():
            print(f"\n[{mode.upper()}]")
            print(f"  Count: {perf['count']}")
            print(f"  Avg Quality: {perf['avg_quality']:.1f}")
            print(f"  Precision: {perf['precision']:.2%}")
            print(f"  Recall: {perf['recall']:.2%}")
            print(f"  F1-Score: {perf['f1_score']:.2%}")
            print(f"  Title Accuracy: {perf['title_accuracy']:.2%}")
            print(f"  Body Accuracy: {perf['body_accuracy']:.2%}")
            print(f"  Date Accuracy: {perf['date_accuracy']:.2%}")

        print()

        # 3. 사이트별 성능 평가
        print("=" * 80)
        print("3️⃣  사이트별 성능 평가 (Top 10)")
        print("=" * 80)

        site_performance = calculate_site_performance(all_results)

        # F1-Score 기준 정렬
        sorted_sites = sorted(
            site_performance.items(), key=lambda x: x[1]["f1_score"], reverse=True
        )

        for i, (site, perf) in enumerate(sorted_sites[:10], 1):
            print(f"\n{i}. {site}")
            print(f"   Count: {perf['count']}")
            print(f"   Avg Quality: {perf['avg_quality']:.1f}")
            print(f"   F1-Score: {perf['f1_score']:.2%}")
            print(
                f"   Title: {perf['title_accuracy']:.2%} | Body: {perf['body_accuracy']:.2%} | Date: {perf['date_accuracy']:.2%}"
            )

        print()

        # 4. Quality Score 분포
        print("=" * 80)
        print("4️⃣  Quality Score 분포")
        print("=" * 80)

        score_ranges = {
            "90-100": len([r for r in all_results if r.quality_score >= 90]),
            "80-89": len([r for r in all_results if 80 <= r.quality_score < 90]),
            "70-79": len([r for r in all_results if 70 <= r.quality_score < 80]),
            "60-69": len([r for r in all_results if 60 <= r.quality_score < 70]),
            "50-59": len([r for r in all_results if 50 <= r.quality_score < 60]),
            "0-49": len([r for r in all_results if r.quality_score < 50]),
        }

        for range_name, count in score_ranges.items():
            percentage = count / len(all_results) * 100 if len(all_results) > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"{range_name}: {count:4d} ({percentage:5.1f}%) {bar}")

        print()

        # 5. 요약
        print("=" * 80)
        print("5️⃣  Phase 1 PoC 평가 요약")
        print("=" * 80)

        success_rate = (
            (overall_metrics["tp"] / overall_metrics["total"] * 100)
            if overall_metrics["total"] > 0
            else 0
        )

        print(f"✅ 전체 F1-Score: {overall_metrics['f1_score']:.2%}")
        print(f"✅ 성공률 (Quality 80+): {success_rate:.1f}%")
        print(f"✅ 평균 정확도 (3-Field): {overall_field_acc['overall_accuracy']:.2%}")
        print(f"✅ 테스트 사이트 수: {len(site_performance)}개")
        print(f"✅ 총 크롤링 결과: {len(all_results)}개")

        print()
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
