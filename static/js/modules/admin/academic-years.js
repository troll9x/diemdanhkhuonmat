// Academic Years Module — full CRUD
let currentPage = 1;

async function loadAcademicYears(page = 1) {
    showState('loading');
    const search = document.getElementById('searchInput')?.value || '';
    const active = document.getElementById('filterActive')?.value;
    let url = `/academic-years?page=${page}&per_page=10`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
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
    document.getElementById('ayTable').innerHTML = items.map(a => `
        <tr>
            <td><strong>${esc(a.year || a.name)}</strong></td>
            <td>${a.start_date || '—'}</td>
            <td>${a.end_date || '—'}</td>
            <td>${a.is_current ? '<span class="badge bg-primary">Hiện tại</span>' : '—'}</td>
            <td><span class="badge bg-${a.is_active?'success':'secondary'}">${a.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editAY(${a.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteAY(${a.id})"><i class="bi bi-trash"></i></button>
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
    if (cur > 1) h += `<li class="page-item"><a class="page-link" onclick="loadAcademicYears(${cur-1})">‹</a></li>`;
    for (let i=1;i<=p.total_pages;i++)
        h += `<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadAcademicYears(${i})">${i}</a></li>`;
    if (cur < p.total_pages) h += `<li class="page-item"><a class="page-link" onclick="loadAcademicYears(${cur+1})">›</a></li>`;
    ul.innerHTML = h;
}

function resetForm() {
    document.getElementById('ayForm').reset();
    document.getElementById('ayId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm năm học';
    document.getElementById('ayYear').disabled = false;
    clearErrors();
}

async function editAY(id) {
    try {
        const a = await api.get(`/academic-years/${id}`);
        document.getElementById('ayId').value         = a.id;
        document.getElementById('ayYear').value        = a.year || a.name || '';
        document.getElementById('ayYear').disabled     = true;
        document.getElementById('ayStart').value       = a.start_date || '';
        document.getElementById('ayEnd').value         = a.end_date || '';
        document.getElementById('ayCurrent').checked  = a.is_current;
        document.getElementById('ayActive').checked   = a.is_active;
        document.getElementById('modalTitle').textContent = 'Sửa năm học';
        clearErrors();
        new bootstrap.Modal(document.getElementById('ayModal')).show();
    } catch(e) { showAlert('Lỗi: ' + e.message, 'danger'); }
}

async function saveAY(e) {
    e.preventDefault(); clearErrors();
    const id    = document.getElementById('ayId').value;
    const year  = document.getElementById('ayYear').value.trim();
    const start = document.getElementById('ayStart').value;
    const end   = document.getElementById('ayEnd').value;
    if (!year)  { showFieldError('yearError','Năm học là bắt buộc'); return; }
    if (!start) { showFieldError('startError','Ngày bắt đầu là bắt buộc'); return; }
    if (!end)   { showFieldError('endError','Ngày kết thúc là bắt buộc'); return; }
    setLoading(true);
    try {
        const body = { year, start_date: start, end_date: end,
            is_current: document.getElementById('ayCurrent').checked,
            is_active:  document.getElementById('ayActive').checked };
        const res = await api[id?'put':'post'](id?`/academic-years/${id}`:'/academic-years', body);
        showAlert(res.message || 'Lưu thành công', 'success');
        bootstrap.Modal.getInstance(document.getElementById('ayModal')).hide();
        loadAcademicYears(currentPage);
    } catch(err) { showAlert('Lỗi: ' + err.message, 'danger'); }
    finally { setLoading(false); }
}

async function deleteAY(id) {
    if (!confirm('Xóa năm học này?')) return;
    try {
        const res = await api.delete(`/academic-years/${id}`);
        showAlert(res.message || 'Đã xóa', 'success');
        loadAcademicYears(currentPage);
    } catch(e) { showAlert('Lỗi: ' + e.message, 'danger'); }
}

// helpers
function showState(s) {
    document.getElementById('loadingState').classList.toggle('d-none', s!=='loading');
    document.getElementById('emptyState').classList.toggle('d-none', s!=='empty');
    document.getElementById('tableContainer').classList.toggle('d-none', s!=='table');
    if (['done','empty','table'].includes(s)) document.getElementById('loadingState').classList.add('d-none');
}
function showAlert(msg, type='info') {
    const el=document.createElement('div'); el.className=`alert alert-${type} alert-dismissible fade show`;
    el.innerHTML=`${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    document.getElementById('alertContainer').appendChild(el); setTimeout(()=>el.remove(),5000);
}
function showFieldError(id,msg){const e=document.getElementById(id);if(e){e.textContent=msg;e.classList.remove('d-none');}}
function clearErrors(){document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');});}
function setLoading(on){
    document.getElementById('submitBtnText').classList.toggle('d-none',on);
    document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);
    document.getElementById('submitBtn').disabled=on;
}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
