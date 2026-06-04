/**
 * Authentication Module
 * Handles login, logout, token management, and user state
 * Matches backend response format from routes/auth.py
 */

class AuthManager {
    constructor() {
        this.tokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.userKey = 'user';
    }

    /**
     * Helper to get cookie value
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Helper to set cookie value
     */
    setCookie(name, value, days = 7) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = "; expires=" + date.toUTCString();
        document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax";
    }

    /**
     * Helper to delete cookie
     */
    deleteCookie(name) {
        document.cookie = name + '=; Max-Age=-99999999; path=/';
    }

    /**
     * Check if user is authenticated
     * Checks both localStorage and cookies for consistency
     */
    /**
     * Sync cookie from localStorage if missing
     */
    syncCookie() {
        const token = this.getToken();
        const cookieToken = this.getCookie(this.tokenKey);
        if (token && !cookieToken) {
            console.log('Syncing access_token from localStorage to cookie...');
            this.setCookie(this.tokenKey, token);
        }
    }

    isAuthenticated() {
        this.syncCookie();
        const token = this.getToken();
        const cookieToken = this.getCookie(this.tokenKey);
        return !!(token && cookieToken);
    }

    /**
     * Get access token
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * Get refresh token
     */
    getRefreshToken() {
        return localStorage.getItem(this.refreshTokenKey);
    }

    /**
     * Set tokens in both localStorage and cookies
     */
    setTokens(accessToken, refreshToken) {
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        this.setCookie(this.tokenKey, accessToken);
    }

    /**
     * Get user info
     */
    getUser() {
        const user = localStorage.getItem(this.userKey);
        return user ? JSON.parse(user) : null;
    }

    /**
     * Set user info
     */
    setUser(user) {
        localStorage.setItem(this.userKey, JSON.stringify(user));
    }

    /**
     * Check if user has role
     * Supports both 'role' and 'user_type' fields from backend
     */
    hasRole(role) {
        const user = this.getUser();
        if (!user) return false;
        
        // Check both role and user_type for compatibility
        return user.role === role || user.user_type === role;
    }

    /**
     * Get user role
     */
    getRole() {
        const user = this.getUser();
        return user ? (user.role || user.user_type) : null;
    }

    /**
     * Login user with username and password
     */
    async login(username, password) {
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Đăng nhập thất bại');
            }

            const data = await response.json();
            console.log("LOGIN RESPONSE", data);
            this.setTokens(data.access_token, data.refresh_token);
            this.setUser(data.user);
            console.log("USER", this.getUser());
            console.log("ROLE", this.getRole());
            console.log("TOKEN", this.getToken());
            return data;
        } catch (error) {
            console.error('Login error:', error);
            throw error;
        }
    }

    /**
     * Refresh access token using refresh token
     */
    async refreshToken() {
        try {
            const refreshToken = this.getRefreshToken();
            if (!refreshToken) {
                throw new Error('No refresh token available');
            }

            const response = await fetch('/api/auth/refresh', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${refreshToken}`
                }
            });

            if (!response.ok) {
                this.logout();
                throw new Error('Token refresh failed');
            }

            const data = await response.json();
            this.setTokens(data.access_token, refreshToken);
            return data.access_token;
        } catch (error) {
            console.error('Token refresh error:', error);
            throw error;
        }
    }

    /**
     * Logout
     */
    async logout() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.userKey);
        this.deleteCookie(this.tokenKey);
    }
}

// Global auth instance
const auth = new AuthManager();

/**
 * Require authentication
 */
function requireAuth() {
    if (!auth.isAuthenticated()) {
        window.location.href = '/login';
    }
}

/**
 * Redirect to appropriate dashboard based on role
 * Maps role to dashboard URL
 * Role values from backend: 'admin', 'lecturer', 'student'
 */
function redirectToDashboard() {
    const user = auth.getUser();
    console.log('redirectToDashboard called, user:', user);
    
    if (!user) {
        console.error('No user found in localStorage');
        window.location.href = '/login';
        return;
    }

    // Get role from user object (backend returns 'role' field)
    const role = user.role;
    
    console.log('User role:', role);
    
    if (!role) {
        console.error('No role found in user object');
        window.location.href = '/login';
        return;
    }
    
    let dashboardUrl = '/login';
    
    switch (role) {
        case 'admin':
            dashboardUrl = '/admin-dashboard';
            break;
        case 'lecturer':
            dashboardUrl = '/lecturer-dashboard';
            break;
        case 'student':
            dashboardUrl = '/student-dashboard';
            break;
        default:
            console.error('Unknown role:', role);
            dashboardUrl = '/login';
    }
    
    console.log('REDIRECTING TO', dashboardUrl);
    console.log('About to call window.location.href');
    window.location.href = dashboardUrl;
    console.log('After window.location.href (should not reach here)');
}

/**
 * Format date helper
 */
function formatDate(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN');
}

/**
 * Format datetime helper
 */
function formatDateTime(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN');
}