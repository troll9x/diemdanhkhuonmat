from flask import Blueprint, jsonify, request
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

# Simple hardcoded admin for local demo — no real auth needed
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if data.get('username') == ADMIN_USER and data.get('password') == ADMIN_PASS:
        token = create_access_token(identity='admin')
        return jsonify({'token': token})
    return jsonify({'error': 'Invalid credentials'}), 401