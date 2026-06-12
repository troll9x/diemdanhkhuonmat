/**
 * Module Quản Lý Lớp Học (Teacher Classes)
 * Cho phép giảng viên:
 *   - Xem danh sách lớp học dưới dạng card
 *   - Tạo mới / sửa / xóa lớp học
 *   - Quản lý thời khóa biểu (lịch học theo ngày trong tuần)
 *   - Xem danh sách sinh viên trong lớp
 *   - Sao chép mã lớp vào clipboard
 *   - Nút điểm danh đầu giờ / cuối giờ trực tiếp từ card
 */

// Tên các thứ trong tuần (ánh xạ từ day_of_week: 0=Thứ 2 … 6=Chủ nhật)
const DAY_NAMES = ['Thứ 2','Thứ 3','Thứ 4','Thứ 5','Thứ 6','Thứ 7','Chủ nhật'];

// ID lớp đang được chỉnh sửa lịch học (dùng trong modal lịch)
let currentClassId = null;

// Bộ đếm hàng lịch học trong form tạo lớp (để tạo ID duy nhất cho từng hàng)
let schedRowCount  = 0;

// ── Khởi động ──────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    // Điền ngày bắt đầu = hôm nay, ngày kết thúc = +6 tháng làm giá trị mặc định
    const today = new Date();
    const plus6 = new Date(today); plus6.setMonth(plus6.getMonth() + 6);
    document.getElementById('classStartDate').value = fmtDate(today);
    document.getElementById('classEndDate').value   = fmtDate(plus6);
    // Thêm một hàng lịch học mặc định vào form tạo lớp
    addSchedRow();
    loadClasses();
});

/**
 * Chuyển đối tượng Date thành chuỗi YYYY-MM-DD cho input[type=date].
 */
function fmtDate(d) {
    return d.toISOString().slice(0, 10);
}

// ── Quản lý hàng lịch học động ─────────────────────────────────────────────────

/**
 * Thêm một hàng lịch học vào form tạo lớp.
 * Mỗi hàng có: Thứ (select), giờ bắt đầu, giờ kết thúc, ngưỡng muộn (phút).
 * Hàng mặc định: Thứ 2, 07:30–09:30, muộn sau 15 phút.
 */
function addSchedRow() {
    schedRowCount++;
    const id = schedRowCount;
    const div = document.createElement('div');
    div.className = 'sched-row';
    div.id = `schedRow${id}`;
    div.innerHTML = `
        <div class="row g-2 align-items-end">
            <div class="col-md-3">
                <label class="form-label small fw-semibold mb-1">Thứ</label>
                <select class="form-select form-select-sm" name="sched_day">
                    ${DAY_NAMES.map((n, i) => `<option value="${i}"${i===0?' selected':''}>${n}</option>`).join('')}
                </select>
            </div>
            <div class="col-md-3">
                <label class="form-label small fw-semibold mb-1">Giờ bắt đầu</label>
                <input type="time" class="form-control form-control-sm" name="sched_start" value="07:30">
            </div>
            <div class="col-md-3">
                <label class="form-label small fw-semibold mb-1">Giờ kết thúc</label>
                <input type="time" class="form-control form-control-sm" name="sched_end" value="09:30">
            </div>
            <div class="col-md-2">
                <label class="form-label small fw-semibold mb-1">Muộn (phút)</label>
                <input type="number" class="form-control form-control-sm" name="sched_late" value="15" min="1" max="120">
            </div>
            <div class="col-md-1 text-end">
                <button type="button" class="btn btn-outline-danger btn-sm"
                        onclick="removeSchedRow(${id})" title="Xoá">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>`;
    document.getElementById('schedRows').appendChild(div);
}

/**
 * Xoá một hàng lịch học khỏi form tạo lớp.
 * @param {number} id - ID của hàng cần xoá
 */
function removeSchedRow(id) {
    const el = document.getElementById(`schedRow${id}`);
    if (el) el.remove();
}

/**
 * Thu thập tất cả hàng lịch học từ form tạo lớp thành mảng object.
 * @returns {Array<{day_of_week, start_time, end_time, late_after_minutes}>}
 */
