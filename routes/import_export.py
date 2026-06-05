"""Routes for bulk import and export operations."""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
import os
from datetime import datetime
from io import BytesIO
import csv

from models import db, Student, Lecturer, Department, Administrator, AuditLog
from utils.decorators import admin_only, permission_required
from utils.csv_import import (
    parse_csv_file,
    validate_required_fields,
    clean_string,
    parse_date,
    parse_integer,
    validate_email,
    validate_phone,
    generate_import_result,
)
from config.settings import Config

import_export_bp = Blueprint('import_export', __name__, url_prefix='/api/import-export')

# Allowed file extensions
ALLOWED_EXTENSIONS = {'csv'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def log_audit(user_id, action, entity_name, details=None):
    """Log audit trail."""
    try:
        admin = Administrator.query.get(user_id)
        if admin:
            audit = AuditLog(
                user_id=user_id,
                user_type='admin',
                action=action,
                entity_name=entity_name,
                new_data=details,
            )
            db.session.add(audit)
            db.session.commit()
    except Exception as e:
        print(f"Error logging audit: {e}")


@import_export_bp.route('/students/template', methods=['GET'])
@jwt_required()
@admin_only
def get_student_import_template():
    """Get CSV template for student import."""
    output = BytesIO()
    writer = csv.writer(output)
    
    # Write header
    headers = [
        'student_code',
        'full_name',
        'email',
        'department_id',
        'major_id',
        'program_id',
        'year_of_admission',
        'phone',
    ]
    writer.writerow(headers)
    
    # Write example row
    writer.writerow([
        'SV001',
        'Nguyễn Văn A',
        'sv001@example.com',
        '1',
        '1',
        '1',
        '2023',
        '0912345678',
    ])
    
    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='student_import_template.csv'
    )


