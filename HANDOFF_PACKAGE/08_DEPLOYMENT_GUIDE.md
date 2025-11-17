# CrawlAgent Deployment Guide

**Version**: 1.0
**Last Updated**: 2025-11-17
**Target Audience**: DevOps, System Administrators, Technical Leads

---

## 📋 Table of Contents

1. [Quick Start (5 Minutes)](#quick-start-5-minutes)
2. [System Requirements](#system-requirements)
3. [Installation Methods](#installation-methods)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Health Checks](#health-checks)
7. [Troubleshooting](#troubleshooting)
8. [Production Deployment](#production-deployment)
9. [Backup & Recovery](#backup--recovery)

---

## 🚀 Quick Start (5 Minutes)

### Prerequisites
- Docker Desktop installed and running
- Git (for cloning the repository)
- API Keys: OpenAI, Anthropic (Claude)

### Steps

```bash
# 1. Clone repository
git clone <repository-url>
cd crawlagent

# 2. Initial setup (creates .env file)
make setup

# 3. Edit .env file with your API keys
vim .env  # or use any text editor
# Required:
#   - OPENAI_API_KEY=sk-proj-...
#   - ANTHROPIC_API_KEY=sk-ant-...

# 4. Start all services
make start

# 5. Access Web UI
open http://localhost:7860
```

**That's it!** 🎉

---

## 💻 System Requirements

### Minimum Requirements

| Component | Specification |
|-----------|--------------|
| **OS** | macOS 10.15+, Ubuntu 20.04+, Windows 10+ (with WSL2) |
| **Docker** | Docker Desktop 4.0+ or Docker Engine 20.10+ |
| **RAM** | 4 GB available |
| **Disk** | 10 GB free space |
| **CPU** | 2 cores |
| **Network** | Internet connection (for LLM API calls) |

### Recommended for Production

| Component | Specification |
|-----------|--------------|
| **RAM** | 8 GB+ |
| **Disk** | 50 GB+ SSD |
| **CPU** | 4 cores+ |
| **PostgreSQL** | Separate server (not Docker) |

---

## 📦 Installation Methods

### Method 1: Docker Compose (Recommended)

**Pros**: One-command deployment, isolated environment, easy cleanup
**Cons**: Requires Docker Desktop

```bash
# Full stack deployment
make start

# Services started:
# - PostgreSQL (port 5432)
# - Gradio UI (port 7860)
# - Scheduler (background)
```

### Method 2: Manual (Development)

**Pros**: Faster iteration, easier debugging
**Cons**: Requires Python 3.11, Poetry, manual setup

```bash
# 1. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 2. Install dependencies
poetry install

# 3. Start PostgreSQL (Docker)
docker-compose up -d postgres

# 4. Run migrations
poetry run alembic upgrade head

# 5. Start UI
poetry run python -m src.ui.app

# 6. (Optional) Start scheduler
poetry run python src/scheduler/daily_crawler.py
```

---

## ⚙️ Configuration

### Environment Variables

CrawlAgent uses `.env` file for configuration. Copy from template:

```bash
cp .env.example .env
```

#### Required Variables

```bash
# API Keys (MUST be set)
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Database (auto-configured in Docker)
DATABASE_URL=postgresql://crawlagent:dev_password@localhost:5432/crawlagent
```

#### Optional Variables

```bash
# LLM Models
UC2_PROPOSER_MODEL=gpt-4o          # Self-healing proposer
UC2_VALIDATOR_MODEL=gpt-4o         # Self-healing validator
UC3_DISCOVERER_MODEL=claude-sonnet-4-5-20250929  # Discovery
UC3_VALIDATOR_MODEL=gpt-4o         # Discovery validator

# Thresholds
UC1_QUALITY_THRESHOLD=80.0         # Minimum quality score
UC2_CONSENSUS_THRESHOLD=0.5        # Self-healing threshold
UC3_CONSENSUS_THRESHOLD=0.5        # Discovery threshold

# Logging
LOG_LEVEL=INFO                     # DEBUG, INFO, WARNING, ERROR
LOG_FILE_PATH=logs/crawlagent.log

# Server
GRADIO_PORT=7860
GRADIO_HOST=0.0.0.0
```

### Database Configuration

#### Default (Docker Compose)

```yaml
# docker-compose.yml
postgres:
  environment:
    POSTGRES_DB: crawlagent
    POSTGRES_USER: crawlagent
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dev_password}
```

#### Production (External PostgreSQL)

```bash
# .env
DATABASE_URL=postgresql://user:pass@production-db.example.com:5432/crawlagent
```

Then disable postgres service in docker-compose:

```bash
# Start only app and scheduler
docker-compose up -d app scheduler
```

---

## 🏃 Running the Application

### Start All Services

```bash
make start
```

This command:
1. Builds Docker images (if not exists)
2. Starts PostgreSQL
3. Waits for DB health check
4. Starts Gradio UI
5. Starts scheduler

### Check Status

```bash
make status
```

Output:
```
NAME                    COMMAND                  SERVICE     STATUS      PORTS
crawlagent-postgres     "docker-entrypoint.s…"   postgres    Up 5 min    0.0.0.0:5432->5432/tcp
crawlagent-app          "python -m src.ui.app"   app         Up 5 min    0.0.0.0:7860->7860/tcp
crawlagent-scheduler    "python src/schedule…"   scheduler   Up 5 min
```

### View Logs

```bash
# All services
make logs

# Specific service
make logs-app
make logs-scheduler
make logs-postgres
```

### Stop Services

```bash
make stop
```

---

## 💚 Health Checks

### Automatic Health Checks

Docker Compose includes built-in health checks:

**PostgreSQL**:
```bash
pg_isready -U crawlagent -d crawlagent
# Interval: 5s, Timeout: 5s, Retries: 5
```

**Gradio UI**:
```bash
curl -f http://localhost:7860
# Interval: 30s, Timeout: 10s, Start Period: 40s
```

### Manual Health Check

```bash
make health
```

Output:
```
💚 Health Check 실행 중...

1️⃣ PostgreSQL:
   ✅ PostgreSQL OK

2️⃣ Web UI (Gradio):
   ✅ Web UI OK (http://localhost:7860)

3️⃣ Scheduler:
   ✅ Scheduler 실행 중
```

### Database Connectivity Test

```bash
make db-query
```

Shows recent crawl results:
```
 id  | site_name |                title                | quality_score |         created_at
-----+-----------+-------------------------------------+---------------+----------------------------
 123 | donga     | 공동구독 플랫폼 피클플러스...        |           100 | 2025-11-17 00:57:40.381689
```

---

## 🔧 Troubleshooting

### Issue 1: Port Already in Use

**Error**: `bind: address already in use`

**Solution**:
```bash
# Check what's using port 7860
lsof -ti:7860

# Kill the process
kill -9 $(lsof -ti:7860)

# Or change port in docker-compose.yml
ports:
  - "8080:7860"  # Use port 8080 instead
```

### Issue 2: PostgreSQL Connection Failed

**Error**: `could not connect to server`

**Check**:
```bash
# 1. Is PostgreSQL running?
make status

# 2. Check health
docker exec crawlagent-postgres pg_isready -U crawlagent

# 3. Check logs
make logs-postgres
```

**Solution**:
```bash
# Restart PostgreSQL
docker-compose restart postgres

# Or rebuild everything
make stop
make start
```

### Issue 3: API Key Not Found

**Error**: `AuthenticationError: Incorrect API key`

**Check**:
```bash
# 1. Does .env file exist?
ls -la .env

# 2. Are API keys set?
grep "OPENAI_API_KEY" .env
grep "ANTHROPIC_API_KEY" .env
```

**Solution**:
```bash
# Edit .env file
vim .env

# Restart services to reload env
make restart
```

### Issue 4: Gradio UI Not Loading

**Symptoms**: `curl http://localhost:7860` fails

**Check**:
```bash
# 1. Is container running?
docker ps | grep crawlagent-app

# 2. Check logs for errors
make logs-app

# 3. Check inside container
make shell-app
curl http://localhost:7860
```

**Solution**:
```bash
# Restart app service
docker-compose restart app

# Or rebuild
docker-compose up -d --build app
```

### Issue 5: Scheduler Not Running

**Check**:
```bash
# 1. Is container running?
docker ps | grep crawlagent-scheduler

# 2. Check logs
make logs-scheduler

# 3. Should see: "[스케줄러 시작] 매일 00:30에..."
```

**Solution**:
```bash
# Test scheduler manually
docker-compose exec scheduler python src/scheduler/daily_crawler.py --test
```

---

## 🏭 Production Deployment

### Security Checklist

- [ ] Change default PostgreSQL password
- [ ] Use strong API keys
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Restrict database access (firewall rules)
- [ ] Set `DEBUG=false` in .env
- [ ] Use secrets management (AWS Secrets Manager, Vault)
- [ ] Enable authentication for Gradio UI

### External PostgreSQL

For production, use managed PostgreSQL (AWS RDS, Google Cloud SQL):

```bash
# .env
DATABASE_URL=postgresql://admin:strong_password@rds.amazonaws.com:5432/crawlagent

# docker-compose.yml
# Comment out postgres service, only run app & scheduler
docker-compose up -d app scheduler
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name crawlagent.example.com;

    location / {
        proxy_pass http://localhost:7860;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Monitoring

#### Prometheus Metrics (Optional)

Add to `src/ui/app.py`:
```python
from prometheus_client import start_http_server, Counter

crawl_total = Counter('crawl_total', 'Total crawls')
crawl_success = Counter('crawl_success', 'Successful crawls')

# Start metrics server
start_http_server(9090)
```

#### Health Check Endpoint

Already available at `http://localhost:7860`

#### Log Aggregation

Use Docker logging driver:
```yaml
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
```

---

## 💾 Backup & Recovery

### Database Backup

#### Manual Backup

```bash
# Backup to file
docker exec crawlagent-postgres pg_dump -U crawlagent crawlagent > backup_$(date +%Y%m%d).sql

# Backup specific tables
docker exec crawlagent-postgres pg_dump -U crawlagent -t crawl_results crawlagent > results_backup.sql
```

#### Automated Backup (Cron)

```bash
# Add to crontab
0 2 * * * cd /path/to/crawlagent && docker exec crawlagent-postgres pg_dump -U crawlagent crawlagent > backups/backup_$(date +\%Y\%m\%d).sql
```

### Database Restore

```bash
# Restore from backup
cat backup_20251117.sql | docker exec -i crawlagent-postgres psql -U crawlagent -d crawlagent
```

### Volume Backup

```bash
# Backup PostgreSQL volume
docker run --rm -v crawlagent_postgres_data:/data -v $(pwd)/backups:/backup ubuntu tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz /data
```

---

## 📞 Support & Contact

### Common Issues

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for detailed solutions.

### Getting Help

1. Check logs: `make logs`
2. Run health check: `make health`
3. Check [GitHub Issues](link-to-repo/issues)
4. Contact: [your-email@example.com]

---

## 📚 Additional Resources

- [README.md](../README.md): Project overview
- [ARCHITECTURE_EXPLANATION.md](./ARCHITECTURE_EXPLANATION.md): System design
- [HANDOFF_CHECKLIST.md](./HANDOFF_CHECKLIST.md): Deployment checklist
- [OPERATIONS_MANUAL.md](./OPERATIONS_MANUAL.md): Day-to-day operations

---

**Last Updated**: 2025-11-17
**Maintained by**: CrawlAgent Team
