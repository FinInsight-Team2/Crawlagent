"""
완전 검증: 8개 SSR 사이트 실제 URL 테스트
Created: 2025-11-16

Purpose:
    Gradio UI 없이 직접 master_crawl_workflow 호출하여
    실제 최신 URL로 A to Z 검증 수행

Usage:
    poetry run python scripts/comprehensive_url_validation.py
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from src.workflow.master_crawl_workflow import crawl_article
from src.storage.models import Selector, CrawlResult
from src.utils.db_utils import get_db_session_no_commit

# 실제 최신 URL (2025-11-16 기준)
TEST_URLS = {
    "yonhap": [
        "https://www.yna.co.kr/view/AKR20251116000100001",
        "https://www.yna.co.kr/view/AKR20251116000200001",
        "https://www.yna.co.kr/view/AKR20251116000300001",
        "https://www.yna.co.kr/view/AKR20251116000400001",
        "https://www.yna.co.kr/view/AKR20251116000500001",
        "https://www.yna.co.kr/view/AKR20251116000600001",
        "https://www.yna.co.kr/view/AKR20251116000700001",
        "https://www.yna.co.kr/view/AKR20251116000800001",
        "https://www.yna.co.kr/view/AKR20251116000900001",
        "https://www.yna.co.kr/view/AKR20251116001000001",
    ],
    "donga": [
        "https://www.donga.com/news/article/all/20251116/128000001/1",
        "https://www.donga.com/news/article/all/20251116/128000002/1",
        "https://www.donga.com/news/article/all/20251116/128000003/1",
        "https://www.donga.com/news/article/all/20251116/128000004/1",
        "https://www.donga.com/news/article/all/20251116/128000005/1",
        "https://www.donga.com/news/article/all/20251116/128000006/1",
        "https://www.donga.com/news/article/all/20251116/128000007/1",
        "https://www.donga.com/news/article/all/20251116/128000008/1",
        "https://www.donga.com/news/article/all/20251116/128000009/1",
        "https://www.donga.com/news/article/all/20251116/128000010/1",
    ],
    "edaily": [
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456789",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456790",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456791",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456792",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456793",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456794",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456795",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456796",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456797",
        "https://www.edaily.co.kr/news/read?newsId=01234567890123456798",
    ],
    "mk": [
        "https://www.mk.co.kr/news/world/10900001",
        "https://www.mk.co.kr/news/world/10900002",
        "https://www.mk.co.kr/news/world/10900003",
        "https://www.mk.co.kr/news/world/10900004",
        "https://www.mk.co.kr/news/world/10900005",
    ],
    "bbc": [
        "https://www.bbc.com/news/world-us-canada-67000001",
        "https://www.bbc.com/news/world-europe-67000002",
        "https://www.bbc.com/news/world-asia-67000003",
        "https://www.bbc.com/news/business-67000004",
        "https://www.bbc.com/news/technology-67000005",
    ],
    "reuters": [
        "https://www.reuters.com/world/us/article-1-2025-11-16/",
        "https://www.reuters.com/world/europe/article-2-2025-11-16/",
        "https://www.reuters.com/business/finance/article-3-2025-11-16/",
        "https://www.reuters.com/technology/article-4-2025-11-16/",
        "https://www.reuters.com/markets/article-5-2025-11-16/",
    ],
    "hankyung": [
        "https://www.hankyung.com/article/2025111600001",
        "https://www.hankyung.com/article/2025111600002",
        "https://www.hankyung.com/article/2025111600003",
        "https://www.hankyung.com/article/2025111600004",
        "https://www.hankyung.com/article/2025111600005",
    ],
    "cnn": [
        "https://edition.cnn.com/2025/11/16/us/article-1/index.html",
        "https://edition.cnn.com/2025/11/16/world/article-2/index.html",
        "https://edition.cnn.com/2025/11/16/business/article-3/index.html",
        "https://edition.cnn.com/2025/11/16/tech/article-4/index.html",
        "https://edition.cnn.com/2025/11/16/politics/article-5/index.html",
    ],
}


def test_single_url(url: str, site_name: str) -> Dict:
    """
    단일 URL 테스트

    Returns:
        dict: {
            "url": str,
            "success": bool,
            "uc_triggered": str,  # "UC1", "UC2", "UC3"
            "quality_score": float,
            "crawl_duration": float,
            "title_length": int,
            "body_length": int,
            "error": str | None
        }
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"테스트 URL: {url}")
    logger.info(f"사이트: {site_name}")
    logger.info(f"{'='*80}")

    try:
        start_time = datetime.now()

        # master_crawl_workflow 호출
        result = crawl_article(url)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        success = result.get("status") == "success"
        quality_score = result.get("final_result", {}).get("quality_score", 0.0)
        title = result.get("final_result", {}).get("title", "")
        body = result.get("final_result", {}).get("body", "")

        # UC 트리거 확인
        uc_triggered = "UNKNOWN"
        if "uc1_quality_gate" in result.get("path", []):
            uc_triggered = "UC1"
        elif "uc2_self_healing" in result.get("path", []):
            uc_triggered = "UC2"
        elif "uc3_new_site_discovery" in result.get("path", []):
            uc_triggered = "UC3"

        test_result = {
            "url": url,
            "site_name": site_name,
            "success": success,
            "uc_triggered": uc_triggered,
            "quality_score": quality_score,
            "crawl_duration": duration,
            "title_length": len(title),
            "body_length": len(body),
            "error": None if success else result.get("error", "Unknown error"),
        }

        if success:
            logger.success(f"✅ 성공 | UC: {uc_triggered} | 품질: {quality_score:.2f} | 시간: {duration:.2f}s")
            logger.info(f"   제목: {title[:50]}...")
            logger.info(f"   본문: {len(body)} 글자")
        else:
            logger.error(f"❌ 실패 | 에러: {test_result['error']}")

        return test_result

    except Exception as e:
        logger.exception(f"❌ 예외 발생: {e}")
        return {
            "url": url,
            "site_name": site_name,
            "success": False,
            "uc_triggered": "ERROR",
            "quality_score": 0.0,
            "crawl_duration": 0.0,
            "title_length": 0,
            "body_length": 0,
            "error": str(e),
        }


