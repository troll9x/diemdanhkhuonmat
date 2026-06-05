# REFACTOR PLAN V2 - Smart Attendance System
## Revised Architecture (Based on User Feedback)

---

## 1. FOLDER STRUCTURE

### Final Folder Tree

```
smart-attendance/
├── app.py                      # Flask entry point (UNCHANGED)
├── models.py                   # Database models (UNCHANGED)
├── config.py                   # Configuration (UNCHANGED)
├── config/                     # Configuration folder (UNCHANGED)
│   ├── __init__.py
│   ├── settings.py
│   └── permissions.py
├── middleware/                  # Middleware (UNCHANGED)
│   ├── __init__.py
│   ├── error_handlers.py
│   └── rate_limit.py
├── routes/                      # API routes (UNCHANGED)
│   ├── __init__.py
│   ├── auth.py
│   ├── attendance.py
│   ├── class_sessions.py
│   ├── class_schedules.py
│   ├── dashboards.py
│   ├── departments.py
│   ├── lecturers.py
│   ├── students.py
│   ├── subjects.py
│   ├── classrooms.py
│   ├── rooms.py
│   ├── buildings.py
│   ├── campuses.py
│   ├── majors.py
│   ├── programs.py
│   ├── academic_years.py
│   ├── semesters.py
│   ├── notifications.py
│   ├── reports.py
│   ├── import_export.py
│   ├── recognition.py
│   ├── training.py
│   ├── system.py
│   └── users.py
├── utils/                       # Utilities (UNCHANGED)
│   ├── __init__.py
│   ├── decorators.py
│   ├── csv_import.py
│   ├── pagination.py
│   └── validators.py
├── antispoof_utils.py          # Anti-spoofing utils (UNCHANGED)
├── face_utils.py                # Face recognition utils (UNCHANGED)
├── seed_data.py                 # Seed data (UNCHANGED)
├── templates/                   # TEMPLATES - TO BE REORGANIZED
│   ├── layouts/
│   │   └── base.html           # NEW - Base layout
│   ├── components/
│   │   ├── common/
│   │   │   ├── sidebar.html    # NEW - Dynamic sidebar
│   │   │   ├── navbar.html     # NEW - Navigation bar
│   │   │   └── footer.html     # NEW - Footer
│   │   ├── tables/
│   │   │   ├── data_table.html # NEW - Reusable table
│   │   │   └── pagination.html # NEW - Pagination
│   │   ├── cards/
│   │   │   ├── stat_card.html  # NEW - Stat card widget
│   │   │   └── info_card.html  # NEW - Info card
│   │   └── forms/
│   │       ├── modal_form.html # NEW - Modal form
│   │       └── search_form.html# NEW - Search form
│   ├── modules/
│   │   ├── auth/
│   │   │   └── login.html      # MOVED from templates/login.html
│   │   ├── admin/
│   │   │   ├── dashboard/
│   │   │   │   └── index.html # MOVED from templates/admin-dashboard.html
│   │   │   ├── users/
│   │   │   │   └── index.html # NEW - User management
│   │   │   ├── departments/
│   │   │   │   └── index.html # NEW - Department management
│   │   │   ├── subjects/
│   │   │   │   └── index.html # NEW - Subject management
│   │   │   ├── classrooms/
│   │   │   │   └── index.html # NEW - Classroom management
│   │   │   ├── attendance/
│   │   │   │   └── index.html # NEW - Attendance records
│   │   │   ├── reports/
│   │   │   │   └── index.html # NEW - Reports
│   │   │   └── settings/
│   │   │       └── index.html # NEW - System settings
│   │   ├── teacher/
│   │   │   ├── dashboard/
│   │   │   │   └── index.html # MOVED from templates/lecturer-dashboard.html
│   │   │   ├── classes/
│   │   │   │   └── index.html # NEW - My classes
│   │   │   ├── subjects/
│   │   │   │   └── index.html # NEW - My subjects
│   │   │   ├── sessions/
│   │   │   │   └── index.html # NEW - Class sessions
│   │   │   ├── attendance/
│   │   │   │   └── index.html # NEW - Teacher attendance
│   │   │   └── reports/
│   │   │       └── index.html # NEW - Teacher reports
│   │   ├── student/
│   │   │   ├── dashboard/
│   │   │   │   └── index.html # MOVED from templates/student-dashboard.html
│   │   │   └── profile/
│   │   │       └── index.html # NEW - Student profile
│   │   └── attendance/
│   │       ├── qr/
│   │       │   └── index.html # NEW - QR attendance page
│   │       └── session/
│   │           └── index.html # NEW - Attendance session
│   └── index.html              # PUBLIC landing page (UNCHANGED)
├── static/
│   ├── js/
│   │   ├── auth.js             # EXISTING - Keep as is
│   │   ├── services/
│   │   │   └── api.js         # NEW - Centralized API client
│   │   ├── components/
│   │   │   ├── sidebar.js      # NEW - Sidebar logic
│   │   │   ├── charts.js       # NEW - Chart helpers
│   │   │   └── tables.js       # NEW - Table helpers
│   │   └── modules/
│   │       ├── admin/
│   │       │   └── routes.js  # NEW - Admin API calls
│   │       ├── teacher/
│   │       │   └── routes.js  # NEW - Teacher API calls
│   │       ├── student/
│   │       │   └── routes.js  # NEW - Student API calls
│   │       └── attendance/
│   │           └── routes.js   # NEW - Attendance API calls
│   ├── css/
│   │   ├── main.css            # EXISTING
│   │   ├── themes.css          # NEW - Theme variables
│   │   └── components.css      # NEW - Component styles
│   └── img/
│       └── (existing images)
├── antispoof_models/            # ML Models (UNCHANGED)
│   ├── MiniFASNetV1SE.onnx
│   └── MiniFASNetV2.onnx
├── uploads/                     # Uploaded files (UNCHANGED)
├── tests/                       # Tests (UNCHANGED)
├── requirements.txt             # Dependencies (UNCHANGED)
├── README.md                    # Documentation (UNCHANGED)
└── .env.example                 # Environment example (UNCHANGED)
```

---

## 2. FILE MIGRATION TABLE

| Action | Source File | Destination File | Notes |
|--------|-------------|------------------|-------|
| **KEEP** | `app.py` | `app.py` | No changes |
| **KEEP** | `models.py` | `models.py` | No changes |
| **KEEP** | `config.py` | `config.py` | No changes |
| **KEEP** | `config/*` | `config/*` | No changes |
| **KEEP** | `routes/*` | `routes/*` | No changes |
| **KEEP** | `utils/*` | `utils/*` | No changes |
| **KEEP** | `middleware/*` | `middleware/*` | No changes |
| **KEEP** | `static/js/auth.js` | `static/js/auth.js` | Keep, refactor later |
| **MOVE** | `templates/login.html` | `templates/modules/auth/login.html` | Update Flask render_template |
| **MOVE** | `templates/admin-dashboard.html` | `templates/modules/admin/dashboard/index.html` | Update sidebar |
| **MOVE** | `templates/lecturer-dashboard.html` | `templates/modules/teacher/dashboard/index.html` | Rename to teacher |
| **MOVE** | `templates/student-dashboard.html` | `templates/modules/student/dashboard/index.html` | Keep as student dashboard |
| **CREATE** | — | `templates/layouts/base.html` | New base layout |
| **CREATE** | — | `templates/components/common/sidebar.html` | Dynamic sidebar |
| **CREATE** | — | `templates/components/common/navbar.html` | Navigation bar |
| **CREATE** | — | `static/js/services/api.js` | API client |
| **CREATE** | — | `static/js/components/sidebar.js` | Sidebar logic |
| **CREATE** | — | `templates/modules/attendance/qr/index.html` | QR attendance page |

---

## 3. ROUTE MIGRATION TABLE

| Current Route | HTTP Method | New Template Path | Required Permission |
|--------------|-------------|-------------------|---------------------|
| `/login` | GET | `modules/auth/login.html` | Public |
| `/admin/dashboard` | GET | `modules/admin/dashboard/index.html` | admin |
| `/teacher/dashboard` | GET | `modules/teacher/dashboard/index.html` | lecturer |
| `/student/dashboard` | GET | `modules/student/dashboard/index.html` | student |
| `/attendance/qr/<session_id>` | GET | `modules/attendance/qr/index.html` | Public (session-based) |

---

## 4. TEMPLATE MIGRATION TABLE

| Original Template | New Location | Purpose | Auth Required |
|------------------|--------------|---------|---------------|
| `login.html` | `modules/auth/login.html` | User login | No |
| `admin-dashboard.html` | `modules/admin/dashboard/index.html` | Admin dashboard | Yes (admin) |
| `lecturer-dashboard.html` | `modules/teacher/dashboard/index.html` | Teacher dashboard | Yes (lecturer) |
| `student-dashboard.html` | `modules/student/dashboard/index.html` | Student dashboard | Yes (student) |
| (new) | `modules/attendance/qr/index.html` | QR attendance for students | No (token-based) |
| (new) | `modules/attendance/session/index.html` | Session management | Yes |

