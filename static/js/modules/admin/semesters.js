// Semesters Module — full CRUD
let currentPage = 1;

async function loadAcademicYears() {
    try {
        const data = await api.get('/academic-years?per_page=100');
        (data.items || []).forEach(a => {
            const sel = document.getElementById('filterAY');
            if (sel) { const o=document.createElement('option');o.value=a.id;o.textContent=a.year||a.name;sel.appendChild(o); }
            const sel2 = document.getElementById('smAY');
            if (sel2) { const o=document.createElement('option');o.value=a.id;o.textContent=a.year||a.name;sel2.appendChild(o); }
        });
    } catch(e) { console.error(e); }
}

async function loadSemesters(page = 1) {
    showState('loading');
    const search = document.getElementById('searchInput')?.value || '';
    const ayId   = document.getElementById('filterAY')?.value;
    const active = document.getElementById('filterActive')?.value;
    let url = `/semesters?page=${page}&per_page=10`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
    if (ayId)   url += `&academic_year_id=${ayId}`;
    if (active) url += `&is_active=${active}`;
    try {
        const data = await api.get(url);
        renderTable(data.items || []);
        renderPagination(data.pagination || {}, page);
        currentPage = page;
    } catch(e) { showAlert('Lỗi: ' + e.message, 'danger'); }
    finally { showState('done'); }
}

function renderTable(items) {
    if (!items.length) { showState('empty'); return; }
    showState('table');
    document.getElementById('semTable').innerHTML = items.map(s => `
        <tr>
            <td><span class="badge bg-info">${esc(s.code)}</span></td>
            <td><strong>${esc(s.name)}</strong></td>
            <td>${esc(s.academic_year?.year || s.academic_year_id || '—')}</td>
            <td>${s.start_date || '—'}</td>
            <td>${s.end_date || '—'}</td>
            <td>${s.is_current ? '<span class="badge bg-primary">Hiện tại</span>' : '—'}</td>
            <td><span class="badge bg-${s.is_active?'success':'secondary'}">${s.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editSem(${s.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteSem(${s.id})"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderPagination(p, cur) {
    const wrap=document.getElementById('paginationContainer'),ul=document.getElementById('paginationList');
    if(!p.total_pages||p.total_pages<=1){wrap?.classList.add('d-none');return;}
    wrap?.classList.remove('d-none');
    let h='';
    if(cur>1) h+=`<li class="page-item"><a class="page-link" onclick="loadSemesters(${cur-1})">‹</a></li>`;
    for(let i=1;i<=p.total_pages;i++) h+=`<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadSemesters(${i})">${i}</a></li>`;
    if(cur<p.total_pages) h+=`<li class="page-item"><a class="page-link" onclick="loadSemesters(${cur+1})">›</a></li>`;
    ul.innerHTML=h;
}

function resetForm() {
    document.getElementById('semForm').reset();
    document.getElementById('semId').value='';
    document.getElementById('modalTitle').textContent='Thêm học kỳ';
    document.getElementById('smCode').disabled=false;
    clearErrors();
}

async function editSem(id) {
    try {
        const s = await api.get(`/semesters/${id}`);
        document.getElementById('semId').value      = s.id;
        document.getElementById('smCode').value     = s.code;
        document.getElementById('smCode').disabled  = true;
        document.getElementById('smName').value     = s.name;
        document.getElementById('smAY').value       = s.academic_year_id || '';
        document.getElementById('smStart').value    = s.start_date || '';
        document.getElementById('smEnd').value      = s.end_date || '';
        document.getElementById('smCurrent').checked= s.is_current;
        document.getElementById('smActive').checked = s.is_active;
        document.getElementById('modalTitle').textContent='Sửa học kỳ';
        clearErrors();
        new bootstrap.Modal(document.getElementById('semModal')).show();
    } catch(e) { showAlert('Lỗi: '+e.message,'danger'); }
}

async function saveSem(e) {
    e.preventDefault(); clearErrors();
    const id    = document.getElementById('semId').value;
    const code  = document.getElementById('smCode').value.trim().toUpperCase();
    const name  = document.getElementById('smName').value.trim();
    const ay    = document.getElementById('smAY').value;
    const start = document.getElementById('smStart').value;
    const end   = document.getElementById('smEnd').value;
    if(!code)  {showFieldError('codeError','Mã là bắt buộc');return;}
    if(!name)  {showFieldError('nameError','Tên là bắt buộc');return;}
    if(!ay)    {showFieldError('ayError','Năm học là bắt buộc');return;}
    if(!start) {showFieldError('startError','Ngày bắt đầu là bắt buộc');return;}
    if(!end)   {showFieldError('endError','Ngày kết thúc là bắt buộc');return;}
    setLoading(true);
    try {
        const body={code,name,academic_year_id:parseInt(ay),start_date:start,end_date:end,
            is_current:document.getElementById('smCurrent').checked,
            is_active:document.getElementById('smActive').checked};
        const res=await api[id?'put':'post'](id?`/semesters/${id}`:'/semesters',body);
        showAlert(res.message||'Lưu thành công','success');
        bootstrap.Modal.getInstance(document.getElementById('semModal')).hide();
        loadSemesters(currentPage);
    } catch(err){showAlert('Lỗi: '+err.message,'danger');}
    finally{setLoading(false);}
}

async function deleteSem(id) {
    if(!confirm('Xóa học kỳ này?')) return;
    try{const res=await api.delete(`/semesters/${id}`);showAlert(res.message||'Đã xóa','success');loadSemesters(currentPage);}
    catch(e){showAlert('Lỗi: '+e.message,'danger');}
}

function showState(s){
    document.getElementById('loadingState').classList.toggle('d-none',s!=='loading');
    document.getElementById('emptyState').classList.toggle('d-none',s!=='empty');
    document.getElementById('tableContainer').classList.toggle('d-none',s!=='table');
    if(['done','empty','table'].includes(s)) document.getElementById('loadingState').classList.add('d-none');
}
function showAlert(msg,type='info'){const el=document.createElement('div');el.className=`alert alert-${type} alert-dismissible fade show`;el.innerHTML=`${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;document.getElementById('alertContainer').appendChild(el);setTimeout(()=>el.remove(),5000);}
function showFieldError(id,msg){const e=document.getElementById(id);if(e){e.textContent=msg;e.classList.remove('d-none');}}
function clearErrors(){document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');});}
function setLoading(on){document.getElementById('submitBtnText').classList.toggle('d-none',on);document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);document.getElementById('submitBtn').disabled=on;}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
