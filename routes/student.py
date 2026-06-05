"""Student-specific API routes: face registration, active sessions, authenticated check-in."""
import cv2
import numpy as np
import pickle
from datetime import datetime
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from models import (
    db, Student, FaceEmbedding, ClassSession, AttendanceRecord, ClassroomStudent
)
from utils.decorators import student_only
from middleware.rate_limit import limiter

student_api_bp = Blueprint('student_api', __name__)

FACE_SIMILARITY_THRESHOLD = 0.45   # ArcFace cross-pose similarity is lower than same-pose

# buffalo_sc has SCRFD (detection) + ArcFaceONNX (recognition) only.
# It does NOT include a pose estimation model, so face.pose is always None.
# We fall back to 5-point keypoint geometry for pose classification.
#
# Keypoints from SCRFD (image coordinates):
#   kps[0] = left eye (leftmost in image)
#   kps[1] = right eye (rightmost in image)
#   kps[2] = nose tip
#
# Pose indicator: ratio = (nose_x - eye_mid_x) / eye_separation
#   ratio ≈  0   → front
#   ratio > +R   → one lateral direction
#   ratio < -R   → other lateral direction
_KPS_YAW_RATIO_THRESH = 0.12   # ~18–22 degree turn

POSE_LABELS = {
    'front':   'Nhìn thẳng',
    'left':    'Quay sang trái',
    'right':   'Quay sang phải',
    'unknown': 'Không xác định',
}


def _classify_pose(face):
    """
    Classify face orientation.
    Priority:
      1. face.pose euler angles  (available with buffalo_l, etc.)
      2. face.kps 5-point geometry (works with buffalo_sc SCRFD)
      3. 'unknown' fallback — caller treats this as "accept any pose"
    Returns (pose_name, pitch_deg, yaw_deg).
    """
    # --- Method 1: euler angles (buffalo_l / models with pose model) ---
    try:
        if face.pose is not None:
            pitch = float(face.pose[0])
            yaw   = float(face.pose[1])
            if abs(yaw) < 20 and abs(pitch) < 20:
                return 'front', pitch, yaw
            if yaw < -20:
                return 'left',  pitch, yaw
            if yaw >  20:
                return 'right', pitch, yaw
            return 'unknown', pitch, yaw
    except Exception:
        pass

    # --- Method 2: 5-keypoint geometry (buffalo_sc SCRFD) ---
    try:
        kps = face.kps
        if kps is not None and len(kps) >= 3:
            lx  = float(kps[0][0])          # left eye x  (image left)
            rx  = float(kps[1][0])          # right eye x (image right)
            nx  = float(kps[2][0])          # nose x
            sep = abs(rx - lx)
            if sep > 1.0:
                ratio = (nx - (lx + rx) / 2.0) / sep
                yaw_approx = ratio * 90.0
                if ratio >  _KPS_YAW_RATIO_THRESH:
                    return 'left',  0.0, yaw_approx
                if ratio < -_KPS_YAW_RATIO_THRESH:
                    return 'right', 0.0, yaw_approx
                return 'front', 0.0, yaw_approx
    except Exception:
        pass

    # --- Fallback: pose undetermined → accept any required pose ---
    return 'unknown', 0.0, 0.0


@student_api_bp.route('/me', methods=['GET'])
@jwt_required()
@student_only
def get_student_me():
    """Return current student profile with face registration status."""
    student_id = int(get_jwt_identity())
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Không tìm thấy sinh viên'}), 404

    embedding_count = FaceEmbedding.query.filter_by(
        student_id=student.id, is_active=True
    ).count()

    return jsonify({
        'id': student.id,
        'student_code': student.student_code,
        'full_name': student.full_name,
        'email': student.email,
        'face_registered': student.face_registered,
        'embedding_count': embedding_count,
        'department': student.department.name if student.department else None,
    }), 200


