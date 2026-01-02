// Data Table Component

function createDataTable(columns, data, actions = null) {
    if (!data || data.length === 0) {
        return '<div class="empty-state">No data available</div>';
    }
    
    const tableHTML = `
        <div class="table-container">
            <table class="table">
                <thead>
                    <tr>
                        ${columns.map(col => `<th>${col.label}</th>`).join('')}
                        ${actions ? '<th>Actions</th>' : ''}
                    </tr>
                </thead>
                <tbody>
                    ${data.map((row, index) => `
                        <tr>
                            ${columns.map(col => {
                                const value = col.render ? col.render(row[col.key], row) : row[col.key] || 'N/A';
                                return `<td>${value}</td>`;
                            }).join('')}
                            ${actions ? `<td>${actions(row, index)}</td>` : ''}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
    
    return tableHTML;
}

function renderDataTable(containerId, columns, data, actions = null) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = createDataTable(columns, data, actions);
}

