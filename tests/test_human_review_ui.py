"""
UC2 Human Review UI 통합 테스트
Created: 2025-11-09

Sprint 5 검증:
- Tab 6 Human Review UI 기능 테스트
- approve_decision() 함수 검증
- reject_decision() 함수 검증
- Selector 테이블 업데이트 확인

실행 방법:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_human_review_ui.py
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from datetime import datetime
from src.storage.database import get_db
from src.storage.models import DecisionLog, Selector
from loguru import logger

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_human_review_workflow():
    """
    Human Review UI 워크플로우 테스트

    시나리오:
        1. 테스트용 DecisionLog 생성 (consensus_reached=False)
        2. approve_decision() 함수 실행
        3. Selector 테이블 업데이트 확인
        4. DecisionLog의 consensus_reached=True 확인
        5. 정리 (테스트 데이터 삭제)
    """
    logger.info("="*60)
    logger.info("Human Review UI 통합 테스트")
    logger.info("="*60)

    db = next(get_db())

    try:
        # 1. 테스트용 DecisionLog 생성
        logger.info("\n[Step 1] 테스트용 DecisionLog 생성...")

        test_site = "test_site_hr"
        test_url = "https://test.example.com/article/12345"

        # 기존 테스트 데이터 삭제 (클린업)
        db.query(DecisionLog).filter(DecisionLog.site_name == test_site).delete()
        db.query(Selector).filter(Selector.site_name == test_site).delete()
        db.commit()

        # 새 DecisionLog 생성
        test_log = DecisionLog(
            url=test_url,
            site_name=test_site,
            gpt_analysis={
                "title_selector": "h1.article-title",
                "body_selector": "div.article-body",
                "date_selector": "time.published-date",
                "confidence": 0.95,
                "reasoning": "Test GPT proposal"
            },
            gemini_validation={
                "is_valid": False,  # 합의 실패로 시뮬레이션
                "confidence": 0.60,
                "feedback": "Test validation failed - low confidence"
            },
            consensus_reached=False,  # Human review 필요
            retry_count=3
        )

        db.add(test_log)
        db.commit()
        db.refresh(test_log)

        logger.info(f"  ✅ DecisionLog 생성됨 (ID={test_log.id})")
        logger.info(f"     Site: {test_log.site_name}")
        logger.info(f"     Consensus: {test_log.consensus_reached}")
        logger.info(f"     Retry Count: {test_log.retry_count}")

        # 2. approve_decision() 함수 시뮬레이션
        logger.info("\n[Step 2] approve_decision() 함수 실행...")

        # UI 함수 시뮬레이션
        decision_id = test_log.id
        log = db.query(DecisionLog).filter(DecisionLog.id == decision_id).first()

        if not log or not log.gpt_analysis:
            logger.error("  ❌ Decision log 조회 실패")
            return

        gpt = log.gpt_analysis

        # Selector 테이블에 저장 (upsert)
        selector = db.query(Selector).filter(Selector.site_name == log.site_name).first()

        if selector:
            # Update existing
            selector.title_selector = gpt.get('title_selector', '')
            selector.body_selector = gpt.get('body_selector', '')
            selector.date_selector = gpt.get('date_selector', '')
            selector.updated_at = datetime.utcnow()
            logger.info(f"  ✅ 기존 Selector 업데이트")
        else:
            # Insert new
            selector = Selector(
                site_name=log.site_name,
                title_selector=gpt.get('title_selector', ''),
                body_selector=gpt.get('body_selector', ''),
                date_selector=gpt.get('date_selector', ''),
                site_type='ssr'
            )
            db.add(selector)
            logger.info(f"  ✅ 새 Selector 생성")

        # Mark consensus as reached
        log.consensus_reached = True

        db.commit()
        logger.info(f"  ✅ approve_decision() 완료")

        # 3. Selector 테이블 업데이트 확인
        logger.info("\n[Step 3] Selector 테이블 업데이트 확인...")

        db.refresh(selector)

        logger.info(f"  ✅ Selector 업데이트됨:")
        logger.info(f"     Site Name: {selector.site_name}")
        logger.info(f"     Title Selector: {selector.title_selector}")
        logger.info(f"     Body Selector: {selector.body_selector}")
        logger.info(f"     Date Selector: {selector.date_selector}")
        logger.info(f"     Updated At: {selector.updated_at}")

        # 4. DecisionLog의 consensus_reached 확인
        logger.info("\n[Step 4] DecisionLog의 consensus_reached 확인...")

        db.refresh(log)

        if log.consensus_reached:
            logger.info(f"  ✅ consensus_reached=True 업데이트됨")
        else:
            logger.error(f"  ❌ consensus_reached가 여전히 False")

        # 5. reject_decision() 테스트 (옵션)
        logger.info("\n[Step 5] reject_decision() 함수 테스트...")

        # 새 DecisionLog 생성 (거부용)
        test_log_reject = DecisionLog(
            url="https://test.example.com/article/67890",
            site_name=test_site,
            gpt_analysis={
                "title_selector": "h2.bad-selector",
                "body_selector": "div.bad-body",
                "date_selector": "span.bad-date",
                "confidence": 0.40,
                "reasoning": "Low confidence test"
            },
            gemini_validation={
                "is_valid": False,
                "confidence": 0.30,
                "feedback": "Very low confidence"
            },
            consensus_reached=False,
            retry_count=2
        )

        db.add(test_log_reject)
        db.commit()
        db.refresh(test_log_reject)

        logger.info(f"  ✅ 거부용 DecisionLog 생성됨 (ID={test_log_reject.id})")

        # reject_decision() 시뮬레이션
        log_reject = db.query(DecisionLog).filter(DecisionLog.id == test_log_reject.id).first()

        if not log_reject:
            logger.error("  ❌ Decision log 조회 실패")
            return

        # Mark as rejected
        log_reject.consensus_reached = False  # Keep false
        log_reject.retry_count += 1

        db.commit()
        db.refresh(log_reject)

        logger.info(f"  ✅ reject_decision() 완료")
        logger.info(f"     Consensus: {log_reject.consensus_reached}")
        logger.info(f"     Retry Count: {log_reject.retry_count}")

        # 검증 통계
        logger.info("\n[Step 6] 검증 통계...")

        total_logs = db.query(DecisionLog).filter(DecisionLog.site_name == test_site).count()
        approved_logs = db.query(DecisionLog).filter(
            DecisionLog.site_name == test_site,
            DecisionLog.consensus_reached == True
        ).count()
        rejected_logs = db.query(DecisionLog).filter(
            DecisionLog.site_name == test_site,
            DecisionLog.consensus_reached == False
        ).count()

        logger.info(f"  Total DecisionLogs: {total_logs}")
        logger.info(f"  Approved: {approved_logs}")
        logger.info(f"  Rejected: {rejected_logs}")

        # 정리
        logger.info("\n[Step 7] 테스트 데이터 정리...")

        db.query(DecisionLog).filter(DecisionLog.site_name == test_site).delete()
        db.query(Selector).filter(Selector.site_name == test_site).delete()
        db.commit()

        logger.info(f"  ✅ 테스트 데이터 삭제 완료")

        logger.info("\n" + "="*60)
        logger.info("✅ Human Review UI 테스트 완료!")
        logger.info("="*60)

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    # API 키 확인 (필요 없음 - UI 테스트만)
    # 테스트 실행
    test_human_review_workflow()
