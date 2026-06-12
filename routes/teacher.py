"""
Các route API dành cho Giảng viên — Quản lý lớp học & Điểm danh với lịch học.
Blueprint: teacher_bp — đăng ký tại /api/teacher
"""
import calendar as _cal
import random
import string
from datetime import date, datetime, time as dtime, timedelta

from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt, get_jwt_identity

from models import (
    db, AppUser, AppClassroom, AppEnrollment,
    AppStudentProfile, AppClassSchedule,
    AttendanceSession, AppAttendanceRecord,
)

# Khai báo Blueprint cho module giảng viên
teacher_bp = Blueprint('teacher', __name__)

# Tên các thứ trong tuần (0=Thứ 2, 6=Chủ nhật theo quy ước Python)
DAY_NAMES = ['Thứ 2', 'Thứ 3', 'Thứ 4', 'Thứ 5', 'Thứ 6', 'Thứ 7', 'Chủ nhật']
# Nhãn hiển thị cho loại phiên điểm danh
SESSION_TYPE_LABEL = {'start': 'Đầu giờ', 'end': 'Cuối giờ'}


# ---------------------------------------------------------------------------
# Các hàm trợ giúp (Helpers)
# ---------------------------------------------------------------------------

def _require_teacher():
    """
    Kiểm tra JWT và đảm bảo người dùng hiện tại có vai trò 'teacher'.
    Trả về: (AppUser, None) nếu hợp lệ, (None, (response, code)) nếu không hợp lệ.
    """
    claims = get_jwt()
    if claims.get('role') != 'teacher':
        return None, (jsonify({'error': 'Chỉ giảng viên mới có quyền truy cập'}), 403)
    user = AppUser.query.get(int(get_jwt_identity()))
    if not user or not user.is_active:
        return None, (jsonify({'error': 'Người dùng không tồn tại'}), 403)
    return user, None


def _gen_class_code(length: int = 6) -> str:
    """
    Tạo mã lớp ngẫu nhiên gồm chữ hoa và số, đảm bảo không trùng với mã đã tồn tại.
    Tham số: length — số ký tự của mã (mặc định 6).
    """
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=length))
        if not AppClassroom.query.filter_by(class_code=code).first():
            return code   # Trả về mã duy nhất không trùng trong DB


def _schedule_json(s: AppClassSchedule) -> dict:
    """Chuyển đổi object AppClassSchedule sang dict JSON để trả về API."""
    return {
        'id': s.id,
        'day_of_week': s.day_of_week,
        'day_name': DAY_NAMES[s.day_of_week],           # Tên thứ tiếng Việt
        'start_time': s.start_time.strftime('%H:%M'),   # Giờ bắt đầu định dạng HH:MM
        'end_time': s.end_time.strftime('%H:%M'),        # Giờ kết thúc
        'late_after_minutes': s.late_after_minutes,     # Ngưỡng phút tính đến muộn
        'is_active': s.is_active,
    }


def _classroom_json(cls: AppClassroom) -> dict:
    """Chuyển đổi object AppClassroom sang dict JSON đầy đủ để trả về API."""
    student_count = cls.enrollments.filter_by(is_active=True).count()  # Số sinh viên đang đăng ký
    today_sessions = AttendanceSession.query.filter_by(
        classroom_id=cls.id, session_date=date.today()
    ).all()  # Các phiên điểm danh hôm nay
    schedules = [_schedule_json(s) for s in
                 cls.schedules.filter_by(is_active=True).order_by(AppClassSchedule.day_of_week).all()]

    today_dow = date.today().weekday()   # Thứ hôm nay (0=Thứ 2)
    today_schedule = cls.schedules.filter_by(day_of_week=today_dow, is_active=True).first()

    return {
        'id': cls.id,
        'name': cls.name,
        'class_code': cls.class_code,
        'description': cls.description,
        'start_date': cls.start_date.isoformat() if cls.start_date else None,
        'end_date': cls.end_date.isoformat() if cls.end_date else None,
        'is_active': cls.is_active,
        'created_at': cls.created_at.isoformat(),
        'student_count': student_count,
        'schedules': schedules,
        'today_schedule': _schedule_json(today_schedule) if today_schedule else None,  # Lịch hôm nay
        'today_sessions': [
            {
                'id': s.id,
                'session_type': s.session_type,
                'session_type_label': SESSION_TYPE_LABEL.get(s.session_type, s.session_type),
                'status': s.status,
                'started_at': s.started_at.isoformat(),
            }
            for s in today_sessions
        ],
    }


