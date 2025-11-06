"""
UC1과 UC2 아키텍처 시각화 스크립트
현재 상태와 미래 통합 비전을 다이어그램으로 생성
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

def create_current_architecture():
    """현재 아키텍처: UC1과 UC2가 분리됨"""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
    fig.suptitle('현재 아키텍처: UC1과 UC2 독립 운영', fontsize=16, fontweight='bold')

    # ========== UC1 (왼쪽) ==========
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 10)
    ax1.axis('off')
    ax1.set_title('UC1: Production Crawler\n(실제 운영 중)', fontsize=14, fontweight='bold')

    # UC1 노드들
    y_start = 8
    node_height = 1
    spacing = 1.5

    # 1. 크롤링
    box1 = FancyBboxPatch((1, y_start), 8, node_height,
                          boxstyle="round,pad=0.1",
                          facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=2)
    ax1.add_patch(box1)
    ax1.text(5, y_start + 0.5, '1. Scrapy 크롤링\n(HTML 수집)',
             ha='center', va='center', fontsize=11, fontweight='bold')

    # 화살표
    ax1.arrow(5, y_start, 0, -spacing+0.3, head_width=0.3, head_length=0.2,
              fc='black', ec='black', linewidth=2)

    # 2. Trafilatura 추출
    y_start -= spacing
    box2 = FancyBboxPatch((1, y_start), 8, node_height,
                          boxstyle="round,pad=0.1",
                          facecolor='#E8F5E9', edgecolor='#388E3C', linewidth=2)
    ax1.add_patch(box2)
    ax1.text(5, y_start + 0.5, '2. Trafilatura 추출\n(제목, 본문, 날짜)',
             ha='center', va='center', fontsize=11, fontweight='bold')

    ax1.arrow(5, y_start, 0, -spacing+0.3, head_width=0.3, head_length=0.2,
              fc='black', ec='black', linewidth=2)

    # 3. GPT 검증
    y_start -= spacing
    box3 = FancyBboxPatch((1, y_start), 8, node_height,
                          boxstyle="round,pad=0.1",
                          facecolor='#FFF9C4', edgecolor='#F57C00', linewidth=2)
    ax1.add_patch(box3)
    ax1.text(5, y_start + 0.5, '3. GPT-4o-mini 검증\n(95점 기준)',
             ha='center', va='center', fontsize=11, fontweight='bold')

    # 분기
    y_start -= spacing
    ax1.arrow(5, y_start+spacing, -2, -0.7, head_width=0.3, head_length=0.2,
              fc='green', ec='green', linewidth=2)
    ax1.arrow(5, y_start+spacing, 2, -0.7, head_width=0.3, head_length=0.2,
              fc='red', ec='red', linewidth=2)

    # 성공
    box4_success = FancyBboxPatch((0.5, y_start-0.5), 3.5, node_height,
                                  boxstyle="round,pad=0.1",
                                  facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=2)
    ax1.add_patch(box4_success)
    ax1.text(2.25, y_start, '✓ DB 저장',
             ha='center', va='center', fontsize=11, fontweight='bold', color='#2E7D32')

    # 실패
    box4_fail = FancyBboxPatch((6, y_start-0.5), 3.5, node_height,
                               boxstyle="round,pad=0.1",
                               facecolor='#FFCDD2', edgecolor='#C62828', linewidth=2)
    ax1.add_patch(box4_fail)
    ax1.text(7.75, y_start, '✗ 버림\n(재시도 없음)',
             ha='center', va='center', fontsize=11, fontweight='bold', color='#C62828')

    # 특징 설명
    ax1.text(5, 0.5, '특징: 단순하고 빠름 / LangGraph 미사용 / 실패 시 복구 불가',
             ha='center', va='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # ========== UC2 (오른쪽) ==========
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 10)
    ax2.axis('off')
    ax2.set_title('UC2: Multi-Agent HITL\n(연구용 프로토타입)', fontsize=14, fontweight='bold')

    y = 8.5

    # START 노드
    start_box = FancyBboxPatch((4, y), 2, 0.6,
                               boxstyle="round,pad=0.05",
                               facecolor='#B0BEC5', edgecolor='#37474F', linewidth=2)
    ax2.add_patch(start_box)
    ax2.text(5, y + 0.3, 'START', ha='center', va='center', fontsize=10, fontweight='bold')

    ax2.arrow(5, y, 0, -0.5, head_width=0.3, head_length=0.2,
              fc='black', ec='black', linewidth=2)

    # 1. GPT Propose
    y -= 1.2
    box1 = FancyBboxPatch((1, y), 8, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#E1F5FE', edgecolor='#0277BD', linewidth=2)
    ax2.add_patch(box1)
    ax2.text(5, y + 0.4, '1. GPT Propose\n(HTML → JSON 추출)',
             ha='center', va='center', fontsize=10, fontweight='bold')

    ax2.arrow(5, y, 0, -0.5, head_width=0.3, head_length=0.2,
              fc='black', ec='black', linewidth=2)

    # 2. Gemini Validate
    y -= 1.2
    box2 = FancyBboxPatch((1, y), 8, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=2)
    ax2.add_patch(box2)
    ax2.text(5, y + 0.4, '2. Gemini Validate\n(교차 검증)',
             ha='center', va='center', fontsize=10, fontweight='bold')

    # 분기점
    y -= 1.0
    ax2.text(5, y, '검증 결과?', ha='center', va='center', fontsize=9,
             bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

    # 성공 경로
    ax2.arrow(5, y-0.2, 3, -1, head_width=0.3, head_length=0.2,
              fc='green', ec='green', linewidth=2)
    success_box = FancyBboxPatch((7, y-2.2), 2, 0.6,
                                 boxstyle="round,pad=0.05",
                                 facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=2)
    ax2.add_patch(success_box)
    ax2.text(8, y-1.9, '✓ END\n(성공)', ha='center', va='center',
             fontsize=9, fontweight='bold', color='#2E7D32')

    # 재시도 경로 (retry < 3)
    ax2.annotate('', xy=(2, y-2.8), xytext=(3, y-0.2),
                arrowprops=dict(arrowstyle='->', color='orange', lw=2,
                               connectionstyle="arc3,rad=.5"))
    ax2.text(1.5, y-1.5, 'retry < 3\n(재시도)', ha='center', va='center',
             fontsize=8, color='orange', fontweight='bold',
             bbox=dict(boxstyle='round', facecolor='#FFE082', alpha=0.7))

    # HITL 경로 (retry >= 3)
    ax2.arrow(5, y-0.2, -2.5, -0.5, head_width=0.3, head_length=0.2,
              fc='red', ec='red', linewidth=2)
    y_hitl = y - 1.2
    hitl_box = FancyBboxPatch((0.5, y_hitl-0.3), 2.5, 0.6,
                              boxstyle="round,pad=0.05",
                              facecolor='#FFCDD2', edgecolor='#C62828', linewidth=2)
    ax2.add_patch(hitl_box)
    ax2.text(1.75, y_hitl, '3. Human\nReview', ha='center', va='center',
             fontsize=9, fontweight='bold', color='#C62828')

    ax2.arrow(1.75, y_hitl-0.3, 0, -0.5, head_width=0.3, head_length=0.2,
              fc='black', ec='black', linewidth=2)

    end_box = FancyBboxPatch((0.75, y_hitl-1.5), 2, 0.6,
                             boxstyle="round,pad=0.05",
                             facecolor='#B0BEC5', edgecolor='#37474F', linewidth=2)
    ax2.add_patch(end_box)
    ax2.text(1.75, y_hitl-1.2, 'END', ha='center', va='center',
             fontsize=10, fontweight='bold')

    # 특징 설명
    ax2.text(5, 0.5, '특징: 자동 복구 시도 / LangGraph 사용 / 비용 높음 / 연구 단계',
             ha='center', va='center', fontsize=10,
             bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

    plt.tight_layout()
    return fig

def create_future_architecture():
    """미래 통합 아키텍처"""
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.suptitle('미래 비전: UC1과 UC2 통합 시스템', fontsize=16, fontweight='bold')

    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12)
    ax.axis('off')

    y = 10.5

    # 1. 크롤링 시작
    box1 = FancyBboxPatch((4, y), 6, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#E3F2FD', edgecolor='#1976D2', linewidth=2)
    ax.add_patch(box1)
    ax.text(7, y + 0.4, '1. Scrapy 크롤링 (HTML 수집)',
            ha='center', va='center', fontsize=11, fontweight='bold')

    ax.arrow(7, y, 0, -0.6, head_width=0.4, head_length=0.2,
             fc='black', ec='black', linewidth=2)

    # 2. Trafilatura 추출 시도
    y -= 1.5
    box2 = FancyBboxPatch((4, y), 6, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#E8F5E9', edgecolor='#388E3C', linewidth=2)
    ax.add_patch(box2)
    ax.text(7, y + 0.4, '2. Trafilatura 추출 시도',
            ha='center', va='center', fontsize=11, fontweight='bold')

    # 분기점 1: 추출 성공 여부
    y -= 1.2
    ax.text(7, y, '추출 성공?', ha='center', va='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8),
            fontweight='bold')

    # 왼쪽: 추출 성공 → UC1
    ax.arrow(7, y-0.3, -3.5, -0.8, head_width=0.4, head_length=0.2,
             fc='green', ec='green', linewidth=2)

    y_uc1 = y - 1.5
    uc1_box = FancyBboxPatch((0.5, y_uc1-1.5), 3, 3,
                             boxstyle="round,pad=0.15",
                             facecolor='#E8F5E9', edgecolor='#2E7D32', linewidth=3)
    ax.add_patch(uc1_box)
    ax.text(2, y_uc1 + 1.2, 'UC1 경로', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#2E7D32')

    # UC1 내부
    ax.text(2, y_uc1 + 0.5, '3. GPT-4o-mini 검증', ha='center', va='center', fontsize=10)
    ax.arrow(2, y_uc1 + 0.2, 0, -0.4, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=1.5)

    ax.text(2, y_uc1 - 0.5, '95점 이상?', ha='center', va='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.6))

    success_box = FancyBboxPatch((0.7, y_uc1-1.3), 1.2, 0.5,
                                 boxstyle="round,pad=0.05",
                                 facecolor='#C8E6C9', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(success_box)
    ax.text(1.3, y_uc1-1.05, '✓ 저장', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#2E7D32')

    fail_box = FancyBboxPatch((2.3, y_uc1-1.3), 1.2, 0.5,
                              boxstyle="round,pad=0.05",
                              facecolor='#FFCDD2', edgecolor='#C62828', linewidth=2)
    ax.add_patch(fail_box)
    ax.text(2.9, y_uc1-1.05, '✗ 버림', ha='center', va='center',
            fontsize=9, fontweight='bold', color='#C62828')

    # 오른쪽: 추출 실패 → 구조 변경 감지
    ax.arrow(7, y-0.3, 3.5, -0.8, head_width=0.4, head_length=0.2,
             fc='red', ec='red', linewidth=2)

    y_detect = y - 1.5
    detect_box = FancyBboxPatch((9, y_detect), 4, 0.8,
                                boxstyle="round,pad=0.1",
                                facecolor='#FFF9C4', edgecolor='#F57C00', linewidth=2)
    ax.add_patch(detect_box)
    ax.text(11, y_detect + 0.4, '3. HTML 구조 변경 감지\n(오류 패턴 분석)',
            ha='center', va='center', fontsize=10, fontweight='bold')

    # 분기점 2: 구조 변경인가?
    y_detect -= 1.2
    ax.text(11, y_detect, '구조 변경?', ha='center', va='center', fontsize=10,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8),
            fontweight='bold')

    # Yes → UC2
    ax.arrow(11, y_detect-0.3, 0, -0.6, head_width=0.4, head_length=0.2,
             fc='red', ec='red', linewidth=2)

    y_uc2 = y_detect - 1.5
    uc2_box = FancyBboxPatch((8, y_uc2-3), 6, 3,
                             boxstyle="round,pad=0.15",
                             facecolor='#E1F5FE', edgecolor='#0277BD', linewidth=3)
    ax.add_patch(uc2_box)
    ax.text(11, y_uc2 + 1.2, 'UC2 경로 (Multi-Agent)', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#0277BD')

    # UC2 내부
    ax.text(11, y_uc2 + 0.5, '4. GPT 추출 시도', ha='center', va='center', fontsize=9)
    ax.arrow(11, y_uc2 + 0.2, 0, -0.4, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=1.5)

    ax.text(11, y_uc2 - 0.4, '5. Gemini 검증', ha='center', va='center', fontsize=9)
    ax.arrow(11, y_uc2 - 0.6, 0, -0.3, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=1.5)

    ax.text(11, y_uc2 - 1.2, '성공 or 재시도(3회)\nor HITL', ha='center', va='center',
            fontsize=8, style='italic')

    ax.text(11, y_uc2 - 1.8, '6. 새 추출 규칙 생성', ha='center', va='center', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='#C8E6C9', alpha=0.8))

    # 피드백 루프
    ax.annotate('', xy=(5, y), xytext=(9, y_uc2-2.5),
                arrowprops=dict(arrowstyle='->', color='blue', lw=3,
                               linestyle='dashed',
                               connectionstyle="arc3,rad=-.3"))
    ax.text(6.5, y_uc2 - 0.5, '피드백:\n추출 규칙 업데이트', ha='center', va='center',
            fontsize=9, color='blue', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

    # No → 일시적 오류
    ax.arrow(11, y_detect-0.3, -2, -0.3, head_width=0.4, head_length=0.2,
             fc='orange', ec='orange', linewidth=2)

    temp_box = FancyBboxPatch((7.5, y_detect-1.2), 2.5, 0.6,
                              boxstyle="round,pad=0.05",
                              facecolor='#FFE082', edgecolor='#F57C00', linewidth=2)
    ax.add_patch(temp_box)
    ax.text(8.75, y_detect-0.9, '일시적 오류\n(재시도)', ha='center', va='center',
            fontsize=9, fontweight='bold')

    # 범례
    legend_elements = [
        mlines.Line2D([], [], color='green', marker='>', linestyle='-', linewidth=2,
                     markersize=10, label='정상 흐름 (UC1)'),
        mlines.Line2D([], [], color='red', marker='>', linestyle='-', linewidth=2,
                     markersize=10, label='복구 흐름 (UC2)'),
        mlines.Line2D([], [], color='blue', marker='>', linestyle='--', linewidth=2,
                     markersize=10, label='피드백 루프'),
        mlines.Line2D([], [], color='orange', marker='>', linestyle='-', linewidth=2,
                     markersize=10, label='재시도'),
    ]
    ax.legend(handles=legend_elements, loc='lower center',
             bbox_to_anchor=(0.5, -0.05), ncol=4, fontsize=10)

    plt.tight_layout()
    return fig

def create_state_explanation():
    """State, Node, Edge 개념 설명"""
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.suptitle('LangGraph 핵심 개념: State, Node, Edge', fontsize=16, fontweight='bold')

    ax.set_xlim(0, 14)
    ax.set_ylim(0, 12)
    ax.axis('off')

    # ========== State 설명 ==========
    y = 10.5
    title_box = FancyBboxPatch((0.5, y), 4, 0.6,
                               boxstyle="round,pad=0.1",
                               facecolor='#FFD54F', edgecolor='#F57F17', linewidth=2)
    ax.add_patch(title_box)
    ax.text(2.5, y + 0.3, '1️⃣ State (상태)', ha='center', va='center',
            fontsize=13, fontweight='bold')

    state_desc = """
