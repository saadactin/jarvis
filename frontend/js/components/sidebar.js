// Sidebar Component

function createSidebar() {
    const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
    
    const menuItems = [
        { icon: '📊', label: 'Dashboard', href: 'dashboard.html', id: 'dashboard' },
        { icon: '🔄', label: 'Operations', href: 'operations.html', id: 'operations' },
        { icon: '🗄️', label: 'Database Masters', href: 'databases.html', id: 'databases' },
        { icon: '🔧', label: 'Service Manager', href: 'services.html', id: 'services' }
    ];
    
    const menuItemsHTML = menuItems.map(item => {
        const isActive = currentPage === item.href || currentPage.includes(item.id);
        return `
            <li class="sidebar-nav-item">
                <a href="${item.href}" class="sidebar-nav-link ${isActive ? 'active' : ''}">
                    <span class="sidebar-nav-icon">${item.icon}</span>
                    <span>${item.label}</span>
                </a>
            </li>
        `;
    }).join('');
    
    return `
        <aside class="sidebar" id="sidebar">
            <nav>
                <ul class="sidebar-nav">
                    ${menuItemsHTML}
                </ul>
            </nav>
        </aside>
    `;
}

function initSidebar() {
    const sidebarContainer = document.getElementById('sidebar');
    if (sidebarContainer) {
        sidebarContainer.innerHTML = createSidebar();
    } else {
        // Create sidebar if container doesn't exist
        const sidebarHTML = createSidebar();
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = sidebarHTML;
        const sidebar = tempDiv.firstElementChild;
        document.body.insertBefore(sidebar, document.body.firstChild);
    }
}

