"""
Routes Dashboard và Phân Tích (Dashboard & Analytics)
Blueprint: dashboards_bp — tiền tố URL: /api/dashboard

Cung cấp dữ liệu thống kê tổng quan cho các loại người dùng khác nhau.

Endpoints (tất cả yêu cầu JWT):
  GET /admin    — Thống kê admin: tổng SV, giảng viên, lớp học, tỉ lệ điểm danh, biểu đồ xu hướng
  GET /lecturer — Thống kê giảng viên: lớp đang dạy, điểm danh hôm nay, SV của mình
  GET /student  — Thống kê sinh viên: lớp đã đăng ký, lịch sử điểm danh, tỉ lệ có mặt
  GET /overview — Tổng quan hệ thống (admin only): trạng thái ML, database, server
"""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_

from models import (
    db, Student, Lecturer, Administrator, ClassroomStudent,
    AttendanceRecord, ClassSession, Classroom,
    Subject, Department, FaceEmbedding, FaceModel, ClassroomSubject,
    AppUser, AppClassroom, AppEnrollment, AttendanceSession, AppAttendanceRecord,
)
from utils.decorators import permission_required
from config.permissions import (
    PERM_VIEW_REPORTS, PERM_VIEW_ALL_REPORTS,
    PERM_MANAGE_MODELS
)

dashboards_bp = Blueprint('dashboards', __name__)


def _classroom_subjects(classroom_id):
    """Return active subjects assigned to a classroom through ClassroomSubject."""
    rows = ClassroomSubject.query.filter_by(classroom_id=classroom_id).all()
    return [
        row.subject for row in rows
        if row.subject and not row.subject.is_deleted and row.subject.is_active
    ]


def _first_subject_name(classroom_id):
    subjects = _classroom_subjects(classroom_id)
    return subjects[0].subject_name if subjects else None


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@dashboards_bp.route('/admin/overview', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_ALL_REPORTS)
def admin_overview():
    """
    Get overview statistics for admin dashboard.
    Returns key metrics and trends.
    """
    print("[API] GET /api/dashboards/admin/overview")
    print(f"[API] Authorization Header: {request.headers.get('Authorization')}")
    print(f"[API] JWT Identity: {get_jwt_identity()}")
    today = datetime.utcnow().date()
    start_of_week = today - timedelta(days=today.weekday())
    start_of_month = today.replace(day=1)
    
    # Total counts
    total_students = Student.query.filter_by(is_active=True).count()
    total_lecturers = Lecturer.query.filter_by(is_active=True).count()
    total_classrooms = Classroom.query.filter_by(is_active=True).count()
    total_subjects = Subject.query.filter_by(is_active=True).count()
    
    # Students with face registered
    students_with_face = db.session.query(Student.id).join(
        FaceEmbedding, FaceEmbedding.student_id == Student.id
    ).filter(
        FaceEmbedding.is_active == True,
        Student.is_active == True
    ).distinct().count()
    
    # Today's attendance
    today_attendance = AttendanceRecord.query.filter(
        func.date(AttendanceRecord.attendance_time) == today
    ).count()
    
    # This week's attendance
    week_attendance = AttendanceRecord.query.filter(
        func.date(AttendanceRecord.attendance_time) >= start_of_week
    ).count()
    
    # This month's attendance
    month_attendance = AttendanceRecord.query.filter(
        func.date(AttendanceRecord.attendance_time) >= start_of_month
    ).count()
    
    # Sessions stats
    today_sessions = ClassSession.query.filter(
        func.date(ClassSession.session_date) == today
    ).count()
    
    ongoing_sessions = ClassSession.query.filter(
        ClassSession.status == 'ongoing'
    ).count()
    
    # Active model info
    active_model = FaceModel.query.filter_by(is_active=True).first()
    
    return jsonify({
        'overview': {
            'total_students': total_students,
            'total_lecturers': total_lecturers,
            'total_classrooms': total_classrooms,
            'total_subjects': total_subjects,
            'students_with_face_registered': students_with_face,
            'face_registration_rate': round(students_with_face / total_students * 100, 1) if total_students > 0 else 0
        },
        'attendance_stats': {
            'today': today_attendance,
            'this_week': week_attendance,
            'this_month': month_attendance
        },
        'session_stats': {
            'today_sessions': today_sessions,
            'ongoing_sessions': ongoing_sessions
        },
        'model_info': {
            'active': active_model is not None,
            'version': active_model.version if active_model else None,
            'algorithm': active_model.algorithm if active_model else None,
            'trained_at': active_model.trained_at.isoformat() if active_model else None
        }
    }), 200


