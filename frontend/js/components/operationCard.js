// Operation Card Component

function createOperationCard(operation) {
    const sourceType = operation.config_data?.source_type || 'N/A';
    const destType = operation.config_data?.dest_type || 'N/A';
    
    return `
        <div class="card">
            <div class="card-header">
                <div>
                    <h3 class="card-title">Operation #${operation.id}</h3>
                    <div class="text-secondary text-sm">${sourceType} → ${destType}</div>
                </div>
                ${createStatusBadge(operation.status)}
            </div>
            <div class="card-body">
                <div class="mb-sm">
                    <span class="text-secondary">Type: </span>
                    <span>${operation.operation_type || 'N/A'}</span>
                </div>
                <div class="mb-sm">
                    <span class="text-secondary">Scheduled: </span>
                    <span>${formatDate(operation.schedule)}</span>
                </div>
                <div>
                    <span class="text-secondary">Created: </span>
                    <span>${formatDate(operation.created_at)}</span>
                </div>
            </div>
            <div class="card-footer">
                <a href="operation-detail.html?id=${operation.id}" class="btn btn-outline btn-sm">View</a>
                ${operation.status === 'pending' ? `
                    <button onclick="executeOperation(${operation.id})" class="btn btn-success btn-sm">Execute</button>
                ` : ''}
                ${operation.status !== 'running' ? `
                    <button onclick="deleteOperation(${operation.id})" class="btn btn-danger btn-sm">Delete</button>
                ` : ''}
            </div>
        </div>
    `;
}

function renderOperationCards(containerId, operations) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    if (!operations || operations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-title">No Operations</div>
                <div class="empty-state-text">Create your first operation to get started.</div>
            </div>
        `;
        return;
    }
    
    const cardsHTML = operations.map(op => createOperationCard(op)).join('');
    container.innerHTML = `<div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-lg);">${cardsHTML}</div>`;
}

