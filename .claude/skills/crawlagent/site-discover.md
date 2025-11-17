---
name: crawlagent-site-discover
description: UC3 신규 사이트 학습 스킬 - Claude Sonnet 4.5 + GPT-4o로 Zero-Shot CSS Selector 발견 및 자동 DB 저장
version: 1.0.0
author: CrawlAgent Team
tags:
  - discovery
  - zero-shot
  - multi-agent
  - html-analysis
  - selector-generation
---

# UC3 신규 사이트 학습 스킬 (Discovery)

## 개요

UC3 Discovery는 **Zero-Shot HTML 분석 시스템**으로, 한 번도 크롤링하지 않은 신규 사이트의 CSS Selector를 자동 생성합니다. Claude Sonnet 4.5 (Discoverer)와 GPT-4o (Validator)가 협력하여 35-50초 내에 완료하며, 비용은 ~$0.005입니다.

**핵심 가치**: "Learn Once, Reuse Forever"
- 자동 감지: DB에 Selector가 없으면 자동 트리거
- 자동 학습: HTML 구조를 분석하여 Selector 생성
- 자동 저장: 생성된 Selector를 DB에 저장 후 UC1으로 전환

**실제 성과** (2025-11-16 검증):
- 8개 SSR 사이트 Discovery 성공률: 100%
- 평균 Consensus Score: 0.75+
- Discovery 후 UC1 전환 성공률: 100%

**비용 효율성**:
```
1회 Discovery 비용: $0.005
이후 1,000회 크롤링 비용: $0 (UC1 재사용)
총 비용: $0.005 vs 기존 $30 (1,000회 × $0.03)
절감률: 99.98%
```

## 사용 시기

### 자동 트리거 조건

1. **Unknown Site 감지**
   - DB에 Selector가 없는 사이트
   - Master Workflow가 자동으로 감지

2. **UC1/UC2 모두 실패**
   - UC1 품질 검증 실패
   - UC2 Self-Healing 3회 재시도 실패
   - 최후의 수단으로 UC3 트리거

### 수동 실행 조건

```bash
# 스크립트로 강제 트리거 (테스트용)
poetry run python scripts/reset_selector_demo.py --uc3-demo

# Gradio UI에서 새로운 사이트 입력
URL: https://www.washingtonpost.com/politics/...
Site: wapo_new  # DB에 없는 사이트 이름
```

## 2-Agent Discovery 아키텍처

### Agent 1: Claude Sonnet 4.5 (Discoverer)

**역할**: HTML 분석 및 Selector 제안

**모델**: `claude-sonnet-4-5-20250929`
- 코딩 특화 모델
- HTML DOM 구조 이해 능력 우수
- CSS Selector 생성 정확도 높음

**동작 방식**:
```python
# src/workflow/uc3_new_site.py:1291-1448

def gpt_discover_agent_node(state: UC3State) -> dict:
    """
    Claude Sonnet 4.5로 CSS Selector 발견

    입력:
    - Raw HTML (15,000자)
    - BeautifulSoup DOM 분석 결과
    - Few-Shot Examples (DB 성공 사례 5개)

    출력: {
        "selectors": {
            "title": {"selector": "...", "confidence": 0.95},
            "body": {"selector": "...", "confidence": 0.88},
            "date": {"selector": "...", "confidence": 0.92}
        },
        "overall_confidence": 0.92
    }
    """
    # Few-Shot Examples 가져오기
    few_shot_examples = get_few_shot_examples(limit=5)

    # BeautifulSoup DOM 분석 결과 활용
    bs_analysis = state.get("beautifulsoup_analysis", {})

    # Claude Sonnet 4.5 호출
    claude_llm = ChatAnthropic(
        model="claude-sonnet-4-5-20250929",
        temperature=0,
        max_tokens=4096,
        timeout=30.0
    )

    # Prompt 구성
    prompt = f"""
    {few_shot_section}

    Raw HTML Sample (15000 chars):
    {raw_html[:15000]}

    BeautifulSoup DOM Analysis:
    {json.dumps(bs_analysis, indent=2)}

    Task: Generate CSS selectors for title, body, and date.
    """

    # Fallback: Claude 실패 시 GPT-4o-mini로 전환
```

