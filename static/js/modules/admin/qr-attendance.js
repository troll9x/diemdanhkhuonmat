/**
 * Module Điểm Danh QR Code (Admin QR Attendance)
 * Cho phép admin tạo và quản lý phiên điểm danh thông qua mã QR.
 * Chỉ hiện các phiên hôm nay và tương lai.
 * Hàm chính:
 *   loadSessionsList()      — Tải danh sách phiên học, lọc phiên từ hôm nay trở đi
 *   showQRCode(sessionId)   — Hiển thị hoặc tạo mã QR cho phiên được chọn
 *   refreshQRCode()         — Làm mới mã QR (tạo mã mới)
 *   loadAttendanceList()    — Tải danh sách sinh viên đã điểm danh cho phiên hiện tại
 *   showResult(msg,type)    — Hiện thông báo kết quả
 */
let currentSessionId = null;
let currentQR = null;

async function loadSessionsList() {
    try {
        const response = await fetch('/api/class-sessions', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error('Failed to load sessions');

        let sessions = await response.json();
        if (!Array.isArray(sessions)) {
            sessions = sessions.items || [];
        }

        // Only show future and today's sessions
        const today = new Date();
        today.setHours(0, 0, 0, 0);

        sessions = sessions.filter(s => {
            const sessDate = new Date(s.session_date);
            return sessDate >= today;
        });

        sessions.sort((a, b) => {
            return new Date(b.session_date) - new Date(a.session_date);
        });

        const select = document.getElementById('sessionSelect');
        sessions.forEach(sess => {
            const option = document.createElement('option');
            const date = new Date(sess.session_date).toLocaleDateString('vi-VN');
            const startTime = sess.start_time ? sess.start_time.substring(0, 5) : '??:??';
            option.value = sess.id;
            option.textContent = `${sess.classroom_name} - ${sess.subject_name} (${date} ${startTime})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading sessions:', error);
        showAlert('Lỗi khi tải buổi học', 'danger');
    }
}

async function loadSessionDetails() {
    const sessionId = document.getElementById('sessionSelect').value;

    if (!sessionId) {
        document.getElementById('sessionDetails').classList.add('d-none');
        return;
    }

    try {
        showLoadingState();
        currentSessionId = sessionId;

        const response = await fetch(`/api/class-sessions/${sessionId}`, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error('Failed to load session');

        const sess = await response.json();

        // Update session info
        document.getElementById('sessClassroom').textContent = sess.classroom_name || '--';
        document.getElementById('sessSubject').textContent = sess.subject_name || '--';

        const date = new Date(sess.session_date).toLocaleDateString('vi-VN');
        const startTime = sess.start_time ? sess.start_time.substring(0, 5) : '--:--';
        const endTime = sess.end_time ? sess.end_time.substring(0, 5) : '--:--';
        document.getElementById('sessTime').textContent = `${date}, ${startTime} - ${endTime}`;
        document.getElementById('sessRoom').textContent = sess.room_name || '-';

        const statusLabels = {
            'scheduled': 'Lên lịch',
            'ongoing': 'Đang diễn ra',
            'completed': 'Hoàn thành',
            'cancelled': 'Hủy'
        };
        const statusColors = {
            'scheduled': 'secondary',
            'ongoing': 'warning',
            'completed': 'success',
            'cancelled': 'danger'
        };
        const statusLabel = statusLabels[sess.status] || sess.status;
        const statusColor = statusColors[sess.status] || 'secondary';
        document.getElementById('sessStatus').innerHTML = `<span class="badge bg-${statusColor}">${statusLabel}</span>`;

        // Generate attendance link — matches public check-in route /attendance/checkin/<session_id>
        const attendanceLink = `${window.location.origin}/attendance/checkin/${sessionId}`;
        document.getElementById('attendanceLink').value = attendanceLink;

        // Generate QR code
        generateQRCode(attendanceLink);

        // Load attendance records
        await loadAttendanceRecords(sessionId);

        document.getElementById('sessionDetails').classList.remove('d-none');
        hideLoadingState();
    } catch (error) {
        console.error('Error loading session details:', error);
        showAlert('Lỗi khi tải chi tiết buổi học', 'danger');
        hideLoadingState();
    }
}

function generateQRCode(url) {
    const qrContainer = document.getElementById('qrCode');
    qrContainer.innerHTML = '';

    currentQR = new QRCode(qrContainer, {
        text: url,
        width: 256,
        height: 256,
        colorDark: '#000000',
        colorLight: '#ffffff',
        correctLevel: QRCode.CorrectLevel.H
    });
}

function downloadQR() {
    const canvas = document.querySelector('#qrCode canvas');
    if (!canvas) {
        showAlert('QR code chưa được tạo', 'warning');
        return;
    }

    const link = document.createElement('a');
    link.href = canvas.toDataURL();
    link.download = `attendance-qr-${currentSessionId}.png`;
    link.click();

    showAlert('QR code đã được tải xuống', 'success');
}

function copyLink() {
    const link = document.getElementById('attendanceLink');
    link.select();
    document.execCommand('copy');

    showAlert('Đường dẫn đã được sao chép', 'success');
}

async function loadAttendanceRecords(sessionId) {
    try {
        document.getElementById('attendanceLoading').classList.remove('d-none');
        document.getElementById('attendanceTable').classList.add('d-none');
        document.getElementById('attendanceEmpty').classList.add('d-none');

        // Try to load attendance records from API
        // Note: This endpoint may not exist yet, so we'll handle gracefully
        try {
            const response = await fetch(`/api/recognize/session/${sessionId}/attendance`, {
                headers: { 'Authorization': `Bearer ${auth.getToken()}` }
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            const records = data.attendance || [];
            if (records.length > 0) {
                renderAttendanceRecords(records);
            } else {
                document.getElementById('attendanceEmpty').classList.remove('d-none');
            }
        } catch (error) {
            document.getElementById('attendanceEmpty').classList.remove('d-none');
            console.log('Could not load attendance records:', error.message);
        }

        document.getElementById('attendanceLoading').classList.add('d-none');
    } catch (error) {
        console.error('Error loading attendance records:', error);
        document.getElementById('attendanceLoading').classList.add('d-none');
    }
}

function renderAttendanceRecords(records) {
    const tbody = document.getElementById('attendanceRecords');
    const tableContainer = document.getElementById('attendanceTable');
    const emptyState = document.getElementById('attendanceEmpty');

    if (!records || records.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    const statusLabels = {
        'present': 'Có mặt',
        'late': 'Muộn',
        'absent': 'Vắng',
        'excused': 'Xin phép'
    };

    const statusColors = {
        'present': 'success',
        'late': 'warning',
        'absent': 'danger',
        'excused': 'info'
    };

    tbody.innerHTML = records.map(rec => {
        // API returns check_in_time (ISO string) and confidence (already %)
        const rawTime = rec.check_in_time || rec.attendance_time;
        const time = rawTime
            ? new Date(rawTime).toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
            : '--:--:--';

        const statusLabel = statusLabels[rec.status] || rec.status;
        const statusColor = statusColors[rec.status] || 'secondary';

        const rawConf = rec.confidence != null ? rec.confidence : (rec.confidence_score != null ? rec.confidence_score * 100 : null);
        const confidenceScore = rawConf != null ? rawConf.toFixed(1) + '%' : '-';

        return `
            <tr>
                <td><small>${escapeHtml(rec.student_code || '--')}</small></td>
                <td><strong>${escapeHtml(rec.student_name || '--')}</strong></td>
                <td><small>${time}</small></td>
                <td><span class="badge bg-${statusColor}">${statusLabel}</span></td>
                <td><small>${confidenceScore}</small></td>
            </tr>
        `;
    }).join('');
}

function refreshAttendance() {
    if (!currentSessionId) {
        showAlert('Vui lòng chọn buổi học', 'warning');
        return;
    }

    loadAttendanceRecords(currentSessionId);
    showAlert('Đã cập nhật danh sách điểm danh', 'success');
}

function showLoadingState() {
    document.getElementById('loadingState').classList.remove('d-none');
    document.getElementById('sessionDetails').classList.add('d-none');
}

function hideLoadingState() {
    document.getElementById('loadingState').classList.add('d-none');
}

function showAlert(message, type = 'info') {
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.getElementById('alertContainer');
    const div = document.createElement('div');
    div.innerHTML = alertHTML;
    container.appendChild(div.firstElementChild);

    setTimeout(() => {
        container.firstElementChild?.remove();
    }, 5000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
