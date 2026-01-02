# Zoho API to ClickHouse Migration Microservice

Flask microservice for syncing data from Zoho CRM API to ClickHouse.

## Installation

```bash
cd zoho_service
pip install -r requirements.txt
```

## Running the Service

```bash
python app.py
```

The service will start on `http://0.0.0.0:5002`

## API Endpoints

### Health Check
```
GET /health
```

### Full Sync
```
POST /sync/full
Content-Type: application/json

{
  "zoho": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.in"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "your_database",
    "username": "default",
    "password": "your_password"
  },
  "selected_modules": ["Accounts", "Contacts"]  // Optional: sync all if not provided
}
```

### Incremental Sync
```
POST /sync/incremental
Content-Type: application/json

{
  "zoho": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.in"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "your_database",
    "username": "default",
    "password": "your_password"
  },
  "selected_modules": ["Accounts", "Contacts"]  // Optional
}
```

**Note:** Incremental sync is currently not implemented. Use `/sync/full` endpoint.

## Zoho API Domain Options

- `https://www.zohoapis.in` (India)
- `https://www.zohoapis.com` (US)
- `https://www.zohoapis.eu` (Europe)
- `https://www.zohoapis.com.au` (Australia)
- `https://www.zohoapis.jp` (Japan)

## Response Format

Success response:
```json
{
  "success": true,
  "synced_modules": [
    {
      "module": "Accounts",
      "record_count": 1500
    }
  ],
  "failed_modules": [],
  "total_records": 1500,
  "errors": []
}
```

Error response:
```json
{
  "success": false,
  "synced_modules": [
    {
      "module": "Accounts",
      "record_count": 1500
    }
  ],
  "failed_modules": [
    {
      "module": "Contacts",
      "error": "error message"
    }
  ],
  "total_records": 1500,
  "errors": ["Contacts: error message"]
}
```

## Features

- Syncs all modules from Zoho CRM to ClickHouse
- Creates tables with `zoho_` prefix (e.g., `zoho_accounts`)
- Handles pagination automatically
- Retry logic for network errors
- Session lock handling for ClickHouse
- All fields from Zoho records are preserved
- Uses ReplacingMergeTree engine for automatic deduplication

## Notes

- Tables are created with `ReplacingMergeTree` engine
- All fields are stored as `Nullable(String)` type
- Records are inserted with `load_time` timestamp
- Full sync fetches ALL records from selected modules