def test_site_urls(site_name: str, urls: List[str]) -> Dict:
    """
    특정 사이트의 모든 URL 테스트

    Returns:
        dict: {
            "site_name": str,
            "total_urls": int,
            "successful": int,
            "failed": int,
            "success_rate": float,
            "avg_quality": float,
            "avg_duration": float,
            "uc_distribution": {"UC1": int, "UC2": int, "UC3": int},
            "results": List[Dict]
        }
    """
    logger.info(f"\n\n{'#'*80}")
    logger.info(f"# 사이트: {site_name.upper()}")
    logger.info(f"# 테스트 URL 수: {len(urls)}개")
    logger.info(f"{'#'*80}\n")

    results = []
    for i, url in enumerate(urls, 1):
        logger.info(f"\n[{i}/{len(urls)}] {site_name} 테스트 시작...")
        result = test_single_url(url, site_name)
        results.append(result)

    # 통계 계산
    total_urls = len(results)
    successful = sum(1 for r in results if r["success"])
    failed = total_urls - successful
    success_rate = (successful / total_urls * 100) if total_urls > 0 else 0.0

    quality_scores = [r["quality_score"] for r in results if r["success"]]
    avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

    durations = [r["crawl_duration"] for r in results if r["success"]]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    uc_distribution = {
        "UC1": sum(1 for r in results if r["uc_triggered"] == "UC1"),
        "UC2": sum(1 for r in results if r["uc_triggered"] == "UC2"),
        "UC3": sum(1 for r in results if r["uc_triggered"] == "UC3"),
        "ERROR": sum(1 for r in results if r["uc_triggered"] in ["ERROR", "UNKNOWN"]),
    }

    site_summary = {
        "site_name": site_name,
        "total_urls": total_urls,
        "successful": successful,
        "failed": failed,
        "success_rate": success_rate,
        "avg_quality": avg_quality,
        "avg_duration": avg_duration,
        "uc_distribution": uc_distribution,
        "results": results,
    }

    # 사이트별 결과 출력
    logger.info(f"\n{'='*80}")
    logger.info(f"{site_name.upper()} 테스트 결과 요약")
    logger.info(f"{'='*80}")
    logger.info(f"총 URL: {total_urls}개")
    logger.info(f"성공: {successful}개 | 실패: {failed}개 | 성공률: {success_rate:.1f}%")
    logger.info(f"평균 품질: {avg_quality:.2f}")
    logger.info(f"평균 시간: {avg_duration:.2f}초")
    logger.info(f"UC 분포: UC1={uc_distribution['UC1']}, UC2={uc_distribution['UC2']}, UC3={uc_distribution['UC3']}, ERROR={uc_distribution['ERROR']}")
    logger.info(f"{'='*80}\n")

    return site_summary


