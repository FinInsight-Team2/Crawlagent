"""
LangGraph Studio 그래프 스크린샷에 설명 추가
회의 발표용 자료 생성

사용법:
1. LangGraph Studio에서 UC1/UC2 그래프 스크린샷 찍기
2. 스크린샷을 docs/studio_uc1.png, docs/studio_uc2.png로 저장
3. 이 스크립트 실행하면 설명이 추가된 이미지 생성
"""
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from PIL import Image
import os

def add_explanations_to_uc1():
    """UC1 그래프에 설명 추가"""
    fig, ax = plt.subplots(figsize=(16, 12))

    # 스크린샷이 있으면 배경으로 사용 (선택사항)
    screenshot_path = '/Users/charlee/Desktop/Intern/crawlagent/docs/studio_uc1.png'
    if os.path.exists(screenshot_path):
        img = Image.open(screenshot_path)
        ax.imshow(img, extent=[0, 16, 0, 12], aspect='auto', alpha=0.3)

    ax.set_xlim(0, 16)
    ax.set_ylim(0, 12)
    ax.axis('off')

    fig.suptitle('UC1: 단순 검증 워크플로우 (LangGraph 미사용)',
                 fontsize=18, fontweight='bold', y=0.98)

    # 제목 설명
    title_box = FancyBboxPatch((0.5, 11), 15, 0.6,
                               boxstyle="round,pad=0.1",
                               facecolor='#FFEB3B', edgecolor='#F57F17',
                               linewidth=3, alpha=0.9)
    ax.add_patch(title_box)
    ax.text(8, 11.3, '⚠️ UC1은 LangGraph를 사용하지 않는 단순 Python 함수입니다',
            ha='center', va='center', fontsize=12, fontweight='bold')

    # UC1 구조 다이어그램
    y = 9.5

    # 노드 1: validate_article 함수
    node1 = FancyBboxPatch((3, y), 10, 1.5,
                          boxstyle="round,pad=0.15",
                          facecolor='#E3F2FD', edgecolor='#1976D2',
                          linewidth=3, alpha=0.95)
    ax.add_patch(node1)
    ax.text(8, y + 1, 'validate_article()',
            ha='center', va='center', fontsize=14, fontweight='bold')
    ax.text(8, y + 0.5, 'GPT-4o-mini로 품질 검증 (95점 기준)',
            ha='center', va='center', fontsize=11)

    # 설명 박스 1
    explain1 = FancyBboxPatch((0.3, y), 2, 1.5,
                             boxstyle="round,pad=0.1",
                             facecolor='#FFF9C4', edgecolor='#F57C00',
                             linewidth=2, alpha=0.9)
    ax.add_patch(explain1)
    ax.text(1.3, y + 1.1, '📌 "노드"', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#E65100')
    ax.text(1.3, y + 0.7, '단순 Python\n함수 1개', ha='center', va='center',
            fontsize=9)
    ax.text(1.3, y + 0.2, 'State 없음', ha='center', va='center',
            fontsize=8, style='italic')

    # 입력
    y_in = y + 2.2
    input_box = FancyBboxPatch((6, y_in), 4, 0.7,
                              boxstyle="round,pad=0.05",
                              facecolor='#C8E6C9', edgecolor='#2E7D32',
                              linewidth=2)
    ax.add_patch(input_box)
    ax.text(8, y_in + 0.35, '입력: 제목, 본문, 날짜',
            ha='center', va='center', fontsize=10, fontweight='bold')

    ax.arrow(8, y_in, 0, -0.5, head_width=0.4, head_length=0.2,
             fc='black', ec='black', linewidth=2)

    # 출력
    y_out = y - 1.2
    ax.arrow(8, y, 0, -0.4, head_width=0.4, head_length=0.2,
             fc='black', ec='black', linewidth=2)

    # 분기
    y_out -= 0.5
    ax.text(8, y_out, 'GPT 점수?', ha='center', va='center', fontsize=11,
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.8),
            fontweight='bold')

    # 성공
    y_success = y_out - 1.5
    ax.arrow(8, y_out-0.2, -2.5, -0.8, head_width=0.4, head_length=0.2,
             fc='green', ec='green', linewidth=3)

    success_box = FancyBboxPatch((3, y_success), 3, 0.8,
                                 boxstyle="round,pad=0.1",
                                 facecolor='#C8E6C9', edgecolor='#2E7D32',
                                 linewidth=2)
    ax.add_patch(success_box)
    ax.text(4.5, y_success + 0.4, '✅ 95점 이상\nDB 저장',
            ha='center', va='center', fontsize=10, fontweight='bold',
            color='#1B5E20')

    # 실패
    ax.arrow(8, y_out-0.2, 2.5, -0.8, head_width=0.4, head_length=0.2,
             fc='red', ec='red', linewidth=3)

    fail_box = FancyBboxPatch((10, y_success), 3, 0.8,
                              boxstyle="round,pad=0.1",
                              facecolor='#FFCDD2', edgecolor='#C62828',
                              linewidth=2)
    ax.add_patch(fail_box)
    ax.text(11.5, y_success + 0.4, '❌ 95점 미만\n버림 (재시도 없음)',
            ha='center', va='center', fontsize=10, fontweight='bold',
            color='#B71C1C')

    # 설명 박스 2
    explain2 = FancyBboxPatch((13.5, y), 2, 1.5,
                             boxstyle="round,pad=0.1",
                             facecolor='#FFE0B2', edgecolor='#E65100',
                             linewidth=2, alpha=0.9)
    ax.add_patch(explain2)
    ax.text(14.5, y + 1.1, '🚫 "엣지"', ha='center', va='center',
            fontsize=10, fontweight='bold', color='#BF360C')
    ax.text(14.5, y + 0.7, 'if-else\n분기만', ha='center', va='center',
            fontsize=9)
    ax.text(14.5, y + 0.2, '조건부\n라우팅 없음', ha='center', va='center',
            fontsize=8, style='italic')

    # 하단 특징 요약
    summary_box = FancyBboxPatch((1, 0.5), 14, 2,
                                boxstyle="round,pad=0.15",
                                facecolor='#ECEFF1', edgecolor='#455A64',
                                linewidth=3, alpha=0.9)
    ax.add_patch(summary_box)

    summary_text = """
📊 UC1 특징:
• 구조: 단순 Python 함수 (validate_article)
• State: 없음 - 함수 인자로 직접 전달
• Node: 1개 (GPT 검증)
• Edge: 없음 - if-else로 분기만 처리
• LangGraph: 사용하지 않음 (langgraph.json에만 등록)
• 장점: 빠르고 단순함, 비용 절감
• 단점: 실패 시 자동 복구 불가능
    """
    ax.text(8, 1.5, summary_text, ha='center', va='center', fontsize=10,
            family='monospace')

    plt.tight_layout()
    return fig

