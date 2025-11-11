# UC2 Self-Healing Implementation Plan

**작성일**: 2025-11-06
**목적**: UC2 Multi-Agent Self-Healing 실제 구현을 위한 상세 계획
**현재 상태**: 30% (Stub Implementation) → 목표: 100% (Production-Ready)

---

## 📋 Executive Summary

### 현재 Gap 분석
- ✅ **완료**: LangGraph StateGraph 구조 (`build_uc2_graph()`)
- ✅ **완료**: UC1 → UC2 트리거 로직 (`yonhap.py`)
- ✅ **완료**: HITL UI (Gradio Tab 5)
- ❌ **미완료**: 실제 GPT/Gemini API 호출
- ❌ **미완료**: HTML 파싱 및 CSS Selector 추출
- ❌ **미완료**: Selector 검증 및 테스트

### 구현 범위
```
[UC1 Failure Detection] → [HTML Fetch] → [GPT Analysis] → [Gemini Validation]
→ [Consensus Check] → [HITL Decision] → [Selector Update]
```

---

## 🎯 Phase 1: Core API Integration (3-4시간)

### 1.1 GPT-4o-mini CSS Selector Proposer

**파일**: `src/agents/uc2_gpt_proposer.py`

**구현 내용**:
```python
"""
UC2 - GPT-4o-mini CSS Selector 제안 Agent
HTML을 분석하여 title, body, date를 추출할 CSS Selector 제안
"""

from openai import OpenAI
import os
from typing import Dict
from loguru import logger

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def propose_selectors(
    url: str,
    html_content: str,
    site_name: str,
    previous_selectors: Dict[str, str] = None
) -> Dict:
    """
    GPT-4o-mini에게 CSS Selector 제안 요청

    Args:
        url: 크롤링 실패한 URL
        html_content: HTML 원문 (최대 50KB)
        site_name: 사이트명 (yonhap, naver, bbc)
        previous_selectors: 이전 Selector (실패한 것)

    Returns:
        {
            "title_selector": "div.article-header h1",
            "body_selector": "div.article-body p",
            "date_selector": "time.published",
            "reasoning": "...",
            "confidence": 85
        }
    """

    # HTML 크기 제한 (50KB)
    if len(html_content) > 50000:
        html_content = html_content[:50000]

    prompt = f"""
당신은 웹 크롤링 전문가입니다. HTML을 분석하여 뉴스 기사를 추출할 CSS Selector를 제안하세요.

## 입력 정보
- **사이트**: {site_name}
- **URL**: {url}
- **이전 Selector** (실패함): {previous_selectors or '없음'}

## HTML 샘플
```html
{html_content}
```

## 임무
다음 3가지 요소를 추출할 **CSS Selector**를 제안하세요:
1. **제목 (title)**: 기사 제목
2. **본문 (body)**: 기사 본문 전체
3. **날짜 (date)**: 발행일

## 제약사항
- CSS Selector만 사용 (XPath 금지)
- 가능한 단순하고 안정적인 Selector 선호
- class, id, tag name 우선 (nth-child 최소화)
- 본문은 여러 태그를 포함할 수 있음 (예: "div.article-body p")

## 출력 형식 (JSON만!)
{{
  "title_selector": "CSS Selector for title",
  "body_selector": "CSS Selector for body",
  "date_selector": "CSS Selector for date",
  "reasoning": "왜 이 Selector를 선택했는지 간단히 설명",
  "confidence": 85  # 0-100
}}

**중요**: JSON 외의 텍스트 출력 금지!
"""

    # GPT-4o-mini 호출
    max_retries = 3
    import time

    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a web scraping expert. Always respond with valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content.strip())
            logger.info(f"[GPT Proposer] confidence={result.get('confidence', 0)} - {result.get('reasoning', '')[:100]}")
            return result

        except Exception as e:
            if "429" in str(e) or "rate_limit" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"[GPT Proposer] Rate Limit (시도 {attempt + 1}/{max_retries}). 2초 대기...")
                    time.sleep(2)
                    continue

            logger.error(f"[GPT Proposer] 예외 발생: {e}")
            return {
                "title_selector": None,
                "body_selector": None,
                "date_selector": None,
                "reasoning": f"GPT 호출 실패: {str(e)}",
                "confidence": 0
            }

    # 모든 재시도 실패
    return {
        "title_selector": None,
        "body_selector": None,
        "date_selector": None,
        "reasoning": "모든 재시도 실패",
        "confidence": 0
    }
```

