import io
import pickle
from datetime import date, datetime, timedelta

import pandas as pd
from flask import Blueprint, jsonify, request, send_file

from models import Attendance, User, db

attendance_bp = Blueprint('attendance', __name__)


@attendance_bp.route('/', methods=['GET'])
def get_attendance():
    date_filter = request.args.get('date')
    dept_filter = request.args.get('department')
    user_filter = request.args.get('user_id')

    query = db.session.query(Attendance, User).join(User)

    if date_filter:
        query = query.filter(Attendance.date == date_filter)
    if dept_filter:
        query = query.filter(User.department == dept_filter)
    if user_filter:
        query = query.filter(Attendance.user_id == user_filter)

    records = query.order_by(Attendance.check_in_time.desc()).all()

    return jsonify([{
        'id': a.id,
        'user_id': a.user_id,
        'name': u.full_name,
        'department': u.department,
        'date': a.date.isoformat(),
        'time': a.check_in_time.strftime('%H:%M:%S'),
        'status': a.status
    } for a, u in records])


@attendance_bp.route('/stats', methods=['GET'])
def get_stats():
    total_users = User.query.count()
    today = date.today()
    today_count = Attendance.query.filter_by(date=today).count()

    return jsonify({
        'total_users': total_users,
        'today_count': today_count,
        'date': today.isoformat()
    })


@attendance_bp.route('/export', methods=['GET'])
def export_csv():
    records = db.session.query(Attendance, User).join(User).all()

    data = [{
        'Name': u.full_name,
        'Department': u.department,
        'Date': a.date,
        'Time': a.check_in_time.strftime('%H:%M:%S'),
        'Status': a.status
    } for a, u in records]

    df = pd.DataFrame(data)
    buf = io.BytesIO()
    df.to_csv(buf, index=False)
    buf.seek(0)

    return send_file(buf, mimetype='text/csv',
                     download_name='attendance.csv', as_attachment=True)