• 정의: 모든 노드가 공유하는 데이터 구조
• UC1 State: 없음 (단순 함수 체인)
• UC2 State (HITLState):
  - html: 원본 HTML 문자열
  - article_json: 추출된 기사 데이터
  - retry_count: 재시도 횟수 (최대 3)
  - reason: 실패 이유
  - status: success/retry/human_review

• 역할: 워크플로우 전체에서 정보 전달
• 불변성: **state로 복사해 이전 상태 유지
"""
    ax.text(0.5, y - 0.5, state_desc, ha='left', va='top', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='#FFF9C4', alpha=0.8))

    # ========== Node 설명 ==========
    y = 6
    title_box2 = FancyBboxPatch((5.5, y), 4, 0.6,
                                boxstyle="round,pad=0.1",
                                facecolor='#81C784', edgecolor='#2E7D32', linewidth=2)
    ax.add_patch(title_box2)
    ax.text(7.5, y + 0.3, '2️⃣ Node (노드)', ha='center', va='center',
            fontsize=13, fontweight='bold')

    node_desc = """
• 정의: State를 입력받아 처리하는 함수
• UC1 Nodes:
  - validate_article() - GPT 검증만

• UC2 Nodes:
  - gpt_propose() - GPT로 JSON 추출 시도
  - gemini_validate() - Gemini로 교차 검증
  - human_review() - 사람 개입 요청

