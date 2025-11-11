# Scheduler Implementation Skill

## Context
You are implementing a scheduling system for CrawlAgent to run automated daily news collection.

## Project Location
**Working Directory**: `/Users/charlee/Desktop/Intern/crawlagent`

## Technology Choice: APScheduler (Recommended)

### Why APScheduler?
- **Python Native**: No external services needed (Redis, RabbitMQ)
- **Simple**: ~20 lines of code to get started
- **Flexible**: Cron-style scheduling or interval-based
- **Persistent**: Can use SQLite backend for job persistence
- **PoC-Ready**: Perfect for proof-of-concept stage

### Installation
```bash
poetry add apscheduler
```

## Basic Implementation Pattern

### Simple Blocking Scheduler (Easiest)

```python
# src/scheduler/daily_crawler.py

from apscheduler.schedulers.blocking import BlockingScheduler
from datetime import date, timedelta
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def crawl_yesterday_news():
    """
    Crawl yesterday's news at 00:30 every day

    Why yesterday? Most news sites finalize article timestamps by midnight.
    """
    yesterday = date.today() - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")

    logger.info(f"Starting daily crawl for {target_date}")

    # Crawl all categories
    categories = ['politics', 'economy', 'society', 'international', 'culture', 'sports']

    for category in categories:
        cmd = [
            "poetry", "run", "scrapy", "crawl", "yonhap",
            "-a", f"target_date={target_date}",
            "-a", f"category={category}"
        ]

        logger.info(f"Crawling {category}...")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/Users/charlee/Desktop/Intern/crawlagent")

        if result.returncode == 0:
            logger.info(f"{category} completed successfully")
        else:
            logger.error(f"{category} failed: {result.stderr[:200]}")

    logger.info(f"Daily crawl for {target_date} completed")


if __name__ == "__main__":
    scheduler = BlockingScheduler()

    # Run every day at 00:30 (cron-style)
    scheduler.add_job(
        crawl_yesterday_news,
        'cron',
        hour=0,
        minute=30,
        id='daily_news_crawl',
        name='Daily News Collection',
        replace_existing=True
    )

    logger.info("Daily crawler scheduler started")
    logger.info("Next run: 00:30 tomorrow")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")
```

### Run Scheduler
```bash
# Start scheduler (blocks terminal)
poetry run python src/scheduler/daily_crawler.py

# Or run in background (macOS/Linux)
nohup poetry run python src/scheduler/daily_crawler.py &

# Or use screen
screen -S crawler
poetry run python src/scheduler/daily_crawler.py
# Ctrl+A, D to detach
```

## Advanced Pattern: Background Scheduler (Non-Blocking)

For running alongside Gradio UI:

```python
# src/scheduler/background_scheduler.py

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from datetime import date, timedelta
import subprocess
import logging

logger = logging.getLogger(__name__)

class CrawlerScheduler:
    """Background scheduler for automated crawling"""

    def __init__(self):
        # Persistent job store (survives restarts)
        jobstores = {
            'default': SQLAlchemyJobStore(url='sqlite:///scheduler.db')
        }

        self.scheduler = BackgroundScheduler(jobstores=jobstores)
        self.scheduler.start()

    def add_daily_job(self, hour=0, minute=30):
        """Add daily crawl job"""
        self.scheduler.add_job(
            func=self._crawl_yesterday,
            trigger='cron',
            hour=hour,
            minute=minute,
            id='daily_crawl',
            replace_existing=True
        )
        logger.info(f"Daily job scheduled at {hour:02d}:{minute:02d}")

    def _crawl_yesterday(self):
        """Execute daily crawl"""
        yesterday = date.today() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

        logger.info(f"[SCHEDULER] Crawling {target_date}")

        # Run Scrapy
        subprocess.run([
            "poetry", "run", "scrapy", "crawl", "yonhap",
            "-a", f"target_date={target_date}"
        ])

    def get_next_run_time(self):
        """Get next scheduled run time"""
        job = self.scheduler.get_job('daily_crawl')
        return job.next_run_time if job else None

    def pause(self):
        """Pause scheduler"""
        self.scheduler.pause()

    def resume(self):
        """Resume scheduler"""
        self.scheduler.resume()

    def shutdown(self):
        """Shutdown scheduler"""
        self.scheduler.shutdown()


# Usage in Gradio app
# src/ui/app.py

from src.scheduler.background_scheduler import CrawlerScheduler

# Global scheduler instance
scheduler = CrawlerScheduler()
scheduler.add_daily_job(hour=0, minute=30)

def start_scheduler():
    scheduler.resume()
    return f"Scheduler started. Next run: {scheduler.get_next_run_time()}"

def stop_scheduler():
    scheduler.pause()
    return "Scheduler paused"

# Add to Gradio UI
with gr.Tab("Scheduler"):
    status = gr.Textbox(value=f"Next run: {scheduler.get_next_run_time()}")
    start_btn = gr.Button("Start")
    stop_btn = gr.Button("Stop")

    start_btn.click(fn=start_scheduler, outputs=[status])
    stop_btn.click(fn=stop_scheduler, outputs=[status])
```

