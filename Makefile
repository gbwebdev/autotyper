.PHONY: help install install-dev test lint format clean build dist binary binary-clean binary-test

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install the package
	pip install -e .

install-dev:  ## Install the package with development dependencies
	pip install -e ".[dev]"

test:  ## Run tests
	pytest

test-cov:  ## Run tests with coverage
	pytest --cov=autotyper --cov-report=html --cov-report=term-missing

lint:  ## Run linting
	flake8 src/ tests/
	mypy src/

format:  ## Format code
	black src/ tests/
	isort src/ tests/

format-check:  ## Check code formatting
	black --check src/ tests/
	isort --check-only src/ tests/

clean:  ## Clean build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

build:  ## Build the package
	python -m build

dist: clean build  ## Create distribution packages

check: format-check lint test  ## Run all checks

all: clean install-dev check  ## Run full development setup and checks

binary:  ## Build standalone Linux binary
	./build-binary.sh

binary-clean:  ## Clean and build standalone Linux binary
	./build-binary.sh clean

binary-test:  ## Test the built binary
	@if [ -f dist/autotyper ]; then \
		echo "Testing binary..."; \
		dist/autotyper --help; \
		dist/autotyper --dump-layout --layout us; \
		echo "Binary tests passed!"; \
	else \
		echo "Binary not found. Run 'make binary' first."; \
		exit 1; \
	fi