@dashboards_bp.route('/admin/attendance-trends', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_ALL_REPORTS)
def attendance_trends():
    """
    Get attendance trends over time.
    Query params: days (default 7), group_by (day/week/month)
    """
    days = request.args.get('days', 7, type=int)
    group_by = request.args.get('group_by', 'day')
    
    today = datetime.utcnow().date()
    start_date = today - timedelta(days=days-1)
    
    # Query attendance grouped by date
    if group_by == 'day':
        results = db.session.query(
            func.date(AttendanceRecord.attendance_time).label('date'),
            func.count(AttendanceRecord.id).label('count')
        ).filter(
            func.date(AttendanceRecord.attendance_time) >= start_date
        ).group_by(
            func.date(AttendanceRecord.attendance_time)
        ).order_by(
            func.date(AttendanceRecord.attendance_time)
        ).all()
        
        trend_data = [{'date': str(r.date), 'count': r.count} for r in results]
    else:
        # Weekly aggregation
        trend_data = []
        for i in range(0, days, 7):
            week_start = start_date + timedelta(days=i)
            week_end = min(week_start + timedelta(days=6), today)
            count = AttendanceRecord.query.filter(
                func.date(AttendanceRecord.attendance_time) >= week_start,
                func.date(AttendanceRecord.attendance_time) <= week_end
            ).count()
            trend_data.append({
                'week_start': str(week_start),
                'week_end': str(week_end),
                'count': count
            })
    
    return jsonify({
        'period': f'last_{days}_days',
        'group_by': group_by,
        'data': trend_data
    }), 200


@dashboards_bp.route('/admin/department-stats', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_ALL_REPORTS)
def department_stats():
    """
    Get attendance statistics by department.
    """
    departments = Department.query.filter_by(is_active=True).all()
    
    stats = []
    for dept in departments:
        # Count students in department
        student_count = Student.query.filter_by(
            department_id=dept.id,
            is_active=True
        ).count()
        
        # Count attendance for students in this department
        attendance_count = db.session.query(AttendanceRecord.id).join(
            Student, AttendanceRecord.student_id == Student.id
        ).filter(
            Student.department_id == dept.id
        ).count()
        
        stats.append({
            'department_id': dept.id,
            'department_name': dept.name,
            'student_count': student_count,
            'total_attendance': attendance_count,
            'avg_attendance_per_student': round(attendance_count / student_count, 1) if student_count > 0 else 0
        })
    
    # Sort by total attendance
    stats.sort(key=lambda x: x['total_attendance'], reverse=True)
    
    return jsonify({
        'total_departments': len(stats),
        'departments': stats
    }), 200


