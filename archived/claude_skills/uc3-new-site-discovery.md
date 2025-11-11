# UC3 New Site Auto-Discovery Skill

## Context
You are developing UC3 (New Site Auto-Discovery) for the CrawlAgent project - an AI-powered system that automatically analyzes new news websites and generates CSS selectors without manual configuration.

## Project Location
**Working Directory**: `/Users/charlee/Desktop/Intern/crawlagent`

## Key Files to Know

### Core Implementation Files
- `src/workflow/uc3_new_site.py`: UC3 LangGraph StateGraph (to be created)
  - Orchestrates new site analysis workflow
  - Fetches HTML, analyzes structure, generates selectors
  - Uses Claude Sonnet 4.5 for intelligent DOM analysis
  - Returns validated CSS selectors ready for production

- `src/agents/claude_site_analyzer.py`: Claude Site Analyzer (to be created)
  - Analyzes news site HTML structure
  - Identifies article title, body, date patterns
  - Generates CSS selectors using DOM understanding
  - Returns structured selector proposal

### Supporting Files
- `src/storage/models.py`: SQLAlchemy ORM models (existing)
  - Selector: CSS selector storage
  - CrawlResult: Crawl results
  - DecisionLog: Analysis logs

- `src/workflow/uc1_validation.py`: UC1 Validation Agent (existing)
  - Used to validate UC3-generated selectors
  - Quality scoring (5W1H journalism standard)

- `src/workflow/uc2_hitl.py`: UC2 HITL Workflow (existing)
  - Fallback if UC3 selector needs refinement
  - 2-Agent consensus (GPT + Gemini)

### Documentation
- `docs/crawlagent/PRD-2-TECHNICAL-SPEC.md`: Technical specification
  - UC3 requirements and workflow

## UC3 Workflow Overview

```
User Input: New site URL
    ↓
1. fetch_site_html
   - Input: URL (single article or homepage)
   - Output: Raw HTML
    ↓
2. claude_analyze_structure
   - Input: Raw HTML
   - Output: Selector proposal (title, body, date, metadata)
    ↓
3. validate_selectors
   - Input: Selectors + sample URLs (3-5 articles)
   - Output: Validation report (success rate, field coverage)
    ↓
4. check_quality
   - Condition: Success rate ≥ 80% AND all required fields present
    ↓
    ├─ Success → save_selector (DB) → trigger_initial_crawl
    └─ Failure → refine_selectors (UC2 fallback) OR human_review
```

## Critical Requirements

### Claude Site Analyzer
- Model: `claude-sonnet-4-5-20250929` (latest)
- Input: Preprocessed HTML (main content tags only)
- Task:
  1. Identify news article structure patterns
  2. Analyze DOM hierarchy and semantic HTML
  3. Generate CSS selectors for:
     - Title (h1, h2, or meta tags)
     - Body (article text, paragraphs)
     - Date (time tags, meta tags, or text patterns)
     - Optional: Author, category, tags
  4. Provide confidence score (0.0 ~ 1.0)

- Output: Pydantic model
  ```python
  class SiteStructureAnalysis(BaseModel):
      site_name: str
      site_type: str  # 'ssr' or 'spa'
      title_selector: str
      body_selector: str
      date_selector: str
      author_selector: Optional[str]
      category_selector: Optional[str]
      confidence: float  # 0.0 ~ 1.0
      reasoning: str  # Why these selectors?
  ```

### Selector Validation
- Method: Test selectors against 3-5 sample articles
- Success criteria:
  - Title: >= 10 chars (90%+ success rate)
  - Body: >= 500 chars (90%+ success rate)
  - Date: Valid date pattern (80%+ success rate)
- Overall threshold: 80%+ success rate

### Quality Gate
- **Success**: Success rate ≥ 80% AND confidence ≥ 0.7
- **Refinement**: 60% ≤ Success rate < 80% → UC2 fallback
- **Failure**: Success rate < 60% → Human review

## Code Patterns to Follow

