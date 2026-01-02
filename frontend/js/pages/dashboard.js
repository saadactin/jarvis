// Dashboard Page Logic

let pollingInterval = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboard();
    
    // Poll for updates every 10 seconds
    pollingInterval = setInterval(loadDashboard, 10000);
});

async function loadDashboard() {
    try {
        // Load summary
        const summary = await operationsAPI.getSummary();
        renderStatsCards('statsContainer', summary);
        
        // Load recent operations
        await loadRecentOperations(summary.recent_operations || []);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showError('Failed to load dashboard data');
    }
}

function loadRecentOperations(operations) {
    const container = document.getElementById('recentOperationsContainer');
    if (!container) return;
    
    if (!operations || operations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📋</div>
                <div class="empty-state-title">No Operations Yet</div>
                <div class="empty-state-text">Create your first migration operation to get started.</div>
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
                        <th>Type</th>
                        <th>Status</th>
                        <th>Created</th>
                        <th>Completed</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
                    ${operations.map(op => `
                        <tr>
                            <td>#${op.id}</td>
                            <td>${op.source_name || 'N/A'}</td>
                            <td>${op.operation_type || 'N/A'}</td>
                            <td>${createStatusBadge(op.status)}</td>
                            <td>${formatDate(op.created_at)}</td>
                            <td>${op.completed_at ? formatDate(op.completed_at) : '-'}</td>
                            <td>
                                <a href="operation-detail.html?id=${op.id}" class="btn btn-outline btn-sm">View</a>
                            </td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    container.innerHTML = tableHTML;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (pollingInterval) {
        clearInterval(pollingInterval);
    }
});

