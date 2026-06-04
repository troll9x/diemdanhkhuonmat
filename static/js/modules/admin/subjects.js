// Subjects Module
let currentPage = 1;
const itemsPerPage = 10;

async function loadDepartments() {
    try {
        const response = await fetch('/api/departments?per_page=100', {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Failed to load departments');

        const data = await response.json();
        const select = document.getElementById('subjDepartment');
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

async function loadSubjects(page = 1) {
    try {
        showLoadingState();

        const search = document.getElementById('searchInput')?.value || '';
        const departmentId = document.getElementById('filterDepartment')?.value;
        const isActive = document.getElementById('filterActive')?.value;

        let url = `/api/subjects?page=${page}&per_page=${itemsPerPage}`;
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
        renderSubjectsTable(data.items);
        renderPagination(data.pagination, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading subjects:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function renderSubjectsTable(subjects) {
    const tbody = document.getElementById('subjectsTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!subjects || subjects.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    tbody.innerHTML = subjects.map(subj => `
        <tr>
            <td>
                <span class="badge bg-info">${escapeHtml(subj.subject_code)}</span>
            </td>
            <td>
                <strong>${escapeHtml(subj.subject_name)}</strong>
            </td>
            <td>
                <span class="badge bg-light text-dark">${subj.credits || '-'}</span>
            </td>
            <td>
                ${subj.department ? escapeHtml(subj.department.name) : '-'}
            </td>
            <td>
                <span class="badge ${subj.is_active ? 'bg-success' : 'bg-secondary'}">
                    ${subj.is_active ? 'Hoạt động' : 'Không hoạt động'}
                </span>
            </td>
            <td>
                <small>${new Date(subj.created_at).toLocaleDateString('vi-VN')}</small>
            </td>
            <td>
                <div class="btn-group btn-group-sm" role="group">
                    <button class="btn btn-outline-warning" onclick="editSubject(${subj.id})" title="Sửa">
                        <i class="bi bi-pencil"></i>
                    </button>
                    <button class="btn btn-outline-danger" onclick="deleteSubject(${subj.id})" title="Xóa">
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
                <a class="page-link" href="#" onclick="loadSubjects(${currentPageNum - 1})">Trước</a>
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
                    <a class="page-link" href="#" onclick="loadSubjects(${i})">${i}</a>
                </li>
            `;
        }
    }

    if (currentPageNum < pagination.total_pages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadSubjects(${currentPageNum + 1})">Tiếp</a>
            </li>
        `;
    }
}

function resetSubjectForm() {
    document.getElementById('subjectForm').reset();
    document.getElementById('subjectId').value = '';
    document.getElementById('modalTitle').textContent = 'Thêm mới môn học';
    document.getElementById('subjCode').disabled = false;
    clearFormErrors();
}

async function editSubject(id) {
    try {
        const response = await fetch(`/api/subjects/${id}`, {
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        if (!response.ok) throw new Error('Không tìm thấy môn học');

        const data = await response.json();
        const subj = data;

        document.getElementById('subjectId').value = subj.id;
        document.getElementById('subjCode').value = subj.subject_code;
        document.getElementById('subjCode').disabled = true;
        document.getElementById('subjName').value = subj.subject_name;
        document.getElementById('subjCredits').value = subj.credits || '';
        document.getElementById('subjDepartment').value = subj.department_id || '';
        document.getElementById('subjDescription').value = subj.description || '';
        document.getElementById('subjActive').checked = subj.is_active;

        document.getElementById('modalTitle').textContent = 'Sửa môn học';
        clearFormErrors();

        const modal = new bootstrap.Modal(document.getElementById('subjectModal'));
        modal.show();
    } catch (error) {
        console.error('Error loading subject:', error);
        showAlert('Lỗi khi tải dữ liệu môn học', 'danger');
    }
}

async function saveSubject(event) {
    event.preventDefault();
    clearFormErrors();

    const id = document.getElementById('subjectId').value;
    const code = document.getElementById('subjCode').value.trim().toUpperCase();
    const name = document.getElementById('subjName').value.trim();
    const credits = document.getElementById('subjCredits').value ? parseInt(document.getElementById('subjCredits').value) : null;
    const departmentId = document.getElementById('subjDepartment').value || null;
    const description = document.getElementById('subjDescription').value.trim();
    const isActive = document.getElementById('subjActive').checked;

    if (!code) {
        showFieldError('codeError', 'Mã môn học là bắt buộc');
        return;
    }
    if (!name) {
        showFieldError('nameError', 'Tên môn học là bắt buộc');
        return;
    }

    setSubmitLoading(true);

    try {
        const method = id ? 'PUT' : 'POST';
        const url = id ? `/api/subjects/${id}` : '/api/subjects';

        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${auth.getToken()}`
            },
            body: JSON.stringify({
                subject_code: code,
                subject_name: name,
                credits: credits,
                department_id: departmentId,
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
        bootstrap.Modal.getInstance(document.getElementById('subjectModal')).hide();
        await loadSubjects(currentPage);
    } catch (error) {
        console.error('Error saving subject:', error);
        showAlert('Lỗi: ' + error.message, 'danger');
    } finally {
        setSubmitLoading(false);
    }
}

async function deleteSubject(id) {
    if (!confirm('Bạn có chắc muốn xóa môn học này?')) {
        return;
    }

    try {
        const response = await fetch(`/api/subjects/${id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${auth.getToken()}`
            }
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Lỗi khi xóa');
        }

        showAlert('Xóa môn học thành công', 'success');
        await loadSubjects(currentPage);
    } catch (error) {
        console.error('Error deleting subject:', error);
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