@dashboards_bp.route('/admin/classroom-performance', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_ALL_REPORTS)
def classroom_performance():
    """
    Get attendance performance by classroom.
    Query params: limit (default 10)
    """
    limit = request.args.get('limit', 10, type=int)
    
    classrooms = Classroom.query.filter_by(is_active=True).limit(limit).all()
    
    performance = []
    for classroom in classrooms:
        # Get all sessions for this classroom
        sessions = ClassSession.query.filter_by(classroom_id=classroom.id).all()
        session_ids = [s.id for s in sessions]
        
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status == 'completed'])
        
        # Get total students enrolled
        enrolled_students = db.session.query(func.count(ClassroomStudent.student_id)).filter(
            ClassroomStudent.classroom_id == classroom.id
        ).scalar() or 0
        
        # Get attendance records
        total_attendance = AttendanceRecord.query.filter(
            AttendanceRecord.session_id.in_(session_ids)
        ).count() if session_ids else 0
        
        # Calculate attendance rate
        expected_attendance = total_sessions * enrolled_students
        attendance_rate = round(total_attendance / expected_attendance * 100, 1) if expected_attendance > 0 else 0
        
        performance.append({
            'classroom_id': classroom.id,
            'classroom_name': classroom.class_name,
            'subject': _first_subject_name(classroom.id),
            'enrolled_students': enrolled_students,
            'total_sessions': total_sessions,
            'completed_sessions': completed_sessions,
            'total_attendance': total_attendance,
            'attendance_rate': attendance_rate
        })
    
    # Sort by attendance rate
    performance.sort(key=lambda x: x['attendance_rate'], reverse=True)
    
    return jsonify({
        'classrooms': performance
    }), 200


# ============================================================
# LECTURER DASHBOARD
# ============================================================

@dashboards_bp.route('/lecturer/overview', methods=['GET'])
@jwt_required()
def lecturer_overview():
    """
    Get overview for lecturer dashboard.
    Shows lecturer's assigned classes and upcoming sessions.
    Supports both new AppUser (role=teacher) and legacy Lecturer model.
    """
    current_user_id = get_jwt_identity()
    role = get_jwt().get('role')

    # New system: AppUser with role='teacher'
    if role == 'teacher':
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Lecturer not found'}), 404
        today = datetime.utcnow().date()
        classrooms = app_user.classrooms_owned.filter_by(is_active=True).all()
        today_sessions = AttendanceSession.query.filter(
            AttendanceSession.teacher_id == app_user.id,
            AttendanceSession.session_date == today,
        ).all()
        total_students = sum(c.enrollments.filter_by(is_active=True).count() for c in classrooms)
        return jsonify({
            'lecturer': {'id': app_user.id, 'full_name': app_user.full_name, 'email': app_user.email},
            'stats': {
                'assigned_classrooms': len(classrooms),
                'today_sessions': len(today_sessions),
                'total_students': total_students,
                'total_attendance': 0,
                'week_attendance': 0,
            },
            'classes': [{'id': c.id, 'class_code': c.class_code, 'name': c.name,
                         'student_count': c.enrollments.filter_by(is_active=True).count()} for c in classrooms],
            'today_sessions': [{'id': s.id, 'classroom_id': s.classroom_id,
                                 'session_type': s.session_type, 'status': s.status} for s in today_sessions],
        }), 200

    # Legacy system: Lecturer model
    lecturer = Lecturer.query.get(int(current_user_id))
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    today = datetime.utcnow().date()
    
    # Get assigned classrooms
    assigned_classrooms = Classroom.query.filter_by(
        lecturer_id=lecturer.id,
        is_active=True
    ).all()
    
    # Get upcoming sessions for today
    today_sessions = ClassSession.query.filter(
        ClassSession.classroom_id.in_([c.id for c in assigned_classrooms]),
        func.date(ClassSession.session_date) == today
    ).all()
    
    # Get attendance stats for lecturer's sessions
    session_ids = [s.id for s in ClassSession.query.filter(
        ClassSession.classroom_id.in_([c.id for c in assigned_classrooms])
    ).all()]
    
    total_attendance = AttendanceRecord.query.filter(
        AttendanceRecord.session_id.in_(session_ids)
    ).count() if session_ids else 0
    
    # This week's attendance
    start_of_week = today - timedelta(days=today.weekday())
    week_attendance = AttendanceRecord.query.filter(
        AttendanceRecord.session_id.in_(session_ids),
        func.date(AttendanceRecord.attendance_time) >= start_of_week
    ).count() if session_ids else 0
    
    # Build classes list with counts and subjects
    classes_list = []
    for c in assigned_classrooms:
        student_count = ClassroomStudent.query.filter_by(classroom_id=c.id).count()
        subjects = [
            {
                'id': subject.id,
                'subject_code': subject.subject_code,
                'subject_name': subject.subject_name,
                'credits': subject.credits,
            }
            for subject in _classroom_subjects(c.id)
        ]
        classes_list.append({
            'id': c.id,
            'class_code': c.class_code,
            'class_name': c.class_name,
            'code': c.class_code,
            'name': c.class_name,
            'is_active': c.is_active,
            'student_count': student_count,
            'subjects': subjects,
            'subject_name': subjects[0]['subject_name'] if subjects else '—',
        })

    return jsonify({
        'lecturer': {
            'id': lecturer.id,
            'full_name': lecturer.full_name,
            'email': lecturer.email
        },
        'stats': {
            'assigned_classrooms': len(assigned_classrooms),
            'today_sessions': len(today_sessions),
            'total_attendance': total_attendance,
            'week_attendance': week_attendance
        },
        'classes': classes_list,
        'today_sessions': [{
            'id': s.id,
            'classroom': s.classroom.class_name if s.classroom else None,
            'classroom_id': s.classroom_id,
            'subject': s.subject.subject_name if s.subject else None,
            'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
            'end_time': s.end_time.strftime('%H:%M') if s.end_time else None,
            'status': s.status
        } for s in today_sessions]
    }), 200