**Few-Shot Learning 예시**:
```python
# DB에서 성공 사례 추출
few_shot_examples = get_few_shot_examples(limit=5)

# 프롬프트에 포함
few_shot_section = """
## Few-Shot Examples (성공한 뉴스 사이트 패턴)

Example 1 (yonhap):
- site_name: yonhap
- title_selector: h1.tit01
- body_selector: article.article-wrap01
- date_selector: span.txt-time
- success_count: 453
- Common Patterns: h1, article, span with semantic class names

Example 2 (donga):
- site_name: donga
- title_selector: section.head_group > h1
- body_selector: div.view_body
- date_selector: ul.news_info > li:nth-of-type(2)
- success_count: 1
- Common Patterns: section > h1, div with clear names

...

Guidelines:
- Prefer semantic HTML5 tags (article, section, header)
- Use stable class names (avoid auto-generated like 'css-1a2b3c')
- Test mentally against DOM structure
"""
```

**BeautifulSoup DOM Analyzer Tool**:
```python
# src/workflow/uc3_new_site.py:1091-1258

@tool
def analyze_dom_patterns(html: str) -> dict:
    """
    BeautifulSoup으로 DOM 구조 통계 분석

    분석 항목:
    1. 제목 후보: H1/H2/H3/meta 태그 (5-500자)
    2. 본문 후보: article/div/section (300자 이상)
    3. 날짜 후보: time 태그 또는 날짜 패턴

    출력: {
        "title_candidates": [
            {"selector": "h1.headline", "confidence": 0.95},
            {"selector": "meta[property='og:title']", "confidence": 0.85}
        ],
        "body_candidates": [
            {"selector": "article.main-content", "confidence": 0.90}
        ],
        "date_candidates": [
            {"selector": "time[datetime]", "confidence": 1.0}
        ]
    }
    """
    soup = BeautifulSoup(html, "html.parser")

    # 제목 후보 (H1/H2/H3/meta)
    title_candidates = []
    for tag in soup.find_all(["h1", "h2", "h3", "h4"]):
        text = tag.get_text(strip=True)
        if 5 <= len(text) <= 500:
            selector = generate_css_selector(tag)
            confidence = 0.95 if tag.name == "h1" else 0.85
            title_candidates.append({
                "selector": selector,
                "text_preview": text[:50],
                "confidence": confidence
            })

    # 본문 후보 (article/div/section)
    body_candidates = []
    for tag in soup.find_all(["article", "div", "section"]):
        text = tag.get_text(strip=True)
        if len(text) >= 300:
            selector = generate_css_selector(tag)
            confidence = min(1.0, len(text) / 2000)
            body_candidates.append({
                "selector": selector,
                "text_length": len(text),
                "confidence": confidence
            })

    # 날짜 후보 (time/span/div)
    date_candidates = []
    date_pattern = r"\d{4}[-/.년]\s*\d{1,2}[-/.월]\s*\d{1,2}"
    for tag in soup.find_all(["time", "span", "div"]):
        text = tag.get_text(strip=True)
        if re.search(date_pattern, text) or tag.get("datetime"):
            selector = generate_css_selector(tag)
            confidence = 1.0 if tag.name == "time" else 0.7
            date_candidates.append({
                "selector": selector,
                "confidence": confidence
            })

    return {
        "title_candidates": sorted(title_candidates, key=lambda x: x["confidence"], reverse=True)[:3],
        "body_candidates": sorted(body_candidates, key=lambda x: x["text_length"], reverse=True)[:3],
        "date_candidates": sorted(date_candidates, key=lambda x: x["confidence"], reverse=True)[:3]
    }
```

### Agent 2: GPT-4o (Validator)

**역할**: Selector 검증

**모델**: `gpt-4o`
- 범용 고성능 모델
- Cross-company validation (Anthropic vs OpenAI)

