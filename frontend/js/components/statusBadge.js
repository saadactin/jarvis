// Status Badge Component

function createStatusBadge(status) {
    // Map status to CSS class (handle special cases)
    let statusClass = `badge-${status}`;
    if (status === 'not_found') {
        statusClass = 'badge-not_found';
    } else if (status === 'error') {
        statusClass = 'badge-error';
    }
    
    const label = getStatusLabel(status);
    
    return `<span class="badge ${statusClass}">${label}</span>`;
}

function getStatusIcon(status) {
    const icons = {
        pending: '⏳',
        running: '🔄',
        completed: '✅',
        failed: '❌',
        cancelled: '⏹️'
    };
    return icons[status] || '❓';
}

function createStatusBadgeWithIcon(status) {
    const statusClass = `badge-${status}`;
    const label = getStatusLabel(status);
    const icon = getStatusIcon(status);
    
    return `<span class="badge ${statusClass}">${icon} ${label}</span>`;
}

