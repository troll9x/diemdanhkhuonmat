/**
 * Module Chi Tiết Lớp Học (Teacher Class Detail)
 * Hiển thị đầy đủ thông tin một lớp học:
 *   - Header: tên lớp, mã lớp (có thể sao chép), lịch học, meta info
 *   - Thanh tiến độ khoảng thời gian khóa học
 *   - Danh sách buổi học theo ngày trong tuần
 *   - Mini stats: tổng SV, tổng buổi học, tổng phiên điểm danh, ngày còn lại
 *   - Danh sách sinh viên (có tìm kiếm), trạng thái đăng ký khuôn mặt
 *   - Modal chỉnh sửa thông tin lớp
 *   - Modal quản lý lịch học
 */
'use strict';

// ID lớp học — được truyền từ template Jinja2
const CLASS_ID = PAGE_CLASS_ID;

// Tên các thứ trong tuần (ánh xạ từ day_of_week: 0=Thứ 2)
const DAY_NAMES = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'];

// Dữ liệu lớp đã tải (dùng cho modal chỉnh sửa)
let classData    = null;

// Danh sách sinh viên đầy đủ (dùng để lọc tìm kiếm phía client)
let studentsFull = [];

// ── Khởi động ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Tải thông tin lớp và danh sách sinh viên song song
    await Promise.all([loadClassDetail(), loadStudents()]);
});

// ── Tải thông tin lớp học ─────────────────────────────────────────────────────

/**
 * Tải và render toàn bộ thông tin lớp: header, ngày, lịch học, mini stats.
 */
async function loadClassDetail() {
    try {
        classData = await api.teacherGetClass(CLASS_ID);
        renderHeader(classData);
        renderDateRange(classData);
        renderSchedules(classData.schedules || []);
        renderMiniStats(classData);
    } catch (e) {
        document.getElementById('className').textContent = 'Lỗi tải dữ liệu';
        showAlert(e.message, 'danger');
    }
}

/**
 * Render header trang: tiêu đề, breadcrumb, mã lớp, meta line (ngày + lịch).
 * @param {object} c - Dữ liệu lớp học
 */
function renderHeader(c) {
    document.title = `${c.name} — Chi tiết lớp`;
    document.getElementById('breadcrumbName').textContent = c.name;
    document.getElementById('className').innerHTML =
        `${esc(c.name)} <span class="badge bg-primary ms-2" style="font-size:.6em;cursor:pointer"
             onclick="copyCode('${c.class_code}')" title="Sao chép mã lớp">
             ${c.class_code} <i class="bi bi-copy ms-1"></i>
         </span>`;

    // Dòng meta: khoảng ngày + lịch học
    const parts = [];
    if (c.start_date && c.end_date)
        parts.push(`<i class="bi bi-calendar-range me-1"></i>${fmtVN(c.start_date)} — ${fmtVN(c.end_date)}`);
    if (c.schedules && c.schedules.length)
        parts.push(`<i class="bi bi-calendar3 me-1"></i>${c.schedules.map(s => `${s.day_name} ${s.start_time}–${s.end_time}`).join(', ')}`);
    document.getElementById('classMeta').innerHTML = parts.join('&nbsp;&nbsp;·&nbsp;&nbsp;');

    // Liên kết trang điểm danh
    const headerActions = document.getElementById('headerActions');
    headerActions.style.display = '';
    document.getElementById('attendanceLink').href = `/teacher/classes/${CLASS_ID}/attendance`;
}

/**
 * Render thanh tiến độ thời gian khóa học.
 * Tính % đã trôi qua, số ngày còn lại, và trạng thái (đang học/đã kết thúc/chưa bắt đầu).
 * @param {object} c - Dữ liệu lớp học
 */
