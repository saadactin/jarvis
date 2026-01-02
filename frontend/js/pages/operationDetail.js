// Operation Detail Page Logic

let operation = null;
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    const operationId = getQueryParam('id');
    if (!operationId) {
        showError('Operation ID is required');
        setTimeout(() => window.location.href = 'operations.html', 2000);
        return;
    }
    
    await loadOperation(operationId);
    
    // Poll for status updates if operation is running
    if (operation && operation.status === 'running') {
        startPolling(operationId);
    }
});

async function loadOperation(id) {
    try {
        // Load operation details
        const response = await operationsAPI.getById(id);
        operation = response.operation;
        
        // Load detailed status
        const statusResponse = await operationsAPI.getStatus(id);
        
        renderOperation(operation, statusResponse);
        
        // Continue polling if still running
        if (operation.status === 'running') {
            if (!pollingInterval) {
                startPolling(id);
            }
        } else {
            stopPolling();
        }
        
    } catch (error) {
        console.error('Error loading operation:', error);
        showError('Failed to load operation details');
    }
}

function renderOperation(op, statusData) {
    // Set operation ID
    document.getElementById('operationId').textContent = op.id;
    
    // Set status
    document.getElementById('operationStatus').innerHTML = createStatusBadge(op.status);
    
    // Set type
    document.getElementById('operationType').textContent = op.operation_type || 'N/A';
    
    // Set source
    const sourceType = op.config_data?.source_type || 'N/A';
    const destType = op.config_data?.dest_type || 'N/A';
    document.getElementById('operationSource').textContent = `${sourceType} → ${destType}`;
    
    // Timeline
    const timelineHTML = `
        <div class="text-sm">
            <div class="mb-sm">
                <span class="text-secondary">Created: </span>
                <span>${formatDate(op.created_at)}</span>
            </div>
            ${op.started_at ? `
                <div class="mb-sm">
                    <span class="text-secondary">Started: </span>
                    <span>${formatDate(op.started_at)}</span>
                </div>
            ` : ''}
            ${op.completed_at ? `
                <div>
                    <span class="text-secondary">Completed: </span>
                    <span>${formatDate(op.completed_at)}</span>
                </div>
            ` : ''}
            ${statusData.duration_formatted ? `
                <div class="mt-sm">
                    <span class="text-secondary">Duration: </span>
                    <span>${statusData.duration_formatted}</span>
                </div>
            ` : ''}
        </div>
    `;
    document.getElementById('operationTimeline').innerHTML = timelineHTML;
    
    // Actions
    const actionsHTML = `
        ${op.status === 'pending' ? `
            <button onclick="executeOperation(${op.id})" class="btn btn-success">Execute Now</button>
        ` : ''}
        ${op.status === 'failed' ? `
            <button onclick="retryOperation(${op.id})" class="btn btn-primary">🔄 Retry Migration</button>
        ` : ''}
        ${op.status !== 'running' && op.status !== 'cancelled' ? `
            <a href="create-operation.html?edit=${op.id}" class="btn btn-outline">Edit</a>
        ` : ''}
        <button onclick="deleteOperation(${op.id}, '${op.status}')" class="btn btn-danger">${op.status === 'running' ? 'Stop & Delete' : 'Delete'}</button>
        <a href="operations.html" class="btn btn-secondary">Back</a>
    `;
    document.getElementById('operationActions').innerHTML = actionsHTML;
    
    // Migration Results
    if (statusData.migration_results) {
        const results = statusData.migration_results;
        const resultsCard = document.getElementById('resultsCard');
        resultsCard.style.display = 'block';
        
        const resultsHTML = `
            <div class="mb-lg">
                <div class="d-flex gap-lg flex-wrap">
                    <div>
                        <div class="text-secondary text-sm">Total Tables</div>
                        <div class="text-xl font-bold">${results.total_tables || 0}</div>
                    </div>
                    <div>
                        <div class="text-secondary text-sm">Tables Migrated</div>
                        <div class="text-xl font-bold text-success">${results.tables_migrated_count || 0}</div>
                    </div>
                    <div>
                        <div class="text-secondary text-sm">Tables Failed</div>
                        <div class="text-xl font-bold text-error">${results.tables_failed_count || 0}</div>
                    </div>
                    <div>
                        <div class="text-secondary text-sm">Total Records</div>
                        <div class="text-xl font-bold">${results.total_records || 0}</div>
                    </div>
                </div>
            </div>
            
            ${results.tables_migrated && results.tables_migrated.length > 0 ? `
                <div class="mb-lg">
                    <h3 class="mb-md">Migrated Tables</h3>
                    <div class="table-container">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Table</th>
                                    <th>Records</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${results.tables_migrated.map(table => `
                                    <tr>
                                        <td>${table.table}</td>
                                        <td>${table.records || 0}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : ''}
            
            ${results.tables_failed && results.tables_failed.length > 0 ? `
                <div>
                    <h3 class="mb-md text-error">Failed Tables</h3>
                    <div class="table-container">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>Table</th>
                                    <th>Error</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${results.tables_failed.map(table => `
                                    <tr>
                                        <td>${table.table}</td>
                                        <td class="text-error">${table.error || 'Unknown error'}</td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            ` : ''}
            
            ${results.errors && results.errors.length > 0 ? `
                <div class="mt-lg">
                    <h3 class="mb-md text-error">Errors</h3>
                    <ul>
                        ${results.errors.map(error => `<li class="text-error">${error}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        `;
        
        document.getElementById('resultsContainer').innerHTML = resultsHTML;
    }
    
    // Configuration
    const configHTML = `
        <div class="mb-lg">
            <h3 class="mb-md">Source Configuration</h3>
            <div class="table-container">
                <table class="table">
                    <tbody>
                        <tr>
                            <th>Type</th>
                            <td>${op.config_data?.source_type || 'N/A'}</td>
                        </tr>
                        ${op.config_data?.source ? Object.entries(op.config_data.source).map(([key, value]) => `
                            <tr>
                                <th>${key.charAt(0).toUpperCase() + key.slice(1)}</th>
                                <td>${key === 'password' ? '••••••••' : value}</td>
                            </tr>
                        `).join('') : ''}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div>
            <h3 class="mb-md">Destination Configuration</h3>
            <div class="table-container">
                <table class="table">
                    <tbody>
                        <tr>
                            <th>Type</th>
                            <td>${op.config_data?.dest_type || 'N/A'}</td>
                        </tr>
                        ${op.config_data?.destination ? Object.entries(op.config_data.destination).map(([key, value]) => `
                            <tr>
                                <th>${key.charAt(0).toUpperCase() + key.slice(1)}</th>
                                <td>${key === 'password' ? '••••••••' : value}</td>
                            </tr>
                        `).join('') : ''}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    document.getElementById('configContainer').innerHTML = configHTML;
    
    // Error message
    if (op.error_message) {
        document.getElementById('errorCard').style.display = 'block';
        document.getElementById('errorMessage').textContent = op.error_message;
    }
}

async function executeOperation(id) {
    if (!confirm('Are you sure you want to execute this operation now?')) {
        return;
    }
    
    try {
        showInfo('Executing operation...');
        await operationsAPI.execute(id, true);
        showSuccess('Operation execution started');
        await loadOperation(id);
    } catch (error) {
        showError(error.message || 'Failed to execute operation');
    }
}

async function retryOperation(id) {
    if (!confirm('Are you sure you want to retry this migration? Existing tables will be skipped and only new/missing data will be migrated.')) {
        return;
    }
    
    try {
        showInfo('Retrying migration... This will continue from where it left off, skipping already migrated tables.');
        await operationsAPI.retry(id);
        showSuccess('Migration retry started. The system will skip existing tables and continue with remaining tables.');
        // Reload operation to show updated status
        await loadOperation(id);
        // Start polling if operation is now running
        if (operation && operation.status === 'running') {
            startPolling(id);
        }
    } catch (error) {
        showError(error.message || 'Failed to retry operation');
    }
}

async function deleteOperation(id, status) {
    // Get current operation status if not provided
    if (!status && operation) {
        status = operation.status;
    }
    
    // Special warning for running operations
    let confirmMessage;
    if (status === 'running') {
        confirmMessage = `Are you sure you want to stop and delete running operation #${id}?\n\n` +
                        `⚠️ WARNING: The migration will be stopped.\n` +
                        `✅ Any tables and data already migrated to ClickHouse will be preserved.\n` +
                        `The operation record will be deleted from the system.`;
    } else {
        confirmMessage = `Are you sure you want to delete operation #${id}?`;
    }
    
    if (!confirm(confirmMessage)) {
        return;
    }
    
    try {
        // Stop polling if running
        if (status === 'running') {
            stopPolling();
        }
        
        showInfo(status === 'running' ? 'Stopping migration and deleting operation...' : 'Deleting operation...');
        await operationsAPI.delete(id);
        showSuccess(status === 'running' 
            ? 'Operation deleted. Migration stopped. Any data already migrated has been preserved in ClickHouse.'
            : 'Operation deleted successfully');
        // Redirect to operations list
        setTimeout(() => {
            window.location.href = 'operations.html';
        }, 1500);
    } catch (error) {
        showError(error.message || 'Failed to delete operation');
    }
}

function startPolling(id) {
    stopPolling();
    pollingInterval = setInterval(async () => {
        await loadOperation(id);
    }, API_CONFIG.POLLING_INTERVAL);
}

function stopPolling() {
    if (pollingInterval) {
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
}

// Make functions globally accessible
window.executeOperation = executeOperation;
window.retryOperation = retryOperation;
window.deleteOperation = deleteOperation;

// Cleanup
window.addEventListener('beforeunload', () => {
    stopPolling();
});

