// Create Operation Wizard Logic

let currentStep = 1;
const totalSteps = 6;
let formData = {
    source_type: null,
    dest_type: null,
    source: {},
    destination: {},
    operation_type: null,
    schedule: null,
    last_sync_time: null
};

// Get database masters for source_id
let databaseMasters = [];

document.addEventListener('DOMContentLoaded', async () => {
    await loadDatabaseMasters();
    initializeWizard();
    setupEventListeners();
});

async function loadDatabaseMasters() {
    try {
        const response = await databaseMasterAPI.getAll();
        databaseMasters = response.databases || [];
        
        // If no database masters, show warning
        if (databaseMasters.length === 0) {
            showInfo('Please register a database master (Universal Migration Service) first');
        }
    } catch (error) {
        console.error('Error loading database masters:', error);
    }
}

function initializeWizard() {
    renderSourceSelection();
    renderDestinationSelection();
    updateWizardProgress();
}

function setupEventListeners() {
    const operationTypeSelect = document.getElementById('operationType');
    if (operationTypeSelect) {
        operationTypeSelect.addEventListener('change', (e) => {
            const lastSyncTimeGroup = document.getElementById('lastSyncTimeGroup');
            if (e.target.value === 'incremental') {
                lastSyncTimeGroup.style.display = 'block';
            } else {
                lastSyncTimeGroup.style.display = 'none';
            }
        });
    }
    
    const form = document.getElementById('operationForm');
    if (form) {
        form.addEventListener('submit', handleSubmit);
    }
}

function renderSourceSelection() {
    const container = document.getElementById('sourceSelection');
    if (!container) return;
    
    const optionsHTML = SOURCE_TYPES.map(source => `
        <div class="source-option" data-value="${source.value}" onclick="selectSource('${source.value}')">
            <div class="source-option-icon">${source.icon}</div>
            <div class="source-option-label">${source.label}</div>
        </div>
    `).join('');
    
    container.innerHTML = optionsHTML;
    
    // Mark selected if exists
    if (formData.source_type) {
        const selected = container.querySelector(`[data-value="${formData.source_type}"]`);
        if (selected) selected.classList.add('selected');
    }
}

function renderDestinationSelection() {
    const container = document.getElementById('destinationSelection');
    if (!container) return;
    
    const optionsHTML = DESTINATION_TYPES.map(dest => `
        <div class="destination-option" data-value="${dest.value}" onclick="selectDestination('${dest.value}')">
            <div class="destination-option-icon">${dest.icon}</div>
            <div class="destination-option-label">${dest.label}</div>
        </div>
    `).join('');
    
    container.innerHTML = optionsHTML;
    
    // Mark selected if exists
    if (formData.dest_type) {
        const selected = container.querySelector(`[data-value="${formData.dest_type}"]`);
        if (selected) selected.classList.add('selected');
    }
}

function selectSource(sourceType) {
    formData.source_type = sourceType;
    
    // Remove previous selection
    document.querySelectorAll('.source-option').forEach(opt => opt.classList.remove('selected'));
    
    // Mark new selection
    const selected = document.querySelector(`.source-option[data-value="${sourceType}"]`);
    if (selected) selected.classList.add('selected');
    
    // Clear source config
    formData.source = {};
    
    // Clear error
    document.getElementById('sourceError').textContent = '';
}

function selectDestination(destType) {
    // Validate: source and destination cannot be the same
    if (formData.source_type === destType) {
        showError('Source and destination cannot be the same. Please select a different destination.');
        return;
    }
    
    formData.dest_type = destType;
    
    // Remove previous selection
    document.querySelectorAll('.destination-option').forEach(opt => opt.classList.remove('selected'));
    
    // Mark new selection
    const selected = document.querySelector(`.destination-option[data-value="${destType}"]`);
    if (selected) selected.classList.add('selected');
    
    // Clear destination config
    formData.destination = {};
    
    // Clear error
    document.getElementById('destinationError').textContent = '';
}

