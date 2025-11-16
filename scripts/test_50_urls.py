"""
CrawlAgent - 50 URL 대규모 테스트
Created: 2025-11-14

Phase 1 PoC 검증:
- 50개 다양한 뉴스 사이트 URL 테스트
- SSR 사이트 커버리지 검증
- UC1/UC2/UC3 라우팅 검증
- F1-Score 재계산
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.workflow.master_crawl_workflow import MasterCrawlState, build_master_graph

# Disable verbose logging for cleaner output
logger.remove()
logger.add(sys.stderr, level="WARNING")


# ============================================================================
# 50 URL Test Set (한국 + 국제 뉴스 사이트)
# ============================================================================

TEST_URLS: List[Tuple[str, str, str]] = [
    # 연합뉴스 (10개)
    ("https://www.yna.co.kr/view/AKR20251113155600001", "yonhap", "연합뉴스 1"),
    ("https://www.yna.co.kr/view/AKR20251113155500001", "yonhap", "연합뉴스 2"),
    ("https://www.yna.co.kr/view/AKR20251113155400001", "yonhap", "연합뉴스 3"),
    ("https://www.yna.co.kr/view/AKR20251113155300001", "yonhap", "연합뉴스 4"),
    ("https://www.yna.co.kr/view/AKR20251113155200001", "yonhap", "연합뉴스 5"),
    ("https://www.yna.co.kr/view/AKR20251113155100001", "yonhap", "연합뉴스 6"),
    ("https://www.yna.co.kr/view/AKR20251113155000001", "yonhap", "연합뉴스 7"),
    ("https://www.yna.co.kr/view/AKR20251113154900001", "yonhap", "연합뉴스 8"),
    ("https://www.yna.co.kr/view/AKR20251113154800001", "yonhap", "연합뉴스 9"),
    ("https://www.yna.co.kr/view/AKR20251113154700001", "yonhap", "연합뉴스 10"),
    # 네이버 뉴스 (10개)
    ("https://n.news.naver.com/mnews/article/018/0006164426", "naver", "네이버 1 (이데일리)"),
    ("https://n.news.naver.com/mnews/article/001/0015305216", "naver", "네이버 2 (연합)"),
    ("https://n.news.naver.com/mnews/article/023/0003893742", "naver", "네이버 3 (조선)"),
    ("https://n.news.naver.com/mnews/article/011/0004429163", "naver", "네이버 4 (경향)"),
    ("https://n.news.naver.com/mnews/article/025/0003451296", "naver", "네이버 5 (중앙)"),
    ("https://n.news.naver.com/mnews/article/005/0001774213", "naver", "네이버 6 (국민)"),
    ("https://n.news.naver.com/mnews/article/008/0005121364", "naver", "네이버 7 (매경)"),
    ("https://n.news.naver.com/mnews/article/009/0005433872", "naver", "네이버 8 (한경)"),
    ("https://n.news.naver.com/mnews/article/015/0005089723", "naver", "네이버 9 (한국경제TV)"),
    ("https://n.news.naver.com/mnews/article/022/0003995164", "naver", "네이버 10 (세계일보)"),
    # KBS (5개)
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8117293", "kbs", "KBS 1"),
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8117292", "kbs", "KBS 2"),
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8117291", "kbs", "KBS 3"),
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8117290", "kbs", "KBS 4"),
    ("https://news.kbs.co.kr/news/pc/view/view.do?ncd=8117289", "kbs", "KBS 5"),
    # BBC (5개)
    ("https://www.bbc.com/news/articles/c4gp1p7lx9lo", "bbc", "BBC 1"),
    ("https://www.bbc.com/news/articles/c5yg2p4xe3eo", "bbc", "BBC 2"),
    ("https://www.bbc.com/news/articles/cy4g73ln7k8o", "bbc", "BBC 3"),
    ("https://www.bbc.com/news/articles/cvgmy80xqnwo", "bbc", "BBC 4"),
    ("https://www.bbc.com/news/articles/cnvj4g8lq3no", "bbc", "BBC 5"),
    # CNN (5개)
    ("https://edition.cnn.com/2025/11/13/politics/trump-elon-musk/index.html", "cnn", "CNN 1"),
    ("https://edition.cnn.com/2025/11/13/business/tesla-stock-musk/index.html", "cnn", "CNN 2"),
    ("https://edition.cnn.com/2025/11/13/tech/openai-sora-video/index.html", "cnn", "CNN 3"),
    ("https://edition.cnn.com/2025/11/13/world/climate-cop29-finance/index.html", "cnn", "CNN 4"),
    (
        "https://edition.cnn.com/2025/11/13/health/weight-loss-drugs-heart/index.html",
        "cnn",
        "CNN 5",
    ),
    # 한국경제 (5개)
    ("https://www.hankyung.com/article/2025111355231", "hankyung", "한국경제 1"),
    ("https://www.hankyung.com/article/2025111355151", "hankyung", "한국경제 2"),
    ("https://www.hankyung.com/article/2025111355071", "hankyung", "한국경제 3"),
    ("https://www.hankyung.com/article/2025111354991", "hankyung", "한국경제 4"),
    ("https://www.hankyung.com/article/2025111354911", "hankyung", "한국경제 5"),
    # 중앙일보 (5개)
    ("https://www.joongang.co.kr/article/25302647", "joongang", "중앙일보 1"),
    ("https://www.joongang.co.kr/article/25302646", "joongang", "중앙일보 2"),
    ("https://www.joongang.co.kr/article/25302645", "joongang", "중앙일보 3"),
    ("https://www.joongang.co.kr/article/25302644", "joongang", "중앙일보 4"),
    ("https://www.joongang.co.kr/article/25302643", "joongang", "중앙일보 5"),
    # 동아일보 (5개)
    ("https://www.donga.com/news/Economy/article/all/20251113/130057814/1", "donga", "동아일보 1"),
    ("https://www.donga.com/news/Politics/article/all/20251113/130057813/1", "donga", "동아일보 2"),
    ("https://www.donga.com/news/Society/article/all/20251113/130057812/1", "donga", "동아일보 3"),
    ("https://www.donga.com/news/World/article/all/20251113/130057811/1", "donga", "동아일보 4"),
    ("https://www.donga.com/news/Culture/article/all/20251113/130057810/1", "donga", "동아일보 5"),
]


def test_single_url(url: str, site_name: str, display_name: str, master_app) -> Dict:
    """
    단일 URL 테스트 실행

    Returns:
        {
            "url": str,
            "site_name": str,
            "display_name": str,
            "success": bool,
            "uc": str,
            "quality_score": int,
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
        success = (
            final_state.get("next_action") == "end" and final_state.get("final_result") is not None
        )
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

        error = final_state.get("error_message", "")

        return {
            "url": url,
            "site_name": site_name,
            "display_name": display_name,
            "success": success,
            "uc": uc,
            "quality_score": quality_score,
            "error": error,
        }

    except Exception as e:
        return {
            "url": url,
            "site_name": site_name,
            "display_name": display_name,
            "success": False,
            "uc": "Error",
            "quality_score": 0,
            "error": str(e),
        }


def main():
    """
    메인 실행 함수 - 50 URL 테스트
    """
    print("=" * 80)
    print("CrawlAgent Phase 1 PoC - 50 URL 대규모 테스트")
    print("=" * 80)
    print()

    # Master workflow 빌드
    print("🏗️  Master Workflow 빌드 중...")
    master_app = build_master_graph()
    print("✅ Master Workflow 준비 완료")
    print()

    # 전체 결과 저장
    results = []

    # 50 URL 테스트
    for i, (url, site_name, display_name) in enumerate(TEST_URLS, 1):
        print(f"[{i}/50] 테스트 중: {display_name}")
        print(f"        URL: {url[:60]}...")

        result = test_single_url(url, site_name, display_name, master_app)
        results.append(result)

        status_icon = "✅" if result["success"] else "❌"
        print(f"        {status_icon} 결과: UC={result['uc']}, Quality={result['quality_score']}")

        if not result["success"] and result["error"]:
            print(f"        ⚠️  Error: {result['error'][:80]}")

        print()

    # ============================================================================
    # 최종 결과 요약
    # ============================================================================
    print("=" * 80)
    print("📊 최종 결과 요약")
    print("=" * 80)
    print()

    # 성공/실패 카운트
    total = len(results)
    success_count = len([r for r in results if r["success"]])
    fail_count = total - success_count

    print(f"✓ 총 테스트: {total}개")
    print(f"✅ 성공: {success_count}개 ({success_count/total*100:.1f}%)")
    print(f"❌ 실패: {fail_count}개 ({fail_count/total*100:.1f}%)")
    print()

    # UC별 카운트
    uc1_count = len([r for r in results if r["uc"] == "UC1"])
    uc2_count = len([r for r in results if r["uc"] == "UC2"])
    uc3_count = len([r for r in results if r["uc"] == "UC3"])

    print(f"📍 UC1 (Quality Validation): {uc1_count}개 ({uc1_count/total*100:.1f}%)")
    print(f"📍 UC2 (Self-Healing): {uc2_count}개 ({uc2_count/total*100:.1f}%)")
    print(f"📍 UC3 (Discovery): {uc3_count}개 ({uc3_count/total*100:.1f}%)")
    print()

    # Quality Score 평균
    success_results = [r for r in results if r["success"]]
    if success_results:
        avg_quality = sum([r["quality_score"] for r in success_results]) / len(success_results)
        print(f"📈 평균 Quality Score: {avg_quality:.1f}/100")
    else:
        print(f"📈 평균 Quality Score: N/A (성공한 테스트 없음)")

    print()

    # 사이트별 성공률
    print("=" * 80)
    print("📊 사이트별 성공률")
    print("=" * 80)

    site_stats = {}
    for r in results:
        site = r["site_name"]
        if site not in site_stats:
            site_stats[site] = {"success": 0, "total": 0}
        site_stats[site]["total"] += 1
        if r["success"]:
            site_stats[site]["success"] += 1

    for site, stats in sorted(site_stats.items()):
        success_rate = stats["success"] / stats["total"] * 100
        print(f"{site:15s}: {stats['success']:2d}/{stats['total']:2d} ({success_rate:5.1f}%)")

    print()

    # 실패한 URL 리스트
    if fail_count > 0:
        print("=" * 80)
        print("❌ 실패한 URL 리스트")
        print("=" * 80)

        for r in results:
            if not r["success"]:
                print(f"• {r['display_name']}")
                print(f"  URL: {r['url']}")
                print(f"  Error: {r['error'][:100]}")
                print()

    print("=" * 80)
    print("✅ 50 URL 테스트 완료")
    print("=" * 80)


if __name__ == "__main__":
    main()
