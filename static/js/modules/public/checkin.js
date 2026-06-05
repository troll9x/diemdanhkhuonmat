// Student Check-in Module

let sessionId = null;
let stream = null;
let canvas = null;

async function loadSessionInfo(id) {
    sessionId = id;
    try {
        const response = await fetch(`/api/class-sessions/${id}`);
        if (!response.ok) throw new Error('Session not found');

        const sess = await response.json();

        // Display session info
        document.getElementById('sessClassroom').textContent = sess.classroom_name || '--';
        document.getElementById('sessSubject').textContent = sess.subject_name || '--';

        const date = new Date(sess.session_date).toLocaleDateString('vi-VN');
        const startTime = sess.start_time ? sess.start_time.substring(0, 5) : '--:--';
        const endTime = sess.end_time ? sess.end_time.substring(0, 5) : '--:--';
        document.getElementById('sessDate').textContent = date;
        document.getElementById('sessTime').textContent = `${startTime} - ${endTime}`;

        const statusLabels = {
            'scheduled': 'Lên lịch',
            'ongoing': 'Đang diễn ra',
            'completed': 'Hoàn thành',
            'cancelled': 'Hủy'
        };
        document.getElementById('sessStatus').textContent = statusLabels[sess.status] || sess.status;

        // Check if session is active
        if (sess.status !== 'scheduled' && sess.status !== 'ongoing') {
            showResult(`Buổi học không mở để điểm danh (${statusLabels[sess.status]})`, 'error');
            disableForm();
        }
    } catch (error) {
        console.error('Error loading session:', error);
        showResult('Lỗi: Không tìm thấy buổi học', 'error');
        disableForm();
    }
}

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { facingMode: 'user' },
            audio: false
        });

        const video = document.getElementById('cameraPreview');
        video.srcObject = stream;
        video.classList.add('active');

        // Create canvas for capture
        canvas = document.createElement('canvas');

        // Update buttons
        document.getElementById('btnStartCamera').style.display = 'none';
        document.getElementById('btnCapture').style.display = 'block';
        document.getElementById('btnStopCamera').style.display = 'block';

        showResult('', 'info'); // Clear result
    } catch (error) {
        console.error('Camera error:', error);
        if (error.name === 'NotAllowedError') {
            showResult('Lỗi: Bạn cần cấp quyền truy cập camera', 'error');
        } else if (error.name === 'NotFoundError') {
            showResult('Lỗi: Không tìm thấy camera', 'error');
        } else {
            showResult('Lỗi: ' + error.message, 'error');
        }
    }
}

function stopCamera() {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
        stream = null;
    }

    const video = document.getElementById('cameraPreview');
    video.classList.remove('active');

    document.getElementById('btnStartCamera').style.display = 'block';
    document.getElementById('btnCapture').style.display = 'none';
    document.getElementById('btnStopCamera').style.display = 'none';
}

async function captureAndSubmit() {
    const studentCode = document.getElementById('studentCode').value.trim();
    if (!studentCode) {
        showResult('Vui lòng nhập mã số sinh viên', 'error');
        return;
    }

    if (!canvas || !stream) {
        showResult('Lỗi: Camera chưa được khởi động', 'error');
        return;
    }

    try {
        // Show loading
        document.getElementById('spinnerBox').classList.add('active');
        document.getElementById('buttonGroup').style.display = 'none';

        // Capture frame from video
        const video = document.getElementById('cameraPreview');
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(video, 0, 0);

        // Convert to blob
        const blob = await new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));

        // Send to recognition API
        const formData = new FormData();
        formData.append('image', blob);
        formData.append('session_id', sessionId);
        formData.append('student_code', studentCode);

        const response = await fetch('/api/checkin', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        // Hide loading
        document.getElementById('spinnerBox').classList.remove('active');
        document.getElementById('buttonGroup').style.display = 'block';

        // Handle response
        if (response.ok || response.status === 200) {
            handleCheckinResult(data);
        } else {
            showResult(data.error || data.message || 'Lỗi khi gửi', 'error');
        }
    } catch (error) {
        console.error('Capture error:', error);
        document.getElementById('spinnerBox').classList.remove('active');
        document.getElementById('buttonGroup').style.display = 'block';
        showResult('Lỗi: ' + error.message, 'error');
    }
}

function handleCheckinResult(data) {
    if (data.status === 'success' || data.status === 'present') {
        showResult('✓ Điểm danh thành công!', 'success');
        if (data.confidence != null) {
            document.getElementById('resultDetails').textContent =
                `Độ chính xác: ${data.confidence.toFixed(1)}%`;
        }
        stopCamera();
        disableForm();
    } else if (data.status === 'already_checked_in') {
        showResult('Bạn đã điểm danh rồi', 'info');
        if (data.message) {
            document.getElementById('resultDetails').textContent = data.message;
        }
    } else if (data.status === 'spoof') {
        showResult('⚠ Phát hiện hình ảnh giả mạo. Vui lòng sử dụng khuôn mặt thật', 'error');
    } else if (data.status === 'unknown' || data.status === 'not_recognized') {
        showResult('⚠ Không nhận diện được khuôn mặt. Vui lòng thử lại', 'error');
    } else if (data.status === 'not_enrolled') {
        showResult('⚠ Sinh viên này chưa đăng ký khuôn mặt', 'error');
    } else if (data.status === 'session_closed') {
        showResult('⚠ Buổi học đã đóng', 'error');
    } else {
        showResult(data.message || 'Lỗi khi xử lý', 'error');
    }
}

function showResult(message, type) {
    const resultBox = document.getElementById('resultBox');
    resultBox.className = `result-box ${type}`;
    document.getElementById('resultMessage').textContent = message;
    if (message) {
        resultBox.classList.add('active');
    } else {
        resultBox.classList.remove('active');
    }
}

function resetForm() {
    document.getElementById('studentCode').value = '';
    stopCamera();
    showResult('', '');
    document.getElementById('btnStartCamera').style.display = 'block';
    document.getElementById('buttonGroup').style.display = 'block';
}

function disableForm() {
    document.getElementById('studentCode').disabled = true;
    document.getElementById('btnStartCamera').disabled = true;
    document.getElementById('btnCapture').disabled = true;
}

// Event listeners
document.getElementById('btnStartCamera').addEventListener('click', startCamera);
document.getElementById('btnCapture').addEventListener('click', captureAndSubmit);
document.getElementById('btnStopCamera').addEventListener('click', stopCamera);

// Allow Enter key to submit
document.getElementById('studentCode').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        captureAndSubmit();
    }
});
