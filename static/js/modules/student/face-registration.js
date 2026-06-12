/**
 * Module Đăng Ký Khuôn Mặt Sinh Viên (Student Face Registration)
 * Quy trình 3 bước: chụp khuôn mặt ở 3 góc (thẳng, trái, phải).
 * Mỗi góc chụp FRAMES_PER_POSE = 10 frame, gửi từng frame lên server kiểm tra pose + antispoof.
 * Sau khi hoàn tất 3 pose, gọi API complete-registration để huấn luyện lại SVM.
 */

// Danh sách các góc cần chụp theo thứ tự
const POSES = ['front', 'left', 'right'];

// Số frame cần chụp cho mỗi góc
const FRAMES_PER_POSE = 10;

// Luồng video từ webcam (MediaStream)
let stream = null;

// Chỉ số góc hiện tại đang chụp (0=front, 1=left, 2=right)
let currentPoseIdx = 0;

// Cờ trạng thái đang chụp
let capturing = false;

// ID của setInterval dùng để chụp frame định kỳ
let captureInterval = null;

// Tham chiếu đến các phần tử DOM
const webcam      = document.getElementById('webcam');        // Video hiển thị webcam
const overlay     = document.getElementById('overlay');       // Lớp phủ lên webcam khi dừng
const startBtn    = document.getElementById('startBtn');      // Nút bắt đầu đăng ký
const stopBtn     = document.getElementById('stopBtn');       // Nút dừng đăng ký
const countBadge  = document.getElementById('captureCount'); // Hiển thị số frame đã chụp
const poseInstr   = document.getElementById('poseInstruction'); // Hướng dẫn tư thế hiện tại
const progressBar = document.getElementById('progressBar');  // Thanh tiến độ tổng thể

// Hướng dẫn văn bản cho từng góc chụp
const POSE_INSTRUCTIONS = {
    front: 'Nhìn thẳng vào camera',
    left:  'Quay đầu nhẹ sang trái',
    right: 'Quay đầu nhẹ sang phải',
};

// ID các phần tử step indicator trên UI (step1, step2, step3)
const POSE_STEP_IDS = ['step1', 'step2', 'step3'];

/**
 * Cập nhật giao diện step indicator:
 * - Bước đã hoàn thành: màu xanh lá (bg-success)
 * - Bước hiện tại: màu xanh dương (bg-primary)
 * - Bước chưa đến: không tô màu
 */
function updateStepUI() {
    POSE_STEP_IDS.forEach((id, i) => {
        const el = document.getElementById(id);
        el.classList.remove('bg-primary', 'bg-success', 'text-white', 'border-primary', 'border-success');
        if (i < currentPoseIdx) {
            // Bước đã hoàn thành
            el.classList.add('bg-success', 'text-white', 'border-success');
        } else if (i === currentPoseIdx) {
            // Bước đang thực hiện
            el.classList.add('bg-primary', 'text-white', 'border-primary');
        }
    });
}

/**
 * Bắt đầu quy trình đăng ký khuôn mặt.
 * Yêu cầu quyền truy cập webcam, hiển thị video, đặt lại bộ đếm,
 * rồi bắt đầu chụp pose đầu tiên.
 */
async function startRegistration() {
    const alertBox = document.getElementById('alertBox');
    alertBox.innerHTML = '';
    try {
        // Mở camera — yêu cầu quyền truy cập từ trình duyệt
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        webcam.srcObject = stream;
        overlay.style.display = 'none';    // Ẩn lớp phủ
        startBtn.classList.add('d-none');  // Ẩn nút Bắt đầu
        stopBtn.classList.remove('d-none'); // Hiện nút Dừng
        capturing = true;
        currentPoseIdx = 0;
        updateStepUI();
        captureNextPose();
    } catch (e) {
        alertBox.innerHTML =
            `<div class="alert alert-danger">Không thể mở camera: ${e.message}</div>`;
    }
}

/**
 * Chụp và gửi frame cho góc tiếp theo.
 * Nếu đã chụp đủ cả 3 góc, gọi finishRegistration().
 * Chụp mỗi 500ms, kiểm tra pose_match từ server trước khi tính frame hợp lệ.
 * Kết quả từ server:
 *   - status='success' + pose_match=true  → frame hợp lệ, tăng bộ đếm
 *   - status='wrong_pose'                 → hiện thông báo điều chỉnh tư thế
 *   - status='spoof'                      → phát hiện giả mạo, dừng đăng ký
 */