function renderDateRange(c) {
    const box = document.getElementById('dateRangeBody');
    if (!c.start_date || !c.end_date) {
        box.innerHTML = '<p class="text-muted mb-0">Chưa đặt thời gian khoá học.</p>';
        return;
    }
    const start = parseLocalDate(c.start_date);
    const end   = parseLocalDate(c.end_date);
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const totalDays    = Math.round((end - start) / 86400000);
    const elapsedDays  = Math.max(0, Math.round((today - start) / 86400000));
    const pct          = Math.min(100, Math.round(elapsedDays / totalDays * 100));
    const daysLeft     = Math.max(0, Math.round((end - today) / 86400000));
    const isActive     = today >= start && today <= end;

    box.innerHTML = `
        <div class="d-flex justify-content-between mb-1 small fw-semibold">
            <span><i class="bi bi-play-circle me-1 text-success"></i>${fmtVN(c.start_date)}</span>
            <span>${fmtVN(c.end_date)}<i class="bi bi-stop-circle ms-1 text-danger"></i></span>
        </div>
        <div class="progress mb-2" style="height:8px">
            <div class="progress-bar bg-${isActive ? 'primary' : (today > end ? 'secondary' : 'success')}"
                 style="width:${pct}%"></div>
        </div>
        <div class="d-flex justify-content-between small text-muted">
            <span>${pct}% tiến độ</span>
            <span>${isActive
                ? `<span class="text-primary">${daysLeft} ngày còn lại</span>`
                : (today > end
                    ? '<span class="text-secondary">Đã kết thúc</span>'
                    : '<span class="text-success">Chưa bắt đầu</span>')
            }</span>
        </div>`;
}

/**
 * Render danh sách các buổi học (lịch học theo thứ).
 * Hiện nút thêm lịch nếu chưa có buổi nào.
 * @param {Array} schedules - Mảng lịch học từ API
 */
function renderSchedules(schedules) {
    const box = document.getElementById('scheduleBody');
    if (!schedules.length) {
        box.innerHTML = `<div class="text-center py-4 text-muted">
            <i class="bi bi-calendar-x d-block fs-2 mb-2"></i>
            Chưa có lịch học nào.<br>
            <button class="btn btn-sm btn-outline-primary mt-2" onclick="openScheduleModal()">
                <i class="bi bi-plus me-1"></i>Thêm lịch học
            </button></div>`;
        return;
    }

    // Sắp xếp lịch theo thứ trong tuần
    const rows = schedules
        .slice().sort((a, b) => a.day_of_week - b.day_of_week)
        .map(s => `
            <div class="d-flex align-items-center justify-content-between px-3 py-3 border-bottom">
                <div class="d-flex align-items-center gap-3">
                    <div class="text-center" style="min-width:48px">
                        <div class="fw-bold text-primary">${DAY_NAMES[s.day_of_week]}</div>
                    </div>
                    <div>
                        <div class="fw-semibold">
                            <i class="bi bi-clock me-1 text-muted"></i>
                            ${s.start_time} – ${s.end_time}
                        </div>
                        <div class="text-muted small">
                            Muộn sau ${s.late_after_minutes} phút
                        </div>
                    </div>
                </div>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-warning"
                            onclick="editSched(${s.day_of_week},'${s.start_time}','${s.end_time}',${s.late_after_minutes})"
                            title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteSched(${s.id})"
                            title="Xoá">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>`).join('');

    box.innerHTML = rows;
}

/**
 * Cập nhật các ô mini stats: số SV, số buổi học, số ngày còn lại.
 * @param {object} c - Dữ liệu lớp học
 */
function renderMiniStats(c) {
    document.getElementById('statStudents').textContent  = c.student_count ?? 0;
    document.getElementById('statSchedules').textContent = c.schedules?.length ?? 0;

    // Tính số ngày còn lại đến ngày kết thúc
    const today = new Date();
    if (c.end_date) {
        const end = new Date(c.end_date);
        const left = Math.max(0, Math.round((end - today) / 86400000));
        document.getElementById('statDaysLeft').textContent = left;
    } else {
        document.getElementById('statDaysLeft').textContent = '—';
    }
}

// ── Tải danh sách sinh viên ────────────────────────────────────────────────────

/**
 * Tải danh sách sinh viên và cập nhật mini stat tổng phiên điểm danh.
 */
async function loadStudents() {
    const box = document.getElementById('studentListBody');
    try {
        const data = await api.teacherGetStudents(CLASS_ID);
        studentsFull = data.students || [];

        // Lấy tổng số phiên điểm danh từ API logs (best effort)
        try {
            const logs = await api.teacherGetAttendanceLogs(CLASS_ID);
            document.getElementById('statSessions').textContent = logs.total_sessions ?? 0;
        } catch (_) {}

        renderStudentTable(studentsFull);
    } catch (e) {
        box.innerHTML = `<div class="alert alert-danger m-3">${e.message}</div>`;
    }
}

/**
 * Render bảng sinh viên với số thứ tự, họ tên, mã SV, trạng thái khuôn mặt, ngày tham gia.
 * @param {Array} students - Mảng sinh viên cần hiển thị
 */
