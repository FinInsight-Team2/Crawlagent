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
    연합뉴스 Spider (SSR) - 2-stage crawling + Incremental Crawling

    Usage:
        # Single category
        scrapy crawl yonhap -a category=politics

        # All categories (default)
        scrapy crawl yonhap

        # Incremental crawling (특정 날짜만 수집)
        scrapy crawl yonhap -a target_date=2025-11-02

        # Incremental + category
        scrapy crawl yonhap -a target_date=2025-11-02 -a category=economy
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

    def __init__(self, category=None, start_urls=None, target_date=None, *args, **kwargs):
        super(YonhapSpider, self).__init__(*args, **kwargs)

        # 페이지네이션 추적용 카운터 (무한 루프 방지)
        self.pages_crawled = {}  # {category: page_count}
        self.MAX_PAGES_PER_CATEGORY = 15  # 카테고리당 최대 15페이지 (타임아웃 방지)

        # 날짜 기반 증분 수집 (Incremental Crawling)
        if target_date:
            from datetime import datetime
            try:
                self.target_date = datetime.strptime(target_date, "%Y-%m-%d").date()
                self.logger.info(f"[INIT] 증분 수집 모드: target_date={self.target_date}")
            except ValueError:
                raise ValueError(f"Invalid target_date format '{target_date}'. Use YYYY-MM-DD")
        else:
            self.target_date = None  # 기본 동작: 날짜 필터 없음

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

            # 카테고리 리스트 페이지 URL 생성 (페이지네이션 지원을 위해 /all 사용)
            self.start_urls = [
                f"https://www.yna.co.kr/{cat}/all"
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

        # 메인 기사 리스트에서만 기사 URL 추출 (광고/외부 섹션 제외)
        article_links = response.css('div.list-type212 a[href*="/view/AKR"]::attr(href)').getall()

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

                # NOTE: URL의 날짜(AKR20251104...)는 기사 ID 생성일이며,
                # 실제 발행일(article:published_time)과 다를 수 있음
                # 따라서 Stage 2(parse_article)에서만 날짜 필터링 수행

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

        # 큐 통계 로깅
        queued_count = len(seen_urls)
        if self.target_date:
            self.logger.info(
                f"[STAGE 1] Queued {queued_count} articles for Stage 2 (target: {self.target_date})"
            )
        else:
            self.logger.info(f"[STAGE 1] Queued {queued_count} unique articles from {category_kr}")

        # 페이지네이션: 현재 페이지 다음 번호 링크 찾기
        # <strong class="num on">1</strong> 다음의 <a class="num">2</a> 를 찾음
        current_page = response.css('div.paging-type01 strong.num.on::text').get()

        if current_page:
            try:
                current_num = int(current_page)

                # 페이지 카운터 초기화 및 증가
                if category not in self.pages_crawled:
                    self.pages_crawled[category] = 0
                self.pages_crawled[category] += 1

                # 최대 페이지 제한 체크 (타임아웃 방지)
                if self.pages_crawled[category] >= self.MAX_PAGES_PER_CATEGORY:
                    self.logger.warning(
                        f"[PAGINATION] 최대 페이지 도달 ({self.MAX_PAGES_PER_CATEGORY}페이지) - "
                        f"{category_kr} 크롤링 중단 (타임아웃 방지)"
                    )
                    return

                next_num = current_num + 1

                # 다음 페이지 번호 링크 찾기 (a.num 중에서)
                next_page = response.css(f'div.paging-type01 a.num[href*="/{next_num}"]::attr(href)').get()

                # 다음 번호가 없으면 "다음" 버튼(다음 블록) 확인
                if not next_page:
                    next_page = response.css('div.paging-type01 a.next::attr(href)').get()

                if next_page:
                    # 상대 URL을 절대 URL로 변환
                    if next_page.startswith('/'):
                        next_page_url = f"https://www.yna.co.kr{next_page}"
                    else:
                        next_page_url = next_page

                    self.logger.info(
                        f"[PAGINATION] Following page {current_num} → {next_page_url} "
                        f"({self.pages_crawled[category]}/{self.MAX_PAGES_PER_CATEGORY})"
                    )
                    yield scrapy.Request(
                        next_page_url,
                        callback=self.parse,
                        meta={
                            'category': category,
                            'category_kr': category_kr
                        }
                    )
                else:
                    self.logger.info(f"[PAGINATION] No more pages for {category_kr} (현재: {current_num}페이지)")
            except ValueError:
                self.logger.warning(f"[PAGINATION] Failed to parse current page number: {current_page}")
        else:
            self.logger.info(f"[PAGINATION] No pagination found for {category_kr}")

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

            # 날짜 기반 증분 수집 필터링
            article_date = None
            if date_str and self.target_date:
                from datetime import datetime
                try:
                    article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()

                    # 다음날 기사면 크롤링 중단
                    if article_date > self.target_date:
                        self.logger.info(
                            f"[증분 수집 중단] 기사 날짜 {article_date} > 목표 {self.target_date}"
                        )
                        return  # 이 기사 스킵하고 다음 기사 계속

                    # 이전날 기사면 스킵
                    if article_date < self.target_date:
                        self.logger.info(
                            f"[증분 수집 스킵] 기사 날짜 {article_date} < 목표 {self.target_date}"
                        )
                        return  # 오래된 기사 스킵

                    self.logger.info(f"[증분 수집 수집] 기사 날짜 {article_date} == 목표 {self.target_date}")

                except Exception as e:
                    self.logger.warning(f"[증분 수집] 날짜 파싱 실패: {date_str}, {e}")
                    # 날짜 파싱 실패 시 기본적으로 계속 수집
            elif date_str:
                # target_date가 없으면 article_date만 추출 (기존 동작)
                from datetime import datetime
                try:
                    article_date = datetime.fromisoformat(date_str.replace('Z', '+00:00')).date()
                except Exception:
                    pass

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

            # 기본 검증 (빠른 필터링 - LLM 호출 전)
            if not title or not body or len(body) < 100:
                self.logger.warning(f"[SKIP] 기본 검증 실패 (너무 짧음): title={bool(title)}, body_len={len(body) if body else 0}")
                return

            # UC1: LLM Quality Gate (핵심!)
            from src.agents.uc1_quality_gate import validate_quality

            validation = validate_quality(
                content_type="news",
                title=title,
                body=body,
                date=date_str,
                category=category,
                category_kr=category_kr,
                url=response.url
            )

            decision = validation['decision']
            confidence = validation['confidence']

            if decision == 'reject':
                self.logger.warning(
                    f"[REJECT] {validation['reasoning']} (confidence: {confidence})"
                )
                return  # DB에 저장 안 함!

            if decision == 'uncertain':
                self.logger.info(f"[UNCERTAIN] UC2 발동 예정 (confidence: {confidence})")
                # TODO: UC2 발동 (추후 구현)
                return  # 임시로 uncertain도 reject

            # decision == 'pass'
            self.logger.info(f"[PASS] confidence: {confidence}")

            # PostgreSQL에 저장 (검증 완료된 데이터만!)
            db_gen = get_db()
            db = next(db_gen)
            try:
                from datetime import date as date_type

                # 중복 체크 (URL 기준)
                existing = db.query(CrawlResult).filter_by(url=response.url).first()
                if existing:
                    self.logger.warning(f"[DUPLICATE] URL already exists: {response.url}")
                    db.close()
                    return  # 중복이면 저장하지 않음

                crawl_result = CrawlResult(
                    url=response.url,
                    site_name="yonhap",
                    category=category,
                    category_kr=category_kr,
                    title=title[:500] if title else None,
                    body=body[:10000] if body else None,
                    date=date_str,
                    quality_score=confidence,  # LLM confidence로 대체!
                    crawl_mode="scrapy",
                    crawl_duration_seconds=0.0,
                    # 증분 수집 필드
                    crawl_date=date_type.today(),
                    article_date=article_date,
                    is_latest=True,
                    # Phase 2: 품질 검증 필드 (NEW!)
                    content_type="news",
                    validation_status="verified",  # UC1 검증 완료
                    validation_method="llm",
                    llm_reasoning=validation['reasoning']
                )
                db.add(crawl_result)
                db.commit()
            finally:
                db.close()

            self.logger.info(
                f"[SUCCESS] Saved [{category_kr}] {title[:50]}... (confidence: {confidence})"
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
                "quality_score": confidence,
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
