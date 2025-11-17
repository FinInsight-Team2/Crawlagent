#!/usr/bin/env python3
"""
CrawlAgent 워크플로우 상세 다이어그램 생성 스크립트

Master Graph + UC1/UC2/UC3 각각의 상세 흐름도를 Mermaid 형식으로 생성합니다.

Usage:
    cd /Users/charlee/Desktop/Intern/crawlagent
    PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python scripts/generate_workflow_diagrams.py
"""

import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Create docs/workflow_diagrams directory
output_dir = project_root / "docs" / "workflow_diagrams"
output_dir.mkdir(parents=True, exist_ok=True)

print(f"📁 Output directory: {output_dir}\n")


# ============================================================================
# 1. Master Workflow Detailed (Already created by visualize_master_graph.py)
# ============================================================================

print("=" * 80)
print("1️⃣  Master Workflow (이미 생성됨)")
print("=" * 80)
print(f"✅ 파일: {project_root}/docs/master_workflow_graph.png")
print("✅ 위치: Gradio UI Tab 2에서 확인 가능\n")


# ============================================================================
# 2. UC1 State Flow Diagram
# ============================================================================

print("=" * 80)
print("2️⃣  UC1 Quality Gate - State Flow")
print("=" * 80)

uc1_mermaid = """
graph TD
    Start([URL 입력]) --> FetchHTML[HTML 다운로드]
    FetchHTML --> GetSelector{DB에 Selector<br/>존재?}

    GetSelector -->|Yes| ExtractFields[CSS Selector로<br/>Title/Body/Date 추출]
    GetSelector -->|No| TriggerUC3[UC3 Discovery<br/>트리거]

    ExtractFields --> Calculate5W1H[5W1H 품질 점수 계산]

    Calculate5W1H --> ScoreBreakdown[점수 분해:<br/>Title: 20<br/>Body: 60<br/>Date: 10<br/>URL: 10]

    ScoreBreakdown --> QualityCheck{품질 점수<br/>≥ 80?}

    QualityCheck -->|Yes ✅| SaveDB[DB 저장]
    QualityCheck -->|No ❌| TriggerUC2[UC2 Self-Healing<br/>트리거]

    SaveDB --> End([성공])
    TriggerUC3 --> End2([UC3로 전환])
    TriggerUC2 --> End3([UC2로 전환])

    style Start fill:#10b981
    style End fill:#10b981
    style SaveDB fill:#3b82f6
    style TriggerUC2 fill:#f59e0b
    style TriggerUC3 fill:#8b5cf6
"""

uc1_output = output_dir / "uc1_state_flow.mmd"
with open(uc1_output, "w") as f:
    f.write(uc1_mermaid)

print(f"✅ 생성 완료: {uc1_output}")
print(f"🌐 시각화: https://mermaid.live 에서 확인 가능\n")


# ============================================================================
# 3. UC2 Consensus Flow Diagram
# ============================================================================

print("=" * 80)
print("3️⃣  UC2 Self-Healing - 2-Agent Consensus")
print("=" * 80)

uc2_mermaid = """
graph TD
    Start([UC1 실패<br/>품질 < 80]) --> LoadFewShot[Few-Shot Examples<br/>DB에서 로드]

    LoadFewShot --> GPTProposer[Agent 1: GPT-4o Proposer<br/>Few-Shot + HTML 분석]

    GPTProposer --> ProposeSelectors[새로운 CSS Selector 제안<br/>+ Confidence Score]

    ProposeSelectors --> TestSelectors[제안된 Selector로<br/>실제 HTML 테스트]

    TestSelectors --> GeminiValidator[Agent 2: Gemini-2.5-pro Validator<br/>추출 결과 검증]

    GeminiValidator --> CalcConsensus[Consensus Score 계산<br/>= GPT × 0.3<br/>+ Gemini × 0.3<br/>+ Extraction × 0.4]

    CalcConsensus --> ConsensusCheck{Consensus<br/>≥ 0.5?}

    ConsensusCheck -->|Yes ✅| UpdateDB[DB Selector 업데이트]
    ConsensusCheck -->|No ❌| RetryCheck{재시도<br/>< 3회?}

    RetryCheck -->|Yes| GPTProposer
    RetryCheck -->|No| TriggerUC3[UC3 Discovery<br/>트리거]

    UpdateDB --> RetryUC1[UC1 재시도<br/>새 Selector로]

    RetryUC1 --> Success([성공])
    TriggerUC3 --> End2([UC3로 전환])

    style Start fill:#f59e0b
    style Success fill:#10b981
    style GPTProposer fill:#3b82f6
    style GeminiValidator fill:#8b5cf6
    style UpdateDB fill:#10b981
"""

