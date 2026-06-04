"""Classroom management routes."""
from flask import Blueprint, jsonify, request
from models import (
    db, Classroom, Student, Subject, Lecturer,
    ClassroomStudent, ClassroomSubject, Semester, AcademicYear
)
from utils.decorators import jwt_required, admin_only
from utils.pagination import paginate
from middleware.rate_limit import limiter
from datetime import datetime

classrooms_bp = Blueprint('classrooms', __name__)


def _cls_dict(cls, include_lists=False):
    """Serialize a Classroom to dict using correct model field names."""
    students_count = ClassroomStudent.query.filter_by(classroom_id=cls.id).count()
    subjects_count = ClassroomSubject.query.filter_by(classroom_id=cls.id).count()

    d = {
        'id': cls.id,
        'code': cls.class_code,
        'name': cls.class_name,
        'is_active': cls.is_active,
        'lecturer': {
            'id': cls.lecturer.id,
            'full_name': cls.lecturer.full_name,
            'lecturer_code': cls.lecturer.lecturer_code,
            'email': cls.lecturer.email,
        } if cls.lecturer else None,
        'room': None,
        'students_count': students_count,
        'subjects_count': subjects_count,
        'created_at': cls.created_at.isoformat(),
        'updated_at': cls.updated_at.isoformat(),
    }
    if include_lists:
        cs_rows = ClassroomStudent.query.filter_by(classroom_id=cls.id).all()
        students = []
        for row in cs_rows:
            s = row.student
            if s and not s.is_deleted:
                students.append({'id': s.id, 'student_code': s.student_code, 'full_name': s.full_name, 'email': s.email})
        d['students'] = students

        csubj_rows = ClassroomSubject.query.filter_by(classroom_id=cls.id).all()
        subjects = []
        for row in csubj_rows:
            s = row.subject
            if s and not s.is_deleted:
                subjects.append({'id': s.id, 'subject_code': s.subject_code, 'subject_name': s.subject_name, 'credits': s.credits})
        d['subjects'] = subjects
    return d


@classrooms_bp.route('', methods=['GET'])
@jwt_required
def list_classrooms():
    """List all classrooms with pagination and filters."""
    search = request.args.get('search', '').strip()
    lecturer_id = request.args.get('lecturer_id', type=int)
    is_active = request.args.get('is_active', 'true').lower() == 'true'

    query = Classroom.query.filter_by(is_deleted=False)

    if is_active is not None:
        query = query.filter_by(is_active=is_active)
    if lecturer_id:
        query = query.filter_by(lecturer_id=lecturer_id)
    if search:
        query = query.filter(
            (Classroom.class_name.ilike(f'%{search}%')) |
            (Classroom.class_code.ilike(f'%{search}%'))
        )

    result = paginate(query)
    items = [_cls_dict(cls) for cls in result['items']]
    return jsonify({'items': items, 'pagination': result['pagination']}), 200


@classrooms_bp.route('/<int:id>', methods=['GET'])
@jwt_required
def get_classroom(id):
    """Get single classroom with full details."""
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404
    return jsonify(_cls_dict(cls, include_lists=True)), 200


