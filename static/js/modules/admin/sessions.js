// Class Sessions Module

const statusLabels = {
    'scheduled': 'Lên lịch',
    'ongoing': 'Đang diễn ra',
    'completed': 'Hoàn thành',
    'cancelled': 'Hủy'
};

const statusColors = {
    'scheduled': 'secondary',
    'ongoing': 'warning',
    'completed': 'success',
    'cancelled': 'danger'
};

async function loadClassrooms() {
    try {
        const response = await fetch('/api/classrooms?per_page=100', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load classrooms');

        const data = await response.json();
        const filterSelect = document.getElementById('filterClassroom');

        data.items.forEach(cls => {
            const option = document.createElement('option');
            option.value = cls.id;
            option.textContent = cls.name;
            filterSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading classrooms:', error);
    }
}

async function loadSessions() {
    try {
        showLoadingState();

        const response = await fetch('/api/class-sessions', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        let sessions = await response.json();
        if (!Array.isArray(sessions)) {
            sessions = sessions.items || [];
        }

        // Apply filters
        const filterDate = document.getElementById('filterDate')?.value;
        const filterClassroom = document.getElementById('filterClassroom')?.value;
        const filterStatus = document.getElementById('filterStatus')?.value;

        if (filterDate) {
            sessions = sessions.filter(s => s.session_date === filterDate);
        }

        if (filterClassroom) {
            sessions = sessions.filter(s => s.classroom_id == filterClassroom);
        }

        if (filterStatus) {
            sessions = sessions.filter(s => s.status === filterStatus);
        }

        // Sort by date and time
        sessions.sort((a, b) => {
            const dateA = new Date(a.session_date + ' ' + a.start_time);
            const dateB = new Date(b.session_date + ' ' + b.start_time);
            return dateA - dateB;
        });

        renderSessionsTable(sessions);
        hideLoadingState();
    } catch (error) {
        console.error('Error loading sessions:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderSessionsTable(sessions) {
    const tbody = document.getElementById('sessionsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!sessions || sessions.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = sessions.map(sess => {
        const date = new Date(sess.session_date).toLocaleDateString('vi-VN');
        const startTime = sess.start_time ? sess.start_time.substring(0, 5) : '--:--';
        const endTime = sess.end_time ? sess.end_time.substring(0, 5) : '--:--';
        const statusColor = statusColors[sess.status] || 'secondary';
        const statusLabel = statusLabels[sess.status] || sess.status;

        return `
        <tr>
            <td>
                <strong>${date}</strong>
            </td>
            <td>
                ${startTime} - ${endTime}
            </td>
            <td>
                <small>${escapeHtml(sess.classroom_name || '--')}</small>
            </td>
            <td>
                <small>${escapeHtml(sess.subject_name || '--')}</small>
            </td>
            <td>
                <small>${escapeHtml(sess.room_name || '-')}</small>
            </td>
            <td>
                <span class="badge bg-${statusColor}">${statusLabel}</span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-info" onclick="openAttendance(${sess.id})" title="Điểm danh">
                        <i class="bi bi-qr-code"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="editStatus(${sess.id})" title="Sửa trạng thái">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteSession(${sess.id})" title="Xóa">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `;
    }).join('');
}

async function generateSessions(event) {
    event.preventDefault();

    const startDate = document.getElementById('genStartDate').value;
    const endDate = document.getElementById('genEndDate').value;

    if (!startDate || !endDate) {
        showAlert('Vui lòng chọn ngày bắt đầu và kết thúc', 'warning');
        return;
    }

    if (startDate > endDate) {
        showAlert('Ngày bắt đầu phải trước ngày kết thúc', 'warning');
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
            body: JSON.stringify({
                start_date: startDate,
                end_date: endDate
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi tạo buổi học');
        }

        showAlert(data.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('generateModal')).hide();
        document.getElementById('generateForm').reset();
        await loadSessions();
    } catch (error) {
        console.error('Error generating sessions:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading('genSubmitBtn', false);
    }
}

async function editStatus(id) {
    document.getElementById('statusSessionId').value = id;
    const modal = new bootstrap.Modal(document.getElementById('statusModal'));
    modal.show();
}

async function saveStatus(event) {
    event.preventDefault();

    const id = document.getElementById('statusSessionId').value;
    const status = document.getElementById('statusSelect').value;

    try {
        const response = await fetch(`/api/class-sessions/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({ status })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi cập nhật');
        }

        showAlert(data.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('statusModal')).hide();
        await loadSessions();
    } catch (error) {
        console.error('Error saving status:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    }
}

async function deleteSession(id) {
    if (!confirm('Bạn có chắc muốn xóa buổi học này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/class-sessions/${id}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa thành công', 'success');
        await loadSessions();
    } catch (error) {
        console.error('Error deleting session:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    }
}

function openAttendance(id) {
    // TODO: Navigate to attendance page or open QR modal
    showAlert('Tính năng điểm danh sẽ được cập nhật', 'info');
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

function setSubmitLoading(btnId, loading) {
    const btn = document.getElementById(btnId);
    const text = document.getElementById(btnId + 'Text');
    const spinner = document.getElementById(btnId + 'Spinner');

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