def _session_json(s: AttendanceSession) -> dict:
    """Chuyển đổi object AttendanceSession sang dict JSON để trả về API."""
    return {
        'id': s.id,
        'session_type': s.session_type,
        'session_type_label': SESSION_TYPE_LABEL.get(s.session_type, s.session_type),
        'status': s.status,
        'session_date': s.session_date.isoformat(),
        'scheduled_start_time': s.scheduled_start_time.strftime('%H:%M') if s.scheduled_start_time else None,
        'late_after_minutes': s.late_after_minutes,
        'started_at': s.started_at.isoformat(),
        'closed_at': s.closed_at.isoformat() if s.closed_at else None,
        'teacher_latitude': s.teacher_latitude,
        'teacher_longitude': s.teacher_longitude,
    }


def _record_row(r: AppAttendanceRecord, s: AttendanceSession) -> dict:
    """Chuyển đổi một bản ghi điểm danh sang dict JSON để hiển thị trong bảng."""
    stu = r.student_user
    return {
        'student_id': r.student_id,
        'student_name': stu.full_name if stu else '—',
        'student_code': (stu.student_profile.student_code if stu and stu.student_profile else None),
        'checkin_time': r.checkin_time.strftime('%H:%M:%S'),   # Giờ điểm danh
        'is_late': r.is_late,                                   # Đến muộn không
        'status': r.status,                                     # present / rejected
        'distance_meters': round(r.distance_meters, 1) if r.distance_meters is not None else None,  # Khoảng cách đến GV
        'confidence': round(r.face_confidence * 100, 1) if r.face_confidence else None,              # Độ tin cậy %
        'reject_reason': r.reject_reason,                       # Lý do từ chối (nếu có)
    }


# ---------------------------------------------------------------------------
# GET /api/teacher/dashboard — Tổng quan dashboard giảng viên
# ---------------------------------------------------------------------------

@teacher_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def teacher_dashboard():
    """
    Trả về thống kê tổng quan cho dashboard giảng viên:
    - Tổng số lớp, sinh viên, phiên điểm danh hôm nay
    - Danh sách 10 lần điểm danh gần nhất
    """
    teacher, err = _require_teacher()
    if err:
        return err

    classrooms = teacher.classrooms_owned.filter_by(is_active=True).all()
    total_students = sum(c.enrollments.filter_by(is_active=True).count() for c in classrooms)

    today = date.today()
    today_sessions = AttendanceSession.query.filter(
        AttendanceSession.teacher_id == teacher.id,
        AttendanceSession.session_date == today,
    ).all()

    # Lấy 10 bản ghi điểm danh gần nhất của tất cả lớp giảng viên này
    recent_records = (
        AppAttendanceRecord.query
        .join(AttendanceSession)
        .filter(AttendanceSession.teacher_id == teacher.id)
        .order_by(AppAttendanceRecord.checkin_time.desc())
        .limit(10).all()
    )

    return jsonify({
        'total_classes': len(classrooms),           # Tổng số lớp đang hoạt động
        'total_students': total_students,           # Tổng số sinh viên trong tất cả lớp
        'today_sessions': len(today_sessions),      # Số phiên điểm danh hôm nay
        'open_sessions': sum(1 for s in today_sessions if s.status == 'open'),  # Số phiên đang mở
        'recent_attendance': [
            {
                'id': r.id,
                'student_name': r.student_user.full_name if r.student_user else '—',
                'classroom_name': r.classroom_ref.name if r.classroom_ref else '—',
                'session_type_label': SESSION_TYPE_LABEL.get(r.session.session_type, '') if r.session else '',
                'checkin_time': r.checkin_time.isoformat(),
                'is_late': r.is_late,
                'status': r.status,
            }
            for r in recent_records
        ],
    }), 200


# ---------------------------------------------------------------------------
# GET/POST /api/teacher/classes — Lấy danh sách / Tạo lớp học
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes', methods=['GET'])
@jwt_required()
def get_classes():
    """Lấy danh sách tất cả lớp học của giảng viên (mới nhất lên trước)."""
    teacher, err = _require_teacher()
    if err:
        return err
    classrooms = teacher.classrooms_owned.order_by(AppClassroom.created_at.desc()).all()
    return jsonify({'classes': [_classroom_json(c) for c in classrooms]}), 200