@student_api_bp.route('/register-face', methods=['POST'])
@limiter.exempt
@jwt_required()
@student_only
def register_face():
    """
    Register one webcam frame as a face embedding.
    Accepts multipart/form-data:
      - image: JPEG file
      - required_pose: 'front' | 'left' | 'right' | 'any'  (default 'any')
    Returns pose_detected and pose_match so the frontend can advance steps.
    """
    from face_utils import decode_image, yolo_has_face, _get_insight

    student_id = int(get_jwt_identity())
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Không tìm thấy sinh viên'}), 404

    required_pose = request.form.get('required_pose', 'any')  # any/front/left/right

    image_file = request.files.get('image')
    if not image_file:
        return jsonify({'error': 'Không có ảnh được gửi'}), 400

    image_bytes = image_file.read()
    if not image_bytes:
        return jsonify({'error': 'Ảnh rỗng'}), 400

    frame = decode_image(image_bytes)
    if frame is None:
        return jsonify({'error': 'Không thể đọc ảnh'}), 400

    # Quick YOLO face gate
    if not yolo_has_face(frame):
        return jsonify({
            'status': 'no_face',
            'message': 'Không phát hiện khuôn mặt. Hãy nhìn thẳng vào camera và đảm bảo ánh sáng đủ',
            'pose_detected': None,
            'pose_match': False,
        }), 200

    # InsightFace
    app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return jsonify({
            'status': 'no_face',
            'message': 'Không thể phân tích khuôn mặt. Hãy thử lại',
            'pose_detected': None,
            'pose_match': False,
        }), 200

    face = max(faces, key=lambda f: f.det_score)

    # Classify pose BEFORE anti-spoof so we can return pose info even on wrong angle
    pose_name, pitch, yaw = _classify_pose(face)

    # Check required pose.
    # 'unknown' means pose model unavailable (buffalo_sc) → accept any frame
    # so the system degrades gracefully to the original 30-frame behavior.
    pose_match = (
        required_pose == 'any'
        or pose_name == required_pose
        or pose_name == 'unknown'
    )
    if not pose_match:
        embedding_count = FaceEmbedding.query.filter_by(
            student_id=student.id, is_active=True
        ).count()
        return jsonify({
            'status': 'wrong_pose',
            'message': (
                f'Đang nhận: {POSE_LABELS.get(pose_name, pose_name)}. '
                f'Cần: {POSE_LABELS.get(required_pose, required_pose)}'
            ),
            'pose_detected': pose_name,
            'pose_match': False,
            'embedding_count': embedding_count,
        }), 200

    # Anti-spoofing (gracefully skipped if models not loaded)
    try:
        from antispoof_utils import check_liveness
        is_live, _ = check_liveness(frame, face.bbox)
        if not is_live:
            return jsonify({
                'status': 'spoof',
                'message': 'Phát hiện ảnh giả mạo. Vui lòng dùng khuôn mặt thật trước camera',
                'pose_detected': pose_name,
                'pose_match': True,
            }), 200
    except Exception:
        pass

    embedding = face.normed_embedding.astype(np.float32)

    face_emb = FaceEmbedding(
        student_id=student.id,
        embedding_vector=pickle.dumps(embedding),
        quality_score=float(face.det_score),
        is_active=True,
    )
    db.session.add(face_emb)
    student.face_registered = True
    db.session.commit()

    embedding_count = FaceEmbedding.query.filter_by(
        student_id=student.id, is_active=True
    ).count()

    return jsonify({
        'status': 'success',
        'message': f'Đã lưu: {POSE_LABELS[pose_name]} (frame #{embedding_count})',
        'embedding_count': embedding_count,
        'face_registered': True,
        'pose_detected': pose_name,
        'pose_match': True,
        'yaw': round(yaw, 1),
        'pitch': round(pitch, 1),
    }), 200


