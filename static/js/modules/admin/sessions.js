// Admin Class Sessions Module

const statusLabels = {
    scheduled: 'Len lich',
    ongoing: 'Dang dien ra',
    completed: 'Hoan thanh',
    cancelled: 'Huy'
};

const statusColors = {
    scheduled: 'secondary',
    ongoing: 'warning',
    completed: 'success',
    cancelled: 'danger'
};

async function loadLookups() {
    await Promise.all([loadClassrooms(), loadSubjects(), loadRooms(), loadLecturers()]);
}

function appendOptions(selectIds, items, getLabel) {
    selectIds.forEach(id => {
        const select = document.getElementById(id);
        if (!select) return;
        const first = select.querySelector('option')?.outerHTML || '<option value="">--</option>';
        select.innerHTML = first;
        items.forEach(item => {
            const option = document.createElement('option');
            option.value = item.id;
            option.textContent = getLabel(item);
            select.appendChild(option);
        });
    });
}

async function loadClassrooms() {
    const response = await fetch('/api/classrooms?per_page=500&is_active=true', {
        headers: { 'Authorization': `Bearer ${auth.getToken()}` }
    });
    const data = await response.json();
    appendOptions(['filterClassroom', 'sessClassroom'], data.items || [], cls => cls.name || cls.code);
}

async function loadSubjects() {
    const response = await fetch('/api/subjects?per_page=500&is_active=true', {
        headers: { 'Authorization': `Bearer ${auth.getToken()}` }
    });
    const data = await response.json();
    appendOptions(['filterSubject', 'sessSubject'], data.items || [], s => `${s.subject_name} (${s.subject_code})`);
}

async function loadRooms() {
    const response = await fetch('/api/rooms?per_page=500&is_active=true', {
        headers: { 'Authorization': `Bearer ${auth.getToken()}` }
    });
    const data = await response.json();
    appendOptions(['sessRoom'], data.items || [], r => r.name || r.code);
}

async function loadLecturers() {
    const response = await fetch('/api/lecturers?per_page=500&is_active=true', {
        headers: { 'Authorization': `Bearer ${auth.getToken()}` }
    });
    const data = await response.json();
    appendOptions(['filterLecturer'], data.items || [], l => `${l.full_name} (${l.lecturer_code})`);
}