@classrooms_bp.route('', methods=['POST'])
@admin_only
@limiter.limit("10 per minute")
def create_classroom():
    """Create new classroom (Admin only)."""
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    code = (data.get('code') or data.get('class_code') or '').strip().upper()
    name = (data.get('name') or data.get('class_name') or '').strip()

    if not code or not name:
        return jsonify({'error': 'Missing required fields: code, name'}), 400

    if Classroom.query.filter_by(class_code=code, is_deleted=False).first():
        return jsonify({'error': f'Classroom code "{code}" already exists'}), 409

    lecturer_id = data.get('lecturer_id') or None
    if lecturer_id:
        if not Lecturer.query.filter_by(id=lecturer_id, is_deleted=False, is_active=True).first():
            return jsonify({'error': 'Lecturer not found'}), 404

    # Use provided or current semester/academic_year (required FK, try to get defaults)
    semester_id = data.get('semester_id') or None
    academic_year_id = data.get('academic_year_id') or None

    if not semester_id:
        current = Semester.query.filter_by(is_current=True, is_active=True).first()
        if not current:
            current = Semester.query.filter_by(is_active=True).order_by(Semester.id.desc()).first()
        if current:
            semester_id = current.id

    if not academic_year_id:
        current = AcademicYear.query.filter_by(is_current=True, is_active=True).first()
        if not current:
            current = AcademicYear.query.filter_by(is_active=True).order_by(AcademicYear.id.desc()).first()
        if current:
            academic_year_id = current.id

    try:
        cls = Classroom(
            class_code=code,
            class_name=name,
            lecturer_id=lecturer_id,
            semester_id=semester_id,
            academic_year_id=academic_year_id,
            is_active=data.get('is_active', True)
        )
        db.session.add(cls)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Could not create classroom: {str(e)}'}), 400

    return jsonify({
        'message': 'Classroom created successfully',
        'classroom': _cls_dict(cls)
    }), 201


@classrooms_bp.route('/<int:id>', methods=['PUT'])
@admin_only
@limiter.limit("10 per minute")
def update_classroom(id):
    """Update classroom (Admin only)."""
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400

    if 'code' in data or 'class_code' in data:
        new_code = (data.get('code') or data.get('class_code', '')).strip().upper()
        if new_code and new_code != cls.class_code:
            if Classroom.query.filter_by(class_code=new_code, is_deleted=False).first():
                return jsonify({'error': f'Classroom code "{new_code}" already exists'}), 409
            cls.class_code = new_code

    if 'name' in data or 'class_name' in data:
        new_name = (data.get('name') or data.get('class_name', '')).strip()
        if new_name:
            cls.class_name = new_name

    if 'lecturer_id' in data:
        lid = data['lecturer_id']
        if lid:
            if not Lecturer.query.filter_by(id=lid, is_deleted=False, is_active=True).first():
                return jsonify({'error': 'Lecturer not found'}), 404
        cls.lecturer_id = lid

    if 'is_active' in data:
        cls.is_active = bool(data['is_active'])

    cls.updated_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Classroom updated successfully', 'classroom': _cls_dict(cls)}), 200


@classrooms_bp.route('/<int:id>', methods=['DELETE'])
@admin_only
@limiter.limit("5 per minute")
def delete_classroom(id):
    """Soft delete classroom (Admin only)."""
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    cls.is_deleted = True
    cls.deleted_at = datetime.utcnow()
    db.session.commit()
    return jsonify({'message': 'Classroom deleted successfully'}), 200


# ── Student management ────────────────────────────────────────────────────────

@classrooms_bp.route('/<int:id>/students', methods=['GET'])
@jwt_required
def get_classroom_students(id):
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    rows = ClassroomStudent.query.filter_by(classroom_id=id).all()
    students = []
    for row in rows:
        s = row.student
        if s and not s.is_deleted:
            students.append({'id': s.id, 'student_code': s.student_code, 'full_name': s.full_name, 'email': s.email})

    return jsonify({
        'classroom': {'id': cls.id, 'code': cls.class_code, 'name': cls.class_name},
        'students': students,
        'count': len(students)
    }), 200


@classrooms_bp.route('/<int:id>/students', methods=['POST'])
@admin_only
@limiter.limit("20 per minute")
def add_students_to_classroom(id):
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    data = request.get_json()
    if not data or 'student_ids' not in data:
        return jsonify({'error': 'student_ids array is required'}), 400

    student_ids = data['student_ids']
    if not isinstance(student_ids, list):
        return jsonify({'error': 'student_ids must be an array'}), 400

    added, skipped = [], []
    for student_id in student_ids:
        student = Student.query.filter_by(id=student_id, is_deleted=False, is_active=True).first()
        if not student:
            skipped.append({'id': student_id, 'reason': 'Student not found or inactive'})
            continue
        if ClassroomStudent.query.filter_by(classroom_id=id, student_id=student_id).first():
            skipped.append({'id': student_id, 'reason': 'Already in classroom'})
            continue
        db.session.add(ClassroomStudent(classroom_id=id, student_id=student_id))
        added.append({'id': student.id, 'student_code': student.student_code, 'full_name': student.full_name})

    db.session.commit()
    return jsonify({'message': f'Added {len(added)} students', 'added': added, 'skipped': skipped}), 200


