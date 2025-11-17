# CrawlAgent - Claude Skills Integration Guide

**Date**: 2025-11-17
**Claude Version**: Claude 3.5 Sonnet
**Skills Format**: 2025 YAML Frontmatter Specification

---

## Overview

This guide explains how to integrate CrawlAgent's adaptive crawling capabilities as **Claude Skills** that can be invoked directly from Claude Console or Claude Code.

### What are Claude Skills?

Claude Skills are pre-packaged capabilities that extend Claude's functionality. For CrawlAgent, we provide three skills corresponding to our three use cases:

1. **crawlagent-quality-check**: Fast rule-based validation (UC1)
2. **crawlagent-selector-heal**: Self-healing selector repair (UC2)
3. **crawlagent-site-discover**: Zero-shot site discovery (UC3)

---

## Installation Instructions

### Prerequisites
- Access to Claude Console or Claude Code
- CrawlAgent instance running (`http://localhost:7860`)
- API access credentials (if using remote deployment)

### Step 1: Create Skills Directory

In your project root, create the following structure:

```
.claude/
└── skills/
    ├── crawlagent-quality-check/
    │   └── SKILL.md
    ├── crawlagent-selector-heal/
    │   └── SKILL.md
    └── crawlagent-site-discover/
        └── SKILL.md
```

### Step 2: Copy Skill Definitions

Copy the SKILL.md files provided in the next section into their respective directories.

### Step 3: Register Skills in Claude Console

1. Open Claude Console
2. Navigate to Settings → Skills
3. Click "Import Custom Skills"
4. Select the `.claude/skills/` directory
5. Verify all three skills appear in the list

### Step 4: Test Installation

In Claude Console, type:
```
Use the crawlagent-quality-check skill to validate this URL:
https://www.yna.co.kr/view/AKR20251116034800504
```

Claude should recognize the skill and execute the validation.

---

## Skill 1: Quality Check (UC1)

### File: `.claude/skills/crawlagent-quality-check/SKILL.md`

```markdown
---
name: crawlagent-quality-check
description: Fast rule-based quality validation for known news sites using 5W1H framework
version: 1.0.0
author: CrawlAgent Team
tags: [crawling, validation, quality-check, news]
---

# CrawlAgent Quality Check Skill

## Purpose
Validates crawled content from known news sites using rule-based 5W1H (Who/What/When/Where/Why/How) framework. Provides sub-2-second validation with zero LLM costs.

## When to Use
- Validating content from known sites (Yonhap, Naver, BBC)
- Need fast quality scores without LLM overhead
- Batch validation of multiple URLs
- Production crawling pipelines

## Parameters

### Required
- `url` (string): Full URL of the news article to crawl and validate
- `site_name` (string): Site identifier (e.g., 'yonhap', 'naver', 'bbc')

### Optional
- `quality_threshold` (number): Minimum quality score (default: 80)
- `save_to_db` (boolean): Whether to save results to PostgreSQL (default: true)

## Example Usage

### Basic Validation
```
Use crawlagent-quality-check to validate:
URL: https://www.yna.co.kr/view/AKR20251116034800504
Site: yonhap
```

### With Custom Threshold
```
Check quality of https://n.news.naver.com/article/001/0014925825
Site: naver
Quality threshold: 95
```

## Expected Output

```json
{
  "status": "success",
  "quality_score": 98,
  "latency_ms": 1547,
  "extracted_content": {
    "title": "Article title here",
    "body": "Full article body...",
    "date": "2025-11-16"
  },
  "validation_details": {
    "who_present": true,
    "what_present": true,
    "when_present": true,
    "where_present": true,
    "why_present": true,
    "how_present": true
  },
  "use_case": "UC1",
  "cost_usd": 0.00
}
```

## Integration Endpoint

If using remote CrawlAgent API:
```
POST http://localhost:7860/api/validate
Content-Type: application/json

{
  "url": "https://...",
  "site_name": "yonhap",
  "quality_threshold": 80
}
```

## Success Criteria
- ✅ Quality score >= threshold
- ✅ Latency < 2 seconds
- ✅ All 5W1H components validated
- ✅ Content successfully extracted

## Troubleshooting

**Issue**: "Site not found in database"
**Solution**: Use `crawlagent-site-discover` skill first to add the site

**Issue**: "Quality score below threshold"
**Solution**: Use `crawlagent-selector-heal` skill to fix selectors

**Issue**: "HTTP 404/403 errors"
**Solution**: Verify URL is accessible and respects robots.txt
```