function collectSchedules() {
    const rows = document.querySelectorAll('#schedRows .sched-row');
    const result = [];
    for (const row of rows) {
        result.push({
            day_of_week:        parseInt(row.querySelector('[name=sched_day]').value),
            start_time:         row.querySelector('[name=sched_start]').value,
            end_time:           row.querySelector('[name=sched_end]').value,
            late_after_minutes: parseInt(row.querySelector('[name=sched_late]').value) || 15,
        });
    }
    return result;
}

// ── Tải danh sách lớp ─────────────────────────────────────────────────────────

/**
 * Tải và render danh sách lớp học dưới dạng card lưới.
 * Hiện nút mở phiên điểm danh đầu/cuối giờ tùy theo trạng thái phiên hôm nay.
 */
async function loadClasses() {
    const list = document.getElementById('classList');
    try {
        const data = await api.teacherGetClasses();
        if (!data.classes || data.classes.length === 0) {
            list.innerHTML = `<div class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-1 d-block mb-2"></i>Chưa có lớp học nào.
                <br><button class="btn btn-primary mt-3"
                            data-bs-toggle="modal" data-bs-target="#createClassModal">
                    <i class="bi bi-plus-circle me-2"></i>Tạo lớp đầu tiên
                </button></div>`;
            return;
        }
        list.innerHTML = `<div class="row g-3">${data.classes.map(classCard).join('')}</div>`;
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">Lỗi tải dữ liệu: ${e.message}</div>`;
    }
}

/**
 * Tạo HTML cho một card lớp học.
 * Hiển thị: tên lớp, mã lớp (có thể sao chép), mô tả, khoảng thời gian,
 * lịch học, số sinh viên, nút điểm danh đầu/cuối giờ.
 * Logic nút điểm danh:
 *   - Chưa có phiên đầu giờ: nút xanh "Đầu giờ"
 *   - Phiên đầu giờ đang mở: nút vàng "Đầu giờ…"
 *   - Đã đóng phiên đầu giờ: nút xám disabled "Đầu giờ ✓"
 *   - Tương tự cho phiên cuối giờ (chỉ hiện sau khi đã mở đầu giờ)
 * @param {object} c - Dữ liệu lớp học từ API
 * @returns {string} HTML card
 */
