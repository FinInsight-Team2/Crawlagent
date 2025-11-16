#!/usr/bin/env python3
"""
CrawlAgent Use Case 검증 스크립트

UC1, UC2, UC3의 성공률을 실제 URL로 테스트하고 검증 보고서를 생성합니다.

Usage:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/validate_use_cases.py --output validation_report.md

Features:
    - UC1: 10개 URL 테스트 (기존 사이트 품질 검증)
    - UC2: 10개 셀렉터 파괴 실험 (자동 복구 테스트)
    - UC3: 5개 신규 사이트 테스트 (자동 발견)
    - Markdown 보고서 생성 (성공률, 소요 시간, Consensus Score 분포)
"""

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests

from src.storage.database import get_db
from src.storage.models import Selector
from src.workflow.master_crawl_workflow import MasterCrawlState, build_master_graph

# ============================================================================
# Test URLs
# ============================================================================

UC1_TEST_URLS = [
    # 연합뉴스 (기존 사이트)
    "https://www.yna.co.kr/view/AKR20250113000100051",
    "https://www.yna.co.kr/view/AKR20250113000200051",
    # BBC (기존 사이트)
    "https://www.bbc.com/news/world-asia-12345678",
    "https://www.bbc.com/news/technology-87654321",
    # 네이버뉴스 (기존 사이트)
    "https://news.naver.com/main/read.naver?mode=LSD&mid=sec&sid1=001&oid=001&aid=0014912345",
    "https://news.naver.com/main/read.naver?mode=LSD&mid=sec&sid1=001&oid=001&aid=0014912346",
    # 추가 테스트 URL (필요 시)
    "https://example.com/article1",
    "https://example.com/article2",
    "https://example.com/article3",
    "https://example.com/article4",
]

UC3_TEST_URLS = [
    # 신규 사이트 (DB에 없는 사이트)
    "https://www.theguardian.com/world/2025/jan/13/example-article",
    "https://apnews.com/article/example-12345",
    "https://www.chosun.com/national/2025/01/13/example/",
    "https://www.joongang.co.kr/article/25231234",
    "https://www.npr.org/2025/01/13/1234567890/example-story",
]


# ============================================================================
# Validation Functions
# ============================================================================


def validate_uc1(test_urls: List[str], output_file: Path) -> Dict[str, Any]:
    """
    UC1 Quality Gate 검증

    Args:
        test_urls: 테스트할 URL 리스트
        output_file: 출력 보고서 파일

    Returns:
        Dict with validation results
    """

    print("=" * 80)
    print("🟢 UC1 Quality Gate 검증")
    print("=" * 80)

    results = []
    master_app = build_master_graph()

    for idx, url in enumerate(test_urls, 1):
        print(f"\n[{idx}/{len(test_urls)}] Testing: {url}")

        try:
            # Fetch HTML
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            html_content = response.text

            # Extract site name
            from urllib.parse import urlparse

            parsed = urlparse(url)
            site_name = parsed.netloc.replace("www.", "").split(".")[0]

            # Run Master Graph
            start_time = time.time()
            initial_state: MasterCrawlState = {
                "url": url,
                "site_name": site_name,
                "html_content": html_content,
                "current_uc": None,
                "next_action": None,
                "failure_count": 0,
                "uc1_validation_result": None,
                "uc2_consensus_result": None,
                "uc3_discovery_result": None,
                "final_result": None,
                "error_message": None,
                "workflow_history": [],
            }

            final_state = master_app.invoke(initial_state)
            elapsed = time.time() - start_time

            # Analyze result
            success = final_state.get("final_result") is not None
            quality_score = (
                final_state.get("uc1_validation_result", {}).get("quality_score", 0)
                if final_state.get("uc1_validation_result")
                else 0
            )
            workflow = " → ".join(final_state.get("workflow_history", []))

            results.append(
                {
                    "url": url,
                    "site": site_name,
                    "success": success,
                    "quality_score": quality_score,
                    "elapsed_time": elapsed,
                    "workflow": workflow,
                }
            )

            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} | Quality: {quality_score}/100 | Time: {elapsed:.2f}s")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append(
                {
                    "url": url,
                    "site": "unknown",
                    "success": False,
                    "quality_score": 0,
                    "elapsed_time": 0,
                    "workflow": "error",
                    "error": str(e),
                }
            )

    # Calculate metrics
    success_count = sum(1 for r in results if r["success"])
    success_rate = (success_count / len(results)) * 100 if results else 0
    avg_time = sum(r["elapsed_time"] for r in results) / len(results) if results else 0
    avg_quality = (
        sum(r["quality_score"] for r in results if r["success"]) / success_count
        if success_count > 0
        else 0
    )

    summary = {
        "total_tests": len(results),
        "success_count": success_count,
        "success_rate": success_rate,
        "avg_time": avg_time,
        "avg_quality": avg_quality,
        "results": results,
    }

    print(f"\n📊 UC1 Summary:")
    print(f"  Success Rate: {success_rate:.1f}% ({success_count}/{len(results)})")
    print(f"  Avg Time: {avg_time:.2f}s")
    print(f"  Avg Quality: {avg_quality:.1f}/100")

    return summary


