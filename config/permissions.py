"""Hằng số phân quyền (RBAC — Kiểm soát truy cập dựa trên vai trò)."""

# ── Vai trò người dùng ────────────────────────────────────────────────────────
ROLE_ADMIN = 'admin'        # Quản trị viên
ROLE_LECTURER = 'lecturer'  # Giảng viên (hệ thống cũ)
ROLE_TEACHER = 'teacher'    # Giảng viên (hệ thống mới AppUser)
ROLE_STUDENT = 'student'    # Sinh viên

# ── Mã quyền (Permission Codes) ───────────────────────────────────────────────

# Quyền của Quản trị viên
PERM_MANAGE_USERS = 'manage_users'                          # Quản lý tài khoản người dùng
PERM_MANAGE_LECTURERS = 'manage_lecturers'                  # Quản lý giảng viên
PERM_MANAGE_STUDENTS = 'manage_students'                    # Quản lý sinh viên
PERM_MANAGE_DEPARTMENTS = 'manage_departments'              # Quản lý phòng ban / khoa
PERM_MANAGE_SUBJECTS = 'manage_subjects'                    # Quản lý môn học
PERM_MANAGE_CLASSROOMS = 'manage_classrooms'                # Quản lý lớp học
PERM_MANAGE_SCHEDULES = 'manage_schedules'                  # Quản lý thời khoá biểu
PERM_MANAGE_SESSIONS = 'manage_sessions'                    # Quản lý buổi học
PERM_VIEW_ALL_ATTENDANCE = 'view_all_attendance'            # Xem toàn bộ dữ liệu điểm danh
PERM_EXPORT_ALL_REPORTS = 'export_all_reports'              # Xuất báo cáo toàn hệ thống
PERM_VIEW_ALL_REPORTS = 'view_all_reports'                  # Xem báo cáo toàn hệ thống
PERM_MANAGE_SYSTEM_SETTINGS = 'manage_system_settings'      # Quản lý cài đặt hệ thống
PERM_VIEW_AUDIT_LOGS = 'view_audit_logs'                    # Xem nhật ký kiểm toán
PERM_MANAGE_MODELS = 'manage_models'                        # Quản lý mô hình AI nhận diện khuôn mặt
PERM_MANAGE_NOTIFICATIONS = 'manage_notifications'          # Quản lý thông báo hệ thống
PERM_MANAGE_CLASS_SCHEDULES = 'manage_class_schedules'      # Quản lý lịch học (dành cho Admin)
PERM_VIEW_CLASS_SCHEDULES = 'view_class_schedules'          # Xem lịch học (Admin và Giảng viên)
PERM_CREATE_CLASS_SCHEDULE = 'create_class_schedule'        # Tạo lịch học mới
PERM_UPDATE_CLASS_SCHEDULE = 'update_class_schedule'        # Cập nhật lịch học
PERM_DELETE_CLASS_SCHEDULE = 'delete_class_schedule'        # Xóa lịch học

# Quyền của Giảng viên
PERM_VIEW_OWN_CLASSES = 'view_own_classes'                          # Xem lớp học của mình
PERM_VIEW_OWN_STUDENTS = 'view_own_students'                        # Xem sinh viên trong lớp của mình
PERM_MANAGE_OWN_SESSIONS = 'manage_own_sessions'                    # Quản lý buổi học của mình
PERM_VIEW_OWN_ATTENDANCE = 'view_own_attendance'                    # Xem điểm danh của lớp mình
PERM_EXPORT_OWN_REPORTS = 'export_own_reports'                      # Xuất báo cáo của lớp mình
PERM_VIEW_REPORTS = 'view_reports'                                  # Xem báo cáo và thống kê

# Quyền của Sinh viên
PERM_VIEW_OWN_PROFILE = 'view_own_profile'                          # Xem hồ sơ cá nhân
PERM_VIEW_STUDENT_OWN_ATTENDANCE = 'view_student_own_attendance'    # Xem lịch sử điểm danh của sinh viên
PERM_REGISTER_FACE = 'register_face'                                # Đăng ký khuôn mặt
PERM_MARK_ATTENDANCE = 'mark_attendance'                            # Thực hiện điểm danh

