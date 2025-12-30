#!/bin/bash
# Test runner script for Obsidian MCP

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Obsidian MCP Test Suite${NC}"
echo "================================"

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}Error: pytest not found${NC}"
    echo "Please install test dependencies: pip install -r requirements.txt"
    exit 1
fi

# Parse command line arguments
TEST_TYPE="${1:-all}"
COVERAGE="${2:-false}"

case "$TEST_TYPE" in
    unit)
        echo -e "${GREEN}Running unit tests...${NC}"
        if [ "$COVERAGE" = "coverage" ]; then
            pytest tests/unit/ -v --cov=app --cov-report=term-missing --cov-report=html
        else
            pytest tests/unit/ -v -m unit
        fi
        ;;
    integration)
        echo -e "${GREEN}Running integration tests...${NC}"
        if [ "$COVERAGE" = "coverage" ]; then
            pytest tests/integration/ -v --cov=app --cov-report=term-missing --cov-report=html
        else
            pytest tests/integration/ -v -m integration
        fi
        ;;
    parser)
        echo -e "${GREEN}Running parser tests...${NC}"
        pytest tests/ -v -m parser
        ;;
    manager)
        echo -e "${GREEN}Running manager tests...${NC}"
        pytest tests/ -v -m manager
        ;;
    api)
        echo -e "${GREEN}Running API tests...${NC}"
        pytest tests/ -v -m api
        ;;
    mcp)
        echo -e "${GREEN}Running MCP tests...${NC}"
        pytest tests/ -v -m mcp
        ;;
    all)
        echo -e "${GREEN}Running all tests...${NC}"
        if [ "$COVERAGE" = "coverage" ]; then
            pytest tests/ -v --cov=app --cov-report=term-missing --cov-report=html
        else
            pytest tests/ -v
        fi
        ;;
    *)
        echo -e "${RED}Unknown test type: $TEST_TYPE${NC}"
        echo "Usage: $0 [unit|integration|parser|manager|api|mcp|all] [coverage]"
        exit 1
        ;;
esac

# Check test result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi
