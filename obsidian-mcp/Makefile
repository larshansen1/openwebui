.PHONY: test test-unit test-integration test-coverage install-dev clean

# Install development dependencies
install-dev:
	pip install -r requirements.txt

# Run all tests
test:
	pytest tests/ -v

# Run unit tests only
test-unit:
	pytest tests/unit/ -v -m unit

# Run integration tests only
test-integration:
	pytest tests/integration/ -v -m integration

# Run tests with coverage report
test-coverage:
	pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html

# Run specific test file
test-file:
	pytest $(FILE) -v

# Run tests matching pattern
test-pattern:
	pytest tests/ -v -k "$(PATTERN)"

# Run tests by marker
test-marker:
	pytest tests/ -v -m "$(MARKER)"

# Clean test artifacts
clean:
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf **/__pycache__
	rm -rf **/*.pyc
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# Show available test markers
test-markers:
	pytest --markers

# Run tests in Docker container
docker-test:
	docker compose exec obsidian-mcp pytest tests/ -v

# Run tests with coverage in Docker
docker-test-coverage:
	docker compose exec obsidian-mcp pytest tests/ -v --cov=app --cov-report=term-missing