**테스트 방법**:
```bash
# Unit Test
poetry run python -c "
from src.agents.uc2_gpt_proposer import propose_selectors
result = propose_selectors(
    url='https://www.yna.co.kr/view/AKR20251103...',
    html_content='<html>...</html>',
    site_name='yonhap'
)
print(result)
"
```

---

### 1.2 Gemini-2.0-flash CSS Selector Validator

**파일**: `src/agents/uc2_gemini_validator.py`

**구현 내용**:
```python
"""
UC2 - Gemini-2.0-flash CSS Selector 검증 Agent
GPT가 제안한 Selector를 HTML에서 실제로 테스트하여 검증
"""

import os
from typing import Dict
from loguru import logger
from bs4 import BeautifulSoup
import google.generativeai as genai

# Gemini API 설정
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def validate_selectors(
    url: str,
    html_content: str,
    gpt_proposal: Dict
) -> Dict:
    """
    Gemini-2.0-flash로 GPT 제안 검증

    Args:
        url: 크롤링 URL
        html_content: HTML 원문
        gpt_proposal: GPT가 제안한 Selector

    Returns:
        {
            "title_valid": true,
            "body_valid": true,
            "date_valid": true,
            "extracted_samples": {
                "title": "샘플 제목",
                "body": "샘플 본문 처음 100자...",
                "date": "2025-11-06"
            },
            "issues": [],
            "recommendation": "approve" | "reject" | "modify",
            "confidence": 90
        }
    """

    # BeautifulSoup으로 실제 추출 테스트
    soup = BeautifulSoup(html_content, 'html.parser')

    extraction_results = {}
    issues = []

    for field in ['title', 'body', 'date']:
        selector = gpt_proposal.get(f'{field}_selector')
        if not selector:
            issues.append(f"{field}_selector가 제공되지 않음")
            extraction_results[field] = None
            continue

        try:
            if field == 'body':
                # 본문은 여러 요소일 수 있음
                elements = soup.select(selector)
                if elements:
                    text = ' '.join([elem.get_text(strip=True) for elem in elements])
                    extraction_results[field] = text[:100] + '...' if len(text) > 100 else text
                else:
                    extraction_results[field] = None
                    issues.append(f"{field}: Selector '{selector}'로 추출 실패")
            else:
                # 제목/날짜는 단일 요소
                element = soup.select_one(selector)
                if element:
                    extraction_results[field] = element.get_text(strip=True)
                else:
                    extraction_results[field] = None
                    issues.append(f"{field}: Selector '{selector}'로 추출 실패")

        except Exception as e:
            extraction_results[field] = None
            issues.append(f"{field}: 추출 중 예외 - {str(e)}")

    # Gemini에게 종합 판단 요청
    prompt = f"""
당신은 CSS Selector 검증 전문가입니다. GPT가 제안한 Selector를 실제 HTML에서 테스트한 결과를 평가하세요.

## GPT 제안
- title_selector: {gpt_proposal.get('title_selector')}
- body_selector: {gpt_proposal.get('body_selector')}
- date_selector: {gpt_proposal.get('date_selector')}
- GPT reasoning: {gpt_proposal.get('reasoning')}
- GPT confidence: {gpt_proposal.get('confidence')}

## 실제 추출 결과
- Title: {extraction_results.get('title', 'None')}
- Body: {extraction_results.get('body', 'None')}
- Date: {extraction_results.get('date', 'None')}

## 발견된 문제
{issues if issues else '없음'}

## 임무
위 결과를 종합하여 판단하세요:
- **approve**: 3개 모두 정상 추출 → 즉시 사용 가능
- **modify**: 일부만 성공 → GPT에게 재시도 요청
- **reject**: 모두 실패 → 사람 개입 필요

## 출력 형식 (JSON만!)
{{
  "title_valid": true/false,
  "body_valid": true/false,
  "date_valid": true/false,
  "recommendation": "approve" | "modify" | "reject",
  "confidence": 90,
  "reasoning": "..."
}}
"""

    # Gemini 호출
    max_retries = 3
    import time

    for attempt in range(max_retries):
        try:
            model = genai.GenerativeModel('gemini-2.0-flash-exp')
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "response_mime_type": "application/json"
                }
            )

            result = json.loads(response.text)
            result['extracted_samples'] = extraction_results
            result['issues'] = issues

            logger.info(f"[Gemini Validator] {result['recommendation']} (confidence={result['confidence']})")
            return result

        except Exception as e:
            if "429" in str(e) or "quota" in str(e).lower():
                if attempt < max_retries - 1:
                    logger.warning(f"[Gemini Validator] Rate Limit (시도 {attempt + 1}/{max_retries}). 5초 대기...")
                    time.sleep(5)
                    continue

            logger.error(f"[Gemini Validator] 예외 발생: {e}")
            return {
                "title_valid": False,
                "body_valid": False,
                "date_valid": False,
                "extracted_samples": extraction_results,
                "issues": issues + [f"Gemini 호출 실패: {str(e)}"],
                "recommendation": "reject",
                "confidence": 0,
                "reasoning": f"검증 실패: {str(e)}"
            }

    # 모든 재시도 실패
    return {
        "title_valid": False,
        "body_valid": False,
        "date_valid": False,
        "extracted_samples": extraction_results,
        "issues": issues + ["Gemini 재시도 실패"],
        "recommendation": "reject",
        "confidence": 0,
        "reasoning": "모든 재시도 실패"
    }
```

