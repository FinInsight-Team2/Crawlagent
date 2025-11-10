#!/usr/bin/env python3
"""
Master Graph 독립 검증 스크립트

목적: 기존 코드를 건드리지 않고 Master Graph 단독 테스트 및 LangSmith 추적 확인

3가지 시나리오:
1. UC1 성공 (정상 크롤링)
2. UC1 실패 → UC2 자동 트리거
3. UC3 신규 사이트 Discovery

Usage:
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/test_master_graph_standalone.py

작성일: 2025-11-10
Phase A: Master Graph 독립 검증
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


def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 80)
    print(f"📋 {title}")
    print("=" * 80 + "\n")


def print_langsmith_info():
    """LangSmith 트레이싱 정보 출력"""
    print_section("LangSmith 트레이싱 확인")

    langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
    langchain_tracing = os.getenv("LANGCHAIN_TRACING_V2")
    langchain_project = os.getenv("LANGCHAIN_PROJECT")

    if langchain_tracing == "true" and langchain_api_key:
        logger.info("✅ LangSmith 트레이싱 활성화됨")
        logger.info(f"   Project: {langchain_project}")
        logger.info(f"   URL: https://smith.langchain.com/o/default/projects/p/{langchain_project}")
        logger.info("")
        logger.info("🔍 Trace를 확인하려면 위 URL을 방문하세요.")
        logger.info("   각 시나리오 실행 후 Trace ID가 로그에 표시됩니다.")
    else:
        logger.warning("⚠️ LangSmith 트레이싱이 비활성화되어 있습니다")
        logger.warning("   .env 파일에서 LANGCHAIN_TRACING_V2=true로 설정하세요")


def test_scenario_1_uc1_success():
    """
    시나리오 1: UC1 성공 (정상 크롤링)

    예상 흐름:
        START → Supervisor → UC1 Validation (품질 통과) → Supervisor → END

    예상 결과:
        - quality_passed: True
        - quality_score >= 80
        - workflow_history에 UC1만 표시
    """
    print_section("시나리오 1: UC1 성공 (정상 크롤링)")

    # 1. Master Graph 빌드
    logger.info("🔧 Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 2. 실제 HTML 다운로드 (연합뉴스 실제 기사)
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030"

    logger.info(f"📥 HTML 다운로드 중: {test_url}")
    try:
        response = requests.get(test_url, timeout=10)
        html_content = response.text
        logger.info(f"✅ HTML 다운로드 완료 (길이: {len(html_content)})")
    except Exception as e:
        logger.error(f"❌ HTML 다운로드 실패: {e}")
        return

    # 3. 초기 State
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

    logger.info("\n📊 초기 State:")
    logger.info(f"   URL: {test_url}")
    logger.info(f"   Site: yonhap")
    logger.info(f"   Failure Count: 0")

    # 4. Master Graph 실행
    logger.info("\n🚀 Master Graph 실행 중...")
    logger.info("   예상 경로: Supervisor → UC1 (성공) → Supervisor → END")

    try:
        result = master_app.invoke(initial_state)

        # 5. 결과 분석
        print_section("시나리오 1: 결과 분석")

        logger.info("✅ Master Graph 실행 완료")
        logger.info(f"\n📊 Workflow History:")
        for i, step in enumerate(result.get("workflow_history", []), 1):
            logger.info(f"   {i}. {step}")

        logger.info(f"\n📈 UC1 결과:")
        uc1_result = result.get("uc1_validation_result", {})
        if uc1_result:
            logger.info(f"   - quality_passed: {uc1_result.get('quality_passed')}")
            logger.info(f"   - quality_score: {uc1_result.get('quality_score')}")
            logger.info(f"   - next_action: {uc1_result.get('next_action')}")

            if uc1_result.get("quality_passed"):
                logger.info("\n✅ 시나리오 1 성공: UC1 품질 검증 통과!")
            else:
                logger.warning("\n⚠️ 시나리오 1 예상 밖: UC1이 실패했습니다")
        else:
            logger.error("\n❌ UC1 결과 없음")

        logger.info(f"\n📌 최종 액션: {result.get('next_action')}")

    except Exception as e:
        logger.error(f"\n❌ 시나리오 1 실패: {e}")
        import traceback
        traceback.print_exc()


def test_scenario_2_uc1_failure_uc2():
    """
    시나리오 2: UC1 실패 → UC2 Self-Healing 트리거

    예상 흐름:
        START → Supervisor → UC1 Validation (품질 실패) → Supervisor → END
        (주의: UC1 내부적으로 UC2를 트리거하므로 Master Graph 레벨에서는 UC2 Node 미실행)

    예상 결과:
        - quality_passed: False
        - quality_score < 80
        - UC1이 내부적으로 UC2/UC3 호출 (uc2_triggered 또는 uc3_triggered 플래그 확인)
    """
    print_section("시나리오 2: UC1 실패 → UC2 자동 트리거")

    # 1. Master Graph 빌드
    logger.info("🔧 Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 2. 실제 HTML 다운로드
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030"

    logger.info(f"📥 HTML 다운로드 중: {test_url}")
    try:
        response = requests.get(test_url, timeout=10)
        html_content = response.text
        logger.info(f"✅ HTML 다운로드 완료")
    except Exception as e:
        logger.error(f"❌ HTML 다운로드 실패: {e}")
        return

    # 3. 초기 State (failure_count=3으로 설정하지만, Master Graph에서는 사용 안 됨)
    # 주의: 현재 구조에서는 UC1이 내부적으로 UC2를 호출하므로
    # Master Graph 레벨에서 UC2 Node를 직접 트리거하지 않습니다.
    # 따라서 이 시나리오는 UC1 내부 로직을 확인하는 용도입니다.

    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": "yonhap",
        "html_content": html_content,
        "current_uc": None,
        "next_action": None,
        "failure_count": 0,  # UC1 내부에서 품질 체크
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": []
    }

    logger.info("\n📊 초기 State:")
    logger.info(f"   URL: {test_url}")
    logger.info(f"   Site: yonhap")
    logger.info(f"   Note: UC1이 품질 실패를 감지하면 내부적으로 UC2 호출")

    # 4. Master Graph 실행
    logger.info("\n🚀 Master Graph 실행 중...")
    logger.info("   예상 경로: Supervisor → UC1 (내부에서 UC2 호출 가능) → Supervisor → END")

    try:
        result = master_app.invoke(initial_state)

        # 5. 결과 분석
        print_section("시나리오 2: 결과 분석")

        logger.info("✅ Master Graph 실행 완료")
        logger.info(f"\n📊 Workflow History:")
        for i, step in enumerate(result.get("workflow_history", []), 1):
            logger.info(f"   {i}. {step}")

        logger.info(f"\n📈 UC1 결과:")
        uc1_result = result.get("uc1_validation_result", {})
        if uc1_result:
            logger.info(f"   - quality_passed: {uc1_result.get('quality_passed')}")
            logger.info(f"   - quality_score: {uc1_result.get('quality_score')}")
            logger.info(f"   - next_action: {uc1_result.get('next_action')}")

        logger.info(f"\n📌 최종 액션: {result.get('next_action')}")
        logger.info("\n💡 Note: 현재 구조에서는 UC1이 내부적으로 UC2/UC3를 호출합니다.")
        logger.info("   Master Graph 레벨에서 UC2 Node가 직접 실행되지 않을 수 있습니다.")

    except Exception as e:
        logger.error(f"\n❌ 시나리오 2 실패: {e}")
        import traceback
        traceback.print_exc()


def test_scenario_3_uc3_new_site():
    """
    시나리오 3: UC3 New Site Discovery

    예상 흐름:
        START → Supervisor → UC3 New Site Discovery → Supervisor → END

    예상 결과:
        - uc3_discovery_result에 결과 포함
        - Selector 생성 성공 또는 실패
    """
    print_section("시나리오 3: UC3 New Site Discovery")

    # 1. Master Graph 빌드
    logger.info("🔧 Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 2. 테스트용 신규 사이트 (실제로는 연합뉴스지만 site_name을 다르게 설정)
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030"
    test_site_name = "test_newsite_standalone"

    logger.info(f"📥 HTML 다운로드 중: {test_url}")
    logger.info(f"   (site_name을 '{test_site_name}'로 설정하여 신규 사이트로 시뮬레이션)")

    try:
        response = requests.get(test_url, timeout=10)
        html_content = response.text
        logger.info(f"✅ HTML 다운로드 완료")
    except Exception as e:
        logger.error(f"❌ HTML 다운로드 실패: {e}")
        return

    # 3. Selector 없음을 확인하고 삭제 (테스트 준비)
    from src.storage.database import get_db
    from src.storage.models import Selector

    db = next(get_db())
    try:
        selector = db.query(Selector).filter_by(site_name=test_site_name).first()
        if selector:
            logger.info(f"⚠️ 기존 Selector 발견 → 삭제 중...")
            db.delete(selector)
            db.commit()
            logger.info(f"✅ 기존 Selector 삭제 완료")
    finally:
        db.close()

    # 4. 초기 State (next_action="uc3"으로 명시적 설정)
    initial_state: MasterCrawlState = {
        "url": test_url,
        "site_name": test_site_name,
        "html_content": html_content,
        "current_uc": None,
        "next_action": "uc3",  # UC3 명시적 트리거
        "failure_count": 0,
        "uc1_validation_result": None,
        "uc2_consensus_result": None,
        "uc3_discovery_result": None,
        "final_result": None,
        "error_message": None,
        "workflow_history": []
    }

    logger.info("\n📊 초기 State:")
    logger.info(f"   URL: {test_url}")
    logger.info(f"   Site: {test_site_name} (신규)")
    logger.info(f"   next_action: uc3 (명시적 트리거)")

    # 5. Master Graph 실행
    logger.info("\n🚀 Master Graph 실행 중...")
    logger.info("   예상 경로: Supervisor → UC3 New Site → Supervisor → END")

    try:
        result = master_app.invoke(initial_state)

        # 6. 결과 분석
        print_section("시나리오 3: 결과 분석")

        logger.info("✅ Master Graph 실행 완료")
        logger.info(f"\n📊 Workflow History:")
        for i, step in enumerate(result.get("workflow_history", []), 1):
            logger.info(f"   {i}. {step}")

        logger.info(f"\n📈 UC3 결과:")
        uc3_result = result.get("uc3_discovery_result", {})
        if uc3_result:
            logger.info(f"   - selectors_discovered: {bool(uc3_result.get('selectors_discovered'))}")
            logger.info(f"   - confidence: {uc3_result.get('confidence', 0):.2f}")

            if uc3_result.get("selectors_discovered"):
                logger.info("\n✅ 시나리오 3 성공: UC3가 Selector 생성 완료!")

                # DB에서 확인
                db = next(get_db())
                try:
                    selector = db.query(Selector).filter_by(site_name=test_site_name).first()
                    if selector:
                        logger.info(f"\n📋 생성된 Selector:")
                        logger.info(f"   - title_selector: {selector.title_selector}")
                        logger.info(f"   - body_selector: {selector.body_selector}")
                        logger.info(f"   - date_selector: {selector.date_selector}")
                        logger.info(f"   - site_type: {selector.site_type}")
                finally:
                    db.close()
            else:
                logger.warning("\n⚠️ UC3 Selector 생성 실패")
        else:
            logger.error("\n❌ UC3 결과 없음")

        logger.info(f"\n📌 최종 액션: {result.get('next_action')}")

    except Exception as e:
        logger.error(f"\n❌ 시나리오 3 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    print("\n" + "=" * 80)
    print("🤖 Master Graph 독립 검증 (Phase A)")
    print("=" * 80 + "\n")

    # LangSmith 정보 출력
    print_langsmith_info()

    # 시나리오 선택
    print_section("시나리오 선택")
    print("실행할 시나리오를 선택하세요:")
    print("1. UC1 성공 (정상 크롤링)")
    print("2. UC1 실패 → UC2 자동 트리거")
    print("3. UC3 신규 사이트 Discovery")
    print("4. 모두 실행")

    choice = input("\n선택 (1/2/3/4): ").strip()

    if choice == "1":
        test_scenario_1_uc1_success()
    elif choice == "2":
        test_scenario_2_uc1_failure_uc2()
    elif choice == "3":
        test_scenario_3_uc3_new_site()
    elif choice == "4":
        test_scenario_1_uc1_success()
        print("\n\n")
        test_scenario_2_uc1_failure_uc2()
        print("\n\n")
        test_scenario_3_uc3_new_site()
    else:
        print("❌ 잘못된 선택입니다.")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("✅ Master Graph 독립 검증 완료!")
    print("=" * 80)
    print("\n💡 다음 단계:")
    print("   1. LangSmith에서 Trace 확인")
    print("   2. 각 UC의 State 변화 추적")
    print("   3. LLM 호출 여부 및 Response 확인")
    print("")


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    main()