function renderSourceConfig() {
    const container = document.getElementById('sourceConfigForm');
    if (!container || !formData.source_type) return;
    
    let formHTML = '';
    
    if (formData.source_type === 'zoho') {
        formHTML = `
            <div class="form-group">
                <label for="zohoRefreshToken" class="form-label required">Refresh Token</label>
                <input type="text" id="zohoRefreshToken" class="form-input" required>
                <span class="form-error" id="zohoRefreshTokenError"></span>
            </div>
            <div class="form-group">
                <label for="zohoClientId" class="form-label required">Client ID</label>
                <input type="text" id="zohoClientId" class="form-input" required>
                <span class="form-error" id="zohoClientIdError"></span>
            </div>
            <div class="form-group">
                <label for="zohoClientSecret" class="form-label required">Client Secret</label>
                <input type="password" id="zohoClientSecret" class="form-input" required>
                <span class="form-error" id="zohoClientSecretError"></span>
            </div>
            <div class="form-group">
                <label for="zohoApiDomain" class="form-label required">API Domain</label>
                <select id="zohoApiDomain" class="form-select" required>
                    <option value="https://www.zohoapis.com">US (https://www.zohoapis.com)</option>
                    <option value="https://www.zohoapis.in">India (https://www.zohoapis.in)</option>
                    <option value="https://www.zohoapis.eu">Europe (https://www.zohoapis.eu)</option>
                    <option value="https://www.zohoapis.com.au">Australia (https://www.zohoapis.com.au)</option>
                    <option value="https://www.zohoapis.jp">Japan (https://www.zohoapis.jp)</option>
                </select>
                <span class="form-error" id="zohoApiDomainError"></span>
            </div>
        `;
    } else if (formData.source_type === 'sqlserver') {
        formHTML = `
            <div class="form-group">
                <label for="sqlServer" class="form-label required">Server</label>
                <input type="text" id="sqlServer" class="form-input" placeholder="localhost\\SQLEXPRESS" required>
                <span class="form-help">Use format: hostname\\instancename or hostname</span>
                <span class="form-error" id="sqlServerError"></span>
            </div>
            <div class="form-group">
                <label for="sqlDatabase" class="form-label required">Database</label>
                <input type="text" id="sqlDatabase" class="form-input" required>
                <span class="form-error" id="sqlDatabaseError"></span>
            </div>
            <div class="form-group">
                <label for="sqlUsername" class="form-label">Username</label>
                <input type="text" id="sqlUsername" class="form-input" placeholder="Leave empty for Windows Auth">
                <span class="form-help">Leave empty for Windows Authentication</span>
                <span class="form-error" id="sqlUsernameError"></span>
            </div>
            <div class="form-group">
                <label for="sqlPassword" class="form-label">Password</label>
                <input type="password" id="sqlPassword" class="form-input" placeholder="Leave empty for Windows Auth">
                <span class="form-error" id="sqlPasswordError"></span>
            </div>
        `;
    } else if (formData.source_type === 'devops') {
        formHTML = `
            <div class="form-group">
                <label for="devopsAccessToken" class="form-label required">Access Token</label>
                <input type="password" id="devopsAccessToken" class="form-input" required>
                <span class="form-help">Azure DevOps Personal Access Token (PAT)</span>
                <span class="form-error" id="devopsAccessTokenError"></span>
            </div>
            <div class="form-group">
                <label for="devopsOrganization" class="form-label required">Organization</label>
                <input type="text" id="devopsOrganization" class="form-input" placeholder="TORAI" required>
                <span class="form-help">Your Azure DevOps organization name</span>
                <span class="form-error" id="devopsOrganizationError"></span>
            </div>
            <div class="form-group">
                <label for="devopsApiVersion" class="form-label required">API Version</label>
                <input type="text" id="devopsApiVersion" class="form-input" value="7.1" required>
                <span class="form-help">Azure DevOps API version (default: 7.1)</span>
                <span class="form-error" id="devopsApiVersionError"></span>
            </div>
        `;
    } else {
        // PostgreSQL or MySQL
        const defaultPort = formData.source_type === 'postgresql' ? 5432 : 3306;
        formHTML = `
            <div class="form-group">
                <label for="sourceHost" class="form-label required">Host</label>
                <input type="text" id="sourceHost" class="form-input" required>
                <span class="form-error" id="sourceHostError"></span>
            </div>
            <div class="form-group">
                <label for="sourcePort" class="form-label required">Port</label>
                <input type="number" id="sourcePort" class="form-input" value="${defaultPort}" required>
                <span class="form-error" id="sourcePortError"></span>
            </div>
            <div class="form-group">
                <label for="sourceDatabase" class="form-label required">Database</label>
                <input type="text" id="sourceDatabase" class="form-input" required>
                <span class="form-error" id="sourceDatabaseError"></span>
            </div>
            <div class="form-group">
                <label for="sourceUsername" class="form-label required">Username</label>
                <input type="text" id="sourceUsername" class="form-input" required>
                <span class="form-error" id="sourceUsernameError"></span>
            </div>
            <div class="form-group">
                <label for="sourcePassword" class="form-label required">Password</label>
                <input type="password" id="sourcePassword" class="form-input" required>
                <span class="form-error" id="sourcePasswordError"></span>
            </div>
        `;
    }
    
    container.innerHTML = formHTML;
    
    // Pre-fill if data exists
    if (formData.source && Object.keys(formData.source).length > 0) {
        if (formData.source_type === 'devops') {
            const accessTokenInput = document.getElementById('devopsAccessToken');
            const orgInput = document.getElementById('devopsOrganization');
            const apiVersionInput = document.getElementById('devopsApiVersion');
            if (accessTokenInput && formData.source.access_token) accessTokenInput.value = formData.source.access_token;
            if (orgInput && formData.source.organization) orgInput.value = formData.source.organization;
            if (apiVersionInput && formData.source.api_version) apiVersionInput.value = formData.source.api_version;
        } else {
            Object.keys(formData.source).forEach(key => {
                const input = document.getElementById(key.replace(/_/g, ''));
                if (input) input.value = formData.source[key];
            });
        }
    }
}

