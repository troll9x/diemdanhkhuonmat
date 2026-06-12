/**
 * Module Điểm Danh Sinh Viên (Student Check-in)
 * Luồng xử lý:
 *   1. Lấy danh sách phiên điểm danh đang mở
 *   2. Sinh viên chọn phiên → hiện bảng điều khiển camera
 *   3. Lấy vị trí GPS → mở camera → chụp frame
 *   4. Gửi ảnh + tọa độ lên API check-in → hiện kết quả
 */

// ID phiên được chọn trước từ URL/trang (nếu có), hoặc null nếu chưa chọn
let selectedSessionId = PAGE_SESSION_ID || null;

// Luồng video webcam (MediaStream)
let webcamStream = null;

/**
 * Bảng ánh xạ trạng thái check-in → cấu hình UI (màu sắc, icon, thông báo).
 * Mỗi key là mã status từ backend, value là cấu hình Bootstrap alert.
 */
const STATUS_UI = {
    success:          { cls: 'success',   icon: 'bi-check-circle-fill',  text: 'Điểm danh thành công' },
    success_late:     { cls: 'warning',   icon: 'bi-clock-fill',         text: 'Điểm danh thành công — Muộn giờ' },
    already_checked_in: { cls: 'info',   icon: 'bi-info-circle-fill',   text: 'Bạn đã điểm danh rồi' },
    mismatch:         { cls: 'danger',    icon: 'bi-x-circle-fill',      text: 'Khuôn mặt không khớp' },
    no_face:          { cls: 'warning',   icon: 'bi-camera-video-off',   text: 'Không phát hiện khuôn mặt' },
    too_far:          { cls: 'danger',    icon: 'bi-geo-alt-fill',       text: 'Quá xa giảng viên' },
    session_closed:   { cls: 'secondary', icon: 'bi-stop-circle',        text: 'Phiên đã kết thúc' },
    spoof:            { cls: 'danger',    icon: 'bi-shield-x',           text: 'Phát hiện giả mạo' },
    not_enrolled:     { cls: 'danger',    icon: 'bi-person-x',           text: 'Không thuộc lớp này' },
};

/**
 * Tải danh sách phiên điểm danh đang mở.
 * Nếu đã có selectedSessionId (từ URL), chuyển thẳng vào bảng điều khiển.
 * Hiện danh sách phiên với nút "Điểm danh" cho từng phiên chưa tham gia.
 * Phiên đã điểm danh sẽ hiện badge "Đã điểm danh" thay vì nút.
 */
