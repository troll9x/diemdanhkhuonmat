/**
 * Guided Face Registration — 3 pose steps (front → left → right)
 * Each step collects 10 frames at the correct angle (total 30).
 * INTERVAL = 300 ms, matching original register.html logic.
 */

// ── Step definitions ───────────────────────────────────────────────────────────
const STEPS = [
    {
        key:    'front',
        label:  'Nhìn thẳng vào camera',
        arrow:  '👁️',
        anim:   'animate-front',
        hint:   'Nhìn thẳng, giữ đầu thẳng đứng',
        target: 10,
        done:   0,
    },
    {
        key:    'left',
        label:  'Quay mặt sang trái',
        arrow:  '⬅️',
        anim:   'animate-left',
        hint:   'Quay đầu từ từ sang trái khoảng 30–40°',
        target: 10,
        done:   0,
    },
    {
        key:    'right',
        label:  'Quay mặt sang phải',
        arrow:  '➡️',
        anim:   'animate-right',
        hint:   'Quay đầu từ từ sang phải khoảng 30–40°',
        target: 10,
        done:   0,
    },
];

const INTERVAL = 300;  // ms between frames (same as original register.html)

let currentStep    = 0;
let totalFrames    = 0;
let running        = false;
let intervalId     = null;
let stream         = null;

// ── DOM refs ───────────────────────────────────────────────────────────────────
const video             = document.getElementById('videoEl');
const canvas            = document.getElementById('captureCanvas');
const cameraWrapper     = document.getElementById('cameraWrapper');
const cameraPlaceholder = document.getElementById('cameraPlaceholder');
const poseGuide         = document.getElementById('poseGuide');
const poseArrow         = document.getElementById('poseArrow');
const poseLabel         = document.getElementById('poseLabel');
const poseFrameCount    = document.getElementById('poseFrameCount');
const statusMsg         = document.getElementById('statusMsg');
const stepProgress      = document.getElementById('stepProgress');
const stepProgressBar   = document.getElementById('stepProgressBar');
const stepProgressLabel = document.getElementById('stepProgressLabel');
const stepProgressCount = document.getElementById('stepProgressCount');
const thumbnailStrip    = document.getElementById('thumbnailStrip');
const instructions      = document.getElementById('instructions');
const overallCard       = document.getElementById('overallProgressCard');
const totalBar          = document.getElementById('totalProgressBar');
const totalText         = document.getElementById('totalProgressText');
const btnStart          = document.getElementById('btnStart');
const btnPause          = document.getElementById('btnPause');
const btnResume         = document.getElementById('btnResume');
const btnReset          = document.getElementById('btnReset');
const successState      = document.getElementById('successState');
const actionButtons     = document.getElementById('actionButtons');

// ── Helpers ────────────────────────────────────────────────────────────────────

function setStatus(msg, cls = 'text-muted') {
    statusMsg.className = `mt-2 small text-center ${cls}`;
    statusMsg.innerHTML = msg;
}

function showEl(el, visible) {
    if (el) el.classList.toggle('d-none', !visible);
}

function captureJpegBlob() {
    canvas.width  = video.videoWidth  || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext('2d').drawImage(video, 0, 0);
    return new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85));
}

// ── UI: Step indicator circles ─────────────────────────────────────────────────

function refreshStepIndicator() {
    STEPS.forEach((step, i) => {
        const el = document.getElementById(`step-ind-${i}`);
        if (!el) return;
        const circle = el.querySelector('.step-circle');
        if (i < currentStep) {
            // Completed
            circle.className = 'step-circle bg-success text-white';
            circle.textContent = '✓';
        } else if (i === currentStep) {
            // Active
            circle.className = 'step-circle bg-primary text-white';
            circle.textContent = i + 1;
        } else {
            // Pending
            circle.className = 'step-circle bg-light text-secondary border';
            circle.textContent = i + 1;
        }
    });
}

// ── UI: Pose guide for current step ───────────────────────────────────────────

function refreshPoseGuide() {
    if (currentStep >= STEPS.length) return;
    const step = STEPS[currentStep];

    poseArrow.textContent = step.arrow;
    poseArrow.className   = `pose-arrow ${step.anim}`;
    poseLabel.textContent = step.label;
    poseFrameCount.textContent = `${step.done} / ${step.target} frame`;

    stepProgressBar.style.width = `${Math.round(step.done / step.target * 100)}%`;
    stepProgressLabel.textContent = `Bước ${currentStep + 1}/3 — ${step.hint}`;
    stepProgressCount.textContent = `${step.done} / ${step.target}`;
}

