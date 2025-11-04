# 개발자 컨텍스트 & 학습 로드맵

**작성일**: 2025-11-05
**프로젝트**: CrawlAgent (LangGraph Multi-Agent Crawler)
**개발자**: Charlee (인턴 → 주니어 개발자 승진 제안)

---

## 🎯 현재 상황 요약

### 대표님 피드백 (2025-11-04 회의)

#### ✅ 긍정적 평가
- **업무 센스**: AI 도구 활용 능력 우수
- **결과 도출**: 프로젝트 완성도 높음 (UC1 Validation, 크롤링 파이프라인, Gradio UI)
- **큰 그림**: 시스템 설계 및 추상화 능력 좋음

#### ⚠️ 우려 사항
1. **AI 도구 의존도 높음**
   - LLM 없이 개발 가능한가?
   - 기본기가 부족하지 않은가?

2. **설명 능력 부족**
   - "어떻게 크롤링하나요?" → 명확한 답변 못함
   - 내부 구현 로직 이해도 낮음
   - 결과는 나왔지만 원리를 설명 못함

3. **핀테크 환경 고려**
   - 금융 IT는 LLM 사용 제한적
   - 웹 검색만으로 개발 가능해야 함

---

## 🚨 핵심 문제 정의

### 문제 1: "결과는 있지만 설명은 못한다"
```
AI 도구 → 코드 생성 → 결과물 완성 ✅
       ↓
   이해 부족 ❌
       ↓
   설명 불가 ❌
```

### 문제 2: "기본기 vs 도구 의존"
- **현재**: AI가 코드 작성 → 복붙 → 실행 → 성공
- **필요**: 원리 이해 → 직접 작성 → 설명 가능

### 문제 3: "승진 조건"
> "LLM 없이도 개발할 수 있고, 만든 것을 설명할 수 있는가?"

---

## 📚 CrawlAgent 프로젝트 완전 이해 (설명 가능 수준)

### Phase 1: 전체 구조 이해하기

#### Q1: "이 시스템이 뭐하는 건가요?" (30초 답변)
**답변 예시**:
> "연합뉴스에서 뉴스 기사를 자동으로 수집하는 시스템입니다. Scrapy로 HTML을 가져오고, GPT-4o-mini가 품질을 검증해서 95점 이상만 PostgreSQL에 저장합니다. Gradio UI로 수집 실행, 데이터 조회, CSV 다운로드를 할 수 있습니다."

**핵심 키워드**:
- Scrapy (크롤링 프레임워크)
- GPT-4o-mini (품질 검증)
- PostgreSQL (데이터 저장)
- Gradio (웹 UI)

---

#### Q2: "어떻게 크롤링하나요?" (2분 답변)

**답변 구조**:

**1단계: 리스트 페이지 수집**
```
https://www.yna.co.kr/economy/all
→ 49개 기사 URL 추출
→ CSS Selector: div.list-type212 a[href*="/view/AKR"]
```

**2단계: 페이지네이션**
```
페이지 1 → 페이지 2 → 페이지 3 ...
- 현재 페이지 번호: div.paging-type01 strong.num.on
- 다음 페이지 링크: a.num[href*="/2"]
- 최대 15페이지 (타임아웃 방지)
```

**3단계: 기사 상세 페이지 크롤링**
```
각 기사 URL 방문
→ Trafilatura로 본문 추출
→ CSS Selector로 제목/날짜 추출
→ GPT-4o-mini로 품질 검증 (95점 이상 저장)
```

**핵심 코드 위치**:
- `src/crawlers/spiders/yonhap.py:153-194` (리스트 페이지)
- `src/crawlers/spiders/yonhap.py:196-250` (페이지네이션)
- `src/crawlers/spiders/yonhap.py:252-320` (기사 상세)

---

#### Q3: "Scrapy는 어떻게 작동하나요?" (3분 답변)

**Scrapy 핵심 개념**:

1. **Spider (크롤러 클래스)**
```python
class YonhapSpider(scrapy.Spider):
    name = "yonhap"
    start_urls = ["https://www.yna.co.kr/economy/all"]

    def parse(self, response):
        # HTML 응답 처리
        article_links = response.css('a[href*="/view/"]::attr(href)').getall()
        for link in article_links:
            yield scrapy.Request(link, callback=self.parse_article)
```

2. **Request/Response 사이클**
```
start_urls → Scrapy Engine → Downloader → HTTP GET
                                              ↓
                                         HTML 응답
                                              ↓
parse() 함수 ← Scrapy Engine ← Response 객체
     ↓
 CSS Selector로 데이터 추출
     ↓
yield (다음 URL 또는 데이터)
```

3. **yield의 의미**
- `yield scrapy.Request()`: 다음 페이지 크롤링 예약
- `yield item`: 데이터 반환 (Item Pipeline으로 전달)

