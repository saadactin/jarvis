# Zoho API to ClickHouse Migration API Documentation

## Base URL
```
http://localhost:5002
```

## Overview

This microservice provides REST API endpoints for syncing data from Zoho CRM to ClickHouse databases. It supports full synchronization of all modules or selected modules.

## Authentication

This service uses Zoho OAuth 2.0 authentication. You need to provide:
- `refresh_token`: Zoho OAuth refresh token
- `client_id`: Zoho OAuth client ID
- `client_secret`: Zoho OAuth client secret
- `api_domain`: Zoho API domain (based on your region)

## Endpoints

### 1. Health Check

Check if the service is running and healthy.

**Endpoint:** `GET /health`

**Request:**
```http
GET /health HTTP/1.1
Host: localhost:5002
```

**Response:**
```json
{
  "status": "healthy",
  "service": "zoho_migration"
}
```

**Status Codes:**
- `200 OK` - Service is healthy

---

### 2. Full Sync

Perform a complete synchronization of all records from Zoho CRM modules to ClickHouse. Fetches all records from specified modules and stores them in ClickHouse.

**Endpoint:** `POST /sync/full`

**Request Headers:**
```http
Content-Type: application/json
```

**Request Body:**
```json
{
  "zoho": {
    "refresh_token": "string (required)",
    "client_id": "string (required)",
    "client_secret": "string (required)",
    "api_domain": "string (optional, default: https://www.zohoapis.in)"
  },
  "clickhouse": {
    "host": "string (required)",
    "database": "string (required)",
    "username": "string (required)",
    "password": "string (required)"
  },
  "selected_modules": ["string"] (optional)
}
```

**Request Example:**
```json
{
  "zoho": {
    "refresh_token": "1000.abc123def456ghi789",
    "client_id": "1000.ABCD1234EFGH5678",
    "client_secret": "abc123def456ghi789jkl012mno345pqr",
    "api_domain": "https://www.zohoapis.in"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "zoho_crm",
    "username": "default",
    "password": "clickhouse_password"
  },
  "selected_modules": ["Accounts", "Contacts", "Deals"]
}
```

**Request with All Modules:**
```json
{
  "zoho": {
    "refresh_token": "1000.abc123def456ghi789",
    "client_id": "1000.ABCD1234EFGH5678",
    "client_secret": "abc123def456ghi789jkl012mno345pqr",
    "api_domain": "https://www.zohoapis.in"
  },
  "clickhouse": {
    "host": "localhost",
    "database": "zoho_crm",
    "username": "default",
    "password": "clickhouse_password"
  }
}
```
*Note: Omitting `selected_modules` will sync all available modules*

**Success Response (200 OK):**
```json
{
  "success": true,
  "synced_modules": [
    {
      "module": "Accounts",
      "record_count": 1500
    },
    {
      "module": "Contacts",
      "record_count": 3200
    },
    {
      "module": "Deals",
      "record_count": 850
    }
  ],
  "failed_modules": [],
  "total_records": 5550,
  "errors": []
}
```

**Error Response (400 Bad Request):**
```json
{
  "error": "zoho.refresh_token is required"
}
```

**Error Response (500 Internal Server Error):**
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
      "error": "Failed to obtain access token"
    }
  ],
  "total_records": 1500,
  "errors": [
    "Contacts: Failed to obtain access token"
  ]
}
```

**Status Codes:**
- `200 OK` - Sync completed successfully
- `400 Bad Request` - Invalid request body or missing required fields
- `500 Internal Server Error` - Sync failed or partial failure

**Notes:**
- Tables in ClickHouse will be prefixed with `zoho_` (e.g., `Accounts` → `zoho_accounts`)
- Uses `ReplacingMergeTree` engine for automatic deduplication
- All fields are stored as `Nullable(String)` type
- Records are inserted with `load_time` timestamp
- Handles pagination automatically (200 records per page)
- Includes retry logic for network errors
- Creates database if it doesn't exist

---

### 3. Incremental Sync

Perform an incremental synchronization of modified records from Zoho CRM to ClickHouse.

**Endpoint:** `POST /sync/incremental`

**Status:** ⚠️ **Not Yet Implemented**

This endpoint is currently not implemented and will return a 501 status code.

**Request:**
```http
POST /sync/incremental HTTP/1.1
Host: localhost:5002
Content-Type: application/json
```

**Response (501 Not Implemented):**
```json
{
  "error": "Incremental sync not yet implemented. Please use /sync/full endpoint.",
  "success": false
}
```

**Status Codes:**
- `501 Not Implemented` - Feature not yet available

---

## Zoho API Domain Options

The `api_domain` field in the Zoho configuration accepts the following values based on your region:

| Region | API Domain |
|--------|------------|
| India | `https://www.zohoapis.in` (default) |
| United States | `https://www.zohoapis.com` |
| Europe | `https://www.zohoapis.eu` |
| Australia | `https://www.zohoapis.com.au` |
| Japan | `https://www.zohoapis.jp` |

The service automatically maps the API domain to the correct accounts domain for OAuth token generation.

---

## Data Storage

### Table Naming Convention
- Module names are converted to lowercase
- Tables are prefixed with `zoho_`
- Example: `Accounts` module → `zoho_accounts` table

### Table Structure
- All fields from Zoho records are preserved
- Fields are sanitized to be ClickHouse-safe (alphanumeric and underscores only)
- All fields stored as `Nullable(String)`
- Automatic `id` field (primary identifier from Zoho)
- Automatic `load_time` field (DateTime, defaults to now())

