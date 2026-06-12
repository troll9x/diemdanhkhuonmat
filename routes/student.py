"""
Các route API dành cho Sinh viên — Tham gia lớp, Đăng ký khuôn mặt, Điểm danh, Lịch sử.
Blueprint: student_api_bp — đăng ký tại /api/student
"""
import cv2
import numpy as np
import pickle
from datetime import date, datetime

from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity
from models import (
    db, AppUser, AppClassroom, AppEnrollment,
    AppStudentProfile, AppFaceEmbedding,
    AttendanceSession, AppAttendanceRecord,
)
from middleware.rate_limit import limiter
from utils.geo import calculate_distance_meters

# Khai báo Blueprint cho module sinh viên
student_api_bp = Blueprint('student_api', __name__)

# Ngưỡng tương đồng cosine tối thiểu để nhận diện khuôn mặt thành công
FACE_SIMILARITY_THRESHOLD = 0.45

# Ngưỡng tỷ lệ keypoint để phân loại hướng nhìn
_KPS_YAW_RATIO_THRESH = 0.12

# Nhãn hiển thị cho các hướng nhìn của khuôn mặt
POSE_LABELS = {
    'front': 'Nhìn thẳng',
    'left': 'Quay sang trái',
    'right': 'Quay sang phải',
    'unknown': 'Không xác định',
}


# ---------------------------------------------------------------------------
# Các hàm trợ giúp (Helpers)
# ---------------------------------------------------------------------------

def _require_student():
    """
    Kiểm tra JWT và đảm bảo người dùng hiện tại có vai trò 'student'.
    Trả về: (AppUser, None) nếu hợp lệ, (None, (response, code)) nếu không.
    """
    claims = get_jwt()
    if claims.get('role') != 'student':
        return None, (jsonify({'error': 'Chỉ sinh viên mới có quyền truy cập'}), 403)
    user = AppUser.query.get(int(get_jwt_identity()))
    if not user or not user.is_active or user.role != 'student':
        return None, (jsonify({'error': 'Người dùng không tồn tại'}), 403)
    return user, None


def _classify_pose(face):
    """
    Phân loại hướng nhìn của khuôn mặt: front (thẳng), left (trái), right (phải).
    Dùng thuộc tính pose của InsightFace hoặc keypoints nếu không có.
    Trả về: (pose_name, pitch_độ, yaw_độ)
    """
    # Ưu tiên dùng pose từ InsightFace nếu có
    try:
        if face.pose is not None:
            pitch = float(face.pose[0])
            yaw = float(face.pose[1])
            if abs(yaw) < 20 and abs(pitch) < 20:
                return 'front', pitch, yaw   # Nhìn thẳng
            return ('left' if yaw < -20 else 'right'), pitch, yaw
    except Exception:
        pass

    # Dùng keypoints (toạ độ mắt và mũi) để ước tính hướng nhìn
    try:
        kps = face.kps
        if kps is not None and len(kps) >= 3:
            lx = float(kps[0][0])   # Mắt trái x
            rx = float(kps[1][0])   # Mắt phải x
            nx = float(kps[2][0])   # Mũi x
            sep = abs(rx - lx)
            if sep > 1.0:
                ratio = (nx - (lx + rx) / 2.0) / sep   # Tỷ lệ lệch của mũi
                yaw_approx = ratio * 90.0
                if ratio > _KPS_YAW_RATIO_THRESH:
                    return 'left', 0.0, yaw_approx
                if ratio < -_KPS_YAW_RATIO_THRESH:
                    return 'right', 0.0, yaw_approx
                return 'front', 0.0, yaw_approx
    except Exception:
        pass

    return 'unknown', 0.0, 0.0   # Không xác định được


# ---------------------------------------------------------------------------
# GET /api/student/dashboard — Tổng quan sinh viên
# ---------------------------------------------------------------------------

