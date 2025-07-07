.PHONY: help lint lint-fix test test-verbose clean format

# Default target
help:
	@echo "Available targets:"
	@echo "  lint         - Run all linting tools (check mode)"
	@echo "  lint-fix     - Run all linting tools (fix mode)"
	@echo "  format       - Format code with black and ruff"
	@echo "  test         - Run tests"
	@echo "  test-verbose - Run tests with verbose output"
	@echo "  clean        - Clean up cache files"

# Linting
lint:
	@echo "Running linting tools in CHECK mode..."
	uv tool run ruff check src tests
	uv tool run ruff format --check src tests
	uv tool run black --check src tests
	uv tool run mypy src
	@echo "Linting checks complete! Run 'lint-fix' to attempt fixing."

lint-fix:
	@echo "Running linting tools in FIX mode..."
	uv tool run ruff check src tests --fix
	uv tool run ruff format src tests
	uv tool run black src tests
	uv tool run mypy src
	@echo "Lint-fix complete!"

# Individual tools
format:
	uv tool run ruff format src tests
	uv tool run black src tests

# Testing
test:
	uv run pytest

test-verbose:
	uv run pytest -v

# Cleanup
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 