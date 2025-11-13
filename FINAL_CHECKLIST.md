# CrawlAgent PoC 최종 검증 체크리스트

**작성일**: 2025-11-12
**목적**: 데모 전 최종 검증

---

## ✅ 완료된 작업

### 1. Few-Shot Learning v2.0 구현
- [x] Few-Shot Retriever 구현 ([src/agents/few_shot_retriever.py](src/agents/few_shot_retriever.py))
- [x] UC2/UC3 통합
- [x] Tavily/Firecrawl 제거 → $0 비용
- [x] 패턴 분석 알고리즘 (ID, class, nested, semantic)

### 2. DB 초기 데이터
- [x] 7개 사이트 Selector 준비
  - 연합뉴스, BBC, 네이버뉴스, Reuters, 한국경제 등
- [x] Few-Shot Examples 검증 완료

### 3. 문서화
- [x] [AI_WORKFLOW_ARCHITECTURE.md](docs/AI_WORKFLOW_ARCHITECTURE.md) 업데이트
- [x] [DEMO_GUIDE.md](DEMO_GUIDE.md) 작성
- [x] [DEMO_STRATEGY.md](DEMO_STRATEGY.md) 작성
- [x] [PRD_CrawlAgent_2025-11-06.md](docs/PRD_CrawlAgent_2025-11-06.md) 참조

---

## 🔄 진행 중

### 4. 실제 데이터 수집
- [ ] 연합뉴스 크롤링 (진행 중...)
- [ ] BBC 크롤링
- [ ] 네이버뉴스 크롤링
- [ ] 크롤링 결과 검증

### 5. Gradio UI 테스트
- [ ] UI 접속 확인 (http://localhost:7860)
- [ ] Few-Shot Examples 표시 확인
- [ ] UC3 탭 기능 테스트
- [ ] 에러 핸들링 확인

---

## 📋 최종 검증 항목

### A. 데이터 검증

```bash
# 1. Selector 개수 확인
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import Selector
db = next(get_db())
print(f'Total selectors: {db.query(Selector).count()}')
"

# 2. CrawlResult 개수 확인
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import CrawlResult
db = next(get_db())
print(f'Total articles: {db.query(CrawlResult).count()}')
"

# 3. Few-Shot Examples 확인
poetry run python -c "
from src.agents.few_shot_retriever import get_few_shot_examples
examples = get_few_shot_examples(limit=5)
print(f'Few-Shot examples: {len(examples)}')
"
```

**목표**:
- Selectors: ≥ 7개
- Articles: ≥ 10개 (데모용)
- Few-Shot: 5개

---

### B. 기능 검증

#### B-1. Few-Shot Retriever

```bash
poetry run python -c "
from src.agents.few_shot_retriever import get_few_shot_examples, format_few_shot_prompt

examples = get_few_shot_examples(limit=3)
for ex in examples:
    print(f\"{ex['site_name']}: {ex['title_selector']}\")

prompt = format_few_shot_prompt(examples)
print(f\"\\nPrompt length: {len(prompt)} chars\")
"
```

**기대 결과**:
- 3개 사이트 패턴 출력
- Prompt 길이: 500-1000자

---

#### B-2. UC1 품질 검증

```bash
# 최근 기사 품질 점수 확인
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import CrawlResult

db = next(get_db())
results = db.query(CrawlResult).order_by(CrawlResult.created_at.desc()).limit(5).all()

print('Recent articles:')
for r in results:
    print(f'  {r.site_name}: {r.quality_score}/100')
"
```

**기대 결과**:
- 모든 기사 quality_score ≥ 95

---

#### B-3. Gradio UI

**수동 테스트**:
1. 브라우저에서 http://localhost:7860 접속
2. "Developer Tools" 탭 → "Show Few-Shot Examples" 클릭
3. UC3 탭 → URL 입력 (연합뉴스 기사) → "Discover Selectors"
4. 결과 확인

**기대 결과**:
- Few-Shot Examples 표시
- UC3 실행 (30-60초)
- Consensus Score 표시

---

### C. 성능 지표 확인

```bash
# Selector별 성공률
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import Selector

db = next(get_db())
selectors = db.query(Selector).all()

print('\\nSelector Performance:')
print(f\"{'Site':<15} {'Success':<10} {'Failure':<10} {'Rate':<10}\")
print('-' * 45)

for sel in selectors:
    total = sel.success_count + sel.failure_count
    rate = sel.success_count / total * 100 if total > 0 else 0
    print(f\"{sel.site_name:<15} {sel.success_count:<10} {sel.failure_count:<10} {rate:<10.1f}%\")
"
```

**기대 결과**:
- 대부분 사이트 성공률 ≥ 80%

---

## 🎯 데모 준비 최종 확인

### 필수 항목
- [ ] PostgreSQL 실행 중
- [ ] Gradio UI 실행 중 (포트 7860)
- [ ] DB에 Selectors ≥ 7개
- [ ] DB에 Articles ≥ 10개
- [ ] Few-Shot Examples 작동
- [ ] 데모 URL 준비 (연합뉴스, BBC)
- [ ] [DEMO_GUIDE.md](DEMO_GUIDE.md) 리뷰

### 선택 항목
- [ ] 스크린 레코딩 백업
- [ ] LangSmith Trace URL 준비
- [ ] 슬라이드 자료

---

## 🐛 알려진 이슈

### 1. 외부 URL 접근 제한
- **문제**: CNN, Reuters 등이 User-Agent 체크
- **대응**: DB에 있는 사이트(연합뉴스, BBC, 네이버)로 데모

### 2. Consensus 실패 가능성
- **문제**: UC3 Consensus Score < 0.55
- **대응**: "Human Review로 넘어감" 설명 + 정확도 80% 강조

### 3. LLM API 에러
- **문제**: OpenAI/Gemini API 장애
- **대응**: 사전 실행 결과 스크린샷 준비

---

## 📊 예상 데모 지표

| Metric | Target | Current |
|--------|--------|---------|
| Selectors in DB | ≥ 7 | 7 ✅ |
| Articles in DB | ≥ 10 | TBD |
| Few-Shot Examples | 5 | 5 ✅ |
| UC1 Quality Rate | ≥ 95% | TBD |
| Gradio Running | Yes | Yes ✅ |

---

## 🚀 Next Steps

1. **크롤링 완료 대기** (10분)
2. **결과 검증** (`check_crawl_results.py`)
3. **Gradio 데모 1회 실행** (UC3)
4. **문서 최종 리뷰**
5. **Git 커밋** (당신이 직접!)

---

**Status**: 🟡 In Progress
**ETA**: 30분

---

## 📞 Contact

문제 발생 시:
1. 백그라운드 작업 확인: `jobs`
2. 로그 확인: `tail -f crawlagent/logs/*.log`
3. DB 상태 확인: `psql -U crawlagent_user -d crawlagent_db`
