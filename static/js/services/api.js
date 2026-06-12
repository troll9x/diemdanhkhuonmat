/**
 * Dịch vụ API Tập trung (Centralized API Service)
 * Xử lý tất cả các lời gọi API với xác thực JWT và xử lý lỗi.
 * Tự động làm mới token khi nhận 401 và chuyển hướng về login khi cần.
 */

class APIService {
    constructor() {
        this.baseURL = '/api';      // URL gốc của API backend
        this.timeout = 30000;       // Thời gian chờ tối đa: 30 giây
    }

    /**
     * Gọi API có xác thực JWT.
     * Tự động thêm Authorization header.
     * Tự động làm mới token khi nhận HTTP 401.
     * Tham số: endpoint (chuỗi URL), options (fetch options)
     */
    async call(endpoint, options = {}) {
        const token = auth.getToken();
        if (!token && !options.public) {
            throw new Error('Not authenticated');   // Chưa đăng nhập
        }

        const url = `${this.baseURL}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (token) {
            headers['Authorization'] = `Bearer ${token}`;   // Gắn JWT token vào header
        }

        const config = {
            ...options,
            headers,
            timeout: this.timeout
        };

        try {
            let response = await fetch(url, config);

            // Xử lý token hết hạn (401) — thử làm mới token và gọi lại
            if (response.status === 401) {
                try {
                    const newToken = await auth.refreshToken();
                    headers['Authorization'] = `Bearer ${newToken}`;
                    response = await fetch(url, { ...config, headers });
                } catch (error) {
                    window.location.href = '/login';   // Refresh thất bại → về trang đăng nhập
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
     * Gửi yêu cầu GET.
     */
    async get(endpoint, options = {}) {
        return this.call(endpoint, { ...options, method: 'GET' });
    }

    /**
     * Gửi yêu cầu POST với dữ liệu JSON.
     */
    async post(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    /**
     * Gửi yêu cầu PUT với dữ liệu JSON (cập nhật toàn bộ).
     */
    async put(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    /**
     * Gửi yêu cầu DELETE.
     */
    async delete(endpoint, options = {}) {
        return this.call(endpoint, { ...options, method: 'DELETE' });
    }

    /**
     * Gửi yêu cầu PATCH với dữ liệu JSON (cập nhật một phần).
     */
    async patch(endpoint, data, options = {}) {
        return this.call(endpoint, {
            ...options,
            method: 'PATCH',
            body: JSON.stringify(data)
        });
    }

    // ============ API XÁC THỰC (AUTH) ============

    /** Đăng nhập — POST /api/auth/login */
    async login(username, password) {
        const response = await this.post('/auth/login', { username, password }, { public: true });
        // Backend trả về: { access_token, refresh_token, user: { id, role, user_type, name, email } }
        return response;
    }

    /** Đăng xuất — POST /api/auth/logout, xoá token và chuyển về trang đăng nhập */
    async logout() {
        try {
            await this.post('/auth/logout', {});
        } catch (error) {
            console.error('Logout error:', error);
        }
        await auth.logout();           // Xoá dữ liệu local
        window.location.href = '/login';
    }

    /** Làm mới access token — POST /api/auth/refresh */
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
        // Backend trả về: { access_token }
        auth.setTokens(data.access_token, refreshToken);
        return data.access_token;
    }

    /** Lấy thông tin người dùng hiện tại — GET /api/auth/me */
    async getCurrentUser() {
        return this.get('/auth/me');
    }

    // ============ API DASHBOARD (TỔNG QUAN) ============

    /** Tổng quan dashboard quản trị viên */
    async getAdminDashboard() {
        return this.get('/dashboards/admin/overview');
    }

    /** Tổng quan dashboard giảng viên */
    async getTeacherDashboard() {
        return this.get('/dashboards/lecturer/overview');
    }

    /** Tổng quan dashboard sinh viên */
    async getStudentDashboard() {
        return this.get('/dashboards/student/profile');
    }

    // ============ API ĐIỂM DANH (ATTENDANCE) ============

    /** Lấy danh sách điểm danh (có lọc theo params) */
    async getAttendance(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/attendance${query ? '?' + query : ''}`);
    }

    /** Ghi nhận điểm danh mới */
    async recordAttendance(data) {
        return this.post('/attendance', data);
    }

    /** Lấy thông tin một phiên điểm danh */
    async getAttendanceSession(sessionId) {
        return this.get(`/attendance/${sessionId}`);
    }

    /** Lấy thống kê của một phiên điểm danh */
    async getAttendanceStats(sessionId) {
        return this.get(`/attendance/${sessionId}/stats`);
    }

    /** Tạo mã QR cho một phiên điểm danh */
    async generateQR(sessionId) {
        return this.get(`/attendance/generate-qr/${sessionId}`);
    }

    // ============ API NHẬN DIỆN KHUÔN MẶT (RECOGNITION) ============

    /** Xác minh khuôn mặt */
    async verifyFace(data) {
        return this.post('/recognize/verify', data);
    }

    /** Phát hiện khuôn mặt trong ảnh */
    async detectFace(imageData) {
        return this.post('/recognize/detect', { image: imageData });
    }

    // ============ API BUỔI HỌC (CLASS SESSIONS) ============

    /** Lấy danh sách buổi học (có lọc) */
    async getClassSessions(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/class-sessions${query ? '?' + query : ''}`);
    }

    /** Tạo buổi học mới */
    async createClassSession(data) {
        return this.post('/class-sessions', data);
    }

    /** Lấy chi tiết một buổi học */
    async getClassSession(sessionId) {
        return this.get(`/class-sessions/${sessionId}`);
    }

    /** Cập nhật buổi học */
    async updateClassSession(sessionId, data) {
        return this.put(`/class-sessions/${sessionId}`, data);
    }

    /** Xoá buổi học */
    async deleteClassSession(sessionId) {
        return this.delete(`/class-sessions/${sessionId}`);
    }

    /** Bắt đầu điểm danh cho buổi học */
    async startSessionAttendance(sessionId) {
        return this.post(`/class-sessions/${sessionId}/start`, {});
    }

    /** Kết thúc điểm danh cho buổi học */
    async endSessionAttendance(sessionId) {
        return this.post(`/class-sessions/${sessionId}/end`, {});
    }

    /** Lấy thống kê trực tiếp (live) của buổi học */
    async getSessionLiveStats(sessionId) {
        return this.get(`/class-sessions/${sessionId}/live-stats`);
    }

    // ============ API DỮ LIỆU DANH MỤC (MASTER DATA) ============

    /** Lấy danh sách khoa/phòng ban */
    async getDepartments(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/departments${query ? '?' + query : ''}`);
    }

    /** Lấy danh sách môn học */
    async getSubjects(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/subjects${query ? '?' + query : ''}`);
    }

    /** Lấy danh sách lớp học */
    async getClassrooms(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/classrooms${query ? '?' + query : ''}`);
    }

    /** Lấy danh sách sinh viên */
    async getStudents(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/students${query ? '?' + query : ''}`);
    }

    /** Lấy danh sách giảng viên */
    async getLecturers(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/lecturers${query ? '?' + query : ''}`);
    }

    // ============ API BÁO CÁO (REPORTS) ============

    /** Lấy URL xuất báo cáo Excel (trả về URL, không gọi trực tiếp) */
    async exportAttendanceExcel(params = {}) {
        const query = new URLSearchParams(params).toString();
        return `/api/reports/attendance/excel${query ? '?' + query : ''}`;
    }

    /** Lấy URL xuất báo cáo PDF */
    async exportAttendancePDF(params = {}) {
        const query = new URLSearchParams(params).toString();
        return `/api/reports/attendance/pdf${query ? '?' + query : ''}`;
    }

    // ============ API HỆ THỐNG (SYSTEM) ============

    /** Lấy thống kê hệ thống */
    async getSystemStats() {
        return this.get('/system/stats');
    }

    /** Kiểm tra sức khoẻ hệ thống */
    async getSystemHealth() {
        return this.get('/system/health');
    }

    // ============ API THÔNG BÁO (NOTIFICATIONS) ============

    /** Lấy danh sách thông báo */
    async getNotifications(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/notifications${query ? '?' + query : ''}`);
    }

    /** Đánh dấu một thông báo đã đọc */
    async markNotificationRead(id) {
        return this.put(`/notifications/${id}/read`, {});
    }

    /** Đánh dấu tất cả thông báo đã đọc */
    async markAllNotificationsRead() {
        return this.put('/notifications/read-all', {});
    }

    /** Xoá một thông báo */
    async deleteNotification(id) {
        return this.delete(`/notifications/${id}`);
    }

    /** Lấy thống kê báo cáo (mặc định 30 ngày gần đây) */
    async getReportStatistics(days = 30) {
        return this.get(`/reports/statistics?days=${days}`);
    }

    /** Lấy danh sách bản ghi điểm danh */
    async listAttendanceRecords(params = {}) {
        const query = new URLSearchParams(params).toString();
        return this.get(`/reports/attendance${query ? '?' + query : ''}`);
    }

    // ============ API SINH VIÊN — MODULE CŨ ============

    /** Lấy thông tin sinh viên hiện tại */
    async getStudentMe() {
        return this.get('/student/me');
    }

    /** Đăng ký khuôn mặt — gửi form-data với ảnh */
    async registerFace(formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/register-face`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData   // FormData với file ảnh và pose
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    /** Lấy các phiên điểm danh đang mở */
    async getActiveSessions() {
        return this.get('/student/active-sessions');
    }

    /** Hoàn thành đăng ký khuôn mặt và kích hoạt huấn luyện SVM */
    async completeRegistration() {
        return this.post('/student/complete-registration', {});
    }

    /** Điểm danh bằng khuôn mặt + GPS — gửi form-data */
    async studentCheckin(sessionId, formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/sessions/${sessionId}/check-in`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData   // FormData với ảnh và toạ độ GPS
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    // ============ API HUẤN LUYỆN MÔ HÌNH (TRAINING) ============

    /** Lấy trạng thái huấn luyện */
    async getTrainingStatus() {
        return this.get('/training/status');
    }

    /** Lấy danh sách các phiên bản mô hình */
    async listFaceModels() {
        return this.get('/training/models');
    }

    /** Kích hoạt huấn luyện mô hình mới */
    async trainModel(data = {}) {
        return this.post('/training/train', data);
    }

    /** Kích hoạt một phiên bản mô hình cụ thể */
    async activateModel(modelId) {
        return this.post(`/training/models/${modelId}/activate`, {});
    }

    /** Xoá một phiên bản mô hình */
    async deleteFaceModel(modelId) {
        return this.delete(`/training/models/${modelId}`);
    }

    // ============ API GIẢNG VIÊN v2 (TEACHER) ============

    /** Dashboard giảng viên — tổng quan lớp học, sinh viên, điểm danh */
    async teacherDashboard() {
        return this.get('/teacher/dashboard');
    }

    /** Lấy danh sách lớp học của giảng viên */
    async teacherGetClasses() {
        return this.get('/teacher/classes');
    }

    /** Tạo lớp học mới (kèm lịch học hàng tuần) */
    async teacherCreateClass(data) {
        return this.post('/teacher/classes', data);
    }

    /** Lấy chi tiết một lớp học */
    async teacherGetClass(classId) {
        return this.get(`/teacher/classes/${classId}`);
    }

    /** Lấy danh sách sinh viên trong lớp */
    async teacherGetStudents(classId) {
        return this.get(`/teacher/classes/${classId}/students`);
    }

    /** Mở phiên điểm danh cho lớp (kèm toạ độ GPS của giảng viên) */
    async teacherStartAttendance(classId, latitude, longitude, sessionType = 'start') {
        return this.post(`/teacher/classes/${classId}/attendance/start`, { latitude, longitude, session_type: sessionType });
    }

    /** Đóng phiên điểm danh */
    async teacherCloseAttendance(classId, sessionType = 'start') {
        return this.post(`/teacher/classes/${classId}/attendance/close`, { session_type: sessionType });
    }

    /** Xem điểm danh hôm nay của lớp */
    async teacherGetTodayAttendance(classId) {
        return this.get(`/teacher/classes/${classId}/attendance/today`);
    }

    /** Xem lịch sử điểm danh đầy đủ của lớp */
    async teacherGetAttendanceLogs(classId) {
        return this.get(`/teacher/classes/${classId}/attendance/logs`);
    }

    /** Cập nhật thông tin lớp học */
    async teacherUpdateClass(classId, data) {
        return this.put(`/teacher/classes/${classId}`, data);
    }

    /** Xoá lớp học */
    async teacherDeleteClass(classId) {
        return this.delete(`/teacher/classes/${classId}`);
    }

    /** Bật/tắt lớp học (toggle active) */
    async teacherToggleClass(classId) {
        return this.patch(`/teacher/classes/${classId}/deactivate`, {});
    }

    /** Lấy sự kiện lịch (FullCalendar) trong khoảng thời gian */
    async teacherGetCalendar(start, end) {
        return this.get(`/teacher/calendar?start=${start}&end=${end}`);
    }

    /** Lấy lịch học hàng tuần của lớp */
    async teacherGetSchedules(classId) {
        return this.get(`/teacher/classes/${classId}/schedules`);
    }

    /** Thêm/cập nhật buổi học vào lịch (upsert theo thứ) */
    async teacherSaveSchedule(classId, data) {
        return this.post(`/teacher/classes/${classId}/schedules`, data);
    }

    /** Cập nhật một buổi trong lịch */
    async teacherUpdateSchedule(classId, schedId, data) {
        return this.put(`/teacher/classes/${classId}/schedules/${schedId}`, data);
    }

    /** Xoá một buổi khỏi lịch */
    async teacherDeleteSchedule(classId, schedId) {
        return this.delete(`/teacher/classes/${classId}/schedules/${schedId}`);
    }

    // ============ API SINH VIÊN v2 (STUDENT) ============

    /** Dashboard sinh viên */
    async studentDashboard() {
        return this.get('/student/dashboard');
    }

    /** Tham gia lớp học bằng mã lớp */
    async studentJoinClass(classCode, studentCode) {
        return this.post('/student/join-class', { class_code: classCode, student_code: studentCode });
    }

    /** Lấy danh sách lớp đã tham gia */
    async studentGetClasses() {
        return this.get('/student/classes');
    }

    /** Kiểm tra phiên điểm danh đang mở cho một lớp */
    async studentGetActiveSession(classId) {
        return this.get(`/student/classes/${classId}/active-session`);
    }

    /** Điểm danh bằng khuôn mặt + GPS (v2) — gửi form-data */
    async studentCheckinV2(sessionId, formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/sessions/${sessionId}/check-in`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    /** Lấy lịch sử điểm danh cá nhân */
    async studentGetAttendanceLogs() {
        return this.get('/student/attendance-logs');
    }

    /** Đăng ký khuôn mặt (v2) — gửi form-data với ảnh và pose */
    async studentRegisterFace(formData) {
        const token = auth.getToken();
        const response = await fetch(`${this.baseURL}/student/register-face`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData,
        });
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.error || `API error: ${response.status}`);
        }
        return response.json();
    }

    /** Hoàn thành đăng ký khuôn mặt và kích hoạt huấn luyện SVM */
    async studentCompleteRegistration() {
        return this.post('/student/complete-registration', {});
    }

    /**
     * Đăng ký tài khoản mới.
     * Tham số: role (teacher/student), fullName, email, password, studentCode (tuỳ chọn)
     */
    async register(role, fullName, email, password, studentCode) {
        return this.post('/auth/register', {
            role, full_name: fullName, email, password,
            student_code: studentCode || undefined,
        }, { public: true });   // Không cần xác thực để đăng ký
    }
}

// Instance toàn cục — dùng ở mọi trang
const api = new APIService();
