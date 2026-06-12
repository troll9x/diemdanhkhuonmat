"""
Routes Nhận Diện Khuôn Mặt (Face Recognition Routes)
Blueprint: recognition_bp — tiền tố URL: /api/recognition

Endpoints:
  POST /frame                          — Xử lý frame video để nhận diện khuôn mặt và điểm danh
                                         (yêu cầu JWT + quyền PERM_MARK_ATTENDANCE)
  GET  /session/<session_id>/attendance — Lấy danh sách điểm danh theo phiên (real-time)
  GET  /health                         — Kiểm tra trạng thái hệ thống nhận diện
                                         (mô hình SVM sẵn sàng chưa, số sinh viên đã đăng ký)

Pipeline nhận diện (process_frame):
  1. Validate session_id và trạng thái phiên học
  2. Kiểm tra mô hình FaceModel đang active
  3. Gọi identify_face(frame_bytes) → (student_id, confidence, is_spoof)
  4. Kiểm tra sinh viên đã đăng ký lớp (ClassroomStudent)
  5. Kiểm tra trùng lặp điểm danh trong cùng phiên
  6. Tạo bản ghi AttendanceRecord và commit DB
"""
from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from face_utils import identify_face
from models import (
    db, Student, AttendanceRecord, ClassSession, 
    FaceModel, FaceEmbedding
)
from utils.decorators import permission_required
from config.permissions import PERM_MARK_ATTENDANCE

recognition_bp = Blueprint('recognition', __name__)


@recognition_bp.route('/frame', methods=['POST'])
@jwt_required()
@permission_required(PERM_MARK_ATTENDANCE)
def process_frame():
    """
    Process a video frame for face recognition and mark attendance.
    
    Required parameters (JSON or form-data):
    - session_id: ID of the ClassSession to mark attendance for
    - frame: Image data (binary) in request body
    
    Returns recognition status and attendance marking result.
    """
    # Get session_id from query params or JSON
    session_id = request.args.get('session_id') or request.json.get('session_id') if request.json else None
    
    if not session_id:
        return jsonify({'error': 'session_id is required'}), 400
    
    # Validate session exists and is active
    session = ClassSession.query.get(session_id)
    if not session:
        return jsonify({'error': 'Class session not found'}), 404
    
    if session.status not in ['scheduled', 'ongoing']:
        return jsonify({'error': f'Cannot mark attendance for session with status: {session.status}'}), 400
    
    # Get active face recognition model
    active_model = FaceModel.query.filter_by(is_active=True).first()
    if not active_model:
        return jsonify({'error': 'No active face recognition model found. Please train a model first.'}), 400
    
    # Process the frame
    frame_data = request.data
    if not frame_data:
        return jsonify({'error': 'No image data provided'}), 400
    
    student_id, confidence, is_spoof = identify_face(frame_data)
    
    # Handle anti-spoofing detection
    if is_spoof:
        return jsonify({
            'status': 'spoof',
            'message': 'Presentation attack detected. Please use a real face.',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # Handle unknown face
    if student_id is None:
        return jsonify({
            'status': 'unknown',
            'message': 'Face not recognized. Please register first.',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # Verify student exists
    student = Student.query.get(student_id)
    if not student:
        return jsonify({
            'status': 'unknown',
            'message': 'Student record not found',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # Check if student is enrolled in this classroom
    from models import ClassroomStudent
    enrollment = ClassroomStudent.query.filter_by(
        classroom_id=session.classroom_id,
        student_id=student_id
    ).first()
    
    if not enrollment:
        return jsonify({
            'status': 'not_enrolled',
            'message': f'{student.full_name} is not enrolled in this class',
            'student_name': student.full_name,
            'student_code': student.student_code,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # Check for duplicate attendance (within the same session)
    existing_record = AttendanceRecord.query.filter_by(
        session_id=session_id,
        student_id=student_id
    ).first()
    
    if existing_record:
        return jsonify({
            'status': 'duplicate',
            'message': f'{student.full_name} has already been marked present',
            'student_name': student.full_name,
            'student_code': student.student_code,
            'check_in_time': existing_record.attendance_time.isoformat() if existing_record.attendance_time else None,
            'confidence': confidence,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    
    # Mark attendance
    attendance = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        attendance_time=datetime.utcnow(),
        status='present',
        confidence_score=confidence / 100.0,
        model_version_id=active_model.id
    )
    db.session.add(attendance)
    
    # Update session status to 'ongoing' if it was 'scheduled'
    if session.status == 'scheduled':
        session.status = 'ongoing'
    
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'message': f'Attendance marked for {student.full_name}',
        'student_name': student.full_name,
        'student_code': student.student_code,
        'department': student.department.name if student.department else None,
        'confidence': confidence,
        'check_in_time': attendance.attendance_time.strftime('%H:%M:%S'),
        'timestamp': datetime.utcnow().isoformat()
    }), 201


@recognition_bp.route('/session/<int:session_id>/attendance', methods=['GET'])
@jwt_required()
def get_session_attendance(session_id):
    """
    Get all attendance records for a specific session.
    Useful for real-time monitoring during class.
    """
    session = ClassSession.query.get_or_404(session_id)
    
    records = AttendanceRecord.query.filter_by(session_id=session_id).all()
    
    result = {
        'session_id': session.id,
        'session_date': session.session_date.isoformat(),
        'classroom': session.classroom.class_name if session.classroom else None,
        'subject': session.subject.subject_name if session.subject else None,
        'status': session.status,
        'total_present': len(records),
        'attendance': []
    }
    
    for record in records:
        result['attendance'].append({
            'id': record.id,
            'student_name': record.student.full_name if record.student else None,
            'student_code': record.student.student_code if record.student else None,
            'check_in_time': record.attendance_time.isoformat() if record.attendance_time else None,
            'confidence': round(record.confidence_score * 100, 1) if record.confidence_score else None,
            'status': record.status
        })
    
    return jsonify(result), 200


@recognition_bp.route('/health', methods=['GET'])
def recognition_health():
    """
    Check if face recognition system is ready.
    Returns model status and system readiness.
    """
    import os
    from face_utils import SVM_PATH
    
    active_model = FaceModel.query.filter_by(is_active=True).first()
    total_embeddings = FaceEmbedding.query.filter_by(is_active=True).count()
    enrolled_students = db.session.query(Student.id).join(
        FaceEmbedding, FaceEmbedding.student_id == Student.id
    ).filter(FaceEmbedding.is_active == True).distinct().count()
    
    return jsonify({
        'status': 'healthy' if active_model and os.path.exists(SVM_PATH) else 'not_ready',
        'model_ready': os.path.exists(SVM_PATH),
        'active_model': {
            'id': active_model.id,
            'version': active_model.version,
            'algorithm': active_model.algorithm,
            'trained_at': active_model.trained_at.isoformat()
        } if active_model else None,
        'enrolled_students': enrolled_students,
        'total_embeddings': total_embeddings,
        'message': 'System ready' if active_model and os.path.exists(SVM_PATH) else 'No trained model available'
    }), 200