---

## Skill 2: Selector Heal (UC2)

### File: `.claude/skills/crawlagent-selector-heal/SKILL.md`

```markdown
---
name: crawlagent-selector-heal
description: Self-healing selector repair using 2-agent consensus (GPT-4o + Gemini)
version: 1.0.0
author: CrawlAgent Team
tags: [crawling, self-healing, ai-repair, consensus]
---

# CrawlAgent Selector Heal Skill

## Purpose
Automatically repairs broken CSS selectors when news sites change their HTML structure. Uses 2-Agent Consensus (GPT-4o Proposer + Gemini Validator) to ensure accurate selector updates.

## When to Use
- Quality scores drop below 80 after site HTML changes
- Selectors return empty/incorrect content
- Manual selector fixes needed but you want automation
- Site maintenance detected

## Parameters

### Required
- `url` (string): URL of the failing article
- `site_name` (string): Site identifier to heal

### Optional
- `consensus_threshold` (number): Minimum agreement score (default: 0.5)
- `max_retries` (number): Maximum heal attempts (default: 3)
- `save_to_db` (boolean): Auto-save healed selectors (default: true)

## Example Usage

### Basic Healing
```
Use crawlagent-selector-heal to fix selectors for:
URL: https://www.yna.co.kr/view/AKR20251116034800504
Site: yonhap
```

### With Custom Consensus
```
Heal selectors for https://n.news.naver.com/article/001/0014925825
Site: naver
Consensus threshold: 0.70
```

## Workflow

1. **Fetch HTML**: Download current page HTML
2. **GPT-4o Proposes**: Analyzes HTML, suggests new selectors
3. **Gemini Validates**: Reviews proposals, gives approval score
4. **Consensus Check**: Computes weighted agreement (0.0-1.0)
5. **DB Update**: Saves new selectors if consensus >= threshold
6. **Retry Validation**: Runs UC1 with new selectors

## Expected Output

```json
{
  "status": "healed",
  "consensus_score": 0.75,
  "latency_ms": 31742,
  "original_quality": 20,
  "healed_quality": 100,
  "new_selectors": {
    "title": ".article-head h1",
    "body": ".article-body p",
    "date": "time.published"
  },
  "agent_details": {
    "proposer": "gpt-4o",
    "validator": "gemini-2.5-pro",
    "proposer_confidence": 0.80,
    "validator_confidence": 0.70
  },
  "use_case": "UC2",
  "cost_usd": 0.002
}
```

## Integration Endpoint

```
POST http://localhost:7860/api/heal
Content-Type: application/json

{
  "url": "https://...",
  "site_name": "yonhap",
  "consensus_threshold": 0.5
}
```

## Success Criteria
- ✅ Consensus >= threshold
- ✅ Healed quality >= 95
- ✅ Selectors saved to DB
- ✅ UC1 retry succeeds

## LangSmith Observability

Every heal operation is traced in LangSmith:
- **Project**: `crawlagent-poc`
- **Trace Name**: `UC2 Self-Healing: {site_name}`
- **View**: https://smith.langchain.com/o/.../crawlagent-poc

## Cost Estimate
- GPT-4o API call: ~$0.001
- Gemini API call: ~$0.001
- **Total**: ~$0.002 per heal

## Troubleshooting

**Issue**: "Consensus below threshold"
**Solution**: Lower threshold to 0.4 or use `max_retries: 5`

**Issue**: "Both agents disagree"
**Solution**: Check if HTML is valid. May need manual selector review.

**Issue**: "Healed quality still low"
**Solution**: Site may have major structural change. Consider UC3 rediscovery.
```

---

## Skill 3: Site Discover (UC3)

### File: `.claude/skills/crawlagent-site-discover/SKILL.md`