@teacher_bp.route('/classes', methods=['POST'])
@jwt_required()
def create_class():
    """
    Tạo lớp học mới cho giảng viên.
    Yêu cầu: name, start_date, end_date, schedules (ít nhất 1 buổi/tuần).
    """
    teacher, err = _require_teacher()
    if err:
        return err

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Tên lớp không được để trống'}), 400

    # Xác thực ngày bắt đầu và kết thúc khoá học
    start_date = end_date = None
    start_str = (data.get('start_date') or '').strip()
    end_str   = (data.get('end_date')   or '').strip()

    if not start_str or not end_str:
        return jsonify({'error': 'Vui lòng nhập ngày bắt đầu và ngày kết thúc khoá học'}), 400

    try:
        from datetime import date as _date
        start_date = _date.fromisoformat(start_str)
        end_date   = _date.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Định dạng ngày không hợp lệ (YYYY-MM-DD)'}), 400

    if end_date <= start_date:
        return jsonify({'error': 'Ngày kết thúc phải sau ngày bắt đầu'}), 400

    # Xác thực danh sách buổi học hàng tuần (bắt buộc ít nhất 1)
    raw_scheds = data.get('schedules') or []
    if not raw_scheds:
        return jsonify({'error': 'Vui lòng thêm ít nhất một buổi học trong tuần'}), 400

    parsed_scheds = []
    for idx, s in enumerate(raw_scheds):
        day = s.get('day_of_week')
        st  = (s.get('start_time') or '').strip()
        et  = (s.get('end_time')   or '').strip()
        if day is None or not st or not et:
            return jsonify({'error': f'Buổi học #{idx+1}: cần có thứ, giờ bắt đầu và giờ kết thúc'}), 400
        try:
            day = int(day)
            start_t = dtime.fromisoformat(st)
            end_t   = dtime.fromisoformat(et)
        except (ValueError, TypeError):
            return jsonify({'error': f'Buổi học #{idx+1}: định dạng thời gian không hợp lệ'}), 400
        if day not in range(7):
            return jsonify({'error': f'Buổi học #{idx+1}: thứ phải từ 0 (Thứ 2) đến 6 (Chủ nhật)'}), 400
        if end_t <= start_t:
            return jsonify({'error': f'Buổi học #{idx+1}: giờ kết thúc phải sau giờ bắt đầu'}), 400
        late = int(s.get('late_after_minutes', 15))
        parsed_scheds.append((day, start_t, end_t, late))

    # Kiểm tra không có 2 buổi học cùng một thứ
    days_seen = [p[0] for p in parsed_scheds]
    if len(days_seen) != len(set(days_seen)):
        return jsonify({'error': 'Mỗi thứ chỉ được có một buổi học'}), 400

    # Tạo lớp học trong DB
    cls = AppClassroom(
        teacher_id=teacher.id,
        name=name,
        class_code=_gen_class_code(),   # Tạo mã lớp ngẫu nhiên duy nhất
        description=(data.get('description') or '').strip() or None,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )
    db.session.add(cls)
    db.session.flush()   # Lấy cls.id trước khi thêm lịch học

    # Thêm các buổi học hàng tuần
    for day, start_t, end_t, late in parsed_scheds:
        sched = AppClassSchedule(
            classroom_id=cls.id,
            day_of_week=day,
            start_time=start_t,
            end_time=end_t,
            late_after_minutes=late,
            is_active=True,
        )
        db.session.add(sched)

    db.session.commit()
    return jsonify({'message': 'Tạo lớp thành công', 'class': _classroom_json(cls)}), 201


# ---------------------------------------------------------------------------
# GET /api/teacher/classes/<class_id> — Lấy chi tiết lớp học
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>', methods=['GET'])
@jwt_required()
def get_class(class_id):
    """Lấy thông tin chi tiết của một lớp học (chỉ giảng viên sở hữu mới xem được)."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404
    return jsonify(_classroom_json(cls)), 200


# ---------------------------------------------------------------------------
# PUT /api/teacher/classes/<class_id> — Cập nhật lớp học
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>', methods=['PUT'])
@jwt_required()
def update_class(class_id):
    """Cập nhật thông tin lớp học: tên, mô tả, ngày bắt đầu/kết thúc."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    data = request.get_json() or {}

    # Xác thực tên lớp
    if 'name' in data:
        name = (data['name'] or '').strip()
        if not name:
            return jsonify({'error': 'Tên lớp không được để trống'}), 400

    # Phân tích và xác thực ngày TRƯỚC KHI cập nhật vào DB
    new_start = cls.start_date
    new_end   = cls.end_date

    if 'start_date' in data:
        raw = data['start_date']
        if raw:
            try:
                new_start = date.fromisoformat(str(raw).strip())
            except ValueError:
                return jsonify({'error': 'start_date không hợp lệ (YYYY-MM-DD)'}), 400
        else:
            new_start = None

    if 'end_date' in data:
        raw = data['end_date']
        if raw:
            try:
                new_end = date.fromisoformat(str(raw).strip())
            except ValueError:
                return jsonify({'error': 'end_date không hợp lệ (YYYY-MM-DD)'}), 400
        else:
            new_end = None

    if new_start and new_end and new_end <= new_start:
        return jsonify({'error': 'Ngày kết thúc phải sau ngày bắt đầu'}), 400

    # Áp dụng tất cả thay đổi
    if 'name' in data:
        cls.name = (data['name'] or '').strip()
    if 'description' in data:
        val = data['description']
        cls.description = val.strip() if isinstance(val, str) else None
    cls.start_date = new_start
    cls.end_date   = new_end

    db.session.commit()
    return jsonify({'message': 'Cập nhật lớp thành công', 'class': _classroom_json(cls)}), 200


