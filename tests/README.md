# Test Suite for Universal Migration Service

This directory contains unit tests and integration tests for the universal migration service.

## Test Structure

- `test_adapters.py` - Unit tests for source and destination adapters
- `test_pipeline.py` - Tests for the universal pipeline engine
- `test_integration.py` - End-to-end integration tests

## Running Tests

### Run all tests
```bash
python -m pytest tests/
```

### Run specific test file
```bash
python -m pytest tests/test_adapters.py
```

### Run with coverage
```bash
python -m pytest tests/ --cov=universal_migration_service --cov-report=html
```

## Test Coverage

### Source Adapters
- PostgreSQL source adapter
- MySQL source adapter
- Zoho API source adapter
- SQL Server source adapter

### Destination Adapters
- ClickHouse destination adapter
- PostgreSQL destination adapter

### Pipeline Engine
- Adapter registration
- Migration orchestration
- Error handling

### Integration Tests
- Health check endpoint
- Migration endpoint validation
- Connection testing
- Zoho to ClickHouse migration
- SQL Server to PostgreSQL migration

## Notes

- Most tests use mocks to avoid requiring actual database connections
- Integration tests may require actual database instances for full testing
- Update test configurations in test files before running