@student_api_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def student_dashboard():
    """
    Trả về thông tin tổng quan cho sinh viên:
    - Thông tin cá nhân, trạng thái đăng ký khuôn mặt
    - Danh sách phiên điểm danh đang mở hôm nay
    """
    student, err = _require_student()
    if err:
        return err

    profile = student.student_profile
    enrollments = student.enrollments.filter_by(is_active=True).all()

    # Tìm các phiên điểm danh đang mở cho các lớp sinh viên đang học
    enrolled_cls_ids = [e.classroom_id for e in enrollments]
    open_sessions = []
    if enrolled_cls_ids:
        sessions = AttendanceSession.query.filter(
            AttendanceSession.classroom_id.in_(enrolled_cls_ids),
            AttendanceSession.status == 'open',
            AttendanceSession.session_date == date.today(),
        ).all()
        for s in sessions:
            # Kiểm tra sinh viên đã điểm danh phiên này chưa
            already = AppAttendanceRecord.query.filter_by(
                session_id=s.id, student_id=student.id
            ).first()
            open_sessions.append({
                'session_id': s.id,
                'classroom_id': s.classroom_id,
                'classroom_name': s.classroom.name if s.classroom else '—',
                'already_checked_in': already is not None,
            })

    return jsonify({
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email,
        'student_code': profile.student_code if profile else None,
        'face_registered': profile.face_registered if profile else False,
        'total_classes': len(enrollments),
        'open_sessions': open_sessions,
    }), 200


# ---------------------------------------------------------------------------
# POST /api/student/join-class — Tham gia lớp học bằng mã
# ---------------------------------------------------------------------------

@student_api_bp.route('/join-class', methods=['POST'])
@jwt_required()
def join_class():
    """
    Sinh viên tham gia lớp học bằng mã lớp do giảng viên cung cấp.
    Yêu cầu: đã đăng ký khuôn mặt trước khi tham gia lớp.
    """
    student, err = _require_student()
    if err:
        return err

    # Bắt buộc đăng ký khuôn mặt trước khi vào lớp
    profile = student.student_profile
    if not profile or not profile.face_registered:
        return jsonify({
            'error': 'Bạn cần đăng ký khuôn mặt trước khi tham gia lớp học',
            'redirect': '/student/face-registration',
        }), 403

    data = request.get_json() or {}
    class_code = (data.get('class_code') or '').strip().upper()
    if not class_code:
        return jsonify({'error': 'Vui lòng nhập mã lớp'}), 400

    cls = AppClassroom.query.filter_by(class_code=class_code, is_active=True).first()
    if not cls:
        return jsonify({'error': 'Mã lớp không tồn tại hoặc đã bị đóng'}), 404

    # Kiểm tra sinh viên đã tham gia lớp này chưa
    existing = AppEnrollment.query.filter_by(
        classroom_id=cls.id, student_id=student.id
    ).first()
    if existing:
        if existing.is_active:
            return jsonify({'error': 'Bạn đã tham gia lớp này rồi'}), 409
        # Nếu đã bị huỷ, kích hoạt lại
        existing.is_active = True
        db.session.commit()
        return jsonify({'message': 'Đã tham gia lại lớp thành công'}), 200

    # Cập nhật mã sinh viên nếu được cung cấp và chưa có
    student_code = (data.get('student_code') or '').strip() or None
    if student_code and student.student_profile:
        if not student.student_profile.student_code:
            student.student_profile.student_code = student_code

    enr = AppEnrollment(
        classroom_id=cls.id,
        student_id=student.id,
        student_code=student_code,
        is_active=True,
    )
    db.session.add(enr)
    db.session.commit()

    return jsonify({
        'message': f'Đã tham gia lớp "{cls.name}" thành công',
        'classroom': {
            'id': cls.id,
            'name': cls.name,
            'class_code': cls.class_code,
        },
    }), 201


# ---------------------------------------------------------------------------
# GET /api/student/classes — Danh sách lớp học đã tham gia
# ---------------------------------------------------------------------------