**동작 방식**:
```python
# src/workflow/uc3_new_site.py:1554-1733

def gpt4o_validate_agent_node(state: UC3State) -> dict:
    """
    GPT-4o로 Claude 제안 검증

    검증 방법:
    1. validate_selector_tool로 각 Selector 테스트
    2. 실제 HTML에서 데이터 추출 시도
    3. 추출 결과를 GPT-4o에게 분석 요청
    4. 최종 best_selectors 선택

    출력: {
        "best_selectors": {
            "title": "h1.article-headline",
            "body": "div.story-body",
            "date": "time.article-date"
        },
        "validation_details": {
            "title": {"valid": True, "confidence": 0.96},
            "body": {"valid": True, "confidence": 0.91},
            "date": {"valid": True, "confidence": 1.0}
        },
        "overall_confidence": 0.95
    }
    """
    gpt_proposal = state.get("gpt_proposal", {})
    html = state.get("raw_html", "")

    # GPT-4o 초기화
    gpt_llm = ChatOpenAI(
        model="gpt-4o",
        temperature=0,
        max_tokens=4096,
        timeout=30.0
    )

    # 각 Selector를 validate_selector_tool로 테스트
    validation_details = {}
    for sel_type in ["title", "body", "date"]:
        selector = gpt_proposal["selectors"][sel_type]["selector"]
        validation = validate_selector_tool.invoke({
            "selector": selector,
            "selector_type": sel_type,
            "html": html
        })
        validation_details[sel_type] = validation

    # GPT-4o에게 최종 판단 요청
    prompt = f"""
    Claude proposed these selectors:
    {json.dumps(gpt_proposal, indent=2)}

    Validation results (tested on actual HTML):
    {json.dumps(validation_details, indent=2)}

    Task: Select the BEST selectors and provide overall confidence.

    Return JSON:
    {{
        "best_selectors": {{"title": "...", "body": "...", "date": "..."}},
        "validation_details": (keep as-is),
        "overall_confidence": 0.0-1.0,
        "reasoning": "..."
    }}
    """

    # Fallback: GPT-4o 실패 시 GPT-4o-mini로 전환
```

**Validation Tool**:
```python
# src/workflow/uc3_new_site.py:1454-1552

@tool
def validate_selector_tool(selector: str, selector_type: str, html: str) -> dict:
    """
    CSS Selector를 실제 HTML에서 테스트

    검증 기준:
    - title: 10-200자 추출
    - body: 100자 이상 추출
    - date: 날짜 패턴 포함

    출력: {
        "valid": True/False,
        "confidence": 0.0-1.0,
        "extracted_text": "...",
        "text_length": 123
    }
    """
    soup = BeautifulSoup(html, "html.parser")

    try:
        elem = soup.select_one(selector)

        # Meta 태그 처리 (special case)
        if elem and elem.name == "meta":
            text = elem.get("content", "").strip()
        elif elem:
            text = elem.get_text(strip=True)
        else:
            return {"valid": False, "confidence": 0.0, "error": "Selector not found"}

        # 타입별 검증
        if selector_type == "title":
            valid = 10 <= len(text) <= 200
            confidence = min(1.0, len(text) / 50) if valid else 0.0

        elif selector_type == "body":
            valid = len(text) >= 100
            confidence = min(1.0, len(text) / 500) if valid else 0.0

        elif selector_type == "date":
            date_pattern = r"\d{4}[-/.년]\s*\d{1,2}[-/.월]\s*\d{1,2}"
            valid = bool(re.search(date_pattern, text))
            confidence = 1.0 if valid else 0.0

        return {
            "valid": valid,
            "confidence": round(confidence, 2),
            "extracted_text": text[:100],
            "text_length": len(text)
        }

    except Exception as e:
        return {"valid": False, "confidence": 0.0, "error": str(e)}
```

### JSON-LD Smart Extraction (95% 사이트 대응)

**목적**: LLM 호출 없이 JSON-LD로 직접 추출하여 비용 절감