---

## 5. ROLE-BASED PERMISSION MAPPING

### ADMIN Permissions (Full Access)
```
PERM_VIEW_DASHBOARD_ADMIN
PERM_MANAGE_USERS
PERM_MANAGE_DEPARTMENTS
PERM_MANAGE_MAJORS
PERM_MANAGE_PROGRAMS
PERM_MANAGE_ACADEMIC_YEARS
PERM_MANAGE_SEMESTERS
PERM_MANAGE_CAMPUSES
PERM_MANAGE_BUILDINGS
PERM_MANAGE_ROOMS
PERM_MANAGE_SUBJECTS
PERM_MANAGE_CLASSROOMS
PERM_MANAGE_SCHEDULES
PERM_MANAGE_SESSIONS
PERM_VIEW_ATTENDANCE
PERM_RECORD_ATTENDANCE
PERM_EXPORT_REPORTS
PERM_MANAGE_NOTIFICATIONS
PERM_MANAGE_FACE_MODELS
PERM_TRAIN_FACE_MODEL
PERM_SYSTEM_SETTINGS
PERM_VIEW_LOGS
```

### TEACHER Permissions (Restricted)
```
PERM_VIEW_DASHBOARD_TEACHER
PERM_VIEW_OWN_CLASSES          # View assigned classes
PERM_VIEW_OWN_SUBJECTS        # View assigned subjects
PERM_MANAGE_SESSIONS          # Manage attendance sessions for own classes
PERM_VIEW_ATTENDANCE         # View attendance for own classes
PERM_RECORD_ATTENDANCE       # Record attendance
PERM_EXPORT_REPORTS         # Export reports for own classes
PERM_VIEW_NOTIFICATIONS     # View notifications
```

### STUDENT Permissions (Minimal)
```
PERM_VIEW_OWN_ATTENDANCE     # View own attendance history
PERM_VIEW_OWN_CLASSES       # View enrolled classes
PERM_RECORD_ATTENDANCE     # Record attendance via QR/face
```

---

## 6. TEACHER CANNOT ACCESS

The following features are **FORBIDDEN** for teachers:

- ❌ Departments management (`/admin/departments`)
- ❌ Majors management (`/admin/majors`)
- ❌ Programs management (`/admin/programs`)
- ❌ Academic Years management (`/admin/academic-years`)
- ❌ Semesters management (`/admin/semesters`)
- ❌ Campuses management (`/admin/campuses`)
- ❌ Buildings management (`/admin/buildings`)
- ❌ Rooms management (`/admin/rooms`)
- ❌ Users management (`/admin/users`)
- ❌ System Settings (`/admin/system`)
- ❌ Backup/Restore
- ❌ Logs viewing (`/admin/logs`)
- ❌ Face Model training (`/admin/training`)

---

## 7. ATTENDANCE WORKFLOW (MANDATORY)

```
TEACHER                                      STUDENT                    SYSTEM
  │                                            │                         │
  ├──> Create Session ───────────────────────> │                         │
  │         (POST /api/class-sessions)         │                         │
  │                                            │                         │
  ├──> Generate QR Code ─────────────────────> │                         │
  │         (QR contains session_token)        │                         │
  │                                            │                         │
  ├──> Generate Attendance Link ────────────> │                         │
  │         (URL: /attendance/qr/<session_id>) │                         │
  │                                            │                         │
  ├──> Display QR / Send Link                  │                         │
  │                                            │                         │
  │                                            │                         │
  │         <──── Scan QR / Open Link ──────> │                         │
  │                                            │                         │
  │                                            ├──> Face Detection      │
  │                                            │     (摄像头 capture)    │
  │                                            │                         │
  │                                            ├──> Anti-Spoofing        │
  │                                            │     (MiniFASNet)        │
  │                                            │                         │
  │                                            ├──> ArcFace Verification │
  │                                            │     (Embedding match)   │
  │                                            │                         │
  │                                            ├──> Model Matching       │
  │                                            │     (SVM/Cosine)        │
  │                                            │                         │
  │                                            ├──> Attendance Record   │
  │                                            │     (POST /api/attendance)
  │                                            │                         │
  │                                            │ <─── Success Response   │
  │                                            │                         │
  ├──> Realtime Dashboard Update <─────────────┤                         │
  │         (WebSocket / Polling)              │                         │
  │                                            │                         │
  ├──> Close Session ───────────────────────> │                         │
  │         (PUT /api/class-sessions/<id>)     │                         │
```