@student_api_bp.route('/classes', methods=['GET'])
@jwt_required()
def get_my_classes():
    """Lấy danh sách tất cả lớp học mà sinh viên đang tham gia."""
    student, err = _require_student()
    if err:
        return err

    enrollments = student.enrollments.filter_by(is_active=True).all()
    result = []
    for enr in enrollments:
        cls = enr.classroom
        if not cls:
            continue
        # Kiểm tra phiên điểm danh hôm nay của lớp
        today_session = AttendanceSession.query.filter_by(
            classroom_id=cls.id, session_date=date.today()
        ).first()
        already = None
        if today_session:
            already = AppAttendanceRecord.query.filter_by(
                session_id=today_session.id, student_id=student.id
            ).first()
        result.append({
            'id': cls.id,
            'name': cls.name,
            'class_code': cls.class_code,
            'teacher_name': cls.teacher.full_name if cls.teacher else '—',
            'joined_at': enr.joined_at.isoformat(),
            'today_session': {
                'id': today_session.id,
                'status': today_session.status,
                'already_checked_in': already is not None,
            } if today_session else None,
        })
    return jsonify({'classes': result}), 200


# ---------------------------------------------------------------------------
# POST /api/student/register-face — Đăng ký khuôn mặt
# ---------------------------------------------------------------------------

@student_api_bp.route('/register-face', methods=['POST'])
@limiter.exempt   # Miễn giới hạn tốc độ cho đăng ký khuôn mặt
@jwt_required()
def register_face():
    """
    Lưu một khung hình webcam làm embedding khuôn mặt.
    Form-data: image (file ảnh), required_pose (any|front|left|right).
    Quy trình: phát hiện khuôn mặt → kiểm tra hướng nhìn → anti-spoof → lưu embedding.
    """
    from face_utils import decode_image, yolo_has_face, _get_insight

    student, err = _require_student()
    if err:
        return err

    required_pose = request.form.get('required_pose', 'any')   # Hướng nhìn yêu cầu

    image_file = request.files.get('image')
    if not image_file:
        return jsonify({'error': 'Không có ảnh được gửi'}), 400

    image_bytes = image_file.read()
    if not image_bytes:
        return jsonify({'error': 'Ảnh rỗng'}), 400

    frame = decode_image(image_bytes)
    if frame is None:
        return jsonify({'error': 'Không thể đọc ảnh'}), 400

    # Bước 1: YOLO kiểm tra nhanh có khuôn mặt không
    if not yolo_has_face(frame):
        return jsonify({
            'status': 'no_face',
            'message': 'Không phát hiện khuôn mặt. Hãy nhìn thẳng vào camera',
            'pose_detected': None,
            'pose_match': False,
        }), 200

    # Bước 2: InsightFace phân tích khuôn mặt chi tiết
    insight_app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = insight_app.get(rgb)
    if not faces:
        return jsonify({
            'status': 'no_face',
            'message': 'Không thể phân tích khuôn mặt. Hãy thử lại',
            'pose_detected': None,
            'pose_match': False,
        }), 200

    face = max(faces, key=lambda f: f.det_score)
    pose_name, pitch, yaw = _classify_pose(face)   # Phân loại hướng nhìn

    # Bước 3: Kiểm tra hướng nhìn có đúng yêu cầu không
    pose_match = (
        required_pose == 'any'
        or pose_name == required_pose
        or pose_name == 'unknown'
    )
    if not pose_match:
        count = AppFaceEmbedding.query.filter_by(user_id=student.id, is_active=True).count()
        return jsonify({
            'status': 'wrong_pose',
            'message': (
                f'Đang nhận: {POSE_LABELS.get(pose_name, pose_name)}. '
                f'Cần: {POSE_LABELS.get(required_pose, required_pose)}'
            ),
            'pose_detected': pose_name,
            'pose_match': False,
            'embedding_count': count,
        }), 200

    # Bước 4: Kiểm tra anti-spoofing (chống ảnh giả mạo)
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
        pass   # Bỏ qua lỗi anti-spoof, vẫn cho phép đăng ký

    # Bước 5: Lưu embedding khuôn mặt vào DB
    embedding = face.normed_embedding.astype(np.float32)

    face_emb = AppFaceEmbedding(
        user_id=student.id,
        embedding_vector=pickle.dumps(embedding),   # Serialize vector bằng pickle
        is_active=True,
    )
    db.session.add(face_emb)

    # Cập nhật trạng thái đã đăng ký khuôn mặt
    if student.student_profile:
        student.student_profile.face_registered = True
    else:
        profile = AppStudentProfile(user_id=student.id, face_registered=True)
        db.session.add(profile)

    db.session.commit()

    count = AppFaceEmbedding.query.filter_by(user_id=student.id, is_active=True).count()
    return jsonify({
        'status': 'success',
        'message': f'Đã lưu: {POSE_LABELS[pose_name]} (frame #{count})',
        'embedding_count': count,
        'face_registered': True,
        'pose_detected': pose_name,
        'pose_match': True,
        'yaw': round(yaw, 1),
        'pitch': round(pitch, 1),
    }), 200