async function loadSessions() {
    if (selectedSessionId) {
        // Đã có phiên từ URL — vào trực tiếp bảng điều khiển
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
        // Render danh sách phiên
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

/**
 * Hiện bảng điều khiển camera để thực hiện điểm danh.
 * Ẩn bảng danh sách phiên, lưu sessionId đã chọn, cập nhật tiêu đề.
 * @param {number} sessionId - ID phiên điểm danh
 * @param {string} label     - Nhãn hiển thị (tên lớp + loại phiên)
 */
function showCheckinPanel(sessionId, label) {
    selectedSessionId = sessionId;
    document.getElementById('sessionSelector').style.display = 'none';
    document.getElementById('checkinPanel').style.display = '';
    document.getElementById('checkinTitle').textContent = label || `Điểm danh — Phiên #${sessionId}`;
}

/**
 * Huỷ bỏ điểm danh — dừng webcam, xoá trạng thái, quay lại danh sách phiên.
 */
function cancelCheckin() {
    stopWebcam();
    selectedSessionId = null;
    document.getElementById('sessionSelector').style.display = '';
    document.getElementById('checkinPanel').style.display = 'none';
    document.getElementById('resultBox').style.display = 'none';
    document.getElementById('checkinControls').style.display = '';
    loadSessions();
}

/**
 * Thực hiện điểm danh bằng khuôn mặt + GPS.
 * Luồng xử lý:
 *   1. Lấy toạ độ GPS (timeout 10 giây)
 *   2. Mở webcam, chờ 1.5 giây cho ảnh ổn định
 *   3. Chụp frame JPEG (chất lượng 85%)
 *   4. Gửi FormData (image + latitude + longitude) lên API
 *   5. Hiện kết quả (thành công/lỗi/muộn/giả mạo...)
 * Trạng thái 'success' + is_late=true → hiển thị dạng 'success_late' (màu vàng).
 */
async function startCheckin() {
    const btn = document.getElementById('checkinBtn');
    const sp  = document.getElementById('checkinSpinner');
    btn.disabled = true;           // Vô hiệu nút để tránh bấm nhiều lần
    sp.classList.remove('d-none'); // Hiện spinner loading
    showResult(null);              // Xoá kết quả cũ

    try {
        // Bước 1: Lấy vị trí GPS
        const pos = await new Promise((resolve, reject) =>
            navigator.geolocation.getCurrentPosition(resolve, reject, { timeout: 10000 }));
        const lat = pos.coords.latitude;
        const lon = pos.coords.longitude;

        // Bước 2: Mở webcam
        const cam = document.getElementById('webcam');
        webcamStream = await navigator.mediaDevices.getUserMedia({ video: true });
        cam.srcObject = webcamStream;
        cam.classList.remove('d-none');

        // Chờ 1.5 giây để camera lấy nét và ổn định độ sáng
        await new Promise(r => setTimeout(r, 1500));

        // Bước 3: Chụp frame vào canvas rồi chuyển sang Blob
        const canvas = document.createElement('canvas');
        canvas.width  = cam.videoWidth  || 320;
        canvas.height = cam.videoHeight || 240;
        canvas.getContext('2d').drawImage(cam, 0, 0);
        const blob = await new Promise(r => canvas.toBlob(r, 'image/jpeg', 0.85));

        stopWebcam(); // Tắt camera ngay sau khi chụp

        // Bước 4: Gửi dữ liệu lên API check-in
        const fd = new FormData();
        fd.append('image', blob, 'checkin.jpg');
        fd.append('latitude', lat);
        fd.append('longitude', lon);

        const data = await api.studentCheckinV2(selectedSessionId, fd);
        // Nếu điểm danh thành công nhưng muộn → đổi status để hiện cảnh báo vàng
        if (data.status === 'success' && data.is_late) data.status = 'success_late';
        showResult(data);
    } catch (e) {
        // e.code có khi lỗi GPS (GeolocationPositionError)
        if (e.code) {
            showResult({ status: 'error', message: 'Không thể lấy GPS: ' + e.message });
        } else {
            showResult({ status: 'error', message: e.message });
        }
    } finally {
        btn.disabled = false;         // Bật lại nút
        sp.classList.add('d-none');   // Ẩn spinner
    }
}

/**
 * Hiện kết quả điểm danh dưới dạng Bootstrap alert.
 * Hiện thêm độ tin cậy (confidence) và khoảng cách GPS nếu có.
 * Nếu thành công: hiện nút "Xem lịch sử" và ẩn nút điểm danh.
 * Nếu thất bại: hiện nút "Quay lại" để thử lại.
 * @param {object|null} data - Dữ liệu kết quả từ API, hoặc null để ẩn
 */
function showResult(data) {
    const box = document.getElementById('resultBox');
    if (!data) { box.style.display = 'none'; return; }

    // Lấy cấu hình UI theo status, fallback về màu xám nếu status lạ
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
    // Ẩn bảng điều khiển camera nếu điểm danh thành công
    document.getElementById('checkinControls').style.display = data.status === 'success' ? 'none' : '';
}

/**
 * Dừng webcam — tắt tất cả track media và ẩn phần tử video.
 */
function stopWebcam() {
    if (webcamStream) {
        webcamStream.getTracks().forEach(t => t.stop());
        webcamStream = null;
    }
    document.getElementById('webcam').classList.add('d-none');
}

/**
 * Escape HTML để ngăn XSS khi render nội dung từ server vào innerHTML.
 * Thay thế các ký tự đặc biệt: & < > " '
 * @param {string} str - Chuỗi cần escape
 * @returns {string} Chuỗi đã được escape
 */
function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Tải danh sách phiên ngay khi trang khởi động
loadSessions();