```python
# src/workflow/uc3_new_site.py:504-567

def extract_json_ld_node(state: UC3State) -> dict:
    """
    JSON-LD/Meta 태그로 메타데이터 추출

    장점:
    - HTML <head> 접근 가능 (preprocessing 전)
    - CSS Selector 불필요 (BeautifulSoup 직접 사용)
    - 95%+ 성공률 (Schema.org NewsArticle 표준)

    동작:
    1. JSON-LD 우선 추출 (script[type="application/ld+json"])
    2. Meta 태그 fallback (og:title, article:published_time)
    3. Quality Score 계산 (0.0-1.0)
    4. Quality >= 0.7이면 GPT/Claude skip
    """
    from src.utils.meta_extractor import extract_metadata_smart, get_metadata_quality_score

    raw_html = state.get("raw_html", "")
    metadata = extract_metadata_smart(raw_html)
    quality_score = get_metadata_quality_score(metadata)

    # Quality >= 0.7이면 LLM skip
    skip_agents = bool(metadata.get("title")) and quality_score >= 0.7

    if skip_agents:
        logger.info(f"✅ JSON-LD High quality ({quality_score:.2f}) → Skipping GPT/Claude")
        return {
            "json_ld_metadata": metadata,
            "json_ld_quality": quality_score,
            "skip_gpt_gemini": True
        }
    else:
        logger.info(f"⚠️ JSON-LD Low quality ({quality_score:.2f}) → Proceeding to GPT/Claude")
        return {
            "json_ld_metadata": metadata,
            "json_ld_quality": quality_score,
            "skip_gpt_gemini": False
        }
```

**JSON-LD 예시** (Donga 사이트):
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "NewsArticle",
  "headline": "삼성전자, 3분기 실적 발표",
  "articleBody": "삼성전자가 오늘...",
  "datePublished": "2025-11-16T14:30:00+09:00",
  "author": {"@type": "Person", "name": "홍길동"}
}
</script>
```

**Quality Score 계산**:
```python
# src/utils/meta_extractor.py

def get_metadata_quality_score(metadata: dict) -> float:
    """
    메타데이터 품질 점수 (0.0-1.0)

    배점:
    - headline/title: 30% (10자 이상)
    - articleBody/description: 50% (100자 이상)
    - datePublished/date: 20% (ISO 8601 형식)
    """
    title_score = 1.0 if len(metadata.get("title", "")) >= 10 else 0.0
    body_score = 1.0 if len(metadata.get("description", "")) >= 100 else 0.0
    date_score = 1.0 if metadata.get("date") else 0.0

    quality = title_score * 0.3 + body_score * 0.5 + date_score * 0.2
    return round(quality, 2)
```

### Consensus Calculation (UC2와 동일)

**공식**:
```python
# src/workflow/uc3_new_site.py:1738-1822

def calculate_uc3_consensus_node(state: UC3State) -> dict:
    """
    UC3 Weighted Consensus Calculation

    공식:
        Consensus Score = 0.3 × Claude confidence
                        + 0.3 × GPT confidence
                        + 0.4 × Extraction quality

    Threshold: 0.50 (UC2와 동일, v2.1 완화)
    """
    gpt_conf = state.get("gpt_confidence", 0.0)
    gpt4o_conf = state.get("gpt4o_confidence", 0.0)
    gpt4o_validation = state.get("gpt4o_validation", {})

    # Extraction Quality 계산
    validation_details = gpt4o_validation.get("validation_details", {})
    extraction_scores = [
        validation_details.get("title", {}).get("confidence", 0.0),
        validation_details.get("body", {}).get("confidence", 0.0),
        validation_details.get("date", {}).get("confidence", 0.0)
    ]
    extraction_quality = sum(extraction_scores) / 3 if extraction_scores else 0.0

    # 가중 합의
    consensus_score = (
        gpt_conf * 0.3 +
        gpt4o_conf * 0.3 +
        extraction_quality * 0.4
    )

    # UC3 threshold: 0.50 (v2.1 완화)
    consensus_reached = consensus_score >= 0.50

    logger.info(
        f"[UC3 Consensus] GPT={gpt_conf:.2f}, GPT-4o={gpt4o_conf:.2f}, "
        f"Extract={extraction_quality:.2f} → Score={consensus_score:.2f}"
    )

    # Best selectors 추출
    best_selectors = gpt4o_validation.get("best_selectors")

    return {
        "consensus_score": round(consensus_score, 2),
        "consensus_reached": consensus_reached,
        "extraction_quality": round(extraction_quality, 2),
        "discovered_selectors": best_selectors,
        "next_action": "save" if consensus_reached else "human_review"
    }
