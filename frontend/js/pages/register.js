// Register Page Logic

document.addEventListener('DOMContentLoaded', () => {
    // Redirect if already authenticated
    redirectIfAuthenticated();
    
    const registerForm = document.getElementById('registerForm');
    const errorMessage = document.getElementById('errorMessage');
    const usernameError = document.getElementById('usernameError');
    const emailError = document.getElementById('emailError');
    const passwordError = document.getElementById('passwordError');
    const confirmPasswordError = document.getElementById('confirmPasswordError');
    
    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        // Clear previous errors
        errorMessage.classList.add('hidden');
        usernameError.textContent = '';
        emailError.textContent = '';
        passwordError.textContent = '';
        confirmPasswordError.textContent = '';
        
        const username = document.getElementById('username').value.trim();
        const email = document.getElementById('email').value.trim();
        const password = document.getElementById('password').value;
        const confirmPassword = document.getElementById('confirmPassword').value;
        
        // Validation
        let hasError = false;
        
        if (!username) {
            usernameError.textContent = 'Username is required';
            hasError = true;
        } else if (username.length < 3) {
            usernameError.textContent = 'Username must be at least 3 characters';
            hasError = true;
        }
        
        if (!email) {
            emailError.textContent = 'Email is required';
            hasError = true;
        } else if (!validateEmail(email)) {
            emailError.textContent = 'Invalid email format';
            hasError = true;
        }
        
        if (!password) {
            passwordError.textContent = 'Password is required';
            hasError = true;
        } else if (password.length < 6) {
            passwordError.textContent = 'Password must be at least 6 characters';
            hasError = true;
        }
        
        if (!confirmPassword) {
            confirmPasswordError.textContent = 'Please confirm your password';
            hasError = true;
        } else if (password !== confirmPassword) {
            confirmPasswordError.textContent = 'Passwords do not match';
            hasError = true;
        }
        
        if (hasError) return;
        
        // Disable form
        const submitButton = registerForm.querySelector('button[type="submit"]');
        submitButton.disabled = true;
        submitButton.textContent = 'Creating account...';
        
        try {
            const response = await authAPI.register(username, email, password);
            
            // Show success message
            showSuccess('Account created successfully! Redirecting to login...');
            
            // Redirect to login
            setTimeout(() => {
                window.location.href = 'login.html';
            }, 2000);
            
        } catch (error) {
            errorMessage.textContent = error.message || 'Registration failed. Please try again.';
            errorMessage.classList.remove('hidden');
            showError(error.message || 'Registration failed');
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = 'Create Account';
        }
    });
});

