// Student Face Registration JS — 3 pose steps (front, left, right)
const POSES = ['front', 'left', 'right'];
const FRAMES_PER_POSE = 10;

let stream = null;
let currentPoseIdx = 0;
let capturing = false;
let captureInterval = null;

const webcam      = document.getElementById('webcam');
const overlay     = document.getElementById('overlay');
const startBtn    = document.getElementById('startBtn');
const stopBtn     = document.getElementById('stopBtn');
const countBadge  = document.getElementById('captureCount');
const poseInstr   = document.getElementById('poseInstruction');
const progressBar = document.getElementById('progressBar');

const POSE_INSTRUCTIONS = {
    front: 'Nhìn thẳng vào camera',
    left:  'Quay đầu nhẹ sang trái',
    right: 'Quay đầu nhẹ sang phải',
};
const POSE_STEP_IDS = ['step1', 'step2', 'step3'];

function updateStepUI() {
    POSE_STEP_IDS.forEach((id, i) => {
        const el = document.getElementById(id);
        el.classList.remove('bg-primary', 'bg-success', 'text-white', 'border-primary', 'border-success');
        if (i < currentPoseIdx) {
            el.classList.add('bg-success', 'text-white', 'border-success');
        } else if (i === currentPoseIdx) {
            el.classList.add('bg-primary', 'text-white', 'border-primary');
        }
    });
}

async function startRegistration() {
    const alertBox = document.getElementById('alertBox');
    alertBox.innerHTML = '';
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        webcam.srcObject = stream;
        overlay.style.display = 'none';
        startBtn.classList.add('d-none');
        stopBtn.classList.remove('d-none');
        capturing = true;
        currentPoseIdx = 0;
        updateStepUI();
        captureNextPose();
    } catch (e) {
        alertBox.innerHTML =
            `<div class="alert alert-danger">Không thể mở camera: ${e.message}</div>`;
    }
}

async function captureNextPose() {
    if (currentPoseIdx >= POSES.length) {
        await finishRegistration();
        return;
    }
    const pose = POSES[currentPoseIdx];
    poseInstr.textContent = POSE_INSTRUCTIONS[pose];
    updateStepUI();
    let count = 0;

    captureInterval = setInterval(async () => {
        if (!capturing) { clearInterval(captureInterval); return; }
        const blob = await captureFrame();
        if (!blob) return;

        const fd = new FormData();
        fd.append('image', blob, 'frame.jpg');
        fd.append('required_pose', pose);

        try {
            const res = await api.studentRegisterFace(fd);
            if (res.status === 'success' && res.pose_match) {
                count++;
                const total = currentPoseIdx * FRAMES_PER_POSE + count;
                countBadge.textContent = `${total} frame`;
                progressBar.style.width =
                    `${Math.round(total / (POSES.length * FRAMES_PER_POSE) * 100)}%`;
                if (count >= FRAMES_PER_POSE) {
                    clearInterval(captureInterval);
                    currentPoseIdx++;
                    setTimeout(captureNextPose, 600);
                }
            } else if (res.status === 'wrong_pose') {
                poseInstr.textContent = res.message || POSE_INSTRUCTIONS[pose];
            } else if (res.status === 'spoof') {
                stopRegistration();
                document.getElementById('alertBox').innerHTML =
                    `<div class="alert alert-danger">${res.message}</div>`;
            }
        } catch (e) {
            console.error('Frame error:', e);
        }
    }, 500);
}

async function captureFrame() {
    const canvas = document.createElement('canvas');
    canvas.width  = webcam.videoWidth  || 320;
    canvas.height = webcam.videoHeight || 240;
    canvas.getContext('2d').drawImage(webcam, 0, 0);
    return new Promise(resolve => canvas.toBlob(resolve, 'image/jpeg', 0.8));
}

async function finishRegistration() {
    stopRegistration();
    poseInstr.textContent = 'Đang hoàn tất đăng ký...';
    progressBar.style.width = '100%';
    try {
        const res = await api.studentCompleteRegistration();
        // Hide mandatory notice — no longer needed
        const notice = document.getElementById('mandatoryNotice');
        if (notice) notice.style.display = 'none';

        document.getElementById('alertBox').innerHTML = `
            <div class="alert alert-success">
                <i class="bi bi-check-circle-fill me-2"></i>
                <strong>${res.message || 'Đăng ký khuôn mặt thành công!'}</strong><br>
                Bạn có thể sử dụng đầy đủ các chức năng của hệ thống.
            </div>`;

        // Redirect to dashboard after 2s
        setTimeout(() => { window.location.href = '/student/dashboard'; }, 2000);
    } catch (e) {
        document.getElementById('alertBox').innerHTML =
            `<div class="alert alert-danger">${e.message}</div>`;
    }
}

function stopRegistration() {
    capturing = false;
    clearInterval(captureInterval);
    if (stream) {
        stream.getTracks().forEach(t => t.stop());
        stream = null;
    }
    overlay.style.display = '';
    overlay.textContent = 'Đã dừng';
    startBtn.classList.remove('d-none');
    stopBtn.classList.add('d-none');
}
