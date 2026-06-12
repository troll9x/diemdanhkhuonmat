/**
 * Module Dashboard Giảng Viên (Teacher Dashboard)
 * Hiển thị:
 *   - Lời chào cá nhân hoá với ngày tháng
 *   - Thống kê: tổng lớp, tổng sinh viên, phiên hôm nay, phiên đang mở
 *   - Lịch sử điểm danh gần đây
 *   - Bảng hôm nay (lớp có lịch dạy hôm nay và trạng thái điểm danh)
 *   - FullCalendar tháng/tuần/danh sách với màu sắc theo lớp và tooltip
 */
'use strict';

// Bảng màu Bootstrap cho lịch — mỗi lớp được gán một màu theo thứ tự
const PALETTE = [
    '#4e73df','#1cc88a','#36b9cc','#f6c23e',
    '#e74a3b','#6f42c1','#fd7e14','#20c997',
];

// Tên thứ trong tuần tiếng Việt — getDay() trả về 0=Chủ Nhật
const DAY_VI = ['CN','T2','T3','T4','T5','T6','T7'];

// Instance FullCalendar
let calendar = null;

// Ánh xạ class_id → màu hex để tô nhất quán giữa lịch và legend
let classColorMap = {};

// Danh sách tất cả lớp (dùng cho bảng hôm nay và bản đồ màu)
let allClasses   = [];

// ── Khởi động ─────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', async () => {
    // Lời chào với ngày tháng đầy đủ
    const user = auth.getUser();
    if (user) {
        document.getElementById('welcomeMsg').textContent =
            `Xin chào, ${user.name || user.full_name || ''}! Hôm nay là ${
                new Date().toLocaleDateString('vi-VN', {weekday:'long', day:'numeric', month:'long', year:'numeric'})
            }`;
    }

    // Tải thống kê và danh sách lớp song song
    await Promise.all([loadStats(), loadClassList()]);

    // Khởi tạo lịch sau khi đã có danh sách lớp (cần bảng màu)
    initCalendar();

    // Tải bảng hôm nay
    loadTodayPanel();
});

// ── Thống kê tổng quan ────────────────────────────────────────────────────────

/**
 * Tải dữ liệu thống kê dashboard và render bảng điểm danh gần đây.
 */
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

/**
 * Render danh sách điểm danh gần đây vào box #recentAttendance.
 * Mỗi dòng hiện tên sinh viên, tên lớp, badge trạng thái và giờ điểm danh.
 * @param {Array} records - Mảng bản ghi điểm danh từ API
 */
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

// ── Danh sách lớp học ─────────────────────────────────────────────────────────

/**
 * Tải danh sách tất cả lớp, gán màu và xây dựng chú thích màu trên lịch.
 */
async function loadClassList() {
    try {
        const data = await api.teacherGetClasses();
        allClasses = data.classes || [];
        // Gán màu theo thứ tự trong PALETTE (lặp vòng nếu vượt 8 lớp)
        allClasses.forEach((c, i) => {
            classColorMap[c.id] = PALETTE[i % PALETTE.length];
        });
        buildLegend();
    } catch (e) {
        console.error('loadClassList', e);
    }
}

/**
 * Xây dựng chú thích màu (legend) bên dưới lịch — hiện tên lớp với chấm màu.
 */
function buildLegend() {
    const legend = document.getElementById('calLegend');
    legend.innerHTML = allClasses.map(c => `
        <span class="d-flex align-items-center gap-1" style="font-size:.75rem">
            <span style="width:10px;height:10px;border-radius:50%;background:${classColorMap[c.id]};flex-shrink:0"></span>
            ${esc(c.name)}
        </span>`).join('');
}

// ── Bảng hôm nay ─────────────────────────────────────────────────────────────

/**
 * Hiển thị danh sách lớp có lịch dạy hôm nay trong bảng Today Panel.
 * Chuyển đổi JS getDay() (0=CN) sang Python weekday (0=Thứ 2).
 * Hiển thị giờ học, số sinh viên, trạng thái điểm danh đầu/cuối giờ.
 */
