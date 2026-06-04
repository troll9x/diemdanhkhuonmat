from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = 'users'
    id            = db.Column(db.Integer, primary_key=True)
    full_name     = db.Column(db.String(100), nullable=False)
    email         = db.Column(db.String(120), unique=True)
    department    = db.Column(db.String(100))
    created_at    = db.Column(db.DateTime, default=datetime.utcnow)
    attendances   = db.relationship('Attendance', backref='user', lazy=True)
    face_captures = db.relationship('FaceCapture', backref='user', lazy=True)


class FaceCapture(db.Model):
    """One ArcFace embedding per captured webcam frame per student."""
    __tablename__ = 'face_captures'
    id          = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    embedding   = db.Column(db.LargeBinary, nullable=False)   # pickled float32[512]
    captured_at = db.Column(db.DateTime, default=datetime.utcnow)


class Attendance(db.Model):
    __tablename__ = 'attendance'
    id            = db.Column(db.Integer, primary_key=True)
    user_id       = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    check_in_time = db.Column(db.DateTime, default=datetime.utcnow)
    date          = db.Column(db.Date, default=datetime.utcnow().date)
    status        = db.Column(db.String(20), default='present')
