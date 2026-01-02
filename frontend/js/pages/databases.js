// Databases Page Logic

let databases = [];
let editingId = null;

document.addEventListener('DOMContentLoaded', async () => {
    await loadDatabases();
});

async function loadDatabases() {
    const container = document.getElementById('databasesContainer');
    if (container) {
        showLoading(container);
    }
    
    try {
        const response = await databaseMasterAPI.getAll();
        databases = response.databases || [];
        renderDatabases();
    } catch (error) {
        console.error('Error loading databases:', error);
        showError('Failed to load database masters');
        if (container) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-title">Error Loading Database Masters</div>
                    <div class="empty-state-text">${error.message}</div>
                    <button onclick="loadDatabases()" class="btn btn-primary mt-md">Retry</button>
                </div>
            `;
        }
    }
}

function renderDatabases() {
    const container = document.getElementById('databasesContainer');
    if (!container) return;
    
    if (databases.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🗄️</div>
                <div class="empty-state-title">No Database Masters</div>
                <div class="empty-state-text">Register a database master (microservice) to get started.</div>
                <button onclick="showAddDatabaseModal()" class="btn btn-primary mt-md">Add Database Master</button>
            </div>
        `;
        return;
    }
    
    const cardsHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: var(--spacing-lg);">
            ${databases.map(db => `
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">${db.name}</h3>
                    </div>
                    <div class="card-body">
                        <div class="mb-md">
                            <div class="text-secondary text-sm">Service URL</div>
                            <div class="text-md">${db.service_url}</div>
                        </div>
                        <div class="mb-md">
                            <div class="text-secondary text-sm">Created</div>
                            <div class="text-sm">${formatDate(db.created_at)}</div>
                        </div>
                    </div>
                    <div class="card-footer">
                        <button onclick="editDatabase(${db.id})" class="btn btn-outline btn-sm">Edit</button>
                        <button onclick="deleteDatabase(${db.id})" class="btn btn-danger btn-sm">Delete</button>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    container.innerHTML = cardsHTML;
    hideLoading(container);
}

function showAddDatabaseModal() {
    editingId = null;
    document.getElementById('modalTitle').textContent = 'Add Database Master';
    document.getElementById('databaseForm').reset();
    document.getElementById('databaseId').value = '';
    document.getElementById('databaseModal').classList.remove('hidden');
}

function closeDatabaseModal() {
    const modal = document.getElementById('databaseModal');
    if (modal) {
        modal.classList.add('hidden');
    }
    editingId = null;
    const form = document.getElementById('databaseForm');
    if (form) {
        form.reset();
    }
}

// Make functions globally accessible
window.showAddDatabaseModal = showAddDatabaseModal;
window.closeDatabaseModal = closeDatabaseModal;
window.editDatabase = editDatabase;
window.deleteDatabase = deleteDatabase;
window.saveDatabase = saveDatabase;
window.loadDatabases = loadDatabases;

function editDatabase(id) {
    const database = databases.find(db => db.id === id);
    if (!database) return;
    
    editingId = id;
    document.getElementById('modalTitle').textContent = 'Edit Database Master';
    document.getElementById('databaseId').value = id;
    document.getElementById('databaseName').value = database.name;
    document.getElementById('databaseUrl').value = database.service_url;
    document.getElementById('databaseModal').classList.remove('hidden');
}

async function saveDatabase() {
    const name = document.getElementById('databaseName').value.trim();
    const url = document.getElementById('databaseUrl').value.trim();
    
    // Clear errors
    document.getElementById('databaseNameError').textContent = '';
    document.getElementById('databaseUrlError').textContent = '';
    
    // Validation
    let hasError = false;
    
    if (!name) {
        document.getElementById('databaseNameError').textContent = 'Name is required';
        hasError = true;
    }
    
    if (!url) {
        document.getElementById('databaseUrlError').textContent = 'Service URL is required';
        hasError = true;
    } else if (!url.startsWith('http://') && !url.startsWith('https://')) {
        document.getElementById('databaseUrlError').textContent = 'URL must start with http:// or https://';
        hasError = true;
    }
    
    if (hasError) return;
    
    const saveButton = document.querySelector('#databaseModal .btn-primary');
    saveButton.disabled = true;
    saveButton.textContent = 'Saving...';
    
    try {
        const data = {
            name: name,
            service_url: url
        };
        
        if (editingId) {
            await databaseMasterAPI.update(editingId, data);
            showSuccess('Database master updated successfully');
        } else {
            await databaseMasterAPI.create(data);
            showSuccess('Database master created successfully');
        }
        
        closeDatabaseModal();
        await loadDatabases();
        
    } catch (error) {
        console.error('Error saving database:', error);
        showError(error.message || 'Failed to save database master');
    } finally {
        saveButton.disabled = false;
        saveButton.textContent = 'Save';
    }
}

async function deleteDatabase(id) {
    const database = databases.find(db => db.id === id);
    if (!database) return;
    
    if (!confirm(`Are you sure you want to delete "${database.name}"?`)) {
        return;
    }
    
    try {
        await databaseMasterAPI.delete(id);
        showSuccess('Database master deleted successfully');
        await loadDatabases();
    } catch (error) {
        showError(error.message || 'Failed to delete database master');
    }
}

