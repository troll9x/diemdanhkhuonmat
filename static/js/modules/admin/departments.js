/**
 * Module Quản Lý Khoa (Admin Departments)
 * CRUD khoa/bộ môn: tạo/sửa/xóa khoa, lọc theo tên và trạng thái.
 * Hàm chính:
 *   loadDepartments(page)   — Tải và phân trang danh sách khoa
 *   renderDepartmentsTable()— Render bảng khoa với nút sửa/xóa
 *   renderPagination()      — Render điều hướng phân trang
 *   editDepartment(id)      — Mở modal sửa khoa
 *   saveDepartment(event)   — Lưu khoa (POST hoặc PUT)
 *   deleteDepartment(id)    — Xóa khoa sau khi xác nhận
 *   escapeHtml()            — Escape HTML ngăn XSS
 */
let currentPage = 1;
const itemsPerPage = 10;

async function loadDepartments(page = 1) {
    try {
        showLoadingState();

        const search = document.getElementById('searchInput')?.value || '';
        const isActive = document.getElementById('filterActive')?.value;

        let url = `/api/departments?page=${page}&per_page=${itemsPerPage}`;
        if (search) url += `&search=${encodeURIComponent(search)}`;
        if (isActive !== '') url += `&is_active=${isActive}`;

        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();
        renderDepartmentsTable(data.items);
        renderPagination(data.pagination, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading departments:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderDepartmentsTable(departments) {
    const tbody = document.getElementById('departmentsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!departments || departments.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = departments.map(dept => `
        <tr>
            <td>
                <span class="badge bg-info">${escapeHtml(dept.code)}</span>
            </td>
            <td>
                <strong>${escapeHtml(dept.name)}</strong>
            </td>
            <td>
                <small>${dept.description ? escapeHtml(dept.description) : '-'}</small>
            </td>
            <td>
                <span class="badge ${dept.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${dept.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <small>${new Date(dept.created_at).toLocaleDateString('vi-VN')}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-warning" onclick="editDepartment(${dept.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteDepartment(${dept.id})" title="Xóa">
                        <i class="bi bi-trash"></i>
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

function renderPagination(pagination, currentPage) {
    const paginationContainer = document.getElementById('paginationContainer');
    const paginationList = document.getElementById('paginationList');

    if (!pagination || pagination.total_pages <= 1) {
        paginationContainer.classList.add('d-none');
        return;
    }

    paginationContainer.classList.remove('d-none');
    paginationList.innerHTML = '';

    // Previous button
    if (currentPage > 1) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadDepartments(${currentPage - 1})">
                    Trước
                </a>
            </li>
        `;
    }

    // Page numbers
    for (let i = 1; i <= pagination.total_pages; i++) {
        if (i === currentPage) {
            paginationList.innerHTML += `
                <li class="page-item active">
                    <span class="page-link">${i}</span>
                </li>
            `;
        } else {
            paginationList.innerHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="loadDepartments(${i})">${i}</a>
                </li>
            `;
        }
    }

    // Next button
    if (currentPage < pagination.total_pages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadDepartments(${currentPage + 1})">
                    Tiếp
                </a>
            </li>
        `;
    }
}

function resetDepartmentForm() {
    document.getElementById('departmentForm').reset();
    document.getElementById('departmentId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới phòng ban';
    document.getElementById('deptCode').disabled = false;
    clearFormErrors();
}

async function editDepartment(id) {
    try {
        const response = await fetch(`/api/departments/${id}`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) {
            throw new Error('Không tìm thấy phòng ban');
        }

        const data = await response.json();
        const dept = data;

        document.getElementById('departmentId').value = dept.id;
        document.getElementById('deptCode').value = dept.code;
        document.getElementById('deptCode').disabled = true;
        document.getElementById('deptName').value = dept.name;
        document.getElementById('deptDescription').value = dept.description || '';
        document.getElementById('deptActive').checked = dept.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa phòng ban';
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('departmentModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading department:', error);
        showAlert('Lỗi khi tải dữ liệu phòng ban', 'danger');
    }
}

async function saveDepartment(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('departmentId').value;
    const code = document.getElementById('deptCode').value.trim().toUpperCase();
    const name = document.getElementById('deptName').value.trim();
    const description = document.getElementById('deptDescription').value.trim();
    const isActive = document.getElementById('deptActive').checked;

    // Validation
    if (!code) {
        showFieldError('codeError', 'Mã phòng ban là bắt buộc');
        return;
    }
    if (!name) {
        showFieldError('nameError', 'Tên phòng ban là bắt buộc');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/departments/${id}` : '/api/departments';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({
                code,
                name,
                description: description || null,
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
        bootstrap.Modal.getInstance(document.getElementById('departmentModal')).hide();
        await loadDepartments(currentPage);
    } catch (error) {
        console.error('Error saving department:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteDepartment(id) {
    if (!confirm('Bạn có chắc muốn xóa phòng ban này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/departments/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            if (response.status === 409) {
                const details = data.details;
                showAlert(
                    `Không thể xóa: ${details.lecturers} giảng viên, ${details.students} sinh viên, ${details.subjects} môn học`,
                    'warning'
                );
            } else {
                throw new Error(data.error || 'Lỗi khi xóa');
            }
            return;
        }

        showAlert('Xóa phòng ban thành công', 'success');
        await loadDepartments(currentPage);
    } catch (error) {
        console.error('Error deleting department:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    }
}

// UI Helpers
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
