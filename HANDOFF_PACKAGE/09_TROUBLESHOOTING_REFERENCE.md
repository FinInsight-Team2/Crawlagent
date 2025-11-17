# CrawlAgent PoC - 트러블슈팅 레퍼런스

**작성일**: 2025-11-18
**버전**: v1.0
**대상**: 개발자, 운영팀

---

## 📋 목차

1. [Issue #1: UC2 Infinite Loop](#issue-1-uc2-infinite-loop)
2. [Issue #2: UC2 Consensus Failure](#issue-2-uc2-consensus-failure)
3. [Issue #3: UC3 Data Not Saved](#issue-3-uc3-data-not-saved)
4. [Issue #4: Claude API JSON Error](#issue-4-claude-api-json-error)
5. [일반적인 문제](#일반적인-문제)

---

## Issue #1: UC2 Infinite Loop

### 증상
```python
retry_count = 0 (계속 0으로 유지)
consensus_reached = False
UC2 → UC2 → UC2 ... (무한 루프, 종료 없음)
```

### 발생 시점
2025-11-17

### 근본 원인
```python
# BEFORE (버그) - uc2_hitl.py
if consensus_reached:
    retry_count = state.get("retry_count", 0)  # consensus=True일 때만 초기화
    next_action = "end"
else:
    # ❌ retry_count 초기화 안 됨!
    # retry_count 변수가 정의되지 않아 NameError 또는 항상 0
    if retry_count < 3:  # NameError 또는 항상 True
        next_action = "retry"
```

**문제점**:
- `retry_count`가 `else` 블록에서 초기화되지 않음
- `if retry_count < 3` 라인에서 NameError 또는 이전 값 0 사용
- 결과적으로 무한 루프

### 해결 방법
```python
# AFTER (수정) - uc2_hitl.py:618-629
# FIX Bug #1: retry_count를 if 블록 밖에서 초기화
retry_count = state.get("retry_count", 0)  # ✅ 조건문 밖으로 이동

# FIX Bug #2: consensus_reached AND is_valid 모두 체크
is_valid = validation.get("is_valid", False)

if consensus_reached and is_valid:
    next_action = "end"  # 합의 성공 + 유효성 확인 → 종료
else:
    if retry_count < 3:
        next_action = "retry"  # 재시도
    else:
        next_action = "human_review"  # 사람 개입

# FIX Bug #3: retry할 때만 retry_count 증가
should_increment = (next_action == "retry")

return {
    **state,
    "retry_count": retry_count + (1 if should_increment else 0),
    "next_action": next_action
}
```

### 학습
- ✅ State 초기화는 조건문 **밖**에서 수행
- ✅ 모든 exit condition 명확히 정의 (`consensus_reached AND is_valid`)
- ✅ Loop counter는 실제 루프 시에만 증가

### 영향
무한 루프 완전 제거, MAX_LOOP_REPEATS=3 정상 작동 ✅

### 코드 위치
[src/workflow/uc2_hitl.py:618-629](../src/workflow/uc2_hitl.py#L618-L629)

---

## Issue #2: UC2 Consensus Failure

### 증상
```python
# UC2 Consensus 실패
Claude Proposer: div.tit-news, div.article-body (틀린 Selector)
GPT-4o Validator: 추출 실패
Consensus Score: 0.36 < 0.75 (REJECTED)
데이터 수집: 실패
```

### 발생 시점
2025-11-18

### 근본 원인 분석
```python
# DB에 저장된 Selector (과거)
title_selector = "h1.title-type017 > span.tit01"
body_selector = "div.content03"

# 실제 현재 HTML 구조 (사이트 변경 후)
<h1 class="tit01">이민 빗장 강화하는 영국...</h1>  # ✅ 실제 존재
<div class="content03">                            # ✅ 실제 존재
  <div class="story-news article">
    [Article content]
  </div>
</div>

# LLM 제안 (Wrong!)
Claude: "div.tit-news" (존재하지 않음, 추측)
GPT-4o: "div.article-body" (존재하지 않음, 추측)
```

**왜 LLM이 틀렸나?**
1. DB Selector가 과거 구조 (`h1.title-type017`) 참조
2. Few-Shot Examples가 generic pattern 제시 (`div.tit-*`)
3. 실제 HTML에 `h1.tit01`이 있지만 LLM이 발견 못함

### 해결 방법: Site-specific HTML Hints

```python
# src/workflow/uc2_hitl.py:172-195
if site_name == "yonhap" or "yna.co.kr" in state['url']:
    html_hint = """
**🔍 CRITICAL: yonhap (yna.co.kr) HTML Structure Hints**:
Based on recent successful crawls and live HTML analysis:

- Title: Look for `h1.tit01` (NOT h1.title-type017)
- Body: Look for `div.content03` - this div contains the full article text
- Date: Use `meta[property='article:published_time']` (most reliable)

Example yonhap structure:
```html
<h1 class="tit01">이랜드 "패션물류센터 화재...</h1>
<div class="content03">
  <div class="story-news article">
    [Article content here]
  </div>
</div>
<meta property="article:published_time" content="2025-11-17T18:10:16+09:00">
```

**WARNING**: Previous attempts used `h1.title-type017 > span.tit01` and `div.article-body`
but these DON'T EXIST in current HTML. Use the hints above instead.
"""
```

### 효과
```
Before (generic few-shot):
- Claude Confidence: 0.60
- GPT-4o Confidence: 0.45
- Extraction Quality: 0.20
- Consensus: 0.36 (FAIL)

After (site-specific hints):
- Claude Confidence: 0.95 ✅
- GPT-4o Confidence: 0.90 ✅
- Extraction Quality: 0.85 ✅
- Consensus: 0.88 (SUCCESS) ✅

데이터 수집:
- Title: "이민 빗장 강화하는 영국..." (50자)
- Body: 3,031자
- Date: "2025-11-17T18:10:16+09:00"
- Quality: 100
```

### 학습
- ✅ Site-specific hints > Generic few-shot examples
- ✅ 실시간 HTML 분석 + LLM 프롬프트 결합 = 정확도 급상승
- ✅ 과거 실패 사례를 WARNING으로 명시 (LLM에게 명확한 가이드)

### 추가 구현 아이디어
- [ ] 모든 사이트에 site-specific hints 자동 생성
- [ ] HTML 구조 변경 감지 시 자동 hints 업데이트
- [ ] LangSmith로 hints 효과 A/B 테스트

### 코드 위치
[src/workflow/uc2_hitl.py:172-195](../src/workflow/uc2_hitl.py#L172-L195)

---

## Issue #3: UC3 Data Not Saved

### 증상
```python
UC3: Selector 생성 성공 ✅
DB: Selector INSERT 완료 ✅
CrawlResult: 데이터 없음 ❌ (왜?)
```

### 발생 시점
2025-11-17

### 근본 원인
```python
# BEFORE (이전 워크플로우)
UC3 → Selector INSERT → END

# 문제: UC1 재시도 없음!
# Selector는 저장되었지만, 실제 데이터 크롤링은 안 함
```

### 해결 방법: UC3 → UC1 Auto-Retry

```python
# AFTER (수정) - master_crawl_workflow.py:789-823
if current_uc == "uc3":
    if selectors_discovered:
        # 1. Selector INSERT
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

        # 2. UC1 자동 재시도 (NEW!) ✅
        return Command(
            update={"current_uc": "uc1"},
            goto="uc1_validation"
        )
    else:
        # Discovery 실패 → Human Review
        return Command(goto=END)
```

### 결과
```
UC3 Discovery (donga)
  ↓
Selector INSERT (DB)
  ↓
UC1 Auto-Retry ✅ (NEW!)
  ↓
Quality: 100
  ↓
CrawlResult INSERT (DB) ✅
  - title: "한국부동산개발협회 20주년..."
  - body: 1,668 chars
  - date: 2025-11-14
  - quality_score: 100
```

### 학습
- ✅ **Discovery는 수단, 최종 목표는 데이터 수집**
- ✅ 모든 UC는 최종적으로 UC1으로 수렴 (Learn Once, Reuse Forever)
- ✅ Workflow 설계 시 **최종 목표(End Goal)** 명확히 정의

### 코드 위치
[src/workflow/master_crawl_workflow.py:789-823](../src/workflow/master_crawl_workflow.py#L789-L823)

---

## Issue #4: Claude API JSON Error

### 증상
```python
ERROR | Claude Propose Node | ❌ Attempt 3 failed:
Expecting value: line 1 column 1 (char 0)
```

### 발생 시점
2025-11-18 (간헐적)

### 근본 원인
- Claude API 응답 오류 (JSON 형식 아님)
- 또는 API timeout (30초 초과)

### 해결 방법: GPT-4o-mini Fallback

```python
# src/workflow/uc2_hitl.py:257-290
try:
    claude_response = claude_llm.invoke(prompt)
    gpt_proposal = json.loads(claude_response.content)
    logger.success("✅ Claude Proposer succeeded")

except Exception as claude_error:
    logger.warning(
        f"[Claude Propose Node] ❌ Claude failed: {claude_error}"
    )
    logger.warning(
        "[Claude Propose Node] 🔄 Falling back to GPT-4o-mini"
    )

    # Fallback: GPT-4o-mini로 전환 ✅
    fallback_llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.3,
        max_tokens=4096,
        timeout=30.0
    )

    fallback_response = fallback_llm.invoke(prompt)
    gpt_proposal = json.loads(fallback_response.content)

    logger.success(
        f"✅ Fallback GPT-4o-mini succeeded "
        f"(confidence: {gpt_proposal.get('confidence', 'N/A')})"
    )
```

### 실제 결과
```
Attempt 1: Claude → JSON Parsing Error ❌
Attempt 2: Claude → JSON Parsing Error ❌
Attempt 3: Claude → JSON Parsing Error ❌
  ↓
Fallback: GPT-4o-mini → SUCCESS ✅
  - Confidence: 0.95
  - Selectors: h1.tit01, div.content03, meta[...]
  - Consensus: 0.88 (AUTO-APPROVED)
```

### 학습
- ✅ **Multi-provider Fallback은 필수** (단일 LLM 의존 위험)
- ✅ Claude ↔ GPT-4o ↔ GPT-4o-mini (3-tier fallback)
- ✅ 사용자에게 투명하게 복구 (로그로만 표시)
- ✅ Cost-Performance 트레이드오프: GPT-4o-mini는 Claude보다 저렴하지만 성능 유사

### 코드 위치
[src/workflow/uc2_hitl.py:257-290](../src/workflow/uc2_hitl.py#L257-L290)

---

## 일반적인 문제

### 문제: PostgreSQL 연결 실패

**증상**:
```
psycopg2.OperationalError: could not connect to server
```

**해결**:
```bash
# PostgreSQL 실행 확인
docker-compose ps

# 실행 안 되어 있으면
docker-compose up -d

# 로그 확인
docker-compose logs postgres
```

---

### 문제: Gradio UI 접속 안 됨

**증상**:
```
http://localhost:7860 접속 불가
```

**해결**:
```bash
# 프로세스 확인
ps aux | grep app.py

# 없으면 실행
cd /Users/charlee/Desktop/Intern/crawlagent
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/ui/app.py

# 백그라운드 실행
PYTHONPATH=/Users/charlee/Desktop/Intern/crawlagent poetry run python src/ui/app.py &
```

---

### 문제: LLM API Key 오류

**증상**:
```
AuthenticationError: Invalid API key
```

**해결**:
```bash
# .env 파일 확인
cat .env | grep API_KEY

# 유효한 키로 업데이트
# ANTHROPIC_API_KEY=sk-ant-...
# OPENAI_API_KEY=sk-...
# GOOGLE_API_KEY=AIza...
```

---

### 문제: LangSmith 트레이스 안 보임

**증상**:
LangSmith에 트레이스 기록 안 됨

**해결**:
```bash
# .env 확인
cat .env | grep LANGCHAIN

# 필요한 설정:
# LANGCHAIN_TRACING_V2=true
# LANGCHAIN_API_KEY=lsv2_pt_...
# LANGCHAIN_PROJECT=crawlagent-poc
```

---

## 로그 확인 방법

### Gradio UI 로그
```bash
# 실시간 로그 (서버가 터미널에서 실행 중일 때)
# 하단 로그 출력 창 확인

# 백그라운드 실행 시
tail -f /tmp/gradio.log
```

### PostgreSQL 로그
```bash
docker-compose logs -f postgres
```

### LangSmith 트레이스
```
URL: https://smith.langchain.com
프로젝트: crawlagent-poc
필터: UC2, UC3 등으로 검색
```

---

## 연락처

**기술 지원**: crawlagent-team@example.com
**GitHub Issues**: /crawlagent/issues

---

**문서 버전**: v1.0
**마지막 업데이트**: 2025-11-18
