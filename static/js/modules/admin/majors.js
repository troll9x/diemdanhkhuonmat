/**
 * Module Quản Lý Chuyên Ngành (Admin Majors)
 * CRUD chuyên ngành: tạo/sửa/xóa chuyên ngành, gắn với khoa.
 * Hàm chính:
 *   loadDepartments()       — Tải danh sách khoa vào dropdown form và bộ lọc
 *   loadMajors(page)        — Tải và phân trang danh sách chuyên ngành
 *   renderTable(items)      — Render bảng chuyên ngành (mã, tên, khoa, trạng thái)
 *   renderPagination()      — Render điều hướng phân trang
 *   openModal(item)         — Mở modal tạo mới hoặc chỉnh sửa chuyên ngành
 *   saveItem(event)         — Lưu chuyên ngành (POST hoặc PUT)
 *   deleteItem(id)          — Xóa chuyên ngành sau khi xác nhận
 *   showState(s)            — Chuyển trạng thái UI: loading / empty / table
 *   showAlert(msg,type)     — Hiện Bootstrap alert
 *   esc(str)                — Escape HTML ngăn XSS
 */
let currentPage = 1;
const PER_PAGE  = 10;

// ── Load departments for dropdowns ────────────────────────────────────────────

async function loadDepartments() {
    try {
        const data = await api.get('/departments?per_page=100');
        const items = data.items || [];
        ['mjDepartment', 'filterDepartment'].forEach(id => {
            const sel = document.getElementById(id);
            if (!sel) return;
            items.forEach(d => {
                const o = document.createElement('option');
                o.value = d.id;
                o.textContent = d.name;
                sel.appendChild(o);
            });
        });
    } catch(e) {
        console.error('loadDepartments error:', e);
    }
}

// ── List ──────────────────────────────────────────────────────────────────────