### API Endpoints Used in Workflow

| Step | Endpoint | Method | Purpose |
|------|----------|--------|---------|
| Create Session | `/api/class-sessions` | POST | Create new attendance session |
| Generate QR | `/api/attendance/generate-qr/<session_id>` | GET | Generate QR code data |
| Get Session | `/api/class-sessions/<session_id>` | GET | Get session details |
| Record Attendance | `/api/attendance` | POST | Record student attendance |
| Verify Face | `/api/recognition/verify` | POST | Verify face embedding |
| Get Live Stats | `/api/attendance/<session_id>/stats` | GET | Get attendance counts |
| Update Session | `/api/class-sessions/<id>` | PUT | Close/update session |

---

## 8. SIDEBAR MENU STRUCTURE

### Admin Sidebar
```json
[
  {"id": "dashboard", "title": "Dashboard", "icon": "bi-speedometer2", "route": "/admin/dashboard"},
  {"id": "master-data", "title": "Master Data", "icon": "bi-database", "children": [
    {"id": "departments", "title": "Phòng ban", "route": "/admin/departments"},
    {"id": "majors", "title": "Chuyên ngành", "route": "/admin/majors"},
    {"id": "programs", "title": "Chương trình", "route": "/admin/programs"},
    {"id": "academic-years", "title": "Năm học", "route": "/admin/academic-years"},
    {"id": "semesters", "title": "Học kỳ", "route": "/admin/semesters"},
    {"id": "campuses", "title": "Cơ sở", "route": "/admin/campuses"},
    {"id": "buildings", "title": "Tòa nhà", "route": "/admin/buildings"},
    {"id": "rooms", "title": "Phòng học", "route": "/admin/rooms"}
  ]},
  {"id": "academic", "title": "Academic Structure", "icon": "bi-book", "children": [
    {"id": "subjects", "title": "Môn học", "route": "/admin/subjects"},
    {"id": "classrooms", "title": "Lớp học", "route": "/admin/classrooms"},
    {"id": "schedules", "title": "Thời khóa biểu", "route": "/admin/schedules"},
    {"id": "sessions", "title": "Buổi học", "route": "/admin/sessions"}
  ]},
  {"id": "users", "title": "Users", "icon": "bi-people", "children": [
    {"id": "lecturers", "title": "Giảng viên", "route": "/admin/lecturers"},
    {"id": "students", "title": "Sinh viên", "route": "/admin/students"}
  ]},
  {"id": "attendance", "title": "Điểm danh", "icon": "bi-clipboard-check", "route": "/admin/attendance"},
  {"id": "face-recognition", "title": "Face Recognition", "icon": "bi-person-bounding-box", "children": [
    {"id": "face-models", "title": "Face Models", "route": "/admin/face-models"},
    {"id": "training", "title": "Training", "route": "/admin/training"}
  ]},
  {"id": "import-export", "title": "Import/Export", "icon": "bi-upload", "route": "/admin/import-export"},
  {"id": "reports", "title": "Reports", "icon": "bi-file-earmark-pdf", "route": "/admin/reports"},
  {"id": "notifications", "title": "Notifications", "icon": "bi-bell", "route": "/admin/notifications"},
  {"id": "system", "title": "System", "icon": "bi-gear", "children": [
    {"id": "settings", "title": "Settings", "route": "/admin/settings"},
    {"id": "logs", "title": "Logs", "route": "/admin/logs"},
    {"id": "backup", "title": "Backup/Restore", "route": "/admin/backup"}
  ]}
]
```

### Teacher Sidebar
```json
[
  {"id": "dashboard", "title": "Dashboard", "icon": "bi-speedometer2", "route": "/teacher/dashboard"},
  {"id": "teaching", "title": "Teaching", "icon": "bi-book", "children": [
    {"id": "my-classes", "title": "My Classes", "route": "/teacher/classes"},
    {"id": "my-subjects", "title": "My Subjects", "route": "/teacher/subjects"},
    {"id": "schedule", "title": "Class Schedule", "route": "/teacher/schedule"}
  ]},
  {"id": "sessions", "title": "Sessions", "icon": "bi-calendar-event", "route": "/teacher/sessions"},
  {"id": "attendance", "title": "Điểm danh", "icon": "bi-clipboard-check", "route": "/teacher/attendance"},
  {"id": "reports", "title": "Reports", "icon": "bi-file-earmark-pdf", "route": "/teacher/reports"},
  {"id": "notifications", "title": "Notifications", "icon": "bi-bell", "route": "/teacher/notifications"}
]
```