function renderDestinationConfig() {
    const container = document.getElementById('destinationConfigForm');
    if (!container || !formData.dest_type) return;
    
    let formHTML = '';
    
    if (formData.dest_type === 'clickhouse') {
        formHTML = `
            <div class="form-group">
                <label for="destHost" class="form-label required">Host</label>
                <input type="text" id="destHost" class="form-input" required>
                <span class="form-error" id="destHostError"></span>
            </div>
            <div class="form-group">
                <label for="destPort" class="form-label required">Port</label>
                <input type="number" id="destPort" class="form-input" value="8123" required>
                <span class="form-help">ClickHouse HTTP API port (default: 8123). If you specify 9000, it will automatically try 8123 first.</span>
                <span class="form-error" id="destPortError"></span>
            </div>
            <div class="form-group">
                <label for="destDatabase" class="form-label required">Database</label>
                <input type="text" id="destDatabase" class="form-input" required>
                <span class="form-error" id="destDatabaseError"></span>
            </div>
            <div class="form-group">
                <label for="destUsername" class="form-label required">Username</label>
                <input type="text" id="destUsername" class="form-input" value="default" required>
                <span class="form-error" id="destUsernameError"></span>
            </div>
            <div class="form-group">
                <label for="destPassword" class="form-label required">Password</label>
                <input type="password" id="destPassword" class="form-input" required>
                <span class="form-error" id="destPasswordError"></span>
            </div>
        `;
    } else {
        // PostgreSQL or MySQL
        const defaultPort = formData.dest_type === 'postgresql' ? 5432 : 3306;
        formHTML = `
            <div class="form-group">
                <label for="destHost" class="form-label required">Host</label>
                <input type="text" id="destHost" class="form-input" required>
                <span class="form-error" id="destHostError"></span>
            </div>
            <div class="form-group">
                <label for="destPort" class="form-label required">Port</label>
                <input type="number" id="destPort" class="form-input" value="${defaultPort}" required>
                <span class="form-error" id="destPortError"></span>
            </div>
            <div class="form-group">
                <label for="destDatabase" class="form-label required">Database</label>
                <input type="text" id="destDatabase" class="form-input" required>
                <span class="form-error" id="destDatabaseError"></span>
            </div>
            <div class="form-group">
                <label for="destUsername" class="form-label required">Username</label>
                <input type="text" id="destUsername" class="form-input" required>
                <span class="form-error" id="destUsernameError"></span>
            </div>
            <div class="form-group">
                <label for="destPassword" class="form-label required">Password</label>
                <input type="password" id="destPassword" class="form-input" required>
                <span class="form-error" id="destPasswordError"></span>
            </div>
        `;
    }
    
    container.innerHTML = formHTML;
    
    // Pre-fill if data exists
    if (formData.destination && Object.keys(formData.destination).length > 0) {
        Object.keys(formData.destination).forEach(key => {
            const input = document.getElementById(`dest${key.charAt(0).toUpperCase() + key.slice(1)}`);
            if (input) input.value = formData.destination[key];
        });
    }
}

