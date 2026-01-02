// Service Manager Page Logic

let services = [];
let pollingInterval = null;
let isInitializing = false;
let isLoadingServices = false;

// Use a flag to prevent multiple initializations
if (!window.servicesPageInitialized) {
    window.servicesPageInitialized = true;
    
    document.addEventListener('DOMContentLoaded', async () => {
        // Prevent multiple initializations
        if (isInitializing) {
            return;
        }
        isInitializing = true;
        
        // Ensure auth is checked before loading services
        if (!requireAuth()) {
            isInitializing = false;
            return; // Will redirect to login
        }
        
        try {
            await loadServices();
            // Start polling for status updates only after initial load completes
            startPolling();
        } catch (error) {
            console.error('Error initializing services page:', error);
            showError('Failed to initialize services page. Please refresh.');
            isInitializing = false;
        }
    });
}

async function loadServices() {
    // Prevent concurrent calls
    if (isLoadingServices) {
        return;
    }
    isLoadingServices = true;
    
    const container = document.getElementById('servicesContainer');
    if (container && !container.classList.contains('loading')) {
        showLoading(container);
    }
    
    try {
        const response = await servicesAPI.getAll();
        services = response.services || [];
        renderServices();
    } catch (error) {
        console.error('Error loading services:', error);
        showError('Failed to load services: ' + (error.message || 'Unknown error'));
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error Loading Services</div>
                    <div class="empty-state-text">${error.message || 'Unknown error'}</div>
                    <button onclick="loadServices()" class="btn btn-primary mt-md">Retry</button>
                </div>
            `;
        }
    } finally {
        isLoadingServices = false;
    }
}

function calculateServiceStats() {
    const stats = {
        total: services.length,
        running: 0,
        stopped: 0,
        failed: 0,
        required: {
            total: 0,
            running: 0,
            stopped: 0,
            failed: 0
        },
        optional: {
            total: 0,
            running: 0,
            stopped: 0,
            failed: 0
        },
        health: 'healthy' // 'healthy', 'warning', 'critical', 'unknown'
    };
    
    services.forEach(service => {
        const status = service.status || 'stopped';
        const isRequired = service.required || false;
        
        // Overall counts
        if (status === 'running') {
            stats.running++;
        } else if (status === 'stopped') {
            stats.stopped++;
        } else if (status === 'failed' || status === 'error') {
            stats.failed++;
        }
        
        // Required/Optional breakdown
        if (isRequired) {
            stats.required.total++;
            if (status === 'running') {
                stats.required.running++;
            } else if (status === 'stopped') {
                stats.required.stopped++;
            } else if (status === 'failed' || status === 'error') {
                stats.required.failed++;
            }
        } else {
            stats.optional.total++;
            if (status === 'running') {
                stats.optional.running++;
            } else if (status === 'stopped') {
                stats.optional.stopped++;
            } else if (status === 'failed' || status === 'error') {
                stats.optional.failed++;
            }
        }
    });
    
    // Determine health status
    if (stats.total === 0) {
        stats.health = 'unknown';
    } else if (stats.required.total > 0) {
        // Critical if required services failed or not all running
        if (stats.required.failed > 0 || stats.required.running < stats.required.total) {
            stats.health = 'critical';
        } else if (stats.failed > 0) {
            // Warning if optional services have errors
            stats.health = 'warning';
        } else {
            stats.health = 'healthy';
        }
    } else if (stats.failed > 0) {
        stats.health = 'warning';
    } else {
        stats.health = 'healthy';
    }
    
    return stats;
}

function renderServiceStats() {
    const container = document.getElementById('serviceStatsContainer');
    if (!container) return;
    
    const stats = calculateServiceStats();
    
    // Determine health status display
    let healthColor = 'success';
    let healthIcon = '✅';
    let healthMessage = 'All Systems Operational';
    
    if (stats.health === 'unknown') {
        healthColor = 'info';
        healthIcon = '❓';
        healthMessage = 'No services configured';
    } else if (stats.health === 'critical') {
        healthColor = 'error';
        healthIcon = '🔴';
        healthMessage = 'Service Issues Detected';
    } else if (stats.health === 'warning') {
        healthColor = 'error';
        healthIcon = '⚠️';
        healthMessage = 'Some Services Stopped';
    }
    
    // Create stat cards
    const statsCards = [
        createStatsCard('🔧', stats.total, 'Total Services', 'primary'),
        createStatsCard('✅', stats.running, 'Running', 'success'),
        createStatsCard('⏹️', stats.stopped, 'Stopped', 'info'),
        createStatsCard('❌', stats.failed, 'Failed/Error', 'error'),
        createStatsCard('⭐', stats.required.total, 'Required', 'primary'),
        createStatsCard(
            healthIcon,
            stats.required.total > 0 ? `${stats.required.running}/${stats.required.total}` : '0/0',
            'Required Running',
            healthColor
        )
    ];
    
    container.innerHTML = `
        <div class="card">
            <div class="card-header">
                <h2 class="card-title">Service Status Overview</h2>
                <div class="text-sm" style="color: var(--${healthColor}); font-weight: 500;">
                    ${healthIcon} ${healthMessage}
                </div>
            </div>
            <div class="card-body">
                <div class="stats-grid">
                    ${statsCards.join('')}
                </div>
            </div>
        </div>
    `;
}

function renderServices() {
    // Render stats dashboard first
    renderServiceStats();
    
    const container = document.getElementById('servicesContainer');
    if (!container) return;
    
    // Clear loading state first
    hideLoading(container);
    
    if (services.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🔧</div>
                <div class="empty-state-title">No Services Found</div>
                <div class="empty-state-text">No services are configured.</div>
            </div>
        `;
        return;
    }
    
    // Separate required and optional services
    const requiredServices = services.filter(s => s.required);
    const optionalServices = services.filter(s => !s.required);
    
    let html = '';
    
    if (requiredServices.length > 0) {
        html += '<div class="mb-lg"><h2 class="mb-md">Required Services</h2>';
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-lg);">';
        html += requiredServices.map(service => createServiceCard(service)).join('');
        html += '</div></div>';
    }
    
    if (optionalServices.length > 0) {
        html += '<div><h2 class="mb-md">Optional Services (Legacy)</h2>';
        html += '<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-lg);">';
        html += optionalServices.map(service => createServiceCard(service)).join('');
        html += '</div></div>';
    }
    
    container.innerHTML = html;
}

