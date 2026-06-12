"""
Routes Quản Lý Phiên Học (Class Session Management)
Blueprint: class_sessions_bp — tiền tố URL: /api/class-sessions

Phiên học là một buổi dạy cụ thể (ngày, giờ, phòng, giảng viên).
Trạng thái: scheduled → ongoing → completed / cancelled.

Endpoints (tất cả yêu cầu JWT):
  GET    /           — Danh sách phiên học có phân trang, lọc nhiều chiều
  POST   /           — Tạo phiên học mới (hoặc tạo hàng loạt theo lịch)
  GET    /<id>       — Chi tiết phiên học
  PUT    /<id>       — Cập nhật thông tin phiên học
  DELETE /<id>       — Xóa phiên học
  POST   /<id>/start — Bắt đầu phiên (chuyển sang ongoing)
  POST   /<id>/end   — Kết thúc phiên (chuyển sang completed)
"""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, date, timedelta

from models import (
    db, ClassSchedule, ClassSession, Classroom, Subject, Room,
    ClassroomStudent, AttendanceRecord, Notification, Student
)
from utils.decorators import permission_required
from config.permissions import (
    PERM_VIEW_CLASS_SCHEDULES,
    PERM_MANAGE_SESSIONS,
    PERM_MANAGE_OWN_SESSIONS
)

class_sessions_bp = Blueprint('class_sessions', __name__)


def _session_dict(session):
    return {
        "id": session.id,
        "session_date": session.session_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "status": session.status,
        "notes": session.notes,
        "classroom_id": session.classroom_id,
        "classroom_name": session.classroom.class_name if session.classroom else None,
        "lecturer_id": session.classroom.lecturer_id if session.classroom else None,
        "lecturer_name": session.classroom.lecturer.full_name if session.classroom and session.classroom.lecturer else None,
        "subject_id": session.subject_id,
        "subject_name": session.subject.subject_name if session.subject else None,
        "room_id": session.room_id,
        "room_name": session.room.name if session.room else None,
    }


def _parse_time(value, field):
    try:
        return datetime.strptime(value, '%H:%M').time() if len(value) == 5 else datetime.strptime(value, '%H:%M:%S').time()
    except Exception:
        raise ValueError(f"Invalid {field} format. Use HH:MM or HH:MM:SS")


@class_sessions_bp.route('', methods=['GET'])
@class_sessions_bp.route('/', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_CLASS_SCHEDULES) # Using schedule view perm for sessions too
def get_class_sessions():
    """Retrieve all class sessions."""
    query = ClassSession.query

    classroom_id = request.args.get('classroom_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    lecturer_id = request.args.get('lecturer_id', type=int)
    status = request.args.get('status')
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if classroom_id:
        query = query.filter(ClassSession.classroom_id == classroom_id)
    if subject_id:
        query = query.filter(ClassSession.subject_id == subject_id)
    if lecturer_id:
        query = query.join(Classroom, ClassSession.classroom_id == Classroom.id).filter(Classroom.lecturer_id == lecturer_id)
    if status:
        query = query.filter(ClassSession.status == status)
    if date_from:
        query = query.filter(ClassSession.session_date >= date.fromisoformat(date_from))
    if date_to:
        query = query.filter(ClassSession.session_date <= date.fromisoformat(date_to))

    sessions = query.order_by(ClassSession.session_date.asc(), ClassSession.start_time.asc()).all()
    return jsonify([_session_dict(s) for s in sessions]), 200


@class_sessions_bp.route('', methods=['POST'])
@class_sessions_bp.route('/', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_SESSIONS)
def create_class_session():
    """Create one concrete class session."""
    data = request.get_json() or {}
    required = ['session_date', 'classroom_id', 'subject_id', 'start_time', 'end_time']
    missing = [field for field in required if not data.get(field)]
    if missing:
        return jsonify({'error': f'Missing required fields: {", ".join(missing)}'}), 400

    classroom = Classroom.query.get(data['classroom_id'])
    if not classroom:
        return jsonify({'error': 'Classroom not found'}), 404
    if not Subject.query.get(data['subject_id']):
        return jsonify({'error': 'Subject not found'}), 404
    room_id = data.get('room_id')
    if room_id and not Room.query.get(room_id):
        return jsonify({'error': 'Room not found'}), 404

    try:
        session_date = date.fromisoformat(data['session_date'])
        start_time = _parse_time(data['start_time'], 'start_time')
        end_time = _parse_time(data['end_time'], 'end_time')
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    if start_time >= end_time:
        return jsonify({'error': 'start_time must be before end_time'}), 400

    session = ClassSession(
        session_date=session_date,
        start_time=start_time,
        end_time=end_time,
        classroom_id=classroom.id,
        subject_id=data['subject_id'],
        room_id=room_id,
        status=data.get('status', 'scheduled'),
        notes=data.get('notes')
    )
    db.session.add(session)
    db.session.commit()
    return jsonify({'message': 'Class session created successfully', 'session': _session_dict(session)}), 201

@class_sessions_bp.route('/today', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_CLASS_SCHEDULES)
def get_today_sessions():
    """Retrieve sessions for the current date."""
    today = date.today()
    sessions = ClassSession.query.filter_by(session_date=today).all()
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "status": s.status,
            "classroom_name": s.classroom.class_name if s.classroom else None,
            "subject_name": s.subject.subject_name if s.subject else None,
            "room_name": s.room.name if s.room else None,
        })
    return jsonify(result), 200

