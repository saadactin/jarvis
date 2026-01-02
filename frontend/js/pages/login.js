// Login Page Logic

document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already authenticated
    redirectIfAuthenticated();
    
    const loginForm = document.getElementById('loginForm');
    const errorMessage = document.getElementById('errorMessage');
    const usernameError = document.getElementById('usernameError');
    const passwordError = document.getElementById('passwordError');
    
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Clear previous errors
        errorMessage.classList.add('hidden');
        usernameError.textContent = '';
        passwordError.textContent = '';
        
        const username = document.getElementById('username').value.trim();
        const password = document.getElementById('password').value;
        const remember = document.getElementById('remember').checked;
        
        // Validation
        let hasError = false;
        
        if (!username) {
            usernameError.textContent = 'Username or email is required';
            hasError = true;
        }
        
        if (!password) {
            passwordError.textContent = 'Password is required';
            hasError = true;
        }
        
        if (hasError) return;
        
        // Disable form
        const submitButton = loginForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Signing in...';
        
        try {
            const response = await authAPI.login(username, password);
            
            // Store token and user
            setToken(response.access_token);
            setUser(response.user);
            
            // Show success message
            showSuccess('Login successful! Redirecting...');
            
            // Redirect to dashboard
            setTimeout(() => {
                window.location.href = 'dashboard.html';
            }, 1000);
            
        } catch (error) {
            errorMessage.textContent = error.message || 'Login failed. Please try again.';
            errorMessage.classList.remove('hidden');
            showError(error.message || 'Login failed');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Sign In';
        }
    });
});