**왜 Scrapy인가?**
- 비동기 처리 (빠름)
- 자동 재시도 (Retry)
- HTTP 캐싱 (중복 요청 방지)
- Middleware (User-Agent, 쿠키 등)

**핵심 파일**:
- `src/crawlers/spiders/yonhap.py` (Spider 정의)
- `scrapy.cfg` (Scrapy 설정)

---

#### Q4: "LangGraph는 왜 쓰나요?" (3분 답변)

**LangGraph 역할**:
> "크롤링 결과를 검증하고 다음 액션을 결정하는 **상태 기반 워크플로우** 엔진입니다."

**핵심 개념**:

1. **State (상태)**
```python
class ValidationState(TypedDict):
    url: str
    title: Optional[str]
    body: Optional[str]
    quality_score: int          # 0-100 점수
    next_action: Literal["save", "heal", "new_site"]  # 다음 액션
```

2. **Node (작업 단위)**
```python
def calculate_quality(state: ValidationState) -> dict:
    # 5W1H 점수 계산
    score = 0
    if state["title"] and len(state["title"]) >= 10:
        score += 20
    if state["body"] and len(state["body"]) >= 500:
        score += 60
    # ...
    return {"quality_score": score}
```

3. **Conditional Edge (조건부 분기)**
```python
def route_by_action(state: ValidationState) -> str:
    if state["quality_score"] >= 80:
        return "save"      # DB 저장
    elif selector_exists:
        return "heal"      # UC2 Self-Healing
    else:
        return "new_site"  # UC3 신규 사이트
```

**왜 LangGraph인가?**
- UC1, UC2, UC3를 **조건부로 연결**
- State 기반 → 추적 가능 (Decision Log)
- Human-in-the-Loop (HITL) 지원

**핵심 파일**:
- `src/workflow/uc1_validation.py` (LangGraph 정의)

---

#### Q5: "GPT-4o-mini는 어떻게 쓰나요?" (2분 답변)

**역할**:
> "크롤링한 기사가 광고/보도자료인지 자동으로 판단합니다."

**처리 흐름**:
```python
# 1. 프롬프트 생성
prompt = f"""
당신은 뉴스 품질 검증 전문가입니다.

입력:
- 제목: {title}
- 본문: {body[:1000]}
- 카테고리: 경제

검증 기준:
- 광고/보도자료는 reject
- 5W1H 포함 여부
- 카테고리 적합성

출력 (JSON):
{{
  "decision": "pass",
  "confidence": 95,
  "reasoning": "경제 카테고리 적합, 5W1H 포함..."
}}
"""

# 2. GPT-4o-mini 호출
response = openai.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": prompt}],
    temperature=0.1,
    response_format={"type": "json_object"}
)

# 3. 결과 파싱
result = json.loads(response.choices[0].message.content)
# {"decision": "pass", "confidence": 95, ...}
```

**비용**:
- GPT-4o-mini: $0.00015/1K tokens
- 기사 1개당: 약 $0.0002 (0.02원)
- 하루 100개: $0.02 (2원)

**핵심 파일**:
- `src/agents/uc1_quality_gate.py:28-161`

---

### Phase 2: 핵심 기술 스택 이해

#### 1. Scrapy (크롤링 프레임워크)
**배우기**:
- 공식 문서: https://docs.scrapy.org/en/latest/intro/tutorial.html
- 핵심: Spider, Request/Response, CSS Selector, yield

**실습**:
```python
# 간단한 Spider 직접 작성
import scrapy

class MySpider(scrapy.Spider):
    name = "test"
    start_urls = ["https://example.com"]

    def parse(self, response):
        title = response.css('h1::text').get()
        print(title)
```

---

#### 2. PostgreSQL + SQLAlchemy (데이터베이스)
**배우기**:
- SQLAlchemy ORM: https://docs.sqlalchemy.org/en/20/tutorial/
- 핵심: Session, Query, ORM Model

**실습**:
```python
# 직접 쿼리 작성
from src.storage.database import get_db
from src.storage.models import CrawlResult

db = next(get_db())
articles = db.query(CrawlResult).filter(
    CrawlResult.quality_score >= 90
).all()

for article in articles:
    print(article.title)
```

---

#### 3. LangGraph (워크플로우 엔진)
**배우기**:
- 공식 문서: https://langchain-ai.github.io/langgraph/
- 핵심: StateGraph, Node, Conditional Edge

**실습**:
```python
# 간단한 State Machine 직접 작성
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

class MyState(TypedDict):
    count: int

def increment(state: MyState) -> dict:
    return {"count": state["count"] + 1}

graph = StateGraph(MyState)
graph.add_node("increment", increment)
graph.add_edge(START, "increment")
graph.add_edge("increment", END)

result = graph.compile().invoke({"count": 0})
print(result)  # {"count": 1}
```

