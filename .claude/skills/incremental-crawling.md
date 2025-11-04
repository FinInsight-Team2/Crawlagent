# 증분 수집 구현 가이드 (Incremental Crawling)

## 목적
CrawlAgent에 날짜 기반 증분 수집 기능을 구현합니다. 특정 날짜의 기사만 수집하고, 다음날 기사가 나타나면 자동으로 중단합니다.

## 프로젝트 위치
**작업 디렉토리**: `/Users/charlee/Desktop/Intern/crawlagent`

## 목표
매일 스케줄 크롤링을 위해:
1. 특정 날짜의 기사만 수집 (예: 2025-11-02)
2. 다음날 기사 발견 시 자동 중단 (2025-11-03)
3. 중복 수집 방지
4. 카테고리별 수집 지원 (정치, 경제, 스포츠 등)

## 구현 전략

### 추천 방식: Spider에 target_date 파라미터 추가

```python
# src/crawlers/spiders/yonhap.py

class YonhapSpider(scrapy.Spider):
    def __init__(self, target_date=None, category=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # 목표 날짜 파싱 (형식: YYYY-MM-DD)
        if target_date:
            from datetime import datetime
            self.target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
            self.logger.info(f"[초기화] 목표 날짜: {self.target_date}")
        else:
            self.target_date = None  # 모든 기사 수집 (기본값)

    def parse_article(self, response, direct=False):
        """기사 추출 및 날짜 확인"""

        # 날짜 추출
        date_str = response.css('meta[property="article:published_time"]::attr(content)').get()

        # 날짜 객체로 변환
        if date_str and self.target_date:
            from datetime import datetime
            try:
                article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()

                # 다음날 기사면 중단
                if article_date > self.target_date:
                    self.logger.info(f"[중단] 기사 날짜 {article_date} > 목표 {self.target_date}")
                    return  # 크롤링 중단

                # 이전날 기사면 스킵
                if article_date < self.target_date:
                    self.logger.info(f"[스킵] 기사 날짜 {article_date} < 목표 {self.target_date}")
                    return  # 오래된 기사 스킵

            except Exception as e:
                self.logger.warning(f"[날짜] 파싱 실패: {date_str}, {e}")

        # 정상 크롤링 계속...
```

### 사용법
```bash
# 특정 날짜 수집
scrapy crawl yonhap -a target_date=2025-11-02

# 특정 날짜 + 카테고리
scrapy crawl yonhap -a target_date=2025-11-02 -a category=politics

# 기본 동작 (날짜 필터 없음)
scrapy crawl yonhap
```

## DB 스키마 확장

### 필수 필드 (높은 우선순위)

```sql
-- 마이그레이션 스크립트: scripts/migrations/001_add_incremental_fields.sql
ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,           -- 수집 날짜
ADD COLUMN article_date DATE,         -- 기사 발행 날짜
ADD COLUMN is_latest BOOLEAN DEFAULT true;  -- 최신 버전 여부

CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);
```

### SQLAlchemy 모델 업데이트

```python
# src/storage/models.py

from sqlalchemy import Date

class CrawlResult(Base):
    __tablename__ = "crawl_results"

    # ... 기존 필드 ...

    # 증분 수집 필드
    crawl_date = Column(Date, nullable=True, index=True, comment="수집 날짜")
    article_date = Column(Date, nullable=True, index=True, comment="기사 발행 날짜")
    is_latest = Column(Boolean, default=True, nullable=False, index=True, comment="최신 버전")
```

### 선택 필드 (향후 확장용)

SNS/동적 콘텐츠 지원용:

```sql
ALTER TABLE crawl_results
ADD COLUMN content_type VARCHAR(50) DEFAULT 'news',  -- 'news', 'sns', 'blog'
ADD COLUMN metadata JSONB,                            -- 유연한 JSON 저장
ADD COLUMN version INTEGER DEFAULT 1,                 -- 동일 URL 버전 번호
ADD COLUMN last_updated TIMESTAMP;                    -- 마지막 업데이트 시각

CREATE INDEX idx_content_type ON crawl_results(content_type);
CREATE INDEX idx_metadata ON crawl_results USING GIN (metadata);
```

## Spider 수정 체크리스트

### 1. 날짜 추출 (이미 구현됨)
```python
# yonhap.py가 이미 날짜 추출함
date_str = response.css('meta[property="article:published_time"]::attr(content)').get()
```

### 2. 날짜 비교 로직 (추가 필요)
```python
from datetime import datetime

def should_crawl_article(self, article_date_str, target_date):
    """
    날짜 기반으로 기사 수집 여부 결정

    반환값:
        - True: 이 기사 수집
        - False: 이 기사 스킵
        - None: 크롤링 중단 (다음날 도달)
    """
    if not target_date:
        return True  # 필터 없음, 모두 수집

    try:
        article_date = datetime.fromisoformat(article_date_str.replace('Z', '+00:00')).date()

        if article_date > target_date:
            self.logger.info(f"[중단] 다음날 감지: {article_date}")
            raise CloseSpider(f"다음날 기사 도달: {article_date}")

        if article_date < target_date:
            self.logger.info(f"[스킵] 오래된 기사: {article_date}")
            return False

        return True  # 같은 날, 수집

    except Exception as e:
        self.logger.warning(f"날짜 파싱 실패: {e}")
        return True  # 파싱 실패 시 기본적으로 수집
```