---

## 🎯 Phase 2: Workflow Integration (2-3시간)

### 2.1 `trigger_uc2_workflow()` 실제 구현

**파일**: `src/crawlers/spiders/yonhap.py` (수정)

**현재 Stub 코드 (lines 52-98)** → **실제 구현으로 교체**:

```python
def trigger_uc2_workflow(self, url: str) -> None:
    """UC2 Self-Healing 워크플로우 트리거 (실제 구현)"""

    self.logger.warning(f"[UC2 트리거] 연속 {self.failure_count}회 실패 → Self-Healing 시작")

    # 1. HTML 다시 가져오기
    import requests
    try:
        response = requests.get(url, timeout=10)
        response.encoding = 'utf-8'
        html_content = response.text
    except Exception as e:
        self.logger.error(f"[UC2] HTML 가져오기 실패: {e}")
        return

    # 2. 이전 Selector 조회
    session = SessionLocal()
    try:
        prev_selector = session.query(Selector).filter_by(site_name="yonhap").first()
        previous_selectors = {
            "title_selector": prev_selector.title_selector if prev_selector else None,
            "body_selector": prev_selector.body_selector if prev_selector else None,
            "date_selector": prev_selector.date_selector if prev_selector else None,
        }
    finally:
        session.close()

    # 3. GPT 제안 요청
    from src.agents.uc2_gpt_proposer import propose_selectors
    gpt_analysis = propose_selectors(
        url=url,
        html_content=html_content,
        site_name="yonhap",
        previous_selectors=previous_selectors
    )

    # 4. Gemini 검증 요청
    from src.agents.uc2_gemini_validator import validate_selectors
    gemini_validation = validate_selectors(
        url=url,
        html_content=html_content,
        gpt_proposal=gpt_analysis
    )

    # 5. Consensus 판단
    consensus_reached = (
        gemini_validation.get('recommendation') == 'approve' and
        all([
            gemini_validation.get('title_valid'),
            gemini_validation.get('body_valid'),
            gemini_validation.get('date_valid')
        ])
    )

    # 6. DecisionLog 저장 (실제 데이터!)
    session = SessionLocal()
    try:
        log = DecisionLog(
            url=url,
            site_name="yonhap",
            gpt_analysis=gpt_analysis,
            gemini_validation=gemini_validation,
            consensus_reached=consensus_reached,
            retry_count=0
        )
        session.add(log)
        session.commit()

        if consensus_reached:
            self.logger.success(f"[UC2] ✅ Consensus 도달! Decision ID: {log.id}")
        else:
            self.logger.warning(f"[UC2] ⚠️ Consensus 실패 → HITL 필요. Decision ID: {log.id}")

        self.uc2_triggered = True

    except Exception as e:
        self.logger.error(f"[UC2] DecisionLog 저장 실패: {e}")
        session.rollback()
    finally:
        session.close()
```

---

## 🎯 Phase 3: Testing Infrastructure (2-3시간)

