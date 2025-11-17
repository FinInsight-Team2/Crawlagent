"""
CrawlAgent - UI Scheduler Control Module
Created: 2025-11-17

UI에서 APScheduler를 제어하기 위한 백엔드 모듈
- 스케줄러 시작/중지
- 상태 조회
- 로그 조회
- 통계 조회
"""

import os
import subprocess
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

from apscheduler.schedulers.background import BackgroundScheduler
from loguru import logger

from src.storage.database import get_db
from src.storage.models import CrawlResult

# 프로젝트 루트
PROJECT_ROOT = Path(__file__).parent.parent.parent

# Global scheduler instance
_scheduler: BackgroundScheduler = None
_scheduler_running = False


def get_scheduler() -> BackgroundScheduler:
    """Get or create global scheduler instance"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
    return _scheduler


def is_scheduler_running() -> bool:
    """Check if scheduler is running"""
    global _scheduler_running
    return _scheduler_running


def start_scheduler(schedule_time: str = "00:30") -> Tuple[str, str]:
    """
    스케줄러 시작

    Args:
        schedule_time: 실행 시각 (HH:MM 형식)

    Returns:
        (status_message, log_message)

    Example:
        >>> start_scheduler("00:30")
        ("✅ 스케줄러 시작됨", "매일 00:30에 자동 크롤링 실행")
    """
    global _scheduler_running

    try:
        # 이미 실행 중인지 확인
        if _scheduler_running:
            return "⚠️ 이미 실행 중", "스케줄러가 이미 실행 중입니다"

        # 시각 파싱
        try:
            hour, minute = schedule_time.split(":")
            hour, minute = int(hour), int(minute)
        except ValueError:
            return "❌ 잘못된 시간 형식", "시간은 HH:MM 형식이어야 합니다 (예: 00:30)"

        # 스케줄러 설정
        scheduler = get_scheduler()

        # daily_crawler.py의 run_daily_crawl 함수 임포트
        from src.scheduler.daily_crawler import run_daily_crawl

        # 작업 추가 (기존 작업 제거 후)
        if scheduler.get_job("daily_crawl"):
            scheduler.remove_job("daily_crawl")

        scheduler.add_job(
            run_daily_crawl,
            trigger="cron",
            hour=hour,
            minute=minute,
            timezone="Asia/Seoul",
            id="daily_crawl",
            name="연합뉴스 일일 크롤링",
            replace_existing=True,
        )

        # 스케줄러 시작
        if not scheduler.running:
            scheduler.start()

        _scheduler_running = True

        log_msg = f"""
✅ 스케줄러 시작 완료

⏰ 실행 시각: 매일 {schedule_time} (한국 시간)
📅 다음 실행: {get_next_run_time()}
🔄 수집 대상: 어제 날짜 뉴스 (4개 카테고리)
        """

        logger.info(f"[UI Scheduler] 스케줄러 시작: {schedule_time}")

        return "✅ 스케줄러 시작됨", log_msg.strip()

    except Exception as e:
        logger.error(f"[UI Scheduler] 시작 실패: {e}")
        return f"❌ 시작 실패", f"오류: {str(e)}"


def stop_scheduler() -> Tuple[str, str]:
    """
    스케줄러 중지

    Returns:
        (status_message, log_message)
    """
    global _scheduler_running

    try:
        if not _scheduler_running:
            return "⚠️ 실행 중 아님", "스케줄러가 실행 중이지 않습니다"

        scheduler = get_scheduler()

        # 작업 제거
        if scheduler.get_job("daily_crawl"):
            scheduler.remove_job("daily_crawl")

        # 스케줄러 종료 (다른 작업이 있을 수 있으므로 조건부)
        if scheduler.running and len(scheduler.get_jobs()) == 0:
            scheduler.shutdown(wait=False)

        _scheduler_running = False

        log_msg = "✅ 스케줄러 중지 완료"

        logger.info("[UI Scheduler] 스케줄러 중지")

        return "⏹️ 스케줄러 중지됨", log_msg

    except Exception as e:
        logger.error(f"[UI Scheduler] 중지 실패: {e}")
        return f"❌ 중지 실패", f"오류: {str(e)}"


def get_scheduler_status() -> str:
    """
    스케줄러 상태 조회

    Returns:
        상태 메시지
    """
    global _scheduler_running

    if not _scheduler_running:
        return "⏹️ 중지됨"

    scheduler = get_scheduler()
    job = scheduler.get_job("daily_crawl")

    if job is None:
        return "⚠️ 작업 없음"

    next_run = job.next_run_time
    if next_run:
        next_run_str = next_run.strftime("%Y-%m-%d %H:%M:%S")
        return f"🟢 실행 중 (다음: {next_run_str})"

    return "🟢 실행 중"


def get_next_run_time() -> str:
    """
    다음 실행 시각 조회

    Returns:
        다음 실행 시각 문자열
    """
    scheduler = get_scheduler()
    job = scheduler.get_job("daily_crawl")

    if job is None:
        return "스케줄 없음"

    next_run = job.next_run_time
    if next_run:
        return next_run.strftime("%Y-%m-%d %H:%M:%S")

    return "알 수 없음"


def run_manual_crawl() -> Tuple[str, str]:
    """
    수동 크롤링 실행 (즉시 실행) - Legacy 단일 사이트

    Returns:
        (status_message, log_message)
    """
    try:
        logger.info("[UI Scheduler] 수동 크롤링 시작")

        # daily_crawler.py --test 실행
        cmd = ["poetry", "run", "python", "src/scheduler/daily_crawler.py", "--test"]

        process = subprocess.Popen(
            cmd,
            cwd=PROJECT_ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # 비동기 실행 (백그라운드)
        # 결과는 로그 파일에서 확인

        log_msg = f"""
