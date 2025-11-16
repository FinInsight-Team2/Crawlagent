"""
CrawlAgent - DB 검증된 URL 재테스트
Created: 2025-11-15

DB에서 Quality 80+ URL 추출하여 재테스트:
- 10개 샘플 URL 재크롤링
- Master Workflow 실행
- 결과 비교 (기존 vs 재테스트)
"""

import sys
from pathlib import Path
from typing import Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.storage.database import get_db
from src.storage.models import CrawlResult
from src.workflow.master_crawl_workflow import MasterCrawlState, build_master_graph

# Disable verbose logging for cleaner output
logger.remove()
logger.add(sys.stderr, level="WARNING")


def test_single_url(url: str, site_name: str, master_app) -> Dict:
    """
    단일 URL 재테스트 실행

    Returns:
        {
            "url": str,
            "site_name": str,
            "success": bool,
            "uc": str,
            "quality_score": int,
            "title": str,
            "body_length": int,
            "date": str,
            "error": str
        }
    """
    try:
        initial_state: MasterCrawlState = {
            "url": url,
            "site_name": site_name,
            "html_content": None,
            "current_uc": None,
            "next_action": None,
            "failure_count": 0,
            "quality_passed": None,
            "extracted_title": None,
            "extracted_body": None,
            "extracted_date": None,
            "uc1_validation_result": None,
            "uc2_consensus_result": None,
            "uc3_discovery_result": None,
            "final_result": None,
            "error_message": None,
            "workflow_history": [],
            "supervisor_reasoning": None,
            "supervisor_confidence": None,
            "routing_context": None,
        }

        final_state = master_app.invoke(initial_state)

        # 결과 분석
        workflow_path = " → ".join(
            [h.split("(")[0].strip() for h in final_state.get("workflow_history", [])]
        )

        # UC 결정
        uc_path_lower = workflow_path.lower()
        if "uc3" in uc_path_lower:
            uc = "UC3"
        elif "uc2" in uc_path_lower:
            uc = "UC2"
        elif "uc1" in uc_path_lower:
            uc = "UC1"
        else:
            uc = "Unknown"

        # Quality score
        uc1_result = final_state.get("uc1_validation_result", {})
        quality_score = uc1_result.get("quality_score", 0) if uc1_result else 0

        # Success: Quality 80+ or final_result exists
        success = quality_score >= 80 or final_state.get("final_result") is not None

        # Extract data
        final_result = final_state.get("final_result", {})
        title = final_result.get("title", "") if final_result else ""
        body = final_result.get("body", "") if final_result else ""
        date = final_result.get("date", "") if final_result else ""

        error = final_state.get("error_message", "")

        return {
            "url": url,
            "site_name": site_name,
            "success": success,
            "uc": uc,
            "quality_score": quality_score,
            "title": title[:100] if title else "",
            "body_length": len(body) if body else 0,
            "date": date,
            "error": error,
        }

    except Exception as e:
        return {
            "url": url,
            "site_name": site_name,
            "success": False,
            "uc": "Error",
            "quality_score": 0,
            "title": "",
            "body_length": 0,
            "date": "",
            "error": str(e),
        }


