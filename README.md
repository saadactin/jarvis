# 🚀 Jarvis Migration System

> **Universal Data Migration Platform** - Migrate data between any supported source and destination with ease.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Jarvis Migration System is a comprehensive, web-based platform for migrating data between various database systems and APIs. Built with a universal adapter architecture, it supports multiple source and destination combinations through a single, unified service.

---

## 📋 Table of Contents

- [Features](#-features)
- [Architecture](#-architecture)
- [Supported Sources & Destinations](#-supported-sources--destinations)
- [Quick Start](#-quick-start)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Usage](#-usage)
- [Project Structure](#-project-structure)
- [API Documentation](#-api-documentation)
- [Migration Examples](#-migration-examples)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Capabilities

- 🔄 **Universal Migration Engine** - Single service handles all source-to-destination combinations
- 🎯 **Multiple Sources** - PostgreSQL, MySQL, SQL Server, Zoho CRM, Azure DevOps
- 📊 **Multiple Destinations** - ClickHouse, PostgreSQL, MySQL
- 🌐 **Web-Based UI** - Intuitive interface for managing migrations
- ⏰ **Scheduled Migrations** - Schedule operations for future execution
- 🔁 **Incremental Sync** - Support for incremental data synchronization
- 🔐 **JWT Authentication** - Secure user authentication and authorization
- 📈 **Real-Time Monitoring** - Live status updates and progress tracking
- 🛡️ **Error Handling** - Comprehensive error handling with retry logic
- 📝 **Operation Management** - Create, view, edit, and delete migration operations

### Advanced Features

- **Adapter Pattern Architecture** - Easy to extend with new database types
- **Automatic Type Mapping** - Intelligent data type conversion between systems
- **Batch Processing** - Efficient batch-based data migration
- **Connection Testing** - Test connections before migration
- **Service Management** - Start/stop services from the UI
- **Operation Cancellation** - Stop running migrations and preserve partial data
- **Comprehensive Logging** - Detailed logs for debugging and monitoring

---

## 🏗️ Architecture

Jarvis Migration System follows a **microservices architecture** with a universal adapter pattern:

```
┌─────────────────────────────────────────────────────────────┐
│                    Main Backend (jarvis-main)               │
│                    Port: 5009                              │
│  • User Authentication (JWT)                                │
│  • Operation Management                                     │
│  • Service Orchestration                                    │
│  • Database Master Registry                                 │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ HTTP API Calls
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              Universal Migration Service                    │
│              Port: 5011                                     │
│  • Universal Pipeline Engine                                │
│  • Source Adapters (PostgreSQL, MySQL, SQL Server, etc.)    │
│  • Destination Adapters (ClickHouse, PostgreSQL, MySQL)      │
│  • Type Mapping & Transformation                          │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ Data Flow
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Web UI)                        │
│                    Port: 8080 (optional)                    │
│  • Dashboard                                                │
│  • Operations Management                                    │
│  • Service Manager                                          │
│  • Real-time Status Updates                                 │
└─────────────────────────────────────────────────────────────┘
```

### Universal Adapter Pattern

The system uses a **universal adapter pattern** that provides:

- **Linear Growth**: Adding one new source works with ALL existing destinations
- **No Duplication**: One adapter per database type (not one per combination)
- **Easy Extension**: Just implement the adapter interface

**Example:** Adding a new source (e.g., MongoDB) automatically enables:
- MongoDB → ClickHouse ✅
- MongoDB → PostgreSQL ✅
- MongoDB → MySQL ✅
- MongoDB → Any future destination ✅

---

## 🗄️ Supported Sources & Destinations

### Sources (5)

| Source | Type | Status |
|--------|------|--------|
| PostgreSQL | Database | ✅ |
| MySQL | Database | ✅ |
| SQL Server | Database | ✅ |
| Zoho CRM | API | ✅ |
| Azure DevOps | API | ✅ |

### Destinations (3)

| Destination | Type | Status |
|-------------|------|--------|
| ClickHouse | Database | ✅ |
| PostgreSQL | Database | ✅ |
| MySQL | Database | ✅ |

### Migration Combinations

With **5 sources** and **3 destinations**, you get **15 possible combinations**:

| Source | → ClickHouse | → PostgreSQL | → MySQL |
|--------|:------------:|:------------:|:-------:|
| **PostgreSQL** | ✅ | ✅ | ✅ |
| **MySQL** | ✅ | ✅ | ✅ |
| **SQL Server** | ✅ | ✅ | ✅ |
| **Zoho CRM** | ✅ | ✅ | ✅ |
| **Azure DevOps** | ✅ | ✅ | ✅ |

> **Note:** Same source/destination migrations (e.g., PostgreSQL → PostgreSQL) are automatically prevented.

---

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- PostgreSQL (for main backend database)
- Access to source and destination databases/APIs

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/jarvis-migration-system.git
cd jarvis-migration-system/Backend
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and fill in your credentials
# See Configuration section for details
```

### 3. Install Dependencies

```bash
# Install main backend dependencies
cd jarvis-main
pip install -r requirements.txt

# Install universal migration service dependencies
cd ../universal_migration_service
pip install -r requirements.txt
```

### 4. Start Services

**Option A: Using Service Manager UI (Recommended)**

1. Start main backend:
   ```bash
   cd jarvis-main
   python app.py
   ```

2. Open frontend in browser: `http://localhost:8080`
3. Login/Register
4. Go to **Service Manager** → Click **"Start All Required"**

**Option B: Manual Start**

```bash
# Terminal 1: Main Backend
cd jarvis-main
python app.py

# Terminal 2: Universal Migration Service
cd universal_migration_service
python app.py
```

### 5. Access the Application

- **Frontend UI**: `http://localhost:8080` (or open `frontend/index.html`)
- **Main Backend API**: `http://localhost:5009`
- **Universal Migration Service**: `http://localhost:5011`

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the root directory (use `.env.example` as template):

```env
# Main Backend
DATABASE_URL=postgresql://user:password@localhost:5432/backend_db
SECRET_KEY=your-secret-key-change-in-production
JWT_SECRET_KEY=your-jwt-secret-key-change-in-production
PORT=5009

# Universal Migration Service
UNIVERSAL_MIGRATION_SERVICE_PORT=5011
UNIVERSAL_MIGRATION_SERVICE_HOST=localhost

# Optional: Test credentials (for test scripts)
DEVOPS_ACCESS_TOKEN=your-token
DEVOPS_ORGANIZATION=your-org
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PASSWORD=your-password
# ... see .env.example for all options
```

### Service Ports

- **Main Backend**: `5009` (configurable via `PORT` env var)
- **Universal Migration Service**: `5011` (configurable via `UNIVERSAL_MIGRATION_SERVICE_PORT`)
- **Frontend**: `8080` (if using web server)

---

## 📖 Usage

### Web UI (Recommended)

1. **Register/Login**: Create an account or login
2. **Create Operation**: 
   - Go to **Operations** → **Create Operation**
   - Follow the 6-step wizard:
     1. Select source type
     2. Select destination type
     3. Configure source connection
     4. Configure destination connection
     5. Set schedule and operation type
     6. Review and submit
3. **Execute**: Click "Execute Now" or wait for scheduled time
4. **Monitor**: View real-time status and results

### API Usage

#### Create and Execute Migration

```bash
# 1. Login and get token
TOKEN=$(curl -X POST http://localhost:5009/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"your_user","password":"your_pass"}' \
  | jq -r '.access_token')

# 2. Create operation
curl -X POST http://localhost:5009/api/operations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "source_id": 1,
    "schedule": "2024-01-15T10:00:00",
    "operation_type": "full",
    "config_data": {
      "source_type": "postgresql",
      "dest_type": "clickhouse",
      "source": {
        "host": "localhost",
        "port": 5432,
        "database": "source_db",
        "username": "postgres",
        "password": "password"
      },
      "destination": {
        "host": "localhost",
        "port": 8123,
        "database": "analytics",
        "username": "default",
        "password": "password"
      }
    }
  }'

# 3. Execute operation
curl -X POST http://localhost:5009/api/operations/1/execute \
  -H "Authorization: Bearer $TOKEN"
```

#### Direct Migration Service Call

```bash
curl -X POST http://localhost:5011/migrate \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "postgresql",
    "dest_type": "mysql",
    "source": {
      "host": "localhost",
      "port": 5432,
      "database": "source_db",
      "username": "postgres",
      "password": "password"
    },
    "destination": {
      "host": "localhost",
      "port": 3306,
      "database": "target_db",
      "username": "root",
      "password": "password"
    },
    "operation_type": "full"
  }'
```

---

## 📁 Project Structure

```
Backend/
├── jarvis-main/                    # Main backend service
│   ├── app.py                      # Flask application
│   ├── models.py                   # Database models
│   ├── service_manager.py          # Service management
│   └── requirements.txt
│
├── universal_migration_service/     # Universal migration engine
│   ├── app.py                      # Migration service API
│   ├── pipeline_engine.py          # Core migration logic
│   ├── adapters/
│   │   ├── sources/                # Source adapters
│   │   │   ├── postgresql_source.py
│   │   │   ├── mysql_source.py
│   │   │   ├── sqlserver_source.py
│   │   │   ├── zoho_source.py
│   │   │   └── devops_source.py
│   │   └── destinations/           # Destination adapters
│   │       ├── clickhouse_dest.py
│   │       ├── postgresql_dest.py
│   │       └── mysql_dest.py
│   └── requirements.txt
│
├── frontend/                       # Web UI
│   ├── index.html
│   ├── dashboard.html
│   ├── operations.html
│   ├── create-operation.html
│   ├── css/                        # Stylesheets
│   └── js/                         # JavaScript modules
│
├── tests/                          # Tests and documentation
│   ├── test_*.py                   # Test scripts
│   ├── *.md                        # Documentation
│   └── README.md
│
├── .env.example                    # Environment template
├── .gitignore
└── README.md                       # This file
```

---

## 📚 API Documentation

### Main Backend API

**Base URL**: `http://localhost:5009`

#### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/auth/me` - Get current user

#### Operations
- `GET /api/operations` - List all operations
- `GET /api/operations/:id` - Get operation details
- `POST /api/operations` - Create new operation
- `PUT /api/operations/:id` - Update operation
- `DELETE /api/operations/:id` - Delete/cancel operation
- `POST /api/operations/:id/execute` - Execute operation
- `GET /api/operations/:id/status` - Get operation status

#### Services
- `GET /api/services` - List all services
- `POST /api/services/:id/start` - Start service
- `POST /api/services/:id/stop` - Stop service
- `GET /api/services/:id/status` - Get service status

### Universal Migration Service API

**Base URL**: `http://localhost:5011`

- `GET /health` - Health check and available adapters
- `POST /migrate` - Execute migration
- `POST /test-connection` - Test database/API connection

For detailed API documentation, see:
- [Main Backend API](jarvis-main/api_docs/API.md)
- [Universal Migration Service](universal_migration_service/README.md)

---

## 🔄 Migration Examples

### PostgreSQL to MySQL

```json
{
  "source_type": "postgresql",
  "dest_type": "mysql",
  "source": {
    "host": "localhost",
    "port": 5432,
    "database": "source_db",
    "username": "postgres",
    "password": "password"
  },
  "destination": {
    "host": "localhost",
    "port": 3306,
    "database": "target_db",
    "username": "root",
    "password": "password"
  },
  "operation_type": "full"
}
```

**Features:**
- ✅ Automatic schema extraction
- ✅ Type conversion (PostgreSQL → MySQL)
- ✅ Primary keys, foreign keys, indexes
- ✅ Default value conversion
- ✅ Upsert logic for data migration

### Zoho CRM to ClickHouse

```json
{
  "source_type": "zoho",
  "dest_type": "clickhouse",
  "source": {
    "refresh_token": "your_refresh_token",
    "client_id": "your_client_id",
    "client_secret": "your_client_secret",
    "api_domain": "https://www.zohoapis.com"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

### Azure DevOps to ClickHouse

```json
{
  "source_type": "devops",
  "dest_type": "clickhouse",
  "source": {
    "access_token": "your_access_token",
    "organization": "your_organization",
    "api_version": "7.1"
  },
  "destination": {
    "host": "localhost",
    "port": 8123,
    "database": "devops_analytics",
    "username": "default",
    "password": "password"
  },
  "operation_type": "full"
}
```

### Incremental Migration

```json
{
  "source_type": "postgresql",
  "dest_type": "clickhouse",
  "source": {...},
  "destination": {...},
  "operation_type": "incremental",
  "last_sync_time": "2024-01-01T00:00:00Z"
}
```

---

## 🧪 Testing

### Run Tests

```bash
# Navigate to tests directory
cd tests

# Run all tests (requires .env file with credentials)
python test_adapters.py
python test_pipeline.py
python test_integration.py
```

### Test Scripts

All test scripts are located in the `tests/` directory:

- `test_devops_to_clickhouse_full.py` - Full DevOps migration test
- `test_zoho_to_clickhouse.py` - Zoho to ClickHouse test
- `test_postgres_to_clickhouse.py` - PostgreSQL to ClickHouse test
- `test_connections_comprehensive.py` - Connection testing

**Note:** Test scripts require environment variables to be set in `.env` file.

---

## 🛠️ Development

### Adding a New Source Adapter

1. Create adapter in `universal_migration_service/adapters/sources/`:
   ```python
   from adapters.sources.base_source import BaseSourceAdapter
   
   class NewSourceAdapter(BaseSourceAdapter):
       def connect(self, config):
           # Implementation
           pass
       # ... implement all abstract methods
   ```

2. Register in `universal_migration_service/app.py`:
   ```python
   from adapters.sources.new_source import NewSourceAdapter
   pipeline.register_source("newsource", NewSourceAdapter)
   ```

3. **Done!** New source now works with ALL existing destinations.

### Adding a New Destination Adapter

1. Create adapter in `universal_migration_service/adapters/destinations/`
2. Register in `app.py`
3. **Done!** New destination receives from ALL existing sources.

---

## 📊 Features by Component

### Main Backend (`jarvis-main/`)
- ✅ JWT-based authentication
- ✅ User management
- ✅ Operation scheduling
- ✅ Service management
- ✅ Database master registry
- ✅ Background scheduler

### Universal Migration Service
- ✅ Universal pipeline engine
- ✅ 5 source adapters
- ✅ 3 destination adapters
- ✅ Automatic type mapping
- ✅ Batch processing
- ✅ Error handling & retry logic
- ✅ Connection testing

### Frontend
- ✅ Responsive web UI
- ✅ Real-time status updates
- ✅ Operation wizard
- ✅ Service manager
- ✅ Dashboard with statistics

---

## 🔒 Security

- ✅ All credentials stored in `.env` (never committed)
- ✅ JWT token-based authentication
- ✅ Password hashing (bcrypt)
- ✅ Environment variable validation
- ✅ `.gitignore` configured for sensitive files

**Important:** Never commit `.env` file or files with hardcoded credentials.

---

## 📝 Documentation

Comprehensive documentation is available in the `tests/` directory:

- [Migration Guides](tests/) - Step-by-step migration guides
- [API Documentation](jarvis-main/api_docs/API.md) - Complete API reference
- [Configuration Guide](tests/ENV_TEMPLATE.md) - Environment setup
- [Feature Documentation](tests/) - Feature-specific guides

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation
- Use environment variables (no hardcoded credentials)
- Write clear commit messages

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Built with [Flask](https://flask.palletsprojects.com/)
- Uses [JWT](https://jwt.io/) for authentication
- Database drivers: `psycopg2`, `pymysql`, `pyodbc`, `clickhouse-connect`

---

## 📞 Support

For issues, questions, or contributions:

- 📧 Open an issue on GitHub
- 📖 Check the [documentation](tests/)
- 🔍 Review [troubleshooting guides](tests/)

---

## 🗺️ Roadmap

### Planned Features

- [ ] MongoDB support
- [ ] Cassandra support
- [ ] Oracle Database support
- [ ] Amazon S3 destination
- [ ] Data transformation rules
- [ ] Field mapping UI
- [ ] Webhook notifications
- [ ] Migration templates
- [ ] Performance analytics
- [ ] Data validation tools

---

## ⭐ Star History

If you find this project useful, please consider giving it a star! ⭐

---

**Made with ❤️ for seamless data migrations**