# ---------------------------------------------------------------------------
# DELETE /api/teacher/classes/<class_id> — Xóa lớp học
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>', methods=['DELETE'])
@jwt_required()
def delete_class(class_id):
    """
    Xóa vĩnh viễn lớp học. Bị chặn nếu lớp đã có dữ liệu điểm danh.
    Nếu có dữ liệu điểm danh, nên dùng deactivate thay vì xóa.
    """
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    # Ngăn xóa nếu đã có bản ghi điểm danh
    total_records = AppAttendanceRecord.query.filter_by(classroom_id=class_id).count()
    if total_records > 0:
        return jsonify({
            'error': f'Không thể xoá lớp đã có dữ liệu điểm danh ({total_records} bản ghi). '
                     f'Hãy huỷ kích hoạt lớp thay vì xoá.',
        }), 409

    # Xóa tuần tự: lịch học → đăng ký → phiên điểm danh → lớp học
    AppClassSchedule.query.filter_by(classroom_id=class_id).delete()
    AppEnrollment.query.filter_by(classroom_id=class_id).delete()
    AttendanceSession.query.filter_by(classroom_id=class_id).delete()
    db.session.delete(cls)
    db.session.commit()
    return jsonify({'message': 'Đã xoá lớp học'}), 200


# ---------------------------------------------------------------------------
# PATCH /api/teacher/classes/<class_id>/deactivate — Bật/tắt lớp học
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/deactivate', methods=['PATCH'])
@jwt_required()
def deactivate_class(class_id):
    """Chuyển đổi trạng thái kích hoạt/huỷ kích hoạt lớp học (toggle)."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    cls.is_active = not cls.is_active   # Đảo trạng thái
    db.session.commit()
    state = 'kích hoạt' if cls.is_active else 'huỷ kích hoạt'
    return jsonify({'message': f'Đã {state} lớp học', 'is_active': cls.is_active}), 200


# ---------------------------------------------------------------------------
# GET /api/teacher/classes/<class_id>/students — Danh sách sinh viên
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/students', methods=['GET'])
@jwt_required()
def get_class_students(class_id):
    """Lấy danh sách sinh viên đang đăng ký trong lớp học."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    enrollments = cls.enrollments.filter_by(is_active=True).all()
    students = []
    for enr in enrollments:
        stu = enr.student
        profile = stu.student_profile if stu else None
        students.append({
            'id': stu.id if stu else None,
            'full_name': stu.full_name if stu else '—',
            'email': stu.email if stu else None,
            'student_code': (profile.student_code if profile else None) or enr.student_code,
            'face_registered': profile.face_registered if profile else False,   # Đã đăng ký khuôn mặt chưa
            'joined_at': enr.joined_at.isoformat(),
        })
    return jsonify({'students': students, 'total': len(students)}), 200


