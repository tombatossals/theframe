.PHONY: install install-dev format lint type-check test clean

# Install production dependencies
install:
	pip install -e .

# Install development dependencies
install-dev:
	pip install -e ".[dev]"

# Format code with black
format:
	black .

# Lint code with flake8
lint:
	flake8 .

# Type check with mypy
type-check:
	mypy .

# Run tests
test:
	pytest

# Clean Python cache files
clean:
	find . -type f -name "*.py[co]" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	rm -rf .mypy_cache

# Run all checks
check: format lint type-check test