@student_api_bp.route('/complete-registration', methods=['POST'])
@limiter.exempt
@jwt_required()
@student_only
def complete_registration():
    """
    Called when student finishes all 3 pose steps.
    Automatically retrains the SVM on ALL students' FaceEmbedding data
    so recognize/check-in can work immediately without admin action.
    Mirrors what old retrain_from_db() did after register_user().
    """
    import pickle as _pickle
    from face_utils import retrain_svm, SVM_PATH
    from models import FaceModel

    student_id = int(get_jwt_identity())

    # Ensure the student has enough embeddings
    count = FaceEmbedding.query.filter_by(
        student_id=student_id, is_active=True
    ).count()
    if count < 10:
        return jsonify({
            'error': f'Chưa đủ mẫu khuôn mặt ({count}/10). Hãy đăng ký thêm.'
        }), 400

    # Load ALL active embeddings from ALL students
    rows = db.session.query(
        FaceEmbedding.student_id, FaceEmbedding.embedding_vector
    ).filter(FaceEmbedding.is_active == True).all()

    embeddings_by_student = {}
    for sid, emb_bytes in rows:
        try:
            emb = _pickle.loads(emb_bytes)
            embeddings_by_student.setdefault(sid, []).append(emb)
        except Exception:
            continue

    if not embeddings_by_student:
        return jsonify({'error': 'Không có dữ liệu embedding nào'}), 400

    # Retrain SVM (same as admin training route)
    success = retrain_svm(embeddings_by_student)
    if not success:
        return jsonify({'error': 'Huấn luyện mô hình thất bại'}), 500

    # Record new FaceModel (deactivate old ones)
    FaceModel.query.update({'is_active': False})
    version = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    new_model = FaceModel(
        model_name=f'AutoTrain_{version}',
        version=version,
        algorithm='SVM',
        model_file_path=SVM_PATH,
        is_active=True,
        trained_at=datetime.utcnow(),
        training_stats={
            'num_students': len(embeddings_by_student),
            'num_embeddings': sum(len(v) for v in embeddings_by_student.values()),
            'trigger': 'student_registration_complete',
        }
    )
    db.session.add(new_model)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Mô hình nhận diện đã được cập nhật',
        'students_in_model': len(embeddings_by_student),
        'total_embeddings': sum(len(v) for v in embeddings_by_student.values()),
    }), 200


@student_api_bp.route('/active-sessions', methods=['GET'])
@limiter.exempt
@jwt_required()
@student_only
def get_active_sessions():
    """
    Return currently active (ongoing) sessions for this student's enrolled classes.
    Polled every 5 seconds by the student dashboard.
    """
    student_id = int(get_jwt_identity())

    enrolled_classroom_ids = [
        cs.classroom_id
        for cs in ClassroomStudent.query.filter_by(student_id=student_id).all()
    ]

    if not enrolled_classroom_ids:
        return jsonify({'sessions': []}), 200

    sessions = ClassSession.query.filter(
        ClassSession.classroom_id.in_(enrolled_classroom_ids),
        ClassSession.status == 'ongoing'
    ).all()

    result = []
    for s in sessions:
        already_attended = AttendanceRecord.query.filter_by(
            session_id=s.id, student_id=student_id
        ).first() is not None

        result.append({
            'id': s.id,
            'classroom': s.classroom.class_name if s.classroom else '—',
            'subject': s.subject.subject_name if s.subject else '—',
            'session_date': s.session_date.isoformat(),
            'start_time': s.start_time.strftime('%H:%M') if s.start_time else None,
            'already_attended': already_attended,
        })

    return jsonify({'sessions': result}), 200


