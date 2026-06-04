"""Class schedule management routes."""
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import time

from models import db, ClassSchedule, Classroom, Subject, Room
from utils.decorators import permission_required
from config.permissions import (
    PERM_CREATE_CLASS_SCHEDULE,
    PERM_VIEW_CLASS_SCHEDULES,
    PERM_UPDATE_CLASS_SCHEDULE,
    PERM_DELETE_CLASS_SCHEDULE
)

class_schedules_bp = Blueprint('class_schedules', __name__)

@class_schedules_bp.route('/', methods=['POST'])
@jwt_required()
@permission_required(PERM_CREATE_CLASS_SCHEDULE)
def create_class_schedule():
    """Create a new class schedule entry."""
    data = request.get_json()
    
    classroom_id = data.get('classroom_id')
    subject_id = data.get('subject_id')
    room_id = data.get('room_id')
    day_of_week = data.get('day_of_week')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')

    if not all([classroom_id, subject_id, day_of_week, start_time_str, end_time_str]):
        return jsonify({"error": "Missing required fields"}), 400

    # Validate foreign keys
    if not Classroom.query.get(classroom_id):
        return jsonify({"error": "Classroom not found"}), 404
    if not Subject.query.get(subject_id):
        return jsonify({"error": "Subject not found"}), 404
    if room_id and not Room.query.get(room_id):
        return jsonify({"error": "Room not found"}), 404

    try:
        start_time = time.fromisoformat(start_time_str)
        end_time = time.fromisoformat(end_time_str)
    except ValueError:
        return jsonify({"error": "Invalid time format. Use HH:MM:SS"}), 400

    if not (1 <= day_of_week <= 7):
        return jsonify({"error": "Day of week must be between 1 (Monday) and 7 (Sunday)"}), 400
    
    if start_time >= end_time:
        return jsonify({"error": "Start time must be before end time"}), 400

    # Check for room conflicts (optional for now, will implement later)
    # For now, just create the schedule

    new_schedule = ClassSchedule(
        classroom_id=classroom_id,
        subject_id=subject_id,
        room_id=room_id,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        is_active=data.get('is_active', True)
    )
    db.session.add(new_schedule)
    db.session.commit()
    
    return jsonify({
        "message": "Class schedule created successfully",
        "id": new_schedule.id,
        "classroom_id": new_schedule.classroom_id,
        "subject_id": new_schedule.subject_id,
        "room_id": new_schedule.room_id,
        "day_of_week": new_schedule.day_of_week,
        "start_time": new_schedule.start_time.isoformat(),
        "end_time": new_schedule.end_time.isoformat(),
        "is_active": new_schedule.is_active
    }), 201

@class_schedules_bp.route('/', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_CLASS_SCHEDULES)
def get_class_schedules():
    """Retrieve all class schedules."""
    schedules = ClassSchedule.query.all()
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "classroom_id": s.classroom.id if s.classroom else None,
            "classroom_name": s.classroom.class_name if s.classroom else None,
            "subject_id": s.subject.id if s.subject else None,
            "subject_name": s.subject.subject_name if s.subject else None,
            "room_id": s.room.id if s.room else None,
            "room_name": s.room.name if s.room else None,
            "day_of_week": s.day_of_week,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "is_active": s.is_active
        })
    return jsonify(result), 200

@class_schedules_bp.route('/<int:schedule_id>', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_CLASS_SCHEDULES)
def get_class_schedule(schedule_id):
    """Retrieve a single class schedule by ID."""
    schedule = ClassSchedule.query.get_or_404(schedule_id)
    return jsonify({
        "id": schedule.id,
        "classroom_id": schedule.classroom.id if schedule.classroom else None,
        "classroom_name": schedule.classroom.class_name if schedule.classroom else None,
        "subject_id": schedule.subject.id if schedule.subject else None,
        "subject_name": schedule.subject.subject_name if schedule.subject else None,
        "room_id": schedule.room.id if schedule.room else None,
        "room_name": schedule.room.name if schedule.room else None,
        "day_of_week": schedule.day_of_week,
        "start_time": schedule.start_time.isoformat(),
        "end_time": schedule.end_time.isoformat(),
        "is_active": schedule.is_active
    }), 200

@class_schedules_bp.route('/<int:schedule_id>', methods=['PUT'])
@jwt_required()
@permission_required(PERM_UPDATE_CLASS_SCHEDULE)
def update_class_schedule(schedule_id):
    """Update an existing class schedule."""
    schedule = ClassSchedule.query.get_or_404(schedule_id)
    data = request.get_json()

    classroom_id = data.get('classroom_id')
    subject_id = data.get('subject_id')
    room_id = data.get('room_id')
    day_of_week = data.get('day_of_week')
    start_time_str = data.get('start_time')
    end_time_str = data.get('end_time')
    is_active = data.get('is_active')

    if classroom_id:
        if not Classroom.query.get(classroom_id):
            return jsonify({"error": "Classroom not found"}), 404
        schedule.classroom_id = classroom_id
    
    if subject_id:
        if not Subject.query.get(subject_id):
            return jsonify({"error": "Subject not found"}), 404
        schedule.subject_id = subject_id
    
    if room_id is not None: # Allow setting room_id to None
        if room_id and not Room.query.get(room_id):
            return jsonify({"error": "Room not found"}), 404
        schedule.room_id = room_id
    
    if day_of_week is not None:
        if not (1 <= day_of_week <= 7):
            return jsonify({"error": "Day of week must be between 1 (Monday) and 7 (Sunday)"}), 400
        schedule.day_of_week = day_of_week
    
    if start_time_str:
        try:
            schedule.start_time = time.fromisoformat(start_time_str)
        except ValueError:
            return jsonify({"error": "Invalid start_time format. Use HH:MM:SS"}), 400
    
    if end_time_str:
        try:
            schedule.end_time = time.fromisoformat(end_time_str)
        except ValueError:
            return jsonify({"error": "Invalid end_time format. Use HH:MM:SS"}), 400

    if schedule.start_time >= schedule.end_time:
        return jsonify({"error": "Start time must be before end time"}), 400

    if is_active is not None:
        schedule.is_active = is_active

    db.session.commit()
    return jsonify({"message": "Class schedule updated successfully"}), 200

@class_schedules_bp.route('/<int:schedule_id>', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_DELETE_CLASS_SCHEDULE)
def delete_class_schedule(schedule_id):
    """Delete a class schedule."""
    schedule = ClassSchedule.query.get_or_404(schedule_id)
    db.session.delete(schedule)
    db.session.commit()
    return jsonify({"message": "Class schedule deleted successfully"}), 200

@class_schedules_bp.route('/by-classroom/<int:classroom_id>', methods=['GET'])
@jwt_required()
@permission_required(PERM_VIEW_CLASS_SCHEDULES)
def get_schedules_by_classroom(classroom_id):
    """Retrieve class schedules for a specific classroom."""
    classroom = Classroom.query.get_or_404(classroom_id)
    schedules = classroom.schedules.all()
    result = []
    for s in schedules:
        result.append({
            "id": s.id,
            "classroom_id": s.classroom.id if s.classroom else None,
            "classroom_name": s.classroom.class_name if s.classroom else None,
            "subject_id": s.subject.id if s.subject else None,
            "subject_name": s.subject.subject_name if s.subject else None,
            "room_id": s.room.id if s.room else None,
            "room_name": s.room.name if s.room else None,
            "day_of_week": s.day_of_week,
            "start_time": s.start_time.isoformat(),
            "end_time": s.end_time.isoformat(),
            "is_active": s.is_active
        })
    return jsonify(result), 200