def main():
    """
    메인 실행 함수 - DB 검증된 URL 10개 재테스트
    """
    print("=" * 80)
    print("CrawlAgent - DB 검증된 URL 재테스트 (2025-11-15)")
    print("=" * 80)
    print()

    # DB 연결
    db_gen = get_db()
    db = next(db_gen)

    try:
        # DB에서 검증된 URL 10개 추출 (다양한 사이트)
        print("🔍 DB에서 검증된 URL 추출 중...")

        # 사이트별로 다양하게 추출
        test_urls = []
        sites = ["yonhap", "naver", "kbs", "bbc", "cnn", "hankyung", "joongang", "donga", "n", "mk"]

        for site in sites:
            result = (
                db.query(CrawlResult)
                .filter(CrawlResult.site_name == site, CrawlResult.quality_score >= 80)
                .order_by(CrawlResult.created_at.desc())
                .first()
            )

            if result:
                test_urls.append(
                    {
                        "url": result.url,
                        "site_name": result.site_name,
                        "original_quality": result.quality_score,
                        "original_title": result.title[:50] if result.title else "",
                        "original_body_length": len(result.body) if result.body else 0,
                        "original_date": result.date,
                        "original_mode": result.crawl_mode,
                    }
                )

                if len(test_urls) >= 10:
                    break

        print(f"✅ 총 {len(test_urls)}개 URL 추출 완료")
        print()

        # Master workflow 빌드
        print("🏗️  Master Workflow 빌드 중...")
        master_app = build_master_graph()
        print("✅ Master Workflow 준비 완료")
        print()

        # 재테스트 결과 저장
        retest_results = []

        # 10 URL 재테스트
        for i, url_data in enumerate(test_urls, 1):
            print(f"[{i}/{len(test_urls)}] 재테스트 중: {url_data['site_name']}")
            print(f"        URL: {url_data['url'][:70]}...")
            print(f"        원본 Quality: {url_data['original_quality']}")

            result = test_single_url(url_data["url"], url_data["site_name"], master_app)

            # 원본 데이터 추가
            result["original_quality"] = url_data["original_quality"]
            result["original_title"] = url_data["original_title"]
            result["original_body_length"] = url_data["original_body_length"]
            result["original_date"] = url_data["original_date"]
            result["original_mode"] = url_data["original_mode"]

            retest_results.append(result)

            status_icon = "✅" if result["success"] else "❌"
            print(
                f"        {status_icon} 재테스트 Quality: {result['quality_score']} (UC: {result['uc']})"
            )

            # 비교 결과
            quality_diff = result["quality_score"] - url_data["original_quality"]
            if quality_diff != 0:
                diff_icon = "📈" if quality_diff > 0 else "📉"
                print(f"        {diff_icon} Quality 차이: {quality_diff:+d}")

            if not result["success"] and result["error"]:
                print(f"        ⚠️  Error: {result['error'][:80]}")

            print()

        # ============================================================================
        # 최종 결과 요약
        # ============================================================================
        print("=" * 80)
        print("📊 재테스트 결과 요약")
        print("=" * 80)
        print()

        # 성공/실패 카운트
        total = len(retest_results)
        success_count = len([r for r in retest_results if r["success"]])
        fail_count = total - success_count

        print(f"✓ 총 재테스트: {total}개")
        print(f"✅ 성공: {success_count}개 ({success_count/total*100:.1f}%)")
        print(f"❌ 실패: {fail_count}개 ({fail_count/total*100:.1f}%)")
        print()

        # UC별 카운트
        uc1_count = len([r for r in retest_results if r["uc"] == "UC1"])
        uc2_count = len([r for r in retest_results if r["uc"] == "UC2"])
        uc3_count = len([r for r in retest_results if r["uc"] == "UC3"])

        print(f"📍 UC1 (Quality Validation): {uc1_count}개")
        print(f"📍 UC2 (Self-Healing): {uc2_count}개")
        print(f"📍 UC3 (Discovery): {uc3_count}개")
        print()

        # Quality Score 비교
        success_results = [r for r in retest_results if r["success"]]
        if success_results:
            avg_original = sum([r["original_quality"] for r in success_results]) / len(
                success_results
            )
            avg_retest = sum([r["quality_score"] for r in success_results]) / len(success_results)
            print(f"📈 원본 평균 Quality: {avg_original:.1f}/100")
            print(f"📈 재테스트 평균 Quality: {avg_retest:.1f}/100")
            print(f"📊 Quality 변화: {avg_retest - avg_original:+.1f}")
        else:
            print(f"📈 평균 Quality: N/A (성공한 테스트 없음)")

        print()

        # 상세 비교 테이블
        print("=" * 80)
        print("📋 상세 비교 결과")
        print("=" * 80)
        print()

        for i, r in enumerate(retest_results, 1):
            print(f"{i}. {r['site_name']}")
            print(f"   URL: {r['url'][:70]}...")
            print(f"   원본: Quality={r['original_quality']}, Mode={r['original_mode']}")
            print(f"   재테스트: Quality={r['quality_score']}, UC={r['uc']}")

            if r["success"]:
                print(f"   제목: {r['title'][:60]}...")
                print(f"   본문 길이: {r['body_length']} chars")
                print(f"   날짜: {r['date']}")
            else:
                error_msg = r["error"] if r["error"] else "Unknown error"
                print(f"   ❌ 실패: {error_msg[:60]}")

            print()

        print("=" * 80)
        print("✅ 재테스트 완료")
        print("=" * 80)

    finally:
        db.close()


if __name__ == "__main__":
    main()