@dashboards_bp.route('/lecturer/class/<int:classroom_id>/stats', methods=['GET'])
@jwt_required()
def lecturer_class_stats(classroom_id):
    """
    Get attendance statistics for a specific class.
    """
    current_user_id = get_jwt_identity()
    lecturer = Lecturer.query.get(int(current_user_id))
    
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    # Verify lecturer owns this classroom
    classroom = Classroom.query.filter_by(
        id=classroom_id,
        lecturer_id=lecturer.id
    ).first()
    
    if not classroom:
        return jsonify({'error': 'Classroom not found or not assigned to you'}), 404
    
    # Get sessions for this classroom
    sessions = ClassSession.query.filter_by(classroom_id=classroom_id).all()
    session_ids = [s.id for s in sessions]
    
    # Get enrolled students
    enrolled_students = db.session.query(func.count(ClassroomStudent.student_id)).filter(
        ClassroomStudent.classroom_id == classroom_id
    ).scalar() or 0
    
    # Get attendance records
    attendance_records = AttendanceRecord.query.filter(
        AttendanceRecord.session_id.in_(session_ids)
    ).all() if session_ids else []
    
    # Group by student
    student_attendance = {}
    for record in attendance_records:
        if record.student_id not in student_attendance:
            student_attendance[record.student_id] = {
                'present': 0,
                'absent': 0,
                'late': 0
            }
        student_attendance[record.student_id][record.status] += 1
    
    # Calculate attendance rate per student
    student_stats = []
    for student_id, stats in student_attendance.items():
        total = stats['present'] + stats['absent'] + stats['late']
        rate = round(stats['present'] / total * 100, 1) if total > 0 else 0
        student_stats.append({
            'student_id': student_id,
            'student_name': Student.query.get(student_id).full_name if Student.query.get(student_id) else None,
            'student_code': Student.query.get(student_id).student_code if Student.query.get(student_id) else None,
            'present': stats['present'],
            'absent': stats['absent'],
            'late': stats['late'],
            'attendance_rate': rate
        })
    
    # Sort by attendance rate
    student_stats.sort(key=lambda x: x['attendance_rate'])
    
    return jsonify({
        'classroom': {
            'id': classroom.id,
            'name': classroom.class_name,
            'subject': _first_subject_name(classroom.id)
        },
        'stats': {
            'total_sessions': len(sessions),
            'enrolled_students': enrolled_students,
            'total_attendance': len(attendance_records),
            'avg_attendance_rate': round(len(attendance_records) / (len(sessions) * enrolled_students) * 100, 1) if sessions and enrolled_students > 0 else 0
        },
        'student_stats': student_stats
    }), 200