function updateWizardProgress() {
    // Update step indicators
    for (let i = 1; i <= totalSteps; i++) {
        const step = document.querySelector(`.wizard-step[data-step="${i}"]`);
        if (step) {
            step.classList.remove('active', 'completed');
            if (i < currentStep) {
                step.classList.add('completed');
            } else if (i === currentStep) {
                step.classList.add('active');
            }
        }
    }
    
    // Show/hide steps
    for (let i = 1; i <= totalSteps; i++) {
        const stepContent = document.getElementById(`step${i}`);
        if (stepContent) {
            if (i === currentStep) {
                stepContent.classList.remove('hidden');
            } else {
                stepContent.classList.add('hidden');
            }
        }
    }
    
    // Update navigation buttons
    const prevButton = document.getElementById('prevButton');
    const nextButton = document.getElementById('nextButton');
    const submitButton = document.getElementById('submitButton');
    
    if (prevButton) {
        prevButton.style.display = currentStep > 1 ? 'block' : 'none';
    }
    
    if (nextButton) {
        nextButton.style.display = currentStep < totalSteps ? 'block' : 'none';
    }
    
    if (submitButton) {
        submitButton.classList.toggle('hidden', currentStep !== totalSteps);
    }
}

function validateStep(step) {
    switch(step) {
        case 1:
            if (!formData.source_type) {
                document.getElementById('sourceError').textContent = 'Please select a source';
                return false;
            }
            return true;
            
        case 2:
            if (!formData.dest_type) {
                document.getElementById('destinationError').textContent = 'Please select a destination';
                return false;
            }
            if (formData.source_type === formData.dest_type) {
                document.getElementById('destinationError').textContent = 'Source and destination cannot be the same';
                return false;
            }
            return true;
            
        case 3:
            return validateSourceConfig();
            
        case 4:
            return validateDestinationConfig();
            
        case 5:
            return validateSchedule();
            
        case 6:
            return true; // Review step, no validation needed
            
        default:
            return true;
    }
}

