#!/usr/bin/env python3
"""
Gradio UI 빠른 테스트 스크립트

목적:
1. Tab 2 PNG 이미지 로드 확인
2. 빠른 UC 테스트 기능 확인
3. UI 정상 실행 확인
"""

import sys
sys.path.insert(0, '.')

print("=" * 60)
print("🎨 Gradio UI 테스트")
print("=" * 60)

# 1. PNG 파일 확인
print("\n📁 PNG 다이어그램 파일 확인:")
import os
ui_diagrams_path = "docs/ui_diagrams"
if os.path.exists(ui_diagrams_path):
    for filename in sorted(os.listdir(ui_diagrams_path)):
        if filename.endswith('.png'):
            filepath = os.path.join(ui_diagrams_path, filename)
            size_kb = os.path.getsize(filepath) // 1024
            print(f"  ✅ {filename} ({size_kb}KB)")
else:
    print(f"  ❌ {ui_diagrams_path} 폴더 없음")

# 2. Master workflow PNG 확인
master_png = "docs/master_workflow_graph.png"
if os.path.exists(master_png):
    size_kb = os.path.getsize(master_png) // 1024
    print(f"  ✅ master_workflow_graph.png ({size_kb}KB)")
else:
    print(f"  ❌ master_workflow_graph.png 없음")

# 3. Gradio UI 로드
print("\n🚀 Gradio UI 로드 중...")
try:
    from src.ui.app import create_app
    app = create_app()
    print("  ✅ UI 로드 성공!")
except Exception as e:
    print(f"  ❌ UI 로드 실패: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 4. 실행
print("\n🌐 Gradio UI 실행 중...")
print("=" * 60)
print("📍 URL: http://localhost:7862")
print("=" * 60)
print("\n🎯 테스트 가이드:")
print("  1. Tab 2 (AI 처리 시스템) 열기")
print("  2. PNG 이미지 5개 확인 (Master + UC1/2/3 + Supervisor)")
print("  3. Tab 1 (콘텐츠 수집) 열기")
print("  4. '빠른 UC 테스트' 섹션에서 아무 URL 테스트")
print("\n💡 Tip: 네이버 뉴스, 조선일보, 중앙일보 등 아무 URL 가능")
print("=" * 60)

app.launch(
    server_name="0.0.0.0",
    server_port=7862,
    share=False,
    show_error=True
)