```markdown
---
name: crawlagent-site-discover
description: Zero-shot site discovery using Claude Sonnet 4.5 HTML analysis
version: 1.0.0
author: CrawlAgent Team
tags: [crawling, discovery, zero-shot, onboarding]
---

# CrawlAgent Site Discover Skill

## Purpose
Discovers CSS selectors for completely unknown news sites using zero-shot HTML analysis. Enables instant onboarding of new sites without manual configuration.

## When to Use
- Crawling a site for the first time
- No existing selectors in database
- Rapid multi-site expansion
- Ad-hoc news collection from unfamiliar sources

## Parameters

### Required
- `url` (string): Sample article URL from the new site
- `site_name` (string): Unique identifier for the site (e.g., 'wapo', 'guardian')

### Optional
- `site_type` (string): 'ssr' or 'spa' (auto-detected if not provided)
- `consensus_threshold` (number): Min agreement score (default: 0.5)
- `validate_immediately` (boolean): Run UC1 after discovery (default: true)

## Example Usage

### Basic Discovery
```
Use crawlagent-site-discover to onboard:
URL: https://www.washingtonpost.com/politics/2025/11/...
Site name: wapo
```

### With Type Specification
```
Discover selectors for https://www.theguardian.com/world/2025/nov/...
Site name: guardian
Site type: ssr
```

## Workflow

1. **Site Check**: Verify site not in database
2. **HTML Fetch**: Download sample article
3. **Claude Analysis**: Claude Sonnet 4.5 analyzes structure (~20s)
4. **GPT Validation**: GPT-4o validates proposed selectors
5. **Consensus**: Compute agreement score
6. **DB Save**: Store discovered selectors
7. **UC1 Test**: Immediate validation with new selectors

## Expected Output

```json
{
  "status": "discovered",
  "consensus_score": 0.68,
  "latency_ms": 45230,
  "discovered_selectors": {
    "title": "h1.article-title",
    "body": "div.article-content p",
    "date": "time[datetime]"
  },
  "site_type": "ssr",
  "validation_quality": 92,
  "agent_details": {
    "discoverer": "claude-sonnet-4-5",
    "validator": "gpt-4o",
    "discoverer_confidence": 0.72,
    "validator_confidence": 0.65
  },
  "use_case": "UC3",
  "cost_usd": 0.005,
  "notes": "Site now usable via UC1 fast path"
}
```

## Integration Endpoint

```
POST http://localhost:7860/api/discover
Content-Type: application/json

{
  "url": "https://...",
  "site_name": "wapo",
  "site_type": "ssr",
  "validate_immediately": true
}
```

## Success Criteria
- ✅ All 3 selectors discovered (title, body, date)
- ✅ Consensus >= threshold
- ✅ Validation quality >= 85
- ✅ Site becomes "known" for future UC1 use

## Performance Impact
- **First crawl**: 35-50 seconds (discovery + validation)
- **Subsequent crawls**: < 2 seconds (UC1 fast path)
- **Cost**: One-time $0.005, then $0.00

## LangSmith Observability

Discovery traces are the longest and most detailed:
- **Project**: `crawlagent-poc`
- **Trace Name**: `UC3 Discovery: {site_name}`
- **Spans**: Claude analysis (longest), GPT validation, consensus calc
- **View**: https://smith.langchain.com/o/.../crawlagent-poc

## Cost Estimate
- Claude Sonnet 4.5 API: ~$0.003 (largest HTML context)
- GPT-4o validation: ~$0.002
- **Total**: ~$0.005 per discovery

## Limitations
- **SSR Only**: Phase 1 supports server-side rendered sites only
- **English/Korean**: Tested primarily on EN/KO sites
- **Article Pages**: Optimized for news articles, not homepages

## Troubleshooting

**Issue**: "Site type detection failed"
**Solution**: Manually specify `site_type: "ssr"` in parameters

**Issue**: "Low validation quality after discovery"
**Solution**: Try different sample URL or manually refine selectors

**Issue**: "Consensus below threshold"
**Solution**: Use threshold 0.4 for exploratory discovery

**Issue**: "Site is SPA (JavaScript-rendered)"
**Solution**: Phase 2 feature. Use Playwright-based SPA crawler (roadmap).
```

---

## Advanced Usage Patterns

### Chaining Skills

**Scenario**: Discover → Validate → Heal (full workflow)

```
1. Use crawlagent-site-discover for https://example.com/article1
   Site: example_news

2. If quality < 95, use crawlagent-selector-heal
   Site: example_news, URL: https://example.com/article2

3. Use crawlagent-quality-check for batch validation
   Site: example_news, URLs: [article3, article4, article5]
```

### Batch Operations