### 3. DB 저장 로직 업데이트
```python
# parse_article 메서드 내부
from datetime import datetime, date

# 날짜 계산
crawl_date = date.today()  # 오늘
article_date = None
if date_str:
    try:
        article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
    except:
        pass

# DB 저장
crawl_result = CrawlResult(
    url=response.url,
    site_name="yonhap",
    # ... 기존 필드 ...
    crawl_date=crawl_date,
    article_date=article_date,
    is_latest=True
)
```

## 스케줄러 통합

### 매일 자동 실행 예시

```python
# src/scheduler/daily_crawler.py (생성 필요)

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import date, timedelta
import subprocess

def run_daily_crawl():
    """어제 뉴스 수집 실행"""
    yesterday = date.today() - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")

    print(f"[스케줄러] {target_date} 일일 크롤링 시작")

    # 모든 카테고리 실행
    categories = ['politics', 'economy', 'society', 'international']

    for category in categories:
        cmd = [
            "poetry", "run", "scrapy", "crawl", "yonhap",
            "-a", f"target_date={target_date}",
            "-a", f"category={category}"
        ]

        print(f"[스케줄러] 실행 중: {category}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            print(f"[스케줄러] {category} 완료")
        else:
            print(f"[스케줄러] {category} 실패: {result.stderr}")

if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # 매일 00:30에 실행 (자정 이후 모든 기사 발행 완료)
    scheduler.add_job(run_daily_crawl, 'cron', hour=0, minute=30)

    print("[스케줄러] 일일 크롤러 시작. 매일 00:30 실행.")
    scheduler.start()
```

## 테스트 전략

### 수동 테스트
```bash
# 특정 날짜 테스트
poetry run scrapy crawl yonhap -a target_date=2025-11-02 -a category=politics

# 수집된 내용 확인
poetry run python -c "
from src.storage.database import get_db
from src.storage.models import CrawlResult
db = next(get_db())
results = db.query(CrawlResult).filter_by(article_date='2025-11-02').all()
print(f'{len(results)}개 기사 발견 (2025-11-02)')
for r in results[:5]:
    print(f'  - {r.title[:50]}')
"
```

### 자동화 테스트 케이스
1. **당일**: target_date의 모든 기사 수집되어야 함
2. **다음날 경계**: article_date > target_date 시 중단
3. **이전날**: article_date < target_date 시 스킵
4. **날짜 필터 없음**: 기존처럼 동작 (모두 수집)
5. **잘못된 날짜**: 우아하게 처리 (경고 로그, 계속)

## 마이그레이션 단계

### 1단계: DB 필드 추가 (15분)
```bash
# 마이그레이션 생성
mkdir -p scripts/migrations
cat > scripts/migrations/001_add_incremental_fields.sql << 'EOF'
-- 증분 수집 필드 추가
ALTER TABLE crawl_results
ADD COLUMN crawl_date DATE,
ADD COLUMN article_date DATE,
ADD COLUMN is_latest BOOLEAN DEFAULT true;

CREATE INDEX idx_crawl_date ON crawl_results(crawl_date);
CREATE INDEX idx_article_date ON crawl_results(article_date);
CREATE INDEX idx_is_latest ON crawl_results(is_latest);
EOF

# 마이그레이션 적용
docker exec -i crawlagent-postgres psql -U crawlagent -d crawlagent < scripts/migrations/001_add_incremental_fields.sql
```

### 2단계: 모델 업데이트 (10분)
`src/storage/models.py` 수정하여 새 필드 추가

### 3단계: Spider 업데이트 (30분)
`src/crawlers/spiders/yonhap.py` 수정:
- `target_date` 파라미터 추가
- 날짜 비교 로직 추가
- DB 저장 시 날짜 포함

### 4단계: 테스트 (20분)
특정 날짜로 테스트 크롤링 실행

### 5단계: 스케줄러 생성 (선택, 15분)
`src/scheduler/daily_crawler.py` 생성

## 이점

1. **효율성**: 새 기사만 수집 (중복 없음)
2. **히스토리 데이터**: 필요 시 특정 날짜 백필 가능
3. **스케줄링**: 매일 자정 어제 뉴스 자동 수집
4. **모니터링**: crawl_date vs article_date로 지연 감지
5. **버전 관리**: 동일 기사의 여러 버전 보관 (업데이트 시)

## 참고 자료

- Spider 구현: `src/crawlers/spiders/yonhap.py`
- DB 모델: `src/storage/models.py`
- Python dateutil: 이미 설치됨 (버전 2.9.0)
- APScheduler: 설치 필요 (`poetry add apscheduler`)
