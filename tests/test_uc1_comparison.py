"""
UC1 Validation 비교 테스트: 규칙 기반 vs LLM 기반

목적:
    규칙 기반 UC1과 LLM 기반 UC1의 성능을 비교 분석합니다.

비교 항목:
    1. 정확도: 광고/보도자료 구분, 품질 평가 정확성
    2. 속도: 실행 시간 (규칙 ~100ms vs LLM ~2-3초)
    3. 비용: 규칙 $0 vs LLM $0.0003/기사
    4. 일관성: 동일 입력 재평가 시 점수 변동

테스트 시나리오:
    1. 정상 기사 (높은 품질)
    2. 짧은 본문 기사 (중간 품질)
    3. 광고/보도자료 (낮은 품질)
    4. 필드 누락 (title/body/date 없음)

실행 방법:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_uc1_comparison.py

작성일: 2025-11-10
"""

import sys
import os
sys.path.insert(0, '/Users/charlee/Desktop/Intern/crawlagent')

from datetime import datetime
from loguru import logger
from src.workflow.uc1_validation import create_uc1_validation_agent
from src.workflow.uc1_validation_llm import create_uc1_llm_agent
import time

# 로그 설정
logger.remove()
logger.add(sys.stdout, level="INFO")


# ============================================================
# 테스트 데이터
# ============================================================

TEST_CASES = [
    {
        "name": "정상 기사 (고품질)",
        "url": "https://www.yna.co.kr/view/AKR20251110000001001",
        "site_name": "yonhap",
        "title": "한중 정상회담 개최, 양국 관계 개선 논의",
        "body": """
        이재명 대통령이 10일 중국 시진핑 주석과 정상회담을 갖고 양국 관계 개선 방안을 논의했다.
        청와대에 따르면 이 대통령은 이날 오전 청와대에서 시 주석과 1시간 30분간 회담을 진행했다.
        회담에서 양 정상은 한중 FTA 2단계 협상 가속화, 문화 교류 확대, 북핵 문제 공동 대응 등을 논의했다.
        이 대통령은 "한중 관계가 새로운 전환점을 맞이했다"며 "양국이 전략적 협력을 강화해 나가자"고 말했다.
        시 주석은 "중국은 한국과의 관계를 매우 중시한다"며 "경제, 안보, 문화 등 모든 분야에서 협력을 확대하겠다"고 화답했다.
        양 정상은 회담 후 6개 분야 협력 MOU를 체결하고 공동 기자회견을 가졌다.
        """,
        "date": "2025-11-10 09:30:00",
        "expected_score_range": (80, 100),
        "expected_action": "save"
    },
    {
        "name": "짧은 본문 기사 (중품질)",
        "url": "https://www.yna.co.kr/view/AKR20251110000002001",
        "site_name": "yonhap",
        "title": "서울 강남구 화재 발생",
        "body": "10일 오전 서울 강남구 대치동의 한 건물에서 화재가 발생했다. 소방당국이 진화 작업을 진행 중이다.",
        "date": "2025-11-10 08:00:00",
        "expected_score_range": (30, 50),
        "expected_action": "heal"
    },
    {
        "name": "광고/보도자료 (저품질)",
        "url": "https://www.example.com/press/123",
        "site_name": "example",
        "title": "[보도자료] 신제품 출시 안내",
        "body": """
        당사는 2025년 11월 10일 신제품 'ABC-100'을 출시합니다.
        ABC-100은 기존 제품 대비 성능이 30% 향상되었습니다.
        자세한 내용은 홈페이지를 참조하세요.
        문의: 02-1234-5678
        """,
        "date": "2025-11-10",
        "expected_score_range": (0, 60),
        "expected_action": "heal"
    },
    {
        "name": "필드 누락 (Title 없음)",
        "url": "https://www.yna.co.kr/view/AKR20251110000003001",
        "site_name": "yonhap",
        "title": None,
        "body": "본문 내용이 있으나 제목이 누락된 경우입니다. 이 경우 Selector가 잘못되었거나 DOM 구조가 변경되었을 가능성이 높습니다.",
        "date": "2025-11-10",
        "expected_score_range": (0, 50),
        "expected_action": "heal"
    },
    {
        "name": "신규 사이트 (Selector 없음)",
        "url": "https://www.newsite.com/article/123",
        "site_name": "newsite",
        "title": "신규 사이트 테스트 기사",
        "body": "이 사이트는 DB에 Selector가 없는 신규 사이트입니다.",
        "date": "2025-11-10",
        "expected_score_range": (0, 100),
        "expected_action": "new_site"
    }
]


