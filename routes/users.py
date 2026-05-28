import pickle
import uuid

from flask import Blueprint, jsonify, request

from face_utils import decode_image, embed_frame, retrain_from_db, yolo_has_face
from models import FaceCapture, User, db

users_bp = Blueprint('users', __name__)

# In-memory capture sessions: {session_id: [embedding_np, ...]}
# Sessions are short-lived (registration flow only).
_sessions: dict = {}

MIN_CAPTURES = 20
TARGET_CAPTURES = 30


@users_bp.route('/', methods=['GET'])
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id,
        'full_name': u.full_name,
        'email': u.email,
        'department': u.department,
        'created_at': u.created_at.isoformat(),
    } for u in users])


# ── Registration: step 1 ─ start a capture session ──────────────────────────

@users_bp.route('/session/start', methods=['POST'])
def start_session():
    sid = str(uuid.uuid4())[:8]
    _sessions[sid] = []
    return jsonify({'session_id': sid, 'target': TARGET_CAPTURES, 'min': MIN_CAPTURES})


# ── Registration: step 2 ─ stream frames until TARGET reached ────────────────

@users_bp.route('/session/<sid>/frame', methods=['POST'])
def capture_frame(sid):
    if sid not in _sessions:
        return jsonify({'error': 'Unknown session'}), 404

    current = len(_sessions[sid])
    if current >= TARGET_CAPTURES:
        return jsonify({'detected': False, 'count': current, 'done': True})

    frame_bgr = decode_image(request.data)

    # Fast YOLO gate — skip InsightFace if no face visible
    if not yolo_has_face(frame_bgr):
        return jsonify({'detected': False, 'count': current})

    embedding, crop_b64 = embed_frame(frame_bgr)
    if embedding is None:
        return jsonify({'detected': False, 'count': current})

    _sessions[sid].append(embedding)
    new_count = len(_sessions[sid])

    return jsonify({
        'detected': True,
        'count': new_count,
        'done': new_count >= TARGET_CAPTURES,
        'thumbnail': crop_b64,
    })


# ── Registration: step 3 ─ save user + embeddings, retrain SVM ───────────────

@users_bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()
    sid = data.get('session_id')

    if not sid or sid not in _sessions:
        return jsonify({'error': 'Invalid or missing session_id'}), 400

    embeddings = _sessions.pop(sid)
    if len(embeddings) < MIN_CAPTURES:
        return jsonify({
            'error': f'Not enough face captures ({len(embeddings)}/{MIN_CAPTURES}). Please capture more frames.'
        }), 400

    full_name = (data.get('full_name') or '').strip()
    if not full_name:
        return jsonify({'error': 'full_name is required'}), 400

    user = User(
        full_name=full_name,
        email=data.get('email') or None,
        department=data.get('department') or None,
    )
    db.session.add(user)
    db.session.flush()  # populate user.id before inserting captures

    for emb in embeddings:
        db.session.add(FaceCapture(user_id=user.id, embedding=pickle.dumps(emb)))

    db.session.commit()

    stats = retrain_from_db()
    return jsonify({
        'message': 'User registered successfully',
        'id': user.id,
        'captures_saved': len(embeddings),
        'classifier': stats,
    }), 201


# ── Delete user + their captures, then retrain ────────────────────────────────

@users_bp.route('/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    FaceCapture.query.filter_by(user_id=user_id).delete()
    db.session.delete(user)
    db.session.commit()
    retrain_from_db()
    return jsonify({'message': 'User deleted'})
