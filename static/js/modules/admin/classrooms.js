// Classrooms Module
let currentPage = 1;
const itemsPerPage = 10;

async function loadLecturers() {
    try {
        const response = await fetch('/api/lecturers?per_page=100', {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to load lecturers');

        const data = await response.json();
        const select = document.getElementById('clsLecturer');
        const filterSelect = document.getElementById('filterLecturer');

        data.items.forEach(lec => {
            const option = document.createElement('option');
            option.value = lec.id;
            option.textContent = `${lec.full_name} (${lec.lecturer_code})`;
            select.appendChild(option);

            const filterOption = document.createElement('option');
            filterOption.value = lec.id;
            filterOption.textContent = `${lec.full_name} (${lec.lecturer_code})`;
            filterSelect.appendChild(filterOption);
        });
    } catch (error) {
        console.error('Error loading lecturers:', error);
    }
}

async function loadClassrooms(page = 1) {
    try {
        showLoadingState();

        const search = document.getElementById('searchInput')?.value || '';
        const lecturerId = document.getElementById('filterLecturer')?.value;
        const isActive = document.getElementById('filterActive')?.value;

        let url = `/api/classrooms?page=${page}&per_page=${itemsPerPage}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (lecturerId) url += `&lecturer_id=${lecturerId}`;
        if (isActive !== '') url += `&is_active=${isActive}`;

        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        renderClassroomsTable(data.items);
        renderPagination(data.pagination, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading classrooms:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderClassroomsTable(classrooms) {
    const tbody = document.getElementById('classroomsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!classrooms || classrooms.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = classrooms.map(cls => `
        <tr>
            <td>
                <span class="badge bg-info">${escapeHtml(cls.code)}</span>
            </td>
            <td>
                <strong>${escapeHtml(cls.name)}</strong>
            </td>
            <td>
                ${cls.lecturer ? escapeHtml(cls.lecturer.full_name) : '-'}
            </td>
            <td>
                ${cls.room ? escapeHtml(cls.room.name) : '-'}
            </td>
            <td>
                <span class="badge bg-light text-dark">${cls.students_count}</span> /
                <span class="badge bg-light text-dark">${cls.subjects_count}</span>
            </td>
            <td>
                <span class="badge ${cls.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${cls.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <small>${new Date(cls.created_at).toLocaleDateString('vi-VN')}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-info"
                            onclick="openStudentsPanel(${cls.id}, '${cls.name.replace(/'/g,'&#39;')}')"
                            title="Quản lý sinh viên">
                        <i class="bi bi-people"></i>
                    </button>
                    <button class="btn btn-outline-warning" onclick="editClassroom(${cls.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteClassroom(${cls.id})" title="Xóa">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderPagination(pagination, currentPageNum) {
    const paginationContainer = document.getElementById('paginationContainer');
    const paginationList = document.getElementById('paginationList');

    if (!pagination || pagination.total_pages <= 1) {
        paginationContainer.classList.add('d-none');
        return;
    }

    paginationContainer.classList.remove('d-none');
    paginationList.innerHTML = '';

    if (currentPageNum > 1) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadClassrooms(${currentPageNum - 1})">Trước</a>
            </li>
        `;
    }

    for (let i = 1; i <= pagination.total_pages; i++) {
        if (i === currentPageNum) {
            paginationList.innerHTML += `
                <li class="page-item active">
                    <span class="page-link">${i}</span>
                </li>
            `;
        } else {
            paginationList.innerHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="loadClassrooms(${i})">${i}</a>
                </li>
            `;
        }
    }

    if (currentPageNum < pagination.total_pages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadClassrooms(${currentPageNum + 1})">Tiếp</a>
            </li>
        `;
    }
}

function resetClassroomForm() {
    document.getElementById('classroomForm').reset();
    document.getElementById('classroomId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới lớp học';
    document.getElementById('clsCode').disabled = false;
    clearFormErrors();
}

async function editClassroom(id) {
    try {
        const response = await fetch(`/api/classrooms/${id}`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Không tìm thấy lớp học');

        const data = await response.json();
        const cls = data;

        document.getElementById('classroomId').value = cls.id;
        document.getElementById('clsCode').value = cls.code;
        document.getElementById('clsCode').disabled = true;
        document.getElementById('clsName').value = cls.name;
        document.getElementById('clsLecturer').value = cls.lecturer_id || '';
        document.getElementById('clsActive').checked = cls.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa lớp học';
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('classroomModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading classroom:', error);
        showAlert('Lỗi khi tải dữ liệu lớp học', 'danger');
    }
}

async function saveClassroom(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('classroomId').value;
    const code = document.getElementById('clsCode').value.trim().toUpperCase();
    const name = document.getElementById('clsName').value.trim();
    const lecturerId = document.getElementById('clsLecturer').value || null;
    const isActive = document.getElementById('clsActive').checked;

    if (!code) {
        showFieldError('codeError', 'Mã lớp là bắt buộc');
        return;
    }
    if (!name) {
        showFieldError('nameError', 'Tên lớp là bắt buộc');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/classrooms/${id}` : '/api/classrooms';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({
                code: code,
                name: name,
                lecturer_id: lecturerId,
                is_active: isActive
            })
        });

        const responseData = await response.json();

        if (!response.ok) {
            if (response.status === 409) {
                showFieldError('codeError', responseData.error);
            } else {
                throw new Error(responseData.error || 'Lỗi khi lưu');
            }
            setSubmitLoading(false);
            return;
        }

        showAlert(responseData.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('classroomModal')).hide();
        await loadClassrooms(currentPage);
    } catch (error) {
        console.error('Error saving classroom:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteClassroom(id) {
    if (!confirm('Bạn có chắc muốn xóa lớp học này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/classrooms/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa lớp học thành công', 'success');
        await loadClassrooms(currentPage);
    } catch (error) {
        console.error('Error deleting classroom:', error);
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

// ── Student Management Panel ──────────────────────────────────────────────────

let _smClassroomId = null;

async function openStudentsPanel(classroomId, className) {
    _smClassroomId = classroomId;
    document.getElementById('smClassName').textContent = className;
    document.getElementById('smSearch').value = '';
    document.getElementById('smSearchResults').innerHTML = '';
    const modal = new bootstrap.Modal(document.getElementById('studentsModal'));
    modal.show();
    await loadEnrolledStudents();
}

async function loadEnrolledStudents() {
    const tbody = document.getElementById('smStudentsTable');
    try {
        const res = await fetch(`/api/classrooms/${_smClassroomId}/students`, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const data = await res.json();
        const students = data.students || [];
        document.getElementById('smCount').textContent = students.length;

        if (!students.length) {
            tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted py-3">Chưa có sinh viên</td></tr>';
            return;
        }
        tbody.innerHTML = students.map(s => `
            <tr>
                <td><code>${escapeHtml(s.student_code)}</code></td>
                <td>${escapeHtml(s.full_name)}</td>
                <td><small>${escapeHtml(s.email || '—')}</small></td>
                <td>
                    <button class="btn btn-danger btn-sm"
                            onclick="removeStudentFromClass(${s.id})"
                            title="Xóa khỏi lớp">
                        <i class="bi bi-x"></i>
                    </button>
                </td>
            </tr>
        `).join('');
    } catch (e) {
        tbody.innerHTML = `<tr><td colspan="4" class="text-danger text-center py-2">Lỗi: ${e.message}</td></tr>`;
    }
}

async function smSearchStudents() {
    const q = document.getElementById('smSearch').value.trim();
    if (!q) return;
    const container = document.getElementById('smSearchResults');
    try {
        const res = await fetch(`/api/students?search=${encodeURIComponent(q)}&per_page=10&is_active=true`, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const data = await res.json();
        const students = data.items || [];
        if (!students.length) {
            container.innerHTML = '<div class="text-muted small">Không tìm thấy sinh viên</div>';
            return;
        }
        container.innerHTML = `
            <div class="list-group">
                ${students.map(s => `
                    <button type="button"
                            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center"
                            onclick="addStudentToClass(${s.id})">
                        <span>
                            <code>${escapeHtml(s.student_code)}</code>
                            ${escapeHtml(s.full_name)}
                            <small class="text-muted ms-2">${escapeHtml(s.email || '')}</small>
                        </span>
                        <i class="bi bi-plus-circle text-success"></i>
                    </button>
                `).join('')}
            </div>`;
    } catch (e) {
        container.innerHTML = `<div class="text-danger small">Lỗi: ${e.message}</div>`;
    }
}

async function addStudentToClass(studentId) {
    try {
        const res = await fetch(`/api/classrooms/${_smClassroomId}/students`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({ student_ids: [studentId] })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Lỗi thêm sinh viên');
        showAlert(data.message || 'Đã thêm sinh viên', 'success');
        document.getElementById('smSearchResults').innerHTML = '';
        document.getElementById('smSearch').value = '';
        await loadEnrolledStudents();
        await loadClassrooms(currentPage);  // refresh counts
    } catch (e) {
        showAlert('Lỗi: ' + e.message, 'danger');
    }
}

async function removeStudentFromClass(studentId) {
    if (!confirm('Xóa sinh viên khỏi lớp này?')) return;
    try {
        const res = await fetch(`/api/classrooms/${_smClassroomId}/students/${studentId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Lỗi xóa sinh viên');
        showAlert('Đã xóa sinh viên khỏi lớp', 'success');
        await loadEnrolledStudents();
        await loadClassrooms(currentPage);
    } catch (e) {
        showAlert('Lỗi: ' + e.message, 'danger');
    }
}