@dashboards_bp.route('/lecturer/sessions', methods=['GET'])
@jwt_required()
def lecturer_sessions():
    """
    Get list of sessions for lecturer's classes.
    Query params: status (scheduled/ongoing/completed), date_from, date_to
    Supports both new AppUser (role=teacher) and legacy Lecturer model.
    """
    current_user_id = get_jwt_identity()
    role = get_jwt().get('role')

    if role == 'teacher':
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Lecturer not found'}), 404
        query = AttendanceSession.query.filter_by(teacher_id=app_user.id)
        status = request.args.get('status')
        if status:
            query = query.filter(AttendanceSession.status == status)
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        if date_from:
            query = query.filter(AttendanceSession.session_date >= date_from)
        if date_to:
            query = query.filter(AttendanceSession.session_date <= date_to)
        sessions = query.order_by(AttendanceSession.session_date.desc()).all()
        return jsonify({'total': len(sessions), 'sessions': [{
            'id': s.id,
            'classroom_id': s.classroom_id,
            'classroom': s.classroom.name if s.classroom else None,
            'session_date': s.session_date.isoformat(),
            'session_type': s.session_type,
            'status': s.status,
            'attendance_count': s.records.count(),
        } for s in sessions]}), 200

    lecturer = Lecturer.query.get(int(current_user_id))
    if not lecturer:
        return jsonify({'error': 'Lecturer not found'}), 404
    
    # Get lecturer's classrooms
    classrooms = Classroom.query.filter_by(
        lecturer_id=lecturer.id,
        is_active=True
    ).all()
    
    query = ClassSession.query.filter(
        ClassSession.classroom_id.in_([c.id for c in classrooms])
    )
    
    # Filter by status
    status = request.args.get('status')
    if status:
        query = query.filter(ClassSession.status == status)
    
    # Filter by date range
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    if date_from:
        query = query.filter(ClassSession.session_date >= date_from)
    if date_to:
        query = query.filter(ClassSession.session_date <= date_to)
    
    sessions = query.order_by(ClassSession.session_date.desc()).all()
    
    result = []
    for session in sessions:
        # Get attendance count
        attendance_count = AttendanceRecord.query.filter_by(session_id=session.id).count()
        
        result.append({
            'id': session.id,
            'classroom_id': session.classroom_id,
            'subject_id': session.subject_id,
            'room_id': session.room_id,
            'classroom': session.classroom.class_name if session.classroom else None,
            'classroom_name': session.classroom.class_name if session.classroom else None,
            'subject': session.subject.subject_name if session.subject else None,
            'subject_name': session.subject.subject_name if session.subject else None,
            'room_name': session.room.name if session.room else None,
            'session_date': session.session_date.isoformat(),
            'start_time': session.start_time.strftime('%H:%M') if session.start_time else None,
            'end_time': session.end_time.strftime('%H:%M') if session.end_time else None,
            'status': session.status,
            'attendance_count': attendance_count
        })
    
    return jsonify({
        'total': len(result),
        'sessions': result
    }), 200


# ============================================================
# STUDENT DASHBOARD
# ============================================================

@dashboards_bp.route('/student/profile', methods=['GET'])
@jwt_required()
def student_profile():
    """
    Get student profile with face registration status.
    Supports both new AppUser (role=student) and legacy Student model.
    """
    current_user_id = get_jwt_identity()
    student = Student.query.get(int(current_user_id))

    if not student:
        # Fallback to new AppUser system
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Student not found'}), 404
        from models import AppFaceEmbedding, AppStudentProfile
        profile = app_user.student_profile
        face_count = AppFaceEmbedding.query.filter_by(user_id=app_user.id, is_active=True).count()
        classrooms = [e.classroom for e in app_user.enrollments.filter_by(is_active=True).all()]
        return jsonify({
            'student': {
                'id': app_user.id,
                'student_code': profile.student_code if profile else None,
                'full_name': app_user.full_name,
                'email': app_user.email,
                'phone': profile.phone if profile else None,
                'department': None, 'major': None,
            },
            'face_registration': {'registered': face_count > 0, 'embedding_count': face_count},
            'enrolled_classrooms': [{'id': c.id, 'code': c.class_code, 'name': c.name} for c in classrooms if c],
        }), 200
    
    # Get face registration status
    face_embeddings = FaceEmbedding.query.filter_by(
        student_id=student.id,
        is_active=True
    ).count()
    
    # Get enrolled classrooms
    enrolled_classrooms = db.session.query(Classroom).join(
        ClassroomStudent, ClassroomStudent.classroom_id == Classroom.id
    ).filter(
        ClassroomStudent.student_id == student.id,
        Classroom.is_active == True
    ).all()
    
    return jsonify({
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name,
            'email': student.email,
            'phone': student.phone,
            'department': student.department.name if student.department else None,
            'major': student.major.name if student.major else None
        },
        'face_registration': {
            'registered': face_embeddings > 0,
            'embedding_count': face_embeddings
        },
        'enrolled_classrooms': [{
            'id': c.id,
            'code': c.class_code,
            'name': c.class_name,
            'lecturer': c.lecturer.full_name if c.lecturer else None
        } for c in enrolled_classrooms]
    }), 200


