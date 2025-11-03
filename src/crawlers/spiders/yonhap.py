"""
NewsFlow PoC - Yonhap News Spider (2-Stage Crawling)
Created: 2025-10-28
Updated: 2025-10-30

연합뉴스 크롤러 (SSR) - Category-based 2-stage crawling
- Site: https://www.yna.co.kr
- Type: Server-Side Rendering (정적 HTML)
- Stage 1: Extract article URLs from category list pages
- Stage 2: Extract article content from detail pages
"""

import scrapy
import trafilatura
from datetime import datetime
from src.storage.database import get_db
from src.storage.models import Selector, CrawlResult


class YonhapSpider(scrapy.Spider):
    """
    연합뉴스 Spider (SSR) - 2-stage crawling

    Usage:
        # Single category
        scrapy crawl yonhap -a category=politics

        # All categories (default)
        scrapy crawl yonhap
    """

    name = "yonhap"
    allowed_domains = ["yna.co.kr"]

    # Category mapping
    CATEGORIES = {
        'politics': '정치',
        'economy': '경제',
        'nk': '북한',
        'international': '국제',
        'society': '사회',
        'culture': '문화',
        'sports': '스포츠'
    }

    def __init__(self, category=None, start_urls=None, *args, **kwargs):
        super(YonhapSpider, self).__init__(*args, **kwargs)

        # Direct URL crawling (for Gradio UI single article crawling)
        if start_urls:
            self.start_urls = [start_urls] if isinstance(start_urls, str) else start_urls
            self.direct_crawl = True
            self.categories = []  # Not needed for direct crawl
            self.logger.info(f"[INIT] Direct crawl mode: {self.start_urls}")
        else:
            # Category-based crawling (original behavior)
            self.direct_crawl = False

            # Category parameter handling
            if category:
                if category not in self.CATEGORIES:
                    raise ValueError(f"Invalid category '{category}'. Valid: {list(self.CATEGORIES.keys())}")
                self.categories = [category]
            else:
                # Default: crawl all categories
                self.categories = list(self.CATEGORIES.keys())

            # Build start URLs for category list pages
            self.start_urls = [
                f"https://www.yna.co.kr/{cat}/index"
                for cat in self.categories
            ]
            self.logger.info(f"[INIT] Categories to crawl: {self.categories}")

        # PostgreSQL에서 Selector 로드 (with proper session handling)
        db_gen = get_db()
        db = next(db_gen)
        try:
            self.selector = db.query(Selector).filter_by(site_name="yonhap").first()
            if not self.selector:
                raise ValueError("Selector for 'yonhap' not found in PostgreSQL")
            self.logger.info(f"[INIT] Loaded selector for yonhap")
        finally:
            db.close()

    def parse(self, response):
        """
        Stage 1: Extract article URLs from category list page
        OR
        Direct article crawling (if URL contains /view/AKR)

        Flexible URL support:
        - Single article: https://www.yna.co.kr/view/AKR20251102...
        - Category page: https://www.yna.co.kr/market-plus/index
        - Predefined category: https://www.yna.co.kr/politics/index

        Article URL pattern: /view/AKR{timestamp}
        """
        # Check if this is a single article URL
        if '/view/AKR' in response.url:
            self.logger.info(f"[DIRECT] Crawling single article: {response.url}")
            yield from self.parse_article(response, direct=True)
            return

        # Otherwise, treat as category/list page
        # Infer category from URL path
        url_parts = response.url.split('/')

        # Try to find category from predefined list first
        category = None
        category_kr = None

        for part in url_parts:
            if part in self.CATEGORIES:
                category = part
                category_kr = self.CATEGORIES[part]
                break

        # If not found in predefined categories, extract from URL
        if not category:
            # Get the path segment before 'index' or last meaningful part
            for part in reversed(url_parts):
                if part and part not in ['index', '']:
                    category = part
                    category_kr = part  # Use same value if not in predefined list
                    break

        # Fallback
        if not category:
            category = 'unknown'
            category_kr = '기타'

        self.logger.info(f"[STAGE 1] Parsing list page: {response.url} (category: {category_kr})")

        # Extract article URLs using CSS selector
        article_links = response.css('a[href*="/view/AKR"]::attr(href)').getall()

        self.logger.info(f"[STAGE 1] Found {len(article_links)} article URLs in {category_kr}")

        # Track unique article URLs to avoid duplicates
        seen_urls = set()

        for link in article_links:
            # Convert relative URL to absolute
            if link.startswith('/view/'):
                article_url = f"https://www.yna.co.kr{link}"
            elif link.startswith('http'):
                article_url = link.split('?')[0]  # Remove query params like ?section=...
            else:
                continue

            # Extract just the article ID to deduplicate
            if '/view/AKR' in article_url:
                article_id = article_url.split('/view/')[1].split('?')[0]

                if article_id in seen_urls:
                    continue
                seen_urls.add(article_id)

                # Rebuild clean URL
                clean_url = f"https://www.yna.co.kr/view/{article_id}"

                # Pass category info to Stage 2
                yield scrapy.Request(
                    clean_url,
                    callback=self.parse_article,
                    meta={
                        'category': category,
                        'category_kr': category_kr
                    }
                )

        self.logger.info(f"[STAGE 1] Queued {len(seen_urls)} unique articles from {category_kr}")

    def parse_article(self, response, direct=False):
        """
        Stage 2: Extract article content from detail page

        Article URL: https://www.yna.co.kr/view/AKR{timestamp}
        Extract: title, body, date + category info
        """
        # Direct crawl mode: infer category from URL or default
        if direct:
            category = response.meta.get('category', 'unknown')
            category_kr = response.meta.get('category_kr', '기타')
        else:
            category = response.meta['category']
            category_kr = response.meta['category_kr']

        self.logger.info(f"[STAGE 2] Crawling article: {response.url}")

        try:
            # Title: h1.tit01 (corrected selector from DOM analysis)
            title = response.css('h1.tit01::text').get()
            if not title:
                # Fallback: meta tag
                title = response.css('meta[property="og:title"]::attr(content)').get()

            # Date: meta tag (corrected selector from DOM analysis)
            date_str = response.css('meta[property="article:published_time"]::attr(content)').get()

            # Body: Trafilatura priority for ad removal
            body = trafilatura.extract(
                response.text,
                include_comments=False,
                include_tables=False,
                no_fallback=False,
                favor_precision=True,  # Ad removal priority
                favor_recall=False
            )

            # Fallback: CSS Selector if Trafilatura fails
            if not body or len(body) < 100:
                self.logger.warning(f"[STAGE 2] Trafilatura failed, using CSS selector backup")
                body_elements = response.css('article.article-wrap01 *::text').getall()
                body = ' '.join(body_elements).strip()

            # Calculate quality score (5W1H)
            quality_score = self.calculate_quality_score(title, body, date_str, response.url)

            # Data validation: only save if quality >= 80
            if quality_score < 80:
                self.logger.warning(
                    f"[STAGE 2] Low quality score {quality_score}: "
                    f"title={bool(title)}, body_len={len(body) if body else 0}, date={bool(date_str)}"
                )
                return

            # PostgreSQL에 저장 (with proper session handling)
            db_gen = get_db()
            db = next(db_gen)
            try:
                crawl_result = CrawlResult(
                    url=response.url,
                    site_name="yonhap",
                    category=category,
                    category_kr=category_kr,
                    title=title[:500] if title else None,
                    body=body[:10000] if body else None,  # Increased from 5000
                    date=date_str,
                    quality_score=quality_score,
                    crawl_mode="scrapy",
                    crawl_duration_seconds=0.0
                )
                db.add(crawl_result)
                db.commit()
            finally:
                db.close()

            self.logger.info(
                f"[SUCCESS] Saved [{category_kr}] {title[:50]}... (score: {quality_score})"
            )

            # Scrapy 출력용
            yield {
                "url": response.url,
                "site_name": "yonhap",
                "category": category,
                "category_kr": category_kr,
                "title": title[:100],
                "body_length": len(body),
                "date": date_str,
                "quality_score": quality_score,
                "status": "saved_to_db"
            }

        except Exception as e:
            self.logger.error(f"[ERROR] Failed to parse {response.url}: {e}")
            import traceback
            self.logger.error(traceback.format_exc())

    def calculate_quality_score(self, title, body, date, url):
        """
        5W1H journalism quality scoring (UC1과 동일한 기준)

        - Title (20 pts): >= 10 chars
        - Body (60 pts): >= 500 chars (full), >= 200 chars (partial 30 pts)
        - Date (10 pts): present
        - URL (10 pts): valid http

        Total: 0-100
        Threshold: 80 pts

        Updated: 2025-11-02 - UC1 Validation Agent와 점수 통일
        """
        score = 0

        # Title: 20 pts (기존 25에서 감소)
        if title and len(title) >= 10:
            score += 20

        # Body: 60 pts (기존 50에서 증가!) ← 핵심 개선!
        if body:
            if len(body) >= 500:
                score += 60
            elif len(body) >= 200:
                score += 30  # 부분 점수 (짧은 본문)

        # Date: 10 pts (기존 15에서 감소)
        if date:
            score += 10

        # URL: 10 pts (유지)
        if url and url.startswith('http'):
            score += 10

        return score