---

#### 4. Gradio (웹 UI)
**배우기**:
- 공식 문서: https://www.gradio.app/guides/quickstart
- 핵심: Blocks, Textbox, Button, click event

**실습**:
```python
import gradio as gr

def greet(name):
    return f"Hello {name}!"

with gr.Blocks() as demo:
    name_input = gr.Textbox(label="Name")
    greet_btn = gr.Button("Greet")
    output = gr.Textbox(label="Output")

    greet_btn.click(fn=greet, inputs=name_input, outputs=output)

demo.launch()
```

---

### Phase 3: 설명 가능한 코드 위치 매핑

#### 크롤링 로직
| 질문 | 답변 | 파일 위치 |
|------|------|----------|
| "어떻게 기사 목록을 가져오나요?" | CSS Selector로 추출 | `yonhap.py:157` |
| "페이지네이션은 어떻게?" | 현재 페이지 번호 찾고 +1 | `yonhap.py:198-250` |
| "중복은 어떻게 제거?" | URL 기준 DB 조회 | `yonhap.py:310-315` |
| "증분 수집이 뭔가요?" | target_date와 기사 날짜 비교 | `yonhap.py:258-280` |

#### LangGraph 로직
| 질문 | 답변 | 파일 위치 |
|------|------|----------|
| "State는 어디 정의?" | TypedDict 클래스 | `uc1_validation.py:29-75` |
| "점수는 어떻게 계산?" | 5W1H 규칙 | `uc1_validation.py:105-170` |
| "분기는 어떻게?" | quality_score >= 80 | `uc1_validation.py:173-235` |
| "Graph는 어디 구성?" | add_node, add_edge | `uc1_validation.py:308-333` |

#### GPT 로직
| 질문 | 답변 | 파일 위치 |
|------|------|----------|
| "프롬프트는 어디?" | get_news_validation_prompt | `uc1_quality_gate.py:164-275` |
| "API 호출은?" | openai.chat.completions.create | `uc1_quality_gate.py:80-88` |
| "결과 파싱은?" | json.loads | `uc1_quality_gate.py:94` |

---

## 🎓 학습 로드맵 (LLM 없이 개발 가능하도록)

### Week 1: 기본기 다지기
**목표**: Scrapy, SQLAlchemy 공식 문서 읽고 직접 작성

#### Day 1-2: Scrapy 기본
- [ ] Scrapy Tutorial 완주 (공식 문서)
- [ ] 간단한 Spider 직접 작성 (예: 네이버 뉴스 1페이지)
- [ ] CSS Selector 연습 (개발자 도구 활용)

#### Day 3-4: SQLAlchemy ORM
- [ ] SQLAlchemy Tutorial 완주
- [ ] CrawlResult 모델 이해 (직접 쿼리 작성)
- [ ] CRUD 직접 구현 (Create, Read, Update, Delete)

#### Day 5-7: LangGraph 기본
- [ ] LangGraph Quickstart 완주
- [ ] 간단한 State Machine 직접 작성
- [ ] UC1 Validation 로직 재구현 (간소화 버전)

---

### Week 2: 코드 리뷰 & 리팩토링
**목표**: 기존 코드를 **주석 없이** 설명할 수 있도록

#### Day 1-3: 크롤러 완전 이해
- [ ] `yonhap.py` 전체 읽고 각 함수 역할 메모
- [ ] parse() 함수 흐름 다이어그램 그리기
- [ ] 페이지네이션 로직 화이트보드에 설명 (혼자)

#### Day 4-5: LangGraph 완전 이해
- [ ] `uc1_validation.py` 전체 읽고 각 Node 역할 메모
- [ ] State 변화 추적 (각 Node에서 어떤 필드 변경되는지)
- [ ] Conditional Edge 로직 화이트보드에 설명

#### Day 6-7: GPT 로직 완전 이해
- [ ] `uc1_quality_gate.py` 프롬프트 분석
- [ ] 왜 이 프롬프트가 효과적인지 설명
- [ ] GPT 없이 규칙 기반으로 대체 가능한 부분 찾기

---

### Week 3: 실전 테스트
**목표**: LLM 없이 기능 추가

#### 도전 과제 1: 새로운 사이트 추가
- [ ] 네이버 뉴스 Spider 직접 작성 (LLM 없이)
- [ ] CSS Selector 직접 찾기 (개발자 도구)
- [ ] 테스트 → 디버깅 → 성공

#### 도전 과제 2: 새로운 검증 로직 추가
- [ ] "이미지 포함 여부" 검증 Node 추가 (LLM 없이)
- [ ] State에 필드 추가
- [ ] Conditional Edge 수정

