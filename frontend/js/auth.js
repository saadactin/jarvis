// Authentication Module

/**
 * Get stored token
 */
function getToken() {
    return localStorage.getItem('token');
}

/**
 * Store token
 */
function setToken(token) {
    localStorage.setItem('token', token);
}

/**
 * Remove token
 */
function removeToken() {
    localStorage.removeItem('token');
}

/**
 * Get stored user
 */
function getUser() {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
}

/**
 * Store user
 */
function setUser(user) {
    localStorage.setItem('user', JSON.stringify(user));
}

/**
 * Remove user
 */
function removeUser() {
    localStorage.removeItem('user');
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    return !!getToken();
}

/**
 * Logout user
 */
function logout() {
    removeToken();
    removeUser();
    window.location.href = 'login.html';
}

/**
 * Check authentication and redirect if needed
 */
function requireAuth() {
    if (!isAuthenticated()) {
        window.location.href = 'login.html';
        return false;
    }
    return true;
}

/**
 * Redirect to dashboard if authenticated
 */
function redirectIfAuthenticated() {
    if (isAuthenticated()) {
        window.location.href = 'dashboard.html';
    }
}
