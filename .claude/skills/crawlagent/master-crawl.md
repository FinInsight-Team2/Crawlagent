---
name: crawlagent-master-crawl
description: CrawlAgent Master Crawl - URL 입력만으로 UC1/UC2/UC3 자동 라우팅하여 뉴스 크롤링 및 자동 복구
version: 1.0.0
author: CrawlAgent Team
tags:
  - master-workflow
  - self-healing
  - auto-routing
  - crawling
  - news
---

# CrawlAgent Master Crawl 스킬

## 개요

Master Crawl 스킬은 **URL만 입력하면 UC1/UC2/UC3를 자동으로 라우팅**하여 뉴스 기사를 크롤링하고, 에러 발생 시 자동으로 복구합니다.

**핵심 가치**: "One Command, Full Automation"
- URL만 제공 → 나머지는 자동
- 에러 자동 감지 → 자동 복구 (UC2/UC3)
- 결과 자동 저장 → DB에 영구 보관

**지원 사이트** (8개 SSR 뉴스):
- 국내: Yonhap, Donga, MK, eDaily, Hankyung
- 해외: BBC, Reuters, CNN

---

## 사용 방법

### 기본 사용

```python
# 1. 단일 URL 크롤링
poetry run python -c "
from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState

graph = build_master_graph()
state = MasterCrawlState(
    url='https://www.yonhapnewstv.co.kr/category/news/politics/all/20231',
    site_name='yonhap',
    category='politics',
    messages=[]
)
result = graph.invoke(state)
print(f\"Title: {result['extracted_data']['title']}\")
print(f\"Quality: {result['quality_score']}\")
print(f\"Use Case: {result['final_use_case']}\")
"
```

### Gradio UI 사용

```bash
# UI 실행
make start

# 브라우저에서
http://localhost:7860

# Tab 1: 실시간 크롤링
- URL 입력: https://www.yonhapnewstv.co.kr/category/news/politics/all/20231
- 사이트: yonhap
- 카테고리: politics
- "크롤링 시작" 클릭
```

---

## 자동 라우팅 로직

### Step 1: Unknown vs Known Site 판별

```python
# src/workflow/master_crawl_workflow.py:214-244

def supervisor_route(state: MasterCrawlState) -> Command[Literal["uc1", "uc3"]]:
    """
    DB에 Selector가 있는지 확인
    """
    db = next(get_db())
    selector = db.query(Selector).filter(
        Selector.site_name == state["site_name"]
    ).first()

    if selector:
        return Command(goto="uc1", update={"selector": selector})
    else:
        return Command(goto="uc3")  # 신규 사이트 → Discovery
```

**결과**:
- Selector 있음 → UC1 (Quality Gate)
- Selector 없음 → UC3 (Discovery)

### Step 2: UC1 → 품질 검증

```python
# src/workflow/uc1_validation.py:68-170

def uc1_quality_gate(state: MasterCrawlState) -> MasterCrawlState:
    """
    5W1H 규칙 기반 품질 검증 (LLM 없음, $0)
    """
    # Selector로 크롤링
    extracted_data = extract_with_selector(state["url"], state["selector"])

    # 품질 점수 계산 (0-100)
    quality_score = calculate_quality_score(extracted_data)

    if quality_score >= 80:
        # 성공 → 종료
        return {**state, "quality_score": quality_score, "final_use_case": "UC1"}
    else:
        # 실패 → UC2로 전환
        return {**state, "quality_score": quality_score, "trigger_uc2": True}
```

**결과**:
- Quality Score ≥ 80 → 성공 종료
- Quality Score < 80 → UC2 (Self-Healing)

### Step 3: UC2 → 자동 복구 (조건부)

```python
# src/workflow/uc2_hitl.py:135-512

def uc2_self_healing(state: MasterCrawlState) -> MasterCrawlState:
    """
    2-Agent Consensus로 Selector 복구
    - Claude Sonnet 4.5: Proposer
    - GPT-4o: Validator
    """
    # Claude가 새 Selector 제안
    claude_proposal = claude_propose_node(state)

    # GPT-4o가 검증
    gpt_validation = gpt_validate_node(claude_proposal)

    # Consensus 점수 계산
    consensus = 0.3 * claude_confidence + 0.3 * gpt_confidence + 0.4 * extraction_quality

    if consensus >= 0.5:
        # 성공 → Selector 업데이트
        update_selector_in_db(new_selector)
        return {**state, "final_use_case": "UC2", "healed": True}
    else:
        # 실패 → UC3로 전환
        return {**state, "trigger_uc3": True}
```