## Alternative: System Cron (Production)

### Advantages
- OS-level reliability
- No Python process needed
- Automatic restart after reboot (if configured)

### Setup
```bash
# Edit crontab
crontab -e

# Add this line (runs at 00:30 daily)
30 0 * * * cd /Users/charlee/Desktop/Intern/crawlagent && /usr/local/bin/poetry run python src/scheduler/run_daily.py >> /var/log/crawler.log 2>&1
```

### Simple Script for Cron
```python
# src/scheduler/run_daily.py

from datetime import date, timedelta
import subprocess
import sys

def main():
    yesterday = date.today() - timedelta(days=1)
    target_date = yesterday.strftime("%Y-%m-%d")

    print(f"[{date.today()}] Crawling {target_date}", file=sys.stderr)

    result = subprocess.run([
        "poetry", "run", "scrapy", "crawl", "yonhap",
        "-a", f"target_date={target_date}"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        print(f"Success: {result.stdout}", file=sys.stderr)
    else:
        print(f"Failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
```

## Scheduler Comparison Table

| Feature | APScheduler | Celery Beat | Cron | GitHub Actions |
|---------|-------------|-------------|------|----------------|
| **Setup Time** | 5 min | 30 min | 10 min | 15 min |
| **Complexity** | Low | High | Very Low | Medium |
| **Dependencies** | None | Redis/RabbitMQ | None | GitHub repo |
| **Python Integration** | Excellent | Excellent | Poor | N/A |
| **UI Control** | Easy | Medium | Hard | N/A |
| **Monitoring** | Built-in | Flower | Logs | GitHub UI |
| **Production Ready** | Yes | Yes | Yes | No (rate limits) |
| **Best For** | PoC, Small | Large scale | Server | CI/CD only |

## Recommended Approach for CrawlAgent

### Phase 1: Development (Now)
**Use**: APScheduler BlockingScheduler
- File: `src/scheduler/daily_crawler.py`
- Run manually during development
- Easy to test and debug

### Phase 2: PoC Demo (UC2 Complete)
**Use**: APScheduler BackgroundScheduler
- Integrate with Gradio UI
- Add "Scheduler" tab for control
- Show next run time, pause/resume

### Phase 3: Production (Future)
**Use**: System Cron
- Most reliable for production
- OS-level process management
- Log rotation with logrotate

## Testing Strategy

### Test Scheduler Locally
```python
# Test with 1-minute interval (instead of daily)
scheduler.add_job(
    crawl_yesterday_news,
    'interval',
    minutes=1,  # Every minute for testing
    id='test_crawl'
)
```

### Manual Test
```bash
# Test the crawl function directly
poetry run python -c "
from src.scheduler.daily_crawler import crawl_yesterday_news
crawl_yesterday_news()
"
```

## Monitoring & Logging

### Add Logging
```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
handler = RotatingFileHandler(
    'logs/scheduler.log',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger('scheduler')
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### Check Logs
```bash
tail -f logs/scheduler.log
```

## Error Handling

```python
def crawl_yesterday_news():
    try:
        yesterday = date.today() - timedelta(days=1)
        target_date = yesterday.strftime("%Y-%m-%d")

        logger.info(f"Starting crawl for {target_date}")

        result = subprocess.run([...], timeout=300)  # 5 min timeout

        if result.returncode != 0:
            logger.error(f"Crawl failed: {result.stderr}")
            # Send notification (email, Slack, etc.)
            send_alert(f"Daily crawl failed for {target_date}")

    except subprocess.TimeoutExpired:
        logger.error("Crawl timed out after 5 minutes")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
```

## Quick Start Commands

```bash
# 1. Install APScheduler
poetry add apscheduler

# 2. Create scheduler file
mkdir -p src/scheduler
touch src/scheduler/__init__.py
touch src/scheduler/daily_crawler.py

# 3. Run scheduler
poetry run python src/scheduler/daily_crawler.py

# 4. Test with specific date
poetry run python -c "
from datetime import date
from src.scheduler.daily_crawler import crawl_yesterday_news
crawl_yesterday_news()
"
```

## References

- APScheduler Documentation: https://apscheduler.readthedocs.io/
- Cron Expression: https://crontab.guru/
- Python subprocess: https://docs.python.org/3/library/subprocess.html