---

## 9. STUDENT DASHBOARD ANALYSIS

**Result: Real Student Dashboard**

The file `templates/student-dashboard.html` is a **REAL STUDENT DASHBOARD** with:
- ✅ Profile display (avatar, name, student code, email)
- ✅ Attendance statistics (total, present, absent, rate)
- ✅ Attendance history table
- ✅ Enrolled classes table

**This is NOT a QR attendance page.** It should be moved to:
- `templates/modules/student/dashboard/index.html`

A **NEW QR attendance page** must be created at:
- `templates/modules/attendance/qr/index.html`

---

## 10. API-TO-PAGE MAPPING

| API Endpoint | Method | Module | Page | Auth |
|--------------|--------|--------|------|------|
| `/api/auth/login` | POST | auth | login.html | Public |
| `/api/auth/me` | GET | all | base.html | JWT |
| `/api/dashboards/admin` | GET | admin | dashboard/index.html | admin |
| `/api/dashboards/lecturer` | GET | teacher | dashboard/index.html | lecturer |
| `/api/dashboards/student` | GET | student | dashboard/index.html | student |
| `/api/departments` | GET/POST | admin | departments/index.html | admin |
| `/api/lecturers` | GET/POST | admin | users/index.html | admin |
| `/api/students` | GET/POST | admin | users/index.html | admin |
| `/api/subjects` | GET/POST | admin | subjects/index.html | admin |
| `/api/classrooms` | GET/POST | admin/teacher | classrooms/index.html | admin/lecturer |
| `/api/class-schedules` | GET/POST | admin/teacher | schedules/index.html | admin/lecturer |
| `/api/class-sessions` | GET/POST | admin/teacher | sessions/index.html | admin/lecturer |
| `/api/attendance` | GET/POST | attendance | qr/index.html | student |
| `/api/attendance/<session_id>` | GET | attendance | qr/index.html | Public |
| `/api/recognition/verify` | POST | attendance | qr/index.html | student |
| `/api/reports/attendance/excel` | GET | admin/teacher | reports/index.html | admin/lecturer |
| `/api/reports/attendance/pdf` | GET | admin/teacher | reports/index.html | admin/lecturer |

---

## 11. IMPLEMENTATION CHECKLIST

```
Phase 1: Create Structure
- [ ] Create templates/layouts/base.html
- [ ] Create templates/components/common/sidebar.html
- [ ] Create templates/components/common/navbar.html
- [ ] Create static/js/services/api.js

Phase 2: Move Templates
- [ ] Move login.html → modules/auth/login.html
- [ ] Move admin-dashboard.html → modules/admin/dashboard/index.html
- [ ] Move lecturer-dashboard.html → modules/teacher/dashboard/index.html
- [ ] Move student-dashboard.html → modules/student/dashboard/index.html

Phase 3: Update Flask Routes
- [ ] Update render_template paths in app.py
- [ ] Update Flask routes for new template locations

Phase 4: Create New Pages
- [ ] Create QR attendance page at modules/attendance/qr/index.html
- [ ] Create session page at modules/attendance/session/index.html

Phase 5: Implement Dynamic Sidebar
- [ ] Update sidebar.html with permission-based rendering
- [ ] Create sidebar.js for dynamic menu
- [ ] Update API to return user permissions

Phase 6: Testing
- [ ] Test admin login and dashboard
- [ ] Test teacher login and restricted access
- [ ] Test student login and dashboard
- [ ] Test QR attendance workflow
- [ ] Verify no backend changes

Phase 7: Documentation
- [ ] Update README.md with new structure
- [ ] Document all mappings
```

---

## 12. APPROVAL REQUEST

**Please review this plan and approve before execution.**

Changes summary:
- ✅ Keep Flask conventions (templates/, static/)
- ✅ Keep auth.js as-is, create api.js separately
- ✅ Student dashboard is REAL - not repurposed
- ✅ Teacher permissions RESTRICTED
- ✅ Attendance workflow MANDATORY
- ✅ All mappings documented

**Ready for execution?**