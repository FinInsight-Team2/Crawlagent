"""
UC1 Human-in-the-Loop (HITL) 시연
Created: 2025-11-02

목적:
    UC1 Validation Agent에서 사람이 개입하는 시나리오를 시연합니다.
    - 점수가 애매한 경우 (70-85점)
    - 사람이 점수를 조정하거나 액션을 변경
    - State 수정 후 재개

실행:
    cd /Users/charlee/Desktop/Intern/NewsFlow/newsflow-poc
    poetry run python scripts/uc1_hitl_demo.py
"""

import sys
sys.path.insert(0, '.')

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, START, END

from src.workflow.uc1_validation import (
    ValidationState,
    extract_fields,
    calculate_quality,
    decide_action,
    route_by_action
)


def create_uc1_with_hitl():
    """
    UC1 Validation Agent with HITL 생성

    interrupt_before=["decide_action"]로 설정하여
    액션 결정 전에 사람이 개입할 수 있도록 함
    """
    builder = StateGraph(ValidationState)

    # 노드 추가
    builder.add_node("extract_fields", extract_fields)
    builder.add_node("calculate_quality", calculate_quality)
    builder.add_node("decide_action", decide_action)

    # 엣지 연결
    builder.add_edge(START, "extract_fields")
    builder.add_edge("extract_fields", "calculate_quality")
    builder.add_edge("calculate_quality", "decide_action")

    # Conditional Edge (3-way 분기)
    builder.add_conditional_edges(
        "decide_action",
        route_by_action,
        {
            "save": END,
            "heal": END,
            "new_site": END
        }
    )

    # HITL 활성화: decide_action 전에 멈춤
    memory = MemorySaver()
    return builder.compile(
        checkpointer=memory,
        interrupt_before=["decide_action"]  # ← 핵심!
    )


def demo_scenario_1_borderline_score():
    """
    시나리오 1: 경계선 점수 (75점)

    상황:
        - Title 누락 (0점)
        - Body 짧음 (200-500자, 30점)
        - Date 있음 (10점)
        - URL 있음 (10점)
        - 총점: 50점 → heal 트리거

    Human 개입:
        - 사람이 보니 사진 기사라서 정상이라고 판단
        - quality_score를 85점으로 상향 조정
        - next_action을 "save"로 변경
    """
    print("\n" + "="*70)
    print("시나리오 1: 경계선 점수 (Human이 점수 상향 조정)")
    print("="*70)

    graph = create_uc1_with_hitl()
    config = {"configurable": {"thread_id": "demo_001"}}

    # 입력 데이터 (사진 기사 - 본문 짧음)
    input_data = {
        "url": "https://www.yna.co.kr/view/photo123",
        "site_name": "yonhap",
        "title": "한강버스 운항 재개",
        "body": "본문 내용..." * 15,  # 약 195자 (짧음)
        "date": "2025-11-02",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save"
    }

    print("\n[단계 1] 중단점까지 실행...")
    print(f"  URL: {input_data['url']}")
    print(f"  Title: {input_data['title']}")
    print(f"  Body: {len(input_data['body'])} chars")
    print(f"  Date: {input_data['date']}")

    # 1단계: 중단점까지 실행 (calculate_quality까지)
    for event in graph.stream(input_data, config):
        print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 2단계: State 확인
    print("\n[단계 2] 현재 State 확인 (멈춤 상태)")
    state = graph.get_state(config)
    print(f"  quality_score: {state.values['quality_score']}")
    print(f"  missing_fields: {state.values['missing_fields']}")
    print(f"  next_action: {state.values.get('next_action', 'None (아직 결정 안됨)')}")
    print(f"  next_node: {state.next}")  # 다음 실행될 노드 (decide_action)

    # 3단계: Human 개입
    print("\n[단계 3] Human 개입 (사람이 판단)")
    print("  👤 Human: 이 기사를 검토해보니 사진 기사로 정상입니다.")
    print("  👤 Human: quality_score를 50 → 85로 상향 조정합니다.")

    # State 수정
    graph.update_state(config, {
        "quality_score": 85,
        "missing_fields": ["body_short"]  # 기록용
    })

    print("  ✅ State 업데이트 완료")

    # 4단계: 수정된 State 확인
    state = graph.get_state(config)
    print(f"  수정 후 quality_score: {state.values['quality_score']}")

    # 5단계: 계속 진행
    print("\n[단계 4] 실행 재개 (decide_action 실행)")
    for event in graph.stream(None, config):
        if event:
            print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 최종 결과
    final_state = graph.get_state(config)
    print("\n[최종 결과]")
    print(f"  quality_score: {final_state.values['quality_score']}")
    print(f"  next_action: {final_state.values['next_action']}")
    print(f"  ✅ 예상: 85점 → 'save' (Human이 승인)")


