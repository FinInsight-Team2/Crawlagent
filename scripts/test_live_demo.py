"""
라이브 데모 시나리오 테스트 스크립트
Created: 2025-11-16

Purpose:
    실제 시연 전 Supervisor 라우팅 동작 검증
    - UC3: Donga Selector 없을 때 → UC3 트리거 확인
    - UC1: Donga Selector 있을 때 → UC1 통과 확인
    - UC2: Yonhap Selector 손상 → UC2 트리거 확인

Usage:
    poetry run python scripts/test_live_demo.py
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.storage.models import Selector
from src.utils.db_utils import get_db_session_no_commit

# 테스트 URL
TEST_URLS = {
    "donga": "https://www.donga.com/news/article/all/20231114/122212345/1",
    "yonhap": "https://www.yna.co.kr/view/AKR20231114000100001",
}


def test_uc3_trigger():
    """
    UC3 트리거 확인: Donga Selector가 없는지 확인

    Returns:
        bool: Selector가 없으면 True (UC3 트리거 예상)
    """
    logger.info("=" * 80)
    logger.info("UC3 Discovery 시나리오 검증")
    logger.info("=" * 80)

    with get_db_session_no_commit() as db:
        donga_selector = db.query(Selector).filter_by(site_name="donga").first()

        if donga_selector:
            logger.error("❌ 실패: Donga Selector가 DB에 존재합니다!")
            logger.info(f"   - title_selector: {donga_selector.title_selector}")
            logger.info(f"   - body_selector: {donga_selector.body_selector}")
            logger.info("   → UC3가 트리거되지 않을 것입니다.")
            logger.info("")
            logger.info("해결 방법:")
            logger.info("  poetry run python scripts/reset_selector_demo.py --uc3-demo")
            return False
        else:
            logger.success("✅ 성공: Donga Selector가 DB에 없습니다!")
            logger.info("   → Supervisor가 UC3 Discovery를 트리거할 것입니다.")
            logger.info("")
            logger.info("예상 동작:")
            logger.info("  1. Supervisor: Donga Selector 없음 감지")
            logger.info("  2. UC3 트리거: Claude + GPT-4o 2-Agent Consensus")
            logger.info("  3. Selector 자동 생성 → DB 저장")
            logger.info("  4. UC1 재시도 → 성공")
            return True


def test_uc2_trigger():
    """
    UC2 트리거 확인: Yonhap Selector가 손상되었는지 확인

    Returns:
        bool: Selector가 손상되었으면 True (UC2 트리거 예상)
    """
    logger.info("=" * 80)
    logger.info("UC2 Self-Healing 시나리오 검증")
    logger.info("=" * 80)

    with get_db_session_no_commit() as db:
        yonhap_selector = db.query(Selector).filter_by(site_name="yonhap").first()

        if not yonhap_selector:
            logger.error("❌ 실패: Yonhap Selector가 DB에 없습니다!")
            logger.info("   → UC2 시연을 할 수 없습니다.")
            return False

        # 손상된 Selector 확인 (demo용 wrong-selector 포함)
        if "wrong-selector" in yonhap_selector.body_selector:
            logger.success("✅ 성공: Yonhap Selector가 손상되었습니다!")
            logger.info(f"   - 손상된 body_selector: {yonhap_selector.body_selector}")
            logger.info("   → UC1 품질 검증 실패 → UC2 Self-Healing 트리거 예상")
            logger.info("")
            logger.info("예상 동작:")
            logger.info("  1. UC1: Quality Score < 80 (실패)")
            logger.info("  2. UC2 트리거: Claude Proposer + GPT-4o Validator")
            logger.info("  3. Selector 자동 수정 → DB 업데이트")
            logger.info("  4. UC1 재시도 → 성공")
            return True
        else:
            logger.warning("⚠️  Yonhap Selector가 정상 상태입니다.")
            logger.info(f"   - body_selector: {yonhap_selector.body_selector}")
            logger.info("   → UC2가 트리거되지 않을 것입니다.")
            logger.info("")
            logger.info("UC2 시연을 원하면:")
            logger.info("  poetry run python scripts/reset_selector_demo.py --uc2-demo")
            return False


def test_uc1_reuse():
    """
    UC1 Reuse 확인: Donga Selector가 복원되었는지 확인

    Returns:
        bool: Selector가 있으면 True (UC1 통과 예상)
    """
    logger.info("=" * 80)
    logger.info("UC1 Reuse 시나리오 검증")
    logger.info("=" * 80)

    with get_db_session_no_commit() as db:
        donga_selector = db.query(Selector).filter_by(site_name="donga").first()

        if donga_selector:
            logger.success("✅ 성공: Donga Selector가 DB에 존재합니다!")
            logger.info(f"   - title_selector: {donga_selector.title_selector}")
            logger.info(f"   - body_selector: {donga_selector.body_selector}")
            logger.info(f"   - 성공 횟수: {donga_selector.success_count}")
            logger.info("   → UC1 Quality Gate 통과 예상 (LLM 호출 없음, 비용 $0)")
            logger.info("")
            logger.info("예상 동작:")
            logger.info("  1. Supervisor: Donga Selector 존재 확인")
            logger.info("  2. UC1 Quality Gate 통과")
            logger.info("  3. Scrapy 크롤링 (LLM 호출 없음)")
            logger.info("  4. Quality Score ≥ 80 → 성공")
            logger.info("  5. 비용: $0, 처리 시간: ~0.5초")
            return True
        else:
            logger.error("❌ 실패: Donga Selector가 DB에 없습니다!")
            logger.info("   → UC1 대신 UC3가 트리거될 것입니다.")
            logger.info("")
            logger.info("UC1 시연을 원하면 먼저 UC3를 실행하세요:")
            logger.info("  1. poetry run python scripts/reset_selector_demo.py --uc3-demo")
            logger.info("  2. Gradio UI에서 Donga URL 크롤링 (UC3 트리거)")
            logger.info("  3. Selector 저장 후 다시 같은 URL 크롤링 (UC1 통과)")
            return False


def main():
    logger.info("🚀 라이브 데모 시나리오 검증 시작\n")

    results = {
        "uc3_ready": test_uc3_trigger(),
        "uc2_ready": test_uc2_trigger(),
        "uc1_ready": test_uc1_reuse(),
    }

    logger.info("")
    logger.info("=" * 80)
    logger.info("최종 검증 결과")
    logger.info("=" * 80)
    logger.info(f"UC3 Discovery 시나리오: {'✅ 준비 완료' if results['uc3_ready'] else '❌ 준비 필요'}")
    logger.info(f"UC2 Self-Healing 시나리오: {'✅ 준비 완료' if results['uc2_ready'] else '⚠️  정상 상태 (시연 불가)'}")
    logger.info(f"UC1 Reuse 시나리오: {'✅ 준비 완료' if results['uc1_ready'] else '❌ UC3 먼저 실행 필요'}")
    logger.info("=" * 80)

    if results["uc3_ready"] and not results["uc1_ready"]:
        logger.info("\n✅ 시연 시나리오 순서:")
        logger.info("  1. UC3 Discovery (Donga) → Selector 생성")
        logger.info("  2. UC1 Reuse (Donga 재시도) → $0 비용 증명")
        logger.info("  3. UC2 Self-Healing (준비 필요 시 --uc2-demo 실행)")

    logger.success("\n🎉 검증 완료!")


if __name__ == "__main__":
    main()