# ---------------------------------------------------------------------------
# POST /api/student/complete-registration — Hoàn thành đăng ký khuôn mặt
# ---------------------------------------------------------------------------

@student_api_bp.route('/complete-registration', methods=['POST'])
@limiter.exempt
@jwt_required()
def complete_registration():
    """
    Huấn luyện lại mô hình SVM sau khi sinh viên hoàn thành đăng ký khuôn mặt.
    Yêu cầu: sinh viên đã đăng ký ít nhất 10 mẫu khuôn mặt.
    """
    import pickle as _pickle
    from face_utils import retrain_svm, SVM_PATH
    from models import FaceModel

    student, err = _require_student()
    if err:
        return err

    count = AppFaceEmbedding.query.filter_by(user_id=student.id, is_active=True).count()
    if count < 10:
        return jsonify({'error': f'Chưa đủ mẫu ({count}/10). Hãy đăng ký thêm.'}), 400

    # Tải tất cả embedding của mọi sinh viên để huấn luyện SVM
    rows = db.session.query(
        AppFaceEmbedding.user_id, AppFaceEmbedding.embedding_vector
    ).filter(AppFaceEmbedding.is_active == True).all()

    embeddings_by_user = {}
    for uid, emb_bytes in rows:
        try:
            emb = _pickle.loads(emb_bytes)
            embeddings_by_user.setdefault(uid, []).append(emb)
        except Exception:
            continue

    if not embeddings_by_user:
        return jsonify({'error': 'Không có dữ liệu embedding nào'}), 400

    # Huấn luyện lại SVM
    success = retrain_svm(embeddings_by_user)
    if not success:
        return jsonify({'error': 'Huấn luyện mô hình thất bại'}), 500

    # Vô hiệu hoá tất cả mô hình cũ và tạo bản ghi mô hình mới
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
            'num_students': len(embeddings_by_user),
            'num_embeddings': sum(len(v) for v in embeddings_by_user.values()),
            'trigger': 'student_registration_complete',
        },
    )
    db.session.add(new_model)
    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Đăng ký khuôn mặt hoàn tất',
        'students_in_model': len(embeddings_by_user),
        'total_embeddings': sum(len(v) for v in embeddings_by_user.values()),
    }), 200


# ---------------------------------------------------------------------------
# GET /api/student/classes/<class_id>/active-session — Phiên điểm danh đang mở
# ---------------------------------------------------------------------------

@student_api_bp.route('/classes/<int:class_id>/active-session', methods=['GET'])
@jwt_required()
def get_active_session(class_id):
    """Kiểm tra xem lớp học có phiên điểm danh đang mở hôm nay không."""
    student, err = _require_student()
    if err:
        return err

    # Kiểm tra sinh viên có trong lớp không
    enr = AppEnrollment.query.filter_by(
        classroom_id=class_id, student_id=student.id, is_active=True
    ).first()
    if not enr:
        return jsonify({'error': 'Bạn không thuộc lớp học này'}), 403

    session = AttendanceSession.query.filter_by(
        classroom_id=class_id,
        session_date=date.today(),
        status='open',
    ).first()

    if not session:
        return jsonify({'session': None}), 200

    # Kiểm tra sinh viên đã điểm danh phiên này chưa
    already = AppAttendanceRecord.query.filter_by(
        session_id=session.id, student_id=student.id
    ).first()

    return jsonify({
        'session': {
            'id': session.id,
            'status': session.status,
            'session_date': session.session_date.isoformat(),
            'started_at': session.started_at.isoformat(),
            'already_checked_in': already is not None,
        },
    }), 200


