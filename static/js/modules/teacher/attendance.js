// Teacher Attendance Page JS
const CLASS_ID = PAGE_CLASS_ID;
const SESSION_LABEL = { start: 'Đầu giờ', end: 'Cuối giờ' };
let pollTimer = null;
let activeTabType = 'start';

// ── Init ──────────────────────────────────────────────────────────────────────

async function init() {
    if (!CLASS_ID) return;
    await loadClassInfo();
    await loadToday();
    // Poll every 10s
    pollTimer = setInterval(loadToday, 10000);
}

async function loadClassInfo() {
    try {
        const data = await api.teacherGetClass(CLASS_ID);
        document.getElementById('classTitle').textContent = data.name;

        // Show today's schedule if available
        if (data.today_schedule) {
            const s = data.today_schedule;
            document.getElementById('classSubtitle').textContent =
                `Hôm nay: ${s.start_time}–${s.end_time}  |  Mã lớp: ${data.class_code}`;
            document.getElementById('lateMinutes').value = s.late_after_minutes;
        } else {
            document.getElementById('classSubtitle').textContent = `Mã lớp: ${data.class_code}`;
        }
    } catch (e) {
        showAlert('Không tải được thông tin lớp: ' + e.message, 'danger');
    }
}

async function loadToday() {
    try {
        const data = await api.teacherGetTodayAttendance(CLASS_ID);
        renderTodaySessions(data);
    } catch (e) {
        showAlert('Lỗi tải dữ liệu: ' + e.message, 'danger');
    }
}

// ── Render sessions ───────────────────────────────────────────────────────────

function renderTodaySessions(data) {
    const sessions = data.sessions || [];
    const enrolled = data.total_enrolled || 0;

    // Summary cards
    const cardBox = document.getElementById('sessionCards');
    if (sessions.length === 0) {
        cardBox.innerHTML = `<div class="col-12">
            <div class="alert alert-info mb-0">
                <i class="bi bi-info-circle me-2"></i>
                Hôm nay chưa có phiên điểm danh nào. Mở phiên bên dưới.
            </div></div>`;
    } else {
        cardBox.innerHTML = sessions.map(s => {
            const pct = enrolled ? Math.round(s.total_attended / enrolled * 100) : 0;
            const statusBadge = s.status === 'open'
                ? '<span class="badge bg-success ms-2">Đang mở</span>'
                : '<span class="badge bg-secondary ms-2">Đã đóng</span>';
            return `<div class="col-md-6">
                <div class="card border-${s.status === 'open' ? 'success' : 'secondary'}">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <h6 class="fw-bold mb-0">
                                <i class="bi bi-${s.session_type === 'start' ? 'play' : 'stop'}-circle me-1"></i>
                                ${SESSION_LABEL[s.session_type] || s.session_type}
                                ${statusBadge}
                            </h6>
                            ${s.status === 'open'
                                ? `<button class="btn btn-danger btn-sm" onclick="closeSession('${s.session_type}')">
                                       <i class="bi bi-stop-circle me-1"></i>Đóng
                                   </button>`
                                : ''}
                        </div>
                        <div class="d-flex gap-3 mb-2">
                            <span><strong>${s.total_attended}</strong>/${enrolled} điểm danh</span>
                            ${s.total_late > 0 ? `<span class="text-warning"><i class="bi bi-clock me-1"></i>${s.total_late} muộn</span>` : ''}
                        </div>
                        <div class="progress" style="height:6px">
                            <div class="progress-bar bg-success" style="width:${pct}%"></div>
                        </div>
                        <div class="d-flex justify-content-between mt-1">
                            <small class="text-muted">Bắt đầu ${new Date(s.started_at).toLocaleTimeString('vi-VN')}</small>
                            <small class="text-muted">${pct}%</small>
                        </div>
                    </div>
                </div>
            </div>`;
        }).join('');
    }

    // Hide start panel if both sessions already exist
    const types = sessions.map(s => s.session_type);
    const hasStart = types.includes('start');
    const hasEnd   = types.includes('end');
    const sel = document.getElementById('sessionTypeSelect');
    // Remove options that already have a session
    Array.from(sel.options).forEach(opt => {
        opt.disabled = types.includes(opt.value);
    });
    // If all types used, disable button
    document.getElementById('startBtn').disabled = hasStart && hasEnd;

    // Tab detail
    if (sessions.length > 0) {
        renderTabs(sessions, enrolled);
        document.getElementById('sessionDetail').style.display = '';
    }
}

