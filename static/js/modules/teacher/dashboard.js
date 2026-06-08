// Teacher Dashboard JS — FullCalendar + stats + today panel
'use strict';

const PALETTE = [
    '#4e73df','#1cc88a','#36b9cc','#f6c23e',
    '#e74a3b','#6f42c1','#fd7e14','#20c997',
];
const DAY_VI = ['CN','T2','T3','T4','T5','T6','T7'];  // getDay() = 0=Sun

let calendar = null;
let classColorMap = {};   // class_id -> color
let allClasses   = [];

// ── Boot ──────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Welcome message
    const user = auth.getUser();
    if (user) {
        document.getElementById('welcomeMsg').textContent =
            `Xin chào, ${user.name || user.full_name || ''}! Hôm nay là ${
                new Date().toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long', year:'numeric'})
            }`;
    }

    // Load dashboard stats + class list in parallel
    await Promise.all([loadStats(), loadClassList()]);

    // Build calendar after we know the classes (for color map)
    initCalendar();

    // Today panel
    loadTodayPanel();
});

// ── Stats ─────────────────────────────────────────────────────────────────────

async function loadStats() {
    try {
        const data = await api.teacherDashboard();
        document.getElementById('totalClasses').textContent  = data.total_classes   ?? 0;
        document.getElementById('totalStudents').textContent = data.total_students  ?? 0;
        document.getElementById('todaySessions').textContent = data.today_sessions  ?? 0;
        document.getElementById('openSessions').textContent  = data.open_sessions   ?? 0;

        renderRecentAttendance(data.recent_attendance || []);
    } catch (e) {
        console.error('loadStats', e);
    }
}

function renderRecentAttendance(records) {
    const box = document.getElementById('recentAttendance');
    if (!records.length) {
        box.innerHTML = '<div class="text-center py-3 text-muted small">Chưa có dữ liệu.</div>';
        return;
    }
    box.innerHTML = records.map(r => `
        <div class="d-flex justify-content-between align-items-center px-3 py-2 border-bottom">
            <div>
                <div class="fw-semibold small">${esc(r.student_name)}</div>
                <div class="text-muted" style="font-size:.75rem">
                    ${esc(r.classroom_name)}
                    ${r.session_type_label ? `· ${r.session_type_label}` : ''}
                </div>
            </div>
            <div class="text-end flex-shrink-0 ms-2">
                <span class="badge bg-${r.status === 'present' ? (r.is_late ? 'warning text-dark' : 'success') : 'danger'}">
                    ${r.status === 'present' ? (r.is_late ? 'Muộn' : 'Đúng giờ') : 'Từ chối'}
                </span>
                <div class="text-muted" style="font-size:.7rem">
                    ${new Date(r.checkin_time).toLocaleTimeString('vi-VN', {hour:'2-digit', minute:'2-digit'})}
                </div>
            </div>
        </div>`).join('');
}

// ── Class list (for color map & today panel) ──────────────────────────────────

async function loadClassList() {
    try {
        const data = await api.teacherGetClasses();
        allClasses = data.classes || [];
        allClasses.forEach((c, i) => {
            classColorMap[c.id] = PALETTE[i % PALETTE.length];
        });
        buildLegend();
    } catch (e) {
        console.error('loadClassList', e);
    }
}

function buildLegend() {
    const legend = document.getElementById('calLegend');
    legend.innerHTML = allClasses.map(c => `
        <span class="d-flex align-items-center gap-1" style="font-size:.75rem">
            <span style="width:10px;height:10px;border-radius:50%;background:${classColorMap[c.id]};flex-shrink:0"></span>
            ${esc(c.name)}
        </span>`).join('');
}

// ── Today panel ───────────────────────────────────────────────────────────────

function loadTodayPanel() {
    const box = document.getElementById('todaySchedule');
    const today = new Date();
    const dow   = today.getDay(); // 0=Sun … but our API uses 0=Mon
    // Convert JS getDay (0=Sun) to Python weekday (0=Mon)
    const apiDow = dow === 0 ? 6 : dow - 1;

    const todayClasses = allClasses.filter(c =>
        c.schedules && c.schedules.some(s => s.day_of_week === apiDow)
    );

    if (!todayClasses.length) {
        box.innerHTML = '<div class="px-3 py-3 text-muted small">Hôm nay không có lịch dạy.</div>';
        return;
    }

    box.innerHTML = todayClasses.map(c => {
        const sched = c.schedules.find(s => s.day_of_week === apiDow);
        const color = classColorMap[c.id] || '#4e73df';

        const todaySess = c.today_sessions || [];
        const hasStart  = todaySess.some(s => s.session_type === 'start');
        const hasEnd    = todaySess.some(s => s.session_type === 'end');
        const openSess  = todaySess.find(s => s.status === 'open');

        return `
        <div class="d-flex align-items-start px-3 py-2 border-bottom">
            <div style="width:4px;border-radius:2px;background:${color};margin-right:10px;align-self:stretch;flex-shrink:0"></div>
            <div class="flex-fill min-width-0">
                <div class="fw-semibold text-truncate small">${esc(c.name)}</div>
                <div class="text-muted" style="font-size:.75rem">
                    <i class="bi bi-clock me-1"></i>${sched.start_time}–${sched.end_time}
                    · ${c.student_count} SV
                </div>
                <div class="mt-1">
                    ${hasStart
                        ? '<span class="badge bg-success me-1" style="font-size:.65rem">Đầu giờ ✓</span>'
                        : ''}
                    ${hasEnd
                        ? '<span class="badge bg-info me-1" style="font-size:.65rem">Cuối giờ ✓</span>'
                        : ''}
                    ${!hasStart
                        ? `<a href="/teacher/classes/${c.id}/attendance"
                              class="badge bg-warning text-dark text-decoration-none me-1"
                              style="font-size:.65rem">Chưa điểm danh</a>`
                        : ''}
                </div>
            </div>
        </div>`;
    }).join('');
}

