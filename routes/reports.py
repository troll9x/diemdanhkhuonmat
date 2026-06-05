"""Routes for attendance reports and exports."""
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from io import BytesIO
import csv
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_RIGHT

from models import (
    db, AttendanceRecord, ClassSession, ClassSchedule, Student, 
    Lecturer, Classroom, Subject, Administrator, AuditLog
)
from utils.decorators import admin_or_lecturer_required, permission_required
from config.permissions import PERM_VIEW_REPORTS, PERM_EXPORT_ALL_REPORTS, PERM_EXPORT_OWN_REPORTS

reports_bp = Blueprint('reports', __name__, url_prefix='/api/reports')


# ==================== ATTENDANCE LIST ====================

@reports_bp.route('/attendance', methods=['GET'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS])
def list_attendance_records():
    """
    List attendance records with filters and pagination.
    Query params: start_date, end_date, classroom_id, subject_id, student_id, status, page, per_page
    """
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 50, type=int), 200)
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        classroom_id = request.args.get('classroom_id', type=int)
        subject_id = request.args.get('subject_id', type=int)
        student_id = request.args.get('student_id', type=int)
        status = request.args.get('status')

        query = AttendanceRecord.query

        if student_id:
            query = query.filter(AttendanceRecord.student_id == student_id)
        if status:
            query = query.filter(AttendanceRecord.status == status)

        # Filter by date/classroom through sessions
        session_filter_needed = start_date or end_date or classroom_id or subject_id
        if session_filter_needed:
            sess_q = ClassSession.query
            if start_date:
                sess_q = sess_q.filter(ClassSession.session_date >= start_date)
            if end_date:
                sess_q = sess_q.filter(ClassSession.session_date <= end_date)
            if classroom_id:
                sess_q = sess_q.filter(ClassSession.classroom_id == classroom_id)
            if subject_id:
                sess_q = sess_q.filter(ClassSession.subject_id == subject_id)
            session_ids = [s.id for s in sess_q.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))

        query = query.order_by(AttendanceRecord.attendance_time.desc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        records = []
        for att in pagination.items:
            session = ClassSession.query.get(att.session_id) if att.session_id else None
            student = Student.query.get(att.student_id) if att.student_id else None
            classroom = Classroom.query.get(session.classroom_id) if session else None
            subject = Subject.query.get(session.subject_id) if session else None

            records.append({
                'id': att.id,
                'student_code': student.student_code if student else 'N/A',
                'student_name': student.full_name if student else 'N/A',
                'classroom_name': classroom.class_name if classroom else 'N/A',
                'subject_name': subject.subject_name if subject else 'N/A',
                'session_date': session.session_date.isoformat() if session else None,
                'attendance_time': att.attendance_time.strftime('%H:%M:%S') if att.attendance_time else None,
                'status': att.status,
                'confidence_score': round(att.confidence_score * 100, 1) if att.confidence_score else None,
            })

        # Summary counts across entire filtered result set (not just page)
        all_atts = query.all() if page == 1 else query.paginate(page=1, per_page=99999, error_out=False).items
        total = len(all_atts)
        present = sum(1 for a in all_atts if a.status == 'present')
        late = sum(1 for a in all_atts if a.status == 'late')
        absent = sum(1 for a in all_atts if a.status == 'absent')

        return jsonify({
            'records': records,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            },
            'summary': {
                'total': pagination.total,
                'present': present,
                'late': late,
                'absent': absent,
                'rate': round((present + late) / total * 100, 1) if total > 0 else 0
            }
        })
    except Exception as e:
        return jsonify({'error': f'Failed to list attendance: {str(e)}'}), 400


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


# ==================== EXCEL EXPORT ====================

