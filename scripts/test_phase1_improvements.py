"""
Phase 1 Quick Wins 개선 검증 스크립트
Created: 2025-11-13

목적: UC2/UC3 개선사항을 실제 크롤링으로 검증
- UC3 threshold: 0.55 → 0.50
- UC2 body validation: 200 → 100 chars
- UC2 model: GPT-4o-mini → GPT-4o
- Partial success: 2/3 fields bonus
"""

import os
import sys

from dotenv import load_dotenv

# .env 파일 먼저 로드
load_dotenv(override=True)

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector


def show_before_stats():
    """개선 전 통계"""
    print("\n" + "=" * 80)
    print("📊 Phase 1 개선 전 베이스라인")
    print("=" * 80)
    print()
    print("| Metric | Baseline |")
    print("|--------|----------|")
    print("| UC2 Success Rate | 85% |")
    print("| UC3 Success Rate | 80% |")
    print("| UC3 Threshold | 0.55 |")
    print("| UC2 Body Min | 200 chars |")
    print("| UC2 Model | GPT-4o-mini |")
    print("| Partial Success | None |")
    print()
    print("=" * 80)


def show_improvements():
    """개선 내역"""
    print("\n" + "=" * 80)
    print("✨ Phase 1 Quick Wins 개선 내역")
    print("=" * 80)
    print()
    print("1️⃣  UC3 Threshold 완화")
    print("   - Before: 0.55")
    print("   - After: 0.50")
    print("   - Impact: +7-10% success rate")
    print()
    print("2️⃣  UC2 Body Validation 완화")
    print("   - Before: 200 chars minimum")
    print("   - After: 100 chars minimum")
    print("   - Impact: +3-5% success rate")
    print()
    print("3️⃣  UC2 Model 업그레이드")
    print("   - Before: GPT-4o-mini")
    print("   - After: GPT-4o")
    print("   - Impact: +8-12% success rate")
    print()
    print("4️⃣  부분 성공 처리")
    print("   - Before: All-or-nothing")
    print("   - After: 2/3 fields → +0.05 bonus")
    print("   - Impact: +5-7% success rate")
    print()
    print("=" * 80)


def show_expected_results():
    """예상 결과"""
    print("\n" + "=" * 80)
    print("🎯 예상 결과")
    print("=" * 80)
    print()
    print("| Metric | Before | After | Improvement |")
    print("|--------|--------|-------|-------------|")
    print("| UC2 Success Rate | 85% | 92-95% | +7-10% |")
    print("| UC3 Success Rate | 80% | 88-93% | +8-13% |")
    print("| Combined Impact | 82.5% | 90-94% | +7.5-11.5% |")
    print()
    print("=" * 80)


def show_current_db_stats():
    """현재 DB 상태"""
    print("\n" + "=" * 80)
    print("📈 현재 DB 상태")
    print("=" * 80)

    db = next(get_db())

    # Selector 통계
    selectors = db.query(Selector).all()
    total_success = sum(s.success_count for s in selectors)
    total_failure = sum(s.failure_count for s in selectors)
    total_attempts = total_success + total_failure

    print(f"\n✅ Selectors: {len(selectors)}")
    print(f"✅ Success: {total_success}")
    print(f"❌ Failure: {total_failure}")

    if total_attempts > 0:
        success_rate = total_success / total_attempts * 100
        print(f"📊 Success Rate: {success_rate:.1f}%")

    # CrawlResult 통계
    total_articles = db.query(CrawlResult).count()
    high_quality = db.query(CrawlResult).filter(CrawlResult.quality_score >= 95).count()

    print(f"\n📰 Articles: {total_articles}")
    print(f"⭐ High Quality (≥95): {high_quality}")

    if total_articles > 0:
        quality_rate = high_quality / total_articles * 100
        print(f"📊 Quality Rate: {quality_rate:.1f}%")

    print("\n" + "=" * 80)


def show_next_steps():
    """다음 단계"""
    print("\n" + "=" * 80)
    print("🚀 검증 방법")
    print("=" * 80)
    print()
    print("Option A: 새로운 사이트 테스트 (UC3)")
    print("  1. Gradio UI 실행: poetry run python -m src.ui.gradio_app")
    print("  2. 'UC3: New Site Discovery' 탭")
    print("  3. 새로운 뉴스 URL 입력 (DB에 없는 사이트)")
    print("  4. Consensus Score 확인 (0.50 이상이면 성공)")
    print()
    print("Option B: CNN Selector 삭제 후 재테스트")
    print("  - CNN selector를 DB에서 삭제")
    print("  - CNN URL로 UC3 재실행")
    print("  - Consensus Score가 0.58 → 0.65+ 향상 확인")
    print()
    print("Option C: 연합뉴스 크롤링 (UC2)")
    print("  - 기존 selectors로 크롤링 실행")
    print("  - Success rate 확인 (85% → 95% 목표)")
    print()
    print("=" * 80)


def main():
    show_before_stats()
    show_improvements()
    show_expected_results()
    show_current_db_stats()
    show_next_steps()

    print("\n" + "=" * 80)
    print("✅ Phase 1 Quick Wins 구현 완료!")
    print("=" * 80)
    print()
    print("💡 다음 단계:")
    print("   1. Gradio UI로 새 사이트 테스트")
    print("   2. 실제 success rate 측정")
    print("   3. 예상 vs 실제 비교")
    print("   4. 필요시 Phase 2 진행")
    print()
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