@dashboards_bp.route('/student/attendance-history', methods=['GET'])
@jwt_required()
def student_attendance_history():
    """
    Get attendance history for current student.
    Query params: limit (default 30), classroom_id (optional)
    Supports both new AppUser (role=student) and legacy Student model.
    """
    current_user_id = get_jwt_identity()
    student = Student.query.get(int(current_user_id))

    if not student:
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Student not found'}), 404
        limit = request.args.get('limit', 30, type=int)
        records = (AppAttendanceRecord.query.filter_by(student_id=app_user.id)
                   .order_by(AppAttendanceRecord.checkin_time.desc()).limit(limit).all())
        SESSION_LABEL = {'start': 'Dau gio', 'end': 'Cuoi gio'}
        history = [{
            'id': r.id,
            'session_date': r.session.session_date.isoformat() if r.session else None,
            'classroom': r.classroom_ref.name if r.classroom_ref else None,
            'subject': None,
            'check_in_time': r.checkin_time.isoformat() if r.checkin_time else None,
            'status': r.status,
            'is_late': r.is_late,
            'confidence': round(r.face_confidence * 100, 1) if r.face_confidence else None,
        } for r in records]
        return jsonify({
            'student': {'id': app_user.id, 'student_code': None, 'full_name': app_user.full_name},
            'total_records': len(history), 'history': history,
        }), 200
    
    limit = request.args.get('limit', 30, type=int)
    classroom_id = request.args.get('classroom_id', type=int)
    
    query = AttendanceRecord.query.filter_by(student_id=student.id)
    
    if classroom_id:
        # Get sessions for this classroom
        session_ids = [s.id for s in ClassSession.query.filter_by(classroom_id=classroom_id).all()]
        query = query.filter(AttendanceRecord.session_id.in_(session_ids))
    
    records = query.order_by(AttendanceRecord.attendance_time.desc()).limit(limit).all()
    
    history = []
    for record in records:
        session = ClassSession.query.get(record.session_id)
        history.append({
            'id': record.id,
            'session_date': session.session_date.isoformat() if session else None,
            'classroom': session.classroom.class_name if session and session.classroom else None,
            'subject': session.subject.subject_name if session and session.subject else None,
            'check_in_time': record.attendance_time.isoformat() if record.attendance_time else None,
            'status': record.status,
            'confidence': round(record.confidence_score * 100, 1) if record.confidence_score else None
        })
    
    return jsonify({
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name
        },
        'total_records': len(history),
        'history': history
    }), 200