# ---------------------------------------------------------------------------
# POST /api/student/sessions/<session_id>/check-in — Điểm danh khuôn mặt + GPS
# ---------------------------------------------------------------------------

@student_api_bp.route('/sessions/<int:session_id>/check-in', methods=['POST'])
@jwt_required()
def student_checkin(session_id):
    """
    Điểm danh bằng khuôn mặt + GPS.
    Form-data: image (file ảnh), latitude (float), longitude (float).
    Quy trình:
      1. Kiểm tra phiên còn mở và sinh viên thuộc lớp
      2. Phát hiện khuôn mặt (YOLO → InsightFace)
      3. Kiểm tra anti-spoof
      4. So sánh cosine với embedding đã đăng ký
      5. Kiểm tra khoảng cách GPS đến giảng viên
      6. Tính trạng thái đến muộn và lưu bản ghi
    """
    from face_utils import decode_image, yolo_has_face, _get_insight

    student, err = _require_student()
    if err:
        return err

    session = AttendanceSession.query.get(session_id)
    if not session:
        return jsonify({'status': 'error', 'message': 'Phiên điểm danh không tồn tại'}), 404

    if session.status == 'closed':
        return jsonify({'status': 'session_closed', 'message': 'Phiên điểm danh đã kết thúc'}), 400

    # Kiểm tra sinh viên có đăng ký lớp này không
    enr = AppEnrollment.query.filter_by(
        classroom_id=session.classroom_id, student_id=student.id, is_active=True
    ).first()
    if not enr:
        return jsonify({'status': 'not_enrolled', 'message': 'Bạn không thuộc lớp học này'}), 403

    # Kiểm tra sinh viên đã điểm danh rồi không
    existing = AppAttendanceRecord.query.filter_by(
        session_id=session_id, student_id=student.id
    ).first()
    if existing:
        return jsonify({
            'status': 'already_checked_in',
            'message': 'Bạn đã điểm danh rồi',
            'checkin_time': existing.checkin_time.strftime('%H:%M:%S'),
        }), 200

    # Kiểm tra sinh viên đã đăng ký khuôn mặt chưa
    profile = student.student_profile
    if not profile or not profile.face_registered:
        return jsonify({
            'status': 'no_face',
            'message': 'Bạn chưa đăng ký khuôn mặt. Vui lòng đăng ký trước',
        }), 400

    # Tải dữ liệu embedding đã đăng ký của sinh viên
    stored_embeddings = AppFaceEmbedding.query.filter_by(
        user_id=student.id, is_active=True
    ).all()
    if not stored_embeddings:
        return jsonify({
            'status': 'no_face',
            'message': 'Không tìm thấy dữ liệu khuôn mặt. Vui lòng đăng ký lại',
        }), 400

    # Đọc toạ độ GPS sinh viên
    lat_str = request.form.get('latitude')
    lon_str = request.form.get('longitude')
    if lat_str is None or lon_str is None:
        return jsonify({'error': 'Cần cung cấp vị trí GPS'}), 400
    try:
        student_lat = float(lat_str)
        student_lon = float(lon_str)
    except (TypeError, ValueError):
        return jsonify({'error': 'Vị trí GPS không hợp lệ'}), 400

    # Đọc ảnh từ request
    image_file = request.files.get('image')
    if not image_file:
        return jsonify({'error': 'Không có ảnh được gửi'}), 400

    image_bytes = image_file.read()
    frame = decode_image(image_bytes)
    if frame is None:
        return jsonify({'error': 'Không thể đọc ảnh'}), 400

    # Phát hiện khuôn mặt bằng YOLO
    if not yolo_has_face(frame):
        return jsonify({'status': 'no_face', 'message': 'Không phát hiện khuôn mặt'}), 200

    # Phân tích khuôn mặt chi tiết bằng InsightFace
    insight_app = _get_insight()
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    faces = insight_app.get(rgb)
    if not faces:
        return jsonify({'status': 'no_face', 'message': 'Không phát hiện khuôn mặt'}), 200

    face = max(faces, key=lambda f: f.det_score)

    # Kiểm tra anti-spoofing
    try:
        from antispoof_utils import check_liveness
        is_live, _ = check_liveness(frame, face.bbox)
        if not is_live:
            return jsonify({
                'status': 'spoof',
                'message': 'Phát hiện ảnh giả mạo. Vui lòng dùng khuôn mặt thật',
            }), 200
    except Exception:
        pass

    query_emb = face.normed_embedding.astype(np.float32)

    # Tính độ tương đồng cosine với tất cả embedding đã đăng ký
    best_sim = 0.0
    for fe in stored_embeddings:
        try:
            stored_emb = pickle.loads(fe.embedding_vector)
            sim = float(np.dot(query_emb, stored_emb))   # Tích vô hướng = cosine sim (đã chuẩn hoá)
            if sim > best_sim:
                best_sim = sim
        except Exception:
            continue

    # Kiểm tra ngưỡng tương đồng
    if best_sim < FACE_SIMILARITY_THRESHOLD:
        return jsonify({
            'status': 'mismatch',
            'message': 'Khuôn mặt không khớp. Vui lòng thử lại hoặc liên hệ giảng viên',
            'confidence': round(best_sim * 100, 1),
        }), 200

    # Kiểm tra khoảng cách GPS đến giảng viên
    teacher_lat = session.teacher_latitude
    teacher_lon = session.teacher_longitude
    distance = None
    reject_reason = None

    if teacher_lat is not None and teacher_lon is not None:
        distance = calculate_distance_meters(student_lat, student_lon, teacher_lat, teacher_lon)
        radius = float(current_app.config.get('ATTENDANCE_RADIUS_METERS', 100))  # Bán kính cho phép (mét)
        if distance > radius:
            # Quá xa — lưu bản ghi bị từ chối
            record = AppAttendanceRecord(
                session_id=session_id,
                classroom_id=session.classroom_id,
                student_id=student.id,
                checkin_time=datetime.utcnow(),
                student_latitude=student_lat,
                student_longitude=student_lon,
                distance_meters=round(distance, 2),
                face_confidence=best_sim,
                status='rejected',
                reject_reason=f'Quá xa giảng viên ({round(distance, 0)}m > {radius}m)',
            )
            db.session.add(record)
            db.session.commit()
            return jsonify({
                'status': 'too_far',
                'message': f'Bạn đang ở quá xa giảng viên ({round(distance, 0)} m). Phạm vi cho phép: {radius} m',
                'distance_meters': round(distance, 1),
            }), 200

    # Tính trạng thái đến muộn (chỉ áp dụng cho phiên đầu giờ)
    now = datetime.utcnow()
    is_late = False
    if session.session_type == 'start':
        from datetime import timedelta
        cutoff = session.started_at + timedelta(minutes=session.late_after_minutes or 15)
        is_late = now > cutoff   # Đến sau thời điểm cho phép = muộn

    # Điểm danh thành công — lưu bản ghi
    record = AppAttendanceRecord(
        session_id=session_id,
        classroom_id=session.classroom_id,
        student_id=student.id,
        checkin_time=now,
        student_latitude=student_lat,
        student_longitude=student_lon,
        distance_meters=round(distance, 2) if distance is not None else None,
        face_confidence=best_sim,
        status='present',
        is_late=is_late,
    )
    db.session.add(record)
    db.session.commit()

    late_msg = ' (Muộn)' if is_late else ''
    return jsonify({
        'status': 'success',
        'message': f'Điểm danh thành công{late_msg}!',
        'student_name': student.full_name,
        'checkin_time': record.checkin_time.strftime('%H:%M:%S'),
        'is_late': is_late,
        'confidence': round(best_sim * 100, 1),    # Độ tin cậy nhận diện khuôn mặt %
        'distance_meters': round(distance, 1) if distance is not None else None,
    }), 201