# ── Định nghĩa chi tiết từng quyền ───────────────────────────────────────────
# Mỗi quyền có: name (tên), description (mô tả), roles (danh sách vai trò có quyền này)
PERMISSIONS = {
    # ── Quyền quản trị ───────────────────────────────────────────────────────
    PERM_MANAGE_USERS: {
        'name': 'Manage Users',
        'description': 'Create, read, update, delete all users',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_LECTURERS: {
        'name': 'Manage Lecturers',
        'description': 'Create, read, update, delete lecturers',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_STUDENTS: {
        'name': 'Manage Students',
        'description': 'Create, read, update, delete students',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_DEPARTMENTS: {
        'name': 'Manage Departments',
        'description': 'Manage department master data',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_SUBJECTS: {
        'name': 'Manage Subjects',
        'description': 'Manage subject master data',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_CLASSROOMS: {
        'name': 'Manage Classrooms',
        'description': 'Create and manage classrooms',
        'roles': [ROLE_ADMIN]
    },
    # ── Quyền quản lý lịch học ───────────────────────────────────────────────
    PERM_MANAGE_CLASS_SCHEDULES: {
        'name': 'Manage Class Schedules',
        'description': 'Create, update, delete class schedules',
        'roles': [ROLE_ADMIN]
    },
    PERM_VIEW_CLASS_SCHEDULES: {
        'name': 'View Class Schedules',
        'description': 'View class schedules',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]   # Admin và Giảng viên đều được xem
    },
    PERM_CREATE_CLASS_SCHEDULE: {
        'name': 'Create Class Schedule',
        'description': 'Create new class schedules',
        'roles': [ROLE_ADMIN]
    },
    PERM_UPDATE_CLASS_SCHEDULE: {
        'name': 'Update Class Schedule',
        'description': 'Update existing class schedules',
        'roles': [ROLE_ADMIN]
    },
    PERM_DELETE_CLASS_SCHEDULE: {
        'name': 'Delete Class Schedule',
        'description': 'Delete class schedules',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_SESSIONS: {
        'name': 'Manage Sessions',
        'description': 'Manage all class sessions',
        'roles': [ROLE_ADMIN]
    },
    PERM_VIEW_ALL_ATTENDANCE: {
        'name': 'View All Attendance',
        'description': 'View attendance records for all classes',
        'roles': [ROLE_ADMIN]
    },
    PERM_EXPORT_ALL_REPORTS: {
        'name': 'Export All Reports',
        'description': 'Export reports for all classes',
        'roles': [ROLE_ADMIN]
    },
    PERM_VIEW_ALL_REPORTS: {
        'name': 'View All Reports',
        'description': 'View all attendance reports and statistics',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_SYSTEM_SETTINGS: {
        'name': 'Manage System Settings',
        'description': 'Configure system settings',
        'roles': [ROLE_ADMIN]
    },
    PERM_VIEW_AUDIT_LOGS: {
        'name': 'View Audit Logs',
        'description': 'View system audit logs',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_MODELS: {
        'name': 'Manage ML Models',
        'description': 'Train and manage face recognition models',
        'roles': [ROLE_ADMIN]
    },
    PERM_MANAGE_NOTIFICATIONS: {
        'name': 'Manage Notifications',
        'description': 'Create and manage system notifications',
        'roles': [ROLE_ADMIN]
    },

    # ── Quyền giảng viên ─────────────────────────────────────────────────────
    PERM_VIEW_OWN_CLASSES: {
        'name': 'View Own Classes',
        'description': 'View classes taught by lecturer',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },
    PERM_VIEW_OWN_STUDENTS: {
        'name': 'View Own Students',
        'description': 'View students in own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },
    PERM_MANAGE_OWN_SESSIONS: {
        'name': 'Manage Own Sessions',
        'description': 'Modify sessions for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },
    PERM_VIEW_OWN_ATTENDANCE: {
        'name': 'View Own Attendance',
        'description': 'View attendance for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },
    PERM_EXPORT_OWN_REPORTS: {
        'name': 'Export Own Reports',
        'description': 'Export reports for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },
    PERM_VIEW_REPORTS: {
        'name': 'View Reports',
        'description': 'View attendance reports and statistics',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER]
    },

    # ── Quyền sinh viên ───────────────────────────────────────────────────────
    PERM_VIEW_OWN_PROFILE: {
        'name': 'View Own Profile',
        'description': 'View own profile information',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_TEACHER, ROLE_STUDENT]
    },
    PERM_VIEW_STUDENT_OWN_ATTENDANCE: {
        'name': 'View Student Own Attendance',
        'description': 'View own attendance history (student)',
        'roles': [ROLE_ADMIN, ROLE_STUDENT]
    },
    PERM_REGISTER_FACE: {
        'name': 'Register Face',
        'description': 'Register face for attendance',
        'roles': [ROLE_ADMIN, ROLE_STUDENT]
    },
    PERM_MARK_ATTENDANCE: {
        'name': 'Mark Attendance',
        'description': 'Mark attendance via face recognition',
        'roles': [ROLE_ADMIN, ROLE_STUDENT]
    }
}


def get_role_permissions(role):
    """
    Lấy danh sách tất cả mã quyền của một vai trò.
    Tham số: role — chuỗi vai trò ('admin', 'lecturer', 'student')
    Trả về: list các mã quyền mà vai trò đó có.
    """
    return [
        perm_code for perm_code, perm_info in PERMISSIONS.items()
        if role in perm_info['roles']
    ]


def has_permission(role, permission_code):
    """
    Kiểm tra xem một vai trò có quyền cụ thể không.
    Tham số:
      role — chuỗi vai trò
      permission_code — mã quyền cần kiểm tra
    Trả về: True nếu có quyền, False nếu không.
    """
    perm = PERMISSIONS.get(permission_code)
    if not perm:
        return False
    return role in perm['roles']
