// Class Schedules Module
let currentPage = 1;
const itemsPerPage = 10;

const dayNames = {
    1: 'Thứ 2',
    2: 'Thứ 3',
    3: 'Thứ 4',
    4: 'Thứ 5',
    5: 'Thứ 6',
    6: 'Thứ 7',
    7: 'CN'
};

async function loadClassrooms() {
    try {
        const response = await fetch('/api/classrooms?per_page=100', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load classrooms');

        const data = await response.json();
        const select = document.getElementById('schClassroom');
        const filterSelect = document.getElementById('filterClassroom');

        data.items.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.id;
            option.textContent = cls.name;
            select.appendChild(option);

            const filterOption = document.createElement('option');
            filterOption.value = cls.id;
            filterOption.textContent = cls.name;
            filterSelect.appendChild(filterOption);
        });
    } catch (error) {
        console.error('Error loading classrooms:', error);
    }
}

async function loadSubjects() {
    try {
        const response = await fetch('/api/subjects?per_page=100', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load subjects');

        const data = await response.json();
        const select = document.getElementById('schSubject');

        data.items.forEach(subj => {
            const option = document.createElement('option');
            option.value = subj.id;
            option.textContent = `${subj.subject_name} (${subj.subject_code})`;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

async function loadRooms() {
    try {
        const response = await fetch('/api/rooms?per_page=100', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load rooms');

        const data = await response.json();
        const select = document.getElementById('schRoom');

        data.items.forEach(room => {
            const option = document.createElement('option');
            option.value = room.id;
            option.textContent = room.name || room.code;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading rooms:', error);
    }
}

async function loadSchedules() {
    try {
        showLoadingState();

        const classroomId = document.getElementById('filterClassroom')?.value;
        const isActive = document.getElementById('filterActive')?.value;

        let url = '/api/class-schedules';
        if (classroomId) {
            url = `/api/class-schedules/by-classroom/${classroomId}`;
        }

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        let schedules = Array.isArray(data) ? data : (data.items || []);

        if (isActive !== '') {
            const filterActive = isActive === 'true';
            schedules = schedules.filter(s => s.is_active === filterActive);
        }

        renderSchedulesTable(schedules);
        hideLoadingState();
    } catch (error) {
        console.error('Error loading schedules:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderSchedulesTable(schedules) {
    const tbody = document.getElementById('schedulesTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!schedules || schedules.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = schedules.map(sch => {
        const startTime = sch.start_time ? sch.start_time.substring(0, 5) : '--:--';
        const endTime = sch.end_time ? sch.end_time.substring(0, 5) : '--:--';
        return `
        <tr>
            <td>
                <strong>${escapeHtml(sch.classroom_name || '--')}</strong>
            </td>
            <td>
                <small>${escapeHtml(sch.subject_name || '--')}</small>
            </td>
            <td>
                <span class="badge bg-info">${dayNames[sch.day_of_week] || '--'}</span>
            </td>
            <td>
                ${startTime} - ${endTime}
            </td>
            <td>
                <small>${escapeHtml(sch.room_name || '-')}</small>
            </td>
            <td>
                <span class="badge ${sch.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${sch.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-warning" onclick="editSchedule(${sch.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteSchedule(${sch.id})" title="Xóa">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
    }).join('');
}

function resetScheduleForm() {
    document.getElementById('scheduleForm').reset();
    document.getElementById('scheduleId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới thời khóa biểu';
    clearFormErrors();
}

async function editSchedule(id) {
    try {
        const response = await fetch(`/api/class-schedules/${id}`, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error('Không tìm thấy thời khóa biểu');

        const sch = await response.json();

        document.getElementById('scheduleId').value = sch.id;
        document.getElementById('schClassroom').value = sch.classroom_id || '';
        document.getElementById('schSubject').value = sch.subject_id || '';
        document.getElementById('schRoom').value = sch.room_id || '';
        document.getElementById('schDay').value = sch.day_of_week;
        document.getElementById('schStartTime').value = sch.start_time ? sch.start_time.substring(0, 5) : '';
        document.getElementById('schEndTime').value = sch.end_time ? sch.end_time.substring(0, 5) : '';
        document.getElementById('schActive').checked = sch.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa thời khóa biểu';
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('scheduleModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading schedule:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
    }
}

async function saveSchedule(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('scheduleId').value;
    const classroomId = document.getElementById('schClassroom').value;
    const subjectId = document.getElementById('schSubject').value;
    const roomId = document.getElementById('schRoom').value || null;
    const dayOfWeek = document.getElementById('schDay').value;
    const startTime = document.getElementById('schStartTime').value;
    const endTime = document.getElementById('schEndTime').value;
    const isActive = document.getElementById('schActive').checked;

    if (!classroomId || !subjectId || !dayOfWeek || !startTime || !endTime) {
        showAlert('Vui lòng điền đầy đủ thông tin bắt buộc', 'warning');
        return;
    }

    if (startTime >= endTime) {
        showFieldError('endTimeError', 'Giờ kết thúc phải sau giờ bắt đầu');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/class-schedules/${id}` : '/api/class-schedules';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({
                classroom_id: parseInt(classroomId),
                subject_id: parseInt(subjectId),
                room_id: roomId ? parseInt(roomId) : null,
                day_of_week: parseInt(dayOfWeek),
                start_time: startTime + ':00',
                end_time: endTime + ':00',
                is_active: isActive
            })
        });

        const responseData = await response.json();

        if (!response.ok) {
            const errorMsg = responseData.error || responseData.message || 'Lỗi khi lưu';
            showAlert(errorMsg, 'danger');
            setSubmitLoading(false);
            return;
        }

        showAlert(responseData.message || 'Lưu thành công', 'success');
        bootstrap.Modal.getInstance(document.getElementById('scheduleModal')).hide();
        await loadSchedules();
    } catch (error) {
        console.error('Error saving schedule:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteSchedule(id) {
    if (!confirm('Bạn có chắc muốn xóa thời khóa biểu này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/class-schedules/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa thành công', 'success');
        await loadSchedules();
    } catch (error) {
        console.error('Error deleting schedule:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    }
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
    const alertHTML = `
        <div class="alert alert-${type} alert-dismissible fade show" role="alert">
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        </div>
    `;

    const container = document.getElementById('alertContainer');
    const div = document.createElement('div');
    div.innerHTML = alertHTML;
    container.appendChild(div.firstElementChild);

    setTimeout(() => {
        container.firstElementChild?.remove();
    }, 5000);
}

function showFieldError(elementId, message) {
    const errorElement = document.getElementById(elementId);
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.remove('d-none');
    }
}

function clearFormErrors() {
    document.querySelectorAll('[id$="Error"]').forEach(el => {
        el.textContent = '';
        el.classList.add('d-none');
    });
}

function setSubmitLoading(loading) {
    const btn = document.getElementById('submitBtn');
    const text = document.getElementById('submitBtnText');
    const spinner = document.getElementById('submitBtnSpinner');

    if (loading) {
        btn.disabled = true;
        text.classList.add('d-none');
        spinner.classList.remove('d-none');
    } else {
        btn.disabled = false;
        text.classList.remove('d-none');
        spinner.classList.add('d-none');
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