function classCard(c) {
    // Chuỗi khoảng thời gian khóa học
    const dateRange = (c.start_date && c.end_date)
        ? `${fmtVN(c.start_date)} — ${fmtVN(c.end_date)}`
        : '<span class="text-muted">Chưa đặt ngày</span>';

    // Tóm tắt lịch học: badge cho từng thứ + giờ
    const schedSummary = c.schedules && c.schedules.length
        ? c.schedules.map(s => `<span class="badge bg-light text-dark border me-1">
              ${s.day_name} ${s.start_time}–${s.end_time}
          </span>`).join('')
        : '<span class="text-muted small">Chưa có lịch</span>';

    // Phân tích trạng thái phiên điểm danh hôm nay
    const types    = c.today_sessions.map(s => s.session_type);
    const openSess = c.today_sessions.filter(s => s.status === 'open');

    // Xây dựng nút điểm danh
    let attBtns = '';
    if (!types.includes('start')) {
        // Chưa mở phiên đầu giờ → nút xanh
        attBtns += btnLink(c.id, 'success', 'play-circle', 'Đầu giờ');
    } else if (openSess.some(s => s.session_type === 'start')) {
        // Phiên đầu giờ đang mở → nút vàng "đang phát"
        attBtns += btnLink(c.id, 'warning', 'broadcast', 'Đầu giờ…');
    } else {
        // Phiên đầu giờ đã đóng → disabled
        attBtns += `<a href="/teacher/classes/${c.id}/attendance"
                       class="btn btn-sm btn-outline-secondary disabled">
                       <i class="bi bi-check me-1"></i>Đầu giờ ✓</a>`;
    }

    // Nút cuối giờ chỉ hiện sau khi đã mở đầu giờ
    if (types.includes('start') && !types.includes('end')) {
        attBtns += btnLink(c.id, 'info', 'stop-circle', 'Cuối giờ', 'ms-1');
    } else if (openSess.some(s => s.session_type === 'end')) {
        attBtns += btnLink(c.id, 'warning', 'broadcast', 'Cuối giờ…', 'ms-1');
    } else if (types.includes('end')) {
        attBtns += `<span class="btn btn-sm btn-outline-secondary ms-1 disabled">Cuối giờ ✓</span>`;
    }

    return `<div class="col-md-6 col-lg-4">
        <div class="card h-100">
            <div class="card-body">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h5 class="fw-bold mb-0 me-2" style="font-size:1rem">
                        <a href="/teacher/classes/${c.id}" class="text-decoration-none text-dark stretched-link-title">
                            ${esc(c.name)}
                        </a>
                    </h5>
                    <span class="badge bg-primary flex-shrink-0" style="cursor:pointer;position:relative;z-index:1"
                          onclick="copyCode('${c.class_code}')" title="Sao chép mã lớp">
                        ${c.class_code} <i class="bi bi-copy ms-1"></i>
                    </span>
                </div>

                ${c.description ? `<p class="text-muted small mb-2">${esc(c.description)}</p>` : ''}

                <p class="mb-1 small">
                    <i class="bi bi-calendar-range me-1 text-secondary"></i>
                    <strong>Khoá học:</strong> ${dateRange}
                </p>
                <div class="mb-2 small">
                    <i class="bi bi-calendar3 me-1 text-secondary"></i>
                    <strong>Lịch học:</strong> ${schedSummary}
                </div>
                <p class="mb-3 small">
                    <i class="bi bi-people me-1 text-secondary"></i>${c.student_count} sinh viên
                </p>

                <div class="d-flex gap-1 flex-wrap">
                    ${attBtns}
                    <button class="btn btn-sm btn-outline-info"
                            onclick="showSchedule(${c.id}, '${esc(c.name)}')">
                        <i class="bi bi-calendar3 me-1"></i>Lịch
                    </button>
                    <button class="btn btn-sm btn-outline-primary"
                            onclick="showStudents(${c.id}, '${esc(c.name)}')">
                        <i class="bi bi-people me-1"></i>SV
                    </button>
                    <a href="/teacher/classes/${c.id}/attendance"
                       class="btn btn-sm btn-outline-secondary">
                        <i class="bi bi-clock-history me-1"></i>Log
                    </a>
                </div>
            </div>
            <div class="card-footer d-flex justify-content-between align-items-center">
                <span class="text-muted small">Tạo ngày ${fmtVN(c.created_at)}</span>
                <div class="d-flex gap-1">
                    <button class="btn btn-sm btn-outline-warning"
                            onclick="editClass(${c.id})"
                            title="Chỉnh sửa lớp học">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-sm btn-outline-danger"
                            onclick="deleteClass(${c.id}, '${esc(c.name)}')"
                            title="Xoá lớp học">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </div>
        </div>
    </div>`;
}

/**
 * Tạo nút liên kết đến trang điểm danh của lớp.
 * @param {number} cid   - ID lớp
 * @param {string} color - Bootstrap màu button (success/warning/info/...)
 * @param {string} icon  - Bootstrap icon name
 * @param {string} label - Nhãn hiển thị
 * @param {string} extra - Class CSS bổ sung (ví dụ: 'ms-1')
 */
function btnLink(cid, color, icon, label, extra = '') {
    return `<a href="/teacher/classes/${cid}/attendance"
               class="btn btn-sm btn-${color} ${extra}">
               <i class="bi bi-${icon} me-1"></i>${label}
           </a>`;
}

// ── Sửa / Xóa lớp ─────────────────────────────────────────────────────────────

/**
 * Mở modal chỉnh sửa thông tin lớp học.
 * Tải dữ liệu lớp từ API và điền vào form.
 * @param {number} classId - ID lớp cần sửa
 */
async function editClass(classId) {
    try {
        const data = await api.teacherGetClass(classId);
        document.getElementById('editClassId').value    = classId;
        document.getElementById('editClassName').value  = data.name || '';
        document.getElementById('editClassDesc').value  = data.description || '';
        document.getElementById('editStartDate').value  = data.start_date || '';
        document.getElementById('editEndDate').value    = data.end_date   || '';
        document.getElementById('editAlertBox').innerHTML = '';
        bootstrap.Modal.getOrCreateInstance(document.getElementById('editClassModal')).show();
    } catch (e) {
        showAlert('Không tải được thông tin lớp: ' + e.message, 'danger');
    }
}