# ---------------------------------------------------------------------------
# GET /api/student/attendance-logs — Lịch sử điểm danh cá nhân
# ---------------------------------------------------------------------------

@student_api_bp.route('/attendance-logs', methods=['GET'])
@jwt_required()
def get_attendance_logs():
    """Lấy toàn bộ lịch sử điểm danh của sinh viên đang đăng nhập."""
    student, err = _require_student()
    if err:
        return err

    records = (
        AppAttendanceRecord.query
        .filter_by(student_id=student.id)
        .order_by(AppAttendanceRecord.checkin_time.desc())
        .all()
    )

    SESSION_LABEL = {'start': 'Đầu giờ', 'end': 'Cuối giờ'}
    logs = []
    for r in records:
        sess = r.session
        cls = r.classroom_ref
        logs.append({
            'id': r.id,
            'classroom_name': cls.name if cls else '—',
            'session_date': sess.session_date.isoformat() if sess else None,
            'session_type': sess.session_type if sess else None,
            'session_type_label': SESSION_LABEL.get(sess.session_type, sess.session_type) if sess else None,
            'checkin_time': r.checkin_time.strftime('%H:%M:%S'),
            'status': r.status,         # present / rejected
            'is_late': r.is_late,       # Đến muộn không
            'distance_meters': round(r.distance_meters, 1) if r.distance_meters else None,
            'confidence': round(r.face_confidence * 100, 1) if r.face_confidence else None,
            'reject_reason': r.reject_reason,
        })

    return jsonify({'logs': logs, 'total': len(logs)}), 200