@dashboards_bp.route('/student/attendance-stats', methods=['GET'])
@jwt_required()
def student_attendance_stats():
    """
    Get attendance statistics for current student.
    Supports both new AppUser (role=student) and legacy Student model.
    """
    current_user_id = get_jwt_identity()
    student = Student.query.get(int(current_user_id))

    if not student:
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Student not found'}), 404
        records = AppAttendanceRecord.query.filter_by(student_id=app_user.id).all()
        total = len(records)
        present = sum(1 for r in records if r.status == 'present' and not r.is_late)
        late = sum(1 for r in records if r.status == 'present' and r.is_late)
        rejected = sum(1 for r in records if r.status == 'rejected')
        rate = round((present + late) / total * 100, 1) if total > 0 else 0
        return jsonify({
            'student': {'id': app_user.id, 'student_code': None, 'full_name': app_user.full_name},
            'overall_stats': {
                'total_records': total, 'present': present, 'late': late,
                'absent': 0, 'excused': 0, 'rejected': rejected,
                'attendance_rate': rate, 'punctuality_rate': 0,
            },
            'by_classroom': [],
        }), 200
    
    # Get all attendance records for this student
    records = AttendanceRecord.query.filter_by(student_id=student.id).all()
    
    total_present = len([r for r in records if r.status == 'present'])
    total_late = len([r for r in records if r.status == 'late'])
    total_absent = len([r for r in records if r.status == 'absent'])
    total_excused = len([r for r in records if r.status == 'excused'])
    total_records = len(records)
    
    # Calculate rates
    attendance_rate = round((total_present + total_late) / total_records * 100, 1) if total_records > 0 else 0
    punctuality_rate = round(total_present / (total_present + total_late) * 100, 1) if (total_present + total_late) > 0 else 0
    
    # Stats by classroom
    classroom_stats = []
    enrolled_classrooms = db.session.query(Classroom).join(
        ClassroomStudent, ClassroomStudent.classroom_id == Classroom.id
    ).filter(
        ClassroomStudent.student_id == student.id
    ).all()
    
    for classroom in enrolled_classrooms:
        session_ids = [s.id for s in ClassSession.query.filter_by(classroom_id=classroom.id).all()]
        classroom_records = [r for r in records if r.session_id in session_ids]
        
        present = len([r for r in classroom_records if r.status == 'present'])
        late = len([r for r in classroom_records if r.status == 'late'])
        total = len(classroom_records)
        
        classroom_stats.append({
            'classroom_id': classroom.id,
            'classroom_name': classroom.class_name,
            'subject': None,
            'total_sessions': len(session_ids),
            'attended': total,
            'present': present,
            'late': late,
            'attendance_rate': round((present + late) / total * 100, 1) if total > 0 else 0
        })
    
    return jsonify({
        'student': {
            'id': student.id,
            'student_code': student.student_code,
            'full_name': student.full_name
        },
        'overall_stats': {
            'total_records': total_records,
            'present': total_present,
            'late': total_late,
            'absent': total_absent,
            'excused': total_excused,
            'attendance_rate': attendance_rate,
            'punctuality_rate': punctuality_rate
        },
        'by_classroom': classroom_stats
    }), 200


@dashboards_bp.route('/student/upcoming-sessions', methods=['GET'])
@jwt_required()
def student_upcoming_sessions():
    """
    Get upcoming sessions for current student.
    Supports both new AppUser (role=student) and legacy Student model.
    """
    current_user_id = get_jwt_identity()
    student = Student.query.get(int(current_user_id))

    if not student:
        app_user = AppUser.query.get(int(current_user_id))
        if not app_user:
            return jsonify({'error': 'Student not found'}), 404
        today = datetime.utcnow().date()
        enrolled_ids = [e.classroom_id for e in app_user.enrollments.filter_by(is_active=True).all()]
        sessions = (AttendanceSession.query
                    .filter(AttendanceSession.classroom_id.in_(enrolled_ids),
                            AttendanceSession.session_date >= today,
                            AttendanceSession.status == 'open')
                    .order_by(AttendanceSession.session_date)
                    .limit(10).all()) if enrolled_ids else []
        return jsonify({'upcoming_sessions': [{
            'id': s.id,
            'classroom': s.classroom.name if s.classroom else None,
            'subject': None,
            'session_date': s.session_date.isoformat(),
            'session_type': s.session_type,
            'status': s.status,
            'already_attended': AppAttendanceRecord.query.filter_by(
                session_id=s.id, student_id=app_user.id).first() is not None,
        } for s in sessions]}), 200
    
    today = datetime.utcnow().date()
    
    # Get student's enrolled classrooms
    enrolled_classroom_ids = [cs.classroom_id for cs in db.session.query(ClassroomStudent).filter(
        ClassroomStudent.student_id == student.id
    ).all()]
    
    # Get upcoming sessions
    sessions = ClassSession.query.filter(
        ClassSession.classroom_id.in_(enrolled_classroom_ids),
        ClassSession.session_date >= today,
        ClassSession.status.in_(['scheduled', 'ongoing'])
    ).order_by(ClassSession.session_date, ClassSession.start_time).limit(10).all()
    
    result = []
    for session in sessions:
        # Check if already attended
        already_attended = AttendanceRecord.query.filter_by(
            session_id=session.id,
            student_id=student.id
        ).first() is not None
        
        result.append({
            'id': session.id,
            'classroom': session.classroom.class_name if session.classroom else None,
            'subject': session.subject.subject_name if session.subject else None,
            'session_date': session.session_date.isoformat(),
            'start_time': session.start_time.strftime('%H:%M') if session.start_time else None,
            'end_time': session.end_time.strftime('%H:%M') if session.end_time else None,
            'status': session.status,
            'already_attended': already_attended
        })
    
    return jsonify({
        'upcoming_sessions': result
    }), 200


