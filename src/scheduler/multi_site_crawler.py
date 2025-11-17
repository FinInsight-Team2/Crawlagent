"""
CrawlAgent - Multi-Site Crawler Module
Created: 2025-11-17

다중 사이트 및 카테고리 자동화 크롤링 지원
- 동적 사이트/카테고리 선택
- Scrapy spider 검증
- 병렬 실행 지원
"""

import subprocess
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from loguru import logger

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent

# 검증된 사이트 및 카테고리 정의
VERIFIED_SITES = {
    "yonhap": {
        "name": "연합뉴스",
        "spider": "yonhap",
        "crawl_count": 827,
        "avg_quality": 94.8,
        "rating": "★★★★★",
        "categories": {
            "politics": "정치",
            "economy": "경제",
            "nk": "북한",
            "international": "국제",
            "society": "사회",
            "culture": "문화",
            "sports": "스포츠"
        }
    },
    "naver": {
        "name": "네이버 뉴스",
        "spider": "naver",
        "crawl_count": 10,
        "avg_quality": 96.0,
        "rating": "★★★★☆",
        "categories": {
            "politics": "정치",
            "economy": "경제",
            "society": "사회",
            "culture": "생활/문화",
            "world": "세계",
            "it": "IT/과학"
        }
    },
    "bbc": {
        "name": "BBC (영문)",
        "spider": "bbc",
        "crawl_count": 2,
        "avg_quality": 90.0,
        "rating": "★★★☆☆",
        "categories": {
            "uk": "UK",
            "world": "World",
            "business": "Business",
            "politics": "Politics",
            "technology": "Technology",
            "science": "Science",
            "health": "Health",
            "education": "Education"
        }
    }
}


def get_available_sites() -> List[Tuple[str, str]]:
    """
    사용 가능한 사이트 목록 반환 (Gradio CheckboxGroup용)

    Returns:
        [(label, value), ...] 형식의 리스트
    """
    sites = []
    for site_key, site_info in VERIFIED_SITES.items():
        label = site_info['name']
        sites.append((label, site_key))

    return sites


def get_site_categories(site_key: str) -> List[Tuple[str, str]]:
    """
    특정 사이트의 카테고리 목록 반환

    Args:
        site_key: 사이트 키 (yonhap, naver, bbc)

    Returns:
        [(label, value), ...] 형식의 리스트
    """
    if site_key not in VERIFIED_SITES:
        return []

    site_info = VERIFIED_SITES[site_key]
    categories = site_info.get("categories", {})

    return [(f"{kor_name} ({eng_key})", eng_key)
            for eng_key, kor_name in categories.items()]


def validate_spider_exists(site_key: str) -> bool:
    """
    Spider 파일이 실제로 존재하는지 확인

    Args:
        site_key: 사이트 키

    Returns:
        True if spider exists
    """
    spider_file = PROJECT_ROOT / "src" / "crawlers" / "spiders" / f"{site_key}.py"
    return spider_file.exists()


def validate_category(site_key: str, category: str) -> bool:
    """
    카테고리가 해당 사이트에서 유효한지 확인

    Args:
        site_key: 사이트 키
        category: 카테고리 키

    Returns:
        True if valid
    """
    if site_key not in VERIFIED_SITES:
        return False

    site_categories = VERIFIED_SITES[site_key].get("categories", {})

    # BBC는 카테고리 없음 (항상 유효)
    if not site_categories:
        return True

    return category in site_categories


