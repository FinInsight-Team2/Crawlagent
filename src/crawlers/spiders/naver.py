"""
NewsFlow PoC - Naver News Spider (2-Stage Crawling)
Created: 2025-11-02

네이버 뉴스 크롤러 (SSR) - Section-based 2-stage crawling
- Site: https://news.naver.com
- Type: Server-Side Rendering (정적 HTML)
- Stage 1: Extract article URLs from section list pages
- Stage 2: Extract article content from detail pages

Selectors (2025-11-02 기준):
    - Title: h2#title_area
    - Body: article#dic_area
    - Date: span.media_end_head_info_datestamp_time
"""

from datetime import datetime

import scrapy

from src.storage.database import get_db
from src.storage.models import CrawlResult, Selector


class NaverSpider(scrapy.Spider):
    """
    네이버 뉴스 Spider (SSR) - 2-stage crawling

    Usage:
        # Single section
        scrapy crawl naver -a section=economy

        # All sections (default)
        scrapy crawl naver

        # Limit articles per section
        scrapy crawl naver -a max_articles=10
    """

    name = "naver"
    allowed_domains = ["news.naver.com", "n.news.naver.com"]

    # Section mapping (Naver News 섹션 코드)
    SECTIONS = {
        "politics": ("100", "정치"),
        "economy": ("101", "경제"),
        "society": ("102", "사회"),
        "culture": ("103", "생활/문화"),
        "world": ("104", "세계"),
        "it": ("105", "IT/과학"),
    }

    def __init__(self, section=None, max_articles=None, start_urls=None, *args, **kwargs):
        super(NaverSpider, self).__init__(*args, **kwargs)

        # Direct URL crawling (for Gradio UI single article crawling)
        if start_urls:
            self.start_urls = [start_urls] if isinstance(start_urls, str) else start_urls
            self.direct_crawl = True
            self.sections = []
            self.max_articles = None
            self.article_counts = {}
            self.logger.info(f"[INIT] Direct crawl mode: {self.start_urls}")
        else:
            # Section-based crawling (original behavior)
            self.direct_crawl = False

            # Section parameter handling
            if section:
                if section not in self.SECTIONS:
                    raise ValueError(
                        f"Invalid section '{section}'. Valid: {list(self.SECTIONS.keys())}"
                    )
                self.sections = [section]
            else:
                # Default: crawl all sections
                self.sections = list(self.SECTIONS.keys())

            # Max articles per section (optional)
            self.max_articles = int(max_articles) if max_articles else None

            # Build start URLs for section list pages
            self.start_urls = [
                f"https://news.naver.com/section/{self.SECTIONS[sec][0]}" for sec in self.sections
            ]

            # Article counter per section
            self.article_counts = {sec: 0 for sec in self.sections}

            self.logger.info(f"[INIT] Sections to crawl: {self.sections}")
            if self.max_articles:
                self.logger.info(f"[INIT] Max articles per section: {self.max_articles}")

        # PostgreSQL에서 Selector 로드
        db_gen = get_db()
        db = next(db_gen)
        try:
            self.selector = db.query(Selector).filter_by(site_name="naver").first()
            if not self.selector:
                raise ValueError("Selector for 'naver' not found in PostgreSQL")
            self.logger.info(f"[INIT] Loaded selector for naver")
        finally:
            db.close()

    def parse(self, response):
        """
        Stage 1: Extract article URLs from section list page
        OR
        Direct article crawling (if direct_crawl=True)

        URL pattern: https://news.naver.com/section/{section_code}
        Article URL: https://n.news.naver.com/mnews/article/{oid}/{aid}
        """
        # Direct crawl mode: crawl the article directly
        if self.direct_crawl or "/article/" in response.url:
            self.logger.info(f"[DIRECT] Crawling article directly: {response.url}")
            yield from self.parse_article(response, direct=True)
            return

        # Section-based crawling (original behavior)
        # Extract section code from URL
        section_code = response.url.split("/")[-1]
        section_name = None
        for sec, (code, name) in self.SECTIONS.items():
            if code == section_code:
                section_name = sec
                break

        if not section_name:
            self.logger.warning(f"[STAGE 1] Unknown section code: {section_code}")
            return

        self.logger.info(f"[STAGE 1] Parsing list page: {response.url}")

        # Extract article URLs (Naver News 패턴: /article/ 포함)
        article_links = response.css('a[href*="/article/"]::attr(href)').getall()

        # 중복 제거 및 comment 링크 제외
        unique_links = []
        seen_urls = set()
        for link in article_links:
            # comment 링크 제외
            if "/comment/" in link:
                continue

            # 절대 URL로 변환
            if link.startswith("/"):
                article_url = f"https://n.news.naver.com{link}"
            elif link.startswith("http"):
                article_url = link
            else:
                continue

            # 중복 제거
            if article_url not in seen_urls:
                seen_urls.add(article_url)
                unique_links.append(article_url)

        self.logger.info(
            f"[STAGE 1] Found {len(unique_links)} unique article URLs in {section_name}"
        )

        for article_url in unique_links:
            # Max articles limit check
            if self.max_articles and self.article_counts[section_name] >= self.max_articles:
                self.logger.info(
                    f"[STAGE 1] Reached max_articles limit ({self.max_articles}) for {section_name}"
                )
                break

            self.article_counts[section_name] += 1

            # Stage 2로 이동 (article 페이지 파싱)
            yield scrapy.Request(
                url=article_url, callback=self.parse_article, meta={"section": section_name}
            )

    def parse_article(self, response, direct=False):
        """
        Stage 2: Extract article content from detail page

        Selectors (2025-11-02 기준):
            - Title: h2#title_area
            - Body: article#dic_area
            - Date: span.media_end_head_info_datestamp_time
        """
        section = response.meta.get("section", "unknown" if not direct else "direct")

        self.logger.info(f"[STAGE 2] Parsing article: {response.url}")

        # Extract fields using DB selectors
        # Naver title은 h2#title_area > span 안에 있으므로 전체 텍스트 가져오기
        title_element = response.css(self.selector.title_selector).get()
        if title_element:
            from scrapy import Selector as ScrapySelector

            title_raw = ScrapySelector(text=title_element).css("::text").getall()
            title_raw = " ".join([t.strip() for t in title_raw if t.strip()])
        else:
            title_raw = None

        body_raw = response.css(f"{self.selector.body_selector}::text").getall()
        date_raw = response.css(f"{self.selector.date_selector}::text").get()

        # Clean and process
        title = title_raw if title_raw else None
        body = "\n".join([line.strip() for line in body_raw if line.strip()]) if body_raw else None
        date_str = date_raw.strip() if date_raw else None

        # Date parsing (Naver 형식: "2025.11.02. 오후 12:30")
        date = None
        if date_str:
            try:
                # "2025.11.02. 오후 12:30" → "2025-11-02"
                date_part = date_str.split(".")[0:3]  # ['2025', '11', '02']
                if len(date_part) == 3:
                    date = f"{date_part[0]}-{date_part[1]}-{date_part[2]}"
            except Exception as e:
                self.logger.warning(f"[STAGE 2] Date parsing failed: {date_str} ({e})")

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
                site_name="naver",
                category=section,
                category_kr=self.SECTIONS[section][1],
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
            "site_name": "naver",
            "section": section,
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

        # Body: 60 pts (핵심 개선!)
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
