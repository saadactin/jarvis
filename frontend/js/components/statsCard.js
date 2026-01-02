// Stats Card Component

function createStatsCard(icon, value, label, color = 'primary') {
    return `
        <div class="stats-card">
            <div class="stats-card-icon">${icon}</div>
            <div class="stats-card-value" style="color: var(--${color})">${value}</div>
            <div class="stats-card-label">${label}</div>
        </div>
    `;
}

function renderStatsCards(containerId, stats) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const cards = [
        createStatsCard('📊', stats.total_operations || 0, 'Total Operations', 'primary'),
        createStatsCard('⏳', stats.by_status?.pending || 0, 'Pending', 'info'),
        createStatsCard('🔄', stats.by_status?.running || 0, 'Running', 'info'),
        createStatsCard('✅', stats.by_status?.completed || 0, 'Completed', 'success'),
        createStatsCard('❌', stats.by_status?.failed || 0, 'Failed', 'error')
    ];
    
    container.innerHTML = `
        <div class="stats-grid">
            ${cards.join('')}
        </div>
    `;
}

