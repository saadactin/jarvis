# API Documentation

This folder contains the API documentation for the SQL PostgreSQL to ClickHouse Migration Service.

## Files

- **API.md** - Comprehensive API documentation in Markdown format
  - Includes endpoint descriptions
  - Request/response examples
  - Error handling information
  - Code examples in multiple languages

- **openapi.yaml** - OpenAPI 3.0.3 specification
  - Machine-readable API specification
  - Can be used with tools like Swagger UI, Postman, etc.
  - Includes all endpoints, schemas, and examples

## Viewing the Documentation

### Markdown Documentation
Simply open `API.md` in any Markdown viewer or text editor.

### OpenAPI Specification

#### Using Swagger UI

1. Install Swagger UI:
   ```bash
   npm install -g swagger-ui-serve
   ```

2. View the specification:
   ```bash
   swagger-ui-serve openapi.yaml
   ```

#### Using Online Tools

1. Copy the contents of `openapi.yaml`
2. Paste into [Swagger Editor](https://editor.swagger.io/)
3. View the interactive documentation

#### Using Postman

1. Import `openapi.yaml` into Postman
2. Postman will generate a collection from the specification
3. Use the collection to test the API

## Quick Reference

### Base URL
- Development: `http://localhost:5003`
- Production: Configure as needed

### Endpoints

- `GET /health` - Health check
- `POST /migrate/full` - Full migration
- `POST /migrate/incremental` - Incremental migration

### Request Format
All POST requests require `Content-Type: application/json` header.

See `API.md` for detailed documentation and examples.