# ============================================================
# SHARED ANALYTICS
# ============================================================

@dashboards_bp.route('/attendance-report', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_REPORTS)
def attendance_report():
    """
    Generate attendance report with filters.
    Query params: 
    - classroom_id, student_id, subject_id, department_id
    - date_from, date_to
    - status (present/late/absent/excused)
    """
    classroom_id = request.args.get('classroom_id', type=int)
    student_id = request.args.get('student_id', type=int)
    subject_id = request.args.get('subject_id', type=int)
    department_id = request.args.get('department_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')
    status = request.args.get('status')
    
    query = AttendanceRecord.query
    
    if classroom_id:
        session_ids = [s.id for s in ClassSession.query.filter_by(classroom_id=classroom_id).all()]
        query = query.filter(AttendanceRecord.session_id.in_(session_ids))
    
    if student_id:
        query = query.filter(AttendanceRecord.student_id == student_id)
    
    if date_from:
        query = query.filter(func.date(AttendanceRecord.attendance_time) >= date_from)
    
    if date_to:
        query = query.filter(func.date(AttendanceRecord.attendance_time) <= date_to)
    
    if status:
        query = query.filter(AttendanceRecord.status == status)
    
    records = query.order_by(AttendanceRecord.attendance_time.desc()).all()
    
    # Build report
    report = []
    for record in records:
        session = ClassSession.query.get(record.session_id)
        student = Student.query.get(record.student_id)
        
        if department_id and student and student.department_id != department_id:
            continue
        
        if subject_id and session and session.subject_id != subject_id:
            continue
        
        report.append({
            'id': record.id,
            'student_code': student.student_code if student else None,
            'student_name': student.full_name if student else None,
            'classroom': session.classroom.class_name if session and session.classroom else None,
            'subject': session.subject.subject_name if session and session.subject else None,
            'session_date': session.session_date.isoformat() if session else None,
            'check_in_time': record.attendance_time.isoformat() if record.attendance_time else None,
            'status': record.status,
            'confidence': round(record.confidence_score * 100, 1) if record.confidence_score else None
        })
    
    # Summary
    summary = {
        'total_records': len(report),
        'present': len([r for r in report if r['status'] == 'present']),
        'late': len([r for r in report if r['status'] == 'late']),
        'absent': len([r for r in report if r['status'] == 'absent']),
        'excused': len([r for r in report if r['status'] == 'excused'])
    }
    
    return jsonify({
        'filters': {
            'classroom_id': classroom_id,
            'student_id': student_id,
            'subject_id': subject_id,
            'department_id': department_id,
            'date_from': date_from,
            'date_to': date_to,
            'status': status
        },
        'summary': summary,
        'records': report
    }), 200