**결과**:
- Consensus ≥ 0.5 → Selector 복구 성공
- Consensus < 0.5 → UC3 (Discovery)

### Step 4: UC3 → 신규 학습 (최후 수단)

```python
# src/workflow/uc3_new_site.py:1291-1893

def uc3_discovery(state: MasterCrawlState) -> MasterCrawlState:
    """
    Zero-Shot HTML 분석으로 Selector 생성
    - Claude Sonnet 4.5: HTML 분석
    - GPT-4o: 검증
    """
    # Claude가 HTML에서 Selector 발견
    claude_discovery = claude_discover_agent_node(state)

    # GPT-4o가 검증
    gpt_validation = gpt_validate_agent_node(claude_discovery)

    # Consensus 점수 계산
    consensus = 0.3 * claude_confidence + 0.3 * gpt_confidence + 0.4 * extraction_quality

    if consensus >= 0.5:
        # 성공 → Selector DB 저장
        save_new_selector_to_db(discovered_selector)
        return {**state, "final_use_case": "UC3", "discovered": True}
    else:
        # 실패 → 에러
        raise Exception("UC3 Discovery 3회 재시도 실패")
```

**결과**:
- Consensus ≥ 0.5 → 신규 Selector 저장 성공
- Consensus < 0.5 → 실패 (에러)

---

## 전체 플로우차트

```
                    START
                      │
                      ▼
            ┌─────────────────┐
            │   Supervisor    │
            │  (Route Logic)  │
            └─────────┬───────┘
                      │
        ┌─────────────┴─────────────┐
        │                           │
   Selector 있음?             Selector 없음?
        │                           │
        ▼                           ▼
  ┌──────────┐              ┌──────────┐
  │   UC1    │              │   UC3    │
  │ Quality  │              │Discovery │
  │  Gate    │              └─────┬────┘
  └────┬─────┘                    │
       │                          │
    Score ≥ 80?              Consensus ≥ 0.5?
       │                          │
    ✓ YES │                    ✓ YES │
       │                          │
       ▼                          ▼
     SUCCESS ◄──────────── Save Selector
       │                          │
       ▼                          │
     END                          │
       │                          │
    ✗ NO                       ✗ NO
       │                          │
       ▼                          ▼
  ┌──────────┐                 ERROR
  │   UC2    │                   │
  │Self-Heal │                   ▼
  └────┬─────┘                  END
       │
  Consensus ≥ 0.5?
       │
    ✓ YES │
       │
       ▼
  Update Selector
       │
       ▼
   Re-try UC1
       │
       ▼
     SUCCESS
       │
       ▼
      END
```

---

## 실제 사용 예시

### 예시 1: Known Site (Yonhap) - UC1 성공

```bash
URL: https://www.yonhapnewstv.co.kr/category/news/politics/all/20231
Site: yonhap
Category: politics

→ Supervisor: Selector 발견 (id: 42) → UC1
→ UC1: Quality Score 98.5 → 성공
→ Result:
  - Title: "국회, 2025년 예산안 통과"
  - Body: "국회는 19일 본회의를..."
  - Date: "2025-11-19"
  - Use Case: UC1
  - Cost: $0
  - Time: 3.2초
```

### 예시 2: Selector 오류 (Yonhap) - UC2 복구

```bash
URL: https://www.yonhapnewstv.co.kr/category/news/politics/all/20231
Site: yonhap
Category: politics

→ Supervisor: Selector 발견 (id: 42) → UC1
→ UC1: Quality Score 45.0 → 실패 (title missing)
→ UC2: Claude + GPT-4o Consensus 0.72 → 복구 성공
→ UC2: New Selector 저장 (id: 43)
→ Re-try UC1: Quality Score 95.0 → 성공
→ Result:
  - Use Case: UC2
  - Healed: True
  - New Selector ID: 43
  - Cost: $0.002
  - Time: 31.7초
```

### 예시 3: 신규 사이트 (WashingtonPost) - UC3 Discovery

