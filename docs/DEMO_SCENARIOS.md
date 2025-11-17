# CrawlAgent Demo Scenarios

**Date**: 2025-11-17
**Version**: 1.0
**Purpose**: Comprehensive demonstration scenarios for UC1/UC2/UC3 workflows

---

## Overview

This document provides three detailed demonstration scenarios showcasing CrawlAgent's adaptive multi-agent crawling capabilities:

1. **Demo 1**: UC1 Quality Gate (Happy Path)
2. **Demo 2**: UC2 Self-Healing (Auto-Recovery)
3. **Demo 3**: UC3 Discovery (New Site Onboarding)

Each scenario includes setup instructions, expected behavior, success metrics, and LangSmith observability.

---

## Demo 1: UC1 Quality Gate - Happy Path

### Objective
Demonstrate fast, rule-based quality validation for known sites with correct selectors.

### Prerequisites
- Gradio UI running (`http://localhost:7860`)
- PostgreSQL with existing selectors for Yonhap
- LangSmith tracking enabled

### Steps

1. **Navigate to UI**
   - Open Gradio UI: `http://localhost:7860`
   - Go to "실시간 크롤링" tab

2. **Input Configuration**
   - URL: `https://www.yna.co.kr/view/AKR20251116034800504`
   - Site: `yonhap`
   - Click "🚀 크롤링 시작"

3. **Expected Workflow**
   ```
   Supervisor → UC1 Validation → SUCCESS
   ```

4. **Expected Results**
   - **Duration**: < 2 seconds
   - **Quality Score**: 95-100 (5W1H based)
   - **Workflow History**: `['supervisor → uc1_validation', 'uc1 → end']`
   - **Extracted Content**:
     - Title: Full article title extracted
     - Body: Multi-paragraph body content
     - Date: ISO 8601 formatted date

5. **Success Metrics**
   ```
   ✅ Latency: < 2s
   ✅ Quality: >= 95
   ✅ Mode: UC1 (no LLM calls)
   ✅ Cost: $0.00 (rule-based only)
   ✅ LangSmith: Traced in crawlagent-poc project
   ```

6. **Verification Steps**
   - Check Gradio output for green success message
   - Verify quality score >= 95
   - Confirm no UC2/UC3 triggers
   - Open LangSmith: `https://smith.langchain.com/o/.../crawlagent-poc`
   - Verify trace shows UC1-only path

### Demo Script (5 minutes)

> **Presenter**: "CrawlAgent's UC1 Quality Gate validates known sites with incredible speed. Watch as we crawl a Yonhap article..."
>
> **[Action]**: Enter URL and click start
>
> **Presenter**: "Notice the sub-2-second completion. UC1 uses rule-based validation with our 5W1H framework - no LLM calls needed. This gives us 100% cost efficiency for stable sites."
>
> **[Show]**: Quality score of 98/100, extracted content with perfect formatting
>
> **Presenter**: "Every crawl is traced in LangSmith, giving us full observability into the decision-making process."

---

## Demo 2: UC2 Self-Healing - Auto-Recovery

### Objective
Demonstrate automatic selector healing when quality drops below threshold.

### Prerequisites
- Yonhap selector in DB (verified working)
- Test URL that will fail with current selector
- LangSmith tracking enabled

### Steps

1. **Setup - Corrupt Selector** (Pre-demo)
   ```python
   from src.storage.database import get_db
   from src.storage.models import Selector

   db = next(get_db())
   selector = db.query(Selector).filter(Selector.site_name == 'yonhap').first()

   # Save original
   original_title = selector.title_selector

   # Corrupt selector
   selector.title_selector = '.wrong-selector'
   db.commit()
   ```

2. **Run Crawl**
   - URL: `https://www.yna.co.kr/view/AKR20251116034800504`
   - Site: `yonhap`
   - Click "🚀 크롤링 시작"

3. **Expected Workflow**
   ```
   Supervisor → UC1 Validation → FAIL (quality 20)
   → Supervisor → UC2 Self-Healing
   → GPT-4o Proposer → Gemini Validator
   → Consensus Reached (0.75)
   → Selector Updated in DB
   → Supervisor → UC1 Re-validation → SUCCESS (quality 100)
   ```

4. **Expected Results**
   - **Duration**: 25-35 seconds (includes LLM calls)
   - **Initial Quality**: 20-40 (missing title)
   - **UC2 Trigger**: Automatic
   - **2-Agent Consensus**: 0.70-0.80
   - **Final Quality**: 95-100 (healed)
   - **Workflow History**:
     ```
     ['supervisor → uc1_validation',
      'uc1 → supervisor (quality_failed)',
      'supervisor → uc2_self_heal',
      'uc2 → supervisor (healed)',
      'supervisor → uc1_validation',
      'uc1 → end']
     ```

5. **Success Metrics**
   ```
   ✅ Auto-Recovery: Yes
   ✅ Consensus: >= 0.5
   ✅ Selector Updated: Yes
   ✅ Final Quality: >= 95
   ✅ LLM Calls: GPT-4o + Gemini (2 providers)
   ✅ Cost: ~$0.002 per heal
   ```

