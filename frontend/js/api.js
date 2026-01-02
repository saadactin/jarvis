// API Client Module

/**
 * Make API request
 */
async function apiRequest(url, options = {}) {
    const token = getToken();
    
    const defaultOptions = {
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (token) {
        defaultOptions.headers['Authorization'] = `Bearer ${token}`;
    }
    
    const config = {
        ...defaultOptions,
        ...options,
        headers: {
            ...defaultOptions.headers,
            ...(options.headers || {})
        }
    };
    
    try {
        const response = await fetch(`${API_CONFIG.BASE_URL}${url}`, config);
        
        // Handle 401 Unauthorized
        if (response.status === 401) {
            logout();
            throw new Error('Session expired. Please login again.');
        }
        
        const data = await response.json();
        
        if (!response.ok) {
            throw new Error(data.error || data.message || 'Request failed');
        }
        
        return data;
    } catch (error) {
        if (error.message.includes('fetch')) {
            throw new Error('Network error. Please check your connection.');
        }
        throw error;
    }
}

// Auth API
const authAPI = {
    login: async (username, password) => {
        return apiRequest(API_CONFIG.ENDPOINTS.AUTH.LOGIN, {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
    },
    
    register: async (username, email, password) => {
        return apiRequest(API_CONFIG.ENDPOINTS.AUTH.REGISTER, {
            method: 'POST',
            body: JSON.stringify({ username, email, password })
        });
    },
    
    getCurrentUser: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.AUTH.ME);
    }
};

// Database Master API
const databaseMasterAPI = {
    getAll: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.DATABASE_MASTER.BASE);
    },
    
    getById: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.DATABASE_MASTER.BY_ID(id));
    },
    
    create: async (data) => {
        return apiRequest(API_CONFIG.ENDPOINTS.DATABASE_MASTER.BASE, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    update: async (id, data) => {
        return apiRequest(API_CONFIG.ENDPOINTS.DATABASE_MASTER.BY_ID(id), {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    delete: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.DATABASE_MASTER.BY_ID(id), {
            method: 'DELETE'
        });
    }
};

// Operations API
const operationsAPI = {
    getAll: async (filters = {}) => {
        const params = new URLSearchParams();
        Object.keys(filters).forEach(key => {
            if (filters[key]) {
                params.append(key, filters[key]);
            }
        });
        const queryString = params.toString();
        const url = queryString 
            ? `${API_CONFIG.ENDPOINTS.OPERATIONS.BASE}?${queryString}`
            : API_CONFIG.ENDPOINTS.OPERATIONS.BASE;
        return apiRequest(url);
    },
    
    getById: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.BY_ID(id));
    },
    
    getStatus: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.STATUS(id));
    },
    
    getSummary: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.SUMMARY);
    },
    
    create: async (data) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.BASE, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    },
    
    update: async (id, data) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.BY_ID(id), {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    },
    
    delete: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.BY_ID(id), {
            method: 'DELETE'
        });
    },
    
    execute: async (id, force = false) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.EXECUTE(id, force), {
            method: 'POST'
        });
    },
    
    retry: async (id) => {
        return apiRequest(API_CONFIG.ENDPOINTS.OPERATIONS.RETRY(id), {
            method: 'POST'
        });
    }
};

// Health Check API
const healthAPI = {
    check: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.HEALTH);
    }
};

// Services API
const servicesAPI = {
    getAll: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.BASE);
    },
    
    getStatus: async (serviceId) => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.STATUS(serviceId));
    },
    
    start: async (serviceId) => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.START(serviceId), {
            method: 'POST'
        });
    },
    
    stop: async (serviceId) => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.STOP(serviceId), {
            method: 'POST'
        });
    },
    
    startAll: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.START_ALL, {
            method: 'POST'
        });
    },
    
    stopAll: async () => {
        return apiRequest(API_CONFIG.ENDPOINTS.SERVICES.STOP_ALL, {
            method: 'POST'
        });
    }
};
