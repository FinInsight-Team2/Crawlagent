# ========================================
# CrawlAgent Makefile
# One-command operations for Docker deployment
# ========================================

.PHONY: help setup start stop restart logs logs-app logs-scheduler logs-postgres status health clean build test

# Default target
.DEFAULT_GOAL := help

# ========================================
# Help
# ========================================
help:  ## Show this help message
	@echo "========================================"
	@echo "CrawlAgent - Make Commands"
	@echo "========================================"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ========================================
# Setup & Installation
# ========================================
setup:  ## Initial setup: Copy .env.example to .env
	@echo "📦 CrawlAgent 초기 설정"
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "✅ .env 파일 생성 완료"; \
		echo ""; \
		echo "⚠️  다음 단계:"; \
		echo "   1. .env 파일을 열어 API 키를 설정하세요:"; \
		echo "      - OPENAI_API_KEY"; \
		echo "      - ANTHROPIC_API_KEY"; \
		echo "   2. 설정 완료 후 'make start' 실행"; \
		echo ""; \
	else \
		echo "⚠️  .env 파일이 이미 존재합니다"; \
		echo "   기존 설정을 유지합니다"; \
	fi

# ========================================
# Docker Operations
# ========================================
build:  ## Build Docker images
	@echo "🔨 Docker 이미지 빌드 중..."
	docker-compose build

start:  ## Start all services (postgres, app, scheduler)
	@echo "🚀 CrawlAgent 시작 중..."
	docker-compose up -d --build
	@echo ""
	@echo "✅ 실행 완료!"
	@echo "   - Web UI: http://localhost:7860"
	@echo "   - Database: localhost:5432"
	@echo ""
	@echo "💡 유용한 명령어:"
	@echo "   - make logs       : 전체 로그 확인"
	@echo "   - make logs-app   : UI 로그만 확인"
	@echo "   - make health     : 상태 점검"
	@echo "   - make stop       : 중지"

stop:  ## Stop all services
	@echo "⏹️  CrawlAgent 중지 중..."
	docker-compose down
	@echo "✅ 중지 완료"

restart:  ## Restart all services
	@echo "🔄 CrawlAgent 재시작 중..."
	docker-compose restart
	@echo "✅ 재시작 완료"

# ========================================
# Logs
# ========================================
logs:  ## Show logs from all services (follow mode)
	docker-compose logs -f

logs-app:  ## Show logs from app service only
	docker-compose logs -f app

logs-scheduler:  ## Show logs from scheduler service only
	docker-compose logs -f scheduler

logs-postgres:  ## Show logs from postgres service only
	docker-compose logs -f postgres

# ========================================
# Status & Health Check
# ========================================
status:  ## Show running containers
	@echo "📊 실행 중인 컨테이너:"
	@docker-compose ps

health:  ## Health check for all services
	@echo "💚 Health Check 실행 중..."
	@echo ""
	@echo "1️⃣ PostgreSQL:"
	@docker exec crawlagent-postgres pg_isready -U crawlagent && echo "   ✅ PostgreSQL OK" || echo "   ❌ PostgreSQL 실패"
	@echo ""
	@echo "2️⃣ Web UI (Gradio):"
	@curl -f -s http://localhost:7860 > /dev/null && echo "   ✅ Web UI OK (http://localhost:7860)" || echo "   ❌ Web UI 접속 불가"
	@echo ""
	@echo "3️⃣ Scheduler:"
	@docker logs crawlagent-scheduler --tail 5 2>&1 | grep -q "스케줄러" && echo "   ✅ Scheduler 실행 중" || echo "   ⚠️  Scheduler 로그 확인 필요"
	@echo ""

# ========================================
# Database Operations
# ========================================
db-shell:  ## Connect to PostgreSQL shell
	docker exec -it crawlagent-postgres psql -U crawlagent -d crawlagent

db-query:  ## Quick query: Show recent crawl results
	docker exec crawlagent-postgres psql -U crawlagent -d crawlagent -c \
		"SELECT id, site_name, LEFT(title, 50) as title, quality_score, created_at FROM crawl_results ORDER BY created_at DESC LIMIT 10;"

db-stats:  ## Show database statistics
	docker exec crawlagent-postgres psql -U crawlagent -d crawlagent -c \
		"SELECT site_name, COUNT(*) as total, AVG(quality_score) as avg_quality, MAX(created_at) as latest FROM crawl_results GROUP BY site_name;"

# ========================================
# Cleanup
# ========================================
clean:  ## Stop and remove all containers, volumes, and images
	@echo "🗑️  전체 데이터 삭제 중 (주의!)"
	@echo "   - 컨테이너 중지 및 삭제"
	@echo "   - PostgreSQL 데이터 삭제"
	@echo "   - Docker 이미지 삭제"
	@read -p "계속하시겠습니까? (y/N): " confirm && [ "$$confirm" = "y" ] || exit 1
	docker-compose down -v --rmi all
	rm -rf logs/* htmlcov/*
	@echo "✅ 삭제 완료"

clean-logs:  ## Remove log files only
	@echo "🗑️  로그 파일 삭제 중..."
	rm -rf logs/*
	@echo "✅ 로그 삭제 완료"

# ========================================
# Development
# ========================================
shell-app:  ## Open shell in app container
	docker exec -it crawlagent-app /bin/bash

shell-postgres:  ## Open shell in postgres container
	docker exec -it crawlagent-postgres /bin/bash

# ========================================
# Testing
# ========================================
test:  ## Run tests inside Docker container
	docker-compose exec app poetry run pytest -v

test-coverage:  ## Run tests with coverage report
	docker-compose exec app poetry run pytest --cov=src --cov-report=html --cov-report=term

# ========================================
# Quick Commands
# ========================================
open:  ## Open Web UI in browser
	@echo "🌐 브라우저에서 UI 열기..."
	@command -v open > /dev/null 2>&1 && open http://localhost:7860 || echo "http://localhost:7860"

ps:  ## Alias for status
	@make status
