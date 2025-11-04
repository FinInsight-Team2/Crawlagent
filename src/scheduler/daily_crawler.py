"""
CrawlAgent - Daily Crawler Scheduler
Created: 2025-11-03

APScheduler를 사용하여 매일 자동으로 어제 뉴스를 수집합니다.

Features:
- 매일 00:30에 자동 실행 (자정 이후 모든 기사 발행 완료 대기)
- 어제 날짜의 기사만 수집 (증분 수집)
- 모든 카테고리 자동 크롤링 (politics, economy, society, international)
- 크롤링 결과 로깅

Usage:
    # 스케줄러 실행 (Blocking mode - 백그라운드 계속 실행)
    poetry run python src/scheduler/daily_crawler.py

    # 수동으로 어제 뉴스 수집 테스트 (스케줄러 없이)
    poetry run python src/scheduler/daily_crawler.py --test

Environment:
    - Docker PostgreSQL: crawlagent-postgres (실행 중이어야 함)
    - Poetry 가상환경: crawlagent-6F2fBCmB-py3.11
"""

import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from loguru import logger

# 프로젝트 루트 경로 설정
PROJECT_ROOT = Path(__file__).parent.parent.parent


def run_daily_crawl():
    """
    어제 뉴스 증분 수집 실행

    - target_date: 어제 (오늘 - 1일)
    - 모든 카테고리 크롤링: politics, economy, society, international
    - 각 카테고리별로 순차 실행
    """
    yesterday = date.today() - timedelta(days=1)
    target_date_str = yesterday.strftime("%Y-%m-%d")

    logger.info("=" * 80)
    logger.info(f"[일일 크롤링 시작] 수집 날짜: {target_date_str}")
    logger.info("=" * 80)

    # 크롤링할 카테고리 목록
    categories = ["politics", "economy", "society", "international"]

    # 결과 통계
    success_count = 0
    failure_count = 0
    failed_categories = []

    for category in categories:
        logger.info(f"\n[카테고리] {category} 크롤링 시작...")

        # Scrapy 명령어 구성
        cmd = [
            "poetry",
            "run",
            "scrapy",
            "crawl",
            "yonhap",
            "-a",
            f"target_date={target_date_str}",
            "-a",
            f"category={category}",
        ]

        try:
            # Scrapy 실행 (project root에서 실행)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5분 타임아웃
                cwd=PROJECT_ROOT,  # 프로젝트 루트에서 실행
            )

            if result.returncode == 0:
                logger.success(f"[카테고리] {category} 완료 ✓")
                success_count += 1

                # Scrapy 로그에서 수집 개수 추출 (선택적)
                if "Saved" in result.stdout:
                    saved_count = result.stdout.count("SUCCESS")
                    logger.info(f"[카테고리] {category} - {saved_count}개 기사 저장")
            else:
                logger.error(f"[카테고리] {category} 실패 ✗")
                logger.error(f"[에러] {result.stderr[:500]}")  # 처음 500자만 로깅
                failure_count += 1
                failed_categories.append(category)

        except subprocess.TimeoutExpired:
            logger.error(f"[카테고리] {category} 타임아웃 (5분 초과) ✗")
            failure_count += 1
            failed_categories.append(category)
        except Exception as e:
            logger.error(f"[카테고리] {category} 예외 발생: {e} ✗")
            failure_count += 1
            failed_categories.append(category)

    # 최종 결과 요약
    logger.info("\n" + "=" * 80)
    logger.info(f"[일일 크롤링 완료] 날짜: {target_date_str}")
    logger.info(f"[결과] 성공: {success_count}/{len(categories)}, 실패: {failure_count}/{len(categories)}")

    if failed_categories:
        logger.warning(f"[실패 카테고리] {', '.join(failed_categories)}")
    else:
        logger.success("[모든 카테고리 성공] ✓")

    logger.info("=" * 80)


def main():
    """
    스케줄러 메인 함수

    - 기본 모드: 매일 00:30 자동 실행 (Blocking)
    - 테스트 모드: 즉시 1회 실행 후 종료
    """
    # 명령행 인자 확인
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        logger.info("[테스트 모드] 즉시 크롤링 실행 (스케줄러 없음)")
        run_daily_crawl()
        return

    # 프로덕션 모드: 스케줄러 실행
    logger.info("[스케줄러 시작] 매일 00:30에 어제 뉴스 자동 수집")
    logger.info(f"[프로젝트 루트] {PROJECT_ROOT}")

    scheduler = BlockingScheduler()

    # 매일 00:30에 실행
    scheduler.add_job(
        run_daily_crawl,
        trigger="cron",
        hour=0,
        minute=30,
        timezone="Asia/Seoul",  # 한국 시간
        id="daily_yonhap_crawl",
        name="연합뉴스 일일 크롤링",
        replace_existing=True,
    )

    logger.info("[스케줄러 레디] Ctrl+C로 중단 가능")
    logger.info("-" * 80)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n[스케줄러 중단] 사용자 요청으로 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