function renderStudentTable(students) {
    const box   = document.getElementById('studentListBody');
    const badge = document.getElementById('studentCountBadge');
    badge.textContent = students.length;

    if (!students.length) {
        box.innerHTML = `<div class="text-center py-5 text-muted">
            <i class="bi bi-people fs-1 d-block mb-2"></i>
            Chưa có sinh viên nào tham gia lớp này.</div>`;
        return;
    }

    const rows = students.map((s, i) => `
        <tr class="student-row">
            <td class="text-muted ps-3">${i + 1}</td>
            <td>
                <div class="fw-semibold">${esc(s.full_name)}</div>
                <div class="text-muted small">${s.email || ''}</div>
            </td>
            <td>${s.student_code || '<span class="text-muted">—</span>'}</td>
            <td>
                ${s.face_registered
                    ? '<span class="badge bg-success"><i class="bi bi-check me-1"></i>Đã đăng ký</span>'
                    : '<span class="badge bg-danger"><i class="bi bi-x me-1"></i>Chưa đăng ký</span>'}
            </td>
            <td class="text-muted small">${s.joined_at ? fmtVN(s.joined_at) : '—'}</td>
        </tr>`).join('');

    box.innerHTML = `
        <table class="table table-hover mb-0">
            <thead class="table-light">
                <tr>
                    <th class="ps-3" style="width:40px">#</th>
                    <th>Họ tên</th>
                    <th>Mã SV</th>
                    <th>Khuôn mặt</th>
                    <th>Ngày tham gia</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>`;
}

/**
 * Lọc danh sách sinh viên theo từ khóa tìm kiếm phía client.
 * Tìm theo: họ tên, mã SV, email.
 */
function filterStudents() {
    const q = document.getElementById('studentSearch').value.toLowerCase();
    const filtered = studentsFull.filter(s =>
        s.full_name.toLowerCase().includes(q) ||
        (s.student_code || '').toLowerCase().includes(q) ||
        (s.email || '').toLowerCase().includes(q)
    );
    renderStudentTable(filtered);
}

// ── Modal chỉnh sửa lớp ───────────────────────────────────────────────────────

/**
 * Mở modal chỉnh sửa thông tin lớp học (tên, mô tả, ngày).
 */
function openEditModal() {
    if (!classData) return;
    document.getElementById('editName').value  = classData.name        || '';
    document.getElementById('editDesc').value  = classData.description || '';
    document.getElementById('editStart').value = classData.start_date  || '';
    document.getElementById('editEnd').value   = classData.end_date    || '';
    document.getElementById('editAlertBox').innerHTML = '';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('editModal')).show();
}

/**
 * Lưu thay đổi thông tin lớp học.
 * Validate ngày tháng và tên không rỗng trước khi gửi API.
 */
async function saveEdit() {
    const alertBox  = document.getElementById('editAlertBox');
    const name      = document.getElementById('editName').value.trim();
    const startDate = document.getElementById('editStart').value;
    const endDate   = document.getElementById('editEnd').value;

    if (!name)             return setAlert(alertBox, 'Tên lớp không được để trống', 'warning');
    if (!startDate)        return setAlert(alertBox, 'Vui lòng chọn ngày bắt đầu', 'warning');
    if (!endDate)          return setAlert(alertBox, 'Vui lòng chọn ngày kết thúc', 'warning');
    if (endDate <= startDate)
        return setAlert(alertBox, 'Ngày kết thúc phải sau ngày bắt đầu', 'warning');

    const btn = document.getElementById('editSaveBtn');
    const sp  = document.getElementById('editSpinner');
    btn.disabled = true; sp.classList.remove('d-none');

    try {
        await api.teacherUpdateClass(CLASS_ID, {
            name,
            description: document.getElementById('editDesc').value.trim() || null,
            start_date:  startDate,
            end_date:    endDate,
        });
        bootstrap.Modal.getOrCreateInstance(document.getElementById('editModal')).hide();
        showAlert('Cập nhật thành công!', 'success');
        loadClassDetail();
    } catch (e) {
        setAlert(alertBox, e.message, 'danger');
    } finally {
        btn.disabled = false; sp.classList.add('d-none');
    }
}

// ── Modal lịch học ────────────────────────────────────────────────────────────

/**
 * Mở modal quản lý lịch học và tải danh sách hiện tại.
 */
function openScheduleModal() {
    document.getElementById('schedAlertBox').innerHTML = '';
    loadSchedList();
    bootstrap.Modal.getOrCreateInstance(document.getElementById('schedModal')).show();
}

