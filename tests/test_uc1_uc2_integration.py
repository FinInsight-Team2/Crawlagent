"""
UC1 → UC2 자동 연계 통합 테스트
Created: 2025-11-08

테스트 시나리오:
1. UC1 품질 검증 실패 (score < 80)
2. UC2 자동 트리거 (heal_with_uc2 노드)
3. GPT + Gemini 합의
4. Selector 업데이트
5. DecisionLog 저장

실행 방법:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_uc1_uc2_integration.py
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from src.workflow.uc1_validation import create_uc1_validation_agent
from src.storage.database import get_db
from src.storage.models import DecisionLog, Selector
from loguru import logger

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_uc1_uc2_integration():
    """
    UC1 → UC2 자동 연계 테스트

    시나리오:
        1. 잘못된 Selector로 크롤링 (title=None)
        2. quality_score < 80 → UC2 트리거
        3. UC2가 새로운 Selector 제안
        4. Selector 업데이트 확인
        5. DecisionLog 저장 확인
    """
    logger.info("="*60)
    logger.info("UC1 → UC2 자동 연계 통합 테스트")
    logger.info("="*60)

    # 1. Graph 생성
    logger.info("\n[Step 1] UC1 Validation Agent Graph 생성...")
    graph = create_uc1_validation_agent()
    logger.info("✅ Graph 생성 완료")

    # 2. 테스트 입력 데이터 (품질 실패 케이스)
    logger.info("\n[Step 2] 테스트 입력 데이터 준비 (title=None, body=짧음)...")

    test_url = "https://www.yna.co.kr/view/AKR20251108000001001"

    inputs = {
        "url": test_url,
        "site_name": "yonhap",
        "title": None,  # Selector 실패 시뮬레이션
        "body": "짧은 본문",  # 500자 미만
        "date": "2025-11-08",
        "quality_score": 0,  # 초기값
        "missing_fields": [],  # 초기값
        "next_action": "save",  # 초기값 (덮어써짐)
        "uc2_triggered": False,
        "uc2_success": False
    }

    logger.info(f"  URL: {test_url}")
    logger.info(f"  Title: {inputs['title']}")
    logger.info(f"  Body: {inputs['body']}")
    logger.info(f"  → 예상 quality_score: 20 (Title 0 + Body 30 + Date 10 + URL 10) = 50 < 80")
    logger.info(f"  → 예상 next_action: 'heal' (UC2 트리거)")

    # 3. UC1 실행 (UC2 자동 연계 포함)
    logger.info("\n[Step 3] UC1 Validation Agent 실행 (UC2 자동 연계)...")

    try:
        result = graph.invoke(inputs)

        logger.info(f"\n[Step 4] 실행 결과:")
        logger.info(f"  Quality Score: {result.get('quality_score')}")
        logger.info(f"  Missing Fields: {result.get('missing_fields')}")
        logger.info(f"  Next Action: {result.get('next_action')}")
        logger.info(f"  UC2 Triggered: {result.get('uc2_triggered')}")
        logger.info(f"  UC2 Success: {result.get('uc2_success')}")

        # 4. DecisionLog 확인
        logger.info("\n[Step 5] DecisionLog 확인...")

        db = next(get_db())
        try:
            decision_log = db.query(DecisionLog).filter_by(
                url=test_url
            ).order_by(DecisionLog.created_at.desc()).first()

            if decision_log:
                logger.info(f"  ✅ DecisionLog 저장됨 (ID={decision_log.id})")
                logger.info(f"     Consensus: {decision_log.consensus_reached}")
                logger.info(f"     Retry Count: {decision_log.retry_count}")
                logger.info(f"     GPT Proposal: {decision_log.gpt_analysis.get('title_selector') if decision_log.gpt_analysis else 'N/A'}")
                logger.info(f"     Gemini Validation: {decision_log.gemini_validation.get('is_valid') if decision_log.gemini_validation else 'N/A'}")
            else:
                logger.warning(f"  ⚠️ DecisionLog가 생성되지 않았습니다")

        finally:
            db.close()

        # 5. Selector 업데이트 확인 (UC2 성공 시)
        if result.get('uc2_success'):
            logger.info("\n[Step 6] Selector 업데이트 확인...")

            db = next(get_db())
            try:
                selector = db.query(Selector).filter_by(site_name="yonhap").first()

                if selector:
                    logger.info(f"  ✅ Selector 업데이트됨:")
                    logger.info(f"     Title Selector: {selector.title_selector}")
                    logger.info(f"     Body Selector: {selector.body_selector}")
                    logger.info(f"     Date Selector: {selector.date_selector}")
                    logger.info(f"     Updated At: {selector.updated_at}")
                else:
                    logger.warning(f"  ⚠️ Selector를 찾을 수 없습니다")

            finally:
                db.close()

        logger.info("\n" + "="*60)
        logger.info("✅ 테스트 완료!")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        logger.error("   .env 파일에 OPENAI_API_KEY를 설정하세요")
        sys.exit(1)

    if not os.getenv("GEMINI_API_KEY"):
        logger.error("❌ GEMINI_API_KEY 환경변수가 설정되지 않았습니다")
        logger.error("   .env 파일에 GEMINI_API_KEY를 설정하세요")
        sys.exit(1)

    # 테스트 실행
    test_uc1_uc2_integration()
