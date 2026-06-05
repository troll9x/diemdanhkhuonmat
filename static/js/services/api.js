/**
 * Centralized API Service
 * Handles all API calls with authentication and error handling
 */

class APIService {
    constructor() {
        this.baseURL = '/api';
        this.timeout = 30000;
    }

    /**
     * Make authenticated API call
     */
    async call(endpoint, options = {}) {
        const token = auth.getToken();
        if (!token && !options.public) {
            throw new Error('Not authenticated');
        }

        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const config = {
            ...options,
            headers,
            timeout: this.timeout
        };

        try {
            let response = await fetch(url, config);

            // Handle token expiration
            if (response.status === 401) {
                try {
                    const newToken = await auth.refreshToken();
                    headers['Authorization'] = `Bearer ${newToken}`;
                    response = await fetch(url, { ...config, headers });
                } catch (error) {
                    window.location.href = '/login';
                    throw error;
                }
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || `API error: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API call failed: ${endpoint}`, error);
            throw error;
        }
    }

    /**
     * Get admin dashboard data
     */
    async getAdminDashboard() {
        return this.get('/dashboards/admin/overview');
    }

    /**
     * GET request
     */
    async get(endpoint, options = {}) {
        return this.call(endpoint, { ...options, method: 'GET' });
    }

    /**
     * POST request
     */
    async post(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * PUT request
     */
    async put(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * DELETE request
     */
    async delete(endpoint, options = {}) {
        return this.call(endpoint, { ...options, method: 'DELETE' });
    }

    /**
     * PATCH request
     */
    async patch(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    // ============ AUTH ENDPOINTS ============

    async login(username, password) {
        const response = await this.post('/auth/login', { username, password }, { public: true });
        // Backend returns: { access_token, refresh_token, user: { id, role, user_type, name, email } }
        return response;
    }

    async logout() {
        try {
            await this.post('/auth/logout', {});
        } catch (error) {
            console.error('Logout error:', error);
        }
        // Clear tokens and user data regardless of API response
        await auth.logout();
        // Redirect to login page
        window.location.href = '/login';
    }

    async refreshToken() {
        const refreshToken = auth.getRefreshToken();
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await fetch(`${this.baseURL}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        if (!response.ok) {
            throw new Error('Token refresh failed');
        }

        const data = await response.json();
        // Backend returns: { access_token }
        auth.setTokens(data.access_token, refreshToken);
        return data.access_token;
    }

    async getCurrentUser() {
        return this.get('/auth/me');
    }

    // ============ DASHBOARD ENDPOINTS ============

    async getAdminDashboard() {
        return this.get('/dashboards/admin/overview');
    }

    async getTeacherDashboard() {
        return this.get('/dashboards/lecturer/overview');
    }

    async getStudentDashboard() {
        return this.get('/dashboards/student/profile');
    }

    // ============ ATTENDANCE ENDPOINTS ============

    async getAttendance(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/attendance${query ? '?' + query : ''}`);
    }

    async recordAttendance(data) {
        return this.post('/attendance', data);
    }

    async getAttendanceSession(sessionId) {
        return this.get(`/attendance/${sessionId}`);
    }

    async getAttendanceStats(sessionId) {
        return this.get(`/attendance/${sessionId}/stats`);
    }

    async generateQR(sessionId) {
        return this.get(`/attendance/generate-qr/${sessionId}`);
    }

    // ============ RECOGNITION ENDPOINTS ============

    async verifyFace(data) {
        return this.post('/recognize/verify', data);
    }

    async detectFace(imageData) {
        return this.post('/recognize/detect', { image: imageData });
    }

    // ============ CLASS SESSIONS ENDPOINTS ============

    async getClassSessions(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/class-sessions${query ? '?' + query : ''}`);
    }

    async createClassSession(data) {
        return this.post('/class-sessions', data);
    }

    async getClassSession(sessionId) {
        return this.get(`/class-sessions/${sessionId}`);
    }

    async updateClassSession(sessionId, data) {
        return this.put(`/class-sessions/${sessionId}`, data);
    }

    async deleteClassSession(sessionId) {
        return this.delete(`/class-sessions/${sessionId}`);
    }

    async startSessionAttendance(sessionId) {
        return this.post(`/class-sessions/${sessionId}/start`, {});
    }

    async endSessionAttendance(sessionId) {
        return this.post(`/class-sessions/${sessionId}/end`, {});
    }

    async getSessionLiveStats(sessionId) {
        return this.get(`/class-sessions/${sessionId}/live-stats`);
    }

    // ============ MASTER DATA ENDPOINTS ============

    async getDepartments(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/departments${query ? '?' + query : ''}`);
    }

    async getSubjects(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/subjects${query ? '?' + query : ''}`);
    }

    async getClassrooms(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/classrooms${query ? '?' + query : ''}`);
    }

    async getStudents(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/students${query ? '?' + query : ''}`);
    }

    async getLecturers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/lecturers${query ? '?' + query : ''}`);
    }

    // ============ REPORTS ENDPOINTS ============

    async exportAttendanceExcel(params = {}) {
        const query = new URLSearchParams(params).toString();
        return `/api/reports/attendance/excel${query ? '?' + query : ''}`;
    }

    async exportAttendancePDF(params = {}) {
        const query = new URLSearchParams(params).toString();
        return `/api/reports/attendance/pdf${query ? '?' + query : ''}`;
    }

    // ============ SYSTEM ENDPOINTS ============

    async getSystemStats() {
        return this.get('/system/stats');
    }

    async getSystemHealth() {
        return this.get('/system/health');
    }

    // ============ NOTIFICATIONS ENDPOINTS ============

    async getNotifications(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/notifications${query ? '?' + query : ''}`);
    }

    async markNotificationRead(id) {
        return this.put(`/notifications/${id}/read`, {});
    }

    async markAllNotificationsRead() {
        return this.put('/notifications/read-all', {});
    }

    async deleteNotification(id) {
        return this.delete(`/notifications/${id}`);
    }

    // ============ REPORTS ENDPOINTS ============

    async getReportStatistics(days = 30) {
        return this.get(`/reports/statistics?days=${days}`);
    }

    async listAttendanceRecords(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/reports/attendance${query ? '?' + query : ''}`);
    }

    // ============ STUDENT MODULE ENDPOINTS ============

    async getStudentMe() {
        return this.get('/student/me');
    }

    async registerFace(formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/register-face`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    async getActiveSessions() {
        return this.get('/student/active-sessions');
    }

    async completeRegistration() {
        return this.post('/student/complete-registration', {});
    }

    async studentCheckin(sessionId, formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/sessions/${sessionId}/check-in`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    // ============ TRAINING ENDPOINTS ============

    async getTrainingStatus() {
        return this.get('/training/status');
    }

    async listFaceModels() {
        return this.get('/training/models');
    }

    async trainModel(data = {}) {
        return this.post('/training/train', data);
    }

    async activateModel(modelId) {
        return this.post(`/training/models/${modelId}/activate`, {});
    }

    async deleteFaceModel(modelId) {
        return this.delete(`/training/models/${modelId}`);
    }
}

// Global API service instance
const api = new APIService();