**Scenario**: Validate 100 URLs from Yonhap

```python
# Pseudocode for Claude integration
for url in urls:
    result = claude.use_skill(
        "crawlagent-quality-check",
        url=url,
        site_name="yonhap",
        quality_threshold=95
    )
    if result["quality_score"] < 95:
        heal_result = claude.use_skill(
            "crawlagent-selector-heal",
            url=url,
            site_name="yonhap"
        )
```

### Monitoring & Alerts

**Scenario**: Detect selector drift

```
Set up daily cron:
1. Use crawlagent-quality-check on sample URLs
2. If avg_quality < 90, trigger alert
3. Auto-invoke crawlagent-selector-heal
4. Log results to monitoring dashboard
```

---

## API Reference (Optional REST Integration)

If exposing CrawlAgent skills via REST API:

### Base URL
```
http://localhost:7860/api
```

### Authentication
```
X-API-Key: your-api-key-here
```

### Endpoints

#### POST /api/validate (UC1)
```json
{
  "url": "string",
  "site_name": "string",
  "quality_threshold": 80
}
```

#### POST /api/heal (UC2)
```json
{
  "url": "string",
  "site_name": "string",
  "consensus_threshold": 0.5,
  "max_retries": 3
}
```

#### POST /api/discover (UC3)
```json
{
  "url": "string",
  "site_name": "string",
  "site_type": "ssr",
  "validate_immediately": true
}
```

### Response Format (All Endpoints)
```json
{
  "status": "success|failed|healed|discovered",
  "data": { ... },
  "error": null,
  "metadata": {
    "use_case": "UC1|UC2|UC3",
    "latency_ms": 1547,
    "cost_usd": 0.002,
    "timestamp": "2025-11-17T20:00:00Z"
  }
}
```

---

## Best Practices

### 1. Prefer UC1 for Known Sites
Always use `crawlagent-quality-check` first. It's free and fast.

### 2. Set Appropriate Thresholds
- **Quality**: 80 (general), 95 (strict)
- **Consensus**: 0.5 (balanced), 0.7 (conservative)

### 3. Monitor LangSmith Traces
Check traces for:
- Unexpected routing (UC1 → UC2 frequently = selector drift)
- High consensus variance (agents disagree = HTML complexity)
- Cost spikes (too many UC2/UC3 calls)

### 4. Batch Discoveries
Discover multiple sites upfront rather than on-demand to reduce latency.

### 5. Cache Results
Store quality scores and validated URLs to avoid redundant crawls.

---

## Troubleshooting Common Issues

### Skill Not Recognized
- **Check**: Skill SKILL.md has valid YAML frontmatter
- **Check**: Directory name matches skill `name` field
- **Solution**: Reimport skills in Claude Console

### API Connection Failed
- **Check**: CrawlAgent server running on port 7860
- **Check**: Firewall/network allows connections
- **Solution**: `curl http://localhost:7860/health`

### Unexpected Routing
- **Check**: LangSmith trace to see supervisor decision
- **Reason**: Quality < threshold triggers UC2
- **Solution**: Adjust thresholds or heal selectors

### High Costs
- **Check**: UC1 usage ratio (should be 95%+)
- **Reason**: Too many UC2/UC3 calls = unstable selectors
- **Solution**: Batch heal, improve selector quality

---

## Support & Resources

### Documentation
- [Architecture Explanation](ARCHITECTURE_EXPLANATION.md)
- [Deployment Guide](DEPLOYMENT_GUIDE.md)
- [Demo Scenarios](DEMO_SCENARIOS.md)
- [PRD](PRD.md)

### LangSmith Dashboard
- **Project**: https://smith.langchain.com/o/.../crawlagent-poc
- **Filters**: By use_case, site_name, date range

### GitHub Repository
- **Issues**: Submit bugs/feature requests
- **Discussions**: Ask questions, share use cases

---

## Changelog

### v1.0.0 (2025-11-17)
- Initial release
- UC1, UC2, UC3 skills
- Gradio UI integration
- LangSmith observability

### Roadmap
- **v1.1**: SPA site support (UC3 Playwright)
- **v1.2**: Skill orchestration (auto-chaining)
- **v1.3**: Real-time monitoring dashboard

---

**Last Updated**: 2025-11-17
**Maintained By**: CrawlAgent Development Team
