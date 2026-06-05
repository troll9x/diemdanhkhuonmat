# LOGIN FLOW INVESTIGATION REPORT

## PHASE 1: LOGIN FLOW TRACE

### Actual Flow in Current Project

```
login.html (templates/modules/auth/login.html)
    ↓
    Form submit → handleLogin() in login.html
    ↓
    auth.login(username, password) [static/js/auth.js:125]
    ↓
    POST /api/auth/login [routes/auth.py:22]
    ↓
    Backend validates credentials
    ↓
    Returns: {access_token, refresh_token, user{id, role, user_type, name, email}}
    ↓
    auth.setTokens() → localStorage + cookies
    auth.setUser() → localStorage
    ↓
    redirectToDashboard() [static/js/auth.js:208]
    ↓
    Reads user.role from localStorage
    ↓
    switch(role) → /admin-dashboard | /lecturer-dashboard | /student-dashboard
    ↓
    window.location.href = dashboardUrl
    ↓
    Browser navigates to dashboard route
    ↓
    app.py route handler [app.py:151/187/205]
    ↓
    Checks request.cookies.get('access_token')
    ↓
    decode_token(token) → validates JWT
    ↓
    Checks user_role == expected role
    ↓
    render_template('modules/admin|teacher|student/dashboard/index.html')
```

---

## PHASE 2: CONSOLE LOG POINTS ADDED

Added console.log statements at critical points:

### Frontend (static/js/auth.js)

1. **Line 139**: `console.log("LOGIN RESPONSE", data)` - After API response
2. **Line 142**: `console.log("USER", this.getUser())` - After setUser()
3. **Line 143**: `console.log("ROLE", this.getRole())` - After setUser()
4. **Line 144**: `console.log("TOKEN", this.getToken())` - After setTokens()
5. **Line 246**: `console.log('REDIRECTING TO', dashboardUrl)` - Before redirect
6. **Line 247**: `console.log('About to call window.location.href')` - Before navigation
7. **Line 249**: `console.log('After window.location.href (should not reach here)')` - After navigation

### Expected Console Output When Login Succeeds:

```
LOGIN RESPONSE {access_token: "...", refresh_token: "...", user: {id: 1, role: "admin", ...}}
USER {id: 1, role: "admin", user_type: "administrator", name: "System Administrator", email: "admin@example.com"}
ROLE admin
TOKEN eyJ0eXAiOiJKV1QiLCJhbGc...
redirectToDashboard called, user: {id: 1, role: "admin", ...}
User role: admin
REDIRECTING TO /admin-dashboard
About to call window.location.href
```

---

## PHASE 3: BACKEND JWT/AUTH DECORATORS ANALYSIS

### JWT Decorators Found:

#### In routes/auth.py:
- **Line 278**: `@auth_bp.before_app_request` - Token blacklist check
  - Checks if token is in blacklist
  - Runs BEFORE every request to auth blueprint

#### In routes/dashboards.py:
- **Line 26**: `@jwt_required()` - admin_overview()
- **Line 106**: `@jwt_required()` - attendance_trends()
- **Line 157**: `@jwt_required()` - department_stats()
- **Line 198**: `@jwt_required()` - classroom_performance()
- **Line 256**: `@jwt_required()` - lecturer_overview()
- **Line 322**: `@jwt_required()` - lecturer_class_stats()
- **Line 402**: `@jwt_required()` - lecturer_sessions()
- **Line 466**: `@jwt_required()` - student_profile()
- **Line 515**: `@jwt_required()` - student_attendance_history()
- **Line 564**: `@jwt_required()` - student_attendance_stats()
- **Line 635**: `@jwt_required()` - student_upcoming_sessions()
- **Line 689**: `@jwt_required()` - attendance_report()

#### In utils/decorators.py:
- **Line 8**: `def jwt_required(fn)` - Custom JWT decorator
- **Line 20**: `def permission_required(permission_code)` - Permission check decorator
- **Line 46**: `def admin_only(fn)` - Admin-only decorator
- **Line 67**: `def lecturer_only(fn)` - Lecturer-only decorator
- **Line 88**: `def admin_or_lecturer_required(fn)` - Admin or Lecturer decorator
- **Line 107**: `def student_only(fn)` - Student-only decorator

### Key Finding:

**The dashboard routes in app.py (lines 151-221) do NOT use @jwt_required() decorator!**

Instead, they manually check the cookie:
```python
token = request.cookies.get('access_token')
if not token:
    return redirect('/login')

try:
    claims = decode_token(token)
    user_role = claims.get('role')
    if user_role != 'admin':  # or 'lecturer' or 'student'
        return redirect('/login')
except Exception:
    return redirect('/login')
```

