# CrawlAgent Configuration Guide

**Version**: 1.0
**Last Updated**: 2025-11-19
**Phase**: 1 Complete

This document provides comprehensive documentation for all environment variables used in CrawlAgent.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Database Configuration](#database-configuration)
3. [API Keys](#api-keys)
4. [LLM Model Configuration](#llm-model-configuration)
5. [Quality & Consensus Thresholds](#quality--consensus-thresholds)
6. [Retry Configuration](#retry-configuration)
7. [HTTP Client Configuration](#http-client-configuration)
8. [Logging Configuration](#logging-configuration)
9. [Server Configuration](#server-configuration)
10. [Performance Configuration](#performance-configuration)
11. [Feature Flags](#feature-flags)
12. [Development/Debug](#developmentdebug)
13. [Troubleshooting](#troubleshooting)

---

## Quick Start

1. **Copy the example file**:
   ```bash
   cp .env.example .env
   ```

2. **Edit `.env` with your values**:
   ```bash
   # Required: Add your API keys
   OPENAI_API_KEY=sk-proj-your-actual-key
   ANTHROPIC_API_KEY=sk-ant-your-actual-key

   # Optional: Update database URL if not using default
   DATABASE_URL=postgresql://crawlagent:password@localhost:5432/crawlagent
   ```

3. **Verify configuration**:
   ```bash
   poetry run python scripts/verify_environment.py
   ```

---

## Database Configuration

### `DATABASE_URL`
**Default**: `postgresql://crawlagent:password@localhost:5432/crawlagent`
**Required**: Yes
**Format**: `postgresql://[user]:[password]@[host]:[port]/[database]`

PostgreSQL database connection string.

**Examples**:
```bash
# Local development
DATABASE_URL=postgresql://crawlagent:password@localhost:5432/crawlagent

# Docker Compose
DATABASE_URL=postgresql://crawlagent:password@db:5432/crawlagent

# Remote database (production)
DATABASE_URL=postgresql://user:pass@db.example.com:5432/crawlagent_prod

# With SSL
DATABASE_URL=postgresql://user:pass@db.example.com:5432/crawlagent?sslmode=require
```

**Troubleshooting**:
- ✗ **Connection refused**: Check if PostgreSQL is running (`docker-compose up db`)
- ✗ **Authentication failed**: Verify username/password in `docker-compose.yml`
- ✗ **Database does not exist**: Run `make setup` to create tables

---

## API Keys

### `OPENAI_API_KEY`
**Default**: None
**Required**: Yes
**Format**: `sk-proj-...` (starts with `sk-proj-` or `sk-`)

OpenAI API key for GPT-4o models (UC2 Validator, UC3 Validator).

**How to get**:
1. Visit https://platform.openai.com/api-keys
2. Click "Create new secret key"
3. Copy the key (starts with `sk-proj-` or `sk-`)

**Used in**:
- UC2: GPT-4o Validator
- UC3: GPT-4o Validator
- Fallback: GPT-4o-mini

**Cost estimate**:
- GPT-4o: ~$0.0025/call
- GPT-4o-mini: ~$0.0001/call (fallback)

**Troubleshooting**:
- ✗ **Invalid API key**: Key must start with `sk-`
- ✗ **Rate limit exceeded**: Wait 60 seconds or upgrade plan
- ✗ **Insufficient quota**: Add payment method at https://platform.openai.com/account/billing

---

### `ANTHROPIC_API_KEY`
**Default**: None
**Required**: Yes
**Format**: `sk-ant-...` (starts with `sk-ant-`)

Anthropic API key for Claude Sonnet 4.5 (UC2 Proposer, UC3 Discoverer).

**How to get**:
1. Visit https://console.anthropic.com/settings/keys
2. Click "Create Key"
3. Copy the key (starts with `sk-ant-`)

**Used in**:
- UC2: Claude Sonnet 4.5 Proposer (primary)
- UC3: Claude Sonnet 4.5 Discoverer (primary)

**Cost estimate**:
- Claude Sonnet 4.5: ~$0.0037/call
- 75% cheaper than GPT-4o for same quality

**Troubleshooting**:
- ✗ **Invalid API key**: Key must start with `sk-ant-`
- ✗ **Rate limit**: Claude has generous rate limits (50 requests/min)
- ✗ **JSON parsing error**: Automatic fallback to GPT-4o-mini

---

### `GEMINI_API_KEY`
**Default**: None
**Required**: No (Optional)
**Format**: Any string

Google Gemini API key for alternative/fallback LLM.

**How to get**:
1. Visit https://aistudio.google.com/app/apikey
2. Click "Create API Key"
3. Copy the key

**Used in**:
- Distributed Supervisor (if `ENABLE_DISTRIBUTED_SUPERVISOR=true`)
- Alternative validator (experimental)

**Note**: Currently optional. Only needed if using distributed supervisor feature.

---

## LLM Model Configuration

### `UC2_PROPOSER_MODEL`
**Default**: `gpt-4o`
**Recommended**: `claude-sonnet-4-5-20250929`
**Type**: String (model identifier)

Model used for UC2 Self-Healing Proposer.

**Valid options**:
- `claude-sonnet-4-5-20250929` - **Recommended** (coding-specialized, 75% cheaper)
- `gpt-4o` - Alternative (higher cost)
- `gpt-4o-mini` - Budget option (lower quality)

**Impact**:
- Claude Sonnet 4.5: Best for CSS Selector generation
- GPT-4o: Good quality but 4x more expensive
- GPT-4o-mini: Fast but lower accuracy (~60% consensus rate)

**Note**: As of Phase 1, code uses Claude Sonnet 4.5 by default despite .env.example showing gpt-4o. Update `.env` to match:
```bash
UC2_PROPOSER_MODEL=claude-sonnet-4-5-20250929
```

---

### `UC2_VALIDATOR_MODEL`
**Default**: `gpt-4o`
**Recommended**: `gpt-4o`
**Type**: String (model identifier)

Model used for UC2 Self-Healing Validator.

**Valid options**:
- `gpt-4o` - **Recommended** (high accuracy validation)
- `gpt-4o-mini` - Budget option
- `claude-sonnet-4-5-20250929` - Alternative

**Impact**:
- GPT-4o: 95%+ validation accuracy
- Cross-company validation (Claude Proposer + GPT-4o Validator) prevents hallucination

---

### `UC3_DISCOVERER_MODEL`
**Default**: `claude-sonnet-4-5-20250929`
**Recommended**: `claude-sonnet-4-5-20250929`
**Type**: String (model identifier)

Model used for UC3 New Site Discovery Discoverer.

**Valid options**:
- `claude-sonnet-4-5-20250929` - **Recommended** (best for zero-shot learning)
- `gpt-4o` - Alternative
- `gpt-4o-mini` - Budget (not recommended for discovery)

**Impact**:
- Claude Sonnet 4.5: 100% success rate on 8 SSR sites
- GPT-4o: Good but slightly lower accuracy
- GPT-4o-mini: Not recommended (fails on complex sites)

---

### `UC3_VALIDATOR_MODEL`
**Default**: `gpt-4o`
**Recommended**: `gpt-4o`
**Type**: String (model identifier)

Model used for UC3 New Site Discovery Validator.

**Valid options**:
- `gpt-4o` - **Recommended**
- `claude-sonnet-4-5-20250929` - Alternative

---

### `FALLBACK_MODEL`
**Default**: `gpt-4o-mini`
**Recommended**: `gpt-4o-mini`
**Type**: String (model identifier)

Fallback model when primary model fails.

**Used when**:
- Claude API returns JSON parsing error
- Primary model hits rate limit
- Primary model timeout (>30s)

**Cost**:
- GPT-4o-mini: ~$0.0001/call (100x cheaper than GPT-4o)

---

## Quality & Consensus Thresholds

### `UC1_QUALITY_THRESHOLD`
**Default**: `80.0`
**Range**: `0.0` - `100.0`
**Type**: Float

Minimum quality score for UC1 Quality Gate to pass.

**Calculation**:
```
Quality = Title(20%) + Body(60%) + Date(10%) + URL(10%)
- Title: 20 points if >= 5 chars
- Body: 60 points if >= 100 chars (proportional)
- Date: 10 points if present
- URL: 10 points if valid HTTP(S)
```

**Recommended values**:
- **80.0** (default): Balanced quality vs. recall
- **90.0**: Strict quality (may miss some articles)
- **70.0**: Lenient (more articles, lower quality)

**Impact**:
- Higher → Fewer UC2/UC3 triggers (faster, cheaper)
- Lower → More UC2/UC3 triggers (slower, expensive)

**Troubleshooting**:
- Too many UC2 triggers? Lower threshold to 70.0
- Low quality results? Raise threshold to 90.0

---

### `UC2_CONSENSUS_THRESHOLD`
**Default**: `0.5`
**Recommended**: `0.7`
**Range**: `0.0` - `1.0`
**Type**: Float

Minimum consensus score for UC2 Self-Healing to auto-approve.

**Calculation**:
```
Consensus = 0.3×Claude + 0.3×GPT-4o + 0.4×Extraction Quality
```

**Recommended values**:
- **0.7** (production): High confidence auto-approval
- **0.6**: Balanced (some manual review)
- **0.5** (default): Lenient (less manual review)

**Impact**:
- `>= 0.7`: Auto-approved (no human review)
- `0.5-0.7`: Conditional approval (may trigger review)
- `< 0.5`: Human review required

**Example**:
```
Claude: 0.95, GPT-4o: 0.90, Quality: 1.0
Consensus = 0.95×0.3 + 0.90×0.3 + 1.0×0.4 = 0.955 ✅ Auto-approved
```

**Note**: Phase 1 code uses 0.7 threshold. Update `.env`:
```bash
UC2_CONSENSUS_THRESHOLD=0.7
```

---

### `UC3_CONSENSUS_THRESHOLD`
**Default**: `0.5`
**Recommended**: `0.7`
**Range**: `0.0` - `1.0`
**Type**: Float

Minimum consensus score for UC3 New Site Discovery.

**Same formula as UC2**:
```
Consensus = 0.3×Claude + 0.3×GPT-4o + 0.4×Extraction Quality
```

**Impact**: Same as UC2 (see above)

---

### Consensus Weights

#### `CONSENSUS_WEIGHT_AGENT1`
**Default**: `0.3`
**Range**: `0.0` - `1.0`
**Type**: Float

Weight for Agent 1 (Claude Proposer) in consensus calculation.

**Constraint**: Must sum to 1.0 with AGENT2 and QUALITY weights.

---

#### `CONSENSUS_WEIGHT_AGENT2`
**Default**: `0.3`
**Range**: `0.0` - `1.0`
**Type**: Float

Weight for Agent 2 (GPT-4o Validator) in consensus calculation.

---

#### `CONSENSUS_WEIGHT_QUALITY`
**Default**: `0.4`
**Range**: `0.0` - `1.0`
**Type**: Float

Weight for Extraction Quality in consensus calculation.

**Recommended**: Keep at 0.4 (highest weight) to prioritize actual extraction results over LLM opinions.

---

## Retry Configuration

### `MAX_RETRIES`
**Default**: `3`
**Range**: `1` - `10`
**Type**: Integer

Global maximum retries for any operation.

**Used in**:
- HTTP requests
- Database operations
- LLM API calls

---

### `RETRY_DELAY`
**Default**: `2`
**Range**: `1` - `60`
**Type**: Integer (seconds)

Delay between retry attempts.

**Backoff strategy**: Exponential (2s → 4s → 8s)

---

### `UC2_MAX_RETRIES`
**Default**: `3`
**Range**: `1` - `5`
**Type**: Integer

Maximum consensus retry attempts in UC2.

**Impact**:
- Higher → More chances to reach consensus (slower, expensive)
- Lower → Faster failure → Human review

**Recommended**: Keep at 3 (balance)

---

### `UC3_MAX_RETRIES`
**Default**: `3`
**Range**: `1` - `5`
**Type**: Integer

Maximum discovery retry attempts in UC3.

**Impact**: Same as UC2

---

## HTTP Client Configuration

### `REQUEST_TIMEOUT`
**Default**: `10`
**Range**: `5` - `60`
**Type**: Integer (seconds)

HTTP request timeout for crawling.

**Recommended values**:
- **10s** (default): Most sites respond within 10s
- **20s**: Slow international sites
- **5s**: Fast local sites only

**Troubleshooting**:
- Timeout errors on slow sites? Increase to 20s
- Want faster failure detection? Decrease to 5s

---

### `USER_AGENT`
**Default**: `Mozilla/5.0 (compatible; CrawlAgent/1.0)`
**Type**: String

HTTP User-Agent header sent with requests.

**Why it matters**:
- Some sites block requests without User-Agent
- Some sites block bot User-Agents

**Alternative values**:
```bash
# Standard browser
USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# News crawler (polite)
USER_AGENT="Mozilla/5.0 (compatible; CrawlAgent/1.0; +https://example.com/bot)"

# Anonymous
USER_AGENT="Mozilla/5.0 (compatible)"
```

**Note**: Some sites may require browser User-Agent to bypass anti-bot protection.

---

## Logging Configuration

### `LOG_LEVEL`
**Default**: `INFO`
**Valid options**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
**Type**: String

Logging verbosity level.

**Recommended by environment**:
- **Production**: `WARNING` (errors only, clean logs)
- **Development**: `INFO` (workflow tracking)
- **Debugging**: `DEBUG` (everything, verbose)

**Impact on log file size**:
- DEBUG: ~10MB/day (1,000 crawls)
- INFO: ~2MB/day
- WARNING: ~100KB/day

---

### `LOG_FILE_PATH`
**Default**: `logs/crawlagent.log`
**Type**: String (file path)

Log file location.

**Recommended**:
- Development: `logs/crawlagent.log` (relative path)
- Production: `/var/log/crawlagent/app.log` (absolute path)

**Note**: Directory must exist or be created by application.

---

### `LOG_ROTATION`
**Default**: `1 day`
**Type**: String (time duration)

Log file rotation interval.

**Valid formats**:
- `1 day` - Rotate daily
- `12 hours` - Rotate twice daily
- `1 week` - Rotate weekly
- `100 MB` - Rotate when file reaches 100MB

**Recommended**: `1 day` for production

---

### `LOG_RETENTION`
**Default**: `30 days`
**Type**: String (time duration)

How long to keep old log files.

**Recommended**:
- **30 days** (default): Balance storage vs. debugging
- **7 days**: Tight storage
- **90 days**: Compliance/audit requirements

---

## Server Configuration

### `GRADIO_HOST`
**Default**: `0.0.0.0`
**Type**: String (IP address)

Gradio UI server bind address.

**Options**:
- `0.0.0.0` - Listen on all interfaces (Docker, remote access)
- `127.0.0.1` - Localhost only (local development)
- `192.168.1.100` - Specific IP

**Security**:
- ⚠️ `0.0.0.0` exposes UI to network (use firewall)
- ✅ `127.0.0.1` is safe for local development

---

### `GRADIO_PORT`
**Default**: `7860`
**Range**: `1024` - `65535`
**Type**: Integer

Gradio UI server port.

**Troubleshooting**:
- ✗ Port already in use? Change to 7861, 8080, etc.
- ✗ Permission denied? Use port > 1024

---

### `GRADIO_SHARE`
**Default**: `false`
**Type**: Boolean (`true`/`false`)

Create public Gradio.live link.

**Options**:
- `false` (default): Local access only
- `true`: Creates public https://xxxxx.gradio.live link

**Security warning**:
- ⚠️ `true` exposes UI to internet (72-hour expiry)
- Only use for demos, NOT production

---

## Performance Configuration

### `MAX_WORKERS`
**Default**: `5`
**Range**: `1` - `20`
**Type**: Integer

Maximum concurrent worker threads for multi-site crawling.

**Recommended by system**:
- **1-2 CPU cores**: MAX_WORKERS=2
- **4 CPU cores**: MAX_WORKERS=5 (default)
- **8+ CPU cores**: MAX_WORKERS=10

**Impact**:
- Higher → Faster multi-site crawling (more memory/CPU)
- Lower → Slower but stable

**Troubleshooting**:
- High CPU usage? Reduce to 2-3
- Slow multi-site? Increase to 10 (if CPU allows)

---

### `DB_POOL_SIZE`
**Default**: `10`
**Range**: `5` - `50`
**Type**: Integer

PostgreSQL connection pool size.

**Recommended**:
- **5**: Single worker (dev)
- **10**: Default (5 workers × 2)
- **20**: High concurrency (10 workers)

**Formula**: `DB_POOL_SIZE >= MAX_WORKERS × 2`

---

### `DB_MAX_OVERFLOW`
**Default**: `20`
**Range**: `10` - `100`
**Type**: Integer

Maximum overflow connections beyond pool size.

**Total max connections**: `DB_POOL_SIZE + DB_MAX_OVERFLOW = 30`

**Troubleshooting**:
- "Too many connections" error? Increase DB_MAX_OVERFLOW
- PostgreSQL max_connections exceeded? Check `postgresql.conf`

---

## Feature Flags

### `ENABLE_JSON_LD_OPTIMIZATION`
**Default**: `true`
**Type**: Boolean

Enable JSON-LD Smart Extraction (UC3 optimization).

**Impact when enabled**:
- ✅ 95%+ sites skip LLM calls (JSON-LD extraction)
- ✅ $0 cost for sites with JSON-LD
- ✅ ~100ms extraction time

**Impact when disabled**:
- ✗ All sites use 2-Agent Consensus
- ✗ $0.033/article cost
- ✗ ~30s extraction time

**Recommended**: Always keep `true` (cost savings)

---

### `ENABLE_DISTRIBUTED_SUPERVISOR`
**Default**: `false`
**Type**: Boolean

Enable 3-Model Distributed Supervisor (experimental).

**What it does**:
- Uses GPT-4o + Claude + Gemini for routing decisions
- Majority voting for fault tolerance
- SPOF prevention

**Impact when enabled**:
- ✅ Fault-tolerant routing (one model can fail)
- ✗ 3x LLM calls per routing decision
- ✗ Slower (3 parallel calls with timeout)

**Cost**:
- Disabled (default): $0/routing (rule-based)
- Enabled: ~$0.01/routing (3 LLM calls)

**Recommended**: Keep `false` unless fault tolerance required

**Requirements**:
- `GEMINI_API_KEY` must be set
- All 3 API keys must be valid

---

### `ENABLE_COST_TRACKING`
**Default**: `true`
**Type**: Boolean

Enable cost tracking and logging.

**Impact when enabled**:
- ✅ Track LLM API costs in `cost_metrics` table
- ✅ View costs in Gradio UI (Tab 5)
- ✅ CSV export of cost data

**Impact when disabled**:
- No cost tracking
- Slightly faster (no DB writes)

**Recommended**: Keep `true` for production (cost visibility)

---

## Development/Debug

### `DEBUG`
**Default**: `false`
**Type**: Boolean

Enable debug mode.

**Impact when enabled**:
- Verbose logging (DEBUG level)
- Stack traces in errors
- Development-friendly error messages

**Recommended**:
- Development: `true`
- Production: `false`

---

### `TESTING`
**Default**: `false`
**Type**: Boolean

Enable testing mode.

**Impact when enabled**:
- Use test database
- Skip some validations
- Mock external APIs (optional)

**Used by**: `pytest` test suite

**Recommended**: Set to `true` only when running `make test`

---

## Troubleshooting

### Common Configuration Errors

#### 1. Missing API Keys
**Symptom**: `ValueError: OPENAI_API_KEY not found in environment`

**Solution**:
```bash
# Check if .env exists
ls -la .env

# Verify API keys are set
grep "API_KEY" .env

# Run verification script
poetry run python scripts/verify_environment.py
```

---

#### 2. Database Connection Failed
**Symptom**: `sqlalchemy.exc.OperationalError: could not connect to server`

**Solution**:
```bash
# Check if PostgreSQL is running
docker-compose ps

# Start database
docker-compose up -d db

# Verify connection string
echo $DATABASE_URL

# Test connection
poetry run python -c "from src.storage.database import get_db; next(get_db())"
```

---

#### 3. Invalid Threshold Values
**Symptom**: `AssertionError: Consensus weights must sum to 1.0`

**Solution**:
```bash
# Check weights in .env
CONSENSUS_WEIGHT_AGENT1=0.3
CONSENSUS_WEIGHT_AGENT2=0.3
CONSENSUS_WEIGHT_QUALITY=0.4
# Total must equal 1.0
```

---

#### 4. Port Already in Use
**Symptom**: `OSError: [Errno 48] Address already in use`

**Solution**:
```bash
# Find process using port 7860
lsof -i :7860

# Kill process
kill -9 <PID>

# Or change port in .env
GRADIO_PORT=7861
```

---

#### 5. Log Directory Not Found
**Symptom**: `FileNotFoundError: [Errno 2] No such file or directory: 'logs/crawlagent.log'`

**Solution**:
```bash
# Create logs directory
mkdir -p logs

# Or use absolute path
LOG_FILE_PATH=/var/log/crawlagent/app.log
```

---

### Configuration Validation

Run the environment verification script:

```bash
poetry run python scripts/verify_environment.py
```

**What it checks**:
- ✅ All required API keys present
- ✅ Database connection working
- ✅ All thresholds in valid range
- ✅ Consensus weights sum to 1.0
- ✅ Log directory exists
- ✅ Models are valid identifiers

---

### Best Practices

1. **Never commit `.env` to git**
   - Add to `.gitignore` (already done)
   - Use `.env.example` as template

2. **Use environment-specific configs**
   ```bash
   # Development
   .env.development

   # Production
   .env.production

   # Load with
   cp .env.production .env
   ```

3. **Rotate API keys regularly**
   - Monthly rotation recommended
   - Use separate keys for dev/prod

4. **Monitor costs**
   - Enable `ENABLE_COST_TRACKING=true`
   - Check Tab 5 in Gradio UI weekly
   - Set budget alerts in OpenAI/Anthropic dashboards

5. **Test configuration changes**
   ```bash
   # After changing .env
   poetry run python scripts/verify_environment.py

   # Test crawl
   make test-crawl
   ```

---

## Configuration Templates

### Minimal (Development)
```bash
DATABASE_URL=postgresql://crawlagent:password@localhost:5432/crawlagent
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
UC2_PROPOSER_MODEL=claude-sonnet-4-5-20250929
UC2_CONSENSUS_THRESHOLD=0.7
UC3_CONSENSUS_THRESHOLD=0.7
DEBUG=true
```

### Production (Docker)
```bash
DATABASE_URL=postgresql://crawlagent:strong_password@db:5432/crawlagent
OPENAI_API_KEY=sk-proj-production-key
ANTHROPIC_API_KEY=sk-ant-production-key
UC2_PROPOSER_MODEL=claude-sonnet-4-5-20250929
UC2_VALIDATOR_MODEL=gpt-4o
UC3_DISCOVERER_MODEL=claude-sonnet-4-5-20250929
UC3_VALIDATOR_MODEL=gpt-4o
UC2_CONSENSUS_THRESHOLD=0.7
UC3_CONSENSUS_THRESHOLD=0.7
LOG_LEVEL=WARNING
ENABLE_COST_TRACKING=true
GRADIO_HOST=0.0.0.0
GRADIO_PORT=7860
MAX_WORKERS=10
DB_POOL_SIZE=20
```

### High-Availability (Distributed Supervisor)
```bash
DATABASE_URL=postgresql://user:pass@db.example.com:5432/crawlagent
OPENAI_API_KEY=sk-proj-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
GEMINI_API_KEY=xxx
UC2_PROPOSER_MODEL=claude-sonnet-4-5-20250929
ENABLE_DISTRIBUTED_SUPERVISOR=true
UC2_CONSENSUS_THRESHOLD=0.7
LOG_LEVEL=INFO
MAX_RETRIES=5
REQUEST_TIMEOUT=20
```

---

## Contact & Support

For configuration questions:
- Check [TROUBLESHOOTING_REFERENCE.md](HANDOFF_PACKAGE/09_TROUBLESHOOTING_REFERENCE.md)
- Run verification: `poetry run python scripts/verify_environment.py`
- Review logs: `tail -f logs/crawlagent.log`

---

**Document Version**: 1.0
**Generated**: 2025-11-19
**Covers**: Phase 1 Complete Configuration