function createServiceCard(service) {
    const status = service.status || 'stopped';
    const statusBadge = createStatusBadge(status);
    
    return `
        <div class="card">
            <div class="card-header">
                <div>
                    <h3 class="card-title">${service.name}</h3>
                    ${service.required ? '<span class="badge badge-running" style="background: #fff3cd; color: #856404;">Required</span>' : ''}
                </div>
                ${statusBadge}
            </div>
            <div class="card-body">
                <div class="mb-md">
                    <div class="text-secondary text-sm">Port</div>
                    <div class="text-md font-bold">${service.port}</div>
                </div>
                <div class="mb-md">
                    <div class="text-secondary text-sm">Description</div>
                    <div class="text-sm">${service.description || 'No description'}</div>
                </div>
                ${service.process_info && service.process_info.pid ? `
                    <div class="mb-md">
                        <div class="text-secondary text-sm">Process ID</div>
                        <div class="text-sm">${service.process_info.pid}</div>
                    </div>
                ` : ''}
            </div>
        </div>
    `;
}

async function startService(serviceId) {
    const button = event?.target;
    const originalText = button ? button.textContent : '';
    if (button) {
        button.disabled = true;
        button.textContent = 'Starting...';
    }
    
    try {
        const response = await servicesAPI.start(serviceId);
        if (response.success) {
            showSuccess(response.message || 'Service started successfully');
        } else {
            showError(response.error || response.message || 'Failed to start service');
        }
        await loadServices();
    } catch (error) {
        console.error('Error starting service:', error);
        showError(error.message || 'Failed to start service');
        await loadServices();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function stopService(serviceId) {
    if (!confirm(`Are you sure you want to stop this service?`)) {
        return;
    }
    
    const button = event?.target;
    const originalText = button ? button.textContent : '';
    if (button) {
        button.disabled = true;
        button.textContent = 'Stopping...';
    }
    
    try {
        const response = await servicesAPI.stop(serviceId);
        if (response.success) {
            showSuccess(response.message || 'Service stopped successfully');
        } else {
            showError(response.error || response.message || 'Failed to stop service');
        }
        await loadServices();
    } catch (error) {
        console.error('Error stopping service:', error);
        showError(error.message || 'Failed to stop service');
        await loadServices();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function startAllServices() {
    if (!confirm('Start all required services? This may take a few moments.')) {
        return;
    }
    
    const button = event?.target;
    const originalText = button ? button.textContent : '';
    if (button) {
        button.disabled = true;
        button.textContent = 'Starting...';
    }
    
    try {
        const response = await servicesAPI.startAll();
        if (response.success) {
            showSuccess(response.message || 'All required services started');
            // Show individual results if available
            if (response.results && response.results.length > 0) {
                const failed = response.results.filter(r => !r.success);
                if (failed.length > 0) {
                    const failedNames = failed.map(r => r.service_id).join(', ');
                    showInfo(`Some services failed to start: ${failedNames}`);
                }
            }
        } else {
            showError(response.error || response.message || 'Failed to start all services');
        }
        await loadServices();
    } catch (error) {
        console.error('Error starting all services:', error);
        showError(error.message || 'Failed to start all services');
        await loadServices();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function stopAllServices() {
    if (!confirm('Stop all running services? This will stop all services immediately.')) {
        return;
    }
    
    const button = event?.target;
    const originalText = button ? button.textContent : '';
    if (button) {
        button.disabled = true;
        button.textContent = 'Stopping...';
    }
    
    try {
        const response = await servicesAPI.stopAll();
        if (response.success) {
            showSuccess(response.message || 'All services stopped');
        } else {
            showError(response.error || response.message || 'Failed to stop all services');
        }
        await loadServices();
    } catch (error) {
        console.error('Error stopping all services:', error);
        showError(error.message || 'Failed to stop all services');
        await loadServices();
    } finally {
        if (button) {
            button.disabled = false;
            button.textContent = originalText;
        }
    }
}

async function refreshServiceStatus(serviceId) {
    try {
        const response = await servicesAPI.getStatus(serviceId);
        // Update the service in the list
        const index = services.findIndex(s => s.id === serviceId);
        if (index !== -1) {
            services[index] = response.service;
            renderServices();
        }
        showInfo('Status refreshed');
    } catch (error) {
        console.error('Error refreshing service status:', error);
        showError(error.message || 'Failed to refresh status');
    }
}

function startPolling() {
    // Clear any existing polling interval first
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
    // Poll for status updates every 20 seconds (reduced frequency to avoid constant refreshing and reduce server load)
    pollingInterval = setInterval(() => {
        if (!isLoadingServices) {
            loadServices();
        }
    }, 20000);
}

// Make loadServices globally accessible (for potential refresh needs)
window.loadServices = loadServices;

// Cleanup
window.addEventListener('beforeunload', () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});