// ── FullCalendar ──────────────────────────────────────────────────────────────

function initCalendar() {
    const el = document.getElementById('teacherCalendar');
    if (!el || typeof FullCalendar === 'undefined') return;

    calendar = new FullCalendar.Calendar(el, {
        initialView: 'dayGridMonth',
        locale: 'vi',
        height: 'auto',
        firstDay: 1,   // Monday first
        headerToolbar: {
            left:   'prev,next today',
            center: 'title',
            right:  'dayGridMonth,timeGridWeek,listMonth',
        },
        buttonText: {
            today:    'Hôm nay',
            month:    'Tháng',
            week:     'Tuần',
            list:     'Danh sách',
        },
        dayMaxEvents: 3,

        // Fetch events from backend for the displayed range
        events: async (info, successCb, failureCb) => {
            try {
                const start = info.startStr.slice(0, 10);
                const end   = info.endStr.slice(0, 10);
                const data  = await api.teacherGetCalendar(start, end);
                // Attach class color from our colorMap (overrides backend color for consistency)
                const events = data.events.map(ev => ({
                    ...ev,
                    color: classColorMap[ev.extendedProps?.class_id] || ev.color,
                }));
                successCb(events);
            } catch (e) {
                failureCb(e);
            }
        },

        // Custom event rendering — add attendance dots
        eventContent(arg) {
            const p = arg.event.extendedProps || {};
            let dotsHtml = '';
            if (p.has_start_session)
                dotsHtml += '<span class="fc-event-att att-start" title="Đã điểm danh đầu giờ"></span>';
            if (p.has_end_session)
                dotsHtml += '<span class="fc-event-att att-end" title="Đã điểm danh cuối giờ"></span>';

            // timeGridWeek view shows time automatically; dayGrid: show abbreviated time
            const isGrid = arg.view.type === 'dayGridMonth';
            const timeStr = isGrid
                ? `<span style="font-size:.7em;opacity:.85">${p.start_time || ''}</span>`
                : '';

            return {
                html: `<div class="fc-event-main-frame" style="padding:1px 3px;overflow:hidden">
                           ${timeStr}
                           <span class="fc-event-title" style="font-weight:600">
                               ${esc(arg.event.title)}
                           </span>
                           ${dotsHtml}
                       </div>`,
            };
        },

        // Tooltip on hover
        eventMouseEnter(info) {
            const p = info.event.extendedProps || {};
            const color = info.event.backgroundColor || '#4e73df';
            const d = info.event.start;
            const dateStr = d ? d.toLocaleDateString('vi-VN', {
                weekday:'long', day:'numeric', month:'long', year:'numeric',
            }) : '';

            const attLines = [];
            if (p.has_start_session) attLines.push('<span class="badge bg-success">Đầu giờ ✓</span>');
            if (p.has_end_session)   attLines.push('<span class="badge bg-info">Cuối giờ ✓</span>');
            if (!p.has_start_session && !p.has_end_session)
                attLines.push('<span class="badge bg-warning text-dark">Chưa điểm danh</span>');

            const tip = document.getElementById('calTooltip');
            tip.innerHTML = `
                <div class="d-flex align-items-center gap-2 mb-2">
                    <span class="cls-dot" style="background:${color}"></span>
                    <strong>${esc(p.class_name || info.event.title)}</strong>
                </div>
                <div class="text-muted small mb-1">${dateStr}</div>
                <div class="mb-1">
                    <i class="bi bi-clock me-1"></i>${p.start_time || ''}–${p.end_time || ''}
                    <span class="ms-2 text-muted">(Muộn sau ${p.late_after_minutes || 15} phút)</span>
                </div>
                <div class="mb-1">
                    <i class="bi bi-people me-1"></i>${p.student_count || 0} sinh viên
                </div>
                <div class="mt-2 d-flex gap-1 flex-wrap">${attLines.join('')}</div>
                <div class="mt-2">
                    <a href="/teacher/classes/${p.class_id}/attendance"
                       class="btn btn-sm btn-outline-primary w-100">
                       <i class="bi bi-clipboard-check me-1"></i>Xem điểm danh
                    </a>
                </div>`;

            const rect = info.el.getBoundingClientRect();
            tip.style.display = 'block';
            tip.style.left = Math.min(rect.left, window.innerWidth - 275) + 'px';
            tip.style.top  = (rect.bottom + 8 + window.scrollY) + 'px';
        },

        eventMouseLeave() {
            document.getElementById('calTooltip').style.display = 'none';
        },

        // Click → navigate to attendance page
        eventClick(info) {
            const classId = info.event.extendedProps?.class_id;
            if (classId) window.location.href = `/teacher/classes/${classId}/attendance`;
        },
    });

    calendar.render();
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Hide tooltip when clicking elsewhere
document.addEventListener('click', () => {
    document.getElementById('calTooltip').style.display = 'none';
});