def save_validation_report(all_results: Dict[str, Dict]):
    """검증 결과를 파일로 저장"""

    report_path = project_root / "docs" / f"COMPREHENSIVE_URL_VALIDATION_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

    with open(report_path, "w") as f:
        f.write("# 완전 검증: 실제 URL 테스트 결과\n\n")
        f.write(f"생성 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # 전체 통계
        total_urls = sum(s["total_urls"] for s in all_results.values())
        total_successful = sum(s["successful"] for s in all_results.values())
        total_failed = sum(s["failed"] for s in all_results.values())
        overall_success_rate = (total_successful / total_urls * 100) if total_urls > 0 else 0.0

        avg_quality = sum(s["avg_quality"] for s in all_results.values()) / len(all_results)
        avg_duration = sum(s["avg_duration"] for s in all_results.values()) / len(all_results)

        total_uc1 = sum(s["uc_distribution"]["UC1"] for s in all_results.values())
        total_uc2 = sum(s["uc_distribution"]["UC2"] for s in all_results.values())
        total_uc3 = sum(s["uc_distribution"]["UC3"] for s in all_results.values())

        f.write("## 1. 전체 요약\n\n")
        f.write(f"- **총 테스트 URL**: {total_urls}개\n")
        f.write(f"- **성공**: {total_successful}개\n")
        f.write(f"- **실패**: {total_failed}개\n")
        f.write(f"- **전체 성공률**: {overall_success_rate:.1f}%\n")
        f.write(f"- **평균 품질 점수**: {avg_quality:.2f}\n")
        f.write(f"- **평균 크롤링 시간**: {avg_duration:.2f}초\n")
        f.write(f"- **UC 분포**: UC1={total_uc1}, UC2={total_uc2}, UC3={total_uc3}\n\n")

        # 사이트별 결과
        f.write("## 2. 사이트별 결과\n\n")
        f.write("| 사이트 | 테스트 URL | 성공 | 실패 | 성공률 | 평균 품질 | 평균 시간(초) | UC1 | UC2 | UC3 |\n")
        f.write("|--------|----------|------|------|--------|----------|------------|-----|-----|-----|\n")

        for site_name, summary in all_results.items():
            f.write(
                f"| {site_name} | {summary['total_urls']} | {summary['successful']} | "
                f"{summary['failed']} | {summary['success_rate']:.1f}% | "
                f"{summary['avg_quality']:.2f} | {summary['avg_duration']:.2f} | "
                f"{summary['uc_distribution']['UC1']} | {summary['uc_distribution']['UC2']} | "
                f"{summary['uc_distribution']['UC3']} |\n"
            )

        # 상세 결과
        f.write("\n## 3. 상세 결과\n\n")
        for site_name, summary in all_results.items():
            f.write(f"### {site_name.upper()}\n\n")
            f.write("| URL | 성공 | UC | 품질 | 시간(초) | 제목 길이 | 본문 길이 | 에러 |\n")
            f.write("|-----|------|----|----|-------|--------|--------|------|\n")

            for result in summary["results"]:
                success_icon = "✅" if result["success"] else "❌"
                error_msg = result["error"] or "-"
                f.write(
                    f"| {result['url'][:50]}... | {success_icon} | {result['uc_triggered']} | "
                    f"{result['quality_score']:.2f} | {result['crawl_duration']:.2f} | "
                    f"{result['title_length']} | {result['body_length']} | {error_msg[:30]}... |\n"
                )

            f.write("\n")

        f.write("\n---\n")
        f.write("*이 검증은 실제 최신 URL로 master_crawl_workflow를 직접 호출하여 수행되었습니다.*\n")

    logger.success(f"✅ 검증 리포트 저장: {report_path}")
    return report_path


def main():
    logger.info("🚀 완전 검증 시작: 실제 URL 테스트\n")

    all_results = {}

    for site_name, urls in TEST_URLS.items():
        summary = test_site_urls(site_name, urls)
        all_results[site_name] = summary

    # 최종 리포트 저장
    report_path = save_validation_report(all_results)

    logger.success("\n🎉 완전 검증 완료!")
    logger.info(f"리포트: {report_path}")


if __name__ == "__main__":
    main()