def run_multi_site_crawl(
    sites: List[str],
    categories_per_site: Dict[str, List[str]],
    target_date: str = None,
    scope: str = "selected"
) -> Tuple[str, str, Dict]:
    """
    다중 사이트/카테고리 크롤링 실행

    Args:
        sites: 실행할 사이트 리스트 (["yonhap", "naver"])
        categories_per_site: 사이트별 카테고리 맵 {"yonhap": ["politics"], "naver": ["economy"]}
        target_date: 수집 날짜 (YYYY-MM-DD), None이면 어제
        scope: "selected" (선택 카테고리만) or "all" (전체 카테고리)

    Returns:
        (status_message, log_message, stats_dict)
    """
    try:
        logger.info(f"[Multi-Site Crawler] 시작: sites={sites}, scope={scope}")

        # 기본값: 어제 날짜
        if not target_date:
            yesterday = date.today() - timedelta(days=1)
            target_date = yesterday.strftime("%Y-%m-%d")

        # 검증
        for site in sites:
            if not validate_spider_exists(site):
                return (
                    "❌ 실행 실패",
                    f"Spider 파일을 찾을 수 없습니다: {site}",
                    {"success": 0, "failed": 1}
                )

        # 실행 계획 수립
        crawl_tasks = []

        for site in sites:
            site_info = VERIFIED_SITES[site]

            # scope에 따라 카테고리 결정
            if scope == "all":
                # 전체 카테고리
                categories = list(site_info.get("categories", {}).keys())
            else:
                # 선택한 카테고리만
                categories = categories_per_site.get(site, [])

            # 모든 사이트 카테고리별 실행 (BBC도 동일)
            if not categories:
                # 카테고리가 없으면 전체 크롤링 (기본 동작)
                crawl_tasks.append({
                    "site": site,
                    "category": None,
                    "target_date": target_date
                })
            else:
                for category in categories:
                    # 카테고리 검증
                    if not validate_category(site, category):
                        logger.warning(f"[Multi-Site] 유효하지 않은 카테고리 스킵: {site}/{category}")
                        continue

                    crawl_tasks.append({
                        "site": site,
                        "category": category,
                        "target_date": target_date
                    })

        if not crawl_tasks:
            return (
                "⚠️ 실행 없음",
                "실행할 크롤링 작업이 없습니다. 사이트와 카테고리를 선택하세요.",
                {"success": 0, "failed": 0}
            )

        # 실행 로그 생성
        log_lines = [
            f"🚀 다중 사이트 크롤링 시작",
            f"📅 수집 날짜: {target_date}",
            f"🎯 실행 작업 수: {len(crawl_tasks)}",
            ""
        ]

        # Scrapy 크롤링 실행
        success_count = 0
        failed_count = 0

        for task in crawl_tasks:
            site = task["site"]
            category = task["category"]

            # 명령어 구성
            cmd = ["poetry", "run", "scrapy", "crawl", site]

            # target_date 파라미터
            cmd.extend(["-a", f"target_date={target_date}"])

            # category 파라미터 (BBC 제외)
            if category:
                cmd.extend(["-a", f"category={category}"])

            # 로그
            task_name = f"{site}/{category}" if category else site
            log_lines.append(f"▶️ {task_name} 실행 중...")
            logger.info(f"[Multi-Site] 실행: {' '.join(cmd)}")

            # 실행
            try:
                result = subprocess.run(
                    cmd,
                    cwd=PROJECT_ROOT,
                    timeout=600,  # 10분 타임아웃 (대량 크롤링 대비)
                    capture_output=True,
                    text=True
                )

                if result.returncode == 0:
                    success_count += 1
                    log_lines.append(f"   ✅ {task_name} 완료")
                else:
                    failed_count += 1
                    log_lines.append(f"   ❌ {task_name} 실패 (코드: {result.returncode})")
                    logger.error(f"[Multi-Site] {task_name} stderr: {result.stderr}")

            except subprocess.TimeoutExpired:
                failed_count += 1
                log_lines.append(f"   ⏱️ {task_name} 타임아웃 (10분 초과)")
                logger.error(f"[Multi-Site] {task_name} timeout")

            except Exception as e:
                failed_count += 1
                log_lines.append(f"   ❌ {task_name} 오류: {str(e)}")
                logger.error(f"[Multi-Site] {task_name} error: {e}")

        # 결과 요약
        log_lines.extend([
            "",
            "=" * 50,
            f"✅ 성공: {success_count}",
            f"❌ 실패: {failed_count}",
            f"📊 총 작업: {len(crawl_tasks)}",
            "=" * 50
        ])

        log_message = "\n".join(log_lines)

        if failed_count == 0:
            status = f"✅ 완료 ({success_count}개 성공)"
        else:
            status = f"⚠️ 부분 완료 (성공: {success_count}, 실패: {failed_count})"

        stats = {
            "success": success_count,
            "failed": failed_count,
            "total": len(crawl_tasks),
            "target_date": target_date
        }

        logger.info(f"[Multi-Site Crawler] 완료: {stats}")

        return status, log_message, stats

    except Exception as e:
        logger.error(f"[Multi-Site Crawler] 예외 발생: {e}")
        return (
            "❌ 실행 실패",
            f"오류: {str(e)}",
            {"success": 0, "failed": 1}
        )


def get_crawl_plan_summary(
    sites: List[str],
    categories_per_site: Dict[str, List[str]],
    scope: str = "selected"
) -> str:
    """
    실행 계획 요약 생성 (실행 전 확인용)

    Args:
        sites: 사이트 리스트
        categories_per_site: 사이트별 카테고리
        scope: 수집 범위

    Returns:
        요약 문자열
    """
    lines = ["📋 실행 계획 요약", ""]

    for site in sites:
        site_info = VERIFIED_SITES.get(site, {})
        site_name = site_info.get("name", site)

        lines.append(f"🔹 {site_name} ({site})")

        if scope == "all":
            categories = list(site_info.get("categories", {}).keys())
            if categories:
                lines.append(f"   └ 전체 카테고리 ({len(categories)}개)")
            else:
                lines.append(f"   └ 카테고리 없음 (전체 수집)")
        else:
            categories = categories_per_site.get(site, [])
            if categories:
                cat_names = [site_info["categories"].get(c, c) for c in categories]
                lines.append(f"   └ 선택 카테고리: {', '.join(cat_names)}")
            else:
                lines.append(f"   └ 카테고리 선택 안 됨")

        lines.append("")

    return "\n".join(lines)