### 3.1 Test Environment Setup

**파일**: `tests/setup_uc2_test_env.py`

```python
"""
UC2 테스트 환경 준비 스크립트
- Selector 고의로 깨뜨리기
- 테스트 URL 준비
- 타이머 설정
"""

from src.storage.database import SessionLocal
from src.storage.models import Selector
from loguru import logger

def corrupt_selector():
    """Selector를 고의로 잘못된 값으로 변경"""
    session = SessionLocal()
    try:
        selector = session.query(Selector).filter_by(site_name="yonhap").first()

        # 백업
        original = {
            "title": selector.title_selector,
            "body": selector.body_selector,
            "date": selector.date_selector
        }
        logger.info(f"[백업] {original}")

        # 고의로 깨뜨리기
        selector.title_selector = "div.WRONG_SELECTOR h1"
        selector.body_selector = "div.NONEXISTENT p"
        selector.date_selector = "time.FAKE_CLASS"

        session.commit()
        logger.success("[Selector 변조 완료] UC2 트리거 준비됨")

        return original

    finally:
        session.close()

def restore_selector(original: dict):
    """Selector 복원"""
    session = SessionLocal()
    try:
        selector = session.query(Selector).filter_by(site_name="yonhap").first()
        selector.title_selector = original['title']
        selector.body_selector = original['body']
        selector.date_selector = original['date']
        session.commit()
        logger.success("[Selector 복원 완료]")
    finally:
        session.close()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python setup_uc2_test_env.py [corrupt|restore]")
        sys.exit(1)

    action = sys.argv[1]

    if action == "corrupt":
        original = corrupt_selector()
        print(f"\n백업 데이터: {original}")
        print("\n복원 명령:")
        print("poetry run python tests/setup_uc2_test_env.py restore")

    elif action == "restore":
        # 하드코딩된 원본 값 (PRD에서 가져옴)
        original = {
            "title": "h1.tit",
            "body": "div.article p",
            "date": "span.date-time"
        }
        restore_selector(original)
```

---

### 3.2 End-to-End Test Script

**파일**: `tests/test_uc2_e2e.py`

```python
"""
UC2 End-to-End 테스트
Self-Healing 전체 플로우 검증
"""

import time
import subprocess
from loguru import logger
from src.storage.database import SessionLocal
from src.storage.models import DecisionLog, Selector

def test_uc2_e2e():
    """
    테스트 시나리오:
    1. Selector 고의로 깨뜨리기
    2. 크롤링 시작 (3회 연속 실패 예상)
    3. UC2 트리거 확인
    4. DecisionLog 생성 확인
    5. Consensus 확인
    6. 복구 시간 측정 (<1시간)
    """

    logger.info("=== UC2 E2E 테스트 시작 ===")

    # Step 1: Selector 변조
    logger.info("[Step 1] Selector 변조...")
    subprocess.run([
        "poetry", "run", "python",
        "tests/setup_uc2_test_env.py", "corrupt"
    ])

    # Step 2: 크롤링 시작 (타이머 시작)
    start_time = time.time()
    logger.info("[Step 2] 크롤링 시작 (UC2 트리거 대기)...")

    result = subprocess.run([
        "poetry", "run", "scrapy", "crawl", "yonhap",
        "-a", "category=economy",
        "-s", "CLOSESPIDER_ITEMCOUNT=5"
    ], capture_output=True, text=True)

    # Step 3: DecisionLog 확인
    logger.info("[Step 3] DecisionLog 확인...")
    session = SessionLocal()
    try:
        logs = session.query(DecisionLog).order_by(DecisionLog.created_at.desc()).limit(1).all()

        if not logs:
            logger.error("❌ DecisionLog 생성 안 됨! UC2 트리거 실패")
            return False

        log = logs[0]
        logger.success(f"✅ DecisionLog 생성 확인: ID={log.id}")
        logger.info(f"  - GPT Analysis: {log.gpt_analysis}")
        logger.info(f"  - Gemini Validation: {log.gemini_validation}")
        logger.info(f"  - Consensus: {log.consensus_reached}")

        # Step 4: Consensus 확인
        if log.consensus_reached:
            # Step 5: Selector 업데이트 확인
            selector = session.query(Selector).filter_by(site_name="yonhap").first()
            logger.info(f"  - Updated Selector: {selector.title_selector}")

            elapsed = time.time() - start_time
            logger.success(f"✅ UC2 Self-Healing 성공! (소요 시간: {elapsed:.1f}초)")

            # KPI 확인: <1시간 (3600초)
            if elapsed < 3600:
                logger.success(f"✅ KPI 통과: 복구 시간 {elapsed:.1f}초 < 3600초")
            else:
                logger.warning(f"⚠️ KPI 미달: 복구 시간 {elapsed:.1f}초 > 3600초")

            return True
        else:
            logger.warning("⚠️ Consensus 실패 → HITL 필요")
            return False

    finally:
        session.close()

    # Step 6: 복원
    logger.info("[Step 6] Selector 복원...")
    subprocess.run([
        "poetry", "run", "python",
        "tests/setup_uc2_test_env.py", "restore"
    ])

if __name__ == "__main__":
    success = test_uc2_e2e()
    exit(0 if success else 1)
```