```bash
URL: https://www.washingtonpost.com/politics/...
Site: wapo
Category: politics

→ Supervisor: Selector 없음 → UC3
→ UC3: Claude HTML 분석 + GPT-4o 검증
→ UC3: Consensus 0.85 → Discovery 성공
→ UC3: New Selector 저장 (id: 19)
→ UC1: Quality Score 92.0 → 성공
→ Result:
  - Use Case: UC3
  - Discovered: True
  - New Selector ID: 19
  - Cost: $0.005
  - Time: 45.3초
```

---

## 비용 및 성능

### 비용 구조

| Use Case | 평균 비용 | 발생 확률 | 설명 |
|----------|----------|----------|------|
| UC1 | $0 | 90% | Rule-based, LLM 없음 |
| UC2 | $0.002 | 8% | 2-Agent Consensus (Claude + GPT-4o) |
| UC3 | $0.005 | 2% | HTML 분석 + Discovery |

**1,000회 크롤링 예상 비용**:
```
UC1: 900회 × $0 = $0
UC2: 80회 × $0.002 = $0.16
UC3: 20회 × $0.005 = $0.10
총: $0.26 / 1,000회
```

### 성능 지표

| 지표 | 값 |
|------|-----|
| UC1 평균 처리 시간 | 3.2초 |
| UC2 평균 처리 시간 | 31.7초 |
| UC3 평균 처리 시간 | 45.3초 |
| 전체 성공률 | 100% (459/459) |
| 평균 품질 점수 | 97.44/100 |

---

## Claude가 실행 가능한 명령어

### 크롤링 실행

```bash
# 프로젝트 루트에서
cd /Users/charlee/Desktop/Intern/crawlagent

# 단일 URL 크롤링
poetry run python -c "
from src.workflow.master_crawl_workflow import build_master_graph, MasterCrawlState

url = 'https://www.yonhapnewstv.co.kr/category/news/politics/all/20231'
graph = build_master_graph()
state = MasterCrawlState(url=url, site_name='yonhap', category='politics', messages=[])
result = graph.invoke(state)

# 결과 출력
print('=== 크롤링 결과 ===')
print(f'Use Case: {result[\"final_use_case\"]}')
print(f'Title: {result[\"extracted_data\"][\"title\"]}')
print(f'Quality: {result[\"quality_score\"]}/100')
"
```

### 결과 조회

```bash
# DB에서 최근 크롤링 조회
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import CrawlResult

db = next(get_db())
results = db.query(CrawlResult).order_by(CrawlResult.created_at.desc()).limit(5).all()

for r in results:
    print(f'{r.site_name} | {r.title[:50]} | Quality: {r.quality_score}')
"
```

### Selector 조회

```bash
# 등록된 Selector 목록
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import Selector

db = next(get_db())
selectors = db.query(Selector).all()

for s in selectors:
    print(f'{s.id} | {s.site_name} | Created: {s.created_at}')
"
```

---

## 에러 처리

### UC1 품질 실패

```python
# 자동으로 UC2 트리거됨
# 사용자 개입 불필요
```

### UC2 Consensus 실패

```python
# 자동으로 UC3 트리거됨
# 3회 재시도 후에도 실패하면 에러
```

### UC3 Discovery 실패

```python
# 에러 메시지와 함께 종료
# 로그에 상세 원인 기록
# → 수동으로 사이트 구조 확인 필요
```

---

## 다음 단계

1. **Claude 콘솔에 스킬 등록**:
   - `.claude/skills/crawlagent/` 폴더를 Claude 프로젝트에 업로드
   - 또는 Claude Desktop에서 자동 인식

2. **Claude에게 요청**:
   ```
   "Yonhap 정치 뉴스를 크롤링해줘"
   "BBC 월드 뉴스 URL로 크롤링 실행"
   "최근 크롤링 결과 5개 보여줘"
   ```

3. **Claude가 자동 실행**:
   - 이 스킬을 참고하여 명령어 생성
   - Terminal에서 자동 실행
   - 결과 파싱 및 사용자에게 요약

---

**작성일**: 2025-11-19
**버전**: 1.0.0
**위치**: `/Users/charlee/Desktop/Intern/crawlagent/.claude/skills/crawlagent/master-crawl.md`
