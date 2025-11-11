"""
LangGraph Interactive Visualization Component
Created: 2025-11-04

목적:
- Plotly를 사용한 LangGraph UC1 워크플로우 시각화
- 인터랙티브 노드/엣지, 툴팁, 줌/팬 지원
- 다크 테마 호환 (#1a1b1e 배경)
"""

import plotly.graph_objects as go
from typing import Dict, List, Tuple


# ============================================================
# Node/Edge 정의
# ============================================================

NODE_INFO = {
    "START": {
        "label": "START",
        "description": "Scrapy crawling begins",
        "color": "#667eea",
        "icon": "🚀",
        "type": "start",
        "state_changes": []
    },
    "extract_fields": {
        "label": "Extract Fields",
        "description": "Read title, body, date from state",
        "color": "#3b82f6",
        "icon": "📥",
        "type": "node",
        "state_changes": []
    },
    "calculate_quality": {
        "label": "Calculate Quality",
        "description": "5W1H scoring (Title:20, Body:60, Date:10, URL:10)",
        "color": "#10b981",
        "icon": "🧮",
        "type": "node",
        "state_changes": ["quality_score", "missing_fields"]
    },
    "decide_action": {
        "label": "Decide Action",
        "description": "Determine next action based on quality score",
        "color": "#f59e0b",
        "icon": "⚡",
        "type": "decision",
        "hitl_point": True,
        "state_changes": ["next_action"],
        "routing_logic": "quality ≥80 → save | <80+Selector → heal | <80+NoSelector → new_site"
    },
    "save": {
        "label": "SAVE",
        "description": "Save to database (quality ≥80)",
        "color": "#10b981",
        "icon": "💾",
        "type": "end",
        "state_changes": []
    },
    "heal": {
        "label": "HEAL (UC2)",
        "description": "Trigger UC2 Self-Healing (DOM recovery)",
        "color": "#17a2b8",
        "icon": "🔄",
        "type": "end",
        "state_changes": []
    },
    "new_site": {
        "label": "NEW_SITE (UC3)",
        "description": "Trigger UC3 New Site Creation",
        "color": "#6c757d",
        "icon": "🆕",
        "type": "end",
        "state_changes": []
    }
}

EDGES = [
    {"from": "START", "to": "extract_fields", "type": "sequential", "label": ""},
    {"from": "extract_fields", "to": "calculate_quality", "type": "sequential", "label": ""},
    {"from": "calculate_quality", "to": "decide_action", "type": "sequential", "label": ""},
    {"from": "decide_action", "to": "save", "type": "conditional", "label": "quality ≥80"},
    {"from": "decide_action", "to": "heal", "type": "conditional", "label": "quality <80<br>+ Selector"},
    {"from": "decide_action", "to": "new_site", "type": "conditional", "label": "quality <80<br>+ No Selector"}
]


# ============================================================
# 그래프 레이아웃 계산
# ============================================================

def calculate_layout() -> Dict[str, Tuple[float, float]]:
    """
    Hierarchical layout 계산 (top-to-bottom)

    Returns:
        Dict[node_name, (x, y)] - 노드별 좌표
    """
    # Level 정의 (수동 설정으로 더 예쁘게)
    levels = {
        "START": 0,
        "extract_fields": 1,
        "calculate_quality": 2,
        "decide_action": 3,
        "save": 4,
        "heal": 4,
        "new_site": 4
    }

    # 같은 레벨 내 x 좌표
    x_positions = {
        "START": 0,
        "extract_fields": 0,
        "calculate_quality": 0,
        "decide_action": 0,
        "save": -1.5,
        "heal": 0,
        "new_site": 1.5
    }

    pos = {}
    for node_name, level in levels.items():
        x = x_positions[node_name]
        y = -level  # 위에서 아래로
        pos[node_name] = (x, y)

    return pos


# ============================================================
# Plotly Figure 생성
# ============================================================

