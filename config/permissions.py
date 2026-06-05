"""Permission constants for RBAC system."""

# User Roles
ROLE_ADMIN = 'admin'
ROLE_LECTURER = 'lecturer'
ROLE_STUDENT = 'student'

# Permission Codes
# Admin Permissions
PERM_MANAGE_USERS = 'manage_users'
PERM_MANAGE_LECTURERS = 'manage_lecturers'
PERM_MANAGE_STUDENTS = 'manage_students'
PERM_MANAGE_DEPARTMENTS = 'manage_departments'
PERM_MANAGE_SUBJECTS = 'manage_subjects'
PERM_MANAGE_CLASSROOMS = 'manage_classrooms'
PERM_MANAGE_SCHEDULES = 'manage_schedules'
PERM_MANAGE_SESSIONS = 'manage_sessions'
PERM_VIEW_ALL_ATTENDANCE = 'view_all_attendance'
PERM_EXPORT_ALL_REPORTS = 'export_all_reports'
PERM_VIEW_ALL_REPORTS = 'view_all_reports'
PERM_MANAGE_SYSTEM_SETTINGS = 'manage_system_settings'
PERM_VIEW_AUDIT_LOGS = 'view_audit_logs'
PERM_MANAGE_MODELS = 'manage_models'
PERM_MANAGE_NOTIFICATIONS = 'manage_notifications'
PERM_MANAGE_CLASS_SCHEDULES = 'manage_class_schedules' # For Admins
PERM_VIEW_CLASS_SCHEDULES = 'view_class_schedules'     # For Admins, Lecturers
PERM_CREATE_CLASS_SCHEDULE = 'create_class_schedule'   # For Admins
PERM_UPDATE_CLASS_SCHEDULE = 'update_class_schedule'   # For Admins
PERM_DELETE_CLASS_SCHEDULE = 'delete_class_schedule'   # For Admins

# Lecturer Permissions
PERM_VIEW_OWN_CLASSES = 'view_own_classes'
PERM_VIEW_OWN_STUDENTS = 'view_own_students'
PERM_MANAGE_OWN_SESSIONS = 'manage_own_sessions'
PERM_VIEW_OWN_ATTENDANCE = 'view_own_attendance'
PERM_EXPORT_OWN_REPORTS = 'export_own_reports'
PERM_VIEW_REPORTS = 'view_reports'

# Student Permissions
PERM_VIEW_OWN_PROFILE = 'view_own_profile'
PERM_VIEW_OWN_ATTENDANCE = 'view_own_attendance'
PERM_REGISTER_FACE = 'register_face'
PERM_MARK_ATTENDANCE = 'mark_attendance'

# Permission Definitions
PERMISSIONS = {
    # Admin
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
    # Class Schedule Permissions
    PERM_MANAGE_CLASS_SCHEDULES: {
        'name': 'Manage Class Schedules',
        'description': 'Create, update, delete class schedules',
        'roles': [ROLE_ADMIN]
    },
    PERM_VIEW_CLASS_SCHEDULES: {
        'name': 'View Class Schedules',
        'description': 'View class schedules',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
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
    # End Class Schedule Permissions
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
    
    # Lecturer
    PERM_VIEW_OWN_CLASSES: {
        'name': 'View Own Classes',
        'description': 'View classes taught by lecturer',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    PERM_VIEW_OWN_STUDENTS: {
        'name': 'View Own Students',
        'description': 'View students in own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    PERM_MANAGE_OWN_SESSIONS: {
        'name': 'Manage Own Sessions',
        'description': 'Modify sessions for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    PERM_VIEW_OWN_ATTENDANCE: {
        'name': 'View Own Attendance',
        'description': 'View attendance for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    PERM_EXPORT_OWN_REPORTS: {
        'name': 'Export Own Reports',
        'description': 'Export reports for own classes',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    PERM_VIEW_REPORTS: {
        'name': 'View Reports',
        'description': 'View attendance reports and statistics',
        'roles': [ROLE_ADMIN, ROLE_LECTURER]
    },
    
    # Student
    PERM_VIEW_OWN_PROFILE: {
        'name': 'View Own Profile',
        'description': 'View own profile information',
        'roles': [ROLE_ADMIN, ROLE_LECTURER, ROLE_STUDENT]
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
    """Get all permission codes for a given role."""
    return [
        perm_code for perm_code, perm_info in PERMISSIONS.items()
        if role in perm_info['roles']
    ]

def has_permission(role, permission_code):
    """Check if a role has a specific permission."""
    perm = PERMISSIONS.get(permission_code)
    if not perm:
        return False
    return role in perm['roles']