### LangGraph StateGraph Pattern
```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Optional

class UC3State(TypedDict):
    url: str
    site_name: str
    raw_html: str
    sample_urls: list[str]  # 3-5 sample articles
    claude_analysis: dict
    validation_report: dict
    selectors_valid: bool
    confidence: float
    next_action: str  # 'save', 'refine', 'human_review'

# Build graph
graph = StateGraph(UC3State)
graph.add_node("fetch_html", fetch_html_node)
graph.add_node("claude_analyze", claude_analyze_node)
graph.add_node("validate_selectors", validate_selectors_node)
graph.add_node("save_selectors", save_selectors_node)
# ... conditional edges
```

### Claude Sonnet Integration
```python
from langchain_anthropic import ChatAnthropic
from pydantic import BaseModel

llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    temperature=0
)

class SiteStructureAnalysis(BaseModel):
    site_name: str
    site_type: str
    title_selector: str
    body_selector: str
    date_selector: str
    confidence: float
    reasoning: str

structured_llm = llm.with_structured_output(SiteStructureAnalysis)
result = structured_llm.invoke(prompt)
```

### HTML Preprocessing
```python
from bs4 import BeautifulSoup

def preprocess_html(raw_html: str) -> str:
    """
    Reduce HTML token count by 50-80%
    Keep only structural tags and sample content
    """
    soup = BeautifulSoup(raw_html, 'html.parser')

    # Remove non-essential tags
    for tag in soup(['script', 'style', 'svg', 'iframe', 'noscript']):
        tag.decompose()

    # Keep only main content area
    main_content = (
        soup.find('main') or
        soup.find('article') or
        soup.find('div', class_=re.compile(r'(content|article|post)'))
    )

    return str(main_content) if main_content else str(soup)
```

### Database Operations
```python
from src.storage.database import get_db
from src.storage.models import Selector

db = next(get_db())
try:
    # Check if site exists
    existing = db.query(Selector).filter_by(site_name=site_name).first()

    if existing:
        # Update existing selector
        existing.title_selector = new_selectors['title']
        existing.body_selector = new_selectors['body']
        existing.date_selector = new_selectors['date']
    else:
        # Create new selector
        selector = Selector(
            site_name=site_name,
            title_selector=new_selectors['title'],
            body_selector=new_selectors['body'],
            date_selector=new_selectors['date'],
            site_type=site_type
        )
        db.add(selector)

    db.commit()
finally:
    db.close()
```

## Prompting Strategy for Claude

### System Prompt
```
You are an expert web scraper analyzing news website structures.

Your task:
1. Analyze the provided HTML
2. Identify CSS selectors for: title, body, date
3. Prioritize semantic HTML (article, time, h1, etc.)
4. Generate robust selectors (class-based, not id-based)
5. Provide confidence score

Guidelines:
- Title: Usually h1, h2, or meta[property="og:title"]
- Body: article > p, div.content p, or main p
- Date: time[datetime], meta[property="article:published_time"], or text patterns
- Prefer stable selectors (avoid auto-generated class names like 'css-1a2b3c')
```

### User Prompt Template
```python
prompt = f"""
Analyze this news article HTML and generate CSS selectors:

Site URL: {url}
Site Name: {site_name}

HTML (preprocessed):
{preprocessed_html}

Tasks:
1. Identify the article title selector
2. Identify the article body selector (main text content)
3. Identify the publication date selector
4. Determine if this is SSR or SPA
5. Provide confidence score (0.0 - 1.0)

Return structured output with:
- title_selector
- body_selector
- date_selector
- site_type ('ssr' or 'spa')
- confidence
- reasoning (why you chose these selectors)
"""
```

## Testing Strategy

### Phase 1: Known Sites
- **Method**: Test UC3 on yonhap (known good site)
- **Expected**: Generated selectors should match existing selectors
- **Success Criteria**: 90%+ field match