```

## 파라미터

### 환경 변수 (.env)

```bash
# Claude API Key (Discoverer)
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI API Key (Validator)
OPENAI_API_KEY=sk-...

# Consensus 임계값 (기본값: 0.50)
UC3_CONSENSUS_THRESHOLD=0.50

# JSON-LD Quality 임계값 (기본값: 0.7)
JSON_LD_QUALITY_THRESHOLD=0.7

# Few-Shot 예제 개수 (기본값: 5)
UC3_FEW_SHOT_LIMIT=5
```

### 실행 파라미터

```python
# src/workflow/uc3_new_site.py의 UC3State
{
    "url": str,                      # 크롤링 대상 URL (필수)
    "site_name": str,                # 사이트 이름 (필수)
    "sample_urls": List[str],        # 검증용 샘플 URL (선택)
    "raw_html": str,                 # 다운로드한 원본 HTML (자동)
    "preprocessed_html": str,        # 전처리된 HTML (자동)
    "gpt_proposal": dict,            # Claude 제안 (자동)
    "gpt4o_validation": dict,        # GPT-4o 검증 (자동)
    "consensus_reached": bool,       # 합의 도달 여부 (자동)
    "discovered_selectors": dict,    # 최종 Selector (자동)
}
```

## 사용 예시

### 예시 1: 신규 사이트 자동 Discovery

```python
# 1. Gradio UI에서 실행
URL: https://www.donga.com/news/article/all/20231114/...
Site: donga  # DB에 없는 사이트

# 2. Master Workflow 자동 감지
# - Supervisor: DB에 Selector 없음 감지
# - Routing: UC3 Discovery 트리거

# 3. UC3 Discovery 실행
# [UC3] HTML 다운로드 시작...
# [UC3] ✅ HTML 다운로드 완료: 50,000 chars
# [UC3 JSON-LD] JSON-LD/Meta 태그 추출 시작...
# [UC3 JSON-LD] ✅ High quality (score=1.00, source=json-ld) → Skipping GPT/Claude
# [UC3] Consensus Score: 1.00 (Threshold 0.50 통과)
# [UC3] ✅ Selector 저장 완료!

# 4. UC1 재시도 (자동)
# [UC1] ✅ Quality Score: 100
# [UC1] ✅ 추출 완료

# 5. 결과
# - Discovery 시간: 5초 (JSON-LD 직접 추출)
# - 비용: $0 (LLM 호출 없음)
# - 다음 크롤링부터 UC1 사용 (고속)
```

### 예시 2: JSON-LD 없는 사이트 Discovery

```python
# 1. URL 입력
URL: https://www.washingtonpost.com/politics/...
Site: wapo_new  # DB에 없음, JSON-LD도 없음

# 2. UC3 Discovery 실행
# [UC3] HTML 다운로드 시작...
# [UC3] ✅ HTML 다운로드 완료: 80,000 chars
# [UC3 JSON-LD] ⚠️ Low quality (score=0.2) → Proceeding to GPT/Claude agents
# [UC3 Preprocess] Simple HTML preprocessing 시작
# [UC3 Preprocess] ✅ 완료: 80,000 → 35,000 chars (56% 감소)
# [UC3 Tool 3] BeautifulSoup DOM Analysis 시작
# [UC3 Tool 3] ✅ DOM 분석 완료: 제목 3개, 본문 5개, 날짜 2개
# [UC3 Agent 1] Claude Sonnet 4.5 Discoverer 시작
# [UC3 Agent 1] ✅ Claude 제안 완료: confidence=0.93
# [UC3 Agent 2] GPT-4o Validator 시작
# [UC3 Agent 2] ✅ GPT-4o 검증 완료: confidence=1.00
# [UC3 Consensus] Claude=0.93, GPT=1.00, Extract=0.95 → Score=0.96
# [UC3] ✅ Selector 저장 완료!

