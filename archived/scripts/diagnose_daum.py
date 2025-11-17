"""
CrawlAgent - API Key & UC3 Diagnostic Script
Created: 2025-11-11

이 스크립트는 다음을 수행합니다:
1. OpenAI API 키 유효성 검증
2. Google Gemini API 키 유효성 검증
3. Daum URL로 UC3 직접 테스트
4. 상세한 에러 메시지 수집 및 분석
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

# Configure logger
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
)


async def test_openai_api():
    """OpenAI API 키 유효성 검증"""
    logger.info("=" * 60)
    logger.info("[1/4] OpenAI API 키 검증 시작")
    logger.info("=" * 60)

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        logger.error("❌ OPENAI_API_KEY가 .env에 설정되지 않았습니다")
        return False

    logger.info(f"✅ API 키 발견: {api_key[:20]}...{api_key[-10:]}")

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=api_key)

        # Simple test: List models
        logger.info("🔍 OpenAI API 연결 테스트 중...")
        response = await client.chat.completions.create(
            model="gpt-4o-mini", messages=[{"role": "user", "content": "Hello"}], max_tokens=5
        )

        logger.success("✅ OpenAI API 연결 성공!")
        logger.info(f"   모델: {response.model}")
        logger.info(f"   응답: {response.choices[0].message.content}")
        return True

    except Exception as e:
        logger.error(f"❌ OpenAI API 연결 실패: {type(e).__name__}")
        logger.error(f"   에러 메시지: {str(e)}")

        if "401" in str(e) or "Incorrect API key" in str(e):
            logger.warning("   💡 API 키가 유효하지 않습니다. .env 파일을 확인하세요")
        elif "quota" in str(e).lower():
            logger.warning("   💡 API 사용량 한도 초과")

        return False


async def test_gemini_api():
    """Google Gemini API 키 유효성 검증"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("[2/4] Google Gemini API 키 검증 시작")
    logger.info("=" * 60)

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        logger.error("❌ GOOGLE_API_KEY가 .env에 설정되지 않았습니다")
        return False

    logger.info(f"✅ API 키 발견: {api_key[:20]}...{api_key[-10:]}")

    try:
        import google.generativeai as genai

        genai.configure(api_key=api_key)

        # Simple test (유료 모델 사용)
        logger.info("🔍 Gemini API 연결 테스트 중 (gemini-2.5-pro)...")
        model = genai.GenerativeModel("gemini-2.5-pro")
        response = model.generate_content("Hello")

        logger.success("✅ Gemini API 연결 성공!")
        logger.info(f"   응답: {response.text[:50]}...")
        return True

    except Exception as e:
        logger.error(f"❌ Gemini API 연결 실패: {type(e).__name__}")
        logger.error(f"   에러 메시지: {str(e)}")

        if "API key not valid" in str(e):
            logger.warning("   💡 API 키가 유효하지 않습니다. .env 파일을 확인하세요")

        return False