---

## 🎯 Phase 4: Production Readiness (1-2시간)

### 4.1 Error Handling 강화

**추가 사항**:
- Rate Limit 대응 (지수 백오프)
- HTML 파싱 실패 처리
- API Key 검증
- Timeout 설정

### 4.2 Logging 및 Monitoring

**파일**: `src/utils/uc2_monitor.py`

```python
"""
UC2 성능 모니터링
- 평균 복구 시간
- Consensus 성공률
- GPT/Gemini 호출 비용
"""

def log_uc2_metrics(
    decision_id: int,
    duration_seconds: float,
    consensus_reached: bool,
    gpt_tokens: int,
    gemini_tokens: int
):
    """UC2 메트릭 로깅"""
    logger.info(
        f"[UC2 Metrics] Decision={decision_id}, "
        f"Duration={duration_seconds:.1f}s, "
        f"Consensus={consensus_reached}, "
        f"Tokens(GPT={gpt_tokens}, Gemini={gemini_tokens})"
    )
```

### 4.3 PRD 최종 업데이트

**파일**: `docs/PRD_CrawlAgent_2025-11-06.md`

**추가할 섹션**:
- UC2 Implementation Details (API 호출 플로우)
- Cost Analysis (GPT + Gemini 토큰 비용)
- Performance Benchmarks (실제 테스트 결과)

---

## 📊 구현 체크리스트

### Phase 1: Core API (3-4h)
- [ ] `uc2_gpt_proposer.py` 작성
- [ ] `uc2_gemini_validator.py` 작성
- [ ] Unit Test 통과 (각 함수 독립 테스트)
- [ ] Rate Limit 대응 검증

### Phase 2: Integration (2-3h)
- [ ] `trigger_uc2_workflow()` 실제 구현
- [ ] DecisionLog 실제 데이터 저장 확인
- [ ] Gradio Tab 5에서 Pending 목록 확인
- [ ] Approve/Reject 기능 테스트

### Phase 3: Testing (2-3h)
- [ ] `setup_uc2_test_env.py` 작성
- [ ] `test_uc2_e2e.py` 작성
- [ ] Selector 변조 → 복구 플로우 검증
- [ ] 복구 시간 <1시간 KPI 달성

### Phase 4: Production (1-2h)
- [ ] Error Handling 강화
- [ ] Logging 추가
- [ ] PRD 최종 업데이트
- [ ] README 업데이트

---

## 🚀 실행 계획

### Day 1 (4시간)
- Morning: Phase 1 - GPT + Gemini API 구현
- Afternoon: Phase 2 - Workflow Integration

### Day 2 (3시간)
- Morning: Phase 3 - Testing Infrastructure
- Afternoon: Phase 4 - Production Readiness

### Total Estimated Time: **7-12 시간**

---

## 📈 Success Criteria

구현 완료 판단 기준:
1. ✅ UC2 E2E 테스트 통과 (Selector 변조 → 자동 복구)
2. ✅ 복구 시간 <1시간 (KPI 달성)
3. ✅ Gradio Tab 5에서 실제 DecisionLog 표시
4. ✅ HITL Approve 클릭 시 Selector 업데이트 확인
5. ✅ PRD Go/No-Go 테이블 3🟢 달성

---

**Last Updated**: 2025-11-06
**Next Action**: Phase 1 시작 - `uc2_gpt_proposer.py` 작성