async function loadSessions() {
    try {
        showLoadingState();
        const params = new URLSearchParams();
        const dateFrom = document.getElementById('filterDateFrom')?.value;
        const dateTo = document.getElementById('filterDateTo')?.value;
        const classroomId = document.getElementById('filterClassroom')?.value;
        const subjectId = document.getElementById('filterSubject')?.value;
        const lecturerId = document.getElementById('filterLecturer')?.value;
        const status = document.getElementById('filterStatus')?.value;
        if (dateFrom) params.set('date_from', dateFrom);
        if (dateTo) params.set('date_to', dateTo);
        if (classroomId) params.set('classroom_id', classroomId);
        if (subjectId) params.set('subject_id', subjectId);
        if (lecturerId) params.set('lecturer_id', lecturerId);
        if (status) params.set('status', status);

        const response = await fetch('/api/class-sessions?' + params.toString(), {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        let sessions = await response.json();
        if (!Array.isArray(sessions)) sessions = sessions.items || [];
        renderSessionsTable(sessions);
    } catch (error) {
        console.error('Error loading sessions:', error);
        showAlert('Loi khi tai du lieu: ' + error.message, 'danger');
        hideLoadingState();
    }
}

function renderSessionsTable(sessions) {
    const tbody = document.getElementById('sessionsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');
    hideLoadingState();

    if (!sessions || sessions.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');
    tbody.innerHTML = sessions.map(sess => {
        const dateText = sess.session_date ? new Date(sess.session_date).toLocaleDateString('vi-VN') : '--';
        const startTime = sess.start_time ? sess.start_time.substring(0, 5) : '--:--';
        const endTime = sess.end_time ? sess.end_time.substring(0, 5) : '--:--';
        const statusColor = statusColors[sess.status] || 'secondary';
        const statusLabel = statusLabels[sess.status] || sess.status;
        return `
            <tr>
                <td><strong>${dateText}</strong><br><small class="text-muted">${sess.session_date || ''}</small></td>
                <td>${startTime} - ${endTime}</td>
                <td>${escapeHtml(sess.classroom_name || '--')}</td>
                <td>${escapeHtml(sess.subject_name || '--')}</td>
                <td>${escapeHtml(sess.lecturer_name || '--')}</td>
                <td>${escapeHtml(sess.room_name || '-')}</td>
                <td><span class="badge bg-${statusColor}">${statusLabel}</span></td>
                <td>
                    <div class="btn-group btn-group-sm">
                        <button class="btn btn-outline-info" onclick="openAttendance(${sess.id})" title="Diem danh"><i class="bi bi-qr-code"></i></button>
                        <button class="btn btn-outline-warning" onclick="editSession(${sess.id})" title="Sua"><i class="bi bi-pencil"></i></button>
                        <button class="btn btn-outline-danger" onclick="deleteSession(${sess.id})" title="Xoa"><i class="bi bi-trash"></i></button>
                    </div>
                </td>
            </tr>`;
    }).join('');
}

function resetSessionForm() {
    document.getElementById('sessionForm').reset();
    document.getElementById('sessionId').value = '';
    document.getElementById('sessionModalTitle').textContent = 'Tao buoi hoc';
    document.getElementById('sessStatus').value = 'scheduled';
}

async function editSession(id) {
    try {
        const response = await fetch(`/api/class-sessions/${id}`, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const sess = await response.json();
        if (!response.ok) throw new Error(sess.error || 'Khong tim thay buoi hoc');
        document.getElementById('sessionId').value = sess.id;
        document.getElementById('sessDate').value = sess.session_date || '';
        document.getElementById('sessClassroom').value = sess.classroom_id || '';
        document.getElementById('sessSubject').value = sess.subject_id || '';
        document.getElementById('sessRoom').value = sess.room_id || '';
        document.getElementById('sessStart').value = (sess.start_time || '').substring(0, 5);
        document.getElementById('sessEnd').value = (sess.end_time || '').substring(0, 5);
        document.getElementById('sessStatus').value = sess.status || 'scheduled';
        document.getElementById('sessNotes').value = sess.notes || '';
        document.getElementById('sessionModalTitle').textContent = 'Sua buoi hoc';
        new bootstrap.Modal(document.getElementById('sessionModal')).show();
    } catch (error) {
        showAlert('Loi: ' + error.message, 'danger');
    }
}

async function saveSession(event) {
    event.preventDefault();
    const id = document.getElementById('sessionId').value;
    const body = {
        session_date: document.getElementById('sessDate').value,
        classroom_id: parseInt(document.getElementById('sessClassroom').value),
        subject_id: parseInt(document.getElementById('sessSubject').value),
        room_id: document.getElementById('sessRoom').value ? parseInt(document.getElementById('sessRoom').value) : null,
        start_time: document.getElementById('sessStart').value,
        end_time: document.getElementById('sessEnd').value,
        status: document.getElementById('sessStatus').value,
        notes: document.getElementById('sessNotes').value || null
    };
    if (!body.session_date || !body.classroom_id || !body.subject_id || !body.start_time || !body.end_time) {
        showAlert('Vui long dien day du thong tin bat buoc', 'warning');
        return;
    }
    if (body.start_time >= body.end_time) {
        showAlert('Gio ket thuc phai sau gio bat dau', 'warning');
        return;
    }
    try {
        const response = await fetch(id ? `/api/class-sessions/${id}` : '/api/class-sessions', {
            method: id ? 'PUT' : 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify(body)
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Loi luu buoi hoc');
        bootstrap.Modal.getInstance(document.getElementById('sessionModal')).hide();
        showAlert(data.message || 'Da luu', 'success');
        await loadSessions();
    } catch (error) {
        showAlert('Loi: ' + error.message, 'danger');
    }
}

async function generateSessions(event) {
    event.preventDefault();
    const startDate = document.getElementById('genStartDate').value;
    const endDate = document.getElementById('genEndDate').value;
    if (!startDate || !endDate) {
        showAlert('Vui long chon ngay bat dau va ket thuc', 'warning');
        return;
    }
    if (startDate > endDate) {
        showAlert('Ngay bat dau phai truoc ngay ket thuc', 'warning');
        return;
    }
    setSubmitLoading('genSubmitBtn', true);
    try {
        const response = await fetch('/api/class-sessions/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({ start_date: startDate, end_date: endDate })
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Loi tao buoi hoc');
        showAlert(data.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('generateModal')).hide();
        document.getElementById('generateForm').reset();
        await loadSessions();
    } catch (error) {
        showAlert('Loi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading('genSubmitBtn', false);
    }
}

async function deleteSession(id) {
    if (!confirm('Xoa buoi hoc nay?')) return;
    try {
        const response = await fetch(`/api/class-sessions/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || 'Loi xoa');
        showAlert('Da xoa buoi hoc', 'success');
        await loadSessions();
    } catch (error) {
        showAlert('Loi: ' + error.message, 'danger');
    }
}

function openAttendance(id) {
    window.open(`/attendance/checkin/${id}`, '_blank');
}

function showLoadingState() {
    document.getElementById('loadingState').classList.remove('d-none');
    document.getElementById('tableContainer').classList.add('d-none');
    document.getElementById('emptyState').classList.add('d-none');
}

function hideLoadingState() {
    document.getElementById('loadingState').classList.add('d-none');
}

function showAlert(message, type = 'info') {
    const container = document.getElementById('alertContainer');
    const div = document.createElement('div');
    div.innerHTML = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;
    container.appendChild(div.firstElementChild);
    setTimeout(() => container.firstElementChild?.remove(), 5000);
}

function setSubmitLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    const text = document.getElementById(btnId + 'Text');
    const spinner = document.getElementById(btnId + 'Spinner');
    if (!btn || !text || !spinner) return;
    btn.disabled = loading;
    text.classList.toggle('d-none', loading);
    spinner.classList.toggle('d-none', !loading);
}

function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}
