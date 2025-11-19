#!/bin/bash
# CrawlAgent Handoff Verification Script
# Version: 1.0
# Date: 2025-11-19

echo "=========================================="
echo "  CrawlAgent Handoff Verification"
echo "=========================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
PASS=0
FAIL=0

# Test 1: Check Python version
echo "[1/8] Checking Python version..."
if python3 --version | grep -q "Python 3.11"; then
    echo -e "   ${GREEN}✓${NC} Python 3.11 found"
    ((PASS++))
else
    echo -e "   ${RED}✗${NC} Python 3.11 not found"
    echo "   Fix: Install Python 3.11"
    ((FAIL++))
fi

# Test 2: Check Poetry
echo "[2/8] Checking Poetry..."
if command -v poetry &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Poetry installed"
    ((PASS++))
else
    echo -e "   ${RED}✗${NC} Poetry not found"
    echo "   Fix: curl -sSL https://install.python-poetry.org | python3 -"
    ((FAIL++))
fi

# Test 3: Check Docker
echo "[3/8] Checking Docker..."
if command -v docker &> /dev/null; then
    echo -e "   ${GREEN}✓${NC} Docker installed"
    ((PASS++))
else
    echo -e "   ${RED}✗${NC} Docker not found"
    echo "   Fix: Install Docker Desktop"
    ((FAIL++))
fi

# Test 4: Check .env file
echo "[4/8] Checking .env file..."
if [ -f .env ]; then
    if grep -q "OPENAI_API_KEY=sk-" .env && grep -q "ANTHROPIC_API_KEY=sk-" .env; then
        echo -e "   ${GREEN}✓${NC} .env file configured with API keys"
        ((PASS++))
    else
        echo -e "   ${YELLOW}⚠${NC} .env file exists but API keys not set"
        echo "   Fix: Add your API keys to .env"
        ((FAIL++))
    fi
else
    echo -e "   ${RED}✗${NC} .env file not found"
    echo "   Fix: cp .env.example .env && nano .env"
    ((FAIL++))
fi

# Test 5: Check PostgreSQL
echo "[5/8] Checking PostgreSQL..."
if docker-compose ps | grep -q "db.*Up"; then
    echo -e "   ${GREEN}✓${NC} PostgreSQL running"
    ((PASS++))
else
    echo -e "   ${YELLOW}⚠${NC} PostgreSQL not running"
    echo "   Fix: docker-compose up -d db"
    ((FAIL++))
fi

# Test 6: Check Python dependencies
echo "[6/8] Checking Python dependencies..."
if poetry run python -c "import langchain, langgraph, gradio" 2>/dev/null; then
    echo -e "   ${GREEN}✓${NC} Core dependencies installed"
    ((PASS++))
else
    echo -e "   ${RED}✗${NC} Dependencies not installed"
    echo "   Fix: poetry install"
    ((FAIL++))
fi

# Test 7: Check database tables
echo "[7/8] Checking database tables..."
if poetry run python -c "from src.storage.database import get_db; from src.storage.models import Selector; db = next(get_db()); db.query(Selector).count()" 2>/dev/null; then
    COUNT=$(poetry run python -c "from src.storage.database import get_db; from src.storage.models import Selector; db = next(get_db()); print(db.query(Selector).count())" 2>/dev/null)
    if [ "$COUNT" -gt 0 ]; then
        echo -e "   ${GREEN}✓${NC} Database tables exist with $COUNT selectors"
        ((PASS++))
    else
        echo -e "   ${YELLOW}⚠${NC} Database tables exist but empty"
        echo "   Info: This is normal for fresh install"
        ((PASS++))
    fi
else
    echo -e "   ${RED}✗${NC} Database tables not found"
    echo "   Fix: make setup"
    ((FAIL++))
fi

# Test 8: Check essential files
echo "[8/8] Checking essential files..."
MISSING=0
for file in pyproject.toml Dockerfile docker-compose.yml Makefile README.md CONFIGURATION.md TESTING.md DATABASE_SCHEMA.md; do
    if [ ! -f "$file" ]; then
        echo -e "   ${RED}✗${NC} Missing: $file"
        ((MISSING++))
    fi
done

if [ $MISSING -eq 0 ]; then
    echo -e "   ${GREEN}✓${NC} All essential files present"
    ((PASS++))
else
    echo -e "   ${RED}✗${NC} $MISSING essential files missing"
    ((FAIL++))
fi

# Summary
echo ""
echo "=========================================="
echo "  Verification Summary"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASS${NC}/8"
echo -e "Failed: ${RED}$FAIL${NC}/8"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ All checks passed! Ready for handoff.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Start UI: make start"
    echo "2. Open browser: http://localhost:7860"
    echo "3. Test crawl on Tab 1"
    exit 0
else
    echo -e "${YELLOW}⚠ Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