#### 도전 과제 3: 버그 수정
- [ ] 의도적으로 버그 만들기 (예: 페이지네이션 무한 루프)
- [ ] 디버깅 (print, pdb 사용)
- [ ] 수정 → 테스트

---

## 🎯 설명 가능 체크리스트

### Level 1: 기본 (1-2분 답변)
- [ ] "이 시스템이 뭐하는 건가요?"
- [ ] "왜 Scrapy를 쓰나요?"
- [ ] "데이터는 어디 저장되나요?"
- [ ] "UI는 어떻게 만들었나요?"

### Level 2: 중급 (3-5분 답변)
- [ ] "어떻게 크롤링하나요?" (리스트 → 페이지네이션 → 상세)
- [ ] "페이지네이션은 어떻게 작동하나요?"
- [ ] "중복 제거는 어떻게 하나요?"
- [ ] "GPT는 왜 쓰나요? 어떻게 쓰나요?"

### Level 3: 고급 (5-10분 답변)
- [ ] "LangGraph State 흐름 설명"
- [ ] "Conditional Edge 로직 설명"
- [ ] "증분 수집이 뭐고 왜 필요한가?"
- [ ] "타임아웃 방지는 어떻게 했나요?"

### Level 4: 전문가 (설계 설명)
- [ ] "왜 이 아키텍처를 선택했나요?"
- [ ] "다른 방법도 있었을 텐데 왜 이렇게 했나요?"
- [ ] "확장성은 어떻게 보장했나요?"
- [ ] "비용 최적화는 어떻게 했나요?"

---

## 💼 대표님께 보여줄 증거

### 1. 기술 블로그 작성
**주제**: "LangGraph로 Self-Healing 크롤러 만들기"

**구성**:
- 문제 정의 (DOM 변경 시 크롤러 깨짐)
- 해결 방법 (LangGraph State Machine)
- 코드 설명 (각 Node 역할)
- 결과 (95점 이상만 저장)

**효과**: 설명 능력 증명

---

### 2. 코드 리뷰 세션
**준비**:
1. `yonhap.py` 전체 흐름 도식화
2. 각 함수 역할 설명 (화이트보드)
3. "왜 이렇게 했나요?" 질문에 답변

**효과**: 내부 로직 이해도 증명

---

### 3. 라이브 코딩
**과제**: "네이버 뉴스 Spider 추가" (LLM 없이)

**평가 기준**:
- 30분 안에 완성
- CSS Selector 직접 찾기
- 테스트 통과

**효과**: 독립 개발 능력 증명

---

## 📌 프로젝트 핵심 개념 요약 (외우기)

### 1. Scrapy
- **비동기 HTTP 요청** 프레임워크
- Spider = 크롤링 로직 클래스
- yield = 다음 작업 예약 (Request or Item)

### 2. LangGraph
- **State 기반 워크플로우** 엔진
- Node = 작업 단위 (함수)
- Conditional Edge = 조건부 분기

### 3. GPT-4o-mini
- **품질 검증** AI (광고/보도자료 제거)
- 비용: $0.0002/기사 (매우 저렴)
- 정확도: 95% 이상

### 4. PostgreSQL
- **관계형 데이터베이스**
- SQLAlchemy ORM 사용
- CrawlResult 테이블 (기사 저장)

### 5. Gradio
- **Python 웹 UI** 프레임워크
- Blocks = 레이아웃 구성
- click event = 버튼 클릭 핸들러

---

## ✅ 다음 액션 아이템

### 즉시 (오늘)
1. [ ] 이 문서를 3번 읽고 메모
2. [ ] "어떻게 크롤링하나요?" 답변 연습 (5분)
3. [ ] `yonhap.py:157-194` 코드 읽고 각 줄 이해

### 이번 주
1. [ ] Scrapy Tutorial 완주
2. [ ] `yonhap.py` 전체 흐름 다이어그램 그리기
3. [ ] 대표님께 "크롤링 로직 설명" 요청 (15분 프레젠테이션)

### 이번 달
1. [ ] LLM 없이 네이버 뉴스 Spider 추가
2. [ ] 기술 블로그 작성
3. [ ] 라이브 코딩 테스트 통과

---

**마지막 조언**:
> "결과물보다 과정이 중요합니다. AI가 코드를 만들어줘도, 그 코드를 **왜** 이렇게 작성했는지, **어떻게** 작동하는지 설명할 수 있어야 진짜 개발자입니다."

**승진 조건 명확화**:
1. LLM 없이 기본 기능 개발 가능
2. 만든 코드를 논리 정연하게 설명 가능
3. 기본기 탄탄함을 증명

**이 문서는 당신의 로드맵입니다. 매일 체크하세요.**

---

**Last Updated**: 2025-11-04
**Status**: 인턴 → 주니어 개발자 승진 준비 중
**Goal**: LLM 의존도 낮추고 설명 가능한 개발자 되기
