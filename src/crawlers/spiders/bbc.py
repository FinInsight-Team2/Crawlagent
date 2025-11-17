"""
NewsFlow PoC - BBC News Spider (2-Stage Crawling)
Created: 2025-11-02

BBC 뉴스 크롤러 (SSR) - Homepage-based 2-stage crawling
- Site: https://www.bbc.com/news
- Type: Server-Side Rendering (정적 HTML)
- Stage 1: Extract article URLs from homepage
- Stage 2: Extract article content from detail pages

Selectors (2025-11-02 기준):
    - Title: h1
    - Body: div[data-component="text-block"] (multiple, 합쳐야 함)
    - Date: time[datetime]
"""

from datetime import datetime

import scrapy

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector


class BBCSpider(scrapy.Spider):
    """
    BBC News Spider (SSR) - 2-stage crawling with category support

    Usage:
        # Crawl from homepage (all categories)
        scrapy crawl bbc

        # Crawl specific category
        scrapy crawl bbc -a category=uk
        scrapy crawl bbc -a category=world
        scrapy crawl bbc -a category=politics

        # Limit number of articles
        scrapy crawl bbc -a max_articles=10 -a category=business
    """

    name = "bbc"
    allowed_domains = ["bbc.com"]

    def __init__(self, max_articles=None, category=None, *args, **kwargs):
        super(BBCSpider, self).__init__(*args, **kwargs)

        # Max articles limit (optional)
        self.max_articles = int(max_articles) if max_articles else None

        # Category support (UK, World, Business, Politics, etc.)
        self.category = category

        # Start URL: BBC News homepage or category page
        if self.category:
            self.start_urls = [f"https://www.bbc.com/news/{self.category}"]
            self.logger.info(f"[INIT] Crawling BBC category: {self.category}")
        else:
            self.start_urls = ["https://www.bbc.com/news"]
            self.logger.info(f"[INIT] Crawling BBC homepage (all categories)")

        # PostgreSQL에서 Selector 로드
        db_gen = get_db()
        db = next(db_gen)
        try:
            self.selector = db.query(Selector).filter_by(site_name="bbc").first()
            if not self.selector:
                raise ValueError("Selector for 'bbc' not found in PostgreSQL")
            self.logger.info(f"[INIT] Loaded selector for bbc")
            if self.max_articles:
                self.logger.info(f"[INIT] Max articles: {self.max_articles}")
        finally:
            db.close()

        # Article counter
        self.article_count = 0

    def parse(self, response):
        """
        Stage 1: Extract article URLs from BBC News homepage

        URL pattern: https://www.bbc.com/news/articles/{article_id}
        """
        self.logger.info(f"[STAGE 1] Parsing homepage: {response.url}")

        # Extract article URLs (BBC News 패턴: /articles/ 포함)
        article_links = response.css('a[href*="/articles/"]::attr(href)').getall()

        # 중복 제거 및 필터링
        unique_links = []
        seen_urls = set()
        for link in article_links:
            # 절대 URL로 변환
            if link.startswith("/"):
                article_url = f"https://www.bbc.com{link}"
            elif link.startswith("http"):
                article_url = link
            else:
                continue

            # /live/, /topics/ 등 제외 (실제 기사만)
            if "/live/" in article_url or "/topics/" in article_url:
                continue

            # 중복 제거
            if article_url not in seen_urls:
                seen_urls.add(article_url)
                unique_links.append(article_url)

        self.logger.info(f"[STAGE 1] Found {len(unique_links)} unique article URLs")

        for article_url in unique_links:
            # Max articles limit check
            if self.max_articles and self.article_count >= self.max_articles:
                self.logger.info(f"[STAGE 1] Reached max_articles limit ({self.max_articles})")
                break

            self.article_count += 1

            # Stage 2로 이동 (article 페이지 파싱)
            yield scrapy.Request(url=article_url, callback=self.parse_article)

    def parse_article(self, response):
        """
        Stage 2: Extract article content from detail page

        Selectors (2025-11-02 기준):
            - Title: h1
            - Body: div[data-component="text-block"] (여러 블록 합침)
            - Date: time[datetime]
        """
        self.logger.info(f"[STAGE 2] Parsing article: {response.url}")

        # Extract fields using DB selectors
        title_raw = response.css(f"{self.selector.title_selector}::text").get()

        # Body: text-block은 여러 개이므로 모두 합침 (각 블록의 모든 하위 텍스트)
        body_blocks = response.css('div[data-component="text-block"]')
        if body_blocks:
            body_texts = []
            for block in body_blocks:
                # 각 블록의 모든 텍스트 추출 (하위 태그 포함)
                texts = block.css("::text").getall()
                body_texts.extend([t.strip() for t in texts if t.strip()])
            body_raw = " ".join(body_texts) if body_texts else None
        else:
            body_raw = None

        # Date: time 태그의 datetime 속성 사용
        date_element = response.css("time[datetime]")
        date_raw = date_element.attrib.get("datetime") if date_element else None

        # Clean and process
        title = title_raw.strip() if title_raw else None
        body = body_raw

        # Date parsing (ISO 8601 형식: "2025-11-02T13:35:02.703Z")
        date = None
        if date_raw:
            try:
                # "2025-11-02T13:35:02.703Z" → "2025-11-02"
                date = date_raw.split("T")[0]
            except Exception as e:
                self.logger.warning(f"[STAGE 2] Date parsing failed: {date_raw} ({e})")

        # Quality scoring (5W1H 저널리즘 기준, UC1과 동일)
        quality_score = self.calculate_quality_score(title, body, date, response.url)

        self.logger.info(
            f"[STAGE 2] Extracted: title={bool(title)}, body={len(body) if body else 0} chars, "
            f"date={date}, score={quality_score}"
        )

        # CrawlResult 저장 (PostgreSQL)
        db_gen = get_db()
        db = next(db_gen)
        try:
            result = CrawlResult(
                url=response.url,
                site_name="bbc",
                title=title,
                body=body,
                date=date,
                quality_score=quality_score,
                crawl_mode="scrapy",
            )
            db.add(result)
            db.commit()
            self.logger.info(f"[STAGE 2] Saved to DB: {response.url}")
        except Exception as e:
            self.logger.error(f"[STAGE 2] DB save failed: {e}")
            db.rollback()
        finally:
            db.close()

        yield {
            "url": response.url,
            "site_name": "bbc",
            "title": title,
            "body": body[:100] if body else None,  # 로그용 (일부만)
            "date": date,
            "quality_score": quality_score,
        }

    def calculate_quality_score(self, title, body, date, url):
        """
        5W1H journalism quality scoring (UC1과 동일한 기준)

        배점:
            - Title: 20 pts (10자 이상)
            - Body: 60 pts (500자 이상 = 60, 200-500자 = 30)
            - Date: 10 pts
            - URL: 10 pts

        Returns:
            int: 0-100 점수
        """
        score = 0

        # Title: 20 pts
        if title and len(title) >= 10:
            score += 20

        # Body: 60 pts
        if body:
            if len(body) >= 500:
                score += 60
            elif len(body) >= 200:
                score += 30  # 부분 점수

        # Date: 10 pts
        if date:
            score += 10

        # URL: 10 pts
        if url and url.startswith("http"):
            score += 10

        return score