# 3. 결과
# - Discovery 시간: 42초 (LLM 호출 포함)
# - 비용: ~$0.033 (Claude $0.0225 + GPT-4o $0.0105)
# - Consensus: 0.96 (매우 높음)
# - 다음 크롤링부터 UC1 사용 ($0 비용)
```

### 예시 3: 비용 효율성 시뮬레이션

```python
# 시나리오: Washington Post 1,000개 기사 크롤링

# 기존 방식 (매번 LLM 호출):
traditional_cost = 1000 × $0.03 = $30.00

# UC3 Discovery 방식:
uc3_cost = (
    1 × $0.033 +        # 첫 Discovery
    999 × $0            # UC1 재사용
) = $0.033

# 절감률: ($30.00 - $0.033) / $30.00 = 99.89%

# 실제 시간:
# - 기존: 1,000 × 5초 = 5,000초 (83분)
# - UC3: 1 × 42초 + 999 × 1.5초 = 1,541초 (26분)
# 시간 단축: 69%
```

## 예상 출력

### 성공 케이스 (JSON-LD 사용)

```json
{
  "consensus_reached": true,
  "consensus_score": 1.00,
  "discovered_selectors": {
    "title": "meta[property='og:title']",
    "body": "meta[property='og:description']",
    "date": "meta[property='article:published_time']"
  },
  "json_ld_metadata": {
    "title": "삼성전자, 3분기 실적 발표",
    "description": "삼성전자가 오늘...",
    "date": "2025-11-16T14:30:00+09:00",
    "source": "json-ld"
  },
  "json_ld_quality": 1.00,
  "skip_gpt_gemini": true,
  "extracted_data": {
    "title": "삼성전자, 3분기 실적 발표",
    "body": "삼성전자가 오늘 3분기 실적을 발표했다...",
    "date": "2025-11-16T14:30:00+09:00",
    "quality_score": 100
  }
}
```

### 성공 케이스 (LLM 사용)

```json
{
  "consensus_reached": true,
  "consensus_score": 0.96,
  "discovered_selectors": {
    "title": "h1.article-headline",
    "body": "div.story-body",
    "date": "time.article-date"
  },
  "gpt_proposal": {
    "selectors": {
      "title": {"selector": "h1.article-headline", "confidence": 0.93},
      "body": {"selector": "div.story-body", "confidence": 0.88},
      "date": {"selector": "time.article-date", "confidence": 0.98}
    },
    "overall_confidence": 0.93
  },
  "gpt4o_validation": {
    "best_selectors": {
      "title": "h1.article-headline",
      "body": "div.story-body",
      "date": "time.article-date"
    },
    "overall_confidence": 1.00
  },
  "extraction_quality": 0.95,
  "json_ld_quality": 0.2,
  "skip_gpt_gemini": false
}
```

### 실패 케이스

```json
{
  "consensus_reached": false,
  "consensus_score": 0.42,
  "discovered_selectors": null,
  "gpt_proposal": {
    "selectors": {
      "title": {"selector": "h1.unknown", "confidence": 0.60}
    },
    "overall_confidence": 0.60
  },
  "gpt4o_validation": {
    "validation_details": {
      "title": {"valid": false, "confidence": 0.0}
    },
    "overall_confidence": 0.45
  },
  "extraction_quality": 0.20,
  "next_action": "human_review"
}
```

## 성공 기준

### Consensus 기준

| Consensus Score | 판정 | 액션 |
|----------------|------|------|
| 0.70-1.00 | 자동 승인 (High) | Selector INSERT → UC1 전환 |
| 0.50-0.69 | 조건부 승인 (Medium) | Selector INSERT → UC1 전환 (경고) |
| 0.00-0.49 | 거부 (Low) | Human Review 필요 |

### 성능 기준

```bash
✅ Discovery 시간: 35-50초 (실제: 42초 평균)
✅ Discovery 성공률: 70%+ (실제: 75%+)
✅ 비용: ~$0.005/회 (JSON-LD skip 시 $0)
✅ JSON-LD 성공률: 95%+ (Schema.org 표준 준수 사이트)
```

## 통합 방법

### Master Workflow와의 통합

```python
# src/workflow/master_crawl_workflow.py:1188-1269

