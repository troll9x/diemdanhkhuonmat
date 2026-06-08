// Teacher Logs JS
let allClasses = [];

async function init() {
    try {
        const data = await api.teacherGetClasses();
        allClasses = data.classes || [];
        const sel = document.getElementById('classFilter');
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

async function loadLogs() {
    const classId = document.getElementById('classFilter').value;
    const list = document.getElementById('logsList');
    list.innerHTML = '<div class="text-center py-5"><div class="spinner-border"></div></div>';

    if (!classId) {
        // Show all classes summary
        if (allClasses.length === 0) {
            list.innerHTML = '<div class="text-center py-5 text-muted">Chưa có lớp học nào.</div>';
            return;
        }
        const sections = [];
        for (const c of allClasses) {
            try {
                const data = await api.teacherGetAttendanceLogs(c.id);
                if (data.logs && data.logs.length > 0) {
                    sections.push(renderLogsSection(c.name, data.logs));
                }
            } catch (_) {}
        }
        list.innerHTML = sections.length ? sections.join('') :
            '<div class="text-center py-5 text-muted">Chưa có phiên điểm danh nào.</div>';
        return;
    }

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
                    <thead><tr><th>Sinh viên</th><th>Giờ vào</th><th>Trạng thái</th><th>Đúng giờ?</th><th>Khoảng cách</th></tr></thead>
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

function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

init();