🚀 수동 크롤링 시작됨 (백그라운드 실행)

📅 수집 대상: 어제 날짜 뉴스
📊 진행 상황: 아래 로그에서 확인

로그는 계속 업데이트됩니다...
        """

        return "🚀 실행 중", log_msg.strip()

    except Exception as e:
        logger.error(f"[UI Scheduler] 수동 크롤링 실패: {e}")
        return f"❌ 실행 실패", f"오류: {str(e)}"


def run_multi_site_manual_crawl(
    sites: List[str],
    categories_per_site: Dict[str, List[str]],
    scope: str = "selected",
    date_list: List[str] = None
) -> Tuple[str, str]:
    """
    다중 사이트 수동 크롤링 실행 (즉시 실행)

    Args:
        sites: 사이트 리스트 (["yonhap", "naver"])
        categories_per_site: 사이트별 카테고리 {"yonhap": ["politics"], "naver": ["economy"]}
        scope: "selected" or "all"
        date_list: 크롤링할 날짜 리스트 (["2025-11-16", "2025-11-17"]). None이면 어제 날짜

    Returns:
        (status_message, log_message)
    """
    try:
        logger.info(f"[UI Scheduler] 다중 사이트 수동 크롤링: sites={sites}, scope={scope}, dates={date_list}")

        # multi_site_crawler 임포트
        from src.scheduler.multi_site_crawler import run_multi_site_crawl

        # 날짜 리스트가 없으면 어제 날짜만
        if not date_list:
            date_list = [None]  # None은 어제 날짜를 의미

        # 각 날짜별로 크롤링 실행
        all_logs = []
        total_crawled = 0

        for target_date in date_list:
            status, log, stats = run_multi_site_crawl(
                sites=sites,
                categories_per_site=categories_per_site,
                target_date=target_date,
                scope=scope
            )
            all_logs.append(f"📅 {target_date or '어제'}: {log}")
            if stats:
                total_crawled += stats.get('total_crawled', 0)

        combined_log = "\n\n".join(all_logs)
        status_msg = f"✅ 완료: 총 {total_crawled}개 기사 수집 ({len(date_list)}일치)"

        return status_msg, combined_log

    except Exception as e:
        logger.error(f"[UI Scheduler] 다중 사이트 크롤링 실패: {e}")
        return f"❌ 실행 실패", f"오류: {str(e)}"


def start_multi_site_scheduler(
    sites: List[str],
    categories_per_site: Dict[str, List[str]],
    scope: str = "selected",
    schedule_time: str = "00:30",
    frequency: str = "daily"
) -> Tuple[str, str]:
    """
    다중 사이트 스케줄러 시작

    Args:
        sites: 사이트 리스트
        categories_per_site: 사이트별 카테고리
        scope: "selected" or "all"
        schedule_time: 실행 시각 (HH:MM)
        frequency: "daily", "weekly", "monthly"

    Returns:
        (status_message, log_message)
    """
    global _scheduler_running

    try:
        # 이미 실행 중인지 확인
        if _scheduler_running:
            return "⚠️ 이미 실행 중", "스케줄러가 이미 실행 중입니다. 먼저 중지하세요."

        # 시각 파싱
        try:
            hour, minute = schedule_time.split(":")
            hour, minute = int(hour), int(minute)
        except ValueError:
            return "❌ 잘못된 시간 형식", "시간은 HH:MM 형식이어야 합니다 (예: 00:30)"

        # 사이트 검증
        if not sites:
            return "❌ 사이트 선택 필요", "최소 1개 이상의 사이트를 선택하세요."

        # 스케줄러 설정
        scheduler = get_scheduler()

        # multi_site_crawler 임포트
        from src.scheduler.multi_site_crawler import run_multi_site_crawl

        # 작업 함수 정의 (클로저로 파라미터 캡처)
        def scheduled_multi_site_crawl():
            logger.info(f"[스케줄 실행] 다중 사이트 크롤링: {sites}")
            run_multi_site_crawl(
                sites=sites,
                categories_per_site=categories_per_site,
                target_date=None,  # 어제 날짜
                scope=scope
            )

        # 기존 작업 제거
        if scheduler.get_job("multi_site_crawl"):
            scheduler.remove_job("multi_site_crawl")

        # 빈도에 따른 트리거 설정
        if frequency == "daily":
            trigger_kwargs = {
                "trigger": "cron",
                "hour": hour,
                "minute": minute,
                "timezone": "Asia/Seoul"
            }
            frequency_text = f"매일 {schedule_time}"

        elif frequency == "weekly":
            # 매주 월요일
            trigger_kwargs = {
                "trigger": "cron",
                "day_of_week": "mon",
                "hour": hour,
                "minute": minute,
                "timezone": "Asia/Seoul"
            }
            frequency_text = f"매주 월요일 {schedule_time}"

        elif frequency == "monthly":
            # 매월 1일
            trigger_kwargs = {
                "trigger": "cron",
                "day": 1,
                "hour": hour,
                "minute": minute,
                "timezone": "Asia/Seoul"
            }
            frequency_text = f"매월 1일 {schedule_time}"

        else:
            return "❌ 잘못된 빈도", f"지원하지 않는 빈도: {frequency}"

        # 작업 추가
        scheduler.add_job(
            scheduled_multi_site_crawl,
            **trigger_kwargs,
            id="multi_site_crawl",
            name="다중 사이트 자동 크롤링",
            replace_existing=True
        )

        # 스케줄러 시작
        if not scheduler.running:
            scheduler.start()

        _scheduler_running = True

        # 실행 계획 요약
        from src.scheduler.multi_site_crawler import get_crawl_plan_summary
        plan_summary = get_crawl_plan_summary(sites, categories_per_site, scope)

        log_msg = f"""
