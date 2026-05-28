from datetime import date, datetime, timedelta

from flask import Blueprint, jsonify, request

from face_utils import identify_face
from models import Attendance, User, db

recognition_bp = Blueprint('recognition', __name__)


@recognition_bp.route('/frame', methods=['POST'])
def process_frame():
    user_id, confidence = identify_face(request.data)

    if user_id is None:
        return jsonify({'status': 'unknown'})

    user = User.query.get(user_id)
    if not user:
        return jsonify({'status': 'unknown'})

    cutoff = datetime.utcnow() - timedelta(minutes=30)
    recent = (Attendance.query
              .filter_by(user_id=user_id)
              .filter(Attendance.check_in_time >= cutoff)
              .first())

    if recent:
        return jsonify({'status': 'duplicate', 'name': user.full_name})

    db.session.add(Attendance(user_id=user_id, date=date.today()))
    db.session.commit()

    return jsonify({
        'status': 'success',
        'name': user.full_name,
        'department': user.department,
        'confidence': confidence,
        'time': datetime.now().strftime('%H:%M:%S'),
    })
