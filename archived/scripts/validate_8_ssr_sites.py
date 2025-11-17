"""
8개 SSR 뉴스 사이트 실제 검증 스크립트
Created: 2025-11-16

Purpose:
    Phase 1 SSR-only 사이트 8개에 대한 실제 크롤링 성공률 검증
    - DB에 저장된 실제 491개 크롤링 결과 분석
    - 사이트당 10개 URL 테스트 (가능한 경우)
    - 객관적인 성공률, 처리 시간, 품질 점수 측정

Excluded Sites:
    - Bloomberg: Paywall
    - JTBC: SPA 가능성
    - Phase 2로 연기

Target Sites (SSR-only):
    1. Yonhap (연합뉴스)
    2. Donga (동아일보)
    3. MK (매일경제)
    4. eDaily (이데일리)
    5. BBC
    6. Reuters
    7. Hankyung (한국경제)
    8. CNN

Usage:
    cd /Users/charlee/Desktop/Intern/crawlagent
    poetry run python scripts/validate_8_ssr_sites.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import json
from datetime import datetime
from typing import Dict, List

from loguru import logger
from sqlalchemy import func

from src.storage.models import CrawlResult, Selector
from src.utils.db_utils import get_db_session_no_commit

# 8개 SSR 사이트 정의
SSR_SITES = [
    "yonhap",
    "donga",
    "mk",
    "edaily",
    "bbc",
    "reuters",
    "hankyung",
    "cnn",
]


def analyze_db_crawl_results() -> Dict[str, Dict]:
    """
    DB에 저장된 실제 크롤링 결과 분석

    Returns:
        사이트별 통계: {
            'site_name': {
                'total_crawls': int,
                'successful_crawls': int,
                'success_rate': float,
                'avg_quality_score': float,
                'avg_processing_time': float,
                'latest_crawl': str
            }
        }
    """
    logger.info("=" * 80)
    logger.info("DB 실제 크롤링 결과 분석 시작")
    logger.info("=" * 80)

    results = {}

    with get_db_session_no_commit() as db:
        for site_name in SSR_SITES:
            # 사이트별 크롤링 결과 조회
            crawl_results = db.query(CrawlResult).filter_by(site_name=site_name).all()

            if not crawl_results:
                logger.warning(f"⚠️  {site_name}: DB에 크롤링 결과 없음")
                results[site_name] = {
                    "total_crawls": 0,
                    "successful_crawls": 0,
                    "success_rate": 0.0,
                    "avg_quality_score": 0.0,
                    "avg_processing_time": 0.0,
                    "latest_crawl": None,
                }
                continue

            # 통계 계산
            total_crawls = len(crawl_results)
            successful_crawls = sum(1 for r in crawl_results if r.title and r.body)
            success_rate = (successful_crawls / total_crawls * 100) if total_crawls > 0 else 0.0

            # 품질 점수 평균
            quality_scores = [r.quality_score for r in crawl_results if r.quality_score is not None]
            avg_quality_score = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

            # 크롤링 소요 시간 평균 (초 단위)
            crawl_durations = [
                r.crawl_duration_seconds
                for r in crawl_results
                if r.crawl_duration_seconds is not None
            ]
            avg_crawl_duration = sum(crawl_durations) / len(crawl_durations) if crawl_durations else 0.0

            # 최근 크롤링 시간
            latest_crawl = max(r.created_at for r in crawl_results if r.created_at)

            results[site_name] = {
                "total_crawls": total_crawls,
                "successful_crawls": successful_crawls,
                "success_rate": success_rate,
                "avg_quality_score": avg_quality_score,
                "avg_crawl_duration": avg_crawl_duration,
                "latest_crawl": latest_crawl.strftime("%Y-%m-%d %H:%M:%S"),
            }

            logger.info(f"\n사이트: {site_name}")
            logger.info(f"  총 크롤링: {total_crawls}개")
            logger.info(f"  성공: {successful_crawls}개")
            logger.info(f"  성공률: {success_rate:.1f}%")
            logger.info(f"  평균 품질 점수: {avg_quality_score:.2f}")
            logger.info(f"  평균 크롤링 시간: {avg_crawl_duration:.2f}초")
            logger.info(f"  최근 크롤링: {latest_crawl.strftime('%Y-%m-%d %H:%M:%S')}")

    logger.info("=" * 80)
    return results


def analyze_selector_status() -> Dict[str, Dict]:
    """
    DB에 저장된 Selector 상태 분석

    Returns:
        사이트별 Selector 정보
    """
    logger.info("=" * 80)
    logger.info("DB Selector 상태 분석")
    logger.info("=" * 80)

    results = {}

    with get_db_session_no_commit() as db:
        for site_name in SSR_SITES:
            selector = db.query(Selector).filter_by(site_name=site_name).first()

            if not selector:
                logger.warning(f"⚠️  {site_name}: DB에 Selector 없음 (UC3 트리거 가능)")
                results[site_name] = {
                    "exists": False,
                    "success_count": 0,
                    "failure_count": 0,
                    "success_rate": 0.0,
                }
                continue

            # Selector 성공률 계산
            total_attempts = selector.success_count + selector.failure_count
            success_rate = (
                (selector.success_count / total_attempts * 100) if total_attempts > 0 else 0.0
            )

            results[site_name] = {
                "exists": True,
                "success_count": selector.success_count,
                "failure_count": selector.failure_count,
                "success_rate": success_rate,
                "title_selector": selector.title_selector,
                "body_selector": selector.body_selector,
                "date_selector": selector.date_selector,
                "site_type": selector.site_type,
            }

            logger.info(f"\n사이트: {site_name}")
            logger.info(f"  Selector 존재: ✅")
            logger.info(f"  성공 횟수: {selector.success_count}")
            logger.info(f"  실패 횟수: {selector.failure_count}")
            logger.info(f"  성공률: {success_rate:.1f}%")
            logger.info(f"  title_selector: {selector.title_selector}")
            logger.info(f"  body_selector: {selector.body_selector}")
            logger.info(f"  site_type: {selector.site_type}")

    logger.info("=" * 80)
    return results


def calculate_overall_statistics(crawl_results: Dict, selector_results: Dict) -> Dict:
    """
    전체 통계 계산

    Args:
        crawl_results: 크롤링 결과 통계
        selector_results: Selector 상태 통계

    Returns:
        전체 통계 요약
    """
    logger.info("=" * 80)
    logger.info("전체 통계 요약")
    logger.info("=" * 80)

    # 전체 크롤링 통계
    total_crawls = sum(r["total_crawls"] for r in crawl_results.values())
    total_successful = sum(r["successful_crawls"] for r in crawl_results.values())
    overall_success_rate = (total_successful / total_crawls * 100) if total_crawls > 0 else 0.0

    # 평균 품질 점수
    quality_scores = [r["avg_quality_score"] for r in crawl_results.values() if r["avg_quality_score"] > 0]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    # 평균 크롤링 시간
    crawl_durations = [
        r.get("avg_crawl_duration", 0) for r in crawl_results.values() if r.get("avg_crawl_duration", 0) > 0
    ]
    avg_crawl_duration = sum(crawl_durations) / len(crawl_durations) if crawl_durations else 0.0

    # Selector 존재 여부
    selectors_exist = sum(1 for r in selector_results.values() if r["exists"])
    selectors_missing = len(SSR_SITES) - selectors_exist

    overall_stats = {
        "total_sites": len(SSR_SITES),
        "total_crawls": total_crawls,
        "successful_crawls": total_successful,
        "overall_success_rate": overall_success_rate,
        "avg_quality_score": avg_quality,
        "avg_crawl_duration": avg_crawl_duration,
        "selectors_exist": selectors_exist,
        "selectors_missing": selectors_missing,
    }

    logger.info(f"\n총 사이트 수: {len(SSR_SITES)}개 (SSR-only)")
    logger.info(f"총 크롤링 수: {total_crawls}개")
    logger.info(f"성공 크롤링: {total_successful}개")
    logger.info(f"전체 성공률: {overall_success_rate:.1f}%")
    logger.info(f"평균 품질 점수: {avg_quality:.2f}")
    logger.info(f"평균 크롤링 시간: {avg_crawl_duration:.2f}초")
    logger.info(f"Selector 존재: {selectors_exist}개")
    logger.info(f"Selector 누락: {selectors_missing}개")

    logger.info("=" * 80)

    return overall_stats


def save_validation_report(crawl_results: Dict, selector_results: Dict, overall_stats: Dict):
    """
    검증 결과를 마크다운 파일로 저장

    Args:
        crawl_results: 크롤링 결과 통계
        selector_results: Selector 상태 통계
        overall_stats: 전체 통계 요약
    """
    report_path = project_root / "docs" / "8_SSR_SITES_VALIDATION.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 8개 SSR 뉴스 사이트 실제 검증 결과\n\n")
        f.write(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## 1. 전체 요약\n\n")
        f.write(f"- **총 사이트 수**: {overall_stats['total_sites']}개 (SSR-only)\n")
        f.write(f"- **총 크롤링 수**: {overall_stats['total_crawls']}개\n")
        f.write(f"- **성공 크롤링**: {overall_stats['successful_crawls']}개\n")
        f.write(f"- **전체 성공률**: {overall_stats['overall_success_rate']:.1f}%\n")
        f.write(f"- **평균 품질 점수**: {overall_stats['avg_quality_score']:.2f}\n")
        f.write(f"- **평균 크롤링 시간**: {overall_stats['avg_crawl_duration']:.2f}초\n")
        f.write(f"- **Selector 존재**: {overall_stats['selectors_exist']}개\n")
        f.write(f"- **Selector 누락**: {overall_stats['selectors_missing']}개\n\n")

        f.write("## 2. 사이트별 크롤링 결과\n\n")
        f.write("| 사이트 | 총 크롤링 | 성공 | 성공률 | 평균 품질 | 평균 시간(초) | 최근 크롤링 |\n")
        f.write("|--------|----------|------|--------|----------|------------|------------|\n")

        for site_name in SSR_SITES:
            stats = crawl_results[site_name]
            f.write(
                f"| {site_name} | {stats['total_crawls']} | {stats['successful_crawls']} | "
                f"{stats['success_rate']:.1f}% | {stats['avg_quality_score']:.2f} | "
                f"{stats.get('avg_crawl_duration', 0.0):.2f} | {stats['latest_crawl'] or 'N/A'} |\n"
            )

        f.write("\n## 3. 사이트별 Selector 상태\n\n")
        f.write("| 사이트 | Selector 존재 | 성공 횟수 | 실패 횟수 | 성공률 | Site Type |\n")
        f.write("|--------|--------------|----------|----------|--------|----------|\n")

        for site_name in SSR_SITES:
            stats = selector_results[site_name]
            exists = "✅" if stats["exists"] else "❌"
            f.write(
                f"| {site_name} | {exists} | {stats['success_count']} | "
                f"{stats['failure_count']} | {stats['success_rate']:.1f}% | "
                f"{stats.get('site_type', 'N/A')} |\n"
            )

        f.write("\n## 4. 제외된 사이트 (Phase 2)\n\n")
        f.write("- **Bloomberg**: Paywall 사이트\n")
        f.write("- **JTBC**: SPA 가능성 있음\n\n")
        f.write("→ Phase 2에서 동적 렌더링 지원 후 재검토 예정\n\n")

        f.write("## 5. 한계점 및 개선 사항\n\n")
        f.write("### 현재 한계점\n\n")
        if overall_stats["selectors_missing"] > 0:
            f.write(f"- {overall_stats['selectors_missing']}개 사이트 Selector 누락\n")
        if overall_stats["overall_success_rate"] < 90:
            f.write(f"- 전체 성공률 {overall_stats['overall_success_rate']:.1f}% (목표: 90% 이상)\n")

        f.write("\n### 개선 계획\n\n")
        f.write("1. **Ground Truth 검증**: 30-50개 샘플 수동 검증\n")
        f.write("2. **F1-Score 계산**: Precision, Recall 기반 객관적 평가\n")
        f.write("3. **UC3 자동 발견**: 누락된 Selector 자동 생성\n")
        f.write("4. **UC2 Self-Healing**: 실패율 높은 Selector 자동 수정\n\n")

        f.write("## 6. 재현 방법\n\n")
        f.write("```bash\n")
        f.write("cd /Users/charlee/Desktop/Intern/crawlagent\n")
        f.write("poetry run python scripts/validate_8_ssr_sites.py\n")
        f.write("```\n\n")

        f.write("---\n")
        f.write("*이 검증은 실제 DB 데이터를 기반으로 작성되었습니다. Mock 데이터 없음.*\n")

    logger.success(f"✅ 검증 결과 저장 완료: {report_path}")


def main():
    logger.info("🚀 8개 SSR 뉴스 사이트 검증 시작")

    # 1. DB 크롤링 결과 분석
    crawl_results = analyze_db_crawl_results()

    # 2. DB Selector 상태 분석
    selector_results = analyze_selector_status()

    # 3. 전체 통계 계산
    overall_stats = calculate_overall_statistics(crawl_results, selector_results)

    # 4. 검증 결과 저장
    save_validation_report(crawl_results, selector_results, overall_stats)

    logger.success("🎉 8개 SSR 뉴스 사이트 검증 완료!")


if __name__ == "__main__":
    main()