function loadTodayPanel() {
    const box = document.getElementById('todaySchedule');
    const today = new Date();
    const dow   = today.getDay(); // 0=CN theo JS
    // Chuyển đổi: JS getDay 0=CN → Python weekday 0=Thứ 2
    const apiDow = dow === 0 ? 6 : dow - 1;

    // Lọc các lớp có lịch học hôm nay
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

        // Kiểm tra đã mở phiên đầu giờ / cuối giờ chưa
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

/**
 * Khởi tạo và render FullCalendar.
 * Cấu hình: tiếng Việt, bắt đầu tuần từ Thứ 2, 3 chế độ xem (tháng/tuần/danh sách).
 * Sự kiện được lấy từ API cho khoảng thời gian đang hiển thị.
 * Mỗi sự kiện được tô màu theo lớp từ classColorMap.
 */
function initCalendar() {
    const el = document.getElementById('teacherCalendar');
    if (!el || typeof FullCalendar === 'undefined') return;

    calendar = new FullCalendar.Calendar(el, {
        initialView: 'dayGridMonth',
        locale: 'vi',
        height: 'auto',
        firstDay: 1, // Bắt đầu tuần từ Thứ 2
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
        dayMaxEvents: 3, // Hiện tối đa 3 sự kiện mỗi ngày, còn lại gộp thành "+N more"

        // Lấy sự kiện từ backend cho khoảng thời gian đang hiển thị
        events: async (info, successCb, failureCb) => {
            try {
                const start = info.startStr.slice(0, 10);
                const end   = info.endStr.slice(0, 10);
                const data  = await api.teacherGetCalendar(start, end);
                // Ghi đè màu từ backend bằng màu trong classColorMap để đồng nhất
                const events = data.events.map(ev => ({
                    ...ev,
                    color: classColorMap[ev.extendedProps?.class_id] || ev.color,
                }));
                successCb(events);
            } catch (e) {
                failureCb(e);
            }
        },

        // Tùy chỉnh hiển thị sự kiện — thêm chấm trạng thái điểm danh
        eventContent(arg) {
            const p = arg.event.extendedProps || {};
            let dotsHtml = '';
            if (p.has_start_session)
                dotsHtml += '<span class="fc-event-att att-start" title="Đã điểm danh đầu giờ"></span>';
            if (p.has_end_session)
                dotsHtml += '<span class="fc-event-att att-end" title="Đã điểm danh cuối giờ"></span>';

            // Chế độ xem tháng: hiện giờ bắt đầu ngắn gọn
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

        // Tooltip khi di chuột vào sự kiện — hiện chi tiết lớp và trạng thái điểm danh
        eventMouseEnter(info) {
            const p = info.event.extendedProps || {};
            const color = info.event.backgroundColor || '#4e73df';
            const d = info.event.start;
            const dateStr = d ? d.toLocaleDateString('vi-VN', {
                weekday:'long', day:'numeric', month:'long', year:'numeric',
            }) : '';

            // Badge trạng thái điểm danh trong tooltip
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

            // Vị trí tooltip: bên dưới sự kiện, căn vào cạnh phải nếu quá rộng
            const rect = info.el.getBoundingClientRect();
            tip.style.display = 'block';
            tip.style.left = Math.min(rect.left, window.innerWidth - 275) + 'px';
            tip.style.top  = (rect.bottom + 8 + window.scrollY) + 'px';
        },

        // Ẩn tooltip khi rời khỏi sự kiện
        eventMouseLeave() {
            document.getElementById('calTooltip').style.display = 'none';
        },

        // Click vào sự kiện → chuyển đến trang điểm danh của lớp đó
        eventClick(info) {
            const classId = info.event.extendedProps?.class_id;
            if (classId) window.location.href = `/teacher/classes/${classId}/attendance`;
        },
    });

    calendar.render();
}

// ── Tiện ích ──────────────────────────────────────────────────────────────────

/**
 * Escape HTML để ngăn XSS khi chèn chuỗi từ server vào innerHTML.
 */
function esc(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Ẩn tooltip khi click ra ngoài lịch
document.addEventListener('click', () => {
    document.getElementById('calTooltip').style.display = 'none';
});
