// Operations Page Logic

let operations = [];
let filteredOperations = [];
let pollingInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadOperations();
    
    // Setup filters
    setupFilters();
    
    // Poll for running operations
    startPolling();
});

function setupFilters() {
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('typeFilter');
    const searchInput = document.getElementById('searchInput');
    const clearFilters = document.getElementById('clearFilters');
    
    const applyFilters = debounce(() => {
        filterOperations();
    }, 300);
    
    if (statusFilter) {
        statusFilter.addEventListener('change', applyFilters);
    }
    
    if (typeFilter) {
        typeFilter.addEventListener('change', applyFilters);
    }
    
    if (searchInput) {
        searchInput.addEventListener('input', applyFilters);
    }
    
    if (clearFilters) {
        clearFilters.addEventListener('click', () => {
            if (statusFilter) statusFilter.value = '';
            if (typeFilter) typeFilter.value = '';
            if (searchInput) searchInput.value = '';
            filterOperations();
        });
    }
}

function filterOperations() {
    const statusFilter = document.getElementById('statusFilter')?.value;
    const typeFilter = document.getElementById('typeFilter')?.value;
    const searchInput = document.getElementById('searchInput')?.value.toLowerCase();
    
    filteredOperations = operations.filter(op => {
        const matchStatus = !statusFilter || op.status === statusFilter;
        const matchType = !typeFilter || op.operation_type === typeFilter;
        const matchSearch = !searchInput || 
            op.id.toString().includes(searchInput) ||
            (op.source_name && op.source_name.toLowerCase().includes(searchInput)) ||
            (op.config_data?.source_type && op.config_data.source_type.toLowerCase().includes(searchInput)) ||
            (op.config_data?.dest_type && op.config_data.dest_type.toLowerCase().includes(searchInput));
        
        return matchStatus && matchType && matchSearch;
    });
    
    renderOperations();
}

async function loadOperations() {
    const container = document.getElementById('operationsContainer');
    if (container) {
        showLoading(container);
    }
    
    try {
        const response = await operationsAPI.getAll();
        operations = response.operations || [];
        filteredOperations = [...operations];
        renderOperations();
    } catch (error) {
        console.error('Error loading operations:', error);
        showError('Failed to load operations');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error Loading Operations</div>
                    <div class="empty-state-text">${error.message}</div>
                    <button onclick="loadOperations()" class="btn btn-primary mt-md">Retry</button>
                </div>
            `;
        }
    }
}

function renderOperations() {
    const container = document.getElementById('operationsContainer');
    if (!container) return;
    
    if (filteredOperations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-title">No Operations Found</div>
                <div class="empty-state-text">Try adjusting your filters or create a new operation.</div>
                <a href="create-operation.html" class="btn btn-primary mt-md">Create Operation</a>
            </div>
        `;
        return;
    }
    
    const tableHTML = `
        <div class="table-container">
            <table class="table">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Source</th>
                        <th>Destination</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Schedule</th>
                        <th>Created</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${filteredOperations.map(op => {
                        const sourceType = op.config_data?.source_type || 'N/A';
                        const destType = op.config_data?.dest_type || 'N/A';
                        return `
                            <tr>
                                <td>#${op.id}</td>
                                <td>${sourceType}</td>
                                <td>${destType}</td>
                                <td>${op.operation_type || 'N/A'}</td>
                                <td>${createStatusBadge(op.status)}</td>
                                <td>${formatDate(op.schedule)}</td>
                                <td>${formatDate(op.created_at)}</td>
                                <td>
                                    <div class="d-flex gap-sm">
                                        <a href="operation-detail.html?id=${op.id}" class="btn btn-outline btn-sm">View</a>
                                        ${op.status === 'pending' ? `
                                            <button onclick="executeOperation(${op.id})" class="btn btn-success btn-sm">Execute</button>
                                        ` : ''}
                                        <button onclick="deleteOperation(${op.id}, '${op.status}')" class="btn btn-danger btn-sm">Delete</button>
                                    </div>
                                </td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    container.innerHTML = tableHTML;
    hideLoading(container);
}

async function executeOperation(id) {
    if (!confirm('Are you sure you want to execute this operation now?')) {
        return;
    }
    
    try {
        showInfo('Executing operation...');
        await operationsAPI.execute(id, true);
        showSuccess('Operation execution started');
        await loadOperations();
    } catch (error) {
        showError(error.message || 'Failed to execute operation');
    }
}

async function deleteOperation(id, status) {
    const operation = operations.find(op => op.id === id);
    if (!operation) return;
    
    // Special warning for running operations
    let confirmMessage;
    if (status === 'running') {
        confirmMessage = `Are you sure you want to delete running operation #${id}?\n\n` +
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
        showInfo(status === 'running' ? 'Stopping migration and deleting operation...' : 'Deleting operation...');
        await operationsAPI.delete(id);
        showSuccess(status === 'running' 
            ? 'Operation deleted. Migration stopped. Any data already migrated has been preserved in ClickHouse.'
            : 'Operation deleted successfully');
        await loadOperations();
    } catch (error) {
        showError(error.message || 'Failed to delete operation');
    }
}

function startPolling() {
    // Poll for running operations every 5 seconds
    pollingInterval = setInterval(() => {
        const hasRunning = operations.some(op => op.status === 'running');
        if (hasRunning) {
            loadOperations();
        }
    }, API_CONFIG.POLLING_INTERVAL);
}

// Make functions globally accessible
window.executeOperation = executeOperation;
window.deleteOperation = deleteOperation;
window.loadOperations = loadOperations;

// Cleanup
window.addEventListener('beforeunload', () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});

