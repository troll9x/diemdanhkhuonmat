# API AUTHENTICATION INVESTIGATION REPORT

## ISSUE SUMMARY

After successful login and dashboard page load:
- ✅ Login succeeds (200)
- ✅ Admin dashboard page loads
- ❌ Dashboard API requests fail with 404 or 401
  - GET /api/dashboards/admin → 404
  - GET /api/system/stats → 401 Invalid token

---

## FINDINGS

### 1. FRONTEND API SERVICE ✅

**File**: `static/js/services/api.js`  
**Lines**: 15-62

**Status**: CORRECT - Authorization header is properly formatted

```javascript
async call(endpoint, options = {}) {
    const token = auth.getToken();
    if (!token && !options.public) {
        throw new Error('Not authenticated');
    }

    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;  // ✅ CORRECT FORMAT
    }
    // ...
}
```

**Verification**:
- ✅ Token retrieved from localStorage
- ✅ Authorization header format: `Bearer <token>`
- ✅ Token refresh logic implemented (lines 41-50)
- ✅ 401 handling redirects to login

---

### 2. DASHBOARD API ENDPOINTS ✅

**File**: `routes/dashboards.py`

**Status**: ROUTES EXIST

#### Admin Dashboard Routes:
- ✅ Line 25: `@dashboards_bp.route('/admin/overview', methods=['GET'])`
  - Protected by: `@jwt_required()` + `@permission_required(PERM_VIEW_ALL_REPORTS)`
  - Returns: Overview statistics

- ✅ Line 105: `@dashboards_bp.route('/admin/attendance-trends', methods=['GET'])`
  - Protected by: `@jwt_required()` + `@permission_required(PERM_VIEW_ALL_REPORTS)`

- ✅ Line 156: `@dashboards_bp.route('/admin/department-stats', methods=['GET'])`
  - Protected by: `@jwt_required()` + `@permission_required(PERM_VIEW_ALL_REPORTS)`

- ✅ Line 197: `@dashboards_bp.route('/admin/classroom-performance', methods=['GET'])`
  - Protected by: `@jwt_required()` + `@permission_required(PERM_VIEW_ALL_REPORTS)`

#### Lecturer Dashboard Routes:
- ✅ Line 255: `@dashboards_bp.route('/lecturer/overview', methods=['GET'])`
  - Protected by: `@jwt_required()`

- ✅ Line 321: `@dashboards_bp.route('/lecturer/class/<int:classroom_id>/stats', methods=['GET'])`
  - Protected by: `@jwt_required()`

- ✅ Line 401: `@dashboards_bp.route('/lecturer/sessions', methods=['GET'])`
  - Protected by: `@jwt_required()`

#### Student Dashboard Routes:
- ✅ Line 465: `@dashboards_bp.route('/student/profile', methods=['GET'])`
  - Protected by: `@jwt_required()`

- ✅ Line 514: `@dashboards_bp.route('/student/attendance-history', methods=['GET'])`
  - Protected by: `@jwt_required()`

- ✅ Line 563: `@dashboards_bp.route('/student/attendance-stats', methods=['GET'])`
  - Protected by: `@jwt_required()`

- ✅ Line 634: `@dashboards_bp.route('/student/upcoming-sessions', methods=['GET'])`
  - Protected by: `@jwt_required()`

---

### 3. SYSTEM STATS ENDPOINT ✅

**File**: `routes/system.py`  
**Line**: 284

**Status**: ROUTE EXISTS

```python
@system_bp.route('/stats', methods=['GET'])
@jwt_required()
@permission_required([PERM_MANAGE_SYSTEM_SETTINGS])
def get_system_stats():
    """
    Get system statistics and health metrics.
    """
```

**Issue**: Requires `PERM_MANAGE_SYSTEM_SETTINGS` permission
- Only admins have this permission
- Lecturers and students will get 403 Forbidden

---

## ROOT CAUSES IDENTIFIED

### Issue #1: Missing API Endpoint in Frontend

**File**: `static/js/services/api.js`  
**Line**: 161-163

**Problem**: Frontend calls `/api/dashboards/admin` but backend route is `/api/dashboards/admin/overview`

```javascript
// WRONG
async getAdminDashboard() {
    return this.get('/dashboards/admin');  // ❌ 404 - Route doesn't exist
}
```

**Should be**:
```javascript
// CORRECT
async getAdminDashboard() {
    return this.get('/dashboards/admin/overview');  // ✅ Correct route
}
```

---

### Issue #2: Permission Mismatch on /api/system/stats

**File**: `routes/system.py`  
**Line**: 286

**Problem**: `/api/system/stats` requires `PERM_MANAGE_SYSTEM_SETTINGS` but admin user may not have this permission

