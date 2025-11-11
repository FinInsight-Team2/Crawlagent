#!/usr/bin/env python3
"""
UI 다이어그램 PNG 생성 스크립트

목적:
- Gradio UI Tab 2를 위한 간단한 플로우차트 PNG 이미지 생성
- Plotly 대신 정적 PNG 사용 (로딩 빠름, 5분 이내 파악 가능)

생성 이미지:
1. uc1_flow_simple.png - UC1 품질 검증 플로우
2. uc2_flow_simple.png - UC2 2-Agent Consensus 플로우
3. uc3_flow_simple.png - UC3 3-Tool Discovery 플로우
4. supervisor_llm_tree.png - Supervisor LLM 의사결정 트리
"""

import os
from pathlib import Path
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import matplotlib.lines as mlines

# Dark theme 색상 (theme.py와 일치)
BG_COLOR = "#1a1b1e"
TEXT_COLOR = "#e5e7eb"
PRIMARY_COLOR = "#667eea"
SUCCESS_COLOR = "#10b981"
WARNING_COLOR = "#f59e0b"
ERROR_COLOR = "#ef4444"
BOX_COLOR = "#2d2e35"

# 출력 디렉토리
OUTPUT_DIR = Path("docs/ui_diagrams")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 기본 Figure 설정
def create_figure(width=12, height=8):
    """Dark theme Figure 생성"""
    fig, ax = plt.subplots(figsize=(width, height), facecolor=BG_COLOR)
    ax.set_facecolor(BG_COLOR)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.axis('off')
    return fig, ax

def draw_box(ax, x, y, w, h, text, color=BOX_COLOR, text_color=TEXT_COLOR, fontsize=11, bold=False):
    """둥근 박스 그리기"""
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.1",
        facecolor=color,
        edgecolor=PRIMARY_COLOR,
        linewidth=2
    )
    ax.add_patch(box)

    weight = 'bold' if bold else 'normal'
    ax.text(
        x + w/2, y + h/2, text,
        ha='center', va='center',
        color=text_color,
        fontsize=fontsize,
        weight=weight,
        wrap=True
    )

def draw_arrow(ax, x1, y1, x2, y2, label="", color=PRIMARY_COLOR):
    """화살표 그리기"""
    arrow = FancyArrowPatch(
        (x1, y1), (x2, y2),
        arrowstyle='->,head_width=0.4,head_length=0.8',
        color=color,
        linewidth=2.5,
        zorder=1
    )
    ax.add_patch(arrow)

    if label:
        mid_x, mid_y = (x1 + x2) / 2, (y1 + y2) / 2
        ax.text(
            mid_x + 0.3, mid_y, label,
            ha='left', va='bottom',
            color=TEXT_COLOR,
            fontsize=9,
            style='italic'
        )

