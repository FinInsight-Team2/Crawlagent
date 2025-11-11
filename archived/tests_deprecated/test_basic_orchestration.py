"""
기본 Multi-Agent Orchestration 테스트

목적:
    Supervisor → UC1 → Supervisor 흐름이 제대로 작동하는지 확인

테스트:
    1. UC1 성공 케이스: quality_score >= 80 → END
    2. UC1 실패 케이스: quality_score < 80 → UC2 라우팅 확인

실행 방법:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_basic_orchestration.py

작성일: 2025-11-10
"""

import sys
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from loguru import logger
from src.workflow.uc1_validation import create_uc1_validation_agent

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO")


def test_uc1_success():
    """
    테스트 1: UC1 성공 (quality_score >= 80)

    입력:
        - title: 충분히 긴 제목 (20자)
        - body: 충분히 긴 본문 (500자 이상)
        - date: 존재
        - url: 정상

    예상 결과:
        - quality_score: 100
        - quality_passed: True
        - next_action: "save"
    """
    logger.info("=" * 80)
    logger.info("[Test 1] UC1 성공 케이스")
    logger.info("=" * 80)

    # UC1 Graph 생성
    uc1_graph = create_uc1_validation_agent()

    # 입력 데이터 (고품질 기사)
    test_state = {
        "url": "https://www.yna.co.kr/view/AKR20251110000001001",
        "site_name": "yonhap",
        "title": "한중 정상회담 개최, 양국 관계 개선 논의",  # 20자
        "body": "이재명 대통령이 10일 중국 시진핑 주석과 정상회담을 갖고 양국 관계 개선 방안을 논의했다. " * 10,  # 500자 이상
        "date": "2025-11-10 09:30:00",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
        "uc2_triggered": False,
        "uc2_success": False
    }

    # UC1 실행
    result = uc1_graph.invoke(test_state)

    # 결과 확인
    logger.info(f"\n📊 결과:")
    logger.info(f"   quality_score: {result.get('quality_score')}")
    logger.info(f"   quality_passed: {result.get('quality_passed')}")
    logger.info(f"   next_action: {result.get('next_action')}")
    logger.info(f"   missing_fields: {result.get('missing_fields')}")

    # 검증
    assert result.get("quality_score") >= 80, f"Expected score >= 80, got {result.get('quality_score')}"
    assert result.get("quality_passed") is True, "Expected quality_passed=True"
    assert result.get("next_action") == "save", f"Expected next_action='save', got {result.get('next_action')}"

    logger.info(f"\n✅ 테스트 1 통과!\n")


def test_uc1_failure_with_selector():
    """
    테스트 2: UC1 실패 + Selector 존재 (quality_score < 80)

    입력:
        - title: 짧은 제목 (5자)
        - body: 짧은 본문 (100자)
        - date: 없음
        - url: 정상

    예상 결과:
        - quality_score: < 80
        - quality_passed: False
        - next_action: "heal" (Selector 존재 시) 또는 "uc3" (Selector 없음)
    """
    logger.info("=" * 80)
    logger.info("[Test 2] UC1 실패 케이스 (Selector 확인)")
    logger.info("=" * 80)

    # UC1 Graph 생성
    uc1_graph = create_uc1_validation_agent()

    # 입력 데이터 (저품질 기사)
    test_state = {
        "url": "https://www.yna.co.kr/view/AKR20251110000002001",
        "site_name": "yonhap",  # DB에 Selector 존재
        "title": "화재",  # 5자
        "body": "서울 강남구에서 화재가 발생했다.",  # 100자 미만
        "date": None,  # 날짜 없음
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
        "uc2_triggered": False,
        "uc2_success": False
    }

    # UC1 실행
    result = uc1_graph.invoke(test_state)

    # 결과 확인
    logger.info(f"\n📊 결과:")
    logger.info(f"   quality_score: {result.get('quality_score')}")
    logger.info(f"   quality_passed: {result.get('quality_passed')}")
    logger.info(f"   next_action: {result.get('next_action')}")
    logger.info(f"   missing_fields: {result.get('missing_fields')}")

    # 검증
    assert result.get("quality_score") < 80, f"Expected score < 80, got {result.get('quality_score')}"
    assert result.get("quality_passed") is False, "Expected quality_passed=False"
    assert result.get("next_action") in ["heal", "uc3"], f"Expected next_action in ['heal', 'uc3'], got {result.get('next_action')}"

    logger.info(f"\n✅ 테스트 2 통과!")
    logger.info(f"   → next_action={result.get('next_action')} (Supervisor가 이 값을 보고 UC2/UC3로 라우팅)\n")


def test_uc1_failure_without_selector():
    """
    테스트 3: UC1 실패 + Selector 없음 (신규 사이트)

    입력:
        - site_name: "newsite" (DB에 없음)
        - 낮은 품질 데이터

    예상 결과:
        - quality_score: < 80
        - quality_passed: False
        - next_action: "uc3" (신규 사이트 Discovery)
    """
    logger.info("=" * 80)
    logger.info("[Test 3] UC1 실패 + 신규 사이트 (UC3 트리거)")
    logger.info("=" * 80)

    # UC1 Graph 생성
    uc1_graph = create_uc1_validation_agent()

    # 입력 데이터 (신규 사이트)
    test_state = {
        "url": "https://www.newsite.com/article/123",
        "site_name": "newsite",  # DB에 Selector 없음
        "title": "뉴스",
        "body": "짧은 본문",
        "date": None,
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save",
        "uc2_triggered": False,
        "uc2_success": False
    }

    # UC1 실행
    result = uc1_graph.invoke(test_state)

    # 결과 확인
    logger.info(f"\n📊 결과:")
    logger.info(f"   quality_score: {result.get('quality_score')}")
    logger.info(f"   quality_passed: {result.get('quality_passed')}")
    logger.info(f"   next_action: {result.get('next_action')}")
    logger.info(f"   missing_fields: {result.get('missing_fields')}")

    # 검증
    assert result.get("quality_score") < 80, f"Expected score < 80, got {result.get('quality_score')}"
    assert result.get("quality_passed") is False, "Expected quality_passed=False"
    assert result.get("next_action") == "uc3", f"Expected next_action='uc3', got {result.get('next_action')}"

    logger.info(f"\n✅ 테스트 3 통과!")
    logger.info(f"   → next_action=uc3 (Supervisor가 UC3 Discovery로 라우팅)\n")


if __name__ == "__main__":
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Multi-Agent Orchestration 기본 테스트 시작")
    logger.info("=" * 80 + "\n")

    try:
        # 테스트 1: UC1 성공
        test_uc1_success()

        # 테스트 2: UC1 실패 + Selector 존재
        test_uc1_failure_with_selector()

        # 테스트 3: UC1 실패 + Selector 없음
        test_uc1_failure_without_selector()

        # 전체 성공
        logger.info("=" * 80)
        logger.info("✅ 모든 테스트 통과!")
        logger.info("=" * 80)
        logger.info("\n📋 다음 단계:")
        logger.info("  1. Master Graph 전체 흐름 테스트 (Supervisor → UC1 → Supervisor → UC2/UC3)")
        logger.info("  2. LangSmith Trace 확인 (전체 경로 시각화)")
        logger.info("  3. UC1 하이브리드 구현 (규칙 기반 + LLM)\n")

    except AssertionError as e:
        logger.error(f"\n❌ 테스트 실패: {e}\n")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ 예상치 못한 에러: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