async function loadMajors(page = 1) {
    showState('loading');
    const search = document.getElementById('searchInput')?.value || '';
    const deptId = document.getElementById('filterDepartment')?.value;
    const active = document.getElementById('filterActive')?.value;

    let url = `/majors?page=${page}&per_page=${PER_PAGE}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (deptId) url += `&department_id=${deptId}`;
    if (active) url += `&is_active=${active}`;

    try {
        const data = await api.get(url);
        renderTable(data.items || []);
        renderPagination(data.pagination || {}, page);
        currentPage = page;
    } catch(e) {
        showAlert('Lỗi khi tải dữ liệu: ' + e.message, 'danger');
    } finally {
        showState('done');
    }
}

function renderTable(items) {
    const tbody = document.getElementById('majorsTable');
    if (!items.length) { showState('empty'); return; }

    showState('table');
    tbody.innerHTML = items.map(m => `
        <tr>
            <td><span class="badge bg-info">${esc(m.code)}</span></td>
            <td><strong>${esc(m.name)}</strong></td>
            <td>${esc(m.department?.name || '—')}</td>
            <td><small>${esc(m.description || '—')}</small></td>
            <td>
                <span class="badge bg-${m.is_active ? 'success' : 'secondary'}">
                    ${m.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editMajor(${m.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteMajor(${m.id})" title="Xóa">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderPagination(p, cur) {
    const wrap = document.getElementById('paginationContainer');
    const ul   = document.getElementById('paginationList');
    if (!p.total_pages || p.total_pages <= 1) { wrap.classList.add('d-none'); return; }
    wrap.classList.remove('d-none');
    let html = '';
    if (cur > 1) html += `<li class="page-item"><a class="page-link" onclick="loadMajors(${cur-1})">‹</a></li>`;
    for (let i = 1; i <= p.total_pages; i++) {
        html += `<li class="page-item ${i===cur?'active':''}">
            <a class="page-link" onclick="loadMajors(${i})">${i}</a></li>`;
    }
    if (cur < p.total_pages) html += `<li class="page-item"><a class="page-link" onclick="loadMajors(${cur+1})">›</a></li>`;
    ul.innerHTML = html;
}

// ── Create / Edit ─────────────────────────────────────────────────────────────

function resetForm() {
    document.getElementById('majorForm').reset();
    document.getElementById('majorId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới chuyên ngành';
    document.getElementById('mjCode').disabled = false;
    clearErrors();
}

async function editMajor(id) {
    try {
        const m = await api.get(`/majors/${id}`);
        document.getElementById('majorId').value          = m.id;
        document.getElementById('mjCode').value           = m.code;
        document.getElementById('mjCode').disabled        = true;
        document.getElementById('mjName').value           = m.name;
        document.getElementById('mjDescription').value    = m.description || '';
        document.getElementById('mjDepartment').value     = m.department?.id || '';
        document.getElementById('mjActive').checked       = m.is_active;
        document.getElementById('modalTitle').textContent = 'Sửa chuyên ngành';
        clearErrors();
        new bootstrap.Modal(document.getElementById('majorModal')).show();
    } catch(e) {
        showAlert('Lỗi khi tải dữ liệu: ' + e.message, 'danger');
    }
}

async function saveMajor(e) {
    e.preventDefault();
    clearErrors();
    const id   = document.getElementById('majorId').value;
    const code = document.getElementById('mjCode').value.trim().toUpperCase();
    const name = document.getElementById('mjName').value.trim();
    const dept = document.getElementById('mjDepartment').value || null;
    const desc = document.getElementById('mjDescription').value.trim();
    const active = document.getElementById('mjActive').checked;

    if (!code) { showFieldError('codeError', 'Mã là bắt buộc'); return; }
    if (!name) { showFieldError('nameError', 'Tên là bắt buộc'); return; }

    setLoading(true);
    try {
        const method = id ? 'PUT'  : 'POST';
        const url    = id ? `/majors/${id}` : '/majors';
        const body   = { code, name, description: desc || null, department_id: dept ? parseInt(dept) : null, is_active: active };
        const res    = await api[id ? 'put' : 'post'](url, body);

        showAlert(res.message || 'Lưu thành công', 'success');
        bootstrap.Modal.getInstance(document.getElementById('majorModal')).hide();
        loadMajors(currentPage);
    } catch(err) {
        if (err.message?.includes('code') || err.message?.includes('Code')) {
            showFieldError('codeError', err.message);
        } else {
            showAlert('Lỗi: ' + err.message, 'danger');
        }
    } finally {
        setLoading(false);
    }
}

// ── Delete ────────────────────────────────────────────────────────────────────

async function deleteMajor(id) {
    if (!confirm('Xóa chuyên ngành này?')) return;
    try {
        const res = await api.delete(`/majors/${id}`);
        showAlert(res.message || 'Đã xóa', 'success');
        loadMajors(currentPage);
    } catch(e) {
        showAlert('Lỗi: ' + e.message, 'danger');
    }
}

// ── UI helpers ────────────────────────────────────────────────────────────────

function showState(state) {
    document.getElementById('loadingState').classList.toggle('d-none', state !== 'loading');
    document.getElementById('emptyState').classList.toggle('d-none',   state !== 'empty');
    document.getElementById('tableContainer').classList.toggle('d-none', state !== 'table');
    if (state === 'done' || state === 'empty' || state === 'table') {
        document.getElementById('loadingState').classList.add('d-none');
    }
}

function showAlert(msg, type = 'info') {
    const el  = document.createElement('div');
    el.className = `alert alert-${type} alert-dismissible fade show`;
    el.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.getElementById('alertContainer').appendChild(el);
    setTimeout(() => el.remove(), 5000);
}

function showFieldError(id, msg) {
    const el = document.getElementById(id);
    if (el) { el.textContent = msg; el.classList.remove('d-none'); }
}

function clearErrors() {
    document.querySelectorAll('[id$="Error"]').forEach(el => { el.textContent = ''; el.classList.add('d-none'); });
}

function setLoading(on) {
    const btn = document.getElementById('submitBtn');
    document.getElementById('submitBtnText').classList.toggle('d-none', on);
    document.getElementById('submitBtnSpinner').classList.toggle('d-none', !on);
    btn.disabled = on;
}

function esc(t) {
    const d = document.createElement('div'); d.textContent = t || ''; return d.innerHTML;
}
