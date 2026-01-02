# PostgreSQL to ClickHouse Migration Script

This script migrates all tables from PostgreSQL's public schema to ClickHouse with a `PG_` prefix.

## Prerequisites

- Python 3.7+
- PostgreSQL database with access credentials
- ClickHouse database with access credentials

## Installation

1. Install required packages:
```bash
pip install -r requirements.txt
```

## Configuration

The script uses environment variables for configuration. Create a `.env` file in the project root with the following variables:

**PostgreSQL:**
- PG_HOST (default: localhost)
- PG_PORT (default: 5432)
- PG_DATABASE
- PG_USERNAME
- PG_PASSWORD

**ClickHouse:**
- CLICKHOUSE_HOST
- CLICKHOUSE_USER (default: default)
- CLICKHOUSE_PASS
- CLICKHOUSE_DB

See `.env.example` for a template.

## Usage

Run the migration script:
```bash
python migrate_pg_to_clickhouse.py
```

## What it does

1. Connects to PostgreSQL and lists all tables in the `public` schema
2. For each table:
   - Retrieves the table schema (columns and data types)
   - Maps PostgreSQL data types to ClickHouse data types
   - Creates a table in ClickHouse with `PG_` prefix (e.g., `okrapi_formdata` → `PG_okrapi_formdata`)
   - Migrates all data from PostgreSQL to ClickHouse

## Features

- Automatic type mapping from PostgreSQL to ClickHouse
- Handles nullable columns
- Batch insertion for efficient data transfer
- Comprehensive logging
- Error handling for individual tables

## Notes

- Tables are created with `MergeTree()` engine
- Unknown PostgreSQL types are mapped to `String` in ClickHouse
- Data is inserted in batches of 1000 rows for efficiency

