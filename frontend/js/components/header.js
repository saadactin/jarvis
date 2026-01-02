// Header Component

function createHeader() {
    const user = getUser();
    
    return `
        <header class="header">
            <div class="d-flex align-center gap-md">
                <button class="mobile-menu-toggle" id="mobileMenuToggle">☰</button>
                <div class="header-logo">Jarvis Migration System</div>
            </div>
            <div class="header-user">
                <span class="header-user-name">${user ? user.username : 'Guest'}</span>
                <div class="header-user-menu">
                    <button class="user-menu-button" id="userMenuButton">▼</button>
                    <div class="user-menu-dropdown" id="userMenuDropdown">
                        <div class="user-menu-item" onclick="logout()">Logout</div>
                    </div>
                </div>
            </div>
        </header>
    `;
}

function initHeader() {
    const headerContainer = document.getElementById('header');
    if (headerContainer) {
        headerContainer.innerHTML = createHeader();
        
        // User menu toggle
        const userMenuButton = document.getElementById('userMenuButton');
        const userMenuDropdown = document.getElementById('userMenuDropdown');
        
        if (userMenuButton && userMenuDropdown) {
            userMenuButton.addEventListener('click', (e) => {
                e.stopPropagation();
                userMenuDropdown.classList.toggle('show');
            });
            
            // Close menu when clicking outside
            document.addEventListener('click', () => {
                userMenuDropdown.classList.remove('show');
            });
        }
        
        // Mobile menu toggle
        const mobileMenuToggle = document.getElementById('mobileMenuToggle');
        if (mobileMenuToggle) {
            mobileMenuToggle.addEventListener('click', () => {
                const sidebar = document.getElementById('sidebar');
                if (sidebar) {
                    sidebar.classList.toggle('open');
                }
            });
        }
    }
}