/**
 * Tải và render danh sách lịch học hiện tại của lớp trong modal.
 */
async function loadSchedList() {
    const box = document.getElementById('schedListBody');
    box.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm"></div></div>';
    try {
        const data = await api.teacherGetSchedules(CLASS_ID);
        if (!data.schedules?.length) {
            box.innerHTML = '<p class="text-muted mb-0">Chưa có buổi học nào.</p>';
            return;
        }
        const rows = data.schedules.map(s => `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <strong>${s.day_name}</strong>
                    <span class="ms-2 text-muted">${s.start_time} – ${s.end_time}</span>
                    <span class="ms-2 badge bg-light text-dark border">Muộn sau ${s.late_after_minutes} phút</span>
                </div>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-warning"
                            onclick="editSched(${s.day_of_week},'${s.start_time}','${s.end_time}',${s.late_after_minutes})">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger" onclick="deleteSched(${s.id})">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>`).join('');
        box.innerHTML = rows;
    } catch (e) {
        box.innerHTML = `<div class="alert alert-danger py-2">${e.message}</div>`;
    }
}

/**
 * Điền dữ liệu lịch học vào form để sửa.
 * Mở modal nếu chưa mở.
 */
function editSched(day, start, end, late) {
    document.getElementById('newDay').value   = day;
    document.getElementById('newStart').value = start;
    document.getElementById('newEnd').value   = end;
    document.getElementById('newLate').value  = late;
    // Mở modal nếu chưa mở
    if (!document.getElementById('schedModal').classList.contains('show'))
        openScheduleModal();
}

/**
 * Lưu lịch học (tạo mới hoặc cập nhật theo thứ).
 * Tải lại cả danh sách modal và thông tin lớp inline.
 */
async function saveSched() {
    const alertBox = document.getElementById('schedAlertBox');
    alertBox.innerHTML = '';
    try {
        await api.teacherSaveSchedule(CLASS_ID, {
            day_of_week:        parseInt(document.getElementById('newDay').value),
            start_time:         document.getElementById('newStart').value,
            end_time:           document.getElementById('newEnd').value,
            late_after_minutes: parseInt(document.getElementById('newLate').value) || 15,
        });
        setAlert(alertBox, 'Lưu lịch thành công!', 'success');
        loadSchedList();
        loadClassDetail(); // Cập nhật lại lịch hiển thị inline
    } catch (e) {
        setAlert(alertBox, e.message, 'danger');
    }
}

/**
 * Xóa một buổi học khỏi lịch sau khi xác nhận.
 * @param {number} schedId - ID bản ghi lịch học
 */
async function deleteSched(schedId) {
    if (!confirm('Xoá buổi học này?')) return;
    try {
        await api.teacherDeleteSchedule(CLASS_ID, schedId);
        loadSchedList();
        loadClassDetail();
    } catch (e) {
        setAlert(document.getElementById('schedAlertBox'), e.message, 'danger');
    }
}

// ── Tiện ích ──────────────────────────────────────────────────────────────────

/**
 * Sao chép mã lớp vào clipboard và hiện thông báo.
 */
function copyCode(code) {
    navigator.clipboard.writeText(code)
        .then(() => showAlert(`Đã sao chép mã lớp: ${code}`, 'success'));
}

/** Hiện Bootstrap alert trong #alertBox, tự đóng sau 4 giây. */
function showAlert(msg, type = 'info') {
    const box = document.getElementById('alertBox');
    box.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
        ${msg}<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
    setTimeout(() => box.innerHTML = '', 4000);
}

/** Đặt alert trong một phần tử DOM cụ thể (dùng trong modal). */
function setAlert(el, msg, type = 'danger') {
    el.innerHTML = `<div class="alert alert-${type} py-2 mb-0">${msg}</div>`;
}

/** Escape HTML để ngăn XSS. */
function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

/**
 * Parse chuỗi YYYY-MM-DD thành đối tượng Date theo múi giờ cục bộ.
 * Tránh vấn đề UTC midnight shift khi parse ISO date string.
 */
function parseLocalDate(iso) {
    if (!iso) return null;
    const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
    return (y && m && d) ? new Date(y, m - 1, d) : null;
}

/**
 * Định dạng chuỗi ngày ISO thành ngày tháng Việt Nam.
 */
function fmtVN(iso) {
    if (!iso) return '—';
    const d = parseLocalDate(iso) || new Date(iso);
    return isNaN(d) ? iso : d.toLocaleDateString('vi-VN');
}
