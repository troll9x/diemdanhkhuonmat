/**
 * Student Authenticated Face Check-in Module
 * Captures one webcam frame and submits to /api/student/sessions/:id/check-in.
 */

let stream = null;

const video = document.getElementById('videoEl');
const canvas = document.getElementById('captureCanvas');
const cameraWrapper = document.getElementById('cameraWrapper');
const cameraPlaceholder = document.getElementById('cameraPlaceholder');
const processingSpinner = document.getElementById('processingSpinner');
const resultBox = document.getElementById('resultBox');
const resultIcon = document.getElementById('resultIcon');
const resultTitle = document.getElementById('resultTitle');
const resultMessage = document.getElementById('resultMessage');
const resultDetail = document.getElementById('resultDetail');
const btnCheckin = document.getElementById('btnCheckin');
const btnRetry = document.getElementById('btnRetry');

// ── Helpers ────────────────────────────────────────────────────────────────────

function captureFrameAsBlob(quality = 0.85) {
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', quality));
}

function showResult(status, title, message, detail = '') {
    cameraWrapper.classList.add('d-none');
    processingSpinner.classList.add('d-none');
    resultBox.classList.remove('d-none');

    const icons = {
        success: '<i class="bi bi-check-circle-fill text-success"></i>',
        error: '<i class="bi bi-x-circle-fill text-danger"></i>',
        warning: '<i class="bi bi-exclamation-circle-fill text-warning"></i>',
        info: '<i class="bi bi-info-circle-fill text-info"></i>',
    };
    resultIcon.innerHTML = icons[status] || icons.info;
    resultTitle.textContent = title;
    resultMessage.textContent = message;
    resultDetail.textContent = detail;

    btnCheckin.classList.add('d-none');
    btnRetry.classList.remove('d-none');
}

function resetUI() {
    resultBox.classList.add('d-none');
    processingSpinner.classList.add('d-none');
    btnRetry.classList.add('d-none');
    btnCheckin.classList.remove('d-none');
}

// ── Session Info ───────────────────────────────────────────────────────────────

async function loadSessionInfo() {
    try {
        const res = await fetch(`/api/class-sessions/${SESSION_ID}`);
        if (!res.ok) throw new Error('Session not found');
        const s = await res.json();

        document.getElementById('sessionLoading').classList.add('d-none');
        document.getElementById('sessionInfo').classList.remove('d-none');

        document.getElementById('sessClassroom').textContent = s.classroom_name || '—';
        document.getElementById('sessSubject').textContent = s.subject_name || '—';
        document.getElementById('sessDate').textContent = s.session_date || '—';
        document.getElementById('sessTime').textContent =
            (s.start_time || '').substring(0, 5) + ' – ' + (s.end_time || '').substring(0, 5);

        const statusMap = { scheduled: 'Chưa bắt đầu', ongoing: 'Đang điểm danh', completed: 'Đã kết thúc', cancelled: 'Đã hủy' };
        const colorMap = { scheduled: 'secondary', ongoing: 'success', completed: 'primary', cancelled: 'danger' };
        const st = s.status || 'unknown';
        document.getElementById('sessStatus').innerHTML =
            `<span class="badge bg-${colorMap[st] || 'secondary'}">${statusMap[st] || st}</span>`;

        if (s.status !== 'ongoing') {
            btnCheckin.disabled = true;
            btnCheckin.innerHTML = '<i class="bi bi-lock"></i> Phiên điểm danh chưa mở';
            btnCheckin.className = 'btn btn-secondary btn-lg';
        }
    } catch (err) {
        document.getElementById('sessionLoading').classList.add('d-none');
        document.getElementById('sessionError').classList.remove('d-none');
        document.getElementById('sessionErrorMsg').textContent = 'Không thể tải thông tin buổi học: ' + err.message;
        btnCheckin.disabled = true;
    }
}

// ── Camera ─────────────────────────────────────────────────────────────────────

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
        });
        video.srcObject = stream;

        // Wait for actual frame data (canplay > loadedmetadata)
        await new Promise(resolve => {
            if (video.readyState >= 3) { resolve(); return; }
            video.addEventListener('canplay', resolve, { once: true });
        });

        cameraWrapper.classList.remove('d-none');
        cameraPlaceholder.classList.add('d-none');

        // Stabilization delay before capture
        await new Promise(r => setTimeout(r, 500));
        return true;
    } catch (err) {
        showResult('error', 'Không thể mở camera', err.message);
        return false;
    }
}

function stopCamera() {
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    video.srcObject = null;
    cameraWrapper.classList.add('d-none');
}

// ── Check-in ───────────────────────────────────────────────────────────────────

async function performCheckin() {
    btnCheckin.classList.add('d-none');
    processingSpinner.classList.remove('d-none');

    // Allow a brief moment for webcam to stabilize
    await new Promise(r => setTimeout(r, 400));

    try {
        const blob = await captureFrameAsBlob();
        stopCamera();

        const formData = new FormData();
        formData.append('image', blob, 'frame.jpg');

        const token = auth.getToken();
        const response = await fetch(`/api/student/sessions/${SESSION_ID}/check-in`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        const data = await response.json();

        switch (data.status) {
            case 'success':
                showResult(
                    'success',
                    'Điểm danh thành công!',
                    data.message,
                    `Giờ điểm danh: ${data.attendance_time} | Độ chính xác: ${data.confidence}%`
                );
                break;
            case 'already_checked_in':
                showResult(
                    'info',
                    'Đã điểm danh rồi',
                    data.message,
                    data.attendance_time ? `Đã điểm lúc: ${data.attendance_time}` : ''
                );
                break;
            case 'mismatch':
                showResult(
                    'error',
                    'Khuôn mặt không khớp',
                    data.message,
                    data.confidence != null ? `Độ tương đồng: ${data.confidence}%` : ''
                );
                break;
            case 'spoof':
                showResult('error', 'Phát hiện gian lận', data.message);
                break;
            case 'no_face':
                showResult('warning', 'Không phát hiện khuôn mặt', data.message);
                break;
            case 'session_closed':
                showResult('warning', 'Phiên điểm danh đã đóng', data.message);
                break;
            case 'not_enrolled':
                showResult('error', 'Không thuộc lớp này', data.message);
                break;
            default:
                showResult('error', 'Lỗi điểm danh', data.message || data.error || 'Lỗi không xác định');
        }
    } catch (err) {
        processingSpinner.classList.add('d-none');
        showResult('error', 'Lỗi kết nối', 'Không thể kết nối tới máy chủ. Vui lòng thử lại.');
        console.error('checkin error:', err);
    }
}

// ── Event Handlers ─────────────────────────────────────────────────────────────

btnCheckin.addEventListener('click', async () => {
    const ok = await startCamera();
    if (!ok) return;

    btnCheckin.innerHTML = '<i class="bi bi-camera-fill"></i> Chụp & Điểm danh';
    btnCheckin.onclick = performCheckin;
});

btnRetry.addEventListener('click', () => {
    resetUI();
    cameraPlaceholder.classList.remove('d-none');
    cameraWrapper.classList.add('d-none');
    // Re-enable button and restore original handler
    btnCheckin.innerHTML = '<i class="bi bi-camera"></i> Mở camera và điểm danh';
    btnCheckin.onclick = null;
    btnCheckin.addEventListener('click', async () => {
        const ok = await startCamera();
        if (!ok) return;
        btnCheckin.innerHTML = '<i class="bi bi-camera-fill"></i> Chụp & Điểm danh';
        btnCheckin.onclick = performCheckin;
    }, { once: true });
});

// ── Init ───────────────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadSessionInfo();
});
