# UC2 DOM Recovery Agent Development Skill

## Context
You are developing UC2 (DOM Recovery Agent) for the CrawlAgent project - a self-healing web crawler that automatically recovers from website structure changes.

## Project Location
**Working Directory**: `/Users/charlee/Desktop/Intern/crawlagent`

## Key Files to Know

### Core Implementation Files
- `src/agents/gpt_analyzer.py`: GPT-4o Analyzer (to be created)
  - Analyzes HTML and generates CSS Selector candidates
  - Uses Structured Output with Pydantic models
  - Returns 3 selector candidates with confidence scores

- `src/agents/gemini_validator.py`: Gemini Validator (to be created)
  - Validates GPT's selector candidates
  - Tests selectors against 10 sample articles
  - Returns validation score (0-100) and valid flag

- `src/workflow/uc2_recovery.py`: LangGraph StateGraph (to be created)
  - Orchestrates the 2-agent consensus workflow
  - Implements conditional routing based on consensus
  - Handles retry logic (max 3 attempts)

### Supporting Files
- `src/storage/models.py`: SQLAlchemy ORM models (existing)
  - Selector: CSS selector storage
  - CrawlResult: Crawl results
  - DecisionLog: 2-agent consensus logs (JSONB)

- `src/workflow/uc1_validation.py`: UC1 Validation Agent (existing)
  - Quality scoring (5W1H journalism standard)
  - Routes to UC2 when quality_score < 80

### Documentation
- `docs/crawlagent/PRD-2-TECHNICAL-SPEC.md`: Technical specification
  - Lines 121-151: UC2 workflow details
  - 2-Agent consensus requirements

- `docs/crawlagent/UC2-DEVELOPMENT-MASTERPLAN.md`: Complete implementation plan
  - All HITL decision points
  - State design, agent prompts, test cases

## UC2 Workflow Overview

```
UC1 (quality_score < 80) → UC2 Recovery
    ↓
1. fetch_raw_html (Scrapy)
    ↓
2. gpt_analyze (GPT-4o)
   - Input: Raw HTML
   - Output: 3 selector candidates + confidence
    ↓
3. gemini_validate (Gemini 2.5 Flash)
   - Input: Selector candidates
   - Output: validation_score + valid flag
    ↓
4. check_consensus
   - Condition: GPT confidence ≥ 0.7 AND Gemini valid=true
    ↓
    ├─ Success → save_selector (DB update) → recrawl (UC1)
    └─ Failure → retry (max 3) → HITL (human intervention)
```

## Critical Requirements

### GPT-4o Analyzer
- Model: `gpt-4o` (latest)
- Input: HTML (preprocessed - main tags only, 50-80% token reduction)
- Output: Pydantic model with Structured Output
  ```python
  class SelectorCandidate(BaseModel):
      title_selector: str
      body_selector: str
      date_selector: str
      confidence: float  # 0.0 ~ 1.0

  class GPTAnalysis(BaseModel):
      candidates: List[SelectorCandidate]  # 3 candidates
      reasoning: str
  ```

### Gemini Validator
- Model: `gemini-2.0-flash-exp` or `gemini-1.5-pro`
- Validation method: Extract 10 samples per candidate
- Success criteria: 80% valid (8/10) + rule-based checks
  - Title: >= 10 chars
  - Body: >= 50 chars per snippet
  - Date: Contains date pattern (regex)

### Consensus Logic
- **Success**: GPT confidence ≥ 0.7 AND Gemini valid=true
- **Failure**: retry_count < 3 → retry with failure reason
- **HITL**: retry_count ≥ 3 → save to decision_logs for manual review

## Code Patterns to Follow

### LangGraph StateGraph Pattern
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class UC2State(TypedDict):
    url: str
    site_name: str
    raw_html: str
    gpt_analysis: dict
    gemini_validation: dict
    consensus_reached: bool
    retry_count: int
    # ... more fields

# Build graph
graph = StateGraph(UC2State)
graph.add_node("fetch_html", fetch_html_node)
graph.add_node("gpt_analyze", gpt_analyze_node)
graph.add_node("gemini_validate", gemini_validate_node)
# ... conditional edges
```

### Pydantic Structured Output
```python
from pydantic import BaseModel
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(model="gpt-4o")
structured_llm = llm.with_structured_output(GPTAnalysis)
result = structured_llm.invoke(prompt)
```

### Database Operations
```python
from src.storage.database import get_db
from src.storage.models import Selector, DecisionLog

db = next(get_db())
try:
    # Update selector
    selector = db.query(Selector).filter_by(site_name="yonhap").first()
    selector.title_selector = new_selector

    # Save decision log
    log = DecisionLog(
        url=url,
        site_name=site_name,
        gpt_analysis=gpt_result,
        gemini_validation=gemini_result,
        consensus_reached=True
    )
    db.add(log)
    db.commit()
finally:
    db.close()
```

## Testing Strategy

### Phase 1: Controlled Testing
- **Method**: Intentionally break existing selector (yonhap)
- **Expected**: UC2 should recover original selector
- **Success Criteria**: Generated selector matches original

### Phase 2: Real-World Testing
- **Method**: Add new site (e.g., CNN, Reuters)
- **Expected**: UC2 generates working selector from scratch
- **Success Criteria**: quality_score ≥ 80 after UC2

## Common Pitfalls to Avoid

1. **Token Limits**: Don't send full HTML to GPT (preprocess first)
2. **Retry Loops**: Always check retry_count to prevent infinite loops
3. **Session Management**: Always use try/finally for DB sessions
4. **Consensus Logic**: Use AND not OR (both agents must agree)
5. **JSONB Format**: Ensure gpt_analysis/gemini_validation are valid JSON

## Quick Commands

```bash
# Run UC2 workflow test
poetry run python -m src.workflow.uc2_recovery

# Test GPT analyzer only
poetry run python -m src.agents.gpt_analyzer

# Test Gemini validator only
poetry run python -m src.agents.gemini_validator

# Check decision logs
poetry run python -c "from src.storage.database import get_db; from src.storage.models import DecisionLog; db=next(get_db()); print(db.query(DecisionLog).all())"
```

## Development Order

1. **State Design** (1h): Define `UC2State` TypedDict
2. **GPT Analyzer** (3h): HTML preprocessing + Structured Output
3. **Gemini Validator** (2h): Sample extraction + validation rules
4. **Consensus Logic** (1h): Conditional routing + retry
5. **DB Integration** (1h): Update selectors + save logs
6. **Testing** (2h): Controlled + real-world tests

**Total**: ~10 hours for UC2 core implementation

## References

- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- OpenAI Structured Outputs: https://platform.openai.com/docs/guides/structured-outputs
- Gemini API: https://ai.google.dev/docs
- PRD-2 (Lines 121-151): UC2 technical details
- UC2 Masterplan: Complete implementation guide
