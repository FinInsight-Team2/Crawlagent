"""
CrawlAgent - Scrapy Settings
Created: 2025-10-28
Updated: 2025-11-06

Scrapy 크롤러 설정:
- User-Agent: 한국 뉴스 사이트 크롤링용
- Download delay: 1초 (예의)
- Multi-Agent Self-Healing Crawler
"""

# Scrapy project name
BOT_NAME = "crawlagent"

# Spider modules
SPIDER_MODULES = ["src.crawlers.spiders"]
NEWSPIDER_MODULE = "src.crawlers.spiders"

# User-Agent (중요!)
# 뉴스 사이트는 User-Agent를 확인하므로 실제 브라우저처럼 보이게 설정
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Obey robots.txt
ROBOTSTXT_OBEY = False  # 뉴스 사이트는 대부분 robots.txt가 너무 제한적

# Download delay (예의)
DOWNLOAD_DELAY = 1  # 1초 대기 (사이트에 부담 주지 않기)

# Concurrent requests
CONCURRENT_REQUESTS = 1  # PoC에서는 1개씩만 (안전)
CONCURRENT_REQUESTS_PER_DOMAIN = 1

# Retry settings
RETRY_ENABLED = True
RETRY_TIMES = 3  # 최대 3회 재시도

# HTTP cache (개발 시 유용)
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 86400  # 24시간
HTTPCACHE_DIR = "httpcache"
HTTPCACHE_IGNORE_HTTP_CODES = [500, 502, 503, 504, 400, 403, 404, 408]

# Log level
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_DATEFORMAT = "%Y-%m-%d %H:%M:%S"

# 모든 사이트 SSR 검증 완료 (2025-10-29)
# scrapy-playwright 제거됨 - 단일 프레임워크 Scrapy 사용

# Item pipelines (나중에 추가 예정)
# ITEM_PIPELINES = {
#     'crawlers.pipelines.NewsflowPipeline': 300,
# }

# AutoThrottle extension (자동 속도 조절)
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1
AUTOTHROTTLE_MAX_DELAY = 3
AUTOTHROTTLE_TARGET_CONCURRENCY = 1.0

# Cookies
COOKIES_ENABLED = True

# Telnet Console (디버깅용)
TELNETCONSOLE_ENABLED = False

# Feed exports (JSON 출력 형식)
FEED_EXPORT_ENCODING = "utf-8"

# Request fingerprinter
REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