@classrooms_bp.route('/<int:id>/students/<int:student_id>', methods=['DELETE'])
@admin_only
def remove_student_from_classroom(id, student_id):
    if not Classroom.query.filter_by(id=id, is_deleted=False).first():
        return jsonify({'error': 'Classroom not found'}), 404
    link = ClassroomStudent.query.filter_by(classroom_id=id, student_id=student_id).first()
    if not link:
        return jsonify({'error': 'Student not in classroom'}), 404
    db.session.delete(link)
    db.session.commit()
    return jsonify({'message': 'Student removed from classroom'}), 200


# ── Subject management ────────────────────────────────────────────────────────

@classrooms_bp.route('/<int:id>/subjects', methods=['GET'])
@jwt_required
def get_classroom_subjects(id):
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    rows = ClassroomSubject.query.filter_by(classroom_id=id).all()
    subjects = []
    for row in rows:
        s = row.subject
        if s and not s.is_deleted:
            subjects.append({'id': s.id, 'subject_code': s.subject_code, 'subject_name': s.subject_name, 'credits': s.credits})

    return jsonify({
        'classroom': {'id': cls.id, 'code': cls.class_code, 'name': cls.class_name},
        'subjects': subjects,
        'count': len(subjects)
    }), 200


@classrooms_bp.route('/<int:id>/subjects', methods=['POST'])
@admin_only
@limiter.limit("20 per minute")
def add_subjects_to_classroom(id):
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404

    data = request.get_json()
    if not data or 'subject_ids' not in data:
        return jsonify({'error': 'subject_ids array is required'}), 400

    subject_ids = data['subject_ids']
    if not isinstance(subject_ids, list):
        return jsonify({'error': 'subject_ids must be an array'}), 400

    added, skipped = [], []
    for subject_id in subject_ids:
        subject = Subject.query.filter_by(id=subject_id, is_deleted=False, is_active=True).first()
        if not subject:
            skipped.append({'id': subject_id, 'reason': 'Subject not found or inactive'})
            continue
        if ClassroomSubject.query.filter_by(classroom_id=id, subject_id=subject_id).first():
            skipped.append({'id': subject_id, 'reason': 'Already in classroom'})
            continue
        db.session.add(ClassroomSubject(classroom_id=id, subject_id=subject_id))
        added.append({'id': subject.id, 'subject_code': subject.subject_code, 'subject_name': subject.subject_name})

    db.session.commit()
    return jsonify({'message': f'Added {len(added)} subjects', 'added': added, 'skipped': skipped}), 200


@classrooms_bp.route('/<int:id>/subjects/<int:subject_id>', methods=['DELETE'])
@admin_only
def remove_subject_from_classroom(id, subject_id):
    if not Classroom.query.filter_by(id=id, is_deleted=False).first():
        return jsonify({'error': 'Classroom not found'}), 404
    link = ClassroomSubject.query.filter_by(classroom_id=id, subject_id=subject_id).first()
    if not link:
        return jsonify({'error': 'Subject not in classroom'}), 404
    db.session.delete(link)
    db.session.commit()
    return jsonify({'message': 'Subject removed from classroom'}), 200


@classrooms_bp.route('/<int:id>/activate', methods=['POST'])
@admin_only
def activate_classroom(id):
    cls = Classroom.query.filter_by(id=id, is_deleted=False).first()
    if not cls:
        return jsonify({'error': 'Classroom not found'}), 404
    cls.is_active = not cls.is_active
    db.session.commit()
    status = 'activated' if cls.is_active else 'deactivated'
    return jsonify({'message': f'Classroom {status}', 'is_active': cls.is_active}), 200