@student_api_bp.route('/sessions/<int:session_id>/check-in', methods=['POST'])
@jwt_required()
@student_only
def student_face_checkin(session_id):
    """
    Authenticated student face check-in for an ongoing session.
    Accepts multipart/form-data with 'image' file.
    Compares webcam embedding against stored embeddings via cosine similarity.
    """
    from face_utils import decode_image, yolo_has_face, _get_insight

    student_id = int(get_jwt_identity())
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'error': 'Không tìm thấy sinh viên'}), 404

    # Validate session
    session = ClassSession.query.get(session_id)
    if not session:
        return jsonify({'status': 'error', 'message': 'Buổi học không tồn tại'}), 404

    if session.status == 'scheduled':
        return jsonify({'status': 'session_closed', 'message': 'Giảng viên chưa mở điểm danh'}), 400
    if session.status in ('completed', 'cancelled'):
        labels = {'completed': 'đã kết thúc', 'cancelled': 'đã hủy'}
        return jsonify({'status': 'session_closed', 'message': f'Phiên điểm danh {labels[session.status]}'}), 400

    # Check enrollment
    enrolled = ClassroomStudent.query.filter_by(
        classroom_id=session.classroom_id, student_id=student_id
    ).first()
    if not enrolled:
        return jsonify({'status': 'not_enrolled', 'message': 'Bạn không thuộc lớp học này'}), 403

    # Check duplicate
    existing = AttendanceRecord.query.filter_by(
        session_id=session_id, student_id=student_id
    ).first()
    if existing:
        return jsonify({
            'status': 'already_checked_in',
            'message': 'Bạn đã điểm danh buổi học này rồi',
            'attendance_time': existing.attendance_time.strftime('%H:%M:%S') if existing.attendance_time else None,
        }), 200

    # Check student has face data
    stored_embeddings = FaceEmbedding.query.filter_by(
        student_id=student_id, is_active=True
    ).all()
    if not stored_embeddings:
        return jsonify({
            'status': 'no_face',
            'message': 'Bạn chưa đăng ký khuôn mặt. Hãy đăng ký khuôn mặt trước khi điểm danh'
        }), 400

    # Read image
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({'error': 'Không có ảnh được gửi'}), 400

    image_bytes = image_file.read()
    frame = decode_image(image_bytes)
    if frame is None:
        return jsonify({'error': 'Không thể đọc ảnh'}), 400

    if not yolo_has_face(frame):
        return jsonify({
            'status': 'no_face',
            'message': 'Không phát hiện khuôn mặt. Hãy nhìn thẳng vào camera'
        }), 200

    # InsightFace embedding
    app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = app.get(rgb)
    if not faces:
        return jsonify({'status': 'no_face', 'message': 'Không phát hiện khuôn mặt'}), 200

    face = max(faces, key=lambda f: f.det_score)

    # Anti-spoofing
    try:
        from antispoof_utils import check_liveness
        is_live, _ = check_liveness(frame, face.bbox)
        if not is_live:
            return jsonify({
                'status': 'spoof',
                'message': 'Phát hiện ảnh giả mạo. Vui lòng dùng khuôn mặt thật trước camera'
            }), 200
    except Exception:
        pass

    query_emb = face.normed_embedding.astype(np.float32)

    # Cosine similarity against all stored embeddings
    best_sim = 0.0
    for fe in stored_embeddings:
        try:
            stored_emb = pickle.loads(fe.embedding_vector)
            sim = float(np.dot(query_emb, stored_emb))
            if sim > best_sim:
                best_sim = sim
        except Exception:
            continue

    if best_sim < FACE_SIMILARITY_THRESHOLD:
        return jsonify({
            'status': 'mismatch',
            'message': 'Khuôn mặt không khớp với dữ liệu đã đăng ký. Vui lòng thử lại hoặc liên hệ giảng viên',
            'confidence': round(best_sim * 100, 1),
        }), 200

    # Record attendance
    record = AttendanceRecord(
        session_id=session_id,
        student_id=student_id,
        classroom_id=session.classroom_id,
        subject_id=session.subject_id,
        attendance_time=datetime.utcnow(),
        status='present',
        confidence_score=best_sim,
        ip_address=request.remote_addr,
        user_agent=(request.headers.get('User-Agent') or '')[:255],
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Điểm danh thành công!',
        'student_name': student.full_name,
        'attendance_time': record.attendance_time.strftime('%H:%M:%S'),
        'confidence': round(best_sim * 100, 1),
    }), 201