• 역할: 실제 작업 수행 (LLM 호출, 검증 등)
• 입력/출력: State 딕셔너리
"""
    ax.text(5.5, y - 0.5, node_desc, ha='left', va='top', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='#C8E6C9', alpha=0.8))

    # ========== Edge 설명 ==========
    y = 1.5
    title_box3 = FancyBboxPatch((10.5, y+4.5), 3, 0.6,
                                boxstyle="round,pad=0.1",
                                facecolor='#64B5F6', edgecolor='#1976D2', linewidth=2)
    ax.add_patch(title_box3)
    ax.text(12, y + 4.8, '3️⃣ Edge (엣지)', ha='center', va='center',
            fontsize=13, fontweight='bold')

    edge_desc = """
• 정의: 노드 간 연결 및 흐름 제어
• UC1 Edges:
  - 없음 (순차 실행)

• UC2 Edges:
  - __start__ → gpt_propose
  - gpt_propose → gemini_validate
  - gemini_validate → __end__ (success)
  - gemini_validate → gpt_propose (retry)
  - gemini_validate → human_review (retry≥3)
  - human_review → __end__

• 조건부 Edge:
  - route_after_validation()
    status에 따라 다음 노드 결정
"""
    ax.text(10.5, y + 4, edge_desc, ha='left', va='top', fontsize=9,
            bbox=dict(boxstyle='round', facecolor='#BBDEFB', alpha=0.8))

    # ========== 시각적 예제: UC2 간단 그래프 ==========
    ex_y = 7
    ax.text(12, ex_y + 3, 'UC2 예제:', ha='center', va='center',
            fontsize=11, fontweight='bold', style='italic')

    # START
    start = mpatches.FancyBboxPatch((11, ex_y + 2), 2, 0.4,
                                    boxstyle="round,pad=0.05",
                                    facecolor='#B0BEC5', edgecolor='black', linewidth=1.5)
    ax.add_patch(start)
    ax.text(12, ex_y + 2.2, 'START', ha='center', va='center', fontsize=8, fontweight='bold')

    # GPT Node
    gpt = mpatches.FancyBboxPatch((10.5, ex_y + 0.8), 3, 0.5,
                                  boxstyle="round,pad=0.05",
                                  facecolor='#E1F5FE', edgecolor='#0277BD', linewidth=1.5)
    ax.add_patch(gpt)
    ax.text(12, ex_y + 1.05, 'gpt_propose\n(Node)', ha='center', va='center', fontsize=7)

    # Edge
    ax.arrow(12, ex_y + 2, 0, -0.6, head_width=0.2, head_length=0.1,
             fc='blue', ec='blue', linewidth=1.5)
    ax.text(12.5, ex_y + 1.5, 'Edge', ha='left', va='center', fontsize=7, color='blue')

    # Gemini Node
    gemini = mpatches.FancyBboxPatch((10.5, ex_y - 0.5), 3, 0.5,
                                     boxstyle="round,pad=0.05",
                                     facecolor='#F3E5F5', edgecolor='#7B1FA2', linewidth=1.5)
    ax.add_patch(gemini)
    ax.text(12, ex_y - 0.25, 'gemini_validate\n(Node)', ha='center', va='center', fontsize=7)

    ax.arrow(12, ex_y + 0.8, 0, -0.6, head_width=0.2, head_length=0.1,
             fc='blue', ec='blue', linewidth=1.5)

    # Conditional Edge
    ax.text(12, ex_y - 0.9, 'Conditional Edge\n(route 함수)', ha='center', va='center',
            fontsize=7, color='purple', fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#E1BEE7', alpha=0.7))

    # State 표시
    state_box = mpatches.FancyBboxPatch((8.5, ex_y + 0.5), 1.5, 1.5,
                                        boxstyle="round,pad=0.05",
                                        facecolor='#FFF9C4', edgecolor='#F57C00',
                                        linewidth=1.5, linestyle='dashed')
    ax.add_patch(state_box)
    ax.text(9.25, ex_y + 1.6, 'State', ha='center', va='center', fontsize=7, fontweight='bold')
    ax.text(9.25, ex_y + 1.2, 'html\nretry\nstatus', ha='center', va='center', fontsize=6)

    ax.annotate('', xy=(10.5, ex_y + 1.05), xytext=(9.8, ex_y + 1.05),
                arrowprops=dict(arrowstyle='->', color='orange', lw=1.5, linestyle='dashed'))
    ax.text(9.25, ex_y + 0.7, '모든 Node가\n공유', ha='center', va='center',
            fontsize=6, color='orange', style='italic')

    plt.tight_layout()
    return fig

if __name__ == '__main__':
    # 1. 현재 아키텍처
    fig1 = create_current_architecture()
    fig1.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/architecture_current.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/architecture_current.png")

    # 2. 미래 통합 아키텍처
    fig2 = create_future_architecture()
    fig2.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/architecture_future.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/architecture_future.png")

    # 3. State/Node/Edge 개념 설명
    fig3 = create_state_explanation()
    fig3.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/langgraph_concepts.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/langgraph_concepts.png")

    print("\n📊 모든 다이어그램 생성 완료!")
    print("회의에서 보여줄 파일:")
    print("  1. architecture_current.png - 현재 독립 구조")
    print("  2. architecture_future.png - 미래 통합 비전")
    print("  3. langgraph_concepts.png - State/Node/Edge 설명")