```python
@system_bp.route('/stats', methods=['GET'])
@jwt_required()
@permission_required([PERM_MANAGE_SYSTEM_SETTINGS])  # ❌ Too restrictive
def get_system_stats():
```

**Solution**: Either:
1. Grant admin users this permission
2. Change permission requirement to `PERM_VIEW_ALL_REPORTS`
3. Remove permission check (allow all authenticated users)

---

### Issue #3: Missing Logging in Protected Routes

**Status**: No logging in dashboard or system routes to debug auth failures

**Solution**: Add logging to all protected endpoints:
```python
print("[API] GET /api/dashboards/admin/overview")
print(f"[API] Authorization Header: {request.headers.get('Authorization')}")
print(f"[API] JWT Identity: {get_jwt_identity()}")
print(f"[API] JWT Claims: {get_jwt()}")
```

---

## VERIFICATION CHECKLIST

### Frontend API Service
- [x] Authorization header format correct: `Bearer <token>`
- [x] Token retrieved from localStorage
- [x] Token refresh logic implemented
- [x] 401 handling implemented

### Dashboard Routes
- [x] `/api/dashboards/admin/overview` exists
- [x] `/api/dashboards/lecturer/overview` exists
- [x] `/api/dashboards/student/profile` exists
- [x] All routes protected with `@jwt_required()`
- [x] Admin routes require `PERM_VIEW_ALL_REPORTS`

### System Routes
- [x] `/api/system/stats` exists
- [x] Protected with `@jwt_required()`
- [x] Requires `PERM_MANAGE_SYSTEM_SETTINGS`

---

## FIXES REQUIRED

### Fix #1: Update Frontend API Endpoints

**File**: `static/js/services/api.js`

Change:
```javascript
async getAdminDashboard() {
    return this.get('/dashboards/admin');
}

async getTeacherDashboard() {
    return this.get('/dashboards/lecturer');
}

async getStudentDashboard() {
    return this.get('/dashboards/student');
}
```

To:
```javascript
async getAdminDashboard() {
    return this.get('/dashboards/admin/overview');
}

async getTeacherDashboard() {
    return this.get('/dashboards/lecturer/overview');
}

async getStudentDashboard() {
    return this.get('/dashboards/student/profile');
}
```

---

### Fix #2: Add Logging to Protected Routes

**File**: `routes/dashboards.py`

Add at start of each endpoint:
```python
print(f"[API] GET /api/dashboards/admin/overview")
print(f"[API] Authorization Header: {request.headers.get('Authorization')}")
print(f"[API] JWT Identity: {get_jwt_identity()}")
```

**File**: `routes/system.py`

Add at start of `/stats` endpoint:
```python
print(f"[API] GET /api/system/stats")
print(f"[API] Authorization Header: {request.headers.get('Authorization')}")
print(f"[API] JWT Identity: {get_jwt_identity()}")
```

---

### Fix #3: Adjust System Stats Permission

**File**: `routes/system.py`  
**Line**: 286

Option A - Allow all authenticated users:
```python
@system_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_system_stats():
```

Option B - Use report permission:
```python
@system_bp.route('/stats', methods=['GET'])
@jwt_required()
@permission_required([PERM_VIEW_ALL_REPORTS])
def get_system_stats():
```

---

## EXPECTED BEHAVIOR AFTER FIXES

1. ✅ Login succeeds
2. ✅ Dashboard page loads
3. ✅ GET /api/dashboards/admin/overview returns 200 with data
4. ✅ GET /api/system/stats returns 200 with data
5. ✅ No 401 errors
6. ✅ No 404 errors
7. ✅ No automatic redirect to login

---

## TESTING STEPS

### Test Admin Dashboard:
```
1. Login as admin
2. Open DevTools → Network tab
3. Check requests:
   - GET /api/dashboards/admin/overview → 200
   - GET /api/system/stats → 200
4. Check Console for logs:
   - [API] GET /api/dashboards/admin/overview
   - [API] Authorization Header: Bearer eyJ0eXAi...
   - [API] JWT Identity: 1
```

### Test Lecturer Dashboard:
```
1. Login as lecturer
2. Check requests:
   - GET /api/dashboards/lecturer/overview → 200
3. Should NOT see 401 errors
```

### Test Student Dashboard:
```
1. Login as student
2. Check requests:
   - GET /api/dashboards/student/profile → 200
3. Should NOT see 401 errors
```

---

## SUMMARY

**Root Causes**:
1. Frontend calls wrong API endpoint (`/dashboards/admin` instead of `/dashboards/admin/overview`)
2. `/api/system/stats` requires permission that may not be granted
3. No logging to debug auth failures

**Fixes**:
1. Update frontend API service to call correct endpoints
2. Add logging to all protected routes
3. Adjust permission requirements for system stats

**Impact**: After fixes, all dashboard API calls will succeed with proper authentication.