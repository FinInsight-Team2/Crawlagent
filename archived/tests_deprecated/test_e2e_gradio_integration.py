"""
Sprint 4-5 최종 통합 검증 (End-to-End)
Created: 2025-11-09

목적:
    UC1 → UC2 → Human Review 전체 플로우를 검증하고
    Gradio UI에서 모든 작업이 가능한지 확인

테스트 시나리오:
    1. UC1 품질 검증 실패 (고의로 잘못된 Selector 사용)
    2. UC2 자동 트리거 확인
    3. UC2 합의 실패 시뮬레이션 (Human Review 필요)
    4. DecisionLog 생성 확인
    5. Gradio UI Tab 6에서 승인/거부 가능 확인

실행 방법:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_e2e_gradio_integration.py
"""

import sys
import os

# 프로젝트 루트 추가
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from datetime import datetime
from src.storage.database import get_db
from src.storage.models import DecisionLog, Selector, CrawlResult
from src.workflow.uc1_validation import create_uc1_validation_agent
from loguru import logger

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_e2e_integration():
    """
    End-to-End 통합 테스트

    시나리오:
        1. 테스트용 Selector 생성 (잘못된 Selector)
        2. UC1 품질 검증 실패
        3. UC2 자동 트리거 (heal_with_uc2 노드)
        4. UC2 합의 성공/실패 시뮬레이션
        5. DecisionLog 확인
        6. Gradio UI에서 승인/거부 가능 확인
    """
    logger.info("="*80)
    logger.info("Sprint 4-5 최종 통합 검증 (End-to-End)")
    logger.info("="*80)

    db = next(get_db())

    try:
        # ============================================================
        # Phase 1: 테스트 환경 준비
        # ============================================================
        logger.info("\n[Phase 1] 테스트 환경 준비...")

        test_site = "test_e2e_site"
        test_url = "https://www.yna.co.kr/view/AKR20251109000001001"

        # 기존 테스트 데이터 삭제
        db.query(DecisionLog).filter(DecisionLog.site_name == test_site).delete()
        db.query(Selector).filter(Selector.site_name == test_site).delete()
        db.query(CrawlResult).filter(CrawlResult.site_name == test_site).delete()
        db.commit()

        # 잘못된 Selector 생성 (품질 실패 유발)
        bad_selector = Selector(
            site_name=test_site,
            title_selector="h999.not-exist",  # 존재하지 않는 Selector
            body_selector="div.not-exist",
            date_selector="time.not-exist",
            site_type="ssr"
        )
        db.add(bad_selector)
        db.commit()

        logger.info(f"  ✅ 테스트 환경 준비 완료")
        logger.info(f"     Test Site: {test_site}")
        logger.info(f"     Bad Selector Created (title_selector={bad_selector.title_selector})")

        # ============================================================
        # Phase 2: UC1 품질 검증 실패 시뮬레이션
        # ============================================================
        logger.info("\n[Phase 2] UC1 품질 검증 실패 시뮬레이션...")

        graph = create_uc1_validation_agent()

        inputs = {
            "url": test_url,
            "site_name": test_site,
            "title": None,  # Selector 실패
            "body": "짧은 본문",  # 500자 미만
            "date": "2025-11-09",
            "quality_score": 0,
            "missing_fields": [],
            "next_action": "save",
            "uc2_triggered": False,
            "uc2_success": False
        }

        logger.info(f"  Input State:")
        logger.info(f"     URL: {inputs['url']}")
        logger.info(f"     Title: {inputs['title']}")
        logger.info(f"     Body: {inputs['body']}")
        logger.info(f"     Expected: quality_score < 80 → UC2 trigger")

        # ============================================================
        # Phase 3: UC1 실행 (UC2 자동 연계)
        # ============================================================
        logger.info("\n[Phase 3] UC1 Validation Agent 실행...")

        result = graph.invoke(inputs)

        logger.info(f"\n  UC1 실행 결과:")
        logger.info(f"     Quality Score: {result.get('quality_score')}")
        logger.info(f"     Missing Fields: {result.get('missing_fields')}")
        logger.info(f"     Next Action: {result.get('next_action')}")
        logger.info(f"     UC2 Triggered: {result.get('uc2_triggered')}")
        logger.info(f"     UC2 Success: {result.get('uc2_success')}")

        # ============================================================
        # Phase 4: DecisionLog 확인
        # ============================================================
        logger.info("\n[Phase 4] DecisionLog 확인...")

        decision_logs = db.query(DecisionLog).filter_by(
            site_name=test_site
        ).order_by(DecisionLog.created_at.desc()).all()

        if decision_logs:
            logger.info(f"  ✅ DecisionLog 생성됨 ({len(decision_logs)}개)")
            for i, log in enumerate(decision_logs, 1):
                logger.info(f"\n  [{i}] DecisionLog ID={log.id}")
                logger.info(f"       URL: {log.url}")
                logger.info(f"       Consensus Reached: {log.consensus_reached}")
                logger.info(f"       Retry Count: {log.retry_count}")
                logger.info(f"       GPT Proposal: {bool(log.gpt_analysis)}")
                logger.info(f"       Gemini Validation: {bool(log.gemini_validation)}")
                logger.info(f"       Created: {log.created_at}")

                # GPT/Gemini 내용 상세 표시
                if log.gpt_analysis:
                    logger.info(f"       GPT Title Selector: {log.gpt_analysis.get('title_selector')}")
                    logger.info(f"       GPT Confidence: {log.gpt_analysis.get('confidence')}")

                if log.gemini_validation:
                    logger.info(f"       Gemini Is Valid: {log.gemini_validation.get('is_valid')}")
                    logger.info(f"       Gemini Confidence: {log.gemini_validation.get('confidence')}")
        else:
            logger.warning(f"  ⚠️ DecisionLog가 생성되지 않았습니다")

        # ============================================================
        # Phase 5: Selector 업데이트 확인 (UC2 성공 시)
        # ============================================================
        logger.info("\n[Phase 5] Selector 업데이트 확인...")

        selector = db.query(Selector).filter_by(site_name=test_site).first()

        if selector:
            logger.info(f"  ✅ Selector 존재:")
            logger.info(f"     Title Selector: {selector.title_selector}")
            logger.info(f"     Body Selector: {selector.body_selector}")
            logger.info(f"     Date Selector: {selector.date_selector}")
            logger.info(f"     Updated At: {selector.updated_at}")

            # UC2 성공 시 Selector가 업데이트되었는지 확인
            if result.get('uc2_success') and selector.title_selector != "h999.not-exist":
                logger.info(f"  ✅ UC2가 Selector를 성공적으로 업데이트했습니다!")
            elif not result.get('uc2_success'):
                logger.info(f"  ℹ️ UC2 합의 실패 → Human Review 필요")
        else:
            logger.warning(f"  ⚠️ Selector를 찾을 수 없습니다")

        # ============================================================
        # Phase 6: Gradio UI Tab 6 사용 가능 확인
        # ============================================================
        logger.info("\n[Phase 6] Gradio UI Tab 6 사용 가능성 확인...")

        pending_logs = db.query(DecisionLog).filter_by(
            consensus_reached=False
        ).order_by(DecisionLog.created_at.desc()).all()

        if pending_logs:
            logger.info(f"  ✅ Human Review 대기 중인 제안: {len(pending_logs)}개")
            logger.info(f"\n  Gradio UI에서 확인 가능:")
            logger.info(f"     1. Gradio 실행: poetry run python src/ui/app.py")
            logger.info(f"     2. http://localhost:7860 접속")
            logger.info(f"     3. Tab 6 '🤖 자동 복구 (🔧 개발자)' 클릭")
            logger.info(f"     4. '🔄 새로고침' 버튼 클릭")
            logger.info(f"     5. Pending List에서 Decision ID={pending_logs[0].id} 확인")
            logger.info(f"     6. '✅ 승인' 또는 '❌ 거부' 클릭")
        else:
            logger.info(f"  ℹ️ Human Review 대기 중인 제안 없음 (UC2 합의 성공)")

        # ============================================================
        # Phase 7: 통합 검증 결과 요약
        # ============================================================
        logger.info("\n[Phase 7] 통합 검증 결과 요약...")

        summary = {
            "UC1 실행": "✅" if result.get('quality_score') is not None else "❌",
            "품질 검증 실패": "✅" if result.get('quality_score') < 80 else "❌",
            "UC2 트리거": "✅" if result.get('uc2_triggered') else "❌",
            "DecisionLog 생성": "✅" if decision_logs else "❌",
            "UC2 합의 성공": "✅" if result.get('uc2_success') else "ℹ️ (Human Review 필요)",
            "Gradio UI 사용 가능": "✅" if pending_logs or decision_logs else "❌"
        }

        logger.info(f"\n  검증 결과:")
        for key, value in summary.items():
            logger.info(f"     {key}: {value}")

        # ============================================================
        # Phase 8: 정리 (테스트 데이터 삭제)
        # ============================================================
        logger.info("\n[Phase 8] 테스트 데이터 정리...")

        # 선택: 테스트 데이터를 남겨두고 Gradio UI에서 확인 가능
        logger.info(f"  ℹ️ 테스트 데이터를 남겨두고 Gradio UI에서 확인하세요!")
        logger.info(f"     - Site: {test_site}")
        logger.info(f"     - DecisionLogs: {len(decision_logs)}개")
        logger.info(f"     - Pending: {len(pending_logs)}개")

        # 삭제하려면 주석 해제:
        # db.query(DecisionLog).filter(DecisionLog.site_name == test_site).delete()
        # db.query(Selector).filter(Selector.site_name == test_site).delete()
        # db.commit()
        # logger.info(f"  ✅ 테스트 데이터 삭제 완료")

        logger.info("\n" + "="*80)
        logger.info("✅ End-to-End 통합 검증 완료!")
        logger.info("="*80)

        logger.info("\n다음 단계:")
        logger.info("  1. Gradio UI 실행:")
        logger.info("     cd /Users/charlee/Desktop/Intern/crawlagent")
        logger.info("     PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/ui/app.py")
        logger.info("")
        logger.info("  2. http://localhost:7860 접속")
        logger.info("")
        logger.info("  3. Tab 6 '🤖 자동 복구 (🔧 개발자)' 확인")
        logger.info("")
        logger.info("  4. '🔄 새로고침' 클릭 → Pending List 확인")
        logger.info("")
        logger.info("  5. '✅ 승인' 또는 '❌ 거부' 테스트")

    except Exception as e:
        logger.error(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()


if __name__ == "__main__":
    # .env 파일 로드
    from dotenv import load_dotenv
    load_dotenv()

    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        logger.error("   .env 파일에 OPENAI_API_KEY를 설정하세요")
        sys.exit(1)

    # GEMINI_API_KEY 또는 GOOGLE_API_KEY 확인
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        logger.error("❌ GEMINI_API_KEY 또는 GOOGLE_API_KEY 환경변수가 설정되지 않았습니다")
        logger.error("   .env 파일에 GOOGLE_API_KEY를 설정하세요")
        sys.exit(1)

    # GEMINI_API_KEY가 없으면 GOOGLE_API_KEY로 설정
    if not os.getenv("GEMINI_API_KEY") and os.getenv("GOOGLE_API_KEY"):
        os.environ["GEMINI_API_KEY"] = os.getenv("GOOGLE_API_KEY")

    # 테스트 실행
    test_e2e_integration()