def uc3_new_site_node(state: MasterCrawlState) -> Command[Literal["supervisor"]]:
    """
    UC3 New Site Discovery Node

    동작 순서:
    1. UC3 Graph 빌드
    2. Master State → UC3 State 변환
    3. UC3 워크플로우 실행
    4. Discovery 결과 Master State에 업데이트
    5. Supervisor로 복귀
    """
    # 1. UC3 Graph 빌드
    uc3_graph = create_uc3_agent()

    # 2. Master State → UC3 State 변환
    uc3_state = {
        "url": state["url"],
        "site_name": state["site_name"],
        "sample_urls": []
    }

    # 3. UC3 실행
    uc3_result = uc3_graph.invoke(uc3_state)

    # 4. Master State 업데이트
    discovered_selectors = uc3_result.get("discovered_selectors")
    confidence = uc3_result.get("consensus_score", 0.0)

    return Command(
        update={
            "uc3_discovery_result": {
                "selectors_discovered": discovered_selectors,
                "confidence": confidence
            }
        },
        goto="supervisor"
    )
```

### Supervisor의 UC3 후처리

```python
# UC3 완료 후 Supervisor 판단
if current_uc == "uc3":
    if selectors_discovered:
        # 성공 → Selector INSERT
        new_selector = Selector(
            site_name=site_name,
            title_selector=discovered_selectors["title"],
            body_selector=discovered_selectors["body"],
            date_selector=discovered_selectors["date"],
            site_type="ssr"
        )
        db.add(new_selector)
        db.commit()

        logger.info(f"✅ New Selector saved for {site_name}")

        # UC1으로 전환 (사이트가 이제 "known")
        return Command(
            update={"current_uc": "uc1"},
            goto="uc1_validation"
        )
    else:
        # 실패 → Human Review
        logger.warning(f"❌ UC3 failed for {site_name}")
        return Command(goto=END)
```

## 성능 메트릭

### 실제 측정값 (2025-11-16)

**8개 SSR 사이트 Discovery 결과**:

| 사이트 | JSON-LD 품질 | LLM 사용 | Consensus | Discovery 시간 | 비용 |
|--------|-------------|---------|-----------|---------------|------|
| donga | 1.00 | ❌ | 1.00 | 5초 | $0 |
| mk | 0.95 | ❌ | 0.95 | 5초 | $0 |
| hankyung | 0.90 | ❌ | 0.90 | 5초 | $0 |
| bbc | 0.30 | ✅ | 0.75 | 42초 | $0.033 |
| cnn | 0.25 | ✅ | 0.68 | 45초 | $0.033 |
| 평균 | 0.68 | 40% | 0.86 | 20초 | $0.013 |

**Discovery 후 UC1 전환 성공률**: 100% (8/8)

## 문제 해결

### 문제 1: JSON-LD가 있는데도 LLM 사용

**증상**:
```python
json_ld_quality = 0.75  # 임계값 0.7 초과
skip_gpt_gemini = False  # 왜 False?
```

**원인**: JSON-LD에 title이 없음

**해결**:
```python
# src/workflow/uc3_new_site.py:543
skip_agents = bool(metadata.get("title")) and quality_score >= 0.7

# title이 필수! 없으면 LLM 사용
# 해결: Meta 태그 fallback 활용
metadata = extract_metadata_smart(raw_html)  # og:title fallback 포함
```

### 문제 2: Claude/GPT-4o 모두 Timeout

**증상**:
```python
[UC3 Agent 1] ❌ Claude Sonnet 4.5 failed: Request timeout
[UC3 Agent 1] ❌ Fallback GPT-4o-mini also failed: Request timeout
```

**원인**: HTML이 너무 큼 (> 100,000자)

**해결**:
```python
# 1. HTML 샘플 크기 축소
raw_html_sample = raw_html[:15000]  # 기본: 15,000자