### Engine
- Uses `ReplacingMergeTree(load_time)` engine
- Orders by `id` field
- Automatically handles duplicates based on `id` and `load_time`

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request succeeded
- **400 Bad Request**: Invalid request parameters
- **500 Internal Server Error**: Server error during processing
- **501 Not Implemented**: Feature not yet available

Error responses include descriptive error messages in the response body.

---

## Rate Limiting and Retry Logic

- The service includes automatic retry logic for network errors (up to 3 retries)
- Handles session locks in ClickHouse by recreating connections
- Implements exponential backoff for retries
- Large modules may take significant time to sync

---

## Examples

### cURL Examples

**Health Check:**
```bash
curl -X GET http://localhost:5002/health
```

**Full Sync (Selected Modules):**
```bash
curl -X POST http://localhost:5002/sync/full \
  -H "Content-Type: application/json" \
  -d '{
    "zoho": {
      "refresh_token": "1000.abc123def456ghi789",
      "client_id": "1000.ABCD1234EFGH5678",
      "client_secret": "abc123def456ghi789jkl012mno345pqr",
      "api_domain": "https://www.zohoapis.in"
    },
    "clickhouse": {
      "host": "localhost",
      "database": "zoho_crm",
      "username": "default",
      "password": "clickhouse_password"
    },
    "selected_modules": ["Accounts", "Contacts"]
  }'
```

**Full Sync (All Modules):**
```bash
curl -X POST http://localhost:5002/sync/full \
  -H "Content-Type: application/json" \
  -d '{
    "zoho": {
      "refresh_token": "1000.abc123def456ghi789",
      "client_id": "1000.ABCD1234EFGH5678",
      "client_secret": "abc123def456ghi789jkl012mno345pqr",
      "api_domain": "https://www.zohoapis.in"
    },
    "clickhouse": {
      "host": "localhost",
      "database": "zoho_crm",
      "username": "default",
      "password": "clickhouse_password"
    }
  }'
```

### Python Example

```python
import requests

# Health check
response = requests.get("http://localhost:5002/health")
print(response.json())

# Full sync
payload = {
    "zoho": {
        "refresh_token": "1000.abc123def456ghi789",
        "client_id": "1000.ABCD1234EFGH5678",
        "client_secret": "abc123def456ghi789jkl012mno345pqr",
        "api_domain": "https://www.zohoapis.in"
    },
    "clickhouse": {
        "host": "localhost",
        "database": "zoho_crm",
        "username": "default",
        "password": "clickhouse_password"
    },
    "selected_modules": ["Accounts", "Contacts"]
}

response = requests.post(
    "http://localhost:5002/sync/full",
    json=payload
)
result = response.json()
print(f"Synced {result['total_records']} records")
for module in result["synced_modules"]:
    print(f"  {module['module']}: {module['record_count']} records")
```

### JavaScript Example

```javascript
// Health check
fetch('http://localhost:5002/health')
  .then(response => response.json())
  .then(data => console.log(data));

// Full sync
const payload = {
  zoho: {
    refresh_token: "1000.abc123def456ghi789",
    client_id: "1000.ABCD1234EFGH5678",
    client_secret: "abc123def456ghi789jkl012mno345pqr",
    api_domain: "https://www.zohoapis.in"
  },
  clickhouse: {
    host: "localhost",
    database: "zoho_crm",
    username: "default",
    password: "clickhouse_password"
  },
  selected_modules: ["Accounts", "Contacts"]
};

fetch('http://localhost:5002/sync/full', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(payload)
})
  .then(response => response.json())
  .then(data => {
    console.log(`Synced ${data.total_records} records`);
    data.synced_modules.forEach(module => {
      console.log(`  ${module.module}: ${module.record_count} records`);
    });
  });
```

---

## Getting Zoho OAuth Credentials

To use this API, you need to obtain OAuth credentials from Zoho:

1. Go to [Zoho API Console](https://api-console.zoho.com/)
2. Create a new client application
3. Note down:
   - **Client ID**: Found in your application details
   - **Client Secret**: Found in your application details
   - **Refresh Token**: Generated after authorizing your application
4. Select the appropriate **API domain** based on your Zoho account region

---

## Security Considerations

- **OAuth Tokens**: Store refresh tokens securely. They provide long-term access to Zoho API.
- **HTTPS**: Use HTTPS in production to encrypt credentials in transit.
- **Credentials**: Never commit credentials to version control.
- **Network Security**: Ensure proper network security between the service and databases.
- **Access Control**: Consider implementing authentication/authorization for the API endpoints in production.

---

## Troubleshooting

### Common Errors

**"Failed to obtain access token"**
- Verify your refresh token, client ID, and client secret are correct
- Check that your API domain matches your Zoho account region
- Ensure your OAuth application is properly configured in Zoho

**"No modules found in Zoho CRM"**
- Verify your access token has proper permissions
- Check that your Zoho account has CRM modules enabled

**"Failed to connect to ClickHouse"**
- Verify ClickHouse is running and accessible
- Check network connectivity
- Verify credentials are correct

**"Session lock" errors**
- The service automatically handles session locks by recreating connections
- If errors persist, check ClickHouse server logs

---

## Support

For issues or questions, please refer to the main README.md file or contact the development team.

