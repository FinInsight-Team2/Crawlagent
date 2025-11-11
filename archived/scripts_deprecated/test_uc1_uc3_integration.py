#!/usr/bin/env python3
"""
Phase 3 검증: UC1→UC2/UC3 자동 연계 테스트

UC1 워크플로우가 Selector 존재 여부에 따라 자동으로 UC2/UC3를 트리거하는지 검증

시나리오:
1. UC2 트리거: Selector 존재 + 품질 실패 → UC2 Self-Healing
2. UC3 트리거: Selector 없음 → UC3 New Site Discovery

Usage:
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/test_uc1_uc3_integration.py
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.workflow.uc1_validation import create_uc1_validation_agent, ValidationState
from src.storage.database import get_db
from src.storage.models import Selector
from loguru import logger
import requests


def print_section(title: str):
    """섹션 구분선 출력"""
    print("\n" + "=" * 80)
    print(f"📋 {title}")
    print("=" * 80 + "\n")


def test_scenario_1_uc2_trigger():
    """
    시나리오 1: UC2 Self-Healing 트리거

    조건:
    - Selector가 DB에 존재 (yonhap)
    - 품질 검증 실패 (일부러 잘못된 데이터 전달)

    기대 결과:
    - heal_or_discover 노드가 UC2를 트리거
    - GPT + Gemini 합의 시도
    """
    print_section("시나리오 1: UC2 Self-Healing 트리거")

    # 1. Selector 존재 확인
    db = next(get_db())
    try:
        selector = db.query(Selector).filter_by(site_name="yonhap").first()
        if not selector:
            logger.error("❌ yonhap Selector가 DB에 없습니다. 먼저 생성해주세요.")
            return
        logger.info(f"✅ Selector 존재 확인: site_name=yonhap")
        logger.info(f"   - title_selector: {selector.title_selector}")
        logger.info(f"   - body_selector: {selector.body_selector}")
        logger.info(f"   - date_selector: {selector.date_selector}")
    finally:
        db.close()

    # 2. UC1 Graph 빌드
    logger.info("\n🔧 UC1 Graph 빌드 중...")
    uc1_graph = create_uc1_validation_agent()

    # 3. 테스트 State (일부러 품질이 낮은 데이터)
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030"

    initial_state: ValidationState = {
        "url": test_url,
        "site_name": "yonhap",
        "title": "짧은제목",  # 너무 짧아서 품질 실패
        "body": "짧은본문",    # 너무 짧아서 품질 실패
        "date": None,         # 날짜 없음
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
        "uc2_triggered": False,
        "uc2_success": False
    }

    logger.info("\n📊 초기 State:")
    logger.info(f"   - URL: {test_url}")
    logger.info(f"   - site_name: yonhap")
    logger.info(f"   - title: {initial_state['title']} (len={len(initial_state['title'])})")
    logger.info(f"   - body: {initial_state['body']} (len={len(initial_state['body'])})")
    logger.info(f"   - date: {initial_state['date']}")

    # 4. UC1 실행
    logger.info("\n🚀 UC1 워크플로우 실행 중...")
    logger.info("   예상: extract_fields → calculate_quality → decide_action → heal_or_discover (UC2)")

    try:
        result = uc1_graph.invoke(initial_state)

        # 5. 결과 분석
        print_section("시나리오 1: 결과 분석")

        logger.info(f"✅ UC1 워크플로우 완료")
        logger.info(f"\n📊 최종 State:")
        logger.info(f"   - quality_score: {result.get('quality_score')}")
        logger.info(f"   - missing_fields: {result.get('missing_fields')}")
        logger.info(f"   - next_action: {result.get('next_action')}")
        logger.info(f"   - uc2_triggered: {result.get('uc2_triggered')}")
        logger.info(f"   - uc2_success: {result.get('uc2_success')}")

        # 검증
        if result.get("uc2_triggered"):
            logger.info("\n✅ UC2 트리거 성공!")
            if result.get("uc2_success"):
                logger.info("   - UC2 합의 성공 → Selector 업데이트됨")
            else:
                logger.info("   - UC2 합의 실패 → 이전 Selector 유지 (완전 자동화)")
        else:
            logger.warning("\n⚠️ UC2가 트리거되지 않았습니다.")

    except Exception as e:
        logger.error(f"\n❌ 시나리오 1 실패: {e}")
        import traceback
        traceback.print_exc()


def test_scenario_2_uc3_trigger():
    """
    시나리오 2: UC3 New Site Discovery 트리거

    조건:
    - Selector가 DB에 없음 (test_newsite)
    - 실제 HTML 다운로드

    기대 결과:
    - heal_or_discover 노드가 UC3를 트리거
    - Claude Sonnet이 Selector 자동 생성
    """
    print_section("시나리오 2: UC3 New Site Discovery 트리거")

    # 1. Selector 없음 확인 (테스트용 site_name)
    test_site_name = "test_newsite"

    db = next(get_db())
    try:
        selector = db.query(Selector).filter_by(site_name=test_site_name).first()
        if selector:
            logger.warning(f"⚠️ {test_site_name} Selector가 이미 존재합니다. 삭제 후 테스트...")
            db.delete(selector)
            db.commit()
            logger.info(f"✅ 기존 Selector 삭제 완료")

        logger.info(f"✅ Selector 없음 확인: site_name={test_site_name}")
    finally:
        db.close()

    # 2. UC1 Graph 빌드
    logger.info("\n🔧 UC1 Graph 빌드 중...")
    uc1_graph = create_uc1_validation_agent()

    # 3. 실제 HTML 다운로드 (연합뉴스 기사)
    test_url = "https://www.yna.co.kr/view/AKR20251108033551030"

    logger.info(f"\n📥 HTML 다운로드 중: {test_url}")
    try:
        response = requests.get(test_url, timeout=10)
        html_content = response.text
        logger.info(f"✅ HTML 다운로드 완료 (길이: {len(html_content)})")
    except Exception as e:
        logger.error(f"❌ HTML 다운로드 실패: {e}")
        return

    # 4. 테스트 State (신규 사이트이므로 추출 데이터 없음)
    initial_state: ValidationState = {
        "url": test_url,
        "site_name": test_site_name,
        "title": None,  # Selector 없으므로 추출 불가
        "body": None,   # Selector 없으므로 추출 불가
        "date": None,   # Selector 없으므로 추출 불가
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "new_site",
        "uc2_triggered": False,
        "uc2_success": False,
        "uc3_triggered": False,
        "uc3_success": False
    }

    logger.info("\n📊 초기 State:")
    logger.info(f"   - URL: {test_url}")
    logger.info(f"   - site_name: {test_site_name} (신규 사이트)")
    logger.info(f"   - title: {initial_state['title']}")
    logger.info(f"   - body: {initial_state['body']}")
    logger.info(f"   - date: {initial_state['date']}")

    # 5. UC1 실행
    logger.info("\n🚀 UC1 워크플로우 실행 중...")
    logger.info("   예상: extract_fields → calculate_quality → decide_action → heal_or_discover (UC3)")

    try:
        result = uc1_graph.invoke(initial_state)

        # 6. 결과 분석
        print_section("시나리오 2: 결과 분석")

        logger.info(f"✅ UC1 워크플로우 완료")
        logger.info(f"\n📊 최종 State:")
        logger.info(f"   - quality_score: {result.get('quality_score')}")
        logger.info(f"   - missing_fields: {result.get('missing_fields')}")
        logger.info(f"   - next_action: {result.get('next_action')}")
        logger.info(f"   - uc3_triggered: {result.get('uc3_triggered')}")
        logger.info(f"   - uc3_success: {result.get('uc3_success')}")

        # 검증
        if result.get("uc3_triggered"):
            logger.info("\n✅ UC3 트리거 성공!")
            if result.get("uc3_success"):
                logger.info("   - Claude Sonnet이 Selector 생성 성공 → DB 저장됨")

                # DB에서 생성된 Selector 확인
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
                logger.info("   - Claude Sonnet Selector 생성 실패 (완전 자동화, 에러 로깅)")
        else:
            logger.warning("\n⚠️ UC3가 트리거되지 않았습니다.")

    except Exception as e:
        logger.error(f"\n❌ 시나리오 2 실패: {e}")
        import traceback
        traceback.print_exc()


def main():
    """메인 함수"""
    print("\n" + "=" * 80)
    print("🤖 Phase 3 검증: UC1→UC2/UC3 자동 연계 테스트")
    print("=" * 80 + "\n")

    # 시나리오 선택
    print("실행할 시나리오를 선택하세요:")
    print("1. UC2 Self-Healing 트리거 (Selector 존재)")
    print("2. UC3 New Site Discovery 트리거 (Selector 없음)")
    print("3. 둘 다 실행")

    choice = input("\n선택 (1/2/3): ").strip()

    if choice == "1":
        test_scenario_1_uc2_trigger()
    elif choice == "2":
        test_scenario_2_uc3_trigger()
    elif choice == "3":
        test_scenario_1_uc2_trigger()
        print("\n\n")
        test_scenario_2_uc3_trigger()
    else:
        print("❌ 잘못된 선택입니다.")
        sys.exit(1)

    print("\n✅ 테스트 완료!")


if __name__ == "__main__":
    main()