function validateSourceConfig() {
    let isValid = true;
    
    if (formData.source_type === 'zoho') {
        const refreshToken = document.getElementById('zohoRefreshToken')?.value.trim();
        const clientId = document.getElementById('zohoClientId')?.value.trim();
        const clientSecret = document.getElementById('zohoClientSecret')?.value.trim();
        const apiDomain = document.getElementById('zohoApiDomain')?.value;
        
        if (!refreshToken) {
            document.getElementById('zohoRefreshTokenError').textContent = 'Refresh token is required';
            isValid = false;
        }
        if (!clientId) {
            document.getElementById('zohoClientIdError').textContent = 'Client ID is required';
            isValid = false;
        }
        if (!clientSecret) {
            document.getElementById('zohoClientSecretError').textContent = 'Client secret is required';
            isValid = false;
        }
        if (!apiDomain) {
            document.getElementById('zohoApiDomainError').textContent = 'API domain is required';
            isValid = false;
        }
        
        if (isValid) {
            formData.source = {
                refresh_token: refreshToken,
                client_id: clientId,
                client_secret: clientSecret,
                api_domain: apiDomain
            };
        }
    } else if (formData.source_type === 'sqlserver') {
        const server = document.getElementById('sqlServer')?.value.trim();
        const database = document.getElementById('sqlDatabase')?.value.trim();
        const username = document.getElementById('sqlUsername')?.value.trim();
        const password = document.getElementById('sqlPassword')?.value;
        
        if (!server) {
            document.getElementById('sqlServerError').textContent = 'Server is required';
            isValid = false;
        }
        if (!database) {
            document.getElementById('sqlDatabaseError').textContent = 'Database is required';
            isValid = false;
        }
        
        if (isValid) {
            formData.source = {
                server: server,
                database: database
            };
            if (username) formData.source.username = username;
            if (password) formData.source.password = password;
        }
    } else if (formData.source_type === 'devops') {
        const accessToken = document.getElementById('devopsAccessToken')?.value.trim();
        const organization = document.getElementById('devopsOrganization')?.value.trim();
        const apiVersion = document.getElementById('devopsApiVersion')?.value.trim() || '7.1';
        
        if (!accessToken) {
            document.getElementById('devopsAccessTokenError').textContent = 'Access token is required';
            isValid = false;
        }
        if (!organization) {
            document.getElementById('devopsOrganizationError').textContent = 'Organization is required';
            isValid = false;
        }
        if (!apiVersion) {
            document.getElementById('devopsApiVersionError').textContent = 'API version is required';
            isValid = false;
        }
        
        if (isValid) {
            formData.source = {
                access_token: accessToken,
                organization: organization,
                api_version: apiVersion
            };
        }
    } else {
        // PostgreSQL or MySQL
        const host = document.getElementById('sourceHost')?.value.trim();
        const port = document.getElementById('sourcePort')?.value;
        const database = document.getElementById('sourceDatabase')?.value.trim();
        const username = document.getElementById('sourceUsername')?.value.trim();
        const password = document.getElementById('sourcePassword')?.value;
        
        if (!host) {
            document.getElementById('sourceHostError').textContent = 'Host is required';
            isValid = false;
        }
        if (!port) {
            document.getElementById('sourcePortError').textContent = 'Port is required';
            isValid = false;
        }
        if (!database) {
            document.getElementById('sourceDatabaseError').textContent = 'Database is required';
            isValid = false;
        }
        if (!username) {
            document.getElementById('sourceUsernameError').textContent = 'Username is required';
            isValid = false;
        }
        if (!password) {
            document.getElementById('sourcePasswordError').textContent = 'Password is required';
            isValid = false;
        }
        
        if (isValid) {
            formData.source = {
                host: host,
                port: parseInt(port),
                database: database,
                username: username,
                password: password
            };
        }
    }
    
    return isValid;
}

function validateDestinationConfig() {
    let isValid = true;
    
    const host = document.getElementById('destHost')?.value.trim();
    const port = document.getElementById('destPort')?.value;
    const database = document.getElementById('destDatabase')?.value.trim();
    const username = document.getElementById('destUsername')?.value.trim();
    const password = document.getElementById('destPassword')?.value;
    
    if (!host) {
        document.getElementById('destHostError').textContent = 'Host is required';
        isValid = false;
    }
    if (!port) {
        document.getElementById('destPortError').textContent = 'Port is required';
        isValid = false;
    }
    if (!database) {
        document.getElementById('destDatabaseError').textContent = 'Database is required';
        isValid = false;
    }
    if (!username) {
        document.getElementById('destUsernameError').textContent = 'Username is required';
        isValid = false;
    }
    if (!password) {
        document.getElementById('destPasswordError').textContent = 'Password is required';
        isValid = false;
    }
    
    if (isValid) {
        formData.destination = {
            host: host,
            port: parseInt(port),
            database: database,
            username: username,
            password: password
        };
    }
    
    return isValid;
}

function validateSchedule() {
    let isValid = true;
    
    const operationType = document.getElementById('operationType')?.value;
    const scheduleDate = document.getElementById('scheduleDate')?.value;
    const scheduleTime = document.getElementById('scheduleTime')?.value;
    const lastSyncTime = document.getElementById('lastSyncTime')?.value;
    
    if (!operationType) {
        document.getElementById('operationTypeError').textContent = 'Operation type is required';
        isValid = false;
    }
    if (!scheduleDate) {
        document.getElementById('scheduleDateError').textContent = 'Schedule date is required';
        isValid = false;
    }
    if (!scheduleTime) {
        document.getElementById('scheduleTimeError').textContent = 'Schedule time is required';
        isValid = false;
    }
    
    if (isValid) {
        formData.operation_type = operationType;
        
        // Combine date and time, assume IST if not specified
        const scheduleDateTime = `${scheduleDate}T${scheduleTime}`;
        const schedule = new Date(scheduleDateTime);
        
        // Add IST offset (UTC+5:30)
        const istOffset = 5.5 * 60 * 60 * 1000;
        const utcSchedule = new Date(schedule.getTime() - istOffset);
        
        formData.schedule = formatDateISO(utcSchedule);
        
        if (operationType === 'incremental' && lastSyncTime) {
            formData.last_sync_time = lastSyncTime;
        }
    }
    
    return isValid;
}