✅ 다중 사이트 스케줄러 시작 완료

⏰ 실행 빈도: {frequency_text}
📅 다음 실행: {get_next_run_time()}

{plan_summary}

🔄 수집 대상: 어제 날짜 뉴스
        """

        logger.info(f"[UI Scheduler] 다중 사이트 스케줄러 시작: {sites}, {frequency_text}")

        return "✅ 스케줄러 시작됨", log_msg.strip()

    except Exception as e:
        logger.error(f"[UI Scheduler] 다중 사이트 스케줄러 시작 실패: {e}")
        return f"❌ 시작 실패", f"오류: {str(e)}"


def get_recent_crawl_stats(days: int = 7) -> Dict:
    """
    최근 N일간 크롤링 통계 조회

    Args:
        days: 조회 기간 (일)

    Returns:
        통계 딕셔너리
    """
    try:
        db = next(get_db())

        # 날짜 범위
        start_date = date.today() - timedelta(days=days)

        # 전체 크롤링 수
        total_count = db.query(CrawlResult)\
            .filter(CrawlResult.created_at >= start_date)\
            .count()

        # 성공 크롤링 수 (quality >= 80)
        success_count = db.query(CrawlResult)\
            .filter(CrawlResult.created_at >= start_date)\
            .filter(CrawlResult.quality_score >= 80)\
            .count()

        # 성공률
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0

        # 일별 통계
        daily_stats = []
        for i in range(days):
            target_date = date.today() - timedelta(days=i)

            count = db.query(CrawlResult)\
                .filter(CrawlResult.created_at >= target_date)\
                .filter(CrawlResult.created_at < target_date + timedelta(days=1))\
                .count()

            daily_stats.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "count": count
            })

        return {
            "total_count": total_count,
            "success_count": success_count,
            "success_rate": round(success_rate, 1),
            "daily_stats": daily_stats
        }

    except Exception as e:
        logger.error(f"[UI Scheduler] 통계 조회 실패: {e}")
        return {
            "total_count": 0,
            "success_count": 0,
            "success_rate": 0,
            "daily_stats": []
        }


def get_scheduler_logs(lines: int = 50) -> str:
    """
    스케줄러 로그 조회

    Args:
        lines: 조회할 라인 수

    Returns:
        로그 문자열
    """
    try:
        log_file = PROJECT_ROOT / "logs" / "crawlagent.log"

        if not log_file.exists():
            return "로그 파일 없음"

        # 마지막 N줄 읽기
        with open(log_file, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            recent_lines = all_lines[-lines:]
            return "".join(recent_lines)

    except Exception as e:
        logger.error(f"[UI Scheduler] 로그 조회 실패: {e}")
        return f"로그 조회 실패: {str(e)}"