@class_sessions_bp.route('/generate', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_SESSIONS)
def generate_sessions():
    """
    Automatically generate class sessions based on active schedules.
    Expects JSON: {"start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD"}
    """
    data = request.get_json()
    start_date_str = data.get('start_date')
    end_date_str = data.get('end_date')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Missing start_date or end_date"}), 400

    try:
        start_date = date.fromisoformat(start_date_str)
        end_date = date.fromisoformat(end_date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    if start_date > end_date:
        return jsonify({"error": "start_date must be before end_date"}), 400

    # Get all active schedules
    schedules = ClassSchedule.query.filter_by(is_active=True).all()
    if not schedules:
        return jsonify({"message": "No active schedules found to generate sessions from"}), 200

    sessions_created = 0
    current_date = start_date
    
    while current_date <= end_date:
        # day_of_week in ClassSchedule: 1=Monday, 7=Sunday
        # date.weekday() returns 0=Monday, 6=Sunday
        day_of_week = current_date.weekday() + 1
        
        for sched in schedules:
            if sched.day_of_week == day_of_week:
                # Check if session already exists for this schedule on this date
                exists = ClassSession.query.filter_by(
                    session_date=current_date,
                    classroom_id=sched.classroom_id,
                    subject_id=sched.subject_id,
                    start_time=sched.start_time
                ).first()
                
                if not exists:
                    new_session = ClassSession(
                        session_date=current_date,
                        start_time=sched.start_time,
                        end_time=sched.end_time,
                        classroom_id=sched.classroom_id,
                        subject_id=sched.subject_id,
                        room_id=sched.room_id,
                        status='scheduled'
                    )
                    db.session.add(new_session)
                    sessions_created += 1
        
        current_date += timedelta(days=1)

    db.session.commit()
    return jsonify({
        "message": f"Successfully generated {sessions_created} class sessions",
        "count": sessions_created
    }), 201

@class_sessions_bp.route('/<int:session_id>', methods=['GET'])
def get_class_session(session_id):
    """Get a single class session by ID. Public endpoint for check-in page."""
    session = ClassSession.query.get_or_404(session_id)
    return jsonify(_session_dict(session)), 200


@class_sessions_bp.route('/<int:session_id>', methods=['PUT'])
@jwt_required()
@permission_required(PERM_MANAGE_SESSIONS)
def update_class_session(session_id):
    """Update a class session (e.g., change status, notes)."""
    session = ClassSession.query.get_or_404(session_id)
    data = request.get_json()

    if 'status' in data:
        valid_statuses = ['scheduled', 'ongoing', 'completed', 'cancelled']
        if data['status'] not in valid_statuses:
            return jsonify({"error": f"Invalid status. Must be one of {valid_statuses}"}), 400
        session.status = data['status']
    
    if 'notes' in data:
        session.notes = data['notes']

    if 'session_date' in data:
        try:
            session.session_date = date.fromisoformat(data['session_date'])
        except ValueError:
            return jsonify({"error": "Invalid session_date format. Use YYYY-MM-DD"}), 400

    if 'start_time' in data:
        try:
            session.start_time = _parse_time(data['start_time'], 'start_time')
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    if 'end_time' in data:
        try:
            session.end_time = _parse_time(data['end_time'], 'end_time')
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    if 'classroom_id' in data:
        classroom_id = data['classroom_id']
        if not Classroom.query.get(classroom_id):
            return jsonify({"error": "Classroom not found"}), 404
        session.classroom_id = classroom_id

    if 'subject_id' in data:
        subject_id = data['subject_id']
        if not Subject.query.get(subject_id):
            return jsonify({"error": "Subject not found"}), 404
        session.subject_id = subject_id
    
    if 'room_id' in data:
        room_id = data['room_id']
        if room_id and not Room.query.get(room_id):
            return jsonify({"error": "Room not found"}), 404
        session.room_id = room_id

    if session.start_time >= session.end_time:
        return jsonify({"error": "start_time must be before end_time"}), 400

    db.session.commit()
    return jsonify({"message": "Class session updated successfully", "session": _session_dict(session)}), 200

@class_sessions_bp.route('/<int:session_id>', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_MANAGE_SESSIONS)
def delete_class_session(session_id):
    """Delete a class session."""
    session = ClassSession.query.get_or_404(session_id)
    db.session.delete(session)
    db.session.commit()
    return jsonify({"message": "Class session deleted successfully"}), 200


# ── Attendance workflow ───────────────────────────────────────────────────────

@class_sessions_bp.route('/<int:session_id>/start', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_OWN_SESSIONS)
def start_attendance(session_id):
    """
    Open attendance for a session.
    - Sets status → ongoing
    - Sends in-app notification to every enrolled student
    - Returns the QR check-in URL
    """
    session = ClassSession.query.get_or_404(session_id)

    # Lecturers may only start attendance for their own classes
    role = get_jwt().get('role')
    if role == 'lecturer':
        classroom = Classroom.query.get(session.classroom_id)
        if not classroom or classroom.lecturer_id != int(get_jwt_identity()):
            return jsonify({'error': 'Bạn không có quyền mở điểm danh lớp này'}), 403

    if session.status == 'completed':
        return jsonify({'error': 'Session already completed'}), 400
    if session.status == 'cancelled':
        return jsonify({'error': 'Session is cancelled'}), 400

    session.status = 'ongoing'
    db.session.flush()

    # Notify enrolled students
    classroom_id = session.classroom_id
    subject_name = session.subject.subject_name if session.subject else 'Buổi học'
    class_name   = session.classroom.class_name  if session.classroom else ''

    enrollments = ClassroomStudent.query.filter_by(classroom_id=classroom_id).all()
    notified = 0
    for enr in enrollments:
        student = Student.query.get(enr.student_id)
        if student and student.is_active and not student.is_deleted:
            notif = Notification(
                user_id=student.id,
                user_type='student',
                title='Điểm danh đã mở',
                message=(
                    f'Buổi học {subject_name} – Lớp {class_name} đã bắt đầu. '
                    f'Hãy quét mã QR để điểm danh.'
                ),
                notification_type='info',
            )
            db.session.add(notif)
            notified += 1

    db.session.commit()

    checkin_url = f'/attendance/checkin/{session_id}'
    return jsonify({
        'message': 'Điểm danh đã được mở',
        'session_id': session_id,
        'status': 'ongoing',
        'checkin_url': checkin_url,
        'students_notified': notified,
    }), 200


@class_sessions_bp.route('/<int:session_id>/end', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_OWN_SESSIONS)
def end_attendance(session_id):
    """Close attendance — sets status → completed."""
    session = ClassSession.query.get_or_404(session_id)

    # Lecturers may only end attendance for their own classes
    role = get_jwt().get('role')
    if role == 'lecturer':
        classroom = Classroom.query.get(session.classroom_id)
        if not classroom or classroom.lecturer_id != int(get_jwt_identity()):
            return jsonify({'error': 'Bạn không có quyền đóng điểm danh lớp này'}), 403

    if session.status not in ('scheduled', 'ongoing'):
        return jsonify({'error': f'Cannot end session with status: {session.status}'}), 400

    session.status = 'completed'
    db.session.commit()

    # Count how many attended
    present = AttendanceRecord.query.filter_by(session_id=session_id).count()
    total   = ClassroomStudent.query.filter_by(classroom_id=session.classroom_id).count()

    return jsonify({
        'message': 'Điểm danh đã được đóng',
        'session_id': session_id,
        'status': 'completed',
        'present': present,
        'total_enrolled': total,
        'absent': max(0, total - present),
    }), 200


@class_sessions_bp.route('/<int:session_id>/live-stats', methods=['GET'])
@jwt_required()
def live_attendance_stats(session_id):
    """
    Live attendance statistics for a running session.
    Polled every 5 seconds by the teacher's Start Attendance page.
    """
    session = ClassSession.query.get_or_404(session_id)

    total_enrolled = ClassroomStudent.query.filter_by(
        classroom_id=session.classroom_id
    ).count()

    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    present = sum(1 for r in records if r.status in ('present', 'late'))
    late    = sum(1 for r in records if r.status == 'late')
    absent  = max(0, total_enrolled - present)

    student_list = []
    for rec in records:
        student = Student.query.get(rec.student_id)
        student_list.append({
            'student_code': student.student_code if student else '—',
            'full_name':    student.full_name    if student else '—',
            'status':       rec.status,
            'attendance_time': rec.attendance_time.strftime('%H:%M:%S') if rec.attendance_time else None,
            'confidence':  round(rec.confidence_score * 100, 1) if rec.confidence_score else None,
        })

    return jsonify({
        'session_id':    session_id,
        'status':        session.status,
        'total_enrolled': total_enrolled,
        'present':       present,
        'late':          late,
        'absent':        absent,
        'rate':          round(present / total_enrolled * 100, 1) if total_enrolled else 0,
        'records':       student_list,
    }), 200
