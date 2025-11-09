# Test UC2 Self-Healing Flow

UC2 Self-Healing 전체 플로우를 End-to-End 테스트하는 스킬입니다.

## 사용 시기
- UC2 구현 완료 후 검증
- 새로운 사이트 추가 시
- Selector 변경 감지 후

## UC2 플로우 개요

```
[UC1 연속 3회 실패]
       ↓
[GPT-4o Proposer]
  - HTML 재분석
  - 3개 CSS Selector 제안
  - confidence 계산
       ↓
[Gemini Validator]
  - 샘플 10개 추출 테스트
  - 각 Selector 검증
  - valid/invalid 판단
       ↓
[2-Agent Consensus]
  - confidence >= 0.7 AND valid = true
  - 합의 도달: Selector 자동 업데이트
  - 합의 실패: HITL (Human Review)
       ↓
[DecisionLog 저장]
  - Gradio UI "UC2 Self-Healing" 탭에서 확인
```

## 작업 순서

1. **테스트 환경 준비**
   ```bash
   # Selector 의도적으로 변조
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import Selector

   session = SessionLocal()
   try:
       selector = session.query(Selector).filter_by(site_name='yonhap').first()
       if selector:
           # 백업
           print(f'백업: {selector.title_selector}')

           # 변조 (틀린 Selector)
           selector.title_selector = 'h1.INVALID_SELECTOR'
           selector.body_selector = 'div.INVALID_BODY'
           session.commit()
           print('✅ Selector 변조 완료 (UC2 테스트용)')
   finally:
       session.close()
   "
   ```

2. **UC2 트리거 확인**
   ```bash
   # 크롤링 시작 (UC1이 3회 연속 실패하면 UC2 트리거)
   poetry run scrapy crawl yonhap -a category=economy -s CLOSESPIDER_ITEMCOUNT=10
   ```

3. **DecisionLog 확인**
   ```python
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import DecisionLog

   session = SessionLocal()
   try:
       logs = session.query(DecisionLog).order_by(
           DecisionLog.created_at.desc()
       ).limit(5).all()

       if not logs:
           print('❌ DecisionLog가 없습니다 (UC2 미트리거)')
       else:
           print(f'📋 최근 DecisionLog {len(logs)}개:')
           for log in logs:
               print(f'  ID={log.id}, Consensus={log.consensus_reached}')
               if log.gpt_analysis:
                   print(f'    GPT: {log.gpt_analysis.get(\"title_selector\", \"N/A\")}')
               if log.gemini_validation:
                   print(f'    Gemini: valid={log.gemini_validation.get(\"valid\", \"N/A\")}')
   finally:
       session.close()
   "
   ```

4. **Gradio UI에서 Human Review**
   - Gradio 실행: `poetry run python src/ui/app.py`
   - "UC2 Self-Healing" 탭으로 이동
   - "새로고침" 클릭
   - 제안된 Selector 검토
   - ✅ 승인 또는 ❌ 거부

5. **Selector 복구 확인**
   ```python
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import Selector

   session = SessionLocal()
   try:
       selector = session.query(Selector).filter_by(site_name='yonhap').first()
       print(f'현재 Title Selector: {selector.title_selector}')
       print(f'현재 Body Selector: {selector.body_selector}')
       print(f'최종 수정: {selector.updated_at}')
   finally:
       session.close()
   "
   ```

6. **재크롤링으로 검증**
   ```bash
   # 복구된 Selector로 정상 크롤링 확인
   poetry run scrapy crawl yonhap -a category=economy -s CLOSESPIDER_ITEMCOUNT=5

   # 성공 여부 확인
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import CrawlResult
   from datetime import date

   session = SessionLocal()
   try:
       today_count = session.query(CrawlResult).filter(
           CrawlResult.crawl_date == date.today()
       ).count()

       if today_count >= 5:
           print(f'✅ UC2 Self-Healing 성공! ({today_count}개 저장)')
       else:
           print(f'❌ 여전히 실패 ({today_count}개만 저장)')
   finally:
       session.close()
   "
   ```

## 성공 기준

- [x] UC1 연속 3회 실패 시 UC2 트리거
- [x] DecisionLog 생성 (gpt_analysis + gemini_validation)
- [x] Gradio UI에서 Human Review 가능
- [x] 승인 시 Selector 자동 업데이트
- [x] 재크롤링 시 정상 작동 (품질 >90)

## KPI

- **복구 시간**: <1시간 (목표)
- **복구 성공률**: >80%
- **자동 합의율**: >50% (Human Review 최소화)

## 예상 출력

```
🧪 UC2 Self-Healing E2E 테스트
===============================
[Step 1] Selector 변조 완료
[Step 2] 크롤링 시작... UC1 3회 실패 대기
[Step 3] ✅ UC2 트리거 확인 (DecisionLog ID=1)
[Step 4] GPT 제안: h1.tit01, div.article-wrap01
[Step 5] Gemini 검증: valid=true (10/10 샘플)
[Step 6] ⚠️ 자동 합의 실패 (confidence=0.65 < 0.7)
[Step 7] 💬 Human Review 필요 → Gradio UI
[Step 8] ✅ Human 승인 완료
[Step 9] ✅ Selector 업데이트 (h1.tit01)
[Step 10] ✅ 재크롤링 성공 (5/5 저장)

🎯 UC2 Self-Healing 성공!
⏱️ 총 소요 시간: 45초
```

## Troubleshooting

**DecisionLog가 생성 안 됨:**
- UC1이 3회 연속 실패하지 않았을 가능성
- `yonhap.py`의 `trigger_uc2_workflow()` 확인

**Gemini 429 에러:**
- Rate Limit 도달 → 잠시 대기
- Tier 1 키 사용 확인

**Selector 업데이트 안 됨:**
- Human Review에서 승인했는지 확인
- `approve_decision()` 함수 로그 확인
