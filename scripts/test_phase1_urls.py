#!/usr/bin/env python3
"""
Phase 1: 10개 실제 URL 자동 테스트 스크립트

Gradio UI 없이 직접 Master Workflow를 호출하여 테스트합니다.

작성일: 2025-11-13
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState
from src.utils.site_detector import extract_site_id
from loguru import logger

# 10개 테스트 URL
TEST_URLS = [
    ("https://www.donga.com/news/Economy/article/all/20251113/132765807/1", "donga", "동아일보"),
    ("https://news.jtbc.co.kr/article/NB12270830", "jtbc", "JTBC"),
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8407074", "kbs", "KBS"),
    ("https://news.sbs.co.kr/news/endPage.do?news_id=N1008329074", "sbs", "SBS"),
    ("https://www.chosun.com/economy/money/2025/11/13/52MHLOUGURGTFOF5Y3TXN3WVIA/", "chosun", "조선일보"),
    ("https://www.hankyung.com/article/2025111326861", "hankyung", "한국경제"),
    ("https://www.bbc.com/news/articles/c891nvwvg2zo", "bbc", "BBC"),
    ("https://yonhapnewstv.co.kr/news/AKR202511131509545Wu", "yonhapnewstv", "연합뉴스TV"),
    ("https://edition.cnn.com/2025/11/13/business/coffee-prices-not-coming-down", "cnn", "CNN"),
    ("https://n.news.naver.com/mnews/article/018/0006163369", "naver", "네이버뉴스"),
]


def test_single_url(master_app, url: str, expected_site_id: str, site_name_kr: str) -> dict:
    """
    단일 URL 테스트 실행

    Returns:
        테스트 결과 딕셔너리
    """
    print(f"\n{'='*80}")
    print(f"테스트: {site_name_kr} ({expected_site_id})")
    print(f"URL: {url}")
    print(f"{'='*80}")

    # Site ID 추출 확인
    extracted_site_id = extract_site_id(url)
    site_id_match = extracted_site_id == expected_site_id

    print(f"✓ Site ID 추출: {extracted_site_id} {'✅' if site_id_match else f'❌ (예상: {expected_site_id})'}")

    # Workflow 실행
    start_time = time.time()

    try:
        initial_state: MasterCrawlState = {
            "url": url,
            "site_name": extracted_site_id,
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
        elapsed_time = time.time() - start_time

        # 결과 분석
        success = final_state.get("next_action") == "end" and final_state.get("final_result") is not None
        uc_path = " → ".join([h.split("(")[0].strip() for h in final_state.get("workflow_history", [])])

        # Get scores from UC results
        uc1_result = final_state.get("uc1_validation_result", {})
        uc2_result = final_state.get("uc2_consensus_result", {})
        uc3_result = final_state.get("uc3_discovery_result", {})

        quality_score = uc1_result.get("quality_score") if uc1_result else None
        consensus_score = uc2_result.get("consensus_score") if uc2_result else None
        error = final_state.get("error_message")

        # UC 결정 (workflow_history에서 추출)
        uc_path_lower = uc_path.lower()
        if "uc3" in uc_path_lower:
            uc = "UC3"
            score = uc3_result.get("confidence") if uc3_result else None
        elif "uc2" in uc_path_lower:
            uc = "UC2"
            score = consensus_score
        elif "uc1" in uc_path_lower:
            uc = "UC1"
            score = quality_score
        else:
            uc = "Unknown"
            score = None

        # 결과 출력
        status_icon = "✅" if success else "❌"
        print(f"{status_icon} 결과: {'성공' if success else '실패'}")
        print(f"✓ UC 경로: {uc}")
        print(f"✓ 전체 경로: {uc_path}")
        print(f"✓ 소요 시간: {elapsed_time:.2f}s")

        if score is not None:
            print(f"✓ 점수: {score:.2f}")

        if error:
            print(f"❌ 에러: {error}")

        # 추출된 데이터 확인
        final_result = final_state.get("final_result")
        if final_result:
            print(f"✓ Title: {final_result.get('title', 'N/A')[:80]}...")
            print(f"✓ Body Length: {len(final_result.get('body', ''))} chars")
            print(f"✓ Date: {final_result.get('date', 'N/A')}")

        return {
            "url": url,
            "site_id": extracted_site_id,
            "site_name_kr": site_name_kr,
            "expected_site_id": expected_site_id,
            "site_id_match": site_id_match,
            "success": success,
            "uc": uc,
            "uc_path": uc_path,
            "elapsed_time": elapsed_time,
            "score": score,
            "error": error,
            "final_result": final_result,
        }

    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"❌ 예외 발생: {e}")

        return {
            "url": url,
            "site_id": extracted_site_id,
            "site_name_kr": site_name_kr,
            "expected_site_id": expected_site_id,
            "site_id_match": site_id_match,
            "success": False,
            "uc": "Error",
            "uc_path": "Error",
            "elapsed_time": elapsed_time,
            "score": None,
            "error": str(e),
            "final_result": None,
        }


def main():
    """메인 테스트 실행"""
    print("\n" + "="*80)
    print("Phase 1: 10개 실제 URL 자동 테스트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # Master Graph 빌드
    print("\n📊 Master Workflow Graph 빌드 중...")
    master_app = build_master_graph()
    print("✅ Graph 빌드 완료")

    # 10개 URL 테스트
    results = []
    for url, expected_site_id, site_name_kr in TEST_URLS:
        result = test_single_url(master_app, url, expected_site_id, site_name_kr)
        results.append(result)
        time.sleep(1)  # API rate limit 방지

    # 결과 요약
    print("\n" + "="*80)
    print("📊 테스트 결과 요약")
    print("="*80)

    success_count = sum(1 for r in results if r["success"])
    site_id_match_count = sum(1 for r in results if r["site_id_match"])
    uc1_count = sum(1 for r in results if r["uc"] == "UC1")
    uc2_count = sum(1 for r in results if r["uc"] == "UC2")
    uc3_count = sum(1 for r in results if r["uc"] == "UC3")
    error_count = sum(1 for r in results if r["uc"] == "Error")

    total_time = sum(r["elapsed_time"] for r in results)
    avg_time = total_time / len(results)

    print(f"\n총 테스트: {len(results)}개")
    print(f"성공: {success_count}개 ({success_count/len(results)*100:.1f}%)")
    print(f"실패: {len(results) - success_count}개")
    print(f"\nSite ID 정규화:")
    print(f"  정확: {site_id_match_count}/{len(results)} ({site_id_match_count/len(results)*100:.1f}%)")
    print(f"\nUC 분포:")
    print(f"  UC1 (DB Hit): {uc1_count}개")
    print(f"  UC2 (Self-Healing): {uc2_count}개")
    print(f"  UC3 (Discovery): {uc3_count}개")
    print(f"  Error: {error_count}개")
    print(f"\n소요 시간:")
    print(f"  총 시간: {total_time:.2f}s")
    print(f"  평균 시간: {avg_time:.2f}s")

    # 상세 결과 표
    print(f"\n{'='*80}")
    print("📋 상세 결과 표")
    print(f"{'='*80}\n")
    print(f"{'#':<3} {'Site':<15} {'UC':<5} {'결과':<4} {'시간':<8} {'점수':<6} {'Site ID':<8}")
    print("-"*80)

    for i, r in enumerate(results, 1):
        status = "✅" if r["success"] else "❌"
        time_str = f"{r['elapsed_time']:.2f}s"
        score_str = f"{r['score']:.2f}" if r['score'] is not None else "N/A"
        site_id_status = "✅" if r['site_id_match'] else "❌"

        print(f"{i:<3} {r['site_name_kr']:<15} {r['uc']:<5} {status:<4} {time_str:<8} {score_str:<6} {site_id_status:<8}")

    print("\n" + "="*80)
    print(f"완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

    # 실패 케이스 상세
    failed_cases = [r for r in results if not r["success"]]
    if failed_cases:
        print(f"\n{'='*80}")
        print("❌ 실패 케이스 상세")
        print(f"{'='*80}\n")

        for r in failed_cases:
            print(f"Site: {r['site_name_kr']} ({r['site_id']})")
            print(f"URL: {r['url']}")
            print(f"Error: {r['error']}")
            print("-"*80)

    return results


if __name__ == "__main__":
    results = main()
