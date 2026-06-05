"""Public student check-in endpoint for QR-based face attendance."""
from datetime import datetime
from flask import Blueprint, jsonify, request

from models import db, Student, AttendanceRecord, ClassSession, FaceModel, ClassroomStudent

checkin_bp = Blueprint('checkin', __name__)


@checkin_bp.route('/api/checkin', methods=['POST'])
def student_checkin():
    """
    Public check-in for QR attendance.
    Accepts multipart/form-data: image, session_id, student_code.
    No JWT required — students scan QR and check in without logging in.
    """
    session_id = request.form.get('session_id')
    student_code = (request.form.get('student_code') or '').strip()
    image_file = request.files.get('image')

    if not session_id:
        return jsonify({'status': 'error', 'message': 'session_id là bắt buộc'}), 400
    if not student_code:
        return jsonify({'status': 'error', 'message': 'Vui lòng nhập mã số sinh viên'}), 400
    if not image_file:
        return jsonify({'status': 'error', 'message': 'Không có ảnh được gửi'}), 400

    # Find student
    student = Student.query.filter_by(student_code=student_code, is_active=True, is_deleted=False).first()
    if not student:
        return jsonify({'status': 'error', 'message': 'Không tìm thấy sinh viên với mã này'}), 404

    # Validate session
    session = ClassSession.query.get(int(session_id))
    if not session:
        return jsonify({'status': 'session_not_found', 'message': 'Buổi học không tồn tại'}), 404

    if session.status != 'ongoing':
        labels = {'completed': 'đã kết thúc', 'cancelled': 'đã hủy'}
        label = labels.get(session.status, session.status)
        return jsonify({'status': 'session_closed', 'message': f'Buổi học {label}, không thể điểm danh'}), 400

    # Check enrollment
    enrolled = ClassroomStudent.query.filter_by(
        classroom_id=session.classroom_id,
        student_id=student.id
    ).first()
    if not enrolled:
        return jsonify({'status': 'not_enrolled', 'message': 'Sinh viên chưa đăng ký lớp này'}), 400

    # Check duplicate
    existing = AttendanceRecord.query.filter_by(
        session_id=int(session_id),
        student_id=student.id
    ).first()
    if existing:
        return jsonify({
            'status': 'already_checked_in',
            'message': 'Bạn đã điểm danh buổi học này rồi',
            'attendance_time': existing.attendance_time.strftime('%H:%M:%S') if existing.attendance_time else None
        }), 200

    # Attempt face recognition
    active_model = FaceModel.query.filter_by(is_active=True).first()
    image_data = image_file.read()

    if not active_model:
        # No model trained yet — accept check-in by student code only
        record = AttendanceRecord(
            session_id=int(session_id),
            student_id=student.id,
            attendance_time=datetime.utcnow(),
            status='present',
            ip_address=request.remote_addr,
            user_agent=(request.headers.get('User-Agent') or '')[:255]
        )
        db.session.add(record)
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Điểm danh thành công (bằng mã SV — chưa có mô hình nhận diện)',
            'student_name': student.full_name,
            'student_code': student.student_code,
            'attendance_time': record.attendance_time.strftime('%H:%M:%S'),
            'confidence': None
        }), 201

    # Run recognition
    try:
        from face_utils import identify_face
        recognized_id, confidence, is_spoof = identify_face(image_data)
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Lỗi nhận diện: {str(e)}'}), 500

    if is_spoof:
        return jsonify({'status': 'spoof', 'message': 'Phát hiện ảnh giả mạo. Vui lòng dùng khuôn mặt thật'}), 200

    if recognized_id is None:
        return jsonify({'status': 'unknown', 'message': 'Không nhận diện được khuôn mặt. Vui lòng thử lại'}), 200

    if recognized_id != student.id:
        return jsonify({'status': 'mismatch', 'message': 'Khuôn mặt không khớp với mã sinh viên đã nhập'}), 200

    # Mark attendance
    record = AttendanceRecord(
        session_id=int(session_id),
        student_id=student.id,
        attendance_time=datetime.utcnow(),
        status='present',
        confidence_score=confidence / 100.0 if confidence else None,
        model_version_id=active_model.id,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get('User-Agent') or '')[:255]
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Điểm danh thành công!',
        'student_name': student.full_name,
        'student_code': student.student_code,
        'attendance_time': record.attendance_time.strftime('%H:%M:%S'),
        'confidence': round(confidence, 1) if confidence else None
    }), 201
