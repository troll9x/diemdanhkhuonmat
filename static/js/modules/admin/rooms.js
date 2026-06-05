// Rooms Module — full CRUD
let currentPage = 1;

const ROOM_TYPES = { regular:'Phòng thường', lab:'Phòng lab', lecture:'Giảng đường', seminar:'Hội thảo', office:'Văn phòng' };

async function loadBuildings() {
    try {
        const data = await api.get('/buildings?per_page=200');
        (data.items || []).forEach(b => {
            ['rmBuilding','filterBuilding'].forEach(id => {
                const sel=document.getElementById(id);
                if(!sel)return;
                const o=document.createElement('option');o.value=b.id;
                o.textContent=`${b.name}${b.campus?.name?' ('+b.campus.name+')':''}`;
                sel.appendChild(o);
            });
        });
    } catch(e) { console.error(e); }
}

async function loadRooms(page = 1) {
    showState('loading');
    const search     = document.getElementById('searchInput')?.value || '';
    const buildingId = document.getElementById('filterBuilding')?.value;
    const roomType   = document.getElementById('filterType')?.value;
    const active     = document.getElementById('filterActive')?.value;
    let url = `/rooms?page=${page}&per_page=10`;
    if (search)     url += `&search=${encodeURIComponent(search)}`;
    if (buildingId) url += `&building_id=${buildingId}`;
    if (roomType)   url += `&room_type=${roomType}`;
    if (active)     url += `&is_active=${active}`;
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
    document.getElementById('roomTable').innerHTML = items.map(r => `
        <tr>
            <td><span class="badge bg-info">${esc(r.code)}</span></td>
            <td><strong>${esc(r.name)}</strong></td>
            <td>${esc(r.building?.name || '—')}</td>
            <td><span class="badge bg-light text-dark">${ROOM_TYPES[r.room_type]||r.room_type||'—'}</span></td>
            <td>${r.capacity ?? '—'}</td>
            <td><span class="badge bg-${r.is_active?'success':'secondary'}">${r.is_active?'Hoạt động':'Không'}</span></td>
            <td>
                <div class="btn-group btn-group-sm">
                    <button class="btn btn-outline-warning" onclick="editRoom(${r.id})"><i class="bi bi-pencil"></i></button>
                    <button class="btn btn-outline-danger"  onclick="deleteRoom(${r.id})"><i class="bi bi-trash"></i></button>
                </div>
            </td>
        </tr>`).join('');
}

function renderPagination(p, cur) {
    const wrap=document.getElementById('paginationContainer'),ul=document.getElementById('paginationList');
    if(!p.total_pages||p.total_pages<=1){wrap?.classList.add('d-none');return;}
    wrap?.classList.remove('d-none');
    let h='';
    if(cur>1) h+=`<li class="page-item"><a class="page-link" onclick="loadRooms(${cur-1})">‹</a></li>`;
    for(let i=1;i<=p.total_pages;i++) h+=`<li class="page-item ${i===cur?'active':''}"><a class="page-link" onclick="loadRooms(${i})">${i}</a></li>`;
    if(cur<p.total_pages) h+=`<li class="page-item"><a class="page-link" onclick="loadRooms(${cur+1})">›</a></li>`;
    ul.innerHTML=h;
}

function resetForm() {
    document.getElementById('roomForm').reset();
    document.getElementById('roomId').value='';
    document.getElementById('modalTitle').textContent='Thêm phòng học';
    document.getElementById('rmCode').disabled=false;
    clearErrors();
}

async function editRoom(id) {
    try {
        const r = await api.get(`/rooms/${id}`);
        document.getElementById('roomId').value       = r.id;
        document.getElementById('rmCode').value       = r.code;
        document.getElementById('rmCode').disabled    = true;
        document.getElementById('rmName').value       = r.name;
        document.getElementById('rmBuilding').value   = r.building_id || r.building?.id || '';
        document.getElementById('rmType').value       = r.room_type || 'regular';
        document.getElementById('rmCapacity').value   = r.capacity || '';
        document.getElementById('rmDesc').value       = r.description || '';
        document.getElementById('rmActive').checked   = r.is_active;
        document.getElementById('modalTitle').textContent='Sửa phòng học';
        clearErrors();
        new bootstrap.Modal(document.getElementById('roomModal')).show();
    } catch(e) { showAlert('Lỗi: '+e.message,'danger'); }
}

async function saveRoom(e) {
    e.preventDefault(); clearErrors();
    const id   = document.getElementById('roomId').value;
    const code = document.getElementById('rmCode').value.trim().toUpperCase();
    const name = document.getElementById('rmName').value.trim();
    if(!code){showFieldError('codeError','Mã là bắt buộc');return;}
    if(!name){showFieldError('nameError','Tên là bắt buộc');return;}
    setLoading(true);
    try {
        const body={code,name,
            building_id:document.getElementById('rmBuilding').value?parseInt(document.getElementById('rmBuilding').value):null,
            room_type:document.getElementById('rmType').value||'regular',
            capacity:parseInt(document.getElementById('rmCapacity').value)||30,
            description:document.getElementById('rmDesc').value.trim()||null,
            is_active:document.getElementById('rmActive').checked};
        const res=await api[id?'put':'post'](id?`/rooms/${id}`:'/rooms',body);
        showAlert(res.message||'Lưu thành công','success');
        bootstrap.Modal.getInstance(document.getElementById('roomModal')).hide();
        loadRooms(currentPage);
    } catch(err){showAlert('Lỗi: '+err.message,'danger');}
    finally{setLoading(false);}
}

async function deleteRoom(id) {
    if(!confirm('Xóa phòng học này?')) return;
    try{const res=await api.delete(`/rooms/${id}`);showAlert(res.message||'Đã xóa','success');loadRooms(currentPage);}
    catch(e){showAlert('Lỗi: '+e.message,'danger');}
}

function showState(s){document.getElementById('loadingState').classList.toggle('d-none',s!=='loading');document.getElementById('emptyState').classList.toggle('d-none',s!=='empty');document.getElementById('tableContainer').classList.toggle('d-none',s!=='table');if(['done','empty','table'].includes(s))document.getElementById('loadingState').classList.add('d-none');}
function showAlert(msg,type='info'){const el=document.createElement('div');el.className=`alert alert-${type} alert-dismissible fade show`;el.innerHTML=`${msg}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;document.getElementById('alertContainer').appendChild(el);setTimeout(()=>el.remove(),5000);}
function showFieldError(id,msg){const e=document.getElementById(id);if(e){e.textContent=msg;e.classList.remove('d-none');}}
function clearErrors(){document.querySelectorAll('[id$="Error"]').forEach(e=>{e.textContent='';e.classList.add('d-none');});}
function setLoading(on){document.getElementById('submitBtnText').classList.toggle('d-none',on);document.getElementById('submitBtnSpinner').classList.toggle('d-none',!on);document.getElementById('submitBtn').disabled=on;}
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML;}
