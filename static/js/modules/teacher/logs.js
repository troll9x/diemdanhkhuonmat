/**
 * Module Lịch Sử Điểm Danh Giảng Viên (Teacher Attendance Logs)
 * Hiển thị lịch sử điểm danh theo từng phiên, nhóm theo lớp học.
 * Có thể lọc theo lớp cụ thể hoặc xem tất cả các lớp cùng lúc.
 * Mỗi phiên hiện: ngày, trạng thái (mở/đóng), tỉ lệ điểm danh,
 * và bảng chi tiết sinh viên (giờ vào, đúng giờ/muộn, khoảng cách GPS).
 */

// Danh sách tất cả lớp học (dùng để render dropdown bộ lọc)
let allClasses = [];

/**
 * Khởi tạo trang:
 *   1. Tải danh sách lớp học để điền vào dropdown bộ lọc
 *   2. Tải logs (mặc định: tất cả lớp)
 */
async function init() {
    try {
        const data = await api.teacherGetClasses();
        allClasses = data.classes || [];
        const sel = document.getElementById('classFilter');
        // Thêm option cho từng lớp vào dropdown
        allClasses.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = c.name;
            sel.appendChild(opt);
        });
        loadLogs();
    } catch (e) {
        document.getElementById('logsList').innerHTML =
            `<div class="alert alert-danger">Lỗi tải lớp: ${e.message}</div>`;
    }
}

/**
 * Tải và render lịch sử điểm danh.
 * Nếu không chọn lớp cụ thể: tải tất cả lớp và gộp vào một trang.
 * Nếu chọn lớp cụ thể: chỉ hiện logs của lớp đó.
 */
async function loadLogs() {
    const classId = document.getElementById('classFilter').value;
    const list = document.getElementById('logsList');
    list.innerHTML = '<div class="text-center py-5"><div class="spinner-border"></div></div>';

    if (!classId) {
        // Không lọc → hiện tất cả lớp
        if (allClasses.length === 0) {
            list.innerHTML = '<div class="text-center py-5 text-muted">Chưa có lớp học nào.</div>';
            return;
        }
        const sections = [];
        // Tải log từng lớp tuần tự (không song song vì muốn duy trì thứ tự)
        for (const c of allClasses) {
            try {
                const data = await api.teacherGetAttendanceLogs(c.id);
                if (data.logs && data.logs.length > 0) {
                    sections.push(renderLogsSection(c.name, data.logs));
                }
            } catch (_) {} // Bỏ qua lớp có lỗi
        }
        list.innerHTML = sections.length ? sections.join('') :
            '<div class="text-center py-5 text-muted">Chưa có phiên điểm danh nào.</div>';
        return;
    }

    // Lọc theo lớp cụ thể
    try {
        const data = await api.teacherGetAttendanceLogs(classId);
        if (!data.logs || data.logs.length === 0) {
            list.innerHTML = '<div class="text-center py-5 text-muted">Chưa có phiên điểm danh nào.</div>';
            return;
        }
        const cls = allClasses.find(c => String(c.id) === classId);
        list.innerHTML = renderLogsSection(cls ? cls.name : '', data.logs);
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    }
}

/**
 * Render một section logs cho một lớp học.
 * Mỗi phiên là một card với header tóm tắt và bảng chi tiết sinh viên.
 * @param {string} className - Tên lớp học
 * @param {Array}  logs      - Mảng phiên điểm danh
 * @returns {string} HTML string
 */
function renderLogsSection(className, logs) {
    const rows = logs.map(log => `
        <div class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span>
                    <i class="bi bi-calendar-event me-2"></i>
                    ${log.session_date}
                    <span class="badge ms-2 bg-${log.status === 'open' ? 'success' : 'secondary'}">${log.status}</span>
                </span>
                <span>
                    <span class="badge bg-primary">${log.total_attended}/${log.total_enrolled} điểm danh</span>
                </span>
            </div>
            ${log.records && log.records.length > 0 ? `
            <div class="card-body p-0">
                <table class="table table-sm mb-0">
                    <thead><tr>
                        <th>Sinh viên</th>
                        <th>Giờ vào</th>
                        <th>Trạng thái</th>
                        <th>Đúng giờ?</th>
                        <th>Khoảng cách</th>
                    </tr></thead>
                    <tbody>${log.records.map(r => `<tr>
                        <td>${escHtml(r.student_name)}</td>
                        <td>${r.checkin_time || '—'}</td>
                        <td><span class="badge bg-${r.status === 'present' ? 'success' : 'danger'}">
                            ${r.status === 'present' ? 'Có mặt' : 'Từ chối'}
                        </span></td>
                        <td>${r.status === 'present'
                            ? (r.is_late
                                ? '<span class="badge bg-warning text-dark">Muộn</span>'
                                : '<span class="badge bg-info">Đúng giờ</span>')
                            : '—'}</td>
                        <td>${r.distance_meters != null ? r.distance_meters + ' m' : '—'}</td>
                    </tr>`).join('')}</tbody>
                </table>
            </div>` : ''}
        </div>`).join('');
    return `<h5 class="fw-bold mb-3">${escHtml(className)}</h5>${rows}`;
}

/**
 * Escape HTML để ngăn XSS khi chèn dữ liệu từ server vào innerHTML.
 */
function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Khởi động trang
init();