async def test_uc3_directly():
    """Daum URL로 UC3 직접 실행"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("[3/4] UC3 Discovery 직접 테스트")
    logger.info("=" * 60)

    test_url = "https://v.daum.net/v/20251111141611257"
    logger.info(f"🎯 테스트 URL: {test_url}")

    try:
        from src.workflow.master_crawl_workflow import MasterCrawlState
        from src.workflow.uc3_discovery import uc3_discovery_node

        # Create minimal state
        state: MasterCrawlState = {
            "url": test_url,
            "site_name": "daum",
            "html": None,
            "screenshot_base64": None,
            "screenshot_timestamp": None,
            "uc1_validation_result": None,
            "uc2_consensus_result": None,
            "uc3_discovery_result": None,
            "current_uc": "uc3",
            "workflow_history": [],
            "supervisor_reasoning": None,
            "quality_passed": None,
            "extracted_title": None,
            "extracted_body": None,
            "extracted_date": None,
        }

        logger.info("🚀 UC3 Discovery 노드 실행 중...")

        # Run UC3
        result = await uc3_discovery_node(state)

        logger.success("✅ UC3 실행 완료!")

        # Analyze result
        if hasattr(result, "update"):
            update = result.update
            uc3_result = update.get("uc3_discovery_result", {})

            consensus_reached = uc3_result.get("consensus_reached", False)
            consensus_score = uc3_result.get("consensus_score", 0.0)

            logger.info(f"   합의 성공: {consensus_reached}")
            logger.info(f"   합의 점수: {consensus_score}")

            if consensus_reached:
                logger.success("   🎉 Daum 사이트 CSS Selector 생성 성공!")
                proposed = uc3_result.get("proposed_selectors", {})
                logger.info(f"   Title: {proposed.get('title_selector', 'N/A')}")
                logger.info(f"   Body: {proposed.get('body_selector', 'N/A')}")
                logger.info(f"   Date: {proposed.get('date_selector', 'N/A')}")
            else:
                logger.warning("   ⚠️  합의 실패 (Consensus Score < 0.7)")

                # Show detailed error
                gpt_analysis = uc3_result.get("gpt_analysis", {})
                gemini_validation = uc3_result.get("gemini_validation", {})

                logger.info("   GPT-4o 분석:")
                logger.info(f"      {gpt_analysis}")
                logger.info("   Gemini 검증:")
                logger.info(f"      {gemini_validation}")

        return True

    except Exception as e:
        logger.error(f"❌ UC3 실행 실패: {type(e).__name__}")
        logger.error(f"   에러 메시지: {str(e)}")

        # Detailed error analysis
        if "401" in str(e):
            logger.warning("   💡 OpenAI API 인증 실패 (401 Unauthorized)")
            logger.warning("   💡 .env 파일의 OPENAI_API_KEY를 확인하세요")
        elif "ConnectionError" in str(e):
            logger.warning("   💡 네트워크 연결 문제")
        elif "timeout" in str(e).lower():
            logger.warning("   💡 API 응답 시간 초과")

        import traceback

        logger.error("   전체 스택 트레이스:")
        traceback.print_exc()

        return False


async def analyze_failure_reasons():
    """실패 원인 종합 분석 및 해결 방법 제시"""
    logger.info("")
    logger.info("=" * 60)
    logger.info("[4/4] 실패 원인 분석 및 해결 방법")
    logger.info("=" * 60)

    # Check database for existing Daum records
    try:
        from src.storage.database import get_db
        from src.storage.models import DecisionLog, Selector

        db = next(get_db())

        # Check if Daum selector exists
        daum_selector = db.query(Selector).filter(Selector.site_name == "daum").first()

        if daum_selector:
            logger.info("✅ Daum Selector가 DB에 존재합니다:")
            logger.info(f"   Success Count: {daum_selector.success_count}")
            logger.info(f"   Failure Count: {daum_selector.failure_count}")
            logger.info(f"   Title Selector: {daum_selector.title_selector}")
        else:
            logger.warning("⚠️  Daum Selector가 DB에 없습니다 (새 사이트)")

        # Check recent decision logs for Daum
        recent_logs = (
            db.query(DecisionLog)
            .filter(DecisionLog.site_name == "daum")
            .order_by(DecisionLog.created_at.desc())
            .limit(3)
            .all()
        )

        if recent_logs:
            logger.info(f"📋 최근 Daum 관련 DecisionLog {len(recent_logs)}개:")
            for log in recent_logs:
                logger.info(f"   - 합의: {log.consensus_reached}, 재시도: {log.retry_count}")
        else:
            logger.info("📋 Daum 관련 DecisionLog 없음")

    except Exception as e:
        logger.error(f"❌ DB 조회 실패: {e}")

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("📊 진단 요약")
    logger.info("=" * 60)
    logger.info(
        """
다음 단계로 진행하세요:

1. API 키가 모두 유효한 경우:
   → Phase 2: Safety Mechanisms 구현 시작
   → Loop Detection, Retry Counter 추가

2. OpenAI API 401 에러가 계속되는 경우:
   → OpenAI 계정에서 API 키 재생성
   → .env 파일 업데이트 후 재시작

3. UC3 합의 실패 (Consensus < 0.7):
   → GPT-4o 분석 결과 확인
   → Gemini 검증 결과 확인
   → Selector 품질 개선 필요

4. 네트워크 에러:
   → 인터넷 연결 확인
   → 방화벽 설정 확인
    """
    )


async def main():
    """메인 진단 실행"""
    logger.info("🔧 CrawlAgent API & UC3 진단 시작\n")

    # Run all tests
    openai_ok = await test_openai_api()
    gemini_ok = await test_gemini_api()

    if openai_ok and gemini_ok:
        logger.info("")
        logger.success("✅ 모든 API 키 검증 성공! UC3 테스트를 진행합니다")
        uc3_ok = await test_uc3_directly()
    else:
        logger.error("")
        logger.error("❌ API 키 검증 실패. UC3 테스트를 건너뜁니다")
        uc3_ok = False

    # Analyze failures
    await analyze_failure_reasons()

    # Final status
    logger.info("")
    logger.info("=" * 60)
    if openai_ok and gemini_ok and uc3_ok:
        logger.success("🎉 전체 진단 성공! 시스템이 정상 작동합니다")
    else:
        logger.warning("⚠️  일부 테스트 실패. 위의 해결 방법을 참고하세요")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