def add_explanations_to_uc2():
    """UC2 그래프에 설명 추가"""
    fig, ax = plt.subplots(figsize=(16, 14))

    # 스크린샷이 있으면 배경으로 사용
    screenshot_path = '/Users/charlee/Desktop/Intern/crawlagent/docs/studio_uc2.png'
    if os.path.exists(screenshot_path):
        img = Image.open(screenshot_path)
        ax.imshow(img, extent=[0, 16, 0, 14], aspect='auto', alpha=0.3)

    ax.set_xlim(0, 16)
    ax.set_ylim(0, 14)
    ax.axis('off')

    fig.suptitle('UC2: Multi-Agent HITL 워크플로우 (LangGraph 사용)',
                 fontsize=18, fontweight='bold', y=0.98)

    # 제목 설명
    title_box = FancyBboxPatch((0.5, 13), 15, 0.6,
                               boxstyle="round,pad=0.1",
                               facecolor='#4CAF50', edgecolor='#1B5E20',
                               linewidth=3, alpha=0.9)
    ax.add_patch(title_box)
    ax.text(8, 13.3, '✅ UC2는 LangGraph StateGraph로 구현된 Multi-Agent 시스템입니다',
            ha='center', va='center', fontsize=12, fontweight='bold', color='white')

    y = 11.5

    # State 설명 (최상단)
    state_box = FancyBboxPatch((0.5, y), 4.5, 1.8,
                              boxstyle="round,pad=0.1",
                              facecolor='#FFF9C4', edgecolor='#F57C00',
                              linewidth=3, alpha=0.95)
    ax.add_patch(state_box)
    ax.text(2.75, y + 1.5, '📦 HITLState', ha='center', va='center',
            fontsize=11, fontweight='bold', color='#E65100')

    state_text = """html: str
article_json: dict
retry_count: int
reason: str
status: str"""
    ax.text(2.75, y + 0.7, state_text, ha='center', va='center',
            fontsize=8, family='monospace')
    ax.text(2.75, y + 0.1, '모든 노드가 공유', ha='center', va='center',
            fontsize=8, style='italic', color='#F57C00')

    # 그래프 구조
    x_center = 8

    # START 노드
    start_y = y + 0.9
    start_box = FancyBboxPatch((x_center - 1, start_y), 2, 0.6,
                               boxstyle="round,pad=0.05",
                               facecolor='#B0BEC5', edgecolor='#37474F',
                               linewidth=2)
    ax.add_patch(start_box)
    ax.text(x_center, start_y + 0.3, '__start__', ha='center', va='center',
            fontsize=10, fontweight='bold')

    ax.arrow(x_center, start_y, 0, -0.4, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=2)

    # Node 1: gpt_propose
    node1_y = start_y - 1.2
    node1 = FancyBboxPatch((x_center - 2, node1_y), 4, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#E1F5FE', edgecolor='#0277BD',
                          linewidth=3, alpha=0.95)
    ax.add_patch(node1)
    ax.text(x_center, node1_y + 0.55, '1️⃣ gpt_propose', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(x_center, node1_y + 0.15, 'GPT-4o-mini로 JSON 추출',
            ha='center', va='center', fontsize=9)

    # 설명 박스 - Node 1
    explain1 = FancyBboxPatch((x_center + 2.5, node1_y), 3.5, 0.8,
                             boxstyle="round,pad=0.05",
                             facecolor='#E3F2FD', edgecolor='#1976D2',
                             linewidth=2, alpha=0.9)
    ax.add_patch(explain1)
    ax.text(x_center + 4.25, node1_y + 0.5, '입력: State[html]',
            ha='center', va='center', fontsize=8)
    ax.text(x_center + 4.25, node1_y + 0.1, '출력: State[article_json]',
            ha='center', va='center', fontsize=8, fontweight='bold')

    ax.arrow(x_center, node1_y, 0, -0.4, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=2)
    ax.text(x_center + 0.5, node1_y - 0.2, 'Edge', ha='left', va='center',
            fontsize=8, color='blue')

    # Node 2: gemini_validate
    node2_y = node1_y - 1.3
    node2 = FancyBboxPatch((x_center - 2, node2_y), 4, 0.8,
                          boxstyle="round,pad=0.1",
                          facecolor='#F3E5F5', edgecolor='#7B1FA2',
                          linewidth=3, alpha=0.95)
    ax.add_patch(node2)
    ax.text(x_center, node2_y + 0.55, '2️⃣ gemini_validate', ha='center', va='center',
            fontsize=11, fontweight='bold')
    ax.text(x_center, node2_y + 0.15, 'Gemini로 교차 검증',
            ha='center', va='center', fontsize=9)

    # 설명 박스 - Node 2
    explain2 = FancyBboxPatch((x_center + 2.5, node2_y), 3.5, 0.8,
                             boxstyle="round,pad=0.05",
                             facecolor='#F3E5F5', edgecolor='#7B1FA2',
                             linewidth=2, alpha=0.9)
    ax.add_patch(explain2)
    ax.text(x_center + 4.25, node2_y + 0.5, '입력: State[article_json]',
            ha='center', va='center', fontsize=8)
    ax.text(x_center + 4.25, node2_y + 0.1, '출력: State[status]',
            ha='center', va='center', fontsize=8, fontweight='bold')

    # 조건부 라우팅 (핵심!)
    route_y = node2_y - 1.1
    route_box = FancyBboxPatch((x_center - 2.5, route_y), 5, 0.6,
                              boxstyle="round,pad=0.05",
                              facecolor='#FFEB3B', edgecolor='#F57F17',
                              linewidth=3, alpha=0.95)
    ax.add_patch(route_box)
    ax.text(x_center, route_y + 0.3, '⚡ route_after_validation()',
            ha='center', va='center', fontsize=10, fontweight='bold')

    # 조건부 라우팅 설명
    route_explain = FancyBboxPatch((x_center + 3, route_y - 0.5), 4, 1.6,
                                  boxstyle="round,pad=0.1",
                                  facecolor='#FFF9C4', edgecolor='#F57C00',
                                  linewidth=2, alpha=0.95)
    ax.add_patch(route_explain)
    ax.text(x_center + 5, route_y + 0.8, '🔀 Conditional Edge',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='#E65100')
    route_cond = """if status == 'success':
    → END
elif retry_count < 3:
    → gpt_propose
else:
    → human_review"""
    ax.text(x_center + 5, route_y + 0.1, route_cond,
            ha='center', va='center', fontsize=7, family='monospace')

    # 경로 1: 성공 → END
    end_y = route_y - 0.8
    ax.arrow(x_center, route_y, 3, -0.3, head_width=0.3, head_length=0.2,
             fc='green', ec='green', linewidth=3)
    ax.text(x_center + 1.5, route_y - 0.3, 'success', ha='center', va='center',
            fontsize=8, color='green', fontweight='bold')

    end_box = FancyBboxPatch((x_center + 2.5, end_y), 1.5, 0.5,
                            boxstyle="round,pad=0.05",
                            facecolor='#C8E6C9', edgecolor='#2E7D32',
                            linewidth=2)
    ax.add_patch(end_box)
    ax.text(x_center + 3.25, end_y + 0.25, '__end__',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='#1B5E20')

    # 경로 2: 재시도 → gpt_propose
    ax.annotate('', xy=(x_center - 2.5, node1_y + 0.4),
                xytext=(x_center - 2.5, route_y),
                arrowprops=dict(arrowstyle='->', color='orange', lw=3,
                               connectionstyle="arc3,rad=-.5"))
    ax.text(x_center - 3.5, node1_y - 0.5, 'retry < 3\n(재시도)',
            ha='center', va='center', fontsize=8, color='orange',
            fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='#FFE082', alpha=0.8))

    # 경로 3: HITL → human_review
    ax.arrow(x_center, route_y, -3, -0.3, head_width=0.3, head_length=0.2,
             fc='red', ec='red', linewidth=3)
    ax.text(x_center - 1.5, route_y - 0.3, 'retry ≥ 3', ha='center', va='center',
            fontsize=8, color='red', fontweight='bold')

    # Node 3: human_review
    hitl_y = route_y - 0.8
    hitl_box = FancyBboxPatch((x_center - 5, hitl_y), 2, 0.5,
                             boxstyle="round,pad=0.05",
                             facecolor='#FFCDD2', edgecolor='#C62828',
                             linewidth=2)
    ax.add_patch(hitl_box)
    ax.text(x_center - 4, hitl_y + 0.25, '3️⃣ human_review',
            ha='center', va='center', fontsize=9, fontweight='bold',
            color='#B71C1C')

    ax.arrow(x_center - 4, hitl_y, 0, -0.3, head_width=0.3, head_length=0.15,
             fc='black', ec='black', linewidth=2)

    # HITL END
    hitl_end = FancyBboxPatch((x_center - 4.75, hitl_y - 0.8), 1.5, 0.5,
                             boxstyle="round,pad=0.05",
                             facecolor='#B0BEC5', edgecolor='#37474F',
                             linewidth=2)
    ax.add_patch(hitl_end)
    ax.text(x_center - 4, hitl_y - 0.55, '__end__',
            ha='center', va='center', fontsize=9, fontweight='bold')

    # 하단 특징 요약
    summary_box = FancyBboxPatch((1, 0.5), 14, 2.5,
                                boxstyle="round,pad=0.15",
                                facecolor='#E8F5E9', edgecolor='#2E7D32',
                                linewidth=3, alpha=0.95)
    ax.add_patch(summary_box)

    summary_text = """
📊 UC2 특징:
• 구조: LangGraph StateGraph (복잡한 워크플로우)
• State: HITLState (html, article_json, retry_count, reason, status) - 모든 노드가 공유
• Node: 5개 (__start__, gpt_propose, gemini_validate, human_review, __end__)
• Edge: 6개 (조건부 라우팅 포함 - route_after_validation 함수)
• LangGraph: ✅ 완전히 활용 (상태 관리, 조건부 분기, 재시도 로직)
• 장점: 자동 복구, Multi-Agent 교차 검증, HITL (Human-in-the-Loop)
• 단점: 비용 높음 (GPT + Gemini 반복 호출), 연구 단계
• 미래: UC1 실패 시 자동으로 UC2 호출하는 통합 시스템으로 발전 예정
    """
    ax.text(8, 1.5, summary_text, ha='center', va='center', fontsize=10,
            family='monospace')

    plt.tight_layout()
    return fig