function renderTabs(sessions, enrolled) {
    const tabBar = document.getElementById('sessionTabs');
    const tabContent = document.getElementById('sessionTabContent');

    tabBar.innerHTML = sessions.map((s, i) =>
        `<li class="nav-item">
            <button class="nav-link ${i === 0 ? 'active' : ''}"
                    onclick="switchTab('${s.session_type}', this)">
                <i class="bi bi-${s.session_type === 'start' ? 'play' : 'stop'}-circle me-1"></i>
                ${SESSION_LABEL[s.session_type]}
            </button>
        </li>`
    ).join('');

    // Build all tab panes
    tabContent.innerHTML = sessions.map((s, i) => {
        const attended = s.attended || [];
        const absent   = s.absent   || [];
        const lateCount = attended.filter(x => x.is_late).length;
        const onTime    = attended.length - lateCount;

        const attendedRows = attended.map(st => `<tr>
            <td><i class="bi bi-check-circle-fill text-success me-1"></i>${esc(st.full_name)}</td>
            <td>${st.student_code || '—'}</td>
            <td>${st.checkin_time || '—'}</td>
            <td>${st.is_late
                ? '<span class="badge bg-warning text-dark"><i class="bi bi-clock me-1"></i>Muộn</span>'
                : '<span class="badge bg-success">Đúng giờ</span>'}</td>
            <td>${st.distance_meters != null ? st.distance_meters + ' m' : '—'}</td>
        </tr>`).join('');

        const absentRows = absent.map(st => `<tr>
            <td><i class="bi bi-x-circle-fill text-danger me-1"></i>${esc(st.full_name)}</td>
            <td>${st.student_code || '—'}</td>
            <td colspan="3" class="text-muted">—</td>
        </tr>`).join('');

        const summary = `<div class="d-flex gap-3 mb-3">
            <span class="badge bg-success fs-6">${attended.length} có mặt</span>
            <span class="badge bg-danger fs-6">${absent.length} vắng</span>
            ${lateCount > 0 ? `<span class="badge bg-warning text-dark fs-6">${lateCount} muộn</span>` : ''}
            ${onTime > 0 ? `<span class="badge bg-info fs-6">${onTime} đúng giờ</span>` : ''}
        </div>`;

        return `<div class="tab-pane-custom" id="tab-${s.session_type}"
                     style="display:${i === 0 ? '' : 'none'}">
            ${summary}
            <table class="table table-sm table-hover">
                <thead>
                    <tr><th>Sinh viên</th><th>Mã SV</th><th>Giờ vào</th>
                        <th>Đúng giờ?</th><th>Khoảng cách</th></tr>
                </thead>
                <tbody>
                    ${attendedRows}
                    ${absentRows || '<tr><td colspan="5" class="text-center text-success">Tất cả đã điểm danh!</td></tr>'}
                </tbody>
            </table>
        </div>`;
    }).join('');
}

function switchTab(type, btn) {
    activeTabType = type;
    document.querySelectorAll('#sessionTabs .nav-link').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-pane-custom').forEach(p => p.style.display = 'none');
    const pane = document.getElementById(`tab-${type}`);
    if (pane) pane.style.display = '';
}

// ── Start attendance ──────────────────────────────────────────────────────────

async function startAttendance() {
    const btn = document.getElementById('startBtn');
    const sp  = document.getElementById('startSpinner');
    btn.disabled = true; sp.classList.remove('d-none');
    showAlert('Đang lấy vị trí GPS...', 'info');

    const sessionType  = document.getElementById('sessionTypeSelect').value;
    const lateMinutes  = parseInt(document.getElementById('lateMinutes').value) || 15;

    try {
        const pos = await new Promise((res, rej) =>
            navigator.geolocation.getCurrentPosition(res, rej, { timeout: 10000 }));

        const resp = await fetch(`/api/teacher/classes/${CLASS_ID}/attendance/start`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + auth.getToken(),
            },
            body: JSON.stringify({
                session_type:      sessionType,
                late_after_minutes: lateMinutes,
                latitude:          pos.coords.latitude,
                longitude:         pos.coords.longitude,
            }),
        });
        const data = await resp.json();
        if (!resp.ok) throw new Error(data.error || 'Lỗi');

        document.getElementById('alertBox').innerHTML = '';
        showAlert(`Đã mở phiên "${SESSION_LABEL[sessionType]}"!`, 'success');
        loadToday();
    } catch (e) {
        const msg = e.code ? 'Không thể lấy GPS: ' + e.message : e.message;
        showAlert(msg, 'danger');
    } finally {
        btn.disabled = false; sp.classList.add('d-none');
    }
}

// ── Close session ─────────────────────────────────────────────────────────────

async function closeSession(sessionType) {
    if (!confirm(`Đóng phiên "${SESSION_LABEL[sessionType]}"?`)) return;
    try {
        await fetch(`/api/teacher/classes/${CLASS_ID}/attendance/close`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + auth.getToken(),
            },
            body: JSON.stringify({ session_type: sessionType }),
        }).then(r => r.json());
        showAlert(`Phiên "${SESSION_LABEL[sessionType]}" đã đóng`, 'secondary');
        clearInterval(pollTimer);
        loadToday();
        pollTimer = setInterval(loadToday, 10000);
    } catch (e) {
        showAlert(e.message, 'danger');
    }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function showAlert(msg, type = 'info') {
    document.getElementById('alertBox').innerHTML =
        `<div class="alert alert-${type} alert-dismissible fade show">
            ${msg}<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
}

function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

if (CLASS_ID) init();
