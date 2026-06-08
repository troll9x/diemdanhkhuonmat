// Student Check-in JS
let selectedSessionId = PAGE_SESSION_ID || null;
let webcamStream = null;

const STATUS_UI = {
    success:          { cls: 'success', icon: 'bi-check-circle-fill',  text: 'Điểm danh thành công' },
    success_late:     { cls: 'warning', icon: 'bi-clock-fill',         text: 'Điểm danh thành công — Muộn giờ' },
    already_checked_in: { cls: 'info',  icon: 'bi-info-circle-fill',   text: 'Bạn đã điểm danh rồi' },
    mismatch:         { cls: 'danger',  icon: 'bi-x-circle-fill',      text: 'Khuôn mặt không khớp' },
    no_face:          { cls: 'warning', icon: 'bi-camera-video-off',   text: 'Không phát hiện khuôn mặt' },
    too_far:          { cls: 'danger',  icon: 'bi-geo-alt-fill',       text: 'Quá xa giảng viên' },
    session_closed:   { cls: 'secondary',icon: 'bi-stop-circle',       text: 'Phiên đã kết thúc' },
    spoof:            { cls: 'danger',  icon: 'bi-shield-x',           text: 'Phát hiện giả mạo' },
    not_enrolled:     { cls: 'danger',  icon: 'bi-person-x',           text: 'Không thuộc lớp này' },
};

async function loadSessions() {
    if (selectedSessionId) {
        showCheckinPanel(selectedSessionId);
        return;
    }
    const list = document.getElementById('sessionList');
    try {
        const data = await api.get('/student/active-sessions');
        if (!data.sessions || data.sessions.length === 0) {
            list.innerHTML =
                '<div class="text-center py-4 text-muted">Không có phiên điểm danh nào đang mở.</div>';
            return;
        }
        list.innerHTML = data.sessions.map(s => `
            <div class="d-flex justify-content-between align-items-center py-2 border-bottom">
                <div>
                    <strong>${escHtml(s.classroom)}</strong>
                    <span class="badge bg-${s.session_type === 'start' ? 'primary' : 'info'} ms-1">
                        ${s.session_type_label || s.session_type}
                    </span>
                    <small class="text-muted ms-2">${s.session_date}</small>
                    ${s.already_attended
                        ? '<span class="badge bg-success ms-2">Đã điểm danh</span>'
                        : ''}
                </div>
                ${!s.already_attended
                    ? `<button class="btn btn-sm btn-success" onclick="showCheckinPanel(${s.id}, '${escHtml(s.classroom)} — ${s.session_type_label || ''}')">
                           <i class="bi bi-camera-video me-1"></i>Điểm danh
                       </button>`
                    : ''}
            </div>`).join('');
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    }
}

function showCheckinPanel(sessionId, label) {
    selectedSessionId = sessionId;
    document.getElementById('sessionSelector').style.display = 'none';
    document.getElementById('checkinPanel').style.display = '';
    document.getElementById('checkinTitle').textContent = label || `Điểm danh — Phiên #${sessionId}`;
}

function cancelCheckin() {
    stopWebcam();
    selectedSessionId = null;
    document.getElementById('sessionSelector').style.display = '';
    document.getElementById('checkinPanel').style.display = 'none';
    document.getElementById('resultBox').style.display = 'none';
    document.getElementById('checkinControls').style.display = '';
    loadSessions();
}

async function startCheckin() {
    const btn = document.getElementById('checkinBtn');
    const sp  = document.getElementById('checkinSpinner');
    btn.disabled = true;
    sp.classList.remove('d-none');
    showResult(null);

    try {
        // 1. Get GPS
        const pos = await new Promise((resolve, reject) =>
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 }));
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        // 2. Open webcam
        const cam = document.getElementById('webcam');
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        cam.srcObject = webcamStream;
        cam.classList.remove('d-none');

        // Wait 1.5s for camera to stabilize
        await new Promise(r => setTimeout(r, 1500));

        // 3. Capture frame
        const canvas = document.createElement('canvas');
        canvas.width  = cam.videoWidth  || 320;
        canvas.height = cam.videoHeight || 240;
        canvas.getContext('2d').drawImage(cam, 0, 0);
        const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85));

        stopWebcam();

        // 4. Submit
        const fd = new FormData();
        fd.append('image', blob, 'checkin.jpg');
        fd.append('latitude', lat);
        fd.append('longitude', lon);

        const data = await api.studentCheckinV2(selectedSessionId, fd);
        // Promote to warning-style if late
        if (data.status === 'success' && data.is_late) data.status = 'success_late';
        showResult(data);
    } catch (e) {
        if (e.code) {
            showResult({ status: 'error', message: 'Không thể lấy GPS: ' + e.message });
        } else {
            showResult({ status: 'error', message: e.message });
        }
    } finally {
        btn.disabled = false;
        sp.classList.add('d-none');
    }
}

function showResult(data) {
    const box = document.getElementById('resultBox');
    if (!data) { box.style.display = 'none'; return; }

    const ui = STATUS_UI[data.status] || { cls: 'secondary', icon: 'bi-info-circle', text: data.status };
    box.style.display = '';
    box.innerHTML = `
        <div class="alert alert-${ui.cls}">
            <i class="bi ${ui.icon} me-2 fs-4"></i>
            <strong>${ui.text}</strong><br>
            ${data.message || ''}
            ${data.confidence != null ? `<br><small>Độ tin cậy: ${data.confidence}%</small>` : ''}
            ${data.distance_meters != null ? `<br><small>Khoảng cách: ${data.distance_meters} m</small>` : ''}
        </div>
        ${data.status === 'success'
            ? '<a href="/student/logs" class="btn btn-sm btn-primary"><i class="bi bi-clock-history me-1"></i>Xem lịch sử</a>'
            : '<button class="btn btn-sm btn-secondary" onclick="cancelCheckin()">Quay lại</button>'}`;
    document.getElementById('checkinControls').style.display = data.status === 'success' ? 'none' : '';
}

function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
    document.getElementById('webcam').classList.add('d-none');
}

function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

loadSessions();