function nextStep() {
    if (!validateStep(currentStep)) {
        return;
    }
    
    if (currentStep === 2) {
        renderSourceConfig();
    } else if (currentStep === 3) {
        renderDestinationConfig();
    } else if (currentStep === 5) {
        renderReview();
    }
    
    if (currentStep < totalSteps) {
        currentStep++;
        updateWizardProgress();
    }
}

function previousStep() {
    if (currentStep > 1) {
        currentStep--;
        updateWizardProgress();
    }
}

function renderReview() {
    const container = document.getElementById('reviewContent');
    if (!container) return;
    
    const reviewHTML = `
        <div class="mb-lg">
            <h3 class="mb-md">Source</h3>
            <div class="table-container">
                <table class="table">
                    <tbody>
                        <tr>
                            <th>Type</th>
                            <td>${formData.source_type}</td>
                        </tr>
                        ${Object.entries(formData.source).map(([key, value]) => `
                            <tr>
                                <th>${key.charAt(0).toUpperCase() + key.slice(1).replace(/_/g, ' ')}</th>
                                <td>${key.includes('password') || key.includes('secret') ? '••••••••' : value}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div class="mb-lg">
            <h3 class="mb-md">Destination</h3>
            <div class="table-container">
                <table class="table">
                    <tbody>
                        <tr>
                            <th>Type</th>
                            <td>${formData.dest_type}</td>
                        </tr>
                        ${Object.entries(formData.destination).map(([key, value]) => `
                            <tr>
                                <th>${key.charAt(0).toUpperCase() + key.slice(1)}</th>
                                <td>${key.includes('password') ? '••••••••' : value}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
        
        <div>
            <h3 class="mb-md">Schedule</h3>
            <div class="table-container">
                <table class="table">
                    <tbody>
                        <tr>
                            <th>Operation Type</th>
                            <td>${formData.operation_type}</td>
                        </tr>
                        <tr>
                            <th>Schedule</th>
                            <td>${formatDate(formData.schedule)}</td>
                        </tr>
                        ${formData.last_sync_time ? `
                            <tr>
                                <th>Last Sync Time</th>
                                <td>${formatDate(formData.last_sync_time)}</td>
                            </tr>
                        ` : ''}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    container.innerHTML = reviewHTML;
}

async function handleSubmit(e) {
    e.preventDefault();
    
    if (!validateStep(6)) {
        return;
    }
    
    // Find Universal Migration Service database master
    const universalService = databaseMasters.find(db => 
        db.name.toLowerCase().includes('universal') || 
        db.service_url.includes('5011')
    );
    
    if (!universalService) {
        showError('Universal Migration Service not found. This should be automatically registered. Please restart the backend or check the Service Manager page.');
        return;
    }
    
    const submitButton = document.getElementById('submitButton');
    submitButton.disabled = true;
    submitButton.textContent = 'Creating...';
    
    try {
        // Prepare config data
        const configData = {
            source_type: formData.source_type,
            dest_type: formData.dest_type,
            source: formData.source,
            destination: formData.destination,
            operation_type: formData.operation_type
        };
        
        if (formData.last_sync_time) {
            configData.last_sync_time = formData.last_sync_time;
        }
        
        // Create operation
        const operationData = {
            source_id: universalService.id,
            schedule: formData.schedule,
            operation_type: formData.operation_type,
            config_data: configData
        };
        
        const response = await operationsAPI.create(operationData);
        
        showSuccess('Operation created successfully!');
        
        setTimeout(() => {
            window.location.href = `operation-detail.html?id=${response.operation.id}`;
        }, 1500);
        
    } catch (error) {
        console.error('Error creating operation:', error);
        showError(error.message || 'Failed to create operation');
        submitButton.disabled = false;
        submitButton.textContent = 'Create Operation';
    }
}

// Make functions globally accessible
window.selectSource = selectSource;
window.selectDestination = selectDestination;
window.nextStep = nextStep;
window.previousStep = previousStep;