6. **Verification Steps**
   - Observe initial failure message
   - Watch UC2 trigger automatically
   - See "2-Agent Consensus" logs
   - Verify selector update in DB
   - Confirm retry succeeds with quality 100
   - Check LangSmith for full trace:
     - GPT-4o analysis span
     - Gemini validation span
     - Consensus calculation span

### Demo Script (8 minutes)

> **Presenter**: "Now let's see CrawlAgent's killer feature - self-healing. I've intentionally broken the Yonhap selector..."
>
> **[Action]**: Run crawl, show initial failure (quality 20)
>
> **Presenter**: "UC1 caught the failure. Now watch CrawlAgent automatically trigger UC2..."
>
> **[Show]**: UC2 activation, GPT-4o proposing new selectors
>
> **Presenter**: "GPT-4o analyzed the HTML and proposed new selectors. Now Gemini validates them..."
>
> **[Show]**: Gemini validation, consensus score 0.75
>
> **Presenter**: "Both agents agreed with 75% confidence. The selector is automatically saved to the database..."
>
> **[Show]**: DB update confirmation
>
> **Presenter**: "...and UC1 retries immediately. Perfect 100 quality score. The system healed itself in 31 seconds without human intervention."
>
> **[Show LangSmith]**: Complete trace showing GPT → Gemini → Consensus → Retry path

---

## Demo 3: UC3 Discovery - New Site Onboarding

### Objective
Demonstrate zero-shot selector discovery for completely unknown sites.

### Prerequisites
- Site NOT in database (e.g., 'washington_post')
- Valid article URL
- LangSmith tracking enabled

### Steps

1. **Identify New Site**
   - Choose a news site not in DB
   - Example: Washington Post, Guardian, etc.
   - Prepare valid article URL

2. **Run Discovery**
   - URL: `https://www.washingtonpost.com/politics/...`
   - Site: `wapo_new` (new identifier)
   - Click "🚀 크롤링 시작"

3. **Expected Workflow**
   ```
   Supervisor → Check DB → Site Not Found
   → Supervisor → UC3 Discovery
   → Claude Sonnet 4.5 Discovery → Selector Proposed
   → GPT-4o Validation
   → Consensus Reached (0.68)
   → Selector Saved to DB
   → Supervisor → UC1 Validation → SUCCESS
   ```

4. **Expected Results**
   - **Duration**: 35-50 seconds (LLM-intensive)
   - **UC3 Trigger**: Automatic (new site detected)
   - **Discovery Model**: Claude Sonnet 4.5
   - **Validation Model**: GPT-4o
   - **Consensus**: >= 0.5
   - **Selectors Discovered**:
     - Title: CSS selector
     - Body: CSS selector
     - Date: CSS selector
   - **Site Type**: 'ssr' or 'spa' (auto-detected)
   - **Final Quality**: 85-100

5. **Success Metrics**
   ```
   ✅ Zero-Shot Discovery: Yes
   ✅ Selectors Generated: 3/3
   ✅ Consensus: >= 0.5
   ✅ Saved to DB: Yes
   ✅ Immediate Usability: Yes
   ✅ LLM Calls: Claude + GPT-4o
   ✅ Cost: ~$0.005 per discovery
   ```

6. **Verification Steps**
   - Observe "Site not found in DB" trigger
   - Watch UC3 Discovery phase
   - See Claude's HTML analysis
   - Verify GPT-4o validation
   - Confirm selector save to DB
   - Check that site is now "known"
   - Run second crawl - should use UC1 (fast path)
   - LangSmith verification:
     - Claude discovery span (longest)
     - GPT validation span
     - Consensus logic span

### Demo Script (10 minutes)

> **Presenter**: "Finally, UC3 Discovery - the most impressive feature. Let's crawl a site CrawlAgent has never seen before..."
>
> **[Action]**: Enter Washington Post URL with 'wapo_new' site name
>
> **Presenter**: "CrawlAgent checks the database... site not found. UC3 Discovery activates."
>
> **[Show]**: Supervisor routing to UC3
>
> **Presenter**: "Claude Sonnet 4.5 analyzes the raw HTML, understanding the site structure..."
>
> **[Show]**: Claude discovery process (takes ~20s)
>
> **Presenter**: "Claude proposes three selectors - title, body, date. Now GPT-4o validates them..."
>
> **[Show]**: GPT validation, consensus 0.68
>
> **Presenter**: "68% consensus - good enough! Selectors saved to database. Now let's verify..."
>
> **[Show]**: Extracted content with quality 92
>
> **Presenter**: "92 quality on first try for a brand new site! Let's run it again..."
>
> **[Action]**: Same URL, click start
>
> **Presenter**: "Notice the difference? This time it completed in 1.5 seconds using UC1. The site is now 'known.' One-time discovery cost, perpetual fast performance."
>
> **[Show LangSmith]**: Compare first run (UC3, 45s) vs second run (UC1, 1.5s)

---

## Common Demo Tips

