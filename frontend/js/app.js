// Main Application Logic

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication for protected pages
    const protectedPages = ['dashboard.html', 'operations.html', 'operation-detail.html', 'create-operation.html', 'databases.html', 'services.html'];
    const currentPage = window.location.pathname.split('/').pop();
    
    if (protectedPages.includes(currentPage)) {
        if (!requireAuth()) {
            return; // Will redirect to login
        }
    }
    
    // Initialize header and sidebar for protected pages
    if (protectedPages.includes(currentPage)) {
        initHeader();
        initSidebar();
    }
});

// Global error handler
window.addEventListener('error', (event) => {
    console.error('Global error:', event.error);
    showError('An unexpected error occurred. Please refresh the page.');
});

// Handle unhandled promise rejections
window.addEventListener('unhandledrejection', (event) => {
    console.error('Unhandled promise rejection:', event.reason);
    showError(event.reason?.message || 'An error occurred. Please try again.');
});

