/**
 * Module Tham Gia Lớp Học (Student Join Class)
 * Cho phép sinh viên nhập mã lớp (và tùy chọn mã sinh viên) để tham gia lớp.
 * Sau khi tham gia thành công, tải lại danh sách lớp hiện tại.
 */

/**
 * Xử lý tham gia lớp học.
 * Lấy mã lớp từ input, chuyển thành chữ hoa, gửi lên API.
 * Hiện thông báo thành công/lỗi và tải lại danh sách lớp.
 */
async function joinClass() {
    const code = document.getElementById('classCode').value.trim().toUpperCase();
    if (!code) {
        showAlert('Vui lòng nhập mã lớp', 'warning');
        return;
    }
    // Mã sinh viên là tùy chọn — một số lớp yêu cầu xác minh mã sinh viên
    const studentCode = document.getElementById('studentCode').value.trim();
    const btn = document.getElementById('joinBtnText').parentElement;
    const sp  = document.getElementById('joinSpinner');
    btn.disabled = true;           // Vô hiệu nút để tránh bấm nhiều lần
    sp.classList.remove('d-none'); // Hiện spinner loading

    try {
        const data = await api.studentJoinClass(code, studentCode || undefined);
        showAlert(data.message || 'Tham gia lớp thành công!', 'success');
        // Xóa các input sau khi tham gia thành công
        document.getElementById('classCode').value = '';
        document.getElementById('studentCode').value = '';
        loadMyClasses(); // Tải lại danh sách lớp
    } catch (e) {
        showAlert(e.message || 'Lỗi tham gia lớp', 'danger');
    } finally {
        btn.disabled = false;         // Bật lại nút
        sp.classList.add('d-none');   // Ẩn spinner
    }
}

/**
 * Tải danh sách lớp học sinh viên đã tham gia.
 * Hiển thị tên lớp, tên giáo viên, mã lớp, ngày tham gia,
 * và trạng thái điểm danh hôm nay (nếu có phiên đang mở).
 */
async function loadMyClasses() {
    const list = document.getElementById('myClassesList');
    try {
        const data = await api.studentGetClasses();
        if (!data.classes || data.classes.length === 0) {
            list.innerHTML = '<div class="text-center py-4 text-muted">Chưa tham gia lớp nào.</div>';
            return;
        }
        list.innerHTML = data.classes.map(c => `
            <div class="d-flex justify-content-between align-items-center p-3 border-bottom">
                <div>
                    <strong>${escHtml(c.name)}</strong>
                    <small class="text-muted ms-2">${c.teacher_name}</small>
                    <br><small class="text-muted">Mã lớp: <code>${c.class_code}</code> — Tham gia: ${new Date(c.joined_at).toLocaleDateString('vi-VN')}</small>
                </div>
                ${c.today_session
                    ? (c.today_session.already_checked_in
                        ? '<span class="badge bg-success">Đã điểm danh hôm nay</span>'
                        : '<span class="badge bg-warning text-dark">Chưa điểm danh</span>')
                    : ''}
            </div>`).join('');
    } catch (e) {
        list.innerHTML = `<div class="alert alert-danger">${e.message}</div>`;
    }
}

/**
 * Hiện thông báo Bootstrap alert trong #alertBox.
 * Alert có nút đóng (dismissible) và tự xoá khi bấm nút.
 * @param {string} msg  - Nội dung thông báo
 * @param {string} type - Loại Bootstrap alert (info/success/danger/warning)
 */
function showAlert(msg, type = 'info') {
    const box = document.getElementById('alertBox');
    box.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
        ${msg}<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
}

/**
 * Escape HTML để ngăn XSS khi chèn chuỗi từ server vào innerHTML.
 */
function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Nhấn Enter trong ô mã lớp → tự động gọi joinClass()
document.getElementById('classCode').addEventListener('keydown', e => {
    if (e.key === 'Enter') joinClass();
});

// Tải danh sách lớp ngay khi trang khởi động
loadMyClasses();