@reports_bp.route('/attendance/excel', methods=['POST'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS, PERM_EXPORT_ALL_REPORTS, PERM_EXPORT_OWN_REPORTS])
def export_attendance_excel():
    """
    Export attendance report to Excel file.
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        classroom_id = data.get('classroom_id')
        session_id = data.get('session_id')
        lecturer_id = data.get('lecturer_id')
        
        # Build query
        query = AttendanceRecord.query
        
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        elif classroom_id:
            sessions = ClassSession.query.filter_by(classroom_id=classroom_id)
            if start_date:
                sessions = sessions.filter(ClassSession.session_date >= start_date)
            if end_date:
                sessions = sessions.filter(ClassSession.session_date <= end_date)
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        else:
            if start_date or end_date:
                sessions = ClassSession.query
                if start_date:
                    sessions = sessions.filter(ClassSession.session_date >= start_date)
                if end_date:
                    sessions = sessions.filter(ClassSession.session_date <= end_date)
                session_ids = [s.id for s in sessions.all()]
                query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        if lecturer_id:
            sessions = ClassSession.query.join(ClassSchedule).filter(
                ClassSchedule.lecturer_id == lecturer_id
            )
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        attendances = query.all()
        
        # Create Excel file
        output = BytesIO()
        
        # Create workbook with multiple sheets
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Summary sheet
            summary_data = {
                'Metric': ['Total Records', 'Present', 'Absent', 'Late', 'Excused', 'Attendance Rate'],
                'Value': [
                    len(attendances),
                    sum(1 for a in attendances if a.status == 'present'),
                    sum(1 for a in attendances if a.status == 'absent'),
                    sum(1 for a in attendances if a.status == 'late'),
                    sum(1 for a in attendances if a.status == 'excused'),
                    f"{(sum(1 for a in attendances if a.status in ['present', 'late']) / len(attendances) * 100):.1f}%" if attendances else "0%"
                ]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed attendance sheet
            detailed_data = []
            for att in attendances:
                session = ClassSession.query.get(att.session_id)
                student = Student.query.get(att.student_id)
                classroom = Classroom.query.get(session.classroom_id) if session else None
                subject = Subject.query.get(classroom.subject_id) if classroom else None
                
                detailed_data.append({
                    'Student Code': student.student_code if student else 'N/A',
                    'Student Name': student.full_name if student else 'N/A',
                    'Subject': subject.name if subject else 'N/A',
                    'Classroom': classroom.name if classroom else 'N/A',
                    'Session Date': session.session_date.strftime('%Y-%m-%d') if session else 'N/A',
                    'Check-in Time': att.attendance_time.strftime('%H:%M:%S') if att.attendance_time else 'N/A',
                    'Status': att.status.capitalize(),
                    'Notes': att.notes or '',
                })
            
            pd.DataFrame(detailed_data).to_excel(writer, sheet_name='Detailed', index=False)
            
            # Student summary sheet
            student_summary = {}
            for att in attendances:
                student = Student.query.get(att.student_id)
                if student:
                    key = (student.student_code, student.full_name)
                    if key not in student_summary:
                        student_summary[key] = {'total': 0, 'present': 0, 'late': 0, 'absent': 0}
                    student_summary[key]['total'] += 1
                    if att.status == 'present':
                        student_summary[key]['present'] += 1
                    elif att.status == 'late':
                        student_summary[key]['late'] += 1
                    elif att.status == 'absent':
                        student_summary[key]['absent'] += 1
            
            summary_data = []
            for (code, name), stats in student_summary.items():
                rate = ((stats['present'] + stats['late']) / stats['total'] * 100) if stats['total'] > 0 else 0
                summary_data.append({
                    'Student Code': code,
                    'Student Name': name,
                    'Total Sessions': stats['total'],
                    'Present': stats['present'],
                    'Late': stats['late'],
                    'Absent': stats['absent'],
                    'Attendance Rate': f"{rate:.1f}%"
                })
            pd.DataFrame(summary_data).to_excel(writer, sheet_name='By Student', index=False)
        
        output.seek(0)
        
        log_audit(current_user_id, 'export', 'Attendance Report (Excel)', {
            'format': 'xlsx',
            'records': len(attendances)
        })
        
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to export Excel: {str(e)}'}), 400


# ==================== PDF EXPORT ====================

@reports_bp.route('/attendance/pdf', methods=['POST'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS, PERM_EXPORT_ALL_REPORTS, PERM_EXPORT_OWN_REPORTS])
def export_attendance_pdf():
    """
    Export attendance report to PDF file.
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        classroom_id = data.get('classroom_id')
        session_id = data.get('session_id')
        
        # Build query
        query = AttendanceRecord.query
        
        if session_id:
            query = query.filter(AttendanceRecord.session_id == session_id)
        elif classroom_id:
            sessions = ClassSession.query.filter_by(classroom_id=classroom_id)
            if start_date:
                sessions = sessions.filter(ClassSession.session_date >= start_date)
            if end_date:
                sessions = sessions.filter(ClassSession.session_date <= end_date)
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        else:
            if start_date or end_date:
                sessions = ClassSession.query
                if start_date:
                    sessions = sessions.filter(ClassSession.session_date >= start_date)
                if end_date:
                    sessions = sessions.filter(ClassSession.session_date <= end_date)
                session_ids = [s.id for s in sessions.all()]
                query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        attendances = query.all()
        
        # Create PDF
        output = BytesIO()
        doc = SimpleDocTemplate(output, pagesize=landscape(A4))
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=20
        )
        
        # Title
        elements.append(Paragraph("Attendance Report", title_style))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            subtitle_style
        ))
        
        # Summary statistics
        total = len(attendances)
        present = sum(1 for a in attendances if a.status == 'present')
        late = sum(1 for a in attendances if a.status == 'late')
        absent = sum(1 for a in attendances if a.status == 'absent')
        excused = sum(1 for a in attendances if a.status == 'excused')
        rate = ((present + late) / total * 100) if total > 0 else 0
        
        summary_data = [
            ['Total', 'Present', 'Late', 'Absent', 'Excused', 'Rate'],
            [str(total), str(present), str(late), str(absent), str(excused), f"{rate:.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[1*inch] * 6)
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#D9E2F3')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
        
        # Detailed table
        table_data = [['#', 'Student Code', 'Name', 'Date', 'Time', 'Status']]
        for i, att in enumerate(attendances[:50], 1):  # Limit to 50 rows
            session = ClassSession.query.get(att.session_id)
            student = Student.query.get(att.student_id)
            table_data.append([
                str(i),
                student.student_code if student else 'N/A',
                student.full_name if student else 'N/A',
                session.session_date.strftime('%Y-%m-%d') if session else 'N/A',
                att.attendance_time.strftime('%H:%M') if att.attendance_time else 'N/A',
                att.status.capitalize()
            ])
        
        if len(attendances) > 50:
            table_data.append(['...', '...', f'{len(attendances) - 50} more records', '...', '...', '...'])
        
        detail_table = Table(table_data, colWidths=[0.5*inch, 1.2*inch, 2*inch, 1.2*inch, 1*inch, 1*inch])
        detail_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4472C4')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F2F2F2')])
        ]))
        elements.append(detail_table)
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Total records: {len(attendances)}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, alignment=TA_RIGHT)
        ))
        
        doc.build(elements)
        output.seek(0)
        
        log_audit(current_user_id, 'export', 'Attendance Report (PDF)', {
            'format': 'pdf',
            'records': len(attendances)
        })
        
        return send_file(
            output,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf'
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to export PDF: {str(e)}'}), 400


# ==================== ADVANCED CSV EXPORT ====================

@reports_bp.route('/attendance/csv', methods=['POST'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS, PERM_EXPORT_ALL_REPORTS, PERM_EXPORT_OWN_REPORTS])
def export_attendance_csv():
    """
    Export attendance report to CSV with advanced filters.
    """
    try:
        current_user_id = get_jwt_identity()
        data = request.get_json() or {}
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        classroom_id = data.get('classroom_id')
        status_filter = data.get('status')
        include_stats = data.get('include_stats', False)
        group_by = data.get('group_by')  # student, date, classroom
        
        # Build query
        query = AttendanceRecord.query
        
        if classroom_id:
            sessions = ClassSession.query.filter_by(classroom_id=classroom_id)
            if start_date:
                sessions = sessions.filter(ClassSession.session_date >= start_date)
            if end_date:
                sessions = sessions.filter(ClassSession.session_date <= end_date)
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        else:
            if start_date or end_date:
                sessions = ClassSession.query
                if start_date:
                    sessions = sessions.filter(ClassSession.session_date >= start_date)
                if end_date:
                    sessions = sessions.filter(ClassSession.session_date <= end_date)
                session_ids = [s.id for s in sessions.all()]
                query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        if status_filter:
            query = query.filter(AttendanceRecord.status == status_filter)
        
        attendances = query.all()
        
        output = BytesIO()
        writer = csv.writer(output)
        
        # Write summary if requested
        if include_stats:
            writer.writerow(['=== ATTENDANCE SUMMARY ==='])
            writer.writerow(['Generated', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
            writer.writerow(['Total Records', len(attendances)])
            writer.writerow(['Present', sum(1 for a in attendances if a.status == 'present')])
            writer.writerow(['Late', sum(1 for a in attendances if a.status == 'late')])
            writer.writerow(['Absent', sum(1 for a in attendances if a.status == 'absent')])
            writer.writerow(['Excused', sum(1 for a in attendances if a.status == 'excused')])
            rate = (sum(1 for a in attendances if a.status in ['present', 'late']) / len(attendances) * 100) if attendances else 0
            writer.writerow(['Attendance Rate', f"{rate:.2f}%"])
            writer.writerow([])  # Empty row separator
        
        # Group data if requested
        if group_by == 'student':
            # Group by student
            student_data = {}
            for att in attendances:
                student = Student.query.get(att.student_id)
                if student:
                    key = student.id
                    if key not in student_data:
                        student_data[key] = {
                            'code': student.student_code,
                            'name': student.full_name,
                            'total': 0,
                            'present': 0,
                            'late': 0,
                            'absent': 0,
                            'excused': 0
                        }
                    student_data[key]['total'] += 1
                    student_data[key][att.status] += 1
            
            writer.writerow(['=== ATTENDANCE BY STUDENT ==='])
            writer.writerow(['Student Code', 'Student Name', 'Total', 'Present', 'Late', 'Absent', 'Excused', 'Rate'])
            for sd in student_data.values():
                rate = ((sd['present'] + sd['late']) / sd['total'] * 100) if sd['total'] > 0 else 0
                writer.writerow([
                    sd['code'], sd['name'], sd['total'],
                    sd['present'], sd['late'], sd['absent'], sd['excused'],
                    f"{rate:.2f}%"
                ])
        
        elif group_by == 'date':
            # Group by date
            date_data = {}
            for att in attendances:
                session = ClassSession.query.get(att.session_id)
                if session:
                    date_key = session.session_date.strftime('%Y-%m-%d')
                    if date_key not in date_data:
                        date_data[date_key] = {'total': 0, 'present': 0, 'late': 0, 'absent': 0, 'excused': 0}
                    date_data[date_key]['total'] += 1
                    date_data[date_key][att.status] += 1
            
            writer.writerow(['=== ATTENDANCE BY DATE ==='])
            writer.writerow(['Date', 'Total', 'Present', 'Late', 'Absent', 'Excused', 'Rate'])
            for date_key in sorted(date_data.keys()):
                dd = date_data[date_key]
                rate = ((dd['present'] + dd['late']) / dd['total'] * 100) if dd['total'] > 0 else 0
                writer.writerow([
                    date_key, dd['total'], dd['present'], dd['late'], dd['absent'], dd['excused'],
                    f"{rate:.2f}%"
                ])
        
        elif group_by == 'classroom':
            # Group by classroom
            classroom_data = {}
            for att in attendances:
                session = ClassSession.query.get(att.session_id)
                if session:
                    classroom = Classroom.query.get(session.classroom_id)
                    if classroom:
                        key = classroom.id
                        if key not in classroom_data:
                            classroom_data[key] = {
                                'name': classroom.name,
                                'total': 0, 'present': 0, 'late': 0, 'absent': 0, 'excused': 0
                            }
                        classroom_data[key]['total'] += 1
                        classroom_data[key][att.status] += 1
            
            writer.writerow(['=== ATTENDANCE BY CLASSROOM ==='])
            writer.writerow(['Classroom', 'Total', 'Present', 'Late', 'Absent', 'Excused', 'Rate'])
            for cd in classroom_data.values():
                rate = ((cd['present'] + cd['late']) / cd['total'] * 100) if cd['total'] > 0 else 0
                writer.writerow([
                    cd['name'], cd['total'], cd['present'], cd['late'], cd['absent'], cd['excused'],
                    f"{rate:.2f}%"
                ])
        
        else:
            # Detailed export
            writer.writerow(['=== DETAILED ATTENDANCE ==='])
            writer.writerow(['Student Code', 'Student Name', 'Classroom', 'Subject', 'Date', 'Check-in Time', 'Status', 'Notes'])
            for att in attendances:
                session = ClassSession.query.get(att.session_id)
                student = Student.query.get(att.student_id)
                classroom = Classroom.query.get(session.classroom_id) if session else None
                subject = Subject.query.get(classroom.subject_id) if classroom else None
                
                writer.writerow([
                    student.student_code if student else 'N/A',
                    student.full_name if student else 'N/A',
                    classroom.name if classroom else 'N/A',
                    subject.name if subject else 'N/A',
                    session.session_date.strftime('%Y-%m-%d') if session else 'N/A',
                    att.attendance_time.strftime('%H:%M:%S') if att.attendance_time else 'N/A',
                    att.status,
                    att.notes or ''
                ])
        
        output.seek(0)
        
        log_audit(current_user_id, 'export', 'Attendance Report (CSV)', {
            'format': 'csv',
            'records': len(attendances),
            'group_by': group_by
        })
        
        return send_file(
            output,
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'attendance_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        
    except Exception as e:
        return jsonify({'error': f'Failed to export CSV: {str(e)}'}), 400


# ==================== REPORT STATISTICS ====================

@reports_bp.route('/statistics', methods=['GET'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS])
def get_report_statistics():
    """
    Get attendance statistics overview.
    """
    try:
        # Get date range from query params
        days = request.args.get('days', 30, type=int)
        start_date = datetime.now() - timedelta(days=days)
        
        # Query attendance in date range
        sessions = ClassSession.query.filter(ClassSession.session_date >= start_date)
        session_ids = [s.id for s in sessions.all()]
        
        attendances = AttendanceRecord.query.filter(AttendanceRecord.session_id.in_(session_ids)).all() if session_ids else []
        
        # Calculate statistics
        total = len(attendances)
        present = sum(1 for a in attendances if a.status == 'present')
        late = sum(1 for a in attendances if a.status == 'late')
        absent = sum(1 for a in attendances if a.status == 'absent')
        excused = sum(1 for a in attendances if a.status == 'excused')
        
        # Daily breakdown
        daily_stats = {}
        for att in attendances:
            session = ClassSession.query.get(att.session_id)
            if session:
                date_key = session.session_date.strftime('%Y-%m-%d')
                if date_key not in daily_stats:
                    daily_stats[date_key] = {'total': 0, 'present': 0, 'late': 0, 'absent': 0}
                daily_stats[date_key]['total'] += 1
                if att.status in ['present', 'late', 'absent']:
                    daily_stats[date_key][att.status] += 1
        
        return jsonify({
            'period': {
                'days': days,
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': datetime.now().strftime('%Y-%m-%d')
            },
            'summary': {
                'total_records': total,
                'present': present,
                'late': late,
                'absent': absent,
                'excused': excused,
                'attendance_rate': f"{((present + late) / total * 100):.2f}%" if total > 0 else "0%"
            },
            'daily': [
                {'date': date, **stats}
                for date, stats in sorted(daily_stats.items())
            ]
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get statistics: {str(e)}'}), 400


# ==================== STUDENT ATTENDANCE REPORT ====================

@reports_bp.route('/student/<int:student_id>', methods=['GET'])
@jwt_required()
@permission_required([PERM_VIEW_REPORTS])
def get_student_attendance_report(student_id):
    """
    Get detailed attendance report for a specific student.
    """
    try:
        student = Student.query.get_or_404(student_id)
        
        # Get query params
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        # Build query
        query = AttendanceRecord.query.filter_by(student_id=student_id)
        
        if start_date:
            sessions = ClassSession.query.filter(ClassSession.session_date >= start_date)
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        if end_date:
            sessions = ClassSession.query.filter(ClassSession.session_date <= end_date)
            session_ids = [s.id for s in sessions.all()]
            query = query.filter(AttendanceRecord.session_id.in_(session_ids))
        
        attendances = query.all()
        
        # Calculate statistics
        total = len(attendances)
        present = sum(1 for a in attendances if a.status == 'present')
        late = sum(1 for a in attendances if a.status == 'late')
        absent = sum(1 for a in attendances if a.status == 'absent')
        excused = sum(1 for a in attendances if a.status == 'excused')
        
        # Detailed records
        records = []
        for att in attendances:
            session = ClassSession.query.get(att.session_id)
            classroom = Classroom.query.get(session.classroom_id) if session else None
            subject = Subject.query.get(classroom.subject_id) if classroom else None
            
            records.append({
                'id': att.id,
                'session_date': session.session_date.strftime('%Y-%m-%d') if session else None,
                'classroom': classroom.name if classroom else None,
                'subject': subject.name if subject else None,
                'attendance_time': att.attendance_time.strftime('%H:%M:%S') if att.attendance_time else None,
                'status': att.status,
                'notes': att.notes
            })
        
        return jsonify({
            'student': {
                'id': student.id,
                'student_code': student.student_code,
                'full_name': student.full_name
            },
            'statistics': {
                'total_sessions': total,
                'present': present,
                'late': late,
                'absent': absent,
                'excused': excused,
                'attendance_rate': f"{((present + late) / total * 100):.2f}%" if total > 0 else "0%"
            },
            'records': records
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get student report: {str(e)}'}), 400