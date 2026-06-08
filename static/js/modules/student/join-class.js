// Student Join Class JS
async function joinClass() {
    const code = document.getElementById('classCode').value.trim().toUpperCase();
    if (!code) {
        showAlert('Vui lòng nhập mã lớp', 'warning');
        return;
    }
    const studentCode = document.getElementById('studentCode').value.trim();
    const btn = document.getElementById('joinBtnText').parentElement;
    const sp  = document.getElementById('joinSpinner');
    btn.disabled = true;
    sp.classList.remove('d-none');

    try {
        const data = await api.studentJoinClass(code, studentCode || undefined);
        showAlert(data.message || 'Tham gia lớp thành công!', 'success');
        document.getElementById('classCode').value = '';
        document.getElementById('studentCode').value = '';
        loadMyClasses();
    } catch (e) {
        showAlert(e.message || 'Lỗi tham gia lớp', 'danger');
    } finally {
        btn.disabled = false;
        sp.classList.add('d-none');
    }
}

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

function showAlert(msg, type = 'info') {
    const box = document.getElementById('alertBox');
    box.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show">
        ${msg}<button class="btn-close" data-bs-dismiss="alert"></button></div>`;
}

function escHtml(str) {
    return String(str || '').replace(/[&<>"']/g, c =>
        ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Enter key triggers join
document.getElementById('classCode').addEventListener('keydown', e => {
    if (e.key === 'Enter') joinClass();
});

loadMyClasses();
