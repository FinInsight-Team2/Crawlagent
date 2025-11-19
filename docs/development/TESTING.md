# CrawlAgent Testing Guide

**Version**: 1.0
**Last Updated**: 2025-11-19
**Test Coverage**: 19% (Target: 80%+)

This document provides comprehensive guidance for running and writing tests in CrawlAgent.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Test Structure](#test-structure)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Writing New Tests](#writing-new-tests)
6. [Test Coverage](#test-coverage)
7. [CI/CD Integration](#cicd-integration)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### Prerequisites

1. **Install dependencies**:
   ```bash
   poetry install
   ```

2. **Set up test database**:
   ```bash
   # Start PostgreSQL container
   docker-compose up -d db

   # Run migrations
   make setup
   ```

3. **Create test `.env`**:
   ```bash
   cp .env.example .env
   # Set TESTING=true in .env
   ```

### Run All Tests

```bash
# Using Makefile (recommended)
make test

# Using Poetry directly
poetry run pytest

# Using pytest directly (if in virtual env)
pytest
```

**Expected output**:
```
======================== test session starts =========================
platform darwin -- Python 3.11.x, pytest-8.x.x, pluggy-1.x.x
rootdir: /Users/charlee/Desktop/Intern/crawlagent
collected 29 items

tests/unit/test_database.py ....                              [ 13%]
tests/unit/test_uc1_quality_gate.py .....                     [ 31%]
tests/unit/test_supervisor.py ...                             [ 42%]
tests/test_uc2.py ........                                    [ 69%]
tests/e2e/test_master_workflow.py ....                        [100%]

==================== 29 passed in 45.2s ==========================
```

---

## Test Structure

### Directory Layout

```
tests/
├── conftest.py                    # Shared pytest fixtures
├── __init__.py
│
├── unit/                          # Unit tests (isolated)
│   ├── test_database.py           # Database operations
│   ├── test_uc1_quality_gate.py   # UC1 quality logic
│   └── test_supervisor.py         # Supervisor routing
│
├── uc2/                           # UC2-specific tests
│   ├── test_gpt_node.py           # Claude propose node (renamed)
│   ├── test_full_workflow.py     # Full UC2 workflow
│   └── test_integration.py       # Integration tests
│
├── e2e/                           # End-to-end tests
│   └── test_master_workflow.py   # Master workflow E2E
│
├── test_uc3.py                    # UC3 discovery tests
├── test_uc3_new_site.py           # UC3 new site tests
├── test_gradio_ui.py              # Gradio UI tests
├── test_healthcheck.py            # Health check tests
├── test_cost_dashboard.py         # Cost tracking tests
└── test_langsmith_tracing.py      # LangSmith integration
```

### Test File Naming Convention

- **Unit tests**: `test_<module_name>.py`
- **Integration tests**: `test_<feature>_integration.py`
- **E2E tests**: `test_<workflow>_e2e.py`

### Test Function Naming Convention

```python
# Good
def test_uc1_quality_gate_passes_when_quality_high():
    pass

def test_uc2_consensus_reaches_when_both_agents_agree():
    pass

# Bad
def test_quality():
    pass

def test_uc2():
    pass
```

**Pattern**: `test_<component>_<action>_<condition>`

---

## Running Tests

### Run All Tests

```bash
make test
```

### Run Specific Test File

```bash
# Single file
pytest tests/unit/test_database.py

# With verbose output
pytest tests/unit/test_database.py -v

# With output capture disabled (see print statements)
pytest tests/unit/test_database.py -s
```

### Run Specific Test Function

```bash
pytest tests/unit/test_database.py::test_database_connection

# With keyword matching
pytest -k "test_database"
```

### Run by Category

```bash
# Unit tests only
pytest tests/unit/

# UC2 tests only
pytest tests/uc2/

# E2E tests only
pytest tests/e2e/

# Exclude slow tests
pytest -m "not slow"
```

### Run with Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html

# View coverage in browser
open htmlcov/index.html

# Terminal coverage report
pytest --cov=src --cov-report=term-missing
```

### Run in Parallel (Faster)

```bash
# Install pytest-xdist
poetry add --group dev pytest-xdist

# Run with 4 workers
pytest -n 4

# Auto-detect CPU cores
pytest -n auto
```

### Run with Specific Markers

```bash
# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m unit

# Run only fast tests
pytest -m "not slow"
```

---

## Test Categories

### Unit Tests (tests/unit/)

**Purpose**: Test individual functions/modules in isolation

**Characteristics**:
- ✅ Fast (< 1s per test)
- ✅ No external dependencies (DB, API, network)
- ✅ Use mocks/stubs for dependencies

**Example**:

```python
# tests/unit/test_uc1_quality_gate.py
def test_quality_score_calculation():
    """Test 5W1H quality score calculation"""
    metadata = {
        "title": "삼성전자 주가 상승",  # 10 chars → 20 points
        "body": "a" * 150,              # 150 chars → 60 points
        "date": "2025-11-19",           # Present → 10 points
        "url": "https://example.com"    # Valid → 10 points
    }

    score = calculate_quality_score(metadata)
    assert score == 100
```

**Run**:
```bash
pytest tests/unit/ -v
```

---

### Integration Tests (tests/uc2/, tests/test_uc3.py)

**Purpose**: Test interaction between multiple components

**Characteristics**:
- ⏱️ Moderate speed (1-10s per test)
- 🔗 Tests component integration
- 🗄️ May use real database (test DB)

**Example**:

```python
# tests/uc2/test_integration.py
def test_uc2_full_consensus_workflow(test_db):
    """Test complete UC2 workflow with real database"""
    state = {
        "url": "https://www.yna.co.kr/view/AKR20251119001",
        "site_name": "yonhap",
        "html_content": load_test_html("yonhap_sample.html")
    }

    # Run full UC2 workflow
    result = run_uc2_workflow(state)

    # Verify consensus reached
    assert result["consensus_reached"] is True
    assert result["consensus_score"] >= 0.7

    # Verify selectors saved to DB
    selector = test_db.query(Selector).filter_by(site_name="yonhap").first()
    assert selector is not None
    assert selector.title_selector is not None
```

**Run**:
```bash
pytest tests/uc2/ -v
pytest tests/test_uc3.py -v
```

---

### End-to-End Tests (tests/e2e/)

**Purpose**: Test complete workflows from start to finish

**Characteristics**:
- ⏱️ Slow (10-60s per test)
- 🌐 Tests full system integration
- 💰 May call real APIs (use sparingly)

**Example**:

```python
# tests/e2e/test_master_workflow.py
@pytest.mark.slow
def test_master_workflow_end_to_end(test_db):
    """Test complete Master Workflow: UC1 → UC2 → UC1"""
    url = "https://www.yna.co.kr/view/AKR20251119001"

    # Run master workflow
    result = run_master_workflow(url)

    # Verify workflow completion
    assert result["status"] == "success"
    assert result["current_uc"] == "uc1"
    assert result["final_quality"] >= 80

    # Verify data saved
    article = test_db.query(CrawlResult).filter_by(url=url).first()
    assert article is not None
    assert len(article.title) >= 5
    assert len(article.body) >= 100
```

**Run**:
```bash
# Run E2E tests (slow)
pytest tests/e2e/ -v

# Skip slow tests
pytest -m "not slow"
```

---

### UI Tests (tests/test_gradio_ui.py)

**Purpose**: Test Gradio interface functionality

**Characteristics**:
- 🖥️ Tests UI components
- ⚡ Fast (mocked backend)

**Example**:

```python
# tests/test_gradio_ui.py
def test_gradio_tab1_crawl_button(mocker):
    """Test Tab 1 real-time crawl button"""
    # Mock the actual crawl function
    mock_crawl = mocker.patch('src.ui.app.run_master_workflow')
    mock_crawl.return_value = {"status": "success", "quality": 95}

    # Simulate button click
    result = handle_crawl_button_click("https://www.yna.co.kr/view/123")

    assert "성공" in result
    assert mock_crawl.called_once()
```

**Run**:
```bash
pytest tests/test_gradio_ui.py -v
```

---

## Writing New Tests

### Test Template

```python
# tests/unit/test_my_module.py
import pytest
from src.my_module import my_function

class TestMyModule:
    """Test suite for my_module"""

    def test_my_function_success_case(self):
        """Test my_function with valid input"""
        # Arrange
        input_data = {"key": "value"}
        expected = "expected result"

        # Act
        result = my_function(input_data)

        # Assert
        assert result == expected

    def test_my_function_error_case(self):
        """Test my_function handles errors gracefully"""
        # Arrange
        invalid_input = None

        # Act & Assert
        with pytest.raises(ValueError):
            my_function(invalid_input)

    @pytest.mark.parametrize("input,expected", [
        ("a", 1),
        ("b", 2),
        ("c", 3),
    ])
    def test_my_function_multiple_inputs(self, input, expected):
        """Test my_function with multiple input values"""
        result = my_function(input)
        assert result == expected
```

### Using Fixtures

Fixtures are defined in `tests/conftest.py`:

```python
# tests/conftest.py
import pytest
from src.storage.database import get_db, Base

@pytest.fixture
def test_db():
    """Provide a test database session"""
    # Setup: Create test DB
    engine = create_test_engine()
    Base.metadata.create_all(engine)
    session = Session(engine)

    yield session

    # Teardown: Clean up
    session.close()
    Base.metadata.drop_all(engine)

@pytest.fixture
def sample_html():
    """Provide sample HTML for testing"""
    with open("tests/fixtures/sample.html") as f:
        return f.read()
```

**Usage in tests**:

```python
def test_database_insert(test_db):
    """Test inserting data into database"""
    article = CrawlResult(url="https://example.com", title="Test")
    test_db.add(article)
    test_db.commit()

    retrieved = test_db.query(CrawlResult).filter_by(url="https://example.com").first()
    assert retrieved.title == "Test"
```

### Mocking External Dependencies

```python
from unittest.mock import Mock, patch

def test_uc2_with_mocked_llm(mocker):
    """Test UC2 without calling real LLM API"""
    # Mock Claude API
    mock_claude_response = {
        "title_selector": "h1.article-title",
        "body_selector": "div.article-body",
        "confidence": 0.95
    }
    mocker.patch('langchain_anthropic.ChatAnthropic.invoke', return_value=mock_claude_response)

    # Run UC2
    result = run_uc2_node(test_state)

    # Verify without real API call
    assert result["claude_proposal"]["confidence"] == 0.95
```

### Parametrized Tests

```python
@pytest.mark.parametrize("quality,expected_action", [
    (95, "save"),      # High quality → save
    (75, "heal"),      # Medium quality → heal
    (45, "uc3"),       # Low quality → uc3
])
def test_uc1_routing_decisions(quality, expected_action):
    """Test UC1 routes correctly based on quality"""
    state = {"quality_score": quality, "selector_exists": True}
    action = decide_next_action(state)
    assert action == expected_action
```

---

## Test Coverage

### Current Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing

# View in browser
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

**Current Status** (as of Phase 1):
```
Name                                      Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------
src/workflow/uc1_validation.py              370    289    19%   25-350
src/workflow/uc2_hitl.py                   1027    850    17%   140-980
src/workflow/uc3_new_site.py               1992   1750    12%   50-1900
src/workflow/master_crawl_workflow.py      1509   1320    13%   100-1450
src/storage/database.py                      89     45    49%   30-75
-----------------------------------------------------------------------
TOTAL                                      15000  12500    19%
```

### Coverage Goals

- **Phase 1**: 19% (current)
- **Phase 2**: 40% (target)
- **Phase 3**: 80% (production-ready)

### Priority Coverage Areas

1. **Critical Paths** (Priority 1):
   - `src/workflow/master_crawl_workflow.py` - Main orchestration
   - `src/workflow/uc1_validation.py` - Quality gate
   - `src/storage/database.py` - Data persistence

2. **High-Risk Areas** (Priority 2):
   - `src/workflow/uc2_hitl.py` - Consensus logic
   - `src/workflow/uc3_new_site.py` - Discovery logic
   - `src/diagnosis/failure_analyzer.py` - Error handling

3. **Nice-to-Have** (Priority 3):
   - `src/ui/app.py` - UI components
   - `src/monitoring/` - Monitoring modules

---

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: crawlagent
          POSTGRES_PASSWORD: password
          POSTGRES_DB: crawlagent_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install Poetry
      run: pip install poetry

    - name: Install dependencies
      run: poetry install

    - name: Run tests with coverage
      env:
        DATABASE_URL: postgresql://crawlagent:password@localhost:5432/crawlagent_test
        OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      run: |
        poetry run pytest --cov=src --cov-report=xml

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

### Pre-commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running tests before commit..."
poetry run pytest tests/unit/

if [ $? -ne 0 ]; then
    echo "❌ Tests failed! Commit aborted."
    exit 1
fi

echo "✅ All tests passed!"
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Troubleshooting

### Common Test Failures

#### 1. Database Connection Error

**Symptom**:
```
sqlalchemy.exc.OperationalError: could not connect to server
```

**Solution**:
```bash
# Start PostgreSQL
docker-compose up -d db

# Verify connection
psql postgresql://crawlagent:password@localhost:5432/crawlagent

# Run migrations
make setup
```

---

#### 2. API Key Missing

**Symptom**:
```
ValueError: OPENAI_API_KEY not found in environment
```

**Solution**:
```bash
# Create .env file
cp .env.example .env

# Add API keys
echo "OPENAI_API_KEY=sk-proj-xxx" >> .env
echo "ANTHROPIC_API_KEY=sk-ant-xxx" >> .env

# Or export for current session
export OPENAI_API_KEY=sk-proj-xxx
export ANTHROPIC_API_KEY=sk-ant-xxx
```

---

#### 3. Import Errors

**Symptom**:
```
ModuleNotFoundError: No module named 'src'
```

**Solution**:
```bash
# Install project in editable mode
poetry install

# Or add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Run tests with PYTHONPATH
PYTHONPATH=. pytest
```

---

#### 4. Fixture Not Found

**Symptom**:
```
fixture 'test_db' not found
```

**Solution**:
```bash
# Ensure conftest.py exists in tests/
ls tests/conftest.py

# Check fixture definition
grep "def test_db" tests/conftest.py

# Run with verbose fixture info
pytest --fixtures
```

---

#### 5. Slow Tests Timeout

**Symptom**:
```
FAILED tests/e2e/test_master_workflow.py::test_complete_workflow - Timeout
```

**Solution**:
```bash
# Skip slow tests during development
pytest -m "not slow"

# Increase timeout for specific test
@pytest.mark.timeout(120)  # 120 seconds
def test_slow_operation():
    pass

# Or globally in pytest.ini
[pytest]
timeout = 60
```

---

### Debugging Tests

```bash
# Run with print statements visible
pytest -s

# Run with detailed output
pytest -vv

# Drop into debugger on failure
pytest --pdb

# Stop at first failure
pytest -x

# Show local variables on failure
pytest -l

# Run last failed tests only
pytest --lf

# Run failed tests first
pytest --ff
```

---

## Best Practices

### 1. Test Independence

✅ **Good**: Each test is independent
```python
def test_uc1_quality_high(test_db):
    # Create test data
    article = CrawlResult(url="test1", quality=95)
    test_db.add(article)
    test_db.commit()

    # Test
    result = check_quality(test_db, "test1")
    assert result == 95

    # Cleanup handled by fixture
```

✗ **Bad**: Tests depend on each other
```python
def test_create_article():
    global article
    article = CrawlResult(url="test1")

def test_read_article():
    # Depends on test_create_article running first!
    assert article.url == "test1"
```

---

### 2. Clear Test Names

✅ **Good**: Descriptive test names
```python
def test_uc2_consensus_reaches_when_both_agents_above_threshold():
    pass

def test_uc1_routes_to_uc2_when_selector_damaged():
    pass
```

✗ **Bad**: Vague test names
```python
def test_consensus():
    pass

def test_routing():
    pass
```

---

### 3. Arrange-Act-Assert Pattern

```python
def test_quality_calculation():
    # Arrange
    metadata = {"title": "Test", "body": "a" * 100, "date": "2025-11-19"}

    # Act
    score = calculate_quality(metadata)

    # Assert
    assert score >= 80
```

---

### 4. Use Fixtures for Common Setup

```python
# conftest.py
@pytest.fixture
def sample_article():
    return {
        "url": "https://example.com/article/123",
        "title": "Test Article",
        "body": "Sample body text",
        "date": "2025-11-19"
    }

# test file
def test_article_validation(sample_article):
    assert validate_article(sample_article) is True
```

---

### 5. Mock External Dependencies

```python
# Don't call real APIs in tests
def test_uc2_node(mocker):
    # Mock instead
    mock_llm = mocker.patch('langchain_anthropic.ChatAnthropic')
    mock_llm.return_value.invoke.return_value = {"result": "mocked"}

    result = call_uc2_node()
    assert result == "mocked"
```

---

## Test Metrics

Track these metrics over time:

1. **Coverage**: Target 80%+
2. **Test Count**: Add 5-10 tests per sprint
3. **Test Speed**: Keep unit tests < 1s
4. **Failure Rate**: < 1% flaky tests

---

## Resources

- **pytest documentation**: https://docs.pytest.org/
- **pytest fixtures**: https://docs.pytest.org/en/stable/fixture.html
- **pytest-cov**: https://pytest-cov.readthedocs.io/
- **Mock/Patch guide**: https://docs.python.org/3/library/unittest.mock.html

---

**Document Version**: 1.0
**Generated**: 2025-11-19
**Test Coverage**: 19% → Target 80%
