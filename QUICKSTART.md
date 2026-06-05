# Quick Start Guide - Smart Attendance System

## Prerequisites
- Python 3.8 or higher
- pip (Python package installer)
- Git (optional, for version control)

## Installation Steps

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

This will install all required packages including:
- Flask, Flask-SQLAlchemy, Flask-JWT-Extended
- Flask-Bcrypt, Flask-CORS, Flask-Migrate
- OpenCV, face-recognition, ultralytics (YOLO)
- And 20+ other dependencies

### 2. Create Environment File
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

Edit `.env` file with your values:
```env
# Minimum required:
SECRET_KEY=your-secret-key-here-change-this
DATABASE_URI=sqlite:///attendance.db
JWT_SECRET_KEY=your-jwt-secret-here-change-this
```

**⚠️ IMPORTANT:** Change the default secret keys!

### 3. Initialize Database
```bash
# Initialize Flask-Migrate
flask db init

# Create migration from models
flask db migrate -m "Initial schema with RBAC"

# Apply migration to database
flask db upgrade
```

### 4. Seed Initial Data
```bash
python seed_data.py
```

This creates:
- ✓ Admin user (username: `admin`, password: `Admin@123`)
- ✓ 4 sample departments (CS, EE, ME, BA)
- ✓ Academic year 2025-2026 and Semester 2
- ✓ Main campus with 3 buildings (A, B, C)
- ✓ 45 rooms (15 per building)

### 5. Run Application
```bash
python app.py
```

Application will start at: **http://localhost:5001**

## Quick Test

### 1. Check Health Endpoint
```bash
curl http://localhost:5001/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "smart-attendance"
}
```

### 2. Login as Admin
```bash
curl -X POST http://localhost:5001/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "Admin@123"
  }'
```

Expected response:
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "role": "admin",
    "user_type": "administrator",
    "name": "System Administrator",
    "email": "admin@attendance.edu"
  }
}
```

### 3. Access Protected Endpoint
```bash
# Replace YOUR_TOKEN with the access_token from login
curl http://localhost:5001/api/auth/me \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Web Interface

After running the application, you can access:

- **Landing Page:** http://localhost:5001/
- **Registration:** http://localhost:5001/register
- **Dashboard:** http://localhost:5001/dashboard
- **Live Attendance:** http://localhost:5001/attendance

## API Endpoints

### Authentication
- `POST /api/auth/login` - Login (admin/lecturer/student)
- `POST /api/auth/refresh` - Refresh access token
- `POST /api/auth/logout` - Logout (blacklist token)
- `POST /api/auth/register/student` - Student self-registration
- `GET /api/auth/me` - Get current user info
- `POST /api/auth/change-password` - Change password

### Users (requires authentication)
- `GET /api/users` - List users
- `POST /api/users` - Create user
- `GET /api/users/<id>` - Get user details
- `PUT /api/users/<id>` - Update user
- `DELETE /api/users/<id>` - Delete user (soft delete)

### Attendance
- `POST /api/recognize` - Face recognition attendance
- `GET /api/attendance` - Get attendance records
- `GET /api/attendance/student/<id>` - Student attendance history
- `POST /api/attendance/manual` - Manual attendance check-in

### Training
- `POST /api/training/register-face` - Register student face
- `POST /api/training/retrain` - Retrain recognition model

## Important Security Notes

### Change Default Credentials Immediately!
```bash
# After first login, change admin password via API:
curl -X POST http://localhost:5001/api/auth/change-password \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "current_password": "Admin@123",
    "new_password": "YourNewStrongPassword123!"
  }'
```

### Production Deployment Checklist
- [ ] Change `SECRET_KEY` and `JWT_SECRET_KEY` to random values
- [ ] Set `DEBUG=False` in production
- [ ] Use PostgreSQL instead of SQLite
- [ ] Set up Redis for rate limiting and token blacklist
- [ ] Configure proper CORS origins
- [ ] Use HTTPS
- [ ] Set up proper logging
- [ ] Configure email service (SMTP)
- [ ] Use environment-specific configs
- [ ] Set up gunicorn with supervisor/systemd
- [ ] Configure nginx as reverse proxy

## Project Structure

```
smart-attendance/
├── app.py                  # Main application (Flask factory)
├── models.py               # Database models (26 models)
├── config/                 # Configuration module
│   ├── settings.py        # Config class
│   └── permissions.py     # RBAC definitions
├── routes/                 # API blueprints
│   ├── auth.py            # Authentication endpoints
│   ├── users.py           # User management
│   ├── attendance.py      # Attendance endpoints
│   ├── recognition.py     # Face recognition
│   └── training.py        # Model training
├── middleware/             # Security middleware
│   ├── error_handlers.py  # Global error handling
│   └── rate_limit.py      # Rate limiting
├── utils/                  # Utility functions
│   ├── decorators.py      # Auth decorators
│   ├── validators.py      # Input validation
│   └── pagination.py      # Query pagination
├── face_utils.py          # Face recognition ML (ArcFace, YOLO)
├── antispoof_utils.py     # Anti-spoofing (MiniFASNet)
├── seed_data.py           # Database seeding script
└── migrations/            # Alembic migrations
```

## Troubleshooting

### Issue: ModuleNotFoundError
```bash
# Make sure all dependencies are installed
pip install -r requirements.txt
```

### Issue: Database not found
```bash
# Initialize and migrate database
flask db init
flask db migrate
flask db upgrade
```

### Issue: "Admin already exists" when seeding
This is normal if you've already run seed_data.py. The script checks for existing data.

### Issue: JWT decode error
Make sure `JWT_SECRET_KEY` in `.env` matches the one used to create tokens.

### Issue: Face recognition not working
```bash
# Download YOLO model (if not already present)
# The app will download yolov8n-face.pt on first run

# Check if antispoof models exist
ls antispoof_models/
# Should see: MiniFASNetV1SE.onnx, MiniFASNetV2.onnx
```

## Next Steps

1. **Change admin password** immediately
2. **Create test users** (lecturers and students)
3. **Register student faces** via `/api/training/register-face`
4. **Test face recognition** via `/api/recognize`
5. **Explore Phase 2-10 features** (see REFACTOR_PLAN.md)

## Support

For detailed implementation plan, see:
- `REFACTOR_PLAN.md` - Complete 10-phase refactor plan
- `PHASE1_PROGRESS.md` - Phase 1 progress report
- `IMPLEMENTATION_STATUS.md` - Current implementation status

## License

This project is for educational purposes.