/**
 * Lưu thay đổi thông tin lớp học (tên, mô tả, ngày bắt đầu/kết thúc).
 * Validate phía client trước khi gửi API.
 */
async function saveEditClass() {
    const alertBox = document.getElementById('editAlertBox');
    const classId   = document.getElementById('editClassId').value;
    const name      = document.getElementById('editClassName').value.trim();
    const desc      = document.getElementById('editClassDesc').value.trim();
    const startDate = document.getElementById('editStartDate').value;
    const endDate   = document.getElementById('editEndDate').value;

    if (!name)      return setAlert(alertBox, 'Tên lớp không được để trống', 'warning');
    if (!startDate) return setAlert(alertBox, 'Vui lòng chọn ngày bắt đầu', 'warning');
    if (!endDate)   return setAlert(alertBox, 'Vui lòng chọn ngày kết thúc', 'warning');
    if (endDate <= startDate)
        return setAlert(alertBox, 'Ngày kết thúc phải sau ngày bắt đầu', 'warning');

    const btn = document.getElementById('editSaveBtn');
    const sp  = document.getElementById('editSaveSpinner');
    btn.disabled = true; sp.classList.remove('d-none');

    try {
        await api.teacherUpdateClass(classId, {
            name,
            description: desc || null,
            start_date:  startDate,
            end_date:    endDate,
        });
        bootstrap.Modal.getOrCreateInstance(document.getElementById('editClassModal')).hide();
        showAlert('Cập nhật lớp học thành công!', 'success');
        loadClasses();
    } catch (e) {
        setAlert(alertBox, e.message, 'danger');
    } finally {
        btn.disabled = false; sp.classList.add('d-none');
    }
}

/**
 * Xóa lớp học sau khi xác nhận.
 * Nếu lớp đã có dữ liệu điểm danh (không thể xóa), đề xuất deactivate thay thế.
 * @param {number} classId   - ID lớp cần xóa
 * @param {string} className - Tên lớp để hiển thị trong confirm dialog
 */
async function deleteClass(classId, className) {
    if (!confirm(`Xoá lớp "${className}"?\n\nHành động này không thể hoàn tác. Chỉ xoá được lớp chưa có dữ liệu điểm danh.`))
        return;

    try {
        await api.teacherDeleteClass(classId);
        showAlert(`Đã xoá lớp "${className}"`, 'success');
        loadClasses();
    } catch (e) {
        // Nếu lớp đã có điểm danh, đề xuất deactivate thay vì xóa
        if (e.message && e.message.includes('dữ liệu điểm danh')) {
            if (confirm(e.message + '\n\nBạn có muốn huỷ kích hoạt lớp này thay thế không?')) {
                try {
                    await api.teacherToggleClass(classId);
                    showAlert('Đã huỷ kích hoạt lớp học', 'warning');
                    loadClasses();
                } catch (e2) {
                    showAlert(e2.message, 'danger');
                }
            }
        } else {
            showAlert(e.message, 'danger');
        }
    }
}

// ── Tạo lớp mới ───────────────────────────────────────────────────────────────

/**
 * Tạo lớp học mới từ form trong modal.
 * Validate: tên không rỗng, ngày hợp lệ, có ít nhất 1 lịch học, không trùng thứ.
 */