# ---------------------------------------------------------------------------
# CRUD Lịch học: GET/POST /api/teacher/classes/<id>/schedules
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/schedules', methods=['GET'])
@jwt_required()
def get_schedules(class_id):
    """Lấy danh sách lịch học hàng tuần của lớp."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    schedules = cls.schedules.order_by(AppClassSchedule.day_of_week).all()
    return jsonify({'schedules': [_schedule_json(s) for s in schedules]}), 200


@teacher_bp.route('/classes/<int:class_id>/schedules', methods=['POST'])
@jwt_required()
def create_schedule(class_id):
    """
    Thêm buổi học mới vào lịch hàng tuần của lớp.
    Nếu thứ đó đã có lịch, tự động cập nhật (upsert).
    """
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    data = request.get_json() or {}
    day = data.get('day_of_week')
    start_str = (data.get('start_time') or '').strip()
    end_str = (data.get('end_time') or '').strip()

    if day is None or not start_str or not end_str:
        return jsonify({'error': 'Cần cung cấp day_of_week, start_time, end_time'}), 400

    day = int(day)
    if day not in range(7):
        return jsonify({'error': 'day_of_week phải từ 0 (Thứ 2) đến 6 (Chủ nhật)'}), 400

    try:
        start_t = dtime.fromisoformat(start_str)
        end_t = dtime.fromisoformat(end_str)
    except ValueError:
        return jsonify({'error': 'Định dạng thời gian không hợp lệ (HH:MM)'}), 400

    if end_t <= start_t:
        return jsonify({'error': 'Giờ kết thúc phải sau giờ bắt đầu'}), 400

    # Upsert: nếu thứ đó đã có lịch thì cập nhật, không thì tạo mới
    existing = AppClassSchedule.query.filter_by(classroom_id=class_id, day_of_week=day).first()
    if existing:
        existing.start_time = start_t
        existing.end_time = end_t
        existing.late_after_minutes = int(data.get('late_after_minutes', 15))
        existing.is_active = True
        db.session.commit()
        return jsonify({'message': 'Cập nhật lịch thành công', 'schedule': _schedule_json(existing)}), 200

    sched = AppClassSchedule(
        classroom_id=class_id,
        day_of_week=day,
        start_time=start_t,
        end_time=end_t,
        late_after_minutes=int(data.get('late_after_minutes', 15)),
        is_active=True,
    )
    db.session.add(sched)
    db.session.commit()
    return jsonify({'message': 'Thêm lịch thành công', 'schedule': _schedule_json(sched)}), 201


@teacher_bp.route('/classes/<int:class_id>/schedules/<int:sched_id>', methods=['PUT'])
@jwt_required()
def update_schedule(class_id, sched_id):
    """Cập nhật giờ học và ngưỡng đến muộn cho một buổi trong lịch."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    sched = AppClassSchedule.query.filter_by(id=sched_id, classroom_id=class_id).first()
    if not sched:
        return jsonify({'error': 'Không tìm thấy lịch học'}), 404

    data = request.get_json() or {}
    if 'start_time' in data:
        try:
            sched.start_time = dtime.fromisoformat(data['start_time'])
        except ValueError:
            return jsonify({'error': 'Định dạng start_time không hợp lệ'}), 400
    if 'end_time' in data:
        try:
            sched.end_time = dtime.fromisoformat(data['end_time'])
        except ValueError:
            return jsonify({'error': 'Định dạng end_time không hợp lệ'}), 400
    if 'late_after_minutes' in data:
        sched.late_after_minutes = int(data['late_after_minutes'])
    if 'is_active' in data:
        sched.is_active = bool(data['is_active'])

    if sched.end_time <= sched.start_time:
        return jsonify({'error': 'Giờ kết thúc phải sau giờ bắt đầu'}), 400

    db.session.commit()
    return jsonify({'message': 'Cập nhật lịch thành công', 'schedule': _schedule_json(sched)}), 200