def create_comparison_chart():
    """UC1 vs UC2 비교표"""
    fig, ax = plt.subplots(figsize=(14, 10))
    fig.suptitle('UC1 vs UC2 상세 비교', fontsize=18, fontweight='bold')

    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis('off')

    # 표 헤더
    header_y = 9
    header_box1 = FancyBboxPatch((1, header_y), 4, 0.6,
                                 boxstyle="round,pad=0.05",
                                 facecolor='#1976D2', edgecolor='#0D47A1',
                                 linewidth=2)
    ax.add_patch(header_box1)
    ax.text(3, header_y + 0.3, '구분', ha='center', va='center',
            fontsize=12, fontweight='bold', color='white')

    header_box2 = FancyBboxPatch((5.5, header_y), 3.5, 0.6,
                                 boxstyle="round,pad=0.05",
                                 facecolor='#E3F2FD', edgecolor='#1976D2',
                                 linewidth=2)
    ax.add_patch(header_box2)
    ax.text(7.25, header_y + 0.3, 'UC1 (Production)', ha='center', va='center',
            fontsize=11, fontweight='bold')

    header_box3 = FancyBboxPatch((9.5, header_y), 3.5, 0.6,
                                 boxstyle="round,pad=0.05",
                                 facecolor='#E1F5FE', edgecolor='#0277BD',
                                 linewidth=2)
    ax.add_patch(header_box3)
    ax.text(11.25, header_y + 0.3, 'UC2 (Research)', ha='center', va='center',
            fontsize=11, fontweight='bold')

    # 비교 항목
    rows = [
        ('LangGraph 사용', '❌ 미사용', '✅ 완전 사용'),
        ('State 관리', '❌ 없음\n(함수 인자)', '✅ HITLState\n(공유 메모리)'),
        ('Node 개수', '1개\n(validate_article)', '5개\n(start/gpt/gemini/hitl/end)'),
        ('Edge 유형', 'if-else 분기', 'Conditional Edge\n(route 함수)'),
        ('재시도 로직', '❌ 없음\n(실패 시 버림)', '✅ 최대 3회\n(자동 재시도)'),
        ('Multi-Agent', '❌ GPT만 사용', '✅ GPT + Gemini\n(교차 검증)'),
        ('HITL', '❌ 없음', '✅ 3회 실패 시\n사람 개입'),
        ('비용', '🟢 낮음\n(GPT 1회 호출)', '🔴 높음\n(GPT+Gemini 반복)'),
        ('속도', '🟢 빠름 (<1초)', '🟡 느림 (3-20초)'),
        ('안정성', '🟢 검증됨', '🟡 연구 단계'),
        ('실패 처리', '🔴 버림', '🟢 자동 복구 시도'),
    ]

    y = header_y - 0.8
    for category, uc1_val, uc2_val in rows:
        # 구분
        cat_box = FancyBboxPatch((1, y), 4, 0.7,
                                boxstyle="round,pad=0.05",
                                facecolor='#FFF9C4', edgecolor='#F57C00',
                                linewidth=1.5)
        ax.add_patch(cat_box)
        ax.text(3, y + 0.35, category, ha='center', va='center',
                fontsize=9, fontweight='bold')

        # UC1
        uc1_box = FancyBboxPatch((5.5, y), 3.5, 0.7,
                                boxstyle="round,pad=0.05",
                                facecolor='#FAFAFA', edgecolor='#BDBDBD',
                                linewidth=1)
        ax.add_patch(uc1_box)
        ax.text(7.25, y + 0.35, uc1_val, ha='center', va='center',
                fontsize=8)

        # UC2
        uc2_box = FancyBboxPatch((9.5, y), 3.5, 0.7,
                                boxstyle="round,pad=0.05",
                                facecolor='#FAFAFA', edgecolor='#BDBDBD',
                                linewidth=1)
        ax.add_patch(uc2_box)
        ax.text(11.25, y + 0.35, uc2_val, ha='center', va='center',
                fontsize=8)

        y -= 0.8

    plt.tight_layout()
    return fig

if __name__ == '__main__':
    print("🎨 UC1/UC2 설명 자료 생성 중...")

    # 1. UC1 설명
    fig1 = add_explanations_to_uc1()
    fig1.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/uc1_explained.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/uc1_explained.png")

    # 2. UC2 설명
    fig2 = add_explanations_to_uc2()
    fig2.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/uc2_explained.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/uc2_explained.png")

    # 3. 비교표
    fig3 = create_comparison_chart()
    fig3.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/uc1_vs_uc2_comparison.png',
                 dpi=300, bbox_inches='tight')
    print("✅ 생성 완료: docs/uc1_vs_uc2_comparison.png")

    print("\n📊 발표 자료 생성 완료!")
    print("\n📌 회의에서 보여줄 순서:")
    print("  1. uc1_explained.png - UC1 구조 설명 (LangGraph 미사용)")
    print("  2. uc2_explained.png - UC2 구조 설명 (State/Node/Edge 강조)")
    print("  3. uc1_vs_uc2_comparison.png - 상세 비교표")
    print("\n💡 LangGraph Studio 화면과 함께 보여주세요!")
    print("   Studio URL: https://smith.langchain.com/studio/?baseUrl=https://michigan-summaries-supporters-watch.trycloudflare.com")
