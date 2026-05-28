from flask import Blueprint, jsonify

from face_utils import retrain_from_db

training_bp = Blueprint('training', __name__)


@training_bp.route('/train', methods=['POST'])
def train():
    stats = retrain_from_db()
    if stats['users'] == 0:
        return jsonify({'error': 'No face captures in database. Register students first.'}), 400

    return jsonify({
        'message': f"SVM retrained on {stats['captures']} captures from {stats['users']} student(s).",
        'users': stats['users'],
        'captures': stats['captures'],
    })


@training_bp.route('/status', methods=['GET'])
def status():
    import os
    from face_utils import SVM_PATH
    from models import FaceCapture, User

    return jsonify({
        'model_ready': os.path.exists(SVM_PATH),
        'enrolled_users': User.query.count(),
        'total_captures': FaceCapture.query.count(),
    })
