/**
 * Module Lịch Sử Điểm Danh Sinh Viên (Student Attendance Logs)
 * Tải và hiển thị toàn bộ lịch sử điểm danh của sinh viên hiện tại dưới dạng bảng.
 * Các cột: Ngày | Lớp | Loại phiên | Giờ vào | Trạng thái | Đúng giờ | Khoảng cách | Lý do từ chối
 * Chạy tự động khi trang tải (IIFE).
 */
(async function () {
    const list = document.getElementById('logsList');
    try {
        // Gọi API lấy toàn bộ lịch sử điểm danh
        const data = await api.studentGetAttendanceLogs();
        const logs = data.logs || [];

        // Hiển thị tổng số bản ghi trên badge
        document.getElementById('totalBadge').textContent = `${logs.length} bản ghi`;

        if (logs.length === 0) {
            list.innerHTML = '<div class="text-center py-5 text-muted">Chưa có lịch sử điểm danh nào.</div>';
            return;
        }

        // Render từng dòng bảng
        // - status: 'present' = có mặt (xanh lá), khác = từ chối (đỏ)
        // - is_late: true = muộn (vàng), false = đúng giờ (xanh nhạt)
        // - distance_meters: khoảng cách GPS tính bằng mét
        // - reject_reason: lý do từ chối (nếu có)
        const rows = logs.map(r => `
            <tr>
                <td>${r.session_date || '—'}</td>
                <td>${escHtml(r.classroom_name)}</td>
                <td class="fw-semibold">${escHtml(r.session_type_label || '—')}</td>
                <td>${r.checkin_time}</td>
                <td>
                    <span class="badge bg-${r.status === 'present' ? 'success' : 'danger'}">
                        ${r.status === 'present' ? 'Có mặt' : 'Từ chối'}
                    </span>
                </td>
                <td>${r.status === 'present'
                    ? (r.is_late
                        ? '<span class="badge bg-warning text-dark">Muộn</span>'
                        : '<span class="badge bg-info">Đúng giờ</span>')
                    : '—'}</td>
                <td>${r.distance_meters != null ? r.distance_meters + ' m' : '—'}</td>
                <td>${r.reject_reason ? `<span class="text-danger small">${escHtml(r.reject_reason)}</span>` : '—'}</td>
            </tr>`).join('');

        // Chèn bảng vào trang
        list.innerHTML = `
            <table class="table table-hover">
                <thead>
                    <tr>
                        <th>Ngày</th><th>Lớp</th><th>Loại phiên</th><th>Giờ vào</th>
                        <th>Trạng thái</th><th>Đúng giờ</th>
                        <th>Khoảng cách</th><th>Lý do từ chối</th>
                    </tr>
                </thead>
                <tbody>${rows}</tbody>
            </table>`;
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">Lỗi tải dữ liệu: ${e.message}</div>`;
    }
}());

/**
 * Escape HTML để ngăn XSS khi chèn dữ liệu từ server vào innerHTML.
 */
function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