uc2_output = output_dir / "uc2_consensus_flow.mmd"
with open(uc2_output, "w") as f:
    f.write(uc2_mermaid)

print(f"✅ 생성 완료: {uc2_output}")
print(f"🌐 시각화: https://mermaid.live 에서 확인 가능\n")


# ============================================================================
# 4. UC3 Discovery Flow Diagram
# ============================================================================

print("=" * 80)
print("4️⃣  UC3 New Site Discovery - 3-Tool + 2-Agent")
print("=" * 80)

uc3_mermaid = """
graph TD
    Start([신규 사이트<br/>URL 입력]) --> FetchHTML[HTML 다운로드]

    FetchHTML --> Preprocess[Tool 1: preprocess_html<br/>Script/Style 제거<br/>Token 50-80% 감소]

    Preprocess --> DOMAnalyze[Tool 2: BeautifulSoup<br/>DOM 통계 분석<br/>Title/Body/Date 후보 추출]

    DOMAnalyze --> LoadFewShot[Tool 3: Few-Shot Retriever<br/>DB 성공 패턴 로드]

    LoadFewShot --> GPTDiscover[Agent 1: GPT-4o Discoverer<br/>DOM 분석 + Few-Shot 학습<br/>→ CSS Selector 제안]

    GPTDiscover --> ValidateTools[실제 HTML에서<br/>Selector 테스트]

    ValidateTools --> GeminiValidator[Agent 2: Gemini-2.5-pro<br/>추출 결과 검증<br/>Best Selectors 선택]

    GeminiValidator --> CalcConsensus[Consensus Score 계산<br/>= GPT × 0.3<br/>+ Gemini × 0.3<br/>+ Extraction × 0.4]

    CalcConsensus --> ConsensusCheck{Consensus<br/>≥ 0.55?}

    ConsensusCheck -->|Yes ✅| SaveNewSite[DB에 신규 사이트 등록<br/>Selector 저장]
    ConsensusCheck -->|No ❌| ManualReview[수동 검토 필요<br/>DecisionLog 기록]

    SaveNewSite --> RetryUC1[UC1로 재시도<br/>이제 알려진 사이트]

    RetryUC1 --> Success([성공])
    ManualReview --> End2([실패 - 수동 확인])

    style Start fill:#8b5cf6
    style Success fill:#10b981
    style Preprocess fill:#3b82f6
    style DOMAnalyze fill:#3b82f6
    style LoadFewShot fill:#3b82f6
    style GPTDiscover fill:#8b5cf6
    style GeminiValidator fill:#f59e0b
    style SaveNewSite fill:#10b981
"""

uc3_output = output_dir / "uc3_discovery_flow.mmd"
with open(uc3_output, "w") as f:
    f.write(uc3_mermaid)

print(f"✅ 생성 완료: {uc3_output}")
print(f"🌐 시각화: https://mermaid.live 에서 확인 가능\n")


# ============================================================================
# 5. Tool Calling Sequence Diagram
# ============================================================================

print("=" * 80)
print("5️⃣  Tool Calling Sequence (UC3 상세)")
print("=" * 80)