# ---------------------------------------------------------------------------
# GET /api/student/active-sessions — Các phiên đang mở (tương thích ngược)
# ---------------------------------------------------------------------------

@student_api_bp.route('/active-sessions', methods=['GET'])
@limiter.exempt
@jwt_required()
def get_active_sessions_legacy():
    """Lấy tất cả phiên điểm danh đang mở hôm nay cho sinh viên (endpoint cũ)."""
    student, err = _require_student()
    if err:
        return err

    enrolled_ids = [
        e.classroom_id for e in student.enrollments.filter_by(is_active=True).all()
    ]
    if not enrolled_ids:
        return jsonify({'sessions': []}), 200

    sessions = AttendanceSession.query.filter(
        AttendanceSession.classroom_id.in_(enrolled_ids),
        AttendanceSession.status == 'open',
        AttendanceSession.session_date == date.today(),
    ).all()

    SESSION_LABEL = {'start': 'Đầu giờ', 'end': 'Cuối giờ'}
    result = []
    for s in sessions:
        already = AppAttendanceRecord.query.filter_by(
            session_id=s.id, student_id=student.id
        ).first()
        result.append({
            'id': s.id,
            'classroom': s.classroom.name if s.classroom else '—',
            'session_date': s.session_date.isoformat(),
            'session_type': s.session_type,
            'session_type_label': SESSION_LABEL.get(s.session_type, s.session_type),
            'already_attended': already is not None,
        })

    return jsonify({'sessions': result}), 200


# ---------------------------------------------------------------------------
# GET /api/student/me — Thông tin sinh viên (tương thích ngược)
# ---------------------------------------------------------------------------

@student_api_bp.route('/me', methods=['GET'])
@jwt_required()
def get_student_me():
    """Trả về thông tin cơ bản của sinh viên đang đăng nhập (endpoint cũ)."""
    student, err = _require_student()
    if err:
        return err

    profile = student.student_profile
    count = AppFaceEmbedding.query.filter_by(user_id=student.id, is_active=True).count()

    return jsonify({
        'id': student.id,
        'full_name': student.full_name,
        'email': student.email,
        'student_code': profile.student_code if profile else None,
        'face_registered': profile.face_registered if profile else False,
        'embedding_count': count,   # Số mẫu khuôn mặt đã đăng ký
    }), 200