// ── UI: Overall progress ───────────────────────────────────────────────────────

function refreshOverall() {
    const total = STEPS.reduce((s, st) => s + st.done, 0);
    totalFrames = total;
    const pct   = Math.round(total / 30 * 100);
    totalBar.style.width  = pct + '%';
    totalText.textContent = `${total} / 30`;
    totalText.className   = total >= 20 ? 'badge bg-success' : total > 0 ? 'badge bg-info text-dark' : 'badge bg-secondary';
}

// ── Camera ─────────────────────────────────────────────────────────────────────

async function startCamera() {
    try {
        stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' }
        });
        video.srcObject = stream;

        // Wait for actual frame data — 'canplay' is more reliable than 'loadedmetadata'
        await new Promise(resolve => {
            if (video.readyState >= 3) { resolve(); return; }   // HAVE_FUTURE_DATA
            video.addEventListener('canplay', resolve, { once: true });
        });

        // Show camera, hide placeholder
        cameraWrapper.classList.remove('d-none');
        cameraPlaceholder.classList.add('d-none');

        // Brief stabilization — let the first real frame arrive
        await new Promise(r => setTimeout(r, 400));
        return true;
    } catch (err) {
        setStatus(`<i class="bi bi-exclamation-triangle text-danger"></i> Không thể mở camera: ${err.message}`, 'text-danger');
        return false;
    }
}

function stopCamera() {
    if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null; }
    video.srcObject = null;
    cameraWrapper.classList.add('d-none');
    cameraPlaceholder.classList.remove('d-none');
}

// ── Frame capture loop ─────────────────────────────────────────────────────────

async function sendFrame() {
    if (!running || currentStep >= STEPS.length) return;

    const step = STEPS[currentStep];

    try {
        const blob = await captureJpegBlob();
        const fd   = new FormData();
        fd.append('image', blob, 'frame.jpg');
        fd.append('required_pose', step.key);

        const res  = await fetch('/api/student/register-face', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` },
            body: fd,
        });
        const data = await res.json();

        switch (data.status) {
            case 'success': {
                video.className = 'ring-ok';
                step.done++;
                refreshPoseGuide();
                refreshOverall();

                // Thumbnail
                const thumb = document.createElement('img');
                thumb.src   = canvas.toDataURL('image/jpeg', 0.55);
                thumb.title = `${step.label} #${step.done}`;
                thumbnailStrip.appendChild(thumb);

                setStatus(
                    `<i class="bi bi-check-circle text-success"></i> ${data.message}`,
                    'text-success'
                );

                // Step complete?
                if (step.done >= step.target) {
                    pauseCapture();
                    if (currentStep + 1 < STEPS.length) {
                        advanceStep();
                    } else {
                        showSuccess();
                    }
                }
                break;
            }
            case 'wrong_pose': {
                video.className = 'ring-warn';
                setStatus(
                    `<i class="bi bi-arrow-repeat text-warning"></i> ${data.message}`,
                    'text-warning'
                );
                break;
            }
            case 'no_face': {
                video.className = 'ring-bad';
                setStatus(
                    `<i class="bi bi-emoji-frown text-secondary"></i> ${data.message}`,
                    'text-secondary'
                );
                break;
            }
            case 'spoof': {
                video.className = 'ring-bad';
                setStatus(
                    `<i class="bi bi-shield-x text-danger"></i> ${data.message}`,
                    'text-danger'
                );
                break;
            }
            default:
                setStatus(
                    `<i class="bi bi-exclamation-circle text-danger"></i> ${data.error || data.message || 'Lỗi'}`,
                    'text-danger'
                );
        }
    } catch (e) {
        console.warn('frame send error:', e);
    }
}

// ── Step management ────────────────────────────────────────────────────────────

function advanceStep() {
    currentStep++;
    refreshStepIndicator();
    refreshPoseGuide();

    const step = STEPS[currentStep];
    setStatus(
        `<span class="badge bg-primary me-1">Bước ${currentStep + 1}/3</span> ${step.label}`,
        'text-primary'
    );

    // Brief pause (1.2s) so user can read the instruction, then resume
    setTimeout(() => {
        if (currentStep < STEPS.length) {
            running    = true;
            intervalId = setInterval(sendFrame, INTERVAL);
            showEl(btnPause,  true);
            showEl(btnResume, false);
        }
    }, 1200);
}

