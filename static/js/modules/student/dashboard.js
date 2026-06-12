/**
 * Module Dashboard Sinh Viên (Student Dashboard)
 * Hiển thị tổng quan:
 *   - Tổng số lớp đã tham gia
 *   - Trạng thái đăng ký khuôn mặt (đã / chưa đăng ký)
 *   - Danh sách phiên điểm danh đang mở hôm nay
 *   - Danh sách tất cả các lớp học đã tham gia
 * Chạy tự động khi trang tải (IIFE).
 */
(async function () {
    // Hiển thị lời chào cá nhân hoá — dùng trường name hoặc full_name từ JWT user
    const user = auth.getUser();
    if (user) {
        document.getElementById('welcomeMsg').textContent =
            `Xin chào, ${user.name || user.full_name || ''}!`;
    }

    try {
        // Gọi API lấy dữ liệu tổng quan sinh viên
        const data = await api.studentDashboard();

        // Hiển thị tổng số lớp học
        document.getElementById('totalClasses').textContent = data.total_classes ?? 0;

        // Hiển thị trạng thái đăng ký khuôn mặt
        const faceEl = document.getElementById('faceStatus');
        if (data.face_registered) {
            faceEl.textContent = 'Đã đăng ký';
            faceEl.className = 'stat-value text-success';
        } else {
            // Chưa đăng ký — hiện cảnh báo và link đến trang đăng ký
            faceEl.textContent = 'Chưa đăng ký';
            faceEl.className = 'stat-value text-danger';
            document.getElementById('faceAlert').innerHTML = `
                <div class="alert alert-warning">
                    <i class="bi bi-exclamation-triangle me-2"></i>
                    Bạn chưa đăng ký khuôn mặt. Hãy <a href="/student/face-registration">đăng ký ngay</a> để có thể điểm danh.
                </div>`;
        }

        // Hiển thị số phiên điểm danh đang mở
        document.getElementById('openSessionCount').textContent =
            (data.open_sessions || []).length;

        // Render danh sách phiên điểm danh đang mở
        const sessBox = document.getElementById('openSessionsList');
        if (!data.open_sessions || data.open_sessions.length === 0) {
            sessBox.innerHTML =
                '<div class="text-center py-4 text-muted">Không có phiên điểm danh nào đang mở.</div>';
        } else {
            sessBox.innerHTML = data.open_sessions.map(s => `
                <div class="d-flex justify-content-between align-items-center p-3 border-bottom">
                    <div>
                        <strong>${escHtml(s.classroom_name)}</strong>
                        ${s.already_checked_in
                            ? '<span class="badge bg-success ms-2">Đã điểm danh</span>'
                            : '<span class="badge bg-warning text-dark ms-2">Chưa điểm danh</span>'}
                    </div>
                    ${!s.already_checked_in
                        ? `<a href="/student/checkin" class="btn btn-sm btn-success">
                               <i class="bi bi-camera-video me-1"></i>Điểm danh ngay
                           </a>`
                        : ''}
                </div>`).join('');
        }

        // Render danh sách lớp học đã tham gia (gọi API riêng)
        const clsBox = document.getElementById('myClassesList');
        const classes = await api.studentGetClasses();
        if (!classes.classes || classes.classes.length === 0) {
            clsBox.innerHTML = `<div class="text-center py-4 text-muted">
                Chưa tham gia lớp nào. <a href="/student/join-class">Tham gia lớp ngay</a></div>`;
        } else {
            clsBox.innerHTML = classes.classes.map(c => `
                <div class="d-flex justify-content-between align-items-center p-3 border-bottom">
                    <div>
                        <strong>${escHtml(c.name)}</strong>
                        <small class="text-muted ms-2">${c.teacher_name}</small>
                        <br><small class="text-muted">Mã lớp: <code>${c.class_code}</code></small>
                    </div>
                    <div>
                        ${c.today_session
                            ? (c.today_session.already_checked_in
                                ? '<span class="badge bg-success">Đã điểm danh</span>'
                                : '<span class="badge bg-warning text-dark">Chưa điểm danh</span>')
                            : '<span class="badge bg-secondary">Chưa mở</span>'}
                    </div>
                </div>`).join('');
        }
    } catch (e) {
        console.error(e);
    }
}());

/**
 * Escape HTML để ngăn XSS khi chèn chuỗi từ server vào innerHTML.
 * @param {string} str - Chuỗi cần escape
 * @returns {string} Chuỗi an toàn để chèn vào HTML
 */
function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
