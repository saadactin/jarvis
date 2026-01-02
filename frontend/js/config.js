// API Configuration
const API_CONFIG = {
    BASE_URL: 'http://localhost:5009',
    ENDPOINTS: {
        AUTH: {
            LOGIN: '/api/auth/login',
            REGISTER: '/api/auth/register',
            ME: '/api/auth/me'
        },
        DATABASE_MASTER: {
            BASE: '/api/database-master',
            BY_ID: (id) => `/api/database-master/${id}`
        },
        OPERATIONS: {
            BASE: '/api/operations',
            BY_ID: (id) => `/api/operations/${id}`,
            STATUS: (id) => `/api/operations/${id}/status`,
            SUMMARY: '/api/operations/summary',
            EXECUTE: (id, force = false) => `/api/operations/${id}/execute?force=${force}`,
            RETRY: (id) => `/api/operations/${id}/retry`
        },
        SERVICES: {
            BASE: '/api/services',
            BY_ID: (id) => `/api/services/${id}`,
            START: (id) => `/api/services/${id}/start`,
            STOP: (id) => `/api/services/${id}/stop`,
            STATUS: (id) => `/api/services/${id}/status`,
            START_ALL: '/api/services/start-all',
            STOP_ALL: '/api/services/stop-all'
        },
        HEALTH: '/health'
    },
    TIMEOUT: 3600000, // 60 minutes for long-running migrations
    POLLING_INTERVAL: 5000 // 5 seconds for running operations
};

// Source and Destination Types
const SOURCE_TYPES = [
    { value: 'postgresql', label: 'PostgreSQL', icon: '🗄️' },
    { value: 'mysql', label: 'MySQL', icon: '🗄️' },
    { value: 'zoho', label: 'Zoho CRM', icon: '☁️' },
    { value: 'sqlserver', label: 'SQL Server', icon: '🗄️' },
    { value: 'devops', label: 'Azure DevOps', icon: '🔧' }
];

const DESTINATION_TYPES = [
    { value: 'clickhouse', label: 'ClickHouse', icon: '📊' },
    { value: 'postgresql', label: 'PostgreSQL', icon: '🗄️' },
    { value: 'mysql', label: 'MySQL', icon: '🗄️' }
];

// Operation Types
const OPERATION_TYPES = [
    { value: 'full', label: 'Full Migration' },
    { value: 'incremental', label: 'Incremental Migration' }
];

// Operation Status
const OPERATION_STATUS = {
    PENDING: 'pending',
    RUNNING: 'running',
    COMPLETED: 'completed',
    FAILED: 'failed'
};

// Status Colors
const STATUS_COLORS = {
    pending: '#757575',
    running: '#0288d1',
    completed: '#2e7d32',
    failed: '#d32f2f',
    cancelled: '#f57c00'
};

// Status Labels
const STATUS_LABELS = {
    pending: 'Pending',
    running: 'Running',
    completed: 'Completed',
    failed: 'Failed',
    cancelled: 'Cancelled',
    stopped: 'Stopped',
    error: 'Error',
    not_found: 'Not Found'
};
