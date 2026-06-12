/**
 * Module Xác thực (Authentication Module)
 * Xử lý đăng nhập, đăng xuất, quản lý JWT token và trạng thái người dùng.
 * Khớp với định dạng response từ routes/auth.py (backend).
 */

class AuthManager {
    constructor() {
        // Khoá lưu trữ token trong localStorage và cookie
        this.tokenKey = 'access_token';
        this.refreshTokenKey = 'refresh_token';
        this.userKey = 'user';
    }

    /**
     * Lấy giá trị cookie theo tên.
     * Trả về giá trị cookie hoặc null nếu không tìm thấy.
     */
    getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }

    /**
     * Đặt giá trị cookie với thời hạn (mặc định 7 ngày).
     * SameSite=Lax để bảo vệ CSRF.
     */
    setCookie(name, value, days = 7) {
        const date = new Date();
        date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
        const expires = "; expires=" + date.toUTCString();
        document.cookie = name + "=" + (value || "") + expires + "; path=/; SameSite=Lax";
    }

    /**
     * Xoá cookie theo tên bằng cách đặt thời hạn về quá khứ.
     */
    deleteCookie(name) {
        document.cookie = name + '=; Max-Age=-99999999; path=/';
    }

    /**
     * Đồng bộ access_token từ localStorage sang cookie nếu cookie bị mất.
     * Cần thiết vì Flask JWT đọc token từ cookie để xác thực các request trang HTML.
     */
    syncCookie() {
        const token = this.getToken();
        const cookieToken = this.getCookie(this.tokenKey);
        if (token && !cookieToken) {
            console.log('Syncing access_token from localStorage to cookie...');
            this.setCookie(this.tokenKey, token);
        }
    }

    /**
     * Kiểm tra người dùng đã đăng nhập chưa.
     * Kiểm tra cả localStorage và cookie để đảm bảo nhất quán.
     */
    isAuthenticated() {
        this.syncCookie();
        const token = this.getToken();
        const cookieToken = this.getCookie(this.tokenKey);
        return !!(token && cookieToken);   // Phải có cả hai mới coi là đã xác thực
    }

    /**
     * Lấy access token từ localStorage.
     */
    getToken() {
        return localStorage.getItem(this.tokenKey);
    }

    /**
     * Lấy refresh token từ localStorage.
     */
    getRefreshToken() {
        return localStorage.getItem(this.refreshTokenKey);
    }

    /**
     * Lưu cả access token và refresh token vào localStorage và cookie.
     * Cookie cần thiết để Flask đọc khi render trang HTML.
     */
    setTokens(accessToken, refreshToken) {
        localStorage.setItem(this.tokenKey, accessToken);
        localStorage.setItem(this.refreshTokenKey, refreshToken);
        this.setCookie(this.tokenKey, accessToken);   // Đồng bộ vào cookie
    }

    /**
     * Lấy thông tin người dùng từ localStorage.
     * Trả về object user hoặc null.
     */
    getUser() {
        const user = localStorage.getItem(this.userKey);
        return user ? JSON.parse(user) : null;
    }

    /**
     * Lưu thông tin người dùng vào localStorage dưới dạng JSON.
     */
    setUser(user) {
        localStorage.setItem(this.userKey, JSON.stringify(user));
    }

    /**
     * Kiểm tra người dùng có vai trò cụ thể không.
     * Hỗ trợ cả trường 'role' và 'user_type' từ backend để tương thích ngược.
     */
    hasRole(role) {
        const user = this.getUser();
        if (!user) return false;
        return user.role === role || user.user_type === role;
    }

    /**
     * Lấy vai trò của người dùng hiện tại.
     * Ưu tiên 'role', fallback về 'user_type'.
     */
    getRole() {
        const user = this.getUser();
        return user ? (user.role || user.user_type) : null;
    }

    /**
     * Đăng nhập bằng username và password.
     * Gọi POST /api/auth/login, lưu token và thông tin user vào storage.
     * Trả về dữ liệu response hoặc ném lỗi.
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
     * Làm mới access token bằng refresh token.
     * Gọi POST /api/auth/refresh, cập nhật token mới vào storage.
     * Tự đăng xuất nếu refresh thất bại.
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
     * Đăng xuất: xoá tất cả dữ liệu người dùng khỏi localStorage và cookie.
     */
    async logout() {
        localStorage.removeItem(this.tokenKey);
        localStorage.removeItem(this.refreshTokenKey);
        localStorage.removeItem(this.userKey);
        this.deleteCookie(this.tokenKey);
    }
}

// Instance toàn cục — dùng ở mọi trang
const auth = new AuthManager();

/**
 * Yêu cầu xác thực: chuyển hướng về trang đăng nhập nếu chưa đăng nhập.
 * Gọi ở đầu mỗi trang yêu cầu đăng nhập.
 */
function requireAuth() {
    if (!auth.isAuthenticated()) {
        window.location.href = '/login';
    }
}

/**
 * Chuyển hướng đến dashboard tương ứng với vai trò người dùng sau khi đăng nhập.
 * Ánh xạ vai trò -> URL dashboard:
 *   admin    -> /admin-dashboard
 *   lecturer -> /lecturer-dashboard
 *   student  -> /student-dashboard
 */
function redirectToDashboard() {
    const user = auth.getUser();
    console.log('redirectToDashboard called, user:', user);

    if (!user) {
        console.error('No user found in localStorage');
        window.location.href = '/login';
        return;
    }

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
        case 'teacher':
            dashboardUrl = '/teacher/dashboard';   // Dashboard mới cho giảng viên
            break;
        case 'student':
            dashboardUrl = '/student/dashboard';   // Dashboard mới cho sinh viên
            break;
        default:
            console.error('Unknown role:', role);
            dashboardUrl = '/login';
    }

    console.log('REDIRECTING TO', dashboardUrl);
    window.location.href = dashboardUrl;
}

/**
 * Định dạng ngày theo múi giờ Việt Nam (vi-VN).
 * Trả về chuỗi ngày hoặc '—' nếu không có giá trị.
 */
function formatDate(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleDateString('vi-VN');
}

/**
 * Định dạng ngày giờ đầy đủ theo múi giờ Việt Nam.
 * Trả về chuỗi ngày giờ hoặc '—' nếu không có giá trị.
 */
function formatDateTime(dateString) {
    if (!dateString) return '—';
    const date = new Date(dateString);
    return date.toLocaleString('vi-VN');
}