def create_langgraph_figure() -> go.Figure:
    """
    LangGraph UC1 워크플로우의 인터랙티브 Plotly Figure 생성

    Returns:
        plotly.graph_objects.Figure
    """
    pos = calculate_layout()

    # ========================================
    # Edge Traces (화살표)
    # ========================================
    edge_traces = []
    edge_label_traces = []

    for edge in EDGES:
        x0, y0 = pos[edge["from"]]
        x1, y1 = pos[edge["to"]]

        # Edge color
        if edge["type"] == "sequential":
            color = "#9ca3af"
            width = 3
        else:  # conditional
            # Conditional edges have color based on target node
            color = NODE_INFO[edge["to"]]["color"]
            width = 4

        # Edge trace (line)
        edge_trace = go.Scatter(
            x=[x0, x1],
            y=[y0, y1],
            mode="lines",
            line=dict(color=color, width=width),
            hoverinfo="skip",
            showlegend=False
        )
        edge_traces.append(edge_trace)

        # Arrow head (annotation으로 추가)
        # 중간 지점에 label 추가
        if edge["label"]:
            mid_x = (x0 + x1) / 2
            mid_y = (y0 + y1) / 2

            # Offset for conditional branches
            if edge["type"] == "conditional":
                # 좌우로 살짝 이동
                if edge["to"] == "save":
                    mid_x -= 0.3
                elif edge["to"] == "new_site":
                    mid_x += 0.3

            label_trace = go.Scatter(
                x=[mid_x],
                y=[mid_y],
                mode="text",
                text=[edge["label"]],
                textfont=dict(size=10, color="#e5e7eb"),
                hoverinfo="skip",
                showlegend=False
            )
            edge_label_traces.append(label_trace)

    # ========================================
    # Node Traces (노드)
    # ========================================
    node_x = []
    node_y = []
    node_colors = []
    node_sizes = []
    node_text = []
    node_hover = []

    for node_name, (x, y) in pos.items():
        info = NODE_INFO[node_name]

        node_x.append(x)
        node_y.append(y)
        node_colors.append(info["color"])

        # Node size
        if info["type"] == "start":
            node_sizes.append(50)
        else:
            node_sizes.append(40)

        # Node label (with icon)
        label = f"{info['icon']}<br>{info['label']}"
        node_text.append(label)

        # Hover tooltip
        hover_text = f"<b>{info['label']}</b><br>"
        hover_text += f"<i>{info['description']}</i><br><br>"
        hover_text += f"<b>Type:</b> {info['type']}<br>"

        if info.get("state_changes"):
            hover_text += f"<b>Updates:</b> {', '.join(info['state_changes'])}<br>"

        if info.get("hitl_point"):
            hover_text += f"<b>⚠️ HITL:</b> Can interrupt here<br>"

        if info.get("routing_logic"):
            hover_text += f"<b>Routing:</b> {info['routing_logic']}<br>"

        node_hover.append(hover_text)

    node_trace = go.Scatter(
        x=node_x,
        y=node_y,
        mode="markers+text",
        marker=dict(
            size=node_sizes,
            color=node_colors,
            line=dict(color="#e5e7eb", width=2)
        ),
        text=node_text,
        textposition="middle center",
        textfont=dict(size=11, color="#ffffff", family="Arial Black"),
        hovertemplate="%{customdata}<extra></extra>",
        customdata=node_hover,
        showlegend=False
    )

    # ========================================
    # Figure 구성
    # ========================================
    fig = go.Figure(data=[*edge_traces, *edge_label_traces, node_trace])

    # Layout 설정 (다크 테마, 반응형)
    fig.update_layout(
        title={
            "text": "🧠 LangGraph UC1 Validation Workflow",
            "font": {"size": 20, "color": "#e5e7eb", "family": "Inter"},
            "x": 0.5,
            "xanchor": "center"
        },
        paper_bgcolor="#1a1b1e",
        plot_bgcolor="#2d2e32",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-2.5, 2.5]
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[-5, 0.5]
        ),
        height=700,        # 600 → 700 (더 높게)
        autosize=True,     # 반응형
        hovermode="closest",
        margin=dict(t=80, b=60, l=60, r=60)  # 여백 조정
    )

    # Arrow annotations (화살표 방향 표시)
    annotations = []
    for edge in EDGES:
        x0, y0 = pos[edge["from"]]
        x1, y1 = pos[edge["to"]]

        # Edge color
        if edge["type"] == "sequential":
            color = "#9ca3af"
        else:
            color = NODE_INFO[edge["to"]]["color"]

        annotations.append(
            dict(
                ax=x0, ay=y0,
                x=x1, y=y1,
                xref="x", yref="y",
                axref="x", ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1.5,
                arrowwidth=2,
                arrowcolor=color,
                opacity=0.8
            )
        )

    fig.update_layout(annotations=annotations)

    return fig


# ============================================================
# Validation State 설명 (사이드패널용)
# ============================================================

def get_state_description() -> str:
    """
    ValidationState 구조 설명 (Markdown)
    """
    return """
### 📦 ValidationState Structure

```python
class ValidationState(TypedDict):
    # Input (from crawling)
    url: str
    site_name: str
    title: Optional[str]
    body: Optional[str]
    date: Optional[str]

    # Validation results
    quality_score: int          # 0-100
    missing_fields: List[str]

    # Next action decision
    next_action: Literal["save", "heal", "new_site"]
```

**Quality Scoring (5W1H):**
- **Title**: 20 points (≥10 characters)
- **Body**: 60 points (≥500 chars = full, ≥200 chars = 30 points)
- **Date**: 10 points (exists)
- **URL**: 10 points (starts with http)

**Routing Logic:**
- `quality_score ≥ 80` → **SAVE** (save to database)
- `quality_score < 80` + Selector exists → **HEAL** (UC2 Self-Healing)
- `quality_score < 80` + No Selector → **NEW_SITE** (UC3 New Site)

**Human-in-the-Loop (HITL):**
- Can interrupt before `decide_action` node
- Modify state and resume execution
"""


# ============================================================
# Export to PNG (버튼용)
# ============================================================

def export_figure_to_png(fig: go.Figure, filepath: str = "langgraph_uc1.png") -> str:
    """
    Plotly Figure를 PNG로 저장

    Args:
        fig: Plotly Figure
        filepath: 저장 경로

    Returns:
        성공/실패 메시지
    """
    try:
        fig.write_image(filepath, width=1200, height=900, scale=2)
        return f"✅ Saved to {filepath}"
    except Exception as e:
        return f"❌ Export failed: {str(e)}\nTip: Install kaleido (pip install kaleido)"