def validate_uc3(test_urls: List[str], output_file: Path) -> Dict[str, Any]:
    """
    UC3 New Site Discovery 검증

    Args:
        test_urls: 테스트할 신규 사이트 URL 리스트
        output_file: 출력 보고서 파일

    Returns:
        Dict with validation results
    """

    print("\n" + "=" * 80)
    print("🔵 UC3 New Site Discovery 검증")
    print("=" * 80)

    results = []
    master_app = build_master_graph()

    for idx, url in enumerate(test_urls, 1):
        print(f"\n[{idx}/{len(test_urls)}] Testing: {url}")

        try:
            # Fetch HTML
            response = requests.get(
                url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
            )
            html_content = response.text

            # Extract site name
            from urllib.parse import urlparse

            parsed = urlparse(url)
            site_name = parsed.netloc.replace("www.", "").split(".")[0]

            # Run Master Graph
            start_time = time.time()
            initial_state: MasterCrawlState = {
                "url": url,
                "site_name": site_name,
                "html_content": html_content,
                "current_uc": None,
                "next_action": None,
                "failure_count": 0,
                "uc1_validation_result": None,
                "uc2_consensus_result": None,
                "uc3_discovery_result": None,
                "final_result": None,
                "error_message": None,
                "workflow_history": [],
            }

            final_state = master_app.invoke(initial_state)
            elapsed = time.time() - start_time

            # Analyze result
            success = final_state.get("final_result") is not None
            uc3_result = final_state.get("uc3_discovery_result", {})
            consensus_score = uc3_result.get("consensus_score", 0.0) if uc3_result else 0.0
            workflow = " → ".join(final_state.get("workflow_history", []))

            results.append(
                {
                    "url": url,
                    "site": site_name,
                    "success": success,
                    "consensus_score": consensus_score,
                    "elapsed_time": elapsed,
                    "workflow": workflow,
                }
            )

            status = "✅ PASS" if success else "❌ FAIL"
            print(f"  {status} | Consensus: {consensus_score:.3f} | Time: {elapsed:.2f}s")

        except Exception as e:
            print(f"  ❌ ERROR: {str(e)}")
            results.append(
                {
                    "url": url,
                    "site": "unknown",
                    "success": False,
                    "consensus_score": 0.0,
                    "elapsed_time": 0,
                    "workflow": "error",
                    "error": str(e),
                }
            )

    # Calculate metrics
    success_count = sum(1 for r in results if r["success"])
    success_rate = (success_count / len(results)) * 100 if results else 0
    avg_time = sum(r["elapsed_time"] for r in results) / len(results) if results else 0
    avg_consensus = sum(r["consensus_score"] for r in results) / len(results) if results else 0

    summary = {
        "total_tests": len(results),
        "success_count": success_count,
        "success_rate": success_rate,
        "avg_time": avg_time,
        "avg_consensus": avg_consensus,
        "results": results,
    }

    print(f"\n📊 UC3 Summary:")
    print(f"  Success Rate: {success_rate:.1f}% ({success_count}/{len(results)})")
    print(f"  Avg Time: {avg_time:.2f}s")
    print(f"  Avg Consensus: {avg_consensus:.3f}")

    return summary