async function createClass() {
    const alertBox = document.getElementById('createAlertBox');
    alertBox.innerHTML = '';

    const name      = document.getElementById('className').value.trim();
    const desc      = document.getElementById('classDesc').value.trim();
    const startDate = document.getElementById('classStartDate').value;
    const endDate   = document.getElementById('classEndDate').value;
    const schedules = collectSchedules();

    if (!name)      return setAlert(alertBox, 'Vui lòng nhập tên lớp', 'warning');
    if (!startDate) return setAlert(alertBox, 'Vui lòng chọn ngày bắt đầu', 'warning');
    if (!endDate)   return setAlert(alertBox, 'Vui lòng chọn ngày kết thúc', 'warning');
    if (endDate <= startDate) return setAlert(alertBox, 'Ngày kết thúc phải sau ngày bắt đầu', 'warning');
    if (schedules.length === 0) return setAlert(alertBox, 'Vui lòng thêm ít nhất một buổi học', 'warning');

    // Kiểm tra không có 2 buổi cùng thứ
    const days = schedules.map(s => s.day_of_week);
    if (new Set(days).size !== days.length)
        return setAlert(alertBox, 'Mỗi thứ chỉ được có một buổi học', 'warning');

    const btn = document.getElementById('createClassBtn');
    const sp  = document.getElementById('createBtnSpinner');
    btn.disabled = true; sp.classList.remove('d-none');

    try {
        await api.teacherCreateClass({
            name, description: desc || undefined,
            start_date: startDate, end_date: endDate,
            schedules,
        });
        bootstrap.Modal.getOrCreateInstance(document.getElementById('createClassModal')).hide();
        // Reset form về trạng thái ban đầu
        document.getElementById('className').value = '';
        document.getElementById('classDesc').value  = '';
        document.getElementById('schedRows').innerHTML = '';
        schedRowCount = 0;
        addSchedRow();
        showAlert('Tạo lớp thành công!', 'success');
        loadClasses();
    } catch (e) {
        setAlert(alertBox, e.message, 'danger');
    } finally {
        btn.disabled = false; sp.classList.add('d-none');
    }
}

// ── Modal danh sách sinh viên ──────────────────────────────────────────────────

/**
 * Mở modal hiển thị danh sách sinh viên trong lớp.
 * @param {number} classId   - ID lớp
 * @param {string} className - Tên lớp để hiển thị trong tiêu đề modal
 */
async function showStudents(classId, className) {
    document.getElementById('studentsModalTitle').textContent = `Sinh viên: ${className}`;
    const list = document.getElementById('studentsList');
    list.innerHTML = '<div class="text-center py-4"><div class="spinner-border"></div></div>';
    bootstrap.Modal.getOrCreateInstance(document.getElementById('studentsModal')).show();
    try {
        const data = await api.teacherGetStudents(classId);
        if (!data.students?.length) {
            list.innerHTML = '<p class="text-muted text-center py-3">Chưa có sinh viên nào.</p>';
            return;
        }
        // Bảng: Họ tên | Mã SV | Email | Trạng thái khuôn mặt
        const rows = data.students.map(s => `<tr>
            <td>${esc(s.full_name)}</td><td>${s.student_code||'—'}</td>
            <td>${s.email||'—'}</td>
            <td>${s.face_registered
                ? '<span class="badge bg-success">Đã đăng ký</span>'
                : '<span class="badge bg-danger">Chưa đăng ký</span>'}</td>
        </tr>`).join('');
        list.innerHTML = `<table class="table table-sm">
            <thead><tr><th>Họ tên</th><th>Mã SV</th><th>Email</th><th>Khuôn mặt</th></tr></thead>
            <tbody>${rows}</tbody></table>`;
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    }
}

// ── Modal thời khóa biểu ───────────────────────────────────────────────────────

/**
 * Mở modal quản lý lịch học của một lớp cụ thể.
 * @param {number} classId   - ID lớp
 * @param {string} className - Tên lớp
 */
async function showSchedule(classId, className) {
    currentClassId = classId;
    document.getElementById('scheduleModalTitle').innerHTML =
        `<i class="bi bi-calendar3 me-2"></i>Thời khóa biểu: ${esc(className)}`;
    bootstrap.Modal.getOrCreateInstance(document.getElementById('scheduleModal')).show();
    loadSchedules();
}

/**
 * Tải và render danh sách lịch học hiện tại của lớp đang chọn.
 */
async function loadSchedules() {
    const list = document.getElementById('scheduleList');
    list.innerHTML = '<div class="text-center py-2"><div class="spinner-border spinner-border-sm"></div></div>';
    try {
        const data = await api.teacherGetSchedules(currentClassId);
        if (!data.schedules?.length) {
            list.innerHTML = '<p class="text-muted mb-3">Chưa có lịch học. Thêm bên dưới.</p>';
            return;
        }
        const rows = data.schedules.map(s => `<tr>
            <td><strong>${s.day_name}</strong></td>
            <td>${s.start_time} – ${s.end_time}</td>
            <td>Muộn sau ${s.late_after_minutes} phút</td>
            <td>
                <button class="btn btn-sm btn-outline-primary me-1"
                        onclick="editSched(${s.day_of_week},'${s.start_time}','${s.end_time}',${s.late_after_minutes})">
                    <i class="bi bi-pencil"></i></button>
                <button class="btn btn-sm btn-outline-danger"
                        onclick="deleteSched(${s.id})">
                    <i class="bi bi-trash"></i></button>
            </td></tr>`).join('');
        list.innerHTML = `<table class="table table-sm mb-3">
            <thead><tr><th>Thứ</th><th>Thời gian</th><th>Ngưỡng muộn</th><th></th></tr></thead>
            <tbody>${rows}</tbody></table>`;
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    }
}