# ============================================================
# 비교 테스트 실행
# ============================================================

def run_comparison_test():
    """
    규칙 기반 vs LLM 기반 UC1 비교 테스트
    """
    logger.info("=" * 80)
    logger.info("UC1 Validation 비교 테스트: 규칙 기반 vs LLM 기반")
    logger.info("=" * 80)

    # Agent 생성
    logger.info("\n[Step 1] Agent 초기화...")
    rule_based_agent = create_uc1_validation_agent()
    llm_based_agent = create_uc1_llm_agent()
    logger.info("  ✅ 규칙 기반 Agent 생성 완료")
    logger.info("  ✅ LLM 기반 Agent 생성 완료")

    # 결과 저장
    comparison_results = []

    # 각 테스트 케이스 실행
    for idx, test_case in enumerate(TEST_CASES, 1):
        logger.info("\n" + "=" * 80)
        logger.info(f"[Test Case {idx}/{len(TEST_CASES)}] {test_case['name']}")
        logger.info("=" * 80)

        # 입력 데이터
        initial_state = {
            "url": test_case["url"],
            "site_name": test_case["site_name"],
            "title": test_case["title"],
            "body": test_case["body"],
            "date": test_case["date"],
            "quality_score": 0,
            "missing_fields": [],
            "next_action": "save",
            "uc2_triggered": False,
            "uc2_success": False
        }

        logger.info(f"\n📝 입력 데이터:")
        logger.info(f"   URL: {test_case['url']}")
        logger.info(f"   Site: {test_case['site_name']}")
        logger.info(f"   Title: {test_case['title'][:50] if test_case['title'] else '[누락]'}...")
        logger.info(f"   Body: {test_case['body'][:100] if test_case['body'] else '[누락]'}...")
        logger.info(f"   Date: {test_case['date']}")

        # ============================================================
        # 규칙 기반 실행
        # ============================================================
        logger.info(f"\n🔧 [1] 규칙 기반 UC1 실행...")
        start_time = time.time()
        try:
            rule_result = rule_based_agent.invoke(initial_state)
            rule_execution_time = (time.time() - start_time) * 1000
            rule_success = True
        except Exception as e:
            logger.error(f"   ❌ 규칙 기반 실행 실패: {e}")
            rule_result = initial_state
            rule_execution_time = 0
            rule_success = False

        logger.info(f"   Quality Score: {rule_result.get('quality_score')}")
        logger.info(f"   Missing Fields: {rule_result.get('missing_fields')}")
        logger.info(f"   Next Action: {rule_result.get('next_action')}")
        logger.info(f"   Execution Time: {rule_execution_time:.2f}ms")

        # ============================================================
        # LLM 기반 실행
        # ============================================================
        logger.info(f"\n🤖 [2] LLM 기반 UC1 실행...")

        # LLM용 State 추가 필드
        llm_state = initial_state.copy()
        llm_state["llm_reasoning"] = ""
        llm_state["llm_execution_time"] = 0.0

        start_time = time.time()
        try:
            llm_result = llm_based_agent.invoke(llm_state)
            llm_total_time = (time.time() - start_time) * 1000
            llm_success = True
        except Exception as e:
            logger.error(f"   ❌ LLM 기반 실행 실패: {e}")
            import traceback
            traceback.print_exc()
            llm_result = llm_state
            llm_total_time = 0
            llm_success = False

        logger.info(f"   Quality Score: {llm_result.get('quality_score')}")
        logger.info(f"   Missing Fields: {llm_result.get('missing_fields')}")
        logger.info(f"   Next Action: {llm_result.get('next_action')}")
        logger.info(f"   LLM Reasoning: {llm_result.get('llm_reasoning', 'N/A')}")
        logger.info(f"   LLM API Time: {llm_result.get('llm_execution_time', 0):.2f}ms")
        logger.info(f"   Total Execution Time: {llm_total_time:.2f}ms")

        # ============================================================
        # 비교 분석
        # ============================================================
        logger.info(f"\n📊 [3] 비교 분석:")

        # 점수 차이
        score_diff = abs(rule_result.get('quality_score', 0) - llm_result.get('quality_score', 0))
        logger.info(f"   점수 차이: {score_diff}점")

        # 속도 비교
        speed_ratio = llm_total_time / rule_execution_time if rule_execution_time > 0 else 0
        logger.info(f"   속도 비교: LLM이 {speed_ratio:.1f}x 느림")

        # 액션 일치 여부
        action_match = rule_result.get('next_action') == llm_result.get('next_action')
        logger.info(f"   액션 일치: {'✅ 일치' if action_match else '❌ 불일치'}")

        # 예상 범위 확인
        expected_min, expected_max = test_case['expected_score_range']
        rule_in_range = expected_min <= rule_result.get('quality_score', 0) <= expected_max
        llm_in_range = expected_min <= llm_result.get('quality_score', 0) <= expected_max

        logger.info(f"   예상 점수 범위: {expected_min}-{expected_max}점")
        logger.info(f"   규칙 기반: {'✅ 범위 내' if rule_in_range else '⚠️ 범위 외'}")
        logger.info(f"   LLM 기반: {'✅ 범위 내' if llm_in_range else '⚠️ 범위 외'}")

        # 결과 저장
        comparison_results.append({
            "test_case": test_case['name'],
            "rule_score": rule_result.get('quality_score', 0),
            "llm_score": llm_result.get('quality_score', 0),
            "score_diff": score_diff,
            "rule_time": rule_execution_time,
            "llm_time": llm_total_time,
            "speed_ratio": speed_ratio,
            "action_match": action_match,
            "rule_in_range": rule_in_range,
            "llm_in_range": llm_in_range,
            "llm_reasoning": llm_result.get('llm_reasoning', 'N/A')
        })

    # ============================================================
    # 종합 분석
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("📈 종합 분석 결과")
    logger.info("=" * 80)

    # 평균 계산
    avg_score_diff = sum(r['score_diff'] for r in comparison_results) / len(comparison_results)
    avg_rule_time = sum(r['rule_time'] for r in comparison_results) / len(comparison_results)
    avg_llm_time = sum(r['llm_time'] for r in comparison_results) / len(comparison_results)
    avg_speed_ratio = sum(r['speed_ratio'] for r in comparison_results) / len(comparison_results)

    action_match_rate = sum(1 for r in comparison_results if r['action_match']) / len(comparison_results) * 100
    rule_accuracy = sum(1 for r in comparison_results if r['rule_in_range']) / len(comparison_results) * 100
    llm_accuracy = sum(1 for r in comparison_results if r['llm_in_range']) / len(comparison_results) * 100

    logger.info(f"\n1️⃣ 정확도:")
    logger.info(f"   규칙 기반 정확도: {rule_accuracy:.1f}%")
    logger.info(f"   LLM 기반 정확도: {llm_accuracy:.1f}%")
    logger.info(f"   액션 일치율: {action_match_rate:.1f}%")
    logger.info(f"   평균 점수 차이: {avg_score_diff:.1f}점")

    logger.info(f"\n2️⃣ 속도:")
    logger.info(f"   규칙 기반 평균: {avg_rule_time:.2f}ms")
    logger.info(f"   LLM 기반 평균: {avg_llm_time:.2f}ms")
    logger.info(f"   속도 비율: LLM이 {avg_speed_ratio:.1f}x 느림")

    logger.info(f"\n3️⃣ 비용 (1,000건 기준):")
    logger.info(f"   규칙 기반: $0")
    logger.info(f"   LLM 기반: ~${0.0003 * 1000:.2f} (GPT-4o-mini)")

    logger.info(f"\n4️⃣ LLM 기반의 장점:")
    logger.info(f"   ✅ 광고/보도자료 구분 가능 (의미적 분석)")
    logger.info(f"   ✅ 5W1H 완결성 평가 가능")
    logger.info(f"   ✅ 컨텍스트 기반 품질 평가")

    logger.info(f"\n5️⃣ 규칙 기반의 장점:")
    logger.info(f"   ✅ 빠른 실행 속도 (~{avg_rule_time:.0f}ms)")
    logger.info(f"   ✅ 비용 없음 ($0)")
    logger.info(f"   ✅ 일관성 보장 (동일 입력 → 동일 출력)")

    # ============================================================
    # 추천 전략
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("💡 추천 전략")
    logger.info("=" * 80)

    logger.info(f"\n🎯 하이브리드 접근:")
    logger.info(f"   1단계: 규칙 기반 UC1 실행 (빠르고 무료)")
    logger.info(f"   2단계: 규칙 기반이 uncertain한 경우만 LLM 사용")
    logger.info(f"      - 예: quality_score가 60-80점 사이 (경계 케이스)")
    logger.info(f"      - 예: body_short 플래그 (LLM이 의미 평가)")
    logger.info(f"      - 예: 광고 의심 키워드 발견 ('보도자료', '문의:')")

    logger.info(f"\n📊 예상 효과:")
    logger.info(f"   - 90% 케이스: 규칙 기반 (빠르고 무료)")
    logger.info(f"   - 10% 케이스: LLM 검증 (정확도 향상)")
    logger.info(f"   - 평균 속도: ~{avg_rule_time * 0.9 + avg_llm_time * 0.1:.0f}ms")
    logger.info(f"   - 비용: ~${0.0003 * 1000 * 0.1:.2f} (1,000건 기준)")

    # ============================================================
    # 상세 결과 테이블
    # ============================================================
    logger.info("\n" + "=" * 80)
    logger.info("📋 상세 결과 테이블")
    logger.info("=" * 80)

    logger.info(f"\n{'케이스':<20} {'규칙점수':<10} {'LLM점수':<10} {'차이':<8} {'액션일치':<10} {'규칙시간(ms)':<15} {'LLM시간(ms)':<15}")
    logger.info("-" * 100)

    for result in comparison_results:
        logger.info(
            f"{result['test_case']:<20} "
            f"{result['rule_score']:<10} "
            f"{result['llm_score']:<10} "
            f"{result['score_diff']:<8.1f} "
            f"{'✅' if result['action_match'] else '❌':<10} "
            f"{result['rule_time']:<15.2f} "
            f"{result['llm_time']:<15.2f}"
        )

    logger.info("\n" + "=" * 80)
    logger.info("✅ 비교 테스트 완료!")
    logger.info("=" * 80)

    logger.info(f"\n다음 단계:")
    logger.info(f"  1. LangSmith에서 LLM 기반 UC1 Trace 확인")
    logger.info(f"     → https://smith.langchain.com/o/default/projects/p/crawlagent-poc")
    logger.info(f"  2. 하이브리드 접근 구현 검토")
    logger.info(f"  3. 10시 회의에서 비교 결과 설명")


if __name__ == "__main__":
    # .env 파일 로드
    from dotenv import load_dotenv
    load_dotenv()

    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다")
        sys.exit(1)

    # 테스트 실행
    run_comparison_test()