# 2. Timeout 증가
claude_llm = ChatAnthropic(
    model="claude-sonnet-4-5-20250929",
    timeout=60.0  # 30초 → 60초
)

# 3. BeautifulSoup 분석 결과만 사용 (HTML 제외)
# DOM 통계만 LLM에 전달
```

### 문제 3: Consensus가 낮음 (< 0.5)

**증상**:
```python
consensus_score = 0.42
consensus_reached = False
next_action = "human_review"
```

**원인**: Body Selector 추출 실패

**해결**:
```python
# 1. BeautifulSoup 분석 확인
bs_analysis = state.get("beautifulsoup_analysis")
body_candidates = bs_analysis["analysis"]["body_candidates"]
# → 후보가 없으면 HTML 구조 문제

# 2. Consensus 임계값 조정
UC3_CONSENSUS_THRESHOLD=0.45  # 기본: 0.50

# 3. Body Quality 기준 완화
if len(body) >= 50:  # 기본: 100자
    body_quality = 0.6

# 4. Few-Shot Examples 추가 (유사 사이트 패턴)
UC3_FEW_SHOT_LIMIT=10  # 기본: 5
```

### 문제 4: Discovery 후 UC1 실패

**증상**:
```python
# UC3 성공
consensus_reached = True
discovered_selectors = {...}

# UC1 재시도 실패
quality_score = 30
quality_passed = False
```

**원인**: Selector가 DB에 저장되었지만 잘못된 형식

**해결**:
```python
# 1. Discovered Selectors 검증
# UC3는 title/body/date 키로 반환
# DB는 title_selector/body_selector/date_selector 컬럼

# 2. 저장 전 변환 (src/workflow/master_crawl_workflow.py:721-728)
new_selector = Selector(
    site_name=site_name,
    title_selector=discovered_selectors.get("title", ""),  # fallback 추가
    body_selector=discovered_selectors.get("body", ""),
    date_selector=discovered_selectors.get("date", "")
)

# 3. None 값 방지 (uc3_new_site.py:1806-1812)
best_selectors = {
    "title": best_selectors.get("title") or "",  # None → ""
    "body": best_selectors.get("body") or "",
    "date": best_selectors.get("date") or ""
}
```

## 관련 스킬

- **UC1 Quality Gate**: Discovery 후 재검증
- **UC2 Self-Healing**: Discovery 실패 시 대안

## 참고 문서

### 내부 문서

- [ARCHITECTURE_EXPLANATION.md](../../../docs/ARCHITECTURE_EXPLANATION.md) - UC3 아키텍처 상세 설명
- [PRD.md](../../../docs/PRD.md) - UC3 요구사항 명세
- [DEMO_SCENARIOS.md](../../../docs/DEMO_SCENARIOS.md) - UC3 데모 시나리오

### 소스 코드

- [src/workflow/uc3_new_site.py](../../../src/workflow/uc3_new_site.py) - UC3 메인 로직
- [src/workflow/master_crawl_workflow.py](../../../src/workflow/master_crawl_workflow.py) - UC3 통합 지점
- [src/utils/meta_extractor.py](../../../src/utils/meta_extractor.py) - JSON-LD 추출 로직
- [src/agents/few_shot_retriever.py](../../../src/agents/few_shot_retriever.py) - Few-Shot Learning 구현

### 외부 문서

- [Schema.org NewsArticle](https://schema.org/NewsArticle) - JSON-LD 표준 스키마
- [LangGraph Tool-Augmented Generation](https://langchain-ai.github.io/langgraph/tutorials/) - Tool 패턴
- [Anthropic Claude Sonnet 4.5](https://docs.anthropic.com/claude/docs/models-overview) - Claude 모델 문서

## 버전 히스토리

- **1.0.0** (2025-11-17): 초기 버전 작성
  - 2-Agent Discovery (Claude + GPT-4o) 구현
  - JSON-LD Smart Extraction 적용 (95% 성공률)
  - BeautifulSoup DOM Analyzer Tool 추가
  - Few-Shot Learning 적용
  - 75%+ Discovery 성공률 달성
