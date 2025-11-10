#!/usr/bin/env python3
"""
Master Workflow 테스트 스크립트

LangGraph Master Graph를 실행하고 결과를 시각화합니다.

Usage:
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/test_master_workflow.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState
from loguru import logger
import requests
import json


def visualize_workflow_history(history: list[str]):
    """워크플로우 히스토리를 보기 좋게 출력"""
    print("\n" + "=" * 80)
    print("📊 워크플로우 실행 경로")
    print("=" * 80)

    for i, step in enumerate(history, 1):
        print(f"{i:2d}. {step}")

    print("=" * 80 + "\n")


def print_state_summary(state: MasterCrawlState):
    """State 요약 출력"""
    print("\n" + "=" * 80)
    print("📋 최종 State 요약")
    print("=" * 80)

    print(f"URL: {state['url']}")
    print(f"Site Name: {state['site_name']}")
    print(f"Current UC: {state.get('current_uc')}")
    print(f"Next Action: {state.get('next_action')}")
    print(f"Failure Count: {state.get('failure_count', 0)}")

    print("\n--- UC1 결과 ---")
    uc1_result = state.get('uc1_validation_result')
    if uc1_result:
        print(f"Quality Passed: {uc1_result.get('quality_passed')}")
        if uc1_result.get('error_message'):
            print(f"Error: {uc1_result.get('error_message')}")
    else:
        print("UC1 실행되지 않음")

    print("\n--- UC2 결과 ---")
    uc2_result = state.get('uc2_consensus_result')
    if uc2_result:
        print(f"Consensus Reached: {uc2_result.get('consensus_reached')}")
        print(f"Consensus Score: {uc2_result.get('consensus_score')}")
        if uc2_result.get('error_message'):
            print(f"Error: {uc2_result.get('error_message')}")
    else:
        print("UC2 실행되지 않음")

    print("\n--- UC3 결과 ---")
    uc3_result = state.get('uc3_discovery_result')
    if uc3_result:
        print(f"Selectors Discovered: {bool(uc3_result.get('selectors_discovered'))}")
        print(f"Confidence: {uc3_result.get('confidence')}")
        if uc3_result.get('error_message'):
            print(f"Error: {uc3_result.get('error_message')}")
    else:
        print("UC3 실행되지 않음")

    if state.get('error_message'):
        print(f"\n❌ 최종 에러: {state['error_message']}")

    print("=" * 80 + "\n")


def test_master_graph_uc1_success():
    """
    시나리오 1: UC1 성공 (정상 크롤링)

    START → supervisor → uc1_validation (성공) → supervisor → END
    """
    print("\n" + "🎯" * 40)
    print("시나리오 1: UC1 성공 (정상 크롤링)")
    print("🎯" * 40 + "\n")

    # Master Graph 빌드
    logger.info("Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 테스트 URL (실제 HTML 필요) - 연합뉴스 실제 기사
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030?section=economy/all"

    logger.info(f"HTML 가져오는 중: {test_url}")
    response = requests.get(test_url, timeout=10)
    html_content = response.text

    # 초기 State
    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "yonhap",
        "html_content": html_content,
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": []
    }

    # Master Graph 실행
    logger.info("🚀 Master Graph 실행 중...")
    final_state = master_app.invoke(initial_state)

    # 결과 출력
    visualize_workflow_history(final_state.get('workflow_history', []))
    print_state_summary(final_state)

    return final_state


def test_master_graph_uc1_failure():
    """
    시나리오 2: UC1 실패 → UC2 트리거

    START → supervisor → uc1_validation (실패) → supervisor → uc2_self_heal → ...
    """
    print("\n" + "🎯" * 40)
    print("시나리오 2: UC1 3회 실패 → UC2 Self-Healing 트리거")
    print("🎯" * 40 + "\n")

    # Master Graph 빌드
    logger.info("Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 테스트 URL - 연합뉴스 실제 기사
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030?section=economy/all"

    logger.info(f"HTML 가져오는 중: {test_url}")
    response = requests.get(test_url, timeout=10)
    html_content = response.text

    # 초기 State (failure_count=3으로 UC2 강제 트리거)
    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "yonhap",
        "html_content": html_content,
        "current_uc": None,
        "next_action": None,
        "failure_count": 3,  # 3회 실패로 설정
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": []
    }

    # Master Graph 실행
    logger.info("🚀 Master Graph 실행 중...")
    final_state = master_app.invoke(initial_state)

    # 결과 출력
    visualize_workflow_history(final_state.get('workflow_history', []))
    print_state_summary(final_state)

    return final_state


def main():
    """메인 함수"""
    print("\n" + "=" * 80)
    print("🤖 CrawlAgent - Master Workflow 테스트")
    print("=" * 80 + "\n")

    # 시나리오 선택
    print("실행할 시나리오를 선택하세요:")
    print("1. UC1 성공 (정상 크롤링)")
    print("2. UC1 실패 → UC2 Self-Healing 트리거")
    print("3. 둘 다 실행")

    choice = input("\n선택 (1/2/3): ").strip()

    if choice == "1":
        test_master_graph_uc1_success()
    elif choice == "2":
        test_master_graph_uc1_failure()
    elif choice == "3":
        test_master_graph_uc1_success()
        print("\n\n")
        test_master_graph_uc1_failure()
    else:
        print("❌ 잘못된 선택입니다.")
        sys.exit(1)

    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()