@import_export_bp.route('/students/import', methods=['POST'])
@jwt_required()
@admin_only
def import_students():
    """
    Bulk import students from CSV file.
    
    CSV columns required:
    - student_code (required, unique)
    - full_name (required)
    - email (required, unique)
    - department_id (required)
    - major_id (optional)
    - program_id (optional)
    - year_of_admission (optional)
    - phone (optional)
    
    Returns:
        {
            "total": 10,
            "success": 9,
            "failed": 1,
            "success_rate": 90.0,
            "errors": [
                {
                    "row": 2,
                    "reason": "Email already exists"
                }
            ]
        }
    """
    current_user_id = get_jwt_identity()
    
    # Check if file provided
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files are allowed'}), 400
    
    # Read file content
    file_content = file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 10MB limit'}), 400
    
    try:
        # Parse CSV
        headers, rows = parse_csv_file(file_content)
        
        if not rows:
            return jsonify({'error': 'CSV file is empty'}), 400
        
        # Validate headers
        required_fields = ['student_code', 'full_name', 'email', 'department_id']
        if not all(field in headers for field in required_fields):
            missing = [f for f in required_fields if f not in headers]
            return jsonify({
                'error': f'Missing required columns: {", ".join(missing)}'
            }), 400
        
        errors = []
        success_count = 0
        total_rows = len(rows)
        
        for row_num, row in enumerate(rows, start=2):  # Start from 2 (skip header)
            try:
                # Validate required fields
                is_valid, missing = validate_required_fields(row, required_fields)
                if not is_valid:
                    errors.append({
                        'row': row_num,
                        'reason': f'Missing fields: {", ".join(missing)}'
                    })
                    continue
                
                # Validate email
                email = clean_string(row.get('email', ''))
                if not validate_email(email):
                    errors.append({
                        'row': row_num,
                        'reason': f'Invalid email format: {email}'
                    })
                    continue
                
                # Check email uniqueness
                existing = Student.query.filter_by(email=email).first()
                if existing:
                    errors.append({
                        'row': row_num,
                        'reason': f'Email already exists: {email}'
                    })
                    continue
                
                # Check student_code uniqueness
                student_code = clean_string(row.get('student_code', ''))
                existing = Student.query.filter_by(student_code=student_code).first()
                if existing:
                    errors.append({
                        'row': row_num,
                        'reason': f'Student code already exists: {student_code}'
                    })
                    continue
                
                # Validate phone
                phone = clean_string(row.get('phone', ''))
                if phone and not validate_phone(phone):
                    errors.append({
                        'row': row_num,
                        'reason': f'Invalid phone format: {phone}'
                    })
                    continue
                
                # Validate department exists
                department_id = parse_integer(row.get('department_id', ''))
                if not department_id:
                    errors.append({
                        'row': row_num,
                        'reason': 'Invalid department_id'
                    })
                    continue
                
                dept = Department.query.get(department_id)
                if not dept:
                    errors.append({
                        'row': row_num,
                        'reason': f'Department not found: {department_id}'
                    })
                    continue
                
                # Parse optional fields
                major_id = parse_integer(row.get('major_id', ''))
                program_id = parse_integer(row.get('program_id', ''))
                year_of_admission = parse_integer(row.get('year_of_admission', ''))
                
                # Create student
                student = Student(
                    student_code=student_code,
                    full_name=clean_string(row.get('full_name', '')),
                    email=email,
                    department_id=department_id,
                    major_id=major_id,
                    program_id=program_id,
                    year_of_admission=year_of_admission,
                    phone=phone,
                    password_hash='',  # Will be hashed on first login
                    is_active=True,
                )
                
                db.session.add(student)
                db.session.flush()
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': row_num,
                    'reason': f'Error: {str(e)}'
                })
        
        # Commit all changes
        db.session.commit()
        
        # Log audit
        log_audit(
            current_user_id,
            'import',
            'Student',
            {
                'total': total_rows,
                'success': success_count,
                'failed': len(errors),
            }
        )
        
        result = generate_import_result(
            total_rows,
            success_count,
            len(errors),
            errors
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to import file: {str(e)}'}), 400


@import_export_bp.route('/lecturers/template', methods=['GET'])
@jwt_required()
@admin_only
def get_lecturer_import_template():
    """Get CSV template for lecturer import."""
    output = BytesIO()
    writer = csv.writer(output)
    
    # Write header
    headers = [
        'lecturer_code',
        'full_name',
        'email',
        'department_id',
        'phone',
    ]
    writer.writerow(headers)
    
    # Write example row
    writer.writerow([
        'GV001',
        'Trần Văn B',
        'gv001@example.com',
        '1',
        '0912345678',
    ])
    
    output.seek(0)
    return send_file(
        output,
        mimetype='text/csv',
        as_attachment=True,
        download_name='lecturer_import_template.csv'
    )


@import_export_bp.route('/lecturers/import', methods=['POST'])
@jwt_required()
@admin_only
def import_lecturers():
    """
    Bulk import lecturers from CSV file.
    
    CSV columns required:
    - lecturer_code (required, unique)
    - full_name (required)
    - email (required, unique)
    - department_id (required)
    - phone (optional)
    
    Returns:
        {
            "total": 10,
            "success": 9,
            "failed": 1,
            "success_rate": 90.0,
            "errors": [...]
        }
    """
    current_user_id = get_jwt_identity()
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only CSV files are allowed'}), 400
    
    file_content = file.read()
    
    if len(file_content) > MAX_FILE_SIZE:
        return jsonify({'error': 'File size exceeds 10MB limit'}), 400
    
    try:
        headers, rows = parse_csv_file(file_content)
        
        if not rows:
            return jsonify({'error': 'CSV file is empty'}), 400
        
        required_fields = ['lecturer_code', 'full_name', 'email', 'department_id']
        if not all(field in headers for field in required_fields):
            missing = [f for f in required_fields if f not in headers]
            return jsonify({
                'error': f'Missing required columns: {", ".join(missing)}'
            }), 400
        
        errors = []
        success_count = 0
        total_rows = len(rows)
        
        for row_num, row in enumerate(rows, start=2):
            try:
                # Validate required fields
                is_valid, missing = validate_required_fields(row, required_fields)
                if not is_valid:
                    errors.append({
                        'row': row_num,
                        'reason': f'Missing fields: {", ".join(missing)}'
                    })
                    continue
                
                # Validate email
                email = clean_string(row.get('email', ''))
                if not validate_email(email):
                    errors.append({
                        'row': row_num,
                        'reason': f'Invalid email format: {email}'
                    })
                    continue
                
                # Check email uniqueness
                existing = Lecturer.query.filter_by(email=email).first()
                if existing:
                    errors.append({
                        'row': row_num,
                        'reason': f'Email already exists: {email}'
                    })
                    continue
                
                # Check lecturer_code uniqueness
                lecturer_code = clean_string(row.get('lecturer_code', ''))
                existing = Lecturer.query.filter_by(lecturer_code=lecturer_code).first()
                if existing:
                    errors.append({
                        'row': row_num,
                        'reason': f'Lecturer code already exists: {lecturer_code}'
                    })
                    continue
                
                # Validate phone
                phone = clean_string(row.get('phone', ''))
                if phone and not validate_phone(phone):
                    errors.append({
                        'row': row_num,
                        'reason': f'Invalid phone format: {phone}'
                    })
                    continue
                
                # Validate department exists
                department_id = parse_integer(row.get('department_id', ''))
                if not department_id:
                    errors.append({
                        'row': row_num,
                        'reason': 'Invalid department_id'
                    })
                    continue
                
                dept = Department.query.get(department_id)
                if not dept:
                    errors.append({
                        'row': row_num,
                        'reason': f'Department not found: {department_id}'
                    })
                    continue
                
                # Create lecturer
                lecturer = Lecturer(
                    lecturer_code=lecturer_code,
                    full_name=clean_string(row.get('full_name', '')),
                    email=email,
                    department_id=department_id,
                    phone=phone,
                    password_hash='',
                    is_active=True,
                )
                
                db.session.add(lecturer)
                db.session.flush()
                success_count += 1
                
            except Exception as e:
                errors.append({
                    'row': row_num,
                    'reason': f'Error: {str(e)}'
                })
        
        db.session.commit()
        
        log_audit(
            current_user_id,
            'import',
            'Lecturer',
            {
                'total': total_rows,
                'success': success_count,
                'failed': len(errors),
            }
        )
        
        result = generate_import_result(
            total_rows,
            success_count,
            len(errors),
            errors
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Failed to import file: {str(e)}'}), 400


@import_export_bp.route('/students/export', methods=['GET'])
@jwt_required()
@admin_only
def export_students():
    """Export all students to CSV file."""
    try:
        current_user_id = get_jwt_identity()
        
        # Get all students
        students = Student.query.filter_by(is_deleted=False).all()
        
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'student_code',
            'full_name',
            'email',
            'department_id',
            'major_id',
            'program_id',
            'year_of_admission',
            'phone',
            'is_active',
            'face_registered',
        ]
        writer.writerow(headers)
        
        # Write data
        for student in students:
            writer.writerow([
                student.student_code,
                student.full_name,
                student.email,
                student.department_id,
                student.major_id or '',
                student.program_id or '',
                student.year_of_admission or '',
                student.phone or '',
                'Yes' if student.is_active else 'No',
                'Yes' if student.face_registered else 'No',
            ])
        
        output.seek(0)
        
        log_audit(current_user_id, 'export', 'Student', {'count': len(students)})
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'students_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'error': f'Failed to export: {str(e)}'}), 400


@import_export_bp.route('/lecturers/export', methods=['GET'])
@jwt_required()
@admin_only
def export_lecturers():
    """Export all lecturers to CSV file."""
    try:
        current_user_id = get_jwt_identity()
        
        # Get all lecturers
        lecturers = Lecturer.query.filter_by(is_deleted=False).all()
        
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write header
        headers = [
            'lecturer_code',
            'full_name',
            'email',
            'department_id',
            'phone',
            'is_active',
        ]
        writer.writerow(headers)
        
        # Write data
        for lecturer in lecturers:
            writer.writerow([
                lecturer.lecturer_code,
                lecturer.full_name,
                lecturer.email,
                lecturer.department_id,
                lecturer.phone or '',
                'Yes' if lecturer.is_active else 'No',
            ])
        
        output.seek(0)
        
        log_audit(current_user_id, 'export', 'Lecturer', {'count': len(lecturers)})
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'lecturers_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
    except Exception as e:
        return jsonify({'error': f'Failed to export: {str(e)}'}), 400