### Phase 2: New Korean News Sites
- **Sites**:
  - https://www.chosun.com/economy/
  - https://www.joongang.co.kr/economy
  - https://www.hani.co.kr/arti/economy/
- **Expected**: UC3 generates working selectors
- **Success Criteria**: quality_score ≥ 80 after UC1 validation

### Phase 3: International Sites (Optional)
- **Sites**: CNN, BBC, Reuters
- **Expected**: UC3 handles different HTML structures
- **Success Criteria**: quality_score ≥ 80

## Common Pitfalls to Avoid

1. **Token Limits**: Always preprocess HTML (remove scripts, styles, etc.)
2. **Selector Fragility**: Avoid id-based selectors (prefer class or semantic tags)
3. **SPA Detection**: Check for client-side rendering (empty body, React/Vue artifacts)
4. **Date Formats**: Support multiple date patterns (ISO, Korean format, etc.)
5. **Sample URLs**: Always validate with 3-5 articles (not just 1)

## Quick Commands

```bash
# Run UC3 workflow
cd /Users/charlee/Desktop/Intern/crawlagent
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/workflow/uc3_new_site.py --url "https://www.yna.co.kr/view/AKR20251109000001001"

# Test Claude analyzer only
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/agents/claude_site_analyzer.py

# List all selectors
poetry run python -c "from src.storage.database import get_db; from src.storage.models import Selector; db=next(get_db()); [print(f'{s.site_name}: {s.title_selector}') for s in db.query(Selector).all()]"

# Test UC3 with UC1 validation
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python tests/test_uc3_new_site.py
```

## Development Order

1. **State Design** (30min): Define `UC3State` TypedDict
2. **HTML Preprocessing** (1h): Reduce HTML token count
3. **Claude Analyzer** (2h): Structured output + prompt engineering
4. **Selector Validation** (1h): Test selectors against samples
5. **Quality Gate Logic** (30min): Conditional routing
6. **DB Integration** (30min): Save new selectors
7. **Testing** (2h): Known sites + new sites
8. **UC1/UC2 Integration** (1h): Trigger validation after UC3

**Total**: ~8 hours for UC3 core implementation

## Integration with Existing Workflows

### UC3 → UC1 (Validation)
```python
# After UC3 generates selectors
from src.workflow.uc1_validation import create_uc1_validation_agent

# Save selector to DB
# Trigger crawl with new selector
# Run UC1 validation
uc1_graph = create_uc1_validation_agent()
result = uc1_graph.invoke({
    "url": sample_url,
    "site_name": site_name,
    # ... extracted data
})

if result['quality_score'] >= 80:
    logger.info("UC3 selectors validated successfully!")
else:
    logger.warning("UC3 selectors need refinement → UC2")
```

### UC3 → UC2 (Refinement)
```python
# If UC3 selectors fail validation
if quality_score < 80:
    from src.workflow.uc2_hitl import create_uc2_hitl_agent

    uc2_graph = create_uc2_hitl_agent()
    result = uc2_graph.invoke({
        "url": url,
        "site_name": site_name,
        # ... state
    })
```

## Sprint 2 Success Criteria

- [ ] Claude Skill created (this file)
- [ ] UC3 workflow implemented (`src/workflow/uc3_new_site.py`)
- [ ] Claude analyzer implemented (`src/agents/claude_site_analyzer.py`)
- [ ] HTML preprocessing function working
- [ ] Validation against 3-5 samples working
- [ ] DB integration (save new selectors)
- [ ] Test file created (`tests/test_uc3_new_site.py`)
- [ ] Tests pass for at least 2 new Korean news sites
- [ ] UC3 → UC1 integration working
- [ ] Sprint 2 completion report written

## References

- Claude Sonnet 4.5 Docs: https://docs.anthropic.com/en/docs/models-overview
- LangGraph Documentation: https://langchain-ai.github.io/langgraph/
- BeautifulSoup: https://www.crummy.com/software/BeautifulSoup/bs4/doc/
- CSS Selectors: https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Selectors
