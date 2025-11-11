# Validate Crawl Quality

크롤링 결과 품질을 자동으로 검증하는 스킬입니다.

## 사용 시기
- 크롤링 완료 후 데이터 품질 확인 필요 시
- 일간 수집 결과 검증
- 새로운 카테고리 또는 사이트 테스트 시

## 작업 순서

1. **DB 연결 및 통계 조회**
   ```python
   poetry run python -c "
   from src.storage.database import SessionLocal
   from src.storage.models import CrawlResult
   from datetime import date, timedelta

   session = SessionLocal()
   try:
       # 최근 24시간 크롤링 결과
       today = date.today()
       yesterday = today - timedelta(days=1)

       articles = session.query(CrawlResult).filter(
           CrawlResult.crawl_date >= yesterday
       ).all()

       if not articles:
           print('❌ 최근 24시간 크롤링 결과가 없습니다')
       else:
           count = len(articles)
           avg_quality = sum(a.quality_score for a in articles) / count

           # 카테고리별 통계
           categories = {}
           for a in articles:
               cat = a.category
               if cat not in categories:
                   categories[cat] = {'count': 0, 'quality_sum': 0}
               categories[cat]['count'] += 1
               categories[cat]['quality_sum'] += a.quality_score

           print(f'📊 총 {count}개 기사 수집')
           print(f'⭐ 평균 품질: {avg_quality:.1f}/100')
           print('\n카테고리별:')
           for cat, stats in categories.items():
               avg = stats['quality_sum'] / stats['count']
               print(f'  {cat}: {stats[\"count\"]}개 (평균 {avg:.1f}점)')
   finally:
       session.close()
   "
   ```

2. **품질 임계값 체크**
   - 평균 품질 점수 < 80: ⚠️ 경고
   - 평균 품질 점수 >= 90: ✅ 양호
   - 수집 개수 < 10: ⚠️ 데이터 부족

3. **이상치 탐지**
   - 특정 카테고리의 수집량이 0: ❌ 크롤러 오류 가능성
   - 품질 점수 급락: ❌ Selector 변경 감지 (UC2 필요)

4. **보고서 생성**
   - 통계 요약
   - 권장 사항
   - 다음 액션

## 예상 출력

```
📊 크롤링 품질 검증 보고서 (2025-11-08)
============================================
✅ 총 45개 기사 수집
⭐ 평균 품질: 94.2/100

카테고리별:
  economy: 20개 (평균 95.0점)
  politics: 15개 (평균 93.5점)
  society: 10개 (평균 93.8점)

🎯 판정: 양호
💡 권장사항: 없음
```
