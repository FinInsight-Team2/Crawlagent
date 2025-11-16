#!/usr/bin/env python3
"""
Master Workflow 그래프 시각화 스크립트

LangGraph의 get_graph() API를 사용하여 워크플로우를 시각화합니다.

Usage:
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/visualize_master_graph.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger

from src.workflow.master_crawl_workflow import build_master_graph


def visualize_graph():
    """Master Graph를 시각화하고 이미지로 저장"""

    logger.info("Master Graph 빌드 중...")
    master_app = build_master_graph()

    # 그래프 구조 가져오기
    graph = master_app.get_graph()

    # Mermaid 다이어그램 출력 (텍스트)
    print("\n" + "=" * 80)
    print("📊 Master Workflow Graph (Mermaid Diagram)")
    print("=" * 80)
    print(graph.draw_mermaid())
    print("=" * 80 + "\n")

    # PNG 이미지로 저장 (시각화)
    try:
        logger.info("그래프를 PNG 이미지로 저장 중...")
        output_path = project_root / "docs" / "master_workflow_graph.png"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        png_data = graph.draw_mermaid_png()
        with open(output_path, "wb") as f:
            f.write(png_data)

        logger.info(f"✅ 그래프 이미지 저장 완료: {output_path}")
        print(f"\n🎨 그래프 이미지를 확인하세요: {output_path}\n")

    except Exception as e:
        logger.error(f"PNG 생성 실패 (Mermaid CLI 미설치 가능성): {e}")
        logger.info("Mermaid CLI 설치: npm install -g @mermaid-js/mermaid-cli")
        print(
            "\n💡 대신 위의 Mermaid 텍스트를 https://mermaid.live 에 붙여넣으면 시각화를 볼 수 있습니다!\n"
        )

    # 그래프 노드와 엣지 정보 출력
    print("=" * 80)
    print("📋 그래프 구조 상세")
    print("=" * 80)

    print("\n🔵 Nodes (노드):")
    for node in graph.nodes:
        print(f"  - {node}")

    print("\n🔗 Edges (엣지):")
    for edge in graph.edges:
        print(f"  - {edge}")

    print("\n" + "=" * 80 + "\n")


if __name__ == "__main__":
    visualize_graph()