async function captureNextPose() {
    // Kiểm tra đã chụp đủ tất cả các góc chưa
    if (currentPoseIdx >= POSES.length) {
        await finishRegistration();
        return;
    }
    const pose = POSES[currentPoseIdx];
    poseInstr.textContent = POSE_INSTRUCTIONS[pose];
    updateStepUI();
    let count = 0; // Số frame hợp lệ đã chụp cho góc này

    // Chụp frame định kỳ mỗi 500ms
    captureInterval = setInterval(async () => {
        if (!capturing) { clearInterval(captureInterval); return; }
        const blob = await captureFrame();
        if (!blob) return;

        // Tạo FormData gửi lên API register-face
        const fd = new FormData();
        fd.append('image', blob, 'frame.jpg');
        fd.append('required_pose', pose); // Thông báo server pose yêu cầu để kiểm tra

        try {
            const res = await api.studentRegisterFace(fd);
            if (res.status === 'success' && res.pose_match) {
                // Frame hợp lệ — cập nhật bộ đếm và thanh tiến độ
                count++;
                const total = currentPoseIdx * FRAMES_PER_POSE + count;
                countBadge.textContent = `${total} frame`;
                progressBar.style.width =
                    `${Math.round(total / (POSES.length * FRAMES_PER_POSE) * 100)}%`;
                if (count >= FRAMES_PER_POSE) {
                    // Đã đủ frame cho góc này — chuyển sang góc tiếp theo sau 600ms
                    clearInterval(captureInterval);
                    currentPoseIdx++;
                    setTimeout(captureNextPose, 600);
                }
            } else if (res.status === 'wrong_pose') {
                // Sai tư thế — nhắc người dùng điều chỉnh
                poseInstr.textContent = res.message || POSE_INSTRUCTIONS[pose];
            } else if (res.status === 'spoof') {
                // Phát hiện giả mạo (ảnh in, màn hình giả) — dừng ngay
                stopRegistration();
                document.getElementById('alertBox').innerHTML =
                    `<div class="alert alert-danger">${res.message}</div>`;
            }
        } catch (e) {
            console.error('Frame error:', e);
        }
    }, 500); // Chụp mỗi 500ms
}

/**
 * Chụp một frame từ webcam dưới dạng Blob JPEG (chất lượng 80%).
 * Vẽ frame vào canvas rồi chuyển đổi sang Blob.
 * Trả về Promise<Blob>.
 */
async function captureFrame() {
    const canvas = document.createElement('canvas');
    canvas.width  = webcam.videoWidth  || 320;
    canvas.height = webcam.videoHeight || 240;
    canvas.getContext('2d').drawImage(webcam, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
}

/**
 * Hoàn tất đăng ký khuôn mặt sau khi chụp đủ 3 góc.
 * Gọi API complete-registration để server huấn luyện lại mô hình SVM.
 * Ẩn thông báo bắt buộc đăng ký và chuyển hướng về dashboard sau 2 giây.
 */
async function finishRegistration() {
    stopRegistration();
    poseInstr.textContent = 'Đang hoàn tất đăng ký...';
    progressBar.style.width = '100%';
    try {
        const res = await api.studentCompleteRegistration();
        // Ẩn thông báo bắt buộc đăng ký khuôn mặt
        const notice = document.getElementById('mandatoryNotice');
        if (notice) notice.style.display = 'none';

        document.getElementById('alertBox').innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle-fill me-2"></i>
                <strong>${res.message || 'Đăng ký khuôn mặt thành công!'}</strong><br>
                Bạn có thể sử dụng đầy đủ các chức năng của hệ thống.
            </div>`;

        // Chuyển hướng về dashboard sinh viên sau 2 giây
        setTimeout(() => { window.location.href = '/student/dashboard'; }, 2000);
    } catch (e) {
        document.getElementById('alertBox').innerHTML =
            `<div class="alert alert-danger">${e.message}</div>`;
    }
}

/**
 * Dừng quy trình đăng ký khuôn mặt:
 * - Dừng setInterval chụp frame
 * - Tắt các track webcam và giải phóng camera
 * - Hiện lại lớp phủ overlay và nút Bắt đầu
 */
function stopRegistration() {
    capturing = false;
    clearInterval(captureInterval);
    if (stream) {
        stream.getTracks().forEach(t => t.stop()); // Tắt từng track (audio/video)
        stream = null;
    }
    overlay.style.display = '';       // Hiện lại overlay
    overlay.textContent = 'Đã dừng';
    startBtn.classList.remove('d-none'); // Hiện lại nút Bắt đầu
    stopBtn.classList.add('d-none');     // Ẩn nút Dừng
}
