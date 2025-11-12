"""
Few-Shot Selector Pattern Retriever

목적:
    DB에서 성공한 CSS Selector 패턴을 가져와
    UC2/UC3의 GPT Few-Shot Examples로 제공

작성일: 2025-11-12
"""

from typing import List, Dict, Optional
from loguru import logger
from src.storage.database import get_db
from src.storage.models import Selector


def get_few_shot_examples(category: str = "news", limit: int = 5) -> List[Dict]:
    """
    DB에서 성공한 selector 패턴 가져오기

    Args:
        category: "news" (뉴스 사이트만)
        limit: 최대 5개

    Returns:
        [
            {
                "site_name": "naver",
                "title_selector": "h2.media_end_head_headline span",
                "body_selector": "div#articleBodyContents",
                "date_selector": "span[data-date-time]",
                "pattern_analysis": {
                    "title_pattern": "h2 + class + nested span",
                    "body_pattern": "div + ID",
                    "date_pattern": "span + data-attribute"
                }
            },
            ...
        ]
    """
    try:
        db = next(get_db())

        # 성공 횟수가 있는 selector만 가져오기 (최근 업데이트 순)
        # is_active 필드가 없으므로 success_count > 0 사용
        selectors = db.query(Selector).filter(
            Selector.success_count > 0
        ).order_by(
            Selector.updated_at.desc()  # 최근 업데이트된 것 우선
        ).limit(limit).all()

        if not selectors:
            logger.warning("[Few-Shot] No active selectors found in DB")
            return []

        examples = []
        for sel in selectors:
            pattern_analysis = analyze_selector_pattern(sel)
            examples.append({
                "site_name": sel.site_name,
                "title_selector": sel.title_selector or "",
                "body_selector": sel.body_selector or "",
                "date_selector": sel.date_selector or "",
                "pattern_analysis": pattern_analysis
            })

        logger.info(f"[Few-Shot] Retrieved {len(examples)} examples from DB")
        return examples

    except Exception as e:
        logger.error(f"[Few-Shot] Error retrieving examples: {e}")
        return []


def analyze_selector_pattern(selector: Selector) -> Dict[str, str]:
    """
    Selector 패턴 분석

    패턴 종류:
        - ID-based: #id
        - class-based: .class
        - nested: parent > child 또는 parent child
        - attribute: [data-attr]
        - semantic: article, section, time 등 HTML5 태그
        - nth-child: :nth-of-type, :nth-child

    예시:
        "div#articleBodyContents" → "div + ID"
        "h2.title span" → "h2 + class + nested span"
        "span[data-date-time]" → "span + data-attribute"
    """
    patterns = {}

    for sel_type in ["title", "body", "date"]:
        sel_str = getattr(selector, f"{sel_type}_selector", None)
        if not sel_str:
            patterns[f"{sel_type}_pattern"] = "N/A"
            continue

        # 패턴 분석
        pattern_parts = []

        # Tag name 추출
        tag = sel_str.split("#")[0].split(".")[0].split("[")[0].split(">")[0].split(" ")[0].strip()
        if tag:
            pattern_parts.append(tag)

        # ID 체크
        if "#" in sel_str:
            pattern_parts.append("ID")

        # Class 체크
        if "." in sel_str and not sel_str.startswith("."):
            pattern_parts.append("class")

        # Data attribute 체크
        if "[data-" in sel_str:
            pattern_parts.append("data-attr")
        elif "[" in sel_str:
            pattern_parts.append("attr")

        # Nested 체크
        if ">" in sel_str:
            pattern_parts.append("direct-child")
        elif " " in sel_str and len(sel_str.split()) > 1:
            pattern_parts.append("nested")

        # nth-child 체크
        if ":nth-" in sel_str:
            pattern_parts.append("nth-child")

        # Semantic HTML5 체크
        if tag in ["article", "section", "time", "header", "footer", "nav", "aside"]:
            pattern_parts.append("semantic")

        patterns[f"{sel_type}_pattern"] = " + ".join(pattern_parts) if pattern_parts else "simple"

    return patterns


def format_few_shot_prompt(examples: List[Dict], include_patterns: bool = True) -> str:
    """
    Few-Shot Examples를 GPT Prompt 형식으로 변환

    Args:
        examples: get_few_shot_examples() 반환값
        include_patterns: 패턴 분석 포함 여부

    Returns:
        GPT Prompt에 삽입할 Few-Shot 텍스트
    """
    if not examples:
        return "No few-shot examples available.\n"

    prompt_text = "다음은 성공적으로 작동하는 뉴스 사이트 CSS Selector 패턴입니다:\n\n"

    for i, ex in enumerate(examples, 1):
        prompt_text += f"예시 {i}: {ex['site_name']}\n"
        prompt_text += f"  - 제목: {ex['title_selector']}\n"
        prompt_text += f"  - 본문: {ex['body_selector']}\n"
        prompt_text += f"  - 날짜: {ex['date_selector']}\n"

        if include_patterns and ex.get('pattern_analysis'):
            pa = ex['pattern_analysis']
            prompt_text += f"  - 패턴 분석:\n"
            prompt_text += f"    * 제목 패턴: {pa.get('title_pattern', 'N/A')}\n"
            prompt_text += f"    * 본문 패턴: {pa.get('body_pattern', 'N/A')}\n"
            prompt_text += f"    * 날짜 패턴: {pa.get('date_pattern', 'N/A')}\n"

        prompt_text += "\n"

    prompt_text += "위 패턴들을 참고하여, 유사한 구조의 selector를 찾아주세요.\n\n"
    return prompt_text


# Example usage
if __name__ == "__main__":
    # Test Few-Shot Retriever
    examples = get_few_shot_examples(limit=5)

    if examples:
        print("✅ Few-Shot Examples Retrieved:")
        for ex in examples:
            print(f"\nSite: {ex['site_name']}")
            print(f"Title: {ex['title_selector']}")
            print(f"Body: {ex['body_selector']}")
            print(f"Pattern: {ex['pattern_analysis']}")

        print("\n" + "="*80)
        print("GPT Prompt Format:")
        print("="*80)
        print(format_few_shot_prompt(examples))
    else:
        print("❌ No examples found in DB")
