// Campuses Module — full CRUD
let currentPage = 1;

async function loadCampuses(page = 1) {
    showState('loading');
    const search = document.getElementById('searchInput')?.value || '';
    const active = document.getElementById('filterActive')?.value;
    let url = `/campuses?page=${page}&per_page=10`;
    if (search) url += `&search=${encodeURIComponent(search)}`;
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
    document.getElementById('campusTable').innerHTML = items.map(c => `
        <tr>
            <td><span class="badge bg-info">${esc(c.code)}</span></td>
            <td><strong>${esc(c.name)}</strong></td>
            <td>${esc(c.address || '—')}</td>
            <td>${esc(c.phone || '—')}</td>
            <td><span class="badge bg-${c.is_active?'success':'secondary'}">${c.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editCampus(${c.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteCampus(${c.id})"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderPagination(p, cur) {
    const wrap=document.getElementById('paginationContainer'),ul=document.getElementById('paginationList');
    if(!p.total_pages||p.total_pages<=1){wrap?.classList.add('d-none');return;}
    wrap?.classList.remove('d-none');
    let h='';
    if(cur>1) h+=`<li class="page-item"><a class="page-link" onclick="loadCampuses(${cur-1})">‹</a></li>`;
    for(let i=1;i<=p.total_pages;i++) h+=`<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadCampuses(${i})">${i}</a></li>`;
    if(cur<p.total_pages) h+=`<li class="page-item"><a class="page-link" onclick="loadCampuses(${cur+1})">›</a></li>`;
    ul.innerHTML=h;
}

function resetForm() {
    document.getElementById('campusForm').reset();
    document.getElementById('campusId').value='';
    document.getElementById('modalTitle').textContent='Thêm cơ sở';
    document.getElementById('cpCode').disabled=false;
    clearErrors();
}

async function editCampus(id) {
    try {
        const c = await api.get(`/campuses/${id}`);
        document.getElementById('campusId').value    = c.id;
        document.getElementById('cpCode').value      = c.code;
        document.getElementById('cpCode').disabled   = true;
        document.getElementById('cpName').value      = c.name;
        document.getElementById('cpAddress').value   = c.address || '';
        document.getElementById('cpPhone').value     = c.phone || '';
        document.getElementById('cpEmail').value     = c.email || '';
        document.getElementById('cpActive').checked  = c.is_active;
        document.getElementById('modalTitle').textContent='Sửa cơ sở';
        clearErrors();
        new bootstrap.Modal(document.getElementById('campusModal')).show();
    } catch(e) { showAlert('Lỗi: '+e.message,'danger'); }
}

async function saveCampus(e) {
    e.preventDefault(); clearErrors();
    const id   = document.getElementById('campusId').value;
    const code = document.getElementById('cpCode').value.trim().toUpperCase();
    const name = document.getElementById('cpName').value.trim();
    if(!code){showFieldError('codeError','Mã là bắt buộc');return;}
    if(!name){showFieldError('nameError','Tên là bắt buộc');return;}
    setLoading(true);
    try {
        const body={code,name,
            address:document.getElementById('cpAddress').value.trim()||null,
            phone:document.getElementById('cpPhone').value.trim()||null,
            email:document.getElementById('cpEmail').value.trim()||null,
            is_active:document.getElementById('cpActive').checked};
        const res=await api[id?'put':'post'](id?`/campuses/${id}`:'/campuses',body);
        showAlert(res.message||'Lưu thành công','success');
        bootstrap.Modal.getInstance(document.getElementById('campusModal')).hide();
        loadCampuses(currentPage);
    } catch(err){showAlert('Lỗi: '+err.message,'danger');}
    finally{setLoading(false);}
}

async function deleteCampus(id) {
    if(!confirm('Xóa cơ sở này?')) return;
    try{const res=await api.delete(`/campuses/${id}`);showAlert(res.message||'Đã xóa','success');loadCampuses(currentPage);}
    catch(e){showAlert('Lỗi: '+e.message,'danger');}
}

function showState(s){document.getElementById('loadingState').classList.toggle('d-none',s!=='loading');document.getElementById('emptyState').classList.toggle('d-none',s!=='empty');document.getElementById('tableContainer').classList.toggle('d-none',s!=='table');if(['done','empty','table'].includes(s))document.getElementById('loadingState').classList.add('d-none');}
function showAlert(msg,type='info'){const el=document.createElement('div');el.className=`alert alert-${type} alert-dismissible fade show`;el.innerHTML=`${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;document.getElementById('alertContainer').appendChild(el);setTimeout(()=>el.remove(),5000);}
function showFieldError(id,msg){const e=document.getElementById(id);if(e){e.textContent=msg;e.classList.remove('d-none');}}
function clearErrors(){document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');});}
function setLoading(on){document.getElementById('submitBtnText').classList.toggle('d-none',on);document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);document.getElementById('submitBtn').disabled=on;}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