### Pre-Demo Checklist
- [ ] Start Docker services (`make start`)
- [ ] Verify Gradio UI accessible
- [ ] Check PostgreSQL connection
- [ ] Confirm LangSmith API key
- [ ] Test one crawl to warm up
- [ ] Have backup URLs ready
- [ ] Open LangSmith dashboard
- [ ] Clear old log files (optional)

### Handling Issues

**Issue: Slow network response**
- Pre-cache HTML content
- Use local test server
- Have screenshots ready

**Issue: LLM API timeout**
- Increase timeout in config
- Have recorded demo ready
- Show LangSmith historical traces

**Issue: Quality score unexpected**
- Explain 5W1H validation logic
- Show raw HTML in debug mode
- Demonstrate selector adjustment

### Presentation Flow

**Recommended Order**:
1. Start with UC1 (fast, impressive)
2. UC2 (show resilience)
3. UC3 (wow factor - discovery)

**Timing**: 25-30 minutes total
- UC1: 5 min
- UC2: 8 min
- UC3: 10 min
- Q&A: 7 min

---

## Success Criteria Summary

### UC1 (Quality Gate)
- ✅ Latency: < 2 seconds
- ✅ Quality: >= 95
- ✅ Cost: $0.00
- ✅ Success Rate: 98%+

### UC2 (Self-Healing)
- ✅ Auto-trigger: < 5 seconds after failure
- ✅ Consensus: >= 0.5
- ✅ Heal Success: 85%+
- ✅ Cost: ~$0.002 per heal

### UC3 (Discovery)
- ✅ Zero-shot discovery: Yes
- ✅ Consensus: >= 0.5
- ✅ Immediate usability: Yes
- ✅ Cost: ~$0.005 per discovery

---

## LangSmith Observability

### What to Show

**For Each Demo**:
1. **Trace Timeline**: Visual workflow path
2. **LLM Calls**: Token usage, latency
3. **Decision Points**: Supervisor reasoning
4. **Consensus Calculation**: Multi-agent agreement
5. **Cost Attribution**: Per-use-case breakdown

**Key Metrics**:
- Total tokens (input + output)
- Latency breakdown
- Model comparisons (GPT vs Claude vs Gemini)
- Success/failure rates

### Demo URLs
- **LangSmith Project**: `https://smith.langchain.com/o/.../crawlagent-poc`
- **Filters**:
  - By Use Case: `metadata.use_case=uc1|uc2|uc3`
  - By Site: `metadata.site_name=yonhap`
  - By Date: Last 24 hours

---

## Troubleshooting During Demo

### Scenario: UC1 fails unexpectedly
**Action**: Immediately pivot to UC2 demo - "This is actually perfect! Watch how UC2 handles this..."

### Scenario: LLM timeout
**Action**: Show LangSmith historical trace - "Here's what normally happens..."

### Scenario: Network issues
**Action**: Use pre-recorded demo video or screenshots

### Scenario: Audience skepticism on accuracy
**Action**: Show raw HTML vs extracted content side-by-side in debug mode

---

## Post-Demo Q&A Preparation

### Expected Questions

**Q**: "How do you handle JavaScript-rendered content?"
**A**: "Currently SSR only (UC1 has SPA detection). Phase 2 adds Playwright for SPA sites."

**Q**: "What's the cost at scale?"
**A**: "UC1 is $0. UC2/UC3 ~$0.002-0.005 per heal/discovery. After discovery, sites use UC1 (free)."

**Q**: "Can it handle non-English sites?"
**A**: "Yes - selectors are language-agnostic CSS. Currently tested on Korean, English, Japanese sites."

**Q**: "How do you ensure quality?"
**A**: "5W1H validation checks for Who/What/When/Where/Why + How. Configurable threshold (default 80)."

**Q**: "What about rate limiting?"
**A**: "Respects robots.txt. Configurable delays. Phase 2 adds distributed rate limiting."

**Q**: "Multi-tenancy support?"
**A**: "Single-tenant currently. Phase 2 roadmap includes multi-tenant architecture with isolated DBs."

---

## Demo Recording Checklist

If recording for async presentation:

- [ ] Screen resolution: 1920x1080
- [ ] Font size: 16pt minimum
- [ ] Remove sensitive API keys from .env
- [ ] Disable desktop notifications
- [ ] Use presenter mode (cursor highlight)
- [ ] Record audio with clear mic
- [ ] Show LangSmith dashboard
- [ ] Include terminal logs
- [ ] Add timestamps overlay
- [ ] Export in MP4 format

---

## Appendix: Test URLs

### Yonhap (UC1 Happy Path)
```
https://www.yna.co.kr/view/AKR20251116034800504
https://www.yna.co.kr/view/AKR20251116035700504
```

### Naver (UC1)
```
https://n.news.naver.com/article/001/0014925825
```

### BBC (UC1)
```
https://www.bbc.com/news/articles/...
```

### New Sites (UC3 Discovery)
```
Washington Post: https://www.washingtonpost.com/politics/2025/11/...
The Guardian: https://www.theguardian.com/world/2025/nov/...
CNN: https://www.cnn.com/2025/11/17/...
```

---

**Document Owner**: CrawlAgent Development Team
**Last Updated**: 2025-11-17
**Review Schedule**: Before each major presentation
