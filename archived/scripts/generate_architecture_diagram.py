"""
CrawlAgent Architecture Diagram Generator v2
실제 구현을 기반으로 한 아키텍처 다이어그램 생성 (개선된 가독성)
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
import matplotlib.patheffects as path_effects

# 한글 폰트 설정
plt.rcParams['font.family'] = 'AppleGothic'
plt.rcParams['axes.unicode_minus'] = False

# Figure 생성 - GitHub Dark 테마
fig, ax = plt.subplots(1, 1, figsize=(18, 13), facecolor='#0d1117')
ax.set_xlim(0, 18)
ax.set_ylim(0, 13)
ax.axis('off')
ax.set_facecolor('#0d1117')

# 색상 팔레트 (더 선명하게)
COLORS = {
    'supervisor': '#7c3aed',
    'uc1': '#10b981',
    'uc2': '#f59e0b',
    'uc3': '#3b82f6',
    'agent': '#8b5cf6',
    'failure': '#ef4444',
    'bg': '#161b22',
    'text': '#c9d1d9',
    'border': '#30363d',
}

def draw_box(x, y, w, h, color, label, sublabels=None, alpha=0.95, border_width=2):
    """깔끔한 박스 그리기"""
    # 배경 그림자
    shadow = FancyBboxPatch((x+0.05, y-0.05), w, h, boxstyle="round,pad=0.15",
                           facecolor='black', alpha=0.3, zorder=1)
    ax.add_patch(shadow)

    # 메인 박스
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.15",
                        facecolor=color, edgecolor='white',
                        linewidth=border_width, alpha=alpha, zorder=2)
    ax.add_patch(box)

    # 라벨
    txt = ax.text(x + w/2, y + h - 0.3, label, ha='center', va='center',
                  fontsize=14, fontweight='bold', color='white', zorder=3)
    txt.set_path_effects([path_effects.withStroke(linewidth=3, foreground='black')])

    # 서브 라벨들
    if sublabels:
        y_offset = y + h - 0.7
        for sublabel in sublabels:
            txt = ax.text(x + w/2, y_offset, sublabel, ha='center', va='center',
                         fontsize=10, color='white', alpha=0.9, zorder=3)
            y_offset -= 0.25

def draw_arrow(x1, y1, x2, y2, color, style='->', width=3, curved=False):
    """화살표 그리기"""
    if curved:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle=style, mutation_scale=25,
                               linewidth=width, color=color, alpha=0.8,
                               connectionstyle="arc3,rad=0.3", zorder=2)
    else:
        arrow = FancyArrowPatch((x1, y1), (x2, y2),
                               arrowstyle=style, mutation_scale=25,
                               linewidth=width, color=color, alpha=0.8, zorder=2)
    ax.add_patch(arrow)

# ============================================================================
# 1. Title
# ============================================================================
ax.text(9, 12.5, 'CrawlAgent Architecture', ha='center', va='center',
        fontsize=28, fontweight='bold', color=COLORS['supervisor'])
ax.text(9, 12, '"Learn Once, Reuse Forever" - LangGraph Supervisor Pattern',
        ha='center', va='center', fontsize=14, style='italic', color=COLORS['text'])

# ============================================================================
# 2. Start
# ============================================================================
draw_box(7, 11, 4, 0.6, COLORS['supervisor'], 'START: URL + HTML Fetch')
draw_arrow(9, 11, 9, 10.2, COLORS['supervisor'])

# ============================================================================
# 3. Supervisor (2-Mode)
# ============================================================================
draw_box(5.5, 8.8, 7, 1.4, COLORS['supervisor'],
         'Supervisor (Intelligent Orchestration)',
         ['Mode 1: Rule-based IF/ELSE ($0)',
          'Mode 2: LLM 3-Model Voting (Optional)',
          'State Analysis + Dynamic Routing'])

draw_arrow(9, 8.8, 9, 8.2, COLORS['supervisor'])

# ============================================================================
# 4. UC1, UC2, UC3 (깔끔한 3단 구성)
# ============================================================================

# UC1 - Quality Gate
draw_box(1, 5, 4.5, 2.8, COLORS['uc1'],
         'UC1: Quality Gate',
         ['"Zero Cost, Maximum Speed"',
          '',
          'DB SELECT Selector',
          'BeautifulSoup Extract',
          'Quality >= 80 Check',
          '',
          'Success: $0, ~100ms'])

# UC2 - Self-Healing
draw_box(6.75, 5, 4.5, 2.8, COLORS['uc2'],
         'UC2: Self-Healing',
         ['"Adapt to Change"',
          '',
          '2-Agent Consensus',
          'Claude + GPT-4o',
          'DB UPDATE Selector',
          '',
          'Success: ~$0.0137'])

# UC3 - Discovery
draw_box(12.5, 5, 4.5, 2.8, COLORS['uc3'],
         'UC3: Discovery',
         ['"Invest Once, Reuse Forever"',
          '',
          'JSON-LD Optimize',
          '2-Agent Consensus',
          'DB INSERT Selector',
          '',
          'Success: ~$0.033'])

# Arrows from Supervisor to UCs
draw_arrow(7, 9, 3.25, 7.8, COLORS['uc1'], curved=True)
draw_arrow(9, 8.8, 9, 7.8, COLORS['uc2'])
draw_arrow(11, 9, 14.75, 7.8, COLORS['uc3'], curved=True)

# ============================================================================
# 5. Fallback Chain
# ============================================================================
# UC1 -> UC2
ax.text(3.25, 4.5, 'FAIL', ha='center', va='center',
        fontsize=11, fontweight='bold', color=COLORS['failure'])
draw_arrow(5.5, 6, 6.75, 6, COLORS['failure'], style='->', width=2.5)

# UC2 -> UC3
ax.text(9, 4.5, 'FAIL', ha='center', va='center',
        fontsize=11, fontweight='bold', color=COLORS['failure'])
draw_arrow(11.25, 6, 12.5, 6, COLORS['failure'], style='->', width=2.5)

# UC3 -> Failure
ax.text(14.75, 4.5, 'FAIL', ha='center', va='center',
        fontsize=11, fontweight='bold', color=COLORS['failure'])
draw_arrow(14.75, 5, 14.75, 4, COLORS['failure'], style='->', width=2.5)

# ============================================================================
# 6. Graceful Failure
# ============================================================================
draw_box(6, 3, 6, 0.7, COLORS['failure'],
         'MAX_RETRIES (3) -> Graceful Failure', alpha=0.3)

draw_arrow(14.75, 4, 12, 3.5, COLORS['failure'], curved=True, width=2.5)

# ============================================================================
# 7. 2-Agent Consensus Detail (왼쪽 하단)
# ============================================================================
# 박스 배경
consensus_bg = Rectangle((0.5, 0.3), 8, 2.3, facecolor=COLORS['bg'],
                         edgecolor=COLORS['agent'], linewidth=2, alpha=0.8)
ax.add_patch(consensus_bg)

ax.text(4.5, 2.35, '2-Agent Consensus System (UC2 & UC3)',
        ha='center', va='center', fontsize=13, fontweight='bold', color=COLORS['agent'])

# Proposer
draw_box(1.5, 1.2, 2.5, 0.7, COLORS['agent'],
         'Claude Sonnet 4.5', ['(Proposer)'], alpha=0.9, border_width=1.5)

# Validator
draw_box(5.5, 1.2, 2.5, 0.7, COLORS['uc1'],
         'GPT-4o', ['(Validator)'], alpha=0.9, border_width=1.5)

# Arrow between
draw_arrow(4, 1.55, 5.5, 1.55, 'white', style='<->', width=2)

# Formula
ax.text(4.5, 0.75, 'Consensus = 0.3×Proposer + 0.3×Validator + 0.4×Quality',
        ha='center', va='center', fontsize=10, style='italic',
        bbox=dict(boxstyle='round,pad=0.4', facecolor='white', alpha=0.15),
        color=COLORS['text'])
ax.text(4.5, 0.45, 'Threshold: UC2 >= 0.5 | UC3 >= 0.55',
        ha='center', va='center', fontsize=9, color=COLORS['text'], alpha=0.7)

# ============================================================================
# 8. Key Metrics (오른쪽 하단)
# ============================================================================
metrics_bg = Rectangle((9.5, 0.3), 8, 2.3, facecolor=COLORS['bg'],
                       edgecolor=COLORS['supervisor'], linewidth=2, alpha=0.8)
ax.add_patch(metrics_bg)

ax.text(13.5, 2.35, 'Core Metrics (459 Real Crawls)',
        ha='center', va='center', fontsize=13, fontweight='bold', color=COLORS['supervisor'])

metrics = [
    ('UC1 Cost', '$0', COLORS['uc1']),
    ('UC2 Cost', '~$0.0137', COLORS['uc2']),
    ('UC3 Cost', '~$0.033', COLORS['uc3']),
    ('UC1 Speed', '~100ms', COLORS['uc1']),
    ('Success Rate', '100%', COLORS['supervisor']),
]

y_pos = 1.8
for label, value, color in metrics:
    ax.text(10.5, y_pos, f'{label}:', ha='left', va='center',
            fontsize=11, color=COLORS['text'], alpha=0.8)
    ax.text(16.5, y_pos, value, ha='right', va='center',
            fontsize=11, fontweight='bold', color=color)
    y_pos -= 0.28

# ============================================================================
# 9. Footer
# ============================================================================
ax.text(9, 0.08, 'PostgreSQL DB | LangGraph Command API | Cross-Company Validation (Anthropic + OpenAI)',
        ha='center', va='center', fontsize=10, color=COLORS['text'], alpha=0.6, style='italic')

# ============================================================================
# Save
# ============================================================================
plt.tight_layout()
plt.savefig('/Users/charlee/Desktop/Intern/crawlagent/docs/architecture_diagram.png',
            dpi=300, bbox_inches='tight', facecolor='#0d1117', edgecolor='none')
print("✅ Architecture diagram v2 saved: docs/architecture_diagram.png")
plt.close()