tool_calling_mermaid = """
sequenceDiagram
    participant User
    participant UC3 as UC3 Workflow
    participant Tool1 as preprocess_html
    participant Tool2 as analyze_dom_patterns
    participant Tool3 as get_few_shot_examples
    participant GPT as GPT-4o Discoverer
    participant ValidTool as validate_selector_tool
    participant Gemini as Gemini-2.5-pro

    User->>UC3: 신규 사이트 URL
    UC3->>UC3: fetch_html_node()

    UC3->>Tool1: HTML 전처리
    Tool1-->>UC3: 정제된 HTML<br/>(Token 50-80% 감소)

    UC3->>Tool2: DOM 통계 분석
    Tool2-->>UC3: Title/Body/Date 후보<br/>(각 Top 3)

    UC3->>Tool3: Few-Shot 검색
    Tool3-->>UC3: 5개 성공 패턴

    UC3->>GPT: DOM 분석 + Few-Shot<br/>→ Selector 제안
    GPT-->>UC3: CSS Selectors<br/>+ Confidence

    UC3->>ValidTool: 제안된 Selector 테스트
    ValidTool-->>UC3: 추출 결과<br/>+ Quality Score

    UC3->>Gemini: 추출 결과 검증<br/>+ Best Selector 선택
    Gemini-->>UC3: Validation Result<br/>+ Consensus

    alt Consensus ≥ 0.55
        UC3->>UC3: DB 저장
        UC3-->>User: ✅ 성공
    else Consensus < 0.55
        UC3-->>User: ❌ 실패<br/>(수동 검토 필요)
    end
"""

tool_output = output_dir / "tool_calling_sequence.mmd"
with open(tool_output, "w") as f:
    f.write(tool_calling_mermaid)

print(f"✅ 생성 완료: {tool_output}")
print(f"🌐 시각화: https://mermaid.live 에서 확인 가능\n")


# ============================================================================
# 6. Emergent Learning Loop
# ============================================================================

print("=" * 80)
print("6️⃣  Emergent Learning Loop (Few-Shot 학습)")
print("=" * 80)

emergent_mermaid = """
graph TD
    Start([신규 사이트<br/>크롤링 성공]) --> SaveDB[DB에 Selector 저장<br/>+ Success Pattern]

    SaveDB --> BuildPool[Few-Shot Examples Pool<br/>누적 증가]

    BuildPool --> NextRequest[다음 요청<br/>신규 사이트 또는 UC2]

    NextRequest --> Retrieve[Few-Shot Retriever<br/>유사 패턴 검색<br/>최대 5개]

    Retrieve --> EnrichPrompt[GPT/Gemini 프롬프트<br/>Few-Shot Examples 포함]

    EnrichPrompt --> BetterAccuracy[정확도 향상<br/>+10-20%]

    BetterAccuracy --> MoreSuccess[더 많은 성공]

    MoreSuccess --> SaveDB

    style Start fill:#10b981
    style BuildPool fill:#3b82f6
    style BetterAccuracy fill:#f59e0b
    style MoreSuccess fill:#10b981

    Note1[자가 개선 루프:<br/>성공 → 패턴 저장 → 학습 → 정확도 향상 → 더 많은 성공]

    BuildPool -.-> Note1
"""

emergent_output = output_dir / "emergent_learning_loop.mmd"
with open(emergent_output, "w") as f:
    f.write(emergent_mermaid)

print(f"✅ 생성 완료: {emergent_output}")
print(f"🌐 시각화: https://mermaid.live 에서 확인 가능\n")


# ============================================================================
# Summary
# ============================================================================

print("=" * 80)
print("📊 생성 완료 요약")
print("=" * 80)
print(
    f"""
✅ 총 6개 다이어그램 생성:

1. Master Workflow (PNG): /docs/master_workflow_graph.png
2. UC1 State Flow (Mermaid): {output_dir}/uc1_state_flow.mmd
3. UC2 Consensus (Mermaid): {output_dir}/uc2_consensus_flow.mmd
4. UC3 Discovery (Mermaid): {output_dir}/uc3_discovery_flow.mmd
5. Tool Calling Sequence (Mermaid): {output_dir}/tool_calling_sequence.mmd
6. Emergent Learning Loop (Mermaid): {output_dir}/emergent_learning_loop.mmd

🌐 Mermaid 파일 시각화 방법:
   1. https://mermaid.live 방문
   2. .mmd 파일 내용 복사/붙여넣기
   3. PNG로 다운로드

💡 Gradio UI에서 확인:
   - Tab 2: AI 아키텍처 설명
   - "전체 워크플로우 구조 보기" Accordion
"""
)
