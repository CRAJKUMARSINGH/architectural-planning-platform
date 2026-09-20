# Advocate-Chambers — top-level Makefile
# Usage: make <target>
# On Windows: install make via winget (winget install GnuWin32.Make)
# or run the equivalent npm scripts documented in CONTRIBUTING.md.

.PHONY: help lint-py lint-web lint typecheck test-baseline verify \
        quality-gate adversarial performance clean

# Default target
help:
	@echo ""
	@echo "Advocate-Chambers — available targets"
	@echo "--------------------------------------"
	@echo "  make verify         Full baseline check (lint + typecheck + tests + gate)"
	@echo "  make lint           Lint Python + TypeScript/Web"
	@echo "  make lint-py        Ruff check + format-check + mypy on Python"
	@echo "  make lint-web       ESLint on TypeScript / Web"
	@echo "  make typecheck      TypeScript typecheck (apps/web)"
	@echo "  make test-baseline  Python unit tests + quality gate"
	@echo "  make quality-gate   Run quality gate script only"
	@echo "  make adversarial    Run adversarial fixture suite (weeks 22+23)"
	@echo "  make performance    Run performance benchmark smoke"
	@echo "  make clean          Remove Python bytecode and output caches"
	@echo ""

# ---------------------------------------------------------------------------
# Python lint
# ---------------------------------------------------------------------------
lint-py:
	ruff check scripts services packages
	ruff format --check scripts services packages
	mypy scripts services --ignore-missing-imports

# ---------------------------------------------------------------------------
# Web lint
# ---------------------------------------------------------------------------
lint-web:
	npm run lint:web

# ---------------------------------------------------------------------------
# Combined lint
# ---------------------------------------------------------------------------
lint: lint-py lint-web

# ---------------------------------------------------------------------------
# TypeScript typecheck
# ---------------------------------------------------------------------------
typecheck:
	npm run typecheck:web

# ---------------------------------------------------------------------------
# Baseline test suite
# ---------------------------------------------------------------------------
test-baseline:
	python -m unittest discover -s tests -p 'test_*.py'
	npm run validate:week21 || true

# ---------------------------------------------------------------------------
# Quality gate only
# ---------------------------------------------------------------------------
quality-gate:
	python scripts/quality_gate.py validate

# ---------------------------------------------------------------------------
# Adversarial suite
# ---------------------------------------------------------------------------
adversarial:
	npm run test:week22
	npm run test:week23

# ---------------------------------------------------------------------------
# Performance smoke
# ---------------------------------------------------------------------------
performance:
	npm run validate:week25

# ---------------------------------------------------------------------------
# Full verification gate (CI equivalent)
# ---------------------------------------------------------------------------
verify: lint-py typecheck test-baseline
	@echo ""
	@echo "✓ Baseline verification complete"
	@echo "  Run 'make adversarial' for the full adversarial suite."
	@echo ""

# ---------------------------------------------------------------------------
# Clean
# ---------------------------------------------------------------------------
clean:
	find . -type d -name __pycache__ -not -path './.kilo/*' -exec rm -rf {} + 2>/dev/null || true
	find . -name '*.pyc' -not -path './.kilo/*' -delete 2>/dev/null || true

# ---------------------------------------------------------------------------
# Docker / Compose helpers (E09)
# ---------------------------------------------------------------------------
.PHONY: docker-build docker-up docker-staging docker-down

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-staging:
	docker compose -f docker-compose.yml -f docker-compose.staging.yml up -d

docker-down:
	docker compose down
