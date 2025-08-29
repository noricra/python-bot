# Makefile for TechBot Marketplace

.PHONY: help install install-dev test lint format type-check security clean run-dev run-prod docker-build docker-run setup-pre-commit

# Default target
help:
	@echo "TechBot Marketplace - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install production dependencies"
	@echo "  install-dev     Install development dependencies"
	@echo "  setup-pre-commit Setup pre-commit hooks"
	@echo ""
	@echo "Quality Assurance:"
	@echo "  test            Run tests with coverage"
	@echo "  lint            Run linting (ruff)"
	@echo "  format          Format code (black)"
	@echo "  type-check      Run type checking (mypy)"
	@echo "  security        Run security checks"
	@echo "  qa              Run all quality checks"
	@echo ""
	@echo "Development:"
	@echo "  run-dev         Run development server"
	@echo "  run-prod        Run production server"
	@echo "  clean           Clean cache files"
	@echo ""
	@echo "Docker:"
	@echo "  docker-build    Build Docker image"
	@echo "  docker-run      Run Docker container"

# Installation
install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements.txt -r requirements-dev.txt

setup-pre-commit:
	pre-commit install
	pre-commit install --hook-type commit-msg

# Quality Assurance
test:
	pytest --cov=app --cov-report=html --cov-report=term-missing

test-fast:
	pytest -x --ff

lint:
	ruff check app/ tests/

lint-fix:
	ruff check --fix app/ tests/

format:
	black app/ tests/

format-check:
	black --check app/ tests/

type-check:
	mypy app/

security:
	safety check
	bandit -r app/

qa: lint format-check type-check test security
	@echo "✅ All quality checks passed!"

# Development
run-dev:
	python marketplace_bot_refactored.py

run-legacy:
	python bot_mlt.py

run-prod:
	python -O marketplace_bot_refactored.py

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .coverage htmlcov/ .pytest_cache/ .mypy_cache/ .ruff_cache/

# Docker
docker-build:
	docker build -t techbot-marketplace:latest .

docker-run:
	docker run --rm -it \
		--env-file .env \
		-v $(PWD)/logs:/app/logs \
		-v $(PWD)/uploads:/app/uploads \
		-v $(PWD)/wallets:/app/wallets \
		techbot-marketplace:latest

# Database
db-backup:
	cp marketplace_database.db marketplace_database.db.backup.$(shell date +%Y%m%d_%H%M%S)

# Monitoring
logs:
	tail -f logs/marketplace.log

# Release
version-check:
	python -c "import app; print(f'Version: 3.0.0')"

# Performance
profile:
	python -m cProfile -o profile.stats marketplace_bot_refactored.py

# Documentation
docs:
	@echo "📚 Generating documentation..."
	@echo "TODO: Add documentation generation"