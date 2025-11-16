"""
Distributed Supervisor - SPOF 해결

3-Model Distributed Voting System:
- GPT-4o, Claude Sonnet 4.5, Gemini 2.0 Flash 병렬 실행
- Majority Voting (3개 중 2개 합의)
- Fault Tolerance (1개 실패해도 계속 동작)

Architecture:
- Layer 1: 3-Model Distributed Supervisor (이 파일)
- Layer 2: Autonomous Workers (UC1, UC2, UC3)
- Layer 3: Autonomous Re-routing (workers 스스로 UC 제안)
- Layer 4: Result Validation & Learning (DB 저장)

Created: 2025-11-14
"""

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, Literal, Optional

from loguru import logger

from src.utils.retry import retry_with_backoff

# ============================================================================
# 3-Model Supervisor
# ============================================================================


def call_gpt4o_supervisor(state: Dict[str, Any]) -> Dict[str, str]:
    """
    GPT-4o Supervisor: UC 라우팅 결정

    Args:
        state: MasterCrawlState

    Returns:
        {"decision": "uc1"|"uc2"|"uc3"|"end", "reasoning": str, "confidence": float}
    """
    from langchain_openai import ChatOpenAI

    try:
        logger.info("[GPT-4o Supervisor] 🧠 Analyzing routing decision...")

        llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.1,  # Low temperature for deterministic routing
            api_key=os.getenv("OPENAI_API_KEY"),
            timeout=10.0,
        )

        current_uc = state.get("current_uc")
        quality_passed = state.get("quality_passed", False)
        failure_count = state.get("failure_count", 0)
        uc1_result = state.get("uc1_validation_result")
        uc2_result = state.get("uc2_consensus_result")
        uc3_result = state.get("uc3_discovery_result")

        # Prompt for routing decision
        prompt = f"""You are a routing supervisor for a multi-agent web crawler system.

Current State:
- current_uc: {current_uc}
- quality_passed: {quality_passed}
- failure_count: {failure_count}
- UC1 result: {uc1_result is not None}
- UC2 result: {uc2_result is not None}
- UC3 result: {uc3_result is not None}

Routing Rules:
1. If current_uc is None → Route to UC1 (Quality Validation)
2. If UC1 passed (quality_passed=True) → Route to END (save to DB)
3. If UC1 failed (quality_passed=False):
   - If failure_count < 3 and Selector exists → Route to UC2 (Self-Healing)
   - If failure_count >= 3 or no Selector → Route to UC3 (Discovery)
4. If UC2 succeeded → Route to UC1 (retry with fixed Selector)
5. If UC2 failed → Route to UC3 (Discovery)
6. If UC3 succeeded → Route to END (save discovered Selector)
7. If UC3 failed → Route to END (terminal failure)

Based on the current state, decide the next UC.

Return JSON:
{{
    "decision": "uc1"|"uc2"|"uc3"|"end",
    "reasoning": "brief explanation (1-2 sentences)",
    "confidence": 0.0-1.0
}}
"""

        response = llm.invoke([{"role": "user", "content": prompt}])

        # Parse JSON
        import json
        import re

        content = response.content

        # Extract JSON from code block if present
        if "```json" in content:
            json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        result = json.loads(content)

        logger.info(
            f"[GPT-4o Supervisor] ✅ Decision: {result['decision']} (conf={result['confidence']:.2f})"
        )

        return {
            "decision": result["decision"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "model": "gpt-4o",
        }

    except Exception as e:
        logger.error(f"[GPT-4o Supervisor] ❌ Error: {e}")
        return {
            "decision": "error",
            "reasoning": f"GPT-4o supervisor error: {str(e)}",
            "confidence": 0.0,
            "model": "gpt-4o",
        }


def call_claude_supervisor(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Claude Sonnet 4.5 Supervisor: UC 라우팅 결정

    Returns:
        {"decision": "uc1"|"uc2"|"uc3"|"end", "reasoning": str, "confidence": float}
    """
    from langchain_anthropic import ChatAnthropic

    try:
        logger.info("[Claude Supervisor] 🧠 Analyzing routing decision...")

        llm = ChatAnthropic(
            model="claude-sonnet-4-5-20250929",
            temperature=0.1,
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            max_tokens=1024,
            timeout=10.0,
        )

        current_uc = state.get("current_uc")
        quality_passed = state.get("quality_passed", False)
        failure_count = state.get("failure_count", 0)
        uc1_result = state.get("uc1_validation_result")
        uc2_result = state.get("uc2_consensus_result")
        uc3_result = state.get("uc3_discovery_result")

        # Same prompt as GPT-4o for consistency
        prompt = f"""You are a routing supervisor for a multi-agent web crawler system.

Current State:
- current_uc: {current_uc}
- quality_passed: {quality_passed}
- failure_count: {failure_count}
- UC1 result: {uc1_result is not None}
- UC2 result: {uc2_result is not None}
- UC3 result: {uc3_result is not None}

Routing Rules:
1. If current_uc is None → Route to UC1 (Quality Validation)
2. If UC1 passed (quality_passed=True) → Route to END (save to DB)
3. If UC1 failed (quality_passed=False):
   - If failure_count < 3 and Selector exists → Route to UC2 (Self-Healing)
   - If failure_count >= 3 or no Selector → Route to UC3 (Discovery)
4. If UC2 succeeded → Route to UC1 (retry with fixed Selector)
5. If UC2 failed → Route to UC3 (Discovery)
6. If UC3 succeeded → Route to END (save discovered Selector)
7. If UC3 failed → Route to END (terminal failure)

Based on the current state, decide the next UC.

Return JSON:
{{
    "decision": "uc1"|"uc2"|"uc3"|"end",
    "reasoning": "brief explanation (1-2 sentences)",
    "confidence": 0.0-1.0
}}
"""

        response = llm.invoke([{"role": "user", "content": prompt}])

        # Parse JSON
        import json
        import re

        content = response.content

        # Extract JSON from code block if present
        if "```json" in content:
            json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        result = json.loads(content)

        logger.info(
            f"[Claude Supervisor] ✅ Decision: {result['decision']} (conf={result['confidence']:.2f})"
        )

        return {
            "decision": result["decision"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "model": "claude-sonnet-4.5",
        }

    except Exception as e:
        logger.error(f"[Claude Supervisor] ❌ Error: {e}")
        return {
            "decision": "error",
            "reasoning": f"Claude supervisor error: {str(e)}",
            "confidence": 0.0,
            "model": "claude-sonnet-4.5",
        }


def call_gemini_supervisor(state: Dict[str, Any]) -> Dict[str, str]:
    """
    Gemini 2.0 Flash Supervisor: UC 라우팅 결정

    Returns:
        {"decision": "uc1"|"uc2"|"uc3"|"end", "reasoning": str, "confidence": float}
    """
    from langchain_google_genai import ChatGoogleGenerativeAI

    try:
        logger.info("[Gemini Supervisor] 🧠 Analyzing routing decision...")

        # Try primary key first, fallback to backup
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY_BACKUP")

        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp", temperature=0.1, google_api_key=api_key, timeout=10.0
        )

        current_uc = state.get("current_uc")
        quality_passed = state.get("quality_passed", False)
        failure_count = state.get("failure_count", 0)
        uc1_result = state.get("uc1_validation_result")
        uc2_result = state.get("uc2_consensus_result")
        uc3_result = state.get("uc3_discovery_result")

        # Same prompt for consistency
        prompt = f"""You are a routing supervisor for a multi-agent web crawler system.

Current State:
- current_uc: {current_uc}
- quality_passed: {quality_passed}
- failure_count: {failure_count}
- UC1 result: {uc1_result is not None}
- UC2 result: {uc2_result is not None}
- UC3 result: {uc3_result is not None}

Routing Rules:
1. If current_uc is None → Route to UC1 (Quality Validation)
2. If UC1 passed (quality_passed=True) → Route to END (save to DB)
3. If UC1 failed (quality_passed=False):
   - If failure_count < 3 and Selector exists → Route to UC2 (Self-Healing)
   - If failure_count >= 3 or no Selector → Route to UC3 (Discovery)
4. If UC2 succeeded → Route to UC1 (retry with fixed Selector)
5. If UC2 failed → Route to UC3 (Discovery)
6. If UC3 succeeded → Route to END (save discovered Selector)
7. If UC3 failed → Route to END (terminal failure)

Based on the current state, decide the next UC.

Return JSON:
{{
    "decision": "uc1"|"uc2"|"uc3"|"end",
    "reasoning": "brief explanation (1-2 sentences)",
    "confidence": 0.0-1.0
}}
"""

        response = llm.invoke([{"role": "user", "content": prompt}])

        # Parse JSON
        import json
        import re

        content = response.content

        # Extract JSON from code block if present
        if "```json" in content:
            json_match = re.search(r"```json\n(.*?)\n```", content, re.DOTALL)
            if json_match:
                content = json_match.group(1)

        result = json.loads(content)

        logger.info(
            f"[Gemini Supervisor] ✅ Decision: {result['decision']} (conf={result['confidence']:.2f})"
        )

        return {
            "decision": result["decision"],
            "reasoning": result["reasoning"],
            "confidence": result["confidence"],
            "model": "gemini-2.0-flash",
        }

    except Exception as e:
        logger.error(f"[Gemini Supervisor] ❌ Error: {e}")
        return {
            "decision": "error",
            "reasoning": f"Gemini supervisor error: {str(e)}",
            "confidence": 0.0,
            "model": "gemini-2.0-flash",
        }


# ============================================================================
# Majority Voting
# ============================================================================


def majority_vote(decisions: list[Dict[str, Any]]) -> Dict[str, Any]:
    """
    3-Model Majority Voting

    Args:
        decisions: List of 3 decisions from GPT-4o, Claude, Gemini

    Returns:
        {
            "final_decision": str,
            "consensus_confidence": float,
            "individual_results": list,
            "fault_tolerance": bool
        }
    """
    from collections import Counter

    logger.info("[Majority Vote] 🗳️  Analyzing 3 supervisor decisions...")

    # 유효한 결정만 필터링 (error 제외)
    valid_decisions = [d for d in decisions if d["decision"] != "error"]

    # 1개 이상 실패 시 → Fault Tolerance 활성화
    fault_tolerance = len(valid_decisions) < 3

    if len(valid_decisions) == 0:
        # 모두 실패 → 보수적 전략: UC3로 라우팅
        logger.error("[Majority Vote] ❌ All supervisors failed → Conservative route to UC3")
        return {
            "final_decision": "uc3",
            "consensus_confidence": 0.0,
            "individual_results": decisions,
            "fault_tolerance": True,
            "reason": "All supervisors failed, routing to UC3 (conservative)",
        }

    # 2개 실패 시 → 1개만 성공 → 해당 모델 결정 수용
    if len(valid_decisions) == 1:
        single_decision = valid_decisions[0]
        logger.warning(
            f"[Majority Vote] ⚠️ Only 1 supervisor succeeded → Using {single_decision['model']} decision: {single_decision['decision']}"
        )
        return {
            "final_decision": single_decision["decision"],
            "consensus_confidence": single_decision["confidence"],
            "individual_results": decisions,
            "fault_tolerance": True,
            "reason": f"Only {single_decision['model']} succeeded, using its decision",
        }

    # 2개 이상 성공 → Majority Voting
    decision_counts = Counter([d["decision"] for d in valid_decisions])
    most_common_decision, count = decision_counts.most_common(1)[0]

    # 합의 신뢰도 계산: 다수결 비율 * 평균 신뢰도
    majority_ratio = count / len(valid_decisions)

    # 다수결 결정을 한 모델들의 평균 신뢰도
    majority_confidences = [
        d["confidence"] for d in valid_decisions if d["decision"] == most_common_decision
    ]
    avg_confidence = sum(majority_confidences) / len(majority_confidences)

    consensus_confidence = majority_ratio * avg_confidence

    logger.info(
        f"[Majority Vote] ✅ Decision: {most_common_decision} ({count}/{len(valid_decisions)} votes, conf={consensus_confidence:.2f})"
    )

    return {
        "final_decision": most_common_decision,
        "consensus_confidence": consensus_confidence,
        "individual_results": decisions,
        "fault_tolerance": fault_tolerance,
        "reason": f"{count}/{len(valid_decisions)} supervisors agreed on {most_common_decision}",
    }


# ============================================================================
# Main Distributed Supervisor
# ============================================================================


def distributed_supervisor_decision(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Distributed Supervisor: 3-Model Parallel Voting

    Args:
        state: MasterCrawlState

    Returns:
        {
            "next_uc": "uc1"|"uc2"|"uc3"|"end",
            "confidence": float,
            "reasoning": str,
            "fault_tolerance_used": bool
        }
    """
    logger.info("[Distributed Supervisor] 🚀 Starting 3-Model Parallel Voting...")

    # Parallel execution with ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all 3 supervisor calls in parallel
        future_to_model = {
            executor.submit(call_gpt4o_supervisor, state): "gpt-4o",
            executor.submit(call_claude_supervisor, state): "claude",
            executor.submit(call_gemini_supervisor, state): "gemini",
        }

        decisions = []

        # Collect results as they complete
        for future in as_completed(future_to_model):
            model_name = future_to_model[future]
            try:
                decision = future.result(timeout=15)  # 15s timeout per model
                decisions.append(decision)
                logger.info(
                    f"[Distributed Supervisor] ✅ {model_name} completed: {decision['decision']}"
                )
            except Exception as e:
                logger.error(f"[Distributed Supervisor] ❌ {model_name} failed: {e}")
                decisions.append(
                    {
                        "decision": "error",
                        "reasoning": f"{model_name} failed: {str(e)}",
                        "confidence": 0.0,
                        "model": model_name,
                    }
                )

    # Majority voting
    vote_result = majority_vote(decisions)

    logger.info(
        f"[Distributed Supervisor] 🏁 Final Decision: {vote_result['final_decision']} (conf={vote_result['consensus_confidence']:.2f}, FT={vote_result['fault_tolerance']})"
    )

    return {
        "next_uc": vote_result["final_decision"],
        "confidence": vote_result["consensus_confidence"],
        "reasoning": vote_result["reason"],
        "fault_tolerance_used": vote_result["fault_tolerance"],
        "individual_votes": vote_result["individual_results"],
    }
