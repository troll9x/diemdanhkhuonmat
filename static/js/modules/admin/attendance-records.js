// Attendance Records Module
let currentPage = 1;
const itemsPerPage = 20;

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

async function loadSubjects() {
    try {
        const response = await fetch('/api/subjects?per_page=100', {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load subjects');

        const data = await response.json();
        const filterSelect = document.getElementById('filterSubject');

        data.items.forEach(subj => {
            const option = document.createElement('option');
            option.value = subj.id;
            option.textContent = `${subj.subject_name} (${subj.subject_code})`;
            filterSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error loading subjects:', error);
    }
}

async function loadAttendance(page = 1) {
    try {
        showLoadingState();

        const filterDate = document.getElementById('filterDate')?.value;
        const filterClassroom = document.getElementById('filterClassroom')?.value;
        const filterSubject = document.getElementById('filterSubject')?.value;
        const filterStatus = document.getElementById('filterStatus')?.value;
        const filterStudent = document.getElementById('filterStudent')?.value;

        // For now, load all attendance records and filter client-side
        // since the backend attendance API may not support all filters
        let url = '/api/attendance';

        // Build query params if backend supports them
        const params = [];
        if (filterDate) params.push(`date=${filterDate}`);
        if (params.length > 0) {
            url += '?' + params.join('&');
        }

        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${auth.getToken()}` }
        });

        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        let records = await response.json();
        if (!Array.isArray(records)) {
            records = records.items || records.data || [];
        }

        // Client-side filtering
        records = filterRecords(records, {
            date: filterDate,
            classroom: filterClassroom,
            subject: filterSubject,
            status: filterStatus,
            student: filterStudent
        });

        // Sort by date descending, then by time
        records.sort((a, b) => {
            const dateA = new Date(a.date || a.session_date || a.attendance_time);
            const dateB = new Date(b.date || b.session_date || b.attendance_time);
            return dateB - dateA;
        });

        // Paginate client-side
        const totalPages = Math.ceil(records.length / itemsPerPage);
        const start = (page - 1) * itemsPerPage;
        const paginatedRecords = records.slice(start, start + itemsPerPage);

        renderAttendanceTable(paginatedRecords);
        renderPagination(totalPages, page);
        currentPage = page;

        hideLoadingState();
    } catch (error) {
        console.error('Error loading attendance:', error);
        showAlert('Lỗi khi tải dữ liệu', 'danger');
        hideLoadingState();
    }
}

function filterRecords(records, filters) {
    return records.filter(rec => {
        if (filters.date && rec.date && rec.date !== filters.date) {
            return false;
        }
        if (filters.status && rec.status !== filters.status) {
            return false;
        }
        if (filters.student && rec.name) {
            const search = filters.student.toLowerCase();
            if (!rec.name.toLowerCase().includes(search) &&
                !rec.student_code?.toLowerCase().includes(search)) {
                return false;
            }
        }
        return true;
    });
}

function renderAttendanceTable(records) {
    const tbody = document.getElementById('attendanceTable');
    const emptyState = document.getElementById('emptyState');
    const tableContainer = document.getElementById('tableContainer');

    if (!records || records.length === 0) {
        emptyState.classList.remove('d-none');
        tableContainer.classList.add('d-none');
        return;
    }

    emptyState.classList.add('d-none');
    tableContainer.classList.remove('d-none');

    const statusLabels = {
        'present': 'Có mặt',
        'late': 'Muộn',
        'absent': 'Vắng',
        'excused': 'Xin phép'
    };

    const statusColors = {
        'present': 'success',
        'late': 'warning',
        'absent': 'danger',
        'excused': 'info'
    };

    tbody.innerHTML = records.map(rec => {
        const date = new Date(rec.date || rec.attendance_time || '').toLocaleDateString('vi-VN');
        const time = new Date(rec.attendance_time || '').toLocaleTimeString('vi-VN', {
            hour: '2-digit',
            minute: '2-digit'
        });

        const statusLabel = statusLabels[rec.status] || rec.status || '-';
        const statusColor = statusColors[rec.status] || 'secondary';

        const confidence = rec.confidence_score
            ? (rec.confidence_score * 100).toFixed(1) + '%'
            : '-';

        return `
            <tr>
                <td><small>${escapeHtml(rec.student_code || '--')}</small></td>
                <td><strong>${escapeHtml(rec.name || rec.student_name || '--')}</strong></td>
                <td><small>${escapeHtml(rec.classroom_name || '--')}</small></td>
                <td><small>${escapeHtml(rec.subject_name || '--')}</small></td>
                <td><small>${date}</small></td>
                <td><small>${time}</small></td>
                <td><span class="badge bg-${statusColor}">${statusLabel}</span></td>
                <td><small>${confidence}</small></td>
            </tr>
        `;
    }).join('');
}

function renderPagination(totalPages, currentPageNum) {
    const paginationContainer = document.getElementById('paginationContainer');
    const paginationList = document.getElementById('paginationList');

    if (totalPages <= 1) {
        paginationContainer.classList.add('d-none');
        return;
    }

    paginationContainer.classList.remove('d-none');
    paginationList.innerHTML = '';

    if (currentPageNum > 1) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadAttendance(${currentPageNum - 1})">Trước</a>
            </li>
        `;
    }

    for (let i = 1; i <= totalPages; i++) {
        if (i === currentPageNum) {
            paginationList.innerHTML += `
                <li class="page-item active">
                    <span class="page-link">${i}</span>
                </li>
            `;
        } else {
            paginationList.innerHTML += `
                <li class="page-item">
                    <a class="page-link" href="#" onclick="loadAttendance(${i})">${i}</a>
                </li>
            `;
        }
    }

    if (currentPageNum < totalPages) {
        paginationList.innerHTML += `
            <li class="page-item">
                <a class="page-link" href="#" onclick="loadAttendance(${currentPageNum + 1})">Tiếp</a>
            </li>
        `;
    }
}

function exportData() {
    showAlert('Tính năng xuất Excel sẽ được cập nhật', 'info');
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

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
