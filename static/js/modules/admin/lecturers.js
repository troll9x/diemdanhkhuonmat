// Lecturers Module
let currentPage = 1;
const itemsPerPage = 10;
let isEditMode = false;

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments?per_page=100', {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to load departments');

        const data = await response.json();
        const select = document.getElementById('lecDepartment');
        const filterSelect = document.getElementById('filterDepartment');

        data.items.forEach(dept => {
            const option = document.createElement('option');
            option.value = dept.id;
            option.textContent = dept.name;
            select.appendChild(option);

            const filterOption = document.createElement('option');
            filterOption.value = dept.id;
            filterOption.textContent = dept.name;
            filterSelect.appendChild(filterOption);
        });
    } catch (error) {
        console.error('Error loading departments:', error);
    }
}

async function loadLecturers(page = 1) {
    try {
        showLoadingState();

        const search = document.getElementById('searchInput')?.value || '';
        const departmentId = document.getElementById('filterDepartment')?.value;
        const isActive = document.getElementById('filterActive')?.value;

        let url = `/api/lecturers?page=${page}&per_page=${itemsPerPage}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (departmentId) url += `&department_id=${departmentId}`;
        if (isActive !== '') url += `&is_active=${isActive}`;

        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        renderLecturersTable(data.items);
        renderPagination(data.pagination, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading lecturers:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderLecturersTable(lecturers) {
    const tbody = document.getElementById('lecturersTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!lecturers || lecturers.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = lecturers.map(lec => `
        <tr>
            <td>
                <span class="badge bg-info">${escapeHtml(lec.lecturer_code)}</span>
            </td>
            <td>
                <strong>${escapeHtml(lec.full_name)}</strong>
            </td>
            <td>
                <small>${escapeHtml(lec.email)}</small>
            </td>
            <td>
                ${lec.phone ? escapeHtml(lec.phone) : '-'}
            </td>
            <td>
                ${lec.department ? escapeHtml(lec.department.name) : '-'}
            </td>
            <td>
                <span class="badge ${lec.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${lec.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-warning" onclick="editLecturer(${lec.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteLecturer(${lec.id})" title="Xóa">
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
                <a class="page-link" href="#" onclick="loadLecturers(${currentPageNum - 1})">Trước</a>
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
                    <a class="page-link" href="#" onclick="loadLecturers(${i})">${i}</a>
                </li>
            `;
        }
    }

    if (currentPageNum < pagination.total_pages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadLecturers(${currentPageNum + 1})">Tiếp</a>
            </li>
        `;
    }
}

function resetLecturerForm() {
    document.getElementById('lecturerForm').reset();
    document.getElementById('lecturerId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới giảng viên';
    document.getElementById('lecCode').disabled = false;
    document.getElementById('lecPassword').required = true;
    document.getElementById('passwordLabel').textContent = '*';
    isEditMode = false;
    clearFormErrors();
}

async function editLecturer(id) {
    try {
        const response = await fetch(`/api/lecturers/${id}`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Không tìm thấy giảng viên');

        const data = await response.json();
        const lec = data;

        document.getElementById('lecturerId').value = lec.id;
        document.getElementById('lecCode').value = lec.lecturer_code;
        document.getElementById('lecCode').disabled = true;
        document.getElementById('lecName').value = lec.full_name;
        document.getElementById('lecEmail').value = lec.email;
        document.getElementById('lecPassword').value = '';
        document.getElementById('lecPassword').required = false;
        document.getElementById('passwordLabel').textContent = '(tùy chọn - để trống nếu không đổi)';
        document.getElementById('lecPhone').value = lec.phone || '';
        document.getElementById('lecDepartment').value = lec.department_id || '';
        document.getElementById('lecActive').checked = lec.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa giảng viên';
        isEditMode = true;
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('lecturerModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading lecturer:', error);
        showAlert('Lỗi khi tải dữ liệu giảng viên', 'danger');
    }
}

async function saveLecturer(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('lecturerId').value;
    const code = document.getElementById('lecCode').value.trim().toUpperCase();
    const name = document.getElementById('lecName').value.trim();
    const email = document.getElementById('lecEmail').value.trim().toLowerCase();
    const password = document.getElementById('lecPassword').value.trim();
    const phone = document.getElementById('lecPhone').value.trim();
    const departmentId = document.getElementById('lecDepartment').value || null;
    const isActive = document.getElementById('lecActive').checked;

    if (!code) {
        showFieldError('codeError', 'Mã giảng viên là bắt buộc');
        return;
    }
    if (!name) {
        showFieldError('nameError', 'Tên giảng viên là bắt buộc');
        return;
    }
    if (!email) {
        showFieldError('emailError', 'Email là bắt buộc');
        return;
    }

    if (!isEditMode && !password) {
        showFieldError('passwordError', 'Mật khẩu là bắt buộc khi thêm mới');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/lecturers/${id}` : '/api/lecturers';

        const body = {
            lecturer_code: code,
            full_name: name,
            email: email,
            phone: phone || null,
            department_id: departmentId,
            is_active: isActive
        };

        if (password) {
            body.password = password;
        }

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify(body)
        });

        const responseData = await response.json();

        if (!response.ok) {
            if (response.status === 409) {
                if (responseData.error.includes('code')) {
                    showFieldError('codeError', responseData.error);
                } else if (responseData.error.includes('email')) {
                    showFieldError('emailError', responseData.error);
                } else {
                    throw new Error(responseData.error);
                }
            } else if (response.status === 400) {
                if (responseData.error.includes('password')) {
                    showFieldError('passwordError', responseData.error);
                } else {
                    throw new Error(responseData.error);
                }
            } else {
                throw new Error(responseData.error || 'Lỗi khi lưu');
            }
            setSubmitLoading(false);
            return;
        }

        showAlert(responseData.message, 'success');
        bootstrap.Modal.getInstance(document.getElementById('lecturerModal')).hide();
        await loadLecturers(currentPage);
    } catch (error) {
        console.error('Error saving lecturer:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteLecturer(id) {
    if (!confirm('Bạn có chắc muốn xóa giảng viên này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/lecturers/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa giảng viên thành công', 'success');
        await loadLecturers(currentPage);
    } catch (error) {
        console.error('Error deleting lecturer:', error);
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