@teacher_bp.route('/classes/<int:class_id>/schedules/<int:sched_id>', methods=['DELETE'])
@jwt_required()
def delete_schedule(class_id, sched_id):
    """Xóa một buổi học khỏi lịch hàng tuần của lớp."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    sched = AppClassSchedule.query.filter_by(id=sched_id, classroom_id=class_id).first()
    if not sched:
        return jsonify({'error': 'Không tìm thấy lịch học'}), 404

    db.session.delete(sched)
    db.session.commit()
    return jsonify({'message': 'Đã xóa lịch học'}), 200


# ---------------------------------------------------------------------------
# POST /api/teacher/classes/<id>/attendance/start — Mở phiên điểm danh
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/attendance/start', methods=['POST'])
@jwt_required()
def start_attendance(class_id):
    """
    Mở phiên điểm danh cho lớp hôm nay.
    Yêu cầu: session_type ('start'/'end'), latitude, longitude của giảng viên.
    Mỗi ngày chỉ có thể mở 1 phiên đầu giờ và 1 phiên cuối giờ.
    """
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    data = request.get_json() or {}
    session_type = data.get('session_type', 'start')
    if session_type not in ('start', 'end'):
        return jsonify({'error': 'session_type phải là start hoặc end'}), 400

    today = date.today()
    # Kiểm tra phiên cùng loại hôm nay đã tồn tại chưa
    existing = AttendanceSession.query.filter_by(
        classroom_id=class_id, session_date=today, session_type=session_type
    ).first()
    if existing:
        label = SESSION_TYPE_LABEL[session_type]
        return jsonify({
            'error': f'Hôm nay đã có phiên "{label}" cho lớp này',
            'session': _session_json(existing),
        }), 409

    # Bắt buộc giảng viên cung cấp vị trí GPS để sinh viên điểm danh theo khoảng cách
    lat = data.get('latitude')
    lon = data.get('longitude')
    if lat is None or lon is None:
        return jsonify({'error': 'Cần cung cấp vị trí GPS (latitude, longitude)'}), 400
    try:
        lat = float(lat)
        lon = float(lon)
    except (TypeError, ValueError):
        return jsonify({'error': 'Vị trí GPS không hợp lệ'}), 400

    # Lấy lịch hôm nay để điền giờ bắt đầu và ngưỡng đến muộn
    today_dow = today.weekday()
    sched = cls.schedules.filter_by(day_of_week=today_dow, is_active=True).first()
    scheduled_start = sched.start_time if sched else None
    late_mins = sched.late_after_minutes if sched else int(data.get('late_after_minutes', 15))

    session = AttendanceSession(
        classroom_id=class_id,
        teacher_id=teacher.id,
        session_date=today,
        session_type=session_type,
        status='open',
        teacher_latitude=lat,
        teacher_longitude=lon,
        scheduled_start_time=scheduled_start,
        late_after_minutes=late_mins,
        started_at=datetime.utcnow(),
    )
    db.session.add(session)
    db.session.commit()

    label = SESSION_TYPE_LABEL[session_type]
    return jsonify({
        'message': f'Đã mở phiên điểm danh "{label}"',
        'session': _session_json(session),
    }), 201


# ---------------------------------------------------------------------------
# POST /api/teacher/classes/<id>/attendance/close — Đóng phiên điểm danh
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/attendance/close', methods=['POST'])
@jwt_required()
def close_attendance(class_id):
    """Đóng phiên điểm danh đang mở của lớp hôm nay."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    data = request.get_json() or {}
    session_type = data.get('session_type', 'start')

    session = AttendanceSession.query.filter_by(
        classroom_id=class_id,
        session_date=date.today(),
        session_type=session_type,
        teacher_id=teacher.id,
    ).first()
    if not session:
        return jsonify({'error': 'Không tìm thấy phiên điểm danh'}), 404
    if session.status == 'closed':
        return jsonify({'error': 'Phiên điểm danh đã được đóng'}), 409

    session.status = 'closed'
    session.closed_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Phiên điểm danh đã đóng', 'session': _session_json(session)}), 200


# ---------------------------------------------------------------------------
# GET /api/teacher/classes/<id>/attendance/today — Điểm danh hôm nay
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/attendance/today', methods=['GET'])
@jwt_required()
def get_today_attendance(class_id):
    """
    Lấy danh sách điểm danh hôm nay của lớp:
    - Sinh viên có mặt và vắng mặt theo từng phiên (đầu giờ/cuối giờ)
    """
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    today = date.today()
    sessions = AttendanceSession.query.filter_by(
        classroom_id=class_id, session_date=today
    ).order_by(AttendanceSession.session_type).all()

    enrollments = cls.enrollments.filter_by(is_active=True).all()
    enrolled = {enr.student_id: enr for enr in enrollments}   # Dict: student_id -> enrollment

    result_sessions = []
    for sess in sessions:
        records = {r.student_id: r for r in sess.records.all()}   # Dict: student_id -> record
        attended = []
        absent = []

        for sid, enr in enrolled.items():
            stu = enr.student
            profile = stu.student_profile if stu else None
            base = {
                'id': sid,
                'full_name': stu.full_name if stu else '—',
                'student_code': (profile.student_code if profile else None) or enr.student_code,
            }
            if sid in records:
                # Sinh viên đã điểm danh
                r = records[sid]
                base.update({
                    'checkin_time': r.checkin_time.strftime('%H:%M:%S'),
                    'is_late': r.is_late,
                    'distance_meters': round(r.distance_meters, 1) if r.distance_meters is not None else None,
                    'confidence': round(r.face_confidence * 100, 1) if r.face_confidence else None,
                })
                attended.append(base)
            else:
                absent.append(base)   # Sinh viên chưa điểm danh

        result_sessions.append({
            **_session_json(sess),
            'total_enrolled': len(enrolled),
            'total_attended': len(attended),
            'total_late': sum(1 for r in records.values() if r.is_late),
            'attended': attended,
            'absent': absent,
        })

    return jsonify({
        'sessions': result_sessions,
        'total_enrolled': len(enrolled),
    }), 200


# ---------------------------------------------------------------------------
# GET /api/teacher/classes/<id>/attendance/logs — Lịch sử điểm danh
# ---------------------------------------------------------------------------

