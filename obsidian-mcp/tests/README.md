# Obsidian MCP Test Suite

Comprehensive test suite for the Obsidian MCP server implementation.

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Unit tests
│   ├── test_parser.py            # MarkdownParser tests
│   └── test_manager.py           # VaultManager tests
└── integration/                   # Integration tests
    ├── test_api_routes.py        # REST API endpoint tests
    └── test_mcp_server.py        # MCP tool tests
```

## Running Tests

### Prerequisites

```bash
# Install test dependencies
pip install -r requirements.txt
```

### Using Make (Recommended)

```bash
# Run all tests
make test

# Run only unit tests
make test-unit

# Run only integration tests
make test-integration

# Run tests with coverage report
make test-coverage

# Run specific test file
make test-file FILE=tests/unit/test_parser.py

# Run tests matching pattern
make test-pattern PATTERN="backlinks"

# Run tests by marker
make test-marker MARKER="parser"

# Clean test artifacts
make clean
```

### Using Test Runner Script

```bash
# Run all tests
./run_tests.sh

# Run specific test types
./run_tests.sh unit
./run_tests.sh integration
./run_tests.sh parser
./run_tests.sh manager
./run_tests.sh api
./run_tests.sh mcp

# Run with coverage
./run_tests.sh all coverage
```

### Using pytest Directly

```bash
# Run all tests
pytest tests/ -v

# Run unit tests only
pytest tests/unit/ -v

# Run integration tests only
pytest tests/integration/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

# Run tests by marker
pytest tests/ -m parser
pytest tests/ -m manager
pytest tests/ -m api
pytest tests/ -m mcp

# Run specific test
pytest tests/unit/test_parser.py::TestMarkdownParser::test_parse_note_with_frontmatter -v
```

### Using Docker

```bash
# Run tests in Docker container
make docker-test

# Run with coverage in Docker
make docker-test-coverage

# Or directly with docker compose
docker compose exec obsidian-mcp pytest tests/ -v
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.parser` - Parser-related tests
- `@pytest.mark.manager` - VaultManager tests
- `@pytest.mark.api` - REST API tests
- `@pytest.mark.mcp` - MCP tool tests

## Test Coverage

Coverage reports are generated in `htmlcov/` directory when running with `--cov` flag.

```bash
# Generate coverage report
pytest tests/ --cov=app --cov-report=html

# Open coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

## Test Fixtures

### Vault Fixtures

- `temp_vault_path` - Empty temporary vault directory
- `sample_notes` - Dictionary of sample note content
- `populated_vault` - Vault populated with sample notes
- `parser` - MarkdownParser instance with populated vault
- `vault_manager` - VaultManager instance with populated vault
- `empty_vault_manager` - VaultManager with empty vault

### API Testing Fixtures

- `client` - FastAPI TestClient
- `headers` - Authentication headers with API key

### MCP Testing Fixtures

- `mcp_server` - ObsidianMCPServer instance

## Writing New Tests

### Unit Test Example

```python
@pytest.mark.unit
@pytest.mark.parser
def test_wiki_link_resolution(parser):
    """Test resolving wiki-links"""
    path = parser.resolve_wiki_link("Welcome")
    assert path == "Welcome.md"
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.api
def test_create_note_api(client, headers):
    """Test creating note via API"""
    payload = {"title": "Test", "content": "Content", "tags": []}
    response = client.post("/tools/create_note", json=payload, headers=headers)
    assert response.status_code == 200
```

### Async MCP Test Example

```python
@pytest.mark.integration
@pytest.mark.mcp
@pytest.mark.asyncio
async def test_mcp_tool(mcp_server):
    """Test MCP tool"""
    result = await mcp_server.call_tool("read_note", {"title": "Welcome"})
    assert len(result) == 1
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v --cov=app --cov-report=xml
```

## Debugging Failed Tests

### Verbose Output

```bash
# Maximum verbosity
pytest tests/ -vv

# Show print statements
pytest tests/ -v -s

# Show local variables on failure
pytest tests/ -v -l
```

### Run Specific Failed Test

```bash
# Copy test name from output
pytest tests/unit/test_parser.py::TestMarkdownParser::test_parse_note_with_frontmatter -v
```

### Use pdb Debugger

```python
def test_something(parser):
    import pdb; pdb.set_trace()
    # Test code here
```

## Performance Considerations

- Unit tests should be fast (< 1s each)
- Integration tests may take longer due to file I/O
- Use `@pytest.mark.slow` for tests that take > 5s

## Test Data

Sample test vault structure:
```
test_vault/
├── Welcome.md
├── Projects.md
├── Ideas.md
├── Getting Started.md
├── Feature Development.md
├── Team.md
├── Orphan Note.md
└── subfolder/
    └── Nested Note.md
```

Each note has frontmatter with title, tags, and wiki-links to other notes for testing backlinks and graph functionality.