def create_uc1_diagram():
    """UC1: 품질 검증 플로우"""
    print("📊 UC1 다이어그램 생성 중...")

    fig, ax = create_figure(12, 8)

    # Title
    ax.text(5, 9.5, "UC1: 품질 검증 (Quality Validation)",
            ha='center', va='top', color=TEXT_COLOR, fontsize=16, weight='bold')

    # Flow
    draw_box(ax, 3.5, 8, 3, 0.6, "START", SUCCESS_COLOR, TEXT_COLOR, 12, True)
    draw_arrow(ax, 5, 7.7, 5, 7.2)

    draw_box(ax, 3, 6.5, 4, 0.6, "DB에서 CSS Selector 조회")
    draw_arrow(ax, 5, 6.2, 5, 5.7)

    draw_box(ax, 3, 5, 4, 0.6, "HTML 파싱 + 추출")
    draw_arrow(ax, 5, 4.7, 5, 4.2)

    draw_box(ax, 2.5, 3.5, 5, 0.6, "품질 점수 계산 (0-100점)\n제목 40 + 본문 40 + 날짜 20")
    draw_arrow(ax, 5, 3.2, 5, 2.7)

    # Decision diamond
    draw_box(ax, 3.5, 1.8, 3, 0.8, "80점 이상?", WARNING_COLOR, TEXT_COLOR, 11, True)

    # YES path
    draw_arrow(ax, 6.5, 2.2, 7.5, 2.2, "YES", SUCCESS_COLOR)
    draw_box(ax, 7.5, 1.9, 2, 0.6, "✅ DB 저장", SUCCESS_COLOR)
    draw_arrow(ax, 8.5, 1.6, 8.5, 1.1)
    draw_box(ax, 7.8, 0.5, 1.4, 0.5, "END", SUCCESS_COLOR, TEXT_COLOR, 11, True)

    # NO path
    draw_arrow(ax, 3.5, 2.2, 2, 2.2, "NO", ERROR_COLOR)
    draw_box(ax, 0.5, 1.9, 1.5, 0.6, "UC2로\n이동", ERROR_COLOR)

    # Stats box
    ax.text(0.5, 0.5, "📊 통과율: 95% (최근 30일)",
            ha='left', va='bottom', color=TEXT_COLOR, fontsize=10)

    plt.tight_layout()
    output_path = OUTPUT_DIR / "uc1_flow_simple.png"
    plt.savefig(output_path, dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✅ UC1 다이어그램 저장: {output_path}")

def create_uc2_diagram():
    """UC2: 2-Agent Consensus 플로우"""
    print("📊 UC2 다이어그램 생성 중...")

    fig, ax = create_figure(12, 8)

    # Title
    ax.text(5, 9.5, "UC2: 2-Agent 자동 복구 (Self-Healing)",
            ha='center', va='top', color=TEXT_COLOR, fontsize=16, weight='bold')

    # Flow
    draw_box(ax, 3.5, 8, 3, 0.6, "UC1 실패 감지", ERROR_COLOR, TEXT_COLOR, 12, True)
    draw_arrow(ax, 5, 7.7, 5, 7.2)

    # Agent 1: GPT-4o
    draw_box(ax, 2.5, 6.5, 5, 0.7, "🤖 GPT-4o Proposer\nCSS Selector 제안", PRIMARY_COLOR)
    draw_arrow(ax, 5, 6.2, 5, 5.7)

    # Agent 2: Gemini
    draw_box(ax, 2.5, 5, 5, 0.7, "🤖 Gemini 2.5 Flash Validator\n실제 HTML에서 검증", PRIMARY_COLOR)
    draw_arrow(ax, 5, 4.7, 5, 4.2)

    # Consensus calculation
    draw_box(ax, 1.5, 3.5, 7, 0.6, "Consensus Score = 0.3×GPT + 0.3×Gemini + 0.4×추출품질")
    draw_arrow(ax, 5, 3.2, 5, 2.7)

    # Decision
    draw_box(ax, 3.5, 1.8, 3, 0.8, "0.6 이상?", WARNING_COLOR, TEXT_COLOR, 11, True)

    # YES path
    draw_arrow(ax, 6.5, 2.2, 7.5, 2.2, "YES", SUCCESS_COLOR)
    draw_box(ax, 7.2, 1.9, 2.3, 0.6, "✅ DB 업데이트", SUCCESS_COLOR)
    draw_arrow(ax, 8.3, 1.6, 8.3, 1.1)
    draw_box(ax, 7.6, 0.5, 1.4, 0.5, "END", SUCCESS_COLOR, TEXT_COLOR, 11, True)

    # NO path
    draw_arrow(ax, 3.5, 2.2, 1.5, 2.2, "NO", ERROR_COLOR)
    draw_box(ax, 0.3, 1.9, 1.2, 0.6, "재시도\n(최대3회)", WARNING_COLOR)
    draw_arrow(ax, 0.9, 1.6, 0.9, 1.1)
    draw_box(ax, 0.2, 0.5, 1.4, 0.5, "Human\nReview", ERROR_COLOR)

    # Stats
    ax.text(0.5, 9, "📊 복구 성공률: 90%",
            ha='left', va='top', color=SUCCESS_COLOR, fontsize=10, weight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "uc2_flow_simple.png"
    plt.savefig(output_path, dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✅ UC2 다이어그램 저장: {output_path}")

def create_uc3_diagram():
    """UC3: 3-Tool Discovery 플로우"""
    print("📊 UC3 다이어그램 생성 중...")

    fig, ax = create_figure(12, 9)

    # Title
    ax.text(5, 8.7, "UC3: 신규 사이트 Discovery (3-Tool + 2-Agent)",
            ha='center', va='top', color=TEXT_COLOR, fontsize=16, weight='bold')

    # START
    draw_box(ax, 3.5, 7.5, 3, 0.5, "신규 사이트 감지", WARNING_COLOR, TEXT_COLOR, 11, True)
    draw_arrow(ax, 5, 7.3, 5, 6.9)

    # 3-Tool parallel
    ax.text(5, 6.7, "3-Tool 병렬 실행", ha='center', va='top', color=TEXT_COLOR, fontsize=11, weight='bold')

    # Tool 1: Tavily
    draw_arrow(ax, 5, 6.5, 1.5, 5.8)
    draw_box(ax, 0.3, 5, 2.4, 0.7, "🔍 Tavily\nGitHub/SO 검색", PRIMARY_COLOR)

    # Tool 2: Firecrawl
    draw_arrow(ax, 5, 6.5, 5, 5.8)
    draw_box(ax, 3.8, 5, 2.4, 0.7, "🔥 Firecrawl\nHTML 전처리", PRIMARY_COLOR)

    # Tool 3: BeautifulSoup
    draw_arrow(ax, 5, 6.5, 8.5, 5.8)
    draw_box(ax, 7.3, 5, 2.4, 0.7, "🍜 BeautifulSoup\nDOM 통계 분석", PRIMARY_COLOR)

    # Converge
    draw_arrow(ax, 1.5, 4.7, 5, 4.2)
    draw_arrow(ax, 5, 4.7, 5, 4.2)
    draw_arrow(ax, 8.5, 4.7, 5, 4.2)

    # 2-Agent Consensus
    draw_box(ax, 2, 3.5, 6, 0.6, "🤖 GPT-4o + Gemini 2.5 Consensus (0.7 이상 승인)")
    draw_arrow(ax, 5, 3.2, 5, 2.7)

    # Decision
    draw_box(ax, 3.5, 1.8, 3, 0.8, "0.7 이상?", WARNING_COLOR, TEXT_COLOR, 11, True)

    # YES
    draw_arrow(ax, 6.5, 2.2, 7.5, 2.2, "YES", SUCCESS_COLOR)
    draw_box(ax, 7.2, 1.9, 2.3, 0.6, "✅ DB 저장", SUCCESS_COLOR)
    draw_arrow(ax, 8.3, 1.6, 8.3, 1.1)
    draw_box(ax, 7.6, 0.5, 1.4, 0.5, "END", SUCCESS_COLOR, TEXT_COLOR, 11, True)

    # NO
    draw_arrow(ax, 3.5, 2.2, 1.5, 2.2, "NO", ERROR_COLOR)
    draw_box(ax, 0.2, 1.9, 1.2, 0.6, "Human\nReview", ERROR_COLOR)

    # Stats
    ax.text(0.5, 8.5, "📌 예: 네이버 뉴스 → 0.89 ✅",
            ha='left', va='top', color=SUCCESS_COLOR, fontsize=10, weight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "uc3_flow_simple.png"
    plt.savefig(output_path, dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✅ UC3 다이어그램 저장: {output_path}")

def create_supervisor_diagram():
    """Supervisor LLM 의사결정 트리"""
    print("📊 Supervisor LLM 다이어그램 생성 중...")

    fig, ax = create_figure(12, 10)

    # Title
    ax.text(5, 9.5, "Phase 4: Supervisor LLM 의사결정 트리",
            ha='center', va='top', color=TEXT_COLOR, fontsize=16, weight='bold')

    # Supervisor
    draw_box(ax, 3.5, 8.2, 3, 0.6, "🎯 Supervisor", PRIMARY_COLOR, TEXT_COLOR, 12, True)
    draw_arrow(ax, 5, 7.9, 5, 7.5)

    # Mode selection
    ax.text(5, 7.3, "환경변수: USE_SUPERVISOR_LLM", ha='center', va='top',
            color=TEXT_COLOR, fontsize=10, style='italic')

    # Two branches
    draw_arrow(ax, 5, 7, 2.5, 6.5, "false", BOX_COLOR)
    draw_arrow(ax, 5, 7, 7.5, 6.5, "true", PRIMARY_COLOR)

    # LEFT: Rule-based
    draw_box(ax, 0.5, 5.8, 4, 0.6, "📋 Rule-based Mode (안정)", BOX_COLOR, TEXT_COLOR, 11, True)

    draw_box(ax, 0.3, 4.9, 4.4, 0.7, "if first entry:\n  → UC1", BOX_COLOR)
    draw_box(ax, 0.3, 3.9, 4.4, 0.7, "elif UC1 failed:\n  → UC2", BOX_COLOR)
    draw_box(ax, 0.3, 2.9, 4.4, 0.7, "elif UC2 failed:\n  → END", BOX_COLOR)

    draw_arrow(ax, 2.5, 4.6, 2.5, 1.8)

    # RIGHT: LLM
    draw_box(ax, 5.5, 5.8, 4, 0.6, "🧠 LLM Mode (GPT-4o-mini)", PRIMARY_COLOR, TEXT_COLOR, 11, True)

    draw_box(ax, 5.3, 4.9, 4.4, 0.7, '"첫 진입이므로\n품질 검증 시작" → UC1', PRIMARY_COLOR)
    draw_box(ax, 5.3, 3.9, 4.4, 0.7, '"UC1 실패, heal 필요"\n→ UC2', PRIMARY_COLOR)
    draw_box(ax, 5.3, 2.9, 4.4, 0.7, '"Consensus 실패,\n사람 검토 필요" → END', PRIMARY_COLOR)

    draw_arrow(ax, 7.5, 4.6, 7.5, 1.8)

    # Converge to result
    draw_box(ax, 3.5, 1, 3, 0.6, "라우팅 결정 완료", SUCCESS_COLOR, TEXT_COLOR, 11, True)

    # Confidence note
    ax.text(7.5, 0.5, "💭 LLM: reasoning + confidence 제공",
            ha='left', va='bottom', color=PRIMARY_COLOR, fontsize=9, style='italic')

    # Current mode
    ax.text(0.5, 0.5, "현재 모드: Rule-based ✅",
            ha='left', va='bottom', color=SUCCESS_COLOR, fontsize=10, weight='bold')

    plt.tight_layout()
    output_path = OUTPUT_DIR / "supervisor_llm_tree.png"
    plt.savefig(output_path, dpi=150, facecolor=BG_COLOR, edgecolor='none', bbox_inches='tight')
    plt.close()
    print(f"✅ Supervisor 다이어그램 저장: {output_path}")

def main():
    """모든 다이어그램 생성"""
    print("=" * 60)
    print("🎨 UI 다이어그램 PNG 생성 시작")
    print("=" * 60)

    # 한글 폰트 설정 (macOS)
    plt.rcParams['font.family'] = 'AppleGothic'
    plt.rcParams['axes.unicode_minus'] = False

    create_uc1_diagram()
    create_uc2_diagram()
    create_uc3_diagram()
    create_supervisor_diagram()

    print("=" * 60)
    print("✅ 모든 다이어그램 생성 완료!")
    print(f"📁 저장 위치: {OUTPUT_DIR.absolute()}")
    print("=" * 60)

if __name__ == "__main__":
    main()