@teacher_bp.route('/classes/<int:class_id>/attendance/logs', methods=['GET'])
@jwt_required()
def get_attendance_logs(class_id):
    """Lấy toàn bộ lịch sử điểm danh của lớp (tất cả các buổi đã qua)."""
    teacher, err = _require_teacher()
    if err:
        return err
    cls = AppClassroom.query.filter_by(id=class_id, teacher_id=teacher.id).first()
    if not cls:
        return jsonify({'error': 'Không tìm thấy lớp học'}), 404

    sessions = (
        AttendanceSession.query
        .filter_by(classroom_id=class_id)
        .order_by(AttendanceSession.session_date.desc(), AttendanceSession.session_type)
        .all()
    )

    total_enrolled = cls.enrollments.filter_by(is_active=True).count()
    logs = []
    for sess in sessions:
        records = sess.records.all()
        attended = [r for r in records if r.status == 'present']
        logs.append({
            **_session_json(sess),
            'total_enrolled': total_enrolled,
            'total_attended': len(attended),
            'total_late': sum(1 for r in attended if r.is_late),
            'records': [_record_row(r, sess) for r in records],
        })

    return jsonify({'logs': logs, 'total_sessions': len(logs)}), 200


@teacher_bp.route('/logs', methods=['GET'])
@jwt_required()
def get_teacher_logs():
    """Tra ve nhat ky tong hop cho trang /teacher/logs."""
    teacher, err = _require_teacher()
    if err:
        return err

    log_type = (request.args.get('type') or '').strip().lower()
    if log_type not in ('', 'class', 'session', 'attendance'):
        return jsonify({'error': 'type khong hop le'}), 400

    page = max(request.args.get('page', 1, type=int), 1)
    per_page = min(max(request.args.get('per_page', 50, type=int), 1), 100)

    start_dt = end_dt = None
    try:
        from_str = (request.args.get('from') or '').strip()
        to_str = (request.args.get('to') or '').strip()
        if from_str:
            start_dt = datetime.combine(date.fromisoformat(from_str), dtime.min)
        if to_str:
            end_dt = datetime.combine(date.fromisoformat(to_str), dtime.max)
    except ValueError:
        return jsonify({'error': 'Dinh dang ngay khong hop le (YYYY-MM-DD)'}), 400

    def in_range(dt):
        if not dt:
            return True
        if start_dt and dt < start_dt:
            return False
        if end_dt and dt > end_dt:
            return False
        return True

    def fmt_dt(dt):
        return dt.strftime('%d/%m/%Y %H:%M') if dt else ''

    logs = []
    classrooms = teacher.classrooms_owned.all()
    class_by_id = {c.id: c for c in classrooms}
    class_ids = list(class_by_id.keys())

    if log_type in ('', 'class'):
        for cls in classrooms:
            if in_range(cls.created_at):
                logs.append({
                    'created_at': fmt_dt(cls.created_at),
                    'sort_at': cls.created_at,
                    'action': 'Tao lop',
                    'target': cls.name,
                    'detail': f'Ma lop: {cls.class_code}',
                    'status': 'success' if cls.is_active else 'inactive',
                })
            if cls.updated_at and cls.updated_at != cls.created_at and in_range(cls.updated_at):
                logs.append({
                    'created_at': fmt_dt(cls.updated_at),
                    'sort_at': cls.updated_at,
                    'action': 'Cap nhat lop',
                    'target': cls.name,
                    'detail': 'Thong tin lop hoc da duoc cap nhat',
                    'status': 'success' if cls.is_active else 'inactive',
                })

    if class_ids and log_type in ('', 'session'):
        sessions = AttendanceSession.query.filter(
            AttendanceSession.teacher_id == teacher.id,
            AttendanceSession.classroom_id.in_(class_ids),
        ).all()
        for sess in sessions:
            cls = class_by_id.get(sess.classroom_id)
            target = cls.name if cls else f'Lop #{sess.classroom_id}'
            detail = f'{SESSION_TYPE_LABEL.get(sess.session_type, sess.session_type)} - {sess.session_date.isoformat()}'
            if in_range(sess.started_at):
                logs.append({
                    'created_at': fmt_dt(sess.started_at),
                    'sort_at': sess.started_at,
                    'action': 'Mo phien diem danh',
                    'target': target,
                    'detail': detail,
                    'status': 'success' if sess.status == 'open' else 'closed',
                })
            if sess.closed_at and in_range(sess.closed_at):
                logs.append({
                    'created_at': fmt_dt(sess.closed_at),
                    'sort_at': sess.closed_at,
                    'action': 'Dong phien diem danh',
                    'target': target,
                    'detail': detail,
                    'status': 'success',
                })

    if class_ids and log_type in ('', 'attendance'):
        records = (
            AppAttendanceRecord.query
            .join(AttendanceSession, AppAttendanceRecord.session_id == AttendanceSession.id)
            .filter(AttendanceSession.teacher_id == teacher.id)
            .filter(AppAttendanceRecord.classroom_id.in_(class_ids))
            .all()
        )
        for rec in records:
            if not in_range(rec.checkin_time):
                continue
            cls = class_by_id.get(rec.classroom_id)
            stu = rec.student_user
            logs.append({
                'created_at': fmt_dt(rec.checkin_time),
                'sort_at': rec.checkin_time,
                'action': 'Sinh vien diem danh',
                'target': cls.name if cls else f'Lop #{rec.classroom_id}',
                'detail': f'{stu.full_name if stu else "Sinh vien"} - {rec.status}',
                'status': 'success' if rec.status == 'present' else 'failed',
            })

    logs.sort(key=lambda item: item.get('sort_at') or datetime.min, reverse=True)
    total = len(logs)
    start = (page - 1) * per_page
    paged = logs[start:start + per_page]
    for item in paged:
        item.pop('sort_at', None)

    return jsonify({
        'logs': paged,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page,
        },
    }), 200


