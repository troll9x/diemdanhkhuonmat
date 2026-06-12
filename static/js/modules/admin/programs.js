/**
 * Module Quản Lý Chương Trình Học (Admin Programs)
 * CRUD chương trình đào tạo: tạo/sửa/xóa chương trình, liên kết với khoa.
 * Hàm chính:
 *   loadDepartments()       — Tải danh sách khoa vào dropdown form và bộ lọc
 *   loadPrograms(page)      — Tải và phân trang danh sách chương trình học
 *   renderTable(items)      — Render bảng chương trình (mã, tên, khoa, tín chỉ, trạng thái)
 *   renderPagination()      — Render điều hướng phân trang
 *   openModal(item)         — Mở modal tạo mới hoặc chỉnh sửa chương trình
 *   saveItem(event)         — Lưu chương trình (POST hoặc PUT)
 *   deleteItem(id)          — Xóa chương trình sau khi xác nhận
 *   showState(s)            — Chuyển trạng thái UI: loading / empty / table
 *   showAlert(msg,type)     — Hiện Bootstrap alert
 *   esc(str)                — Escape HTML ngăn XSS
 */
let currentPage = 1;

async function loadDepartments() {
    try {
        const data = await api.get('/departments?per_page=100');
        (data.items || []).forEach(d => {
            ['pgDepartment', 'filterDepartment'].forEach(id => {
                const sel = document.getElementById(id);
                if (!sel) return;
                const o = document.createElement('option');
                o.value = d.id; o.textContent = d.name;
                sel.appendChild(o);
            });
        });
    } catch(e) { console.error(e); }
}

async function loadPrograms(page = 1) {
    showState('loading');
    const search = document.getElementById('searchInput')?.value || '';
    const deptId = document.getElementById('filterDepartment')?.value;
    const active = document.getElementById('filterActive')?.value;
    let url = `/programs?page=${page}&per_page=10`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (deptId) url += `&department_id=${deptId}`;
    if (active) url += `&is_active=${active}`;
    try {
        const data = await api.get(url);
        renderTable(data.items || []);
        renderPagination(data.pagination || {}, page);
        currentPage = page;
    } catch(e) { showAlert('Lỗi tải dữ liệu: ' + e.message, 'danger'); }
    finally { showState('done'); }
}

function renderTable(items) {
    if (!items.length) { showState('empty'); return; }
    showState('table');
    document.getElementById('programsTable').innerHTML = items.map(p => `
        <tr>
            <td><span class="badge bg-info">${esc(p.code)}</span></td>
            <td><strong>${esc(p.name)}</strong></td>
            <td>${esc(p.department?.name || '—')}</td>
            <td>${p.duration_years ? p.duration_years + ' năm' : '—'}</td>
            <td><span class="badge bg-${p.is_active?'success':'secondary'}">${p.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editProgram(${p.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteProgram(${p.id})"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderPagination(p, cur) {
    const wrap = document.getElementById('paginationContainer');
    const ul   = document.getElementById('paginationList');
    if (!p.total_pages || p.total_pages <= 1) { wrap?.classList.add('d-none'); return; }
    wrap?.classList.remove('d-none');
    let h = '';
    if (cur > 1) h += `<li class="page-item"><a class="page-link" onclick="loadPrograms(${cur-1})">‹</a></li>`;
    for (let i = 1; i <= p.total_pages; i++)
        h += `<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadPrograms(${i})">${i}</a></li>`;
    if (cur < p.total_pages) h += `<li class="page-item"><a class="page-link" onclick="loadPrograms(${cur+1})">›</a></li>`;
    ul.innerHTML = h;
}

function resetForm() {
    document.getElementById('programForm').reset();
    document.getElementById('programId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới chương trình';
    document.getElementById('pgCode').disabled = false;
    clearErrors();
}

async function editProgram(id) {
    try {
        const p = await api.get(`/programs/${id}`);
        document.getElementById('programId').value        = p.id;
        document.getElementById('pgCode').value           = p.code;
        document.getElementById('pgCode').disabled        = true;
        document.getElementById('pgName').value           = p.name;
        document.getElementById('pgDuration').value       = p.duration_years || '';
        document.getElementById('pgDescription').value    = p.description || '';
        document.getElementById('pgDepartment').value     = p.department?.id || '';
        document.getElementById('pgActive').checked       = p.is_active;
        document.getElementById('modalTitle').textContent = 'Sửa chương trình';
        clearErrors();
        new bootstrap.Modal(document.getElementById('programModal')).show();
    } catch(e) { showAlert('Lỗi: ' + e.message, 'danger'); }
}

async function saveProgram(e) {
    e.preventDefault(); clearErrors();
    const id   = document.getElementById('programId').value;
    const code = document.getElementById('pgCode').value.trim().toUpperCase();
    const name = document.getElementById('pgName').value.trim();
    if (!code) { showFieldError('codeError','Mã là bắt buộc'); return; }
    if (!name) { showFieldError('nameError','Tên là bắt buộc'); return; }
    setLoading(true);
    try {
        const body = {
            code, name,
            duration_years: parseInt(document.getElementById('pgDuration').value) || null,
            description: document.getElementById('pgDescription').value.trim() || null,
            department_id: document.getElementById('pgDepartment').value || null,
            is_active: document.getElementById('pgActive').checked
        };
        const res = await api[id ? 'put' : 'post'](id ? `/programs/${id}` : '/programs', body);
        showAlert(res.message || 'Lưu thành công', 'success');
        bootstrap.Modal.getInstance(document.getElementById('programModal')).hide();
        loadPrograms(currentPage);
    } catch(err) { showAlert('Lỗi: ' + err.message, 'danger'); }
    finally { setLoading(false); }
}

async function deleteProgram(id) {
    if (!confirm('Xóa chương trình này?')) return;
    try {
        const res = await api.delete(`/programs/${id}`);
        showAlert(res.message || 'Đã xóa', 'success');
        loadPrograms(currentPage);
    } catch(e) { showAlert('Lỗi: ' + e.message, 'danger'); }
}

// ── helpers ───────────────────────────────────────────────────────────────────
function showState(s) {
    document.getElementById('loadingState').classList.toggle('d-none', s!=='loading');
    document.getElementById('emptyState').classList.toggle('d-none', s!=='empty');
    document.getElementById('tableContainer').classList.toggle('d-none', s!=='table');
    if (['done','empty','table'].includes(s)) document.getElementById('loadingState').classList.add('d-none');
}
function showAlert(msg, type='info') {
    const el = document.createElement('div');
    el.className = `alert alert-${type} alert-dismissible fade show`;
    el.innerHTML = `${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.getElementById('alertContainer').appendChild(el);
    setTimeout(() => el.remove(), 5000);
}
function showFieldError(id, msg) { const e=document.getElementById(id); if(e){e.textContent=msg;e.classList.remove('d-none');} }
function clearErrors() { document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');}); }
function setLoading(on) {
    document.getElementById('submitBtnText').classList.toggle('d-none',on);
    document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);
    document.getElementById('submitBtn').disabled=on;
}
function esc(t) { const d=document.createElement('div');d.textContent=t||'';return d.innerHTML; }