def demo_scenario_2_reject_healing():
    """
    시나리오 2: Healing 거부

    상황:
        - Body 누락 (0점)
        - 총점: 40점 → heal 트리거 예정

    Human 개입:
        - 사람이 보니 이 사이트는 더 이상 크롤링하지 않기로 결정
        - next_action을 "save"로 변경하여 healing 건너뜀
    """
    print("\n" + "="*70)
    print("시나리오 2: Healing 거부 (Human이 healing 취소)")
    print("="*70)

    graph = create_uc1_with_hitl()
    config = {"configurable": {"thread_id": "demo_002"}}

    # 입력 데이터 (Body 누락)
    input_data = {
        "url": "https://www.deprecated-site.com/article/123",
        "site_name": "deprecated_site",
        "title": "제목",
        "body": None,  # ← Selector 실패
        "date": "2025-11-02",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save"
    }

    print("\n[단계 1] 중단점까지 실행...")
    print(f"  URL: {input_data['url']}")
    print(f"  site_name: {input_data['site_name']}")
    print(f"  Body: None (← Selector 실패)")

    # 1단계: 중단점까지 실행
    for event in graph.stream(input_data, config):
        print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 2단계: State 확인
    print("\n[단계 2] 현재 State 확인")
    state = graph.get_state(config)
    print(f"  quality_score: {state.values['quality_score']}")
    print(f"  missing_fields: {state.values['missing_fields']}")

    # 3단계: Human 개입
    print("\n[단계 3] Human 개입 (healing 거부)")
    print("  👤 Human: 이 사이트는 deprecated되었습니다.")
    print("  👤 Human: healing 대신 그냥 skip하겠습니다.")
    print("  👤 Human: next_action을 강제로 'save'로 변경합니다.")

    # decide_action을 건너뛰고 직접 next_action 설정
    graph.update_state(config, {
        "next_action": "save"  # 강제로 저장
    })

    print("  ✅ State 업데이트 완료")

    # 4단계: 계속 진행
    print("\n[단계 4] 실행 재개")
    for event in graph.stream(None, config):
        if event:
            print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 최종 결과
    final_state = graph.get_state(config)
    print("\n[최종 결과]")
    print(f"  quality_score: {final_state.values['quality_score']}")
    print(f"  next_action: {final_state.values['next_action']}")
    print(f"  ✅ Human이 healing을 거부하고 저장했습니다")


def demo_scenario_3_manual_inspection():
    """
    시나리오 3: 수동 검사 (정상 케이스)

    상황:
        - 모든 필드 정상 (100점)
        - 자동으로 save될 예정

    Human 개입:
        - 사람이 중간에 State만 확인하고 그대로 진행
        - 개입 없이 통과
    """
    print("\n" + "="*70)
    print("시나리오 3: 수동 검사 (개입 없이 통과)")
    print("="*70)

    graph = create_uc1_with_hitl()
    config = {"configurable": {"thread_id": "demo_003"}}

    # 입력 데이터 (정상)
    input_data = {
        "url": "https://www.yna.co.kr/view/normal123",
        "site_name": "yonhap",
        "title": "정상 기사 제목",
        "body": "본문 내용..." * 100,  # 긴 본문
        "date": "2025-11-02",
        "quality_score": 0,
        "missing_fields": [],
        "next_action": "save"
    }

    print("\n[단계 1] 중단점까지 실행...")
    print(f"  URL: {input_data['url']}")
    print(f"  Body: {len(input_data['body'])} chars")

    # 1단계: 중단점까지 실행
    for event in graph.stream(input_data, config):
        print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 2단계: State 확인
    print("\n[단계 2] 현재 State 확인")
    state = graph.get_state(config)
    print(f"  quality_score: {state.values['quality_score']}")
    print(f"  missing_fields: {state.values['missing_fields']}")

    # 3단계: Human 개입 (없음)
    print("\n[단계 3] Human 개입")
    print("  👤 Human: 점수가 100점이므로 정상입니다.")
    print("  👤 Human: 수정 없이 그대로 진행합니다.")

    # 4단계: 계속 진행 (수정 없음)
    print("\n[단계 4] 실행 재개 (수정 없음)")
    for event in graph.stream(None, config):
        if event:
            print(f"  → 노드 실행: {list(event.keys())[0]}")

    # 최종 결과
    final_state = graph.get_state(config)
    print("\n[최종 결과]")
    print(f"  quality_score: {final_state.values['quality_score']}")
    print(f"  next_action: {final_state.values['next_action']}")
    print(f"  ✅ 정상 기사, 개입 없이 save되었습니다")


def main():
    """
    UC1 HITL 시연 메인
    """
    print("="*70)
    print("UC1 Human-in-the-Loop (HITL) 시연")
    print("="*70)
    print("\n목적:")
    print("  1. interrupt_before로 중단점 설정")
    print("  2. State 확인 및 수정")
    print("  3. 실행 재개")
    print("\n3가지 시나리오:")
    print("  1. 경계선 점수 → Human이 상향 조정")
    print("  2. Healing 거부 → Human이 액션 변경")
    print("  3. 정상 케이스 → Human이 확인만 (수정 없음)")

    # 시나리오 1: 점수 상향 조정
    demo_scenario_1_borderline_score()

    # 시나리오 2: Healing 거부
    demo_scenario_2_reject_healing()

    # 시나리오 3: 수동 검사
    demo_scenario_3_manual_inspection()

    # 결과 요약
    print("\n" + "="*70)
    print("HITL 시연 완료")
    print("="*70)
    print("\n✅ 모든 시나리오 성공!")
    print("\n학습 포인트:")
    print("  1. interrupt_before로 원하는 지점에서 멈출 수 있음")
    print("  2. graph.get_state()로 현재 State 확인 가능")
    print("  3. graph.update_state()로 State 수정 가능")
    print("  4. graph.stream(None, config)로 재개 가능")
    print("\nUC2에서 적용:")
    print("  - GPT-4o + Gemini 분석 완료 후")
    print("  - 합의 판단 전에 interrupt")
    print("  - Human이 두 모델 결과 비교")
    print("  - confidence_score 조정 또는 거부권 행사")


if __name__ == "__main__":
    main()