/**
 * Điền dữ liệu lịch học vào form để sửa.
 * @param {number} day   - day_of_week (0=Thứ 2)
 * @param {string} start - Giờ bắt đầu HH:MM
 * @param {string} end   - Giờ kết thúc HH:MM
 * @param {number} late  - Ngưỡng muộn tính bằng phút
 */
function editSched(day, start, end, late) {
    document.getElementById('schedDay').value   = day;
    document.getElementById('schedStart').value = start;
    document.getElementById('schedEnd').value   = end;
    document.getElementById('schedLate').value  = late;
}

/**
 * Lưu lịch học (tạo mới hoặc cập nhật nếu đã tồn tại cùng thứ).
 * Tải lại danh sách lịch và danh sách lớp sau khi lưu thành công.
 */
async function saveSchedule() {
    document.getElementById('scheduleAlertBox').innerHTML = '';
    try {
        await api.teacherSaveSchedule(currentClassId, {
            day_of_week:        parseInt(document.getElementById('schedDay').value),
            start_time:         document.getElementById('schedStart').value,
            end_time:           document.getElementById('schedEnd').value,
            late_after_minutes: parseInt(document.getElementById('schedLate').value) || 15,
        });
        setAlert(document.getElementById('scheduleAlertBox'), 'Lưu lịch thành công!', 'success');
        loadSchedules(); loadClasses();
    } catch (e) {
        setAlert(document.getElementById('scheduleAlertBox'), e.message, 'danger');
    }
}

/**
 * Xóa một buổi học khỏi lịch sau khi xác nhận.
 * @param {number} schedId - ID bản ghi lịch học
 */
async function deleteSched(schedId) {
    if (!confirm('Xoá lịch học này?')) return;
    try {
        await api.teacherDeleteSchedule(currentClassId, schedId);
        loadSchedules(); loadClasses();
    } catch (e) {
        setAlert(document.getElementById('scheduleAlertBox'), e.message, 'danger');
    }
}

// ── Tiện ích ──────────────────────────────────────────────────────────────────

/**
 * Sao chép mã lớp vào clipboard và hiện thông báo xác nhận.
 * @param {string} code - Mã lớp cần sao chép
 */
function copyCode(code) {
    navigator.clipboard.writeText(code)
        .then(() => showAlert(`Đã sao chép mã lớp: ${code}`, 'success'));
}

/**
 * Hiện Bootstrap alert trong #alertBox, tự đóng sau 4 giây.
 * @param {string} msg  - Nội dung thông báo
 * @param {string} type - Loại alert Bootstrap
 */
function showAlert(msg, type = 'info') {
    const box = document.getElementById('alertBox');
    box.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
        ${msg}<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
    setTimeout(() => box.innerHTML = '', 4000);
}

/**
 * Đặt thông báo lỗi trong một phần tử DOM cụ thể (dùng trong modal).
 * @param {HTMLElement} el  - Phần tử chứa alert
 * @param {string}      msg - Nội dung thông báo
 * @param {string}      type - Loại Bootstrap alert
 */
function setAlert(el, msg, type = 'danger') {
    el.innerHTML = `<div class="alert alert-${type} py-2">${msg}</div>`;
}

/**
 * Escape HTML để ngăn XSS.
 */
function esc(str) {
    return String(str||'').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

/**
 * Định dạng chuỗi ISO date thành ngày tháng Việt Nam.
 * @param {string} iso - Chuỗi ngày ISO (YYYY-MM-DD hoặc ISO datetime)
 * @returns {string} Chuỗi ngày vi-VN hoặc '—'
 */
function fmtVN(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    return isNaN(d) ? iso : d.toLocaleDateString('vi-VN');
}