# ---------------------------------------------------------------------------
# GET /api/teacher/calendar — Sự kiện lịch (FullCalendar)
# ---------------------------------------------------------------------------

# Bảng màu để phân biệt các lớp trên lịch (mỗi lớp một màu)
_PALETTE = [
    '#4e73df', '#1cc88a', '#36b9cc', '#f6c23e',
    '#e74a3b', '#6f42c1', '#fd7e14', '#20c997',
]


@teacher_bp.route('/calendar', methods=['GET'])
@jwt_required()
def get_calendar():
    """
    Trả về danh sách sự kiện tương thích với FullCalendar cho tất cả lớp
    trong khoảng thời gian được yêu cầu.
    Query params: start (YYYY-MM-DD), end (YYYY-MM-DD).
    """
    teacher, err = _require_teacher()
    if err:
        return err

    start_str = request.args.get('start', '')
    end_str   = request.args.get('end', '')

    try:
        range_start = date.fromisoformat(start_str[:10]) if start_str else date.today().replace(day=1)
        range_end   = date.fromisoformat(end_str[:10])   if end_str   else range_start + timedelta(days=41)
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    classrooms = teacher.classrooms_owned.filter_by(is_active=True).all()

    # Tìm tất cả phiên điểm danh trong khoảng thời gian này
    sessions_in_range = AttendanceSession.query.filter(
        AttendanceSession.teacher_id == teacher.id,
        AttendanceSession.session_date >= range_start,
        AttendanceSession.session_date <= range_end,
    ).all()

    # Lập chỉ mục: (classroom_id, ngày) -> [loại phiên đã mở]
    att_index: dict = {}
    for s in sessions_in_range:
        key = (s.classroom_id, s.session_date)
        att_index.setdefault(key, []).append(s.session_type)

    events = []
    for cls_idx, cls in enumerate(classrooms):
        color = _PALETTE[cls_idx % len(_PALETTE)]   # Chọn màu theo chỉ số lớp
        schedules = cls.schedules.filter_by(is_active=True).all()
        if not schedules:
            continue

        sched_by_dow = {s.day_of_week: s for s in schedules}   # Dict: thứ -> lịch
        student_count = cls.enrollments.filter_by(is_active=True).count()

        # Duyệt từng ngày trong khoảng thời gian
        cur = range_start
        while cur <= range_end:
            # Bỏ qua ngày nằm ngoài thời gian của khoá học
            if cls.start_date and cur < cls.start_date:
                cur += timedelta(days=1)
                continue
            if cls.end_date and cur > cls.end_date:
                cur += timedelta(days=1)
                continue

            sched = sched_by_dow.get(cur.weekday())
            if sched:
                day_session_types = att_index.get((cls.id, cur), [])
                events.append({
                    'id': f'cls_{cls.id}_{cur.isoformat()}',
                    'title': cls.name,
                    'start': f'{cur.isoformat()}T{sched.start_time.strftime("%H:%M:%S")}',
                    'end':   f'{cur.isoformat()}T{sched.end_time.strftime("%H:%M:%S")}',
                    'color': color,
                    'extendedProps': {
                        'class_id':           cls.id,
                        'class_code':         cls.class_code,
                        'class_name':         cls.name,
                        'start_time':         sched.start_time.strftime('%H:%M'),
                        'end_time':           sched.end_time.strftime('%H:%M'),
                        'late_after_minutes': sched.late_after_minutes,
                        'student_count':      student_count,
                        'has_start_session':  'start' in day_session_types,  # Đã mở phiên đầu giờ chưa
                        'has_end_session':    'end'   in day_session_types,  # Đã mở phiên cuối giờ chưa
                        'session_types':      day_session_types,
                    },
                })

            cur += timedelta(days=1)

    return jsonify({'events': events}), 200
