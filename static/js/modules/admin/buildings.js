// Buildings Module — full CRUD
let currentPage = 1;

async function loadCampuses() {
    try {
        const data = await api.get('/campuses?per_page=100');
        (data.items || []).forEach(c => {
            ['bdCampus','filterCampus'].forEach(id => {
                const sel=document.getElementById(id);
                if(!sel)return;
                const o=document.createElement('option');o.value=c.id;o.textContent=c.name;sel.appendChild(o);
            });
        });
    } catch(e) { console.error(e); }
}

async function loadBuildings(page = 1) {
    showState('loading');
    const search   = document.getElementById('searchInput')?.value || '';
    const campusId = document.getElementById('filterCampus')?.value;
    const active   = document.getElementById('filterActive')?.value;
    let url = `/buildings?page=${page}&per_page=10`;
    if (search)   url += `&search=${encodeURIComponent(search)}`;
    if (campusId) url += `&campus_id=${campusId}`;
    if (active)   url += `&is_active=${active}`;
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
    document.getElementById('buildingTable').innerHTML = items.map(b => `
        <tr>
            <td><span class="badge bg-info">${esc(b.code)}</span></td>
            <td><strong>${esc(b.name)}</strong></td>
            <td>${esc(b.campus?.name || '—')}</td>
            <td>${b.floors ?? '—'}</td>
            <td><span class="badge bg-${b.is_active?'success':'secondary'}">${b.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editBuilding(${b.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteBuilding(${b.id})"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderPagination(p, cur) {
    const wrap=document.getElementById('paginationContainer'),ul=document.getElementById('paginationList');
    if(!p.total_pages||p.total_pages<=1){wrap?.classList.add('d-none');return;}
    wrap?.classList.remove('d-none');
    let h='';
    if(cur>1) h+=`<li class="page-item"><a class="page-link" onclick="loadBuildings(${cur-1})">‹</a></li>`;
    for(let i=1;i<=p.total_pages;i++) h+=`<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadBuildings(${i})">${i}</a></li>`;
    if(cur<p.total_pages) h+=`<li class="page-item"><a class="page-link" onclick="loadBuildings(${cur+1})">›</a></li>`;
    ul.innerHTML=h;
}

function resetForm() {
    document.getElementById('buildingForm').reset();
    document.getElementById('buildingId').value='';
    document.getElementById('modalTitle').textContent='Thêm tòa nhà';
    document.getElementById('bdCode').disabled=false;
    clearErrors();
}

async function editBuilding(id) {
    try {
        const b = await api.get(`/buildings/${id}`);
        document.getElementById('buildingId').value   = b.id;
        document.getElementById('bdCode').value       = b.code;
        document.getElementById('bdCode').disabled    = true;
        document.getElementById('bdName').value       = b.name;
        document.getElementById('bdCampus').value     = b.campus_id || b.campus?.id || '';
        document.getElementById('bdFloors').value     = b.floors || '';
        document.getElementById('bdDesc').value       = b.description || '';
        document.getElementById('bdActive').checked   = b.is_active;
        document.getElementById('modalTitle').textContent='Sửa tòa nhà';
        clearErrors();
        new bootstrap.Modal(document.getElementById('buildingModal')).show();
    } catch(e) { showAlert('Lỗi: '+e.message,'danger'); }
}

async function saveBuilding(e) {
    e.preventDefault(); clearErrors();
    const id     = document.getElementById('buildingId').value;
    const code   = document.getElementById('bdCode').value.trim().toUpperCase();
    const name   = document.getElementById('bdName').value.trim();
    const campus = document.getElementById('bdCampus').value;
    if(!code)   {showFieldError('codeError','Mã là bắt buộc');return;}
    if(!name)   {showFieldError('nameError','Tên là bắt buộc');return;}
    if(!campus) {showFieldError('campusError','Cơ sở là bắt buộc');return;}
    setLoading(true);
    try {
        const body={code,name,campus_id:parseInt(campus),
            floors:parseInt(document.getElementById('bdFloors').value)||null,
            description:document.getElementById('bdDesc').value.trim()||null,
            is_active:document.getElementById('bdActive').checked};
        const res=await api[id?'put':'post'](id?`/buildings/${id}`:'/buildings',body);
        showAlert(res.message||'Lưu thành công','success');
        bootstrap.Modal.getInstance(document.getElementById('buildingModal')).hide();
        loadBuildings(currentPage);
    } catch(err){showAlert('Lỗi: '+err.message,'danger');}
    finally{setLoading(false);}
}

async function deleteBuilding(id) {
    if(!confirm('Xóa tòa nhà này?')) return;
    try{const res=await api.delete(`/buildings/${id}`);showAlert(res.message||'Đã xóa','success');loadBuildings(currentPage);}
    catch(e){showAlert('Lỗi: '+e.message,'danger');}
}

function showState(s){document.getElementById('loadingState').classList.toggle('d-none',s!=='loading');document.getElementById('emptyState').classList.toggle('d-none',s!=='empty');document.getElementById('tableContainer').classList.toggle('d-none',s!=='table');if(['done','empty','table'].includes(s))document.getElementById('loadingState').classList.add('d-none');}
function showAlert(msg,type='info'){const el=document.createElement('div');el.className=`alert alert-${type} alert-dismissible fade show`;el.innerHTML=`${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;document.getElementById('alertContainer').appendChild(el);setTimeout(()=>el.remove(),5000);}
function showFieldError(id,msg){const e=document.getElementById(id);if(e){e.textContent=msg;e.classList.remove('d-none');}}
function clearErrors(){document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');});}
function setLoading(on){document.getElementById('submitBtnText').classList.toggle('d-none',on);document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);document.getElementById('submitBtn').disabled=on;}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