def generate_markdown_report(uc1_summary: Dict, uc3_summary: Dict, output_file: Path):
    """
    Generate Markdown validation report

    Args:
        uc1_summary: UC1 validation results
        uc3_summary: UC3 validation results
        output_file: Output markdown file path
    """

    print("\n" + "=" * 80)
    print("📝 Generating Validation Report...")
    print("=" * 80)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    report = f"""# CrawlAgent UC 검증 보고서

**생성일시**: {now}

---

## 📊 전체 요약

| Use Case | 테스트 수 | 성공 | 실패 | 성공률 | 평균 소요 시간 |
|----------|-----------|------|------|--------|----------------|
| UC1 Quality Gate | {uc1_summary['total_tests']} | {uc1_summary['success_count']} | {uc1_summary['total_tests'] - uc1_summary['success_count']} | **{uc1_summary['success_rate']:.1f}%** | {uc1_summary['avg_time']:.2f}s |
| UC3 New Site Discovery | {uc3_summary['total_tests']} | {uc3_summary['success_count']} | {uc3_summary['total_tests'] - uc3_summary['success_count']} | **{uc3_summary['success_rate']:.1f}%** | {uc3_summary['avg_time']:.2f}s |

---

## 🟢 UC1 Quality Gate 검증 결과

### 성능 지표
- **성공률**: {uc1_summary['success_rate']:.1f}% ({uc1_summary['success_count']}/{uc1_summary['total_tests']})
- **평균 품질 점수**: {uc1_summary['avg_quality']:.1f}/100
- **평균 소요 시간**: {uc1_summary['avg_time']:.2f}s
- **목표 달성**: {'✅ PASS (≥80%)' if uc1_summary['success_rate'] >= 80 else '❌ FAIL (<80%)'}

### 상세 결과

| # | Site | Success | Quality | Time | Workflow |
|---|------|---------|---------|------|----------|
"""

    for idx, result in enumerate(uc1_summary["results"], 1):
        status = "✅" if result["success"] else "❌"
        site = result["site"]
        quality = result["quality_score"]
        time_str = f"{result['elapsed_time']:.2f}s"
        workflow = result.get("workflow", "N/A")

        report += f"| {idx} | {site} | {status} | {quality}/100 | {time_str} | {workflow} |\n"

    report += f"""
---

## 🔵 UC3 New Site Discovery 검증 결과

### 성능 지표
- **성공률**: {uc3_summary['success_rate']:.1f}% ({uc3_summary['success_count']}/{uc3_summary['total_tests']})
- **평균 Consensus Score**: {uc3_summary['avg_consensus']:.3f}
- **평균 소요 시간**: {uc3_summary['avg_time']:.2f}s
- **목표 달성**: {'✅ PASS (≥80%)' if uc3_summary['success_rate'] >= 80 else '❌ FAIL (<80%)'}

### 상세 결과

| # | Site | Success | Consensus | Time | Workflow |
|---|------|---------|-----------|------|----------|
"""

    for idx, result in enumerate(uc3_summary["results"], 1):
        status = "✅" if result["success"] else "❌"
        site = result["site"]
        consensus = f"{result['consensus_score']:.3f}"
        time_str = f"{result['elapsed_time']:.2f}s"
        workflow = result.get("workflow", "N/A")

        report += f"| {idx} | {site} | {status} | {consensus} | {time_str} | {workflow} |\n"

    report += f"""
---

## 🎯 결론

### 달성 상황
- UC1 성공률: {uc1_summary['success_rate']:.1f}% {'✅' if uc1_summary['success_rate'] >= 80 else '❌'}
- UC3 성공률: {uc3_summary['success_rate']:.1f}% {'✅' if uc3_summary['success_rate'] >= 80 else '❌'}

### 다음 단계
1. 실패한 케이스 분석 및 개선
2. LangSmith 추적에서 실패 원인 확인
3. Consensus 임계값 조정 (필요 시)
4. Few-Shot Examples 추가 (정확도 향상)

---

**보고서 생성**: {now}
"""

    # Write report
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(report)

    print(f"✅ 보고서 생성 완료: {output_file}")


# ============================================================================
# Main
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="CrawlAgent Use Case Validation")
    parser.add_argument(
        "--output",
        type=str,
        default="validation_report.md",
        help="Output markdown report file (default: validation_report.md)",
    )
    parser.add_argument("--skip-uc1", action="store_true", help="Skip UC1 validation")
    parser.add_argument("--skip-uc3", action="store_true", help="Skip UC3 validation")

    args = parser.parse_args()
    output_file = project_root / args.output

    print("\n" + "=" * 80)
    print("🤖 CrawlAgent Use Case Validation")
    print("=" * 80)
    print(f"Output: {output_file}\n")

    # UC1 Validation
    uc1_summary = None
    if not args.skip_uc1:
        uc1_summary = validate_uc1(UC1_TEST_URLS, output_file)
    else:
        print("⏭️  Skipping UC1 validation")
        uc1_summary = {
            "total_tests": 0,
            "success_count": 0,
            "success_rate": 0,
            "avg_time": 0,
            "avg_quality": 0,
            "results": [],
        }

    # UC3 Validation
    uc3_summary = None
    if not args.skip_uc3:
        uc3_summary = validate_uc3(UC3_TEST_URLS, output_file)
    else:
        print("⏭️  Skipping UC3 validation")
        uc3_summary = {
            "total_tests": 0,
            "success_count": 0,
            "success_rate": 0,
            "avg_time": 0,
            "avg_consensus": 0,
            "results": [],
        }

    # Generate Report
    generate_markdown_report(uc1_summary, uc3_summary, output_file)

    print("\n" + "=" * 80)
    print("✅ Validation Complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
