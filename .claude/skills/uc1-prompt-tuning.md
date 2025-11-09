# UC1 Prompt Tuning

UC1 Quality Gate 프롬프트를 조정하고 A/B 테스트하는 스킬입니다.

## 사용 시기
- 수용률이 너무 낮을 때 (<50%)
- 수용률이 너무 높을 때 (>95%, 품질 저하 우려)
- 새로운 카테고리 추가 시

## 작업 순서

1. **현재 프롬프트 분석**
   - `src/agents/uc1_quality_gate.py` 읽기
   - 현재 decision threshold 확인 (pass/reject/uncertain)
   - 카테고리별 예시 확인

2. **최근 REJECT/UNCERTAIN 사유 분석**
   ```bash
   # 최근 크롤링 로그에서 거부 사유 추출
   grep -E "REJECT|UNCERTAIN" /tmp/crawl_*.log | \
     grep "reasoning" | \
     cut -d":" -f3- | \
     sort | uniq -c | sort -rn | head -10
   ```

3. **수용률 계산**
   ```python
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import CrawlResult
   from datetime import date

   session = SessionLocal()
   try:
       # 특정 날짜의 결과 (예: 11월 7일)
       target_date = date(2025, 11, 7)
       saved_count = session.query(CrawlResult).filter(
           CrawlResult.article_date == target_date,
           CrawlResult.category == 'economy'
       ).count()

       # 로그에서 total processed 확인 필요
       print(f'저장: {saved_count}개')
       print('(로그에서 REJECT + UNCERTAIN 개수 확인 필요)')
   finally:
       session.close()
   "
   ```

4. **프롬프트 수정 전략**

   **수용률이 너무 낮은 경우 (<50%):**
   - `**엄격하게**` → `**합리적으로**`
   - `**무조건 reject**` → `**uncertain**`
   - 카테고리 예시 확장 (엄격 → 포괄적)
   - confidence threshold 낮춤 (95 → 90)

   **수용률이 너무 높은 경우 (>95%):**
   - `**합리적으로**` → `**엄격하게**`
   - 광고/보도자료 필터링 강화
   - confidence threshold 높임 (90 → 95)

5. **수정 후 A/B 테스트**
   - 같은 날짜 데이터로 재크롤링
   - 수용률 비교
   - 품질 점수 비교

6. **최적값 찾기**
   - 목표: 70-85% 수용률
   - 평균 품질: >90점
   - UNCERTAIN 비율: 10-15% (UC2로 전달)

## 프롬프트 수정 체크리스트

- [ ] 카테고리 예시 적절한가?
- [ ] confidence threshold 적절한가?
- [ ] "무조건 reject" 문구 있는가? → uncertain으로 변경
- [ ] 소스 신뢰 로직 포함되었는가?
- [ ] Decision 규칙 명확한가?

## 예상 출력

```
📊 UC1 프롬프트 튜닝 보고서
============================
현재 설정:
  - Confidence threshold: 90
  - Decision logic: 합리적 평가
  - 소스 신뢰: 활성화

11월 7일 경제 기사 테스트:
  - 수용률: 83.3% (20/24)
  - 평균 품질: 95.0/100
  - UNCERTAIN: 16.7% (4/24) → UC2로

🎯 판정: 최적 범위 (70-85%)
💡 권장사항: 현재 설정 유지
```