// ── Controls ───────────────────────────────────────────────────────────────────

async function startCapture() {
    btnStart.disabled = true;
    setStatus('Đang mở camera…', 'text-muted');

    const ok = await startCamera();
    if (!ok) { btnStart.disabled = false; return; }

    // Show UI elements
    poseGuide.classList.remove('d-none');
    stepProgress.classList.remove('d-none');
    overallCard.style.display = 'block';
    instructions.classList.remove('d-none');

    refreshStepIndicator();
    refreshPoseGuide();
    refreshOverall();

    showEl(btnStart,  false);
    showEl(btnPause,  true);
    showEl(btnReset,  true);

    running    = true;
    intervalId = setInterval(sendFrame, INTERVAL);

    setStatus(
        `<span class="spinner-border spinner-border-sm"></span> Bước 1/3 — ${STEPS[0].label}`,
        'text-muted'
    );
}

function pauseCapture() {
    running = false;
    clearInterval(intervalId);
    showEl(btnPause,  false);
    showEl(btnResume, true);
    setStatus(`Đã tạm dừng tại bước ${currentStep + 1}.`, 'text-muted');
}

function resumeCapture() {
    if (currentStep >= STEPS.length) return;
    running    = true;
    intervalId = setInterval(sendFrame, INTERVAL);
    showEl(btnResume, false);
    showEl(btnPause,  true);
    setStatus(
        `<span class="spinner-border spinner-border-sm"></span> Tiếp tục — ${STEPS[currentStep].label}`,
        'text-muted'
    );
}

function resetCapture() {
    running = false;
    clearInterval(intervalId);
    stopCamera();

    STEPS.forEach(s => { s.done = 0; });
    currentStep  = 0;
    totalFrames  = 0;

    thumbnailStrip.innerHTML = '';
    refreshStepIndicator();
    refreshOverall();

    poseGuide.classList.add('d-none');
    stepProgress.classList.add('d-none');
    overallCard.style.display = 'none';
    instructions.classList.add('d-none');

    showEl(btnStart,  true);
    showEl(btnPause,  false);
    showEl(btnResume, false);
    showEl(btnReset,  false);
    btnStart.disabled = false;

    setStatus('Nhấn <strong>Bắt đầu</strong> để bắt đầu lại.', 'text-muted');
}

async function showSuccess() {
    stopCamera();
    actionButtons.classList.add('d-none');
    poseGuide.classList.add('d-none');
    refreshOverall();

    // Auto-retrain SVM — mirrors old retrain_from_db() call in register_user()
    setStatus(
        '<span class="spinner-border spinner-border-sm"></span> Đang cập nhật mô hình nhận diện…',
        'text-muted'
    );
    try {
        const res = await fetch('/api/student/complete-registration', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const data = await res.json();
        if (data.status === 'success') {
            setStatus(
                `<i class="bi bi-check-circle text-success"></i> Mô hình đã cập nhật (${data.students_in_model} sinh viên, ${data.total_embeddings} mẫu)`,
                'text-success'
            );
        } else {
            setStatus(
                `<i class="bi bi-exclamation-triangle text-warning"></i> ${data.error || 'Cập nhật mô hình thất bại — admin cần retrain thủ công'}`,
                'text-warning'
            );
        }
    } catch (e) {
        setStatus(
            '<i class="bi bi-wifi-off text-warning"></i> Lỗi kết nối khi cập nhật mô hình',
            'text-warning'
        );
        console.warn('complete-registration error:', e);
    }

    successState.classList.remove('d-none');
}

// ── Events ─────────────────────────────────────────────────────────────────────

btnStart.addEventListener('click',  startCapture);
btnPause.addEventListener('click',  pauseCapture);
btnResume.addEventListener('click', resumeCapture);
btnReset.addEventListener('click',  resetCapture);

// ── Init: check existing embeddings ───────────────────────────────────────────

(async () => {
    try {
        const res = await fetch('/api/student/me', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!res.ok) return;
        const data = await res.json();
        if (data.embedding_count > 0) {
            setStatus(
                `<i class="bi bi-info-circle text-info"></i> Đã có ${data.embedding_count} mẫu trước đó. Có thể đăng ký thêm để tăng độ chính xác.`,
                'text-info'
            );
        }
    } catch (e) { /* ignore */ }
})();
