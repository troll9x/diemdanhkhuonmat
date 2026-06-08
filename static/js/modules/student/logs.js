// Student Attendance Logs JS
(async function () {
    const list = document.getElementById('logsList');
    try {
        const data = await api.studentGetAttendanceLogs();
        const logs = data.logs || [];
        document.getElementById('totalBadge').textContent = `${logs.length} bản ghi`;

        if (logs.length === 0) {
            list.innerHTML = '<div class="text-center py-5 text-muted">Chưa có lịch sử điểm danh nào.</div>';
            return;
        }

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

function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
