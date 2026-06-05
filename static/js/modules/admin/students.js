// Students Module
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
        const select = document.getElementById('stdDepartment');
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

async function loadMajors() {
    try {
        const departmentId = document.getElementById('stdDepartment').value;
        const select = document.getElementById('stdMajor');

        select.innerHTML = '<option value="">-- Chọn chuyên ngành --</option>';

        if (!departmentId) return;

        const response = await fetch(`/api/majors?department_id=${departmentId}&per_page=100`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to load majors');

        const data = await response.json();
        data.items.forEach(major => {
            const option = document.createElement('option');
            option.value = major.id;
            option.textContent = major.name;
            select.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading majors:', error);
    }
}

async function loadStudents(page = 1) {
    try {
        showLoadingState();

        const search = document.getElementById('searchInput')?.value || '';
        const departmentId = document.getElementById('filterDepartment')?.value;
        const isActive = document.getElementById('filterActive')?.value;
        const faceRegistered = document.getElementById('filterFaceRegistered')?.value;

        let url = `/api/students?page=${page}&per_page=${itemsPerPage}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (departmentId) url += `&department_id=${departmentId}`;
        if (isActive !== '') url += `&is_active=${isActive}`;
        if (faceRegistered !== '') url += `&face_registered=${faceRegistered}`;

        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const data = await response.json();
        renderStudentsTable(data.items);
        renderPagination(data.pagination, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading students:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderStudentsTable(students) {
    const tbody = document.getElementById('studentsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!students || students.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = students.map(std => `
        <tr>
            <td>
                <span class="badge bg-info">${escapeHtml(std.student_code)}</span>
            </td>
            <td>
                <strong>${escapeHtml(std.full_name)}</strong>
            </td>
            <td>
                <small>${std.email ? escapeHtml(std.email) : '-'}</small>
            </td>
            <td>
                ${std.phone ? escapeHtml(std.phone) : '-'}
            </td>
            <td>
                ${std.department ? escapeHtml(std.department.name) : '-'}
            </td>
            <td>
                <span class="badge ${std.face_registered ? 'bg-success' : 'bg-warning'}">
                    ${std.face_registered ? 'Đã' : 'Chưa'}
                </span>
            </td>
            <td>
                <span class="badge ${std.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${std.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-warning" onclick="editStudent(${std.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteStudent(${std.id})" title="Xóa">
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
                <a class="page-link" href="#" onclick="loadStudents(${currentPageNum - 1})">Trước</a>
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
                    <a class="page-link" href="#" onclick="loadStudents(${i})">${i}</a>
                </li>
            `;
        }
    }

    if (currentPageNum < pagination.total_pages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadStudents(${currentPageNum + 1})">Tiếp</a>
            </li>
        `;
    }
}

function resetStudentForm() {
    document.getElementById('studentForm').reset();
    document.getElementById('studentId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới sinh viên';
    document.getElementById('stdCode').disabled = false;
    document.getElementById('stdPassword').required = true;
    document.getElementById('passwordLabel').textContent = '*';
    isEditMode = false;
    clearFormErrors();
}

async function editStudent(id) {
    try {
        const response = await fetch(`/api/students/${id}`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Không tìm thấy sinh viên');

        const data = await response.json();
        const std = data;

        document.getElementById('studentId').value = std.id;
        document.getElementById('stdCode').value = std.student_code;
        document.getElementById('stdCode').disabled = true;
        document.getElementById('stdName').value = std.full_name;
        document.getElementById('stdEmail').value = std.email || '';
        document.getElementById('stdPassword').value = '';
        document.getElementById('stdPassword').required = false;
        document.getElementById('passwordLabel').textContent = '(tùy chọn - để trống nếu không đổi)';
        document.getElementById('stdPhone').value = std.phone || '';
        document.getElementById('stdYear').value = std.year_of_admission || '';
        document.getElementById('stdDepartment').value = std.department_id || '';
        await loadMajors();
        document.getElementById('stdMajor').value = std.major_id || '';
        document.getElementById('stdActive').checked = std.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa sinh viên';
        isEditMode = true;
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('studentModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading student:', error);
        showAlert('Lỗi khi tải dữ liệu sinh viên', 'danger');
    }
}

async function saveStudent(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('studentId').value;
    const code = document.getElementById('stdCode').value.trim().toUpperCase();
    const name = document.getElementById('stdName').value.trim();
    const email = document.getElementById('stdEmail').value.trim().toLowerCase();
    const password = document.getElementById('stdPassword').value.trim();
    const phone = document.getElementById('stdPhone').value.trim();
    const year = document.getElementById('stdYear').value ? parseInt(document.getElementById('stdYear').value) : null;
    const departmentId = document.getElementById('stdDepartment').value || null;
    const majorId = document.getElementById('stdMajor').value || null;
    const isActive = document.getElementById('stdActive').checked;

    if (!code) {
        showFieldError('codeError', 'Mã sinh viên là bắt buộc');
        return;
    }
    if (!name) {
        showFieldError('nameError', 'Tên sinh viên là bắt buộc');
        return;
    }

    if (!isEditMode && !password) {
        showFieldError('passwordError', 'Mật khẩu là bắt buộc khi thêm mới');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/students/${id}` : '/api/students';

        const body = {
            student_code: code,
            full_name: name,
            email: email || null,
            phone: phone || null,
            year_of_admission: year,
            department_id: departmentId,
            major_id: majorId,
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
        bootstrap.Modal.getInstance(document.getElementById('studentModal')).hide();
        await loadStudents(currentPage);
    } catch (error) {
        console.error('Error saving student:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteStudent(id) {
    if (!confirm('Bạn có chắc muốn xóa sinh viên này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/students/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa sinh viên thành công', 'success');
        await loadStudents(currentPage);
    } catch (error) {
        console.error('Error deleting student:', error);
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