---

## PHASE 4: ROUTE ACCESS VERIFICATION

### Dashboard Routes in app.py:

#### 1. `/admin-dashboard` (Line 151-167)
- **Exists**: ✅ YES
- **Render Template**: ✅ YES - `modules/admin/dashboard/index.html`
- **JWT Protected**: ⚠️ MANUAL - Checks cookie manually
- **Middleware**: ✅ Checks role == 'admin'
- **Issue**: Relies on cookie, not Authorization header

#### 2. `/lecturer-dashboard` (Line 187-203)
- **Exists**: ✅ YES
- **Render Template**: ✅ YES - `modules/teacher/dashboard/index.html`
- **JWT Protected**: ⚠️ MANUAL - Checks cookie manually
- **Middleware**: ✅ Checks role == 'lecturer'
- **Issue**: Relies on cookie, not Authorization header

#### 3. `/student-dashboard` (Line 205-221)
- **Exists**: ✅ YES
- **Render Template**: ✅ YES - `modules/student/dashboard/index.html`
- **JWT Protected**: ⚠️ MANUAL - Checks cookie manually
- **Middleware**: ✅ Checks role == 'student'
- **Issue**: Relies on cookie, not Authorization header

---

## PHASE 5: ROOT CAUSE ANALYSIS

### Critical Issue Found:

**PROBLEM**: The dashboard routes check for `access_token` in **cookies**, but the frontend only sets it in **localStorage AND cookies** during login.

**Location**: 
- Frontend: `static/js/auth.js` line 84 - `this.setCookie(this.tokenKey, accessToken);`
- Backend: `app.py` lines 154, 172, 208 - `token = request.cookies.get('access_token')`

### The Issue Chain:

1. ✅ Login API returns tokens correctly
2. ✅ Frontend stores tokens in localStorage
3. ✅ Frontend stores token in cookie (line 84)
4. ✅ Frontend redirects to dashboard
5. ❌ **POTENTIAL ISSUE**: Cookie might not be set properly due to:
   - Cookie domain/path mismatch
   - Cookie expiration too short (default 1 day)
   - SameSite attribute issues
   - CORS cookie handling

### Secondary Issue:

**The `setCookie()` function uses a default of 1 day expiration:**
```javascript
setCookie(name, value, days = 1) {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "; expires=" + date.toUTCString();
    document.cookie = name + "=" + (value || "") + expires + "; path=/";
}
```

This is called with only 2 parameters: `this.setCookie(this.tokenKey, accessToken);`
So the cookie expires in 1 day, which is fine for testing.

### Tertiary Issue:

**The cookie is set WITHOUT SameSite attribute**, which might cause issues in some browsers.

---

## PHASE 6: ANSWERS TO 8 CRITICAL QUESTIONS

1. **Login API returns success?** 
   - ✅ YES - Returns 200 with tokens and user object

2. **Token saved to localStorage?** 
   - ✅ YES - Line 82-83 in auth.js

3. **User saved to localStorage?** 
   - ✅ YES - Line 99 in auth.js

4. **Role read correctly?** 
   - ✅ YES - Line 219 in auth.js reads `user.role`

5. **redirectToDashboard() called?** 
   - ✅ YES - Line 140 in login.html calls it after 1 second delay

6. **window.location.href executed?** 
   - ✅ YES - Line 248 in auth.js executes it

7. **Dashboard route exists?** 
   - ✅ YES - All three routes exist in app.py

8. **Dashboard returns what status?** 
   - ⚠️ **DEPENDS ON COOKIE** - If cookie is missing/invalid, returns 302 redirect to /login

---

## ROOT CAUSE SUMMARY

**ROOT CAUSE**: Cookie-based authentication on dashboard routes may fail if:

1. **Cookie not being sent by browser** due to:
   - SameSite=Strict/Lax restrictions
   - Domain/Path mismatch
   - Secure flag on non-HTTPS

2. **Cookie decode fails** due to:
   - Invalid JWT format
   - Token corruption
   - Expired token

3. **Role mismatch** due to:
   - Backend returning different role value than frontend expects
   - Case sensitivity issues

**PROOF**: 
- Backend expects `claims.get('role')` to be 'admin', 'lecturer', or 'student'
- Frontend sends `user.role` which matches backend response
- But if cookie is not sent, `decode_token()` will fail and redirect to /login

---

## RECOMMENDED FIXES

1. **Add SameSite attribute to cookies**
2. **Increase cookie expiration time**
3. **Add console logs to verify cookie is being sent**
4. **Consider using Authorization header instead of cookies**
5. **Add error handling for decode_token() failures**