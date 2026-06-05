"""Face recognition model training routes."""
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime
import os

from face_utils import retrain_svm
from models import db, FaceEmbedding, FaceModel, Student
from utils.decorators import permission_required
from config.permissions import PERM_MANAGE_MODELS

training_bp = Blueprint('training', __name__)


@training_bp.route('/train', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_MODELS)
def train_model():
    """
    Train a new face recognition model from registered student embeddings.
    
    Optional parameters (JSON):
    - version: Version string for the new model (default: auto-generated timestamp)
    - algorithm: Algorithm to use ('SVM' or 'cosine', default: 'SVM')
    - set_active: Whether to set this model as active immediately (default: True)
    
    Returns training statistics and model information.
    """
    data = request.get_json() or {}
    
    # Get active embeddings grouped by student
    embeddings_query = db.session.query(
        FaceEmbedding.student_id,
        FaceEmbedding.embedding_vector
    ).filter(
        FaceEmbedding.is_active == True
    ).all()
    
    if not embeddings_query:
        return jsonify({
            'error': 'No face embeddings found',
            'message': 'Please register student faces before training a model'
        }), 400
    
    # Group embeddings by student_id
    import pickle
    embeddings_by_student = {}
    for student_id, emb_bytes in embeddings_query:
        embedding = pickle.loads(emb_bytes)
        embeddings_by_student.setdefault(student_id, []).append(embedding)
    
    num_students = len(embeddings_by_student)
    num_embeddings = sum(len(embs) for embs in embeddings_by_student.values())
    
    if num_students == 0:
        return jsonify({
            'error': 'No students with face embeddings',
            'message': 'At least one student must be registered'
        }), 400
    
    # Train the model
    algorithm = data.get('algorithm', 'SVM')
    success = retrain_svm(embeddings_by_student)
    
    if not success:
        return jsonify({
            'error': 'Model training failed',
            'message': 'Unable to train model with current data'
        }), 500
    
    # Create FaceModel record
    version = data.get('version', datetime.utcnow().strftime('%Y%m%d_%H%M%S'))
    set_active = data.get('set_active', True)
    
    # If setting as active, deactivate other models
    if set_active:
        FaceModel.query.update({'is_active': False})
    
    from face_utils import SVM_PATH
    new_model = FaceModel(
        model_name=f'FaceRecognitionModel_{version}',
        version=version,
        algorithm=algorithm,
        model_file_path=SVM_PATH,
        is_active=set_active,
        trained_at=datetime.utcnow(),
        training_stats={
            'num_students': num_students,
            'num_embeddings': num_embeddings,
            'students_list': list(embeddings_by_student.keys())
        }
    )
    db.session.add(new_model)
    db.session.commit()
    
    return jsonify({
        'message': f'Model trained successfully',
        'model': {
            'id': new_model.id,
            'version': new_model.version,
            'algorithm': new_model.algorithm,
            'is_active': new_model.is_active,
            'trained_at': new_model.trained_at.isoformat()
        },
        'training_stats': {
            'num_students': num_students,
            'num_embeddings': num_embeddings,
            'model_path': SVM_PATH
        }
    }), 201


@training_bp.route('/models', methods=['GET'])
@jwt_required()
@permission_required(PERM_MANAGE_MODELS)
def list_models():
    """
    List all trained face recognition models.
    Shows model history and version information.
    """
    models = FaceModel.query.order_by(FaceModel.trained_at.desc()).all()
    
    result = []
    for model in models:
        result.append({
            'id': model.id,
            'model_name': model.model_name,
            'version': model.version,
            'algorithm': model.algorithm,
            'accuracy': model.accuracy,
            'is_active': model.is_active,
            'trained_at': model.trained_at.isoformat(),
            'training_stats': model.training_stats
        })
    
    return jsonify({
        'total': len(result),
        'models': result
    }), 200


@training_bp.route('/models/<int:model_id>/activate', methods=['POST'])
@jwt_required()
@permission_required(PERM_MANAGE_MODELS)
def activate_model(model_id):
    """
    Set a specific model as the active model for recognition.
    Deactivates all other models.
    """
    model = FaceModel.query.get_or_404(model_id)
    
    # Deactivate all models
    FaceModel.query.update({'is_active': False})
    
    # Activate the selected model
    model.is_active = True
    db.session.commit()
    
    return jsonify({
        'message': f'Model {model.version} is now active',
        'model': {
            'id': model.id,
            'version': model.version,
            'algorithm': model.algorithm,
            'trained_at': model.trained_at.isoformat()
        }
    }), 200


@training_bp.route('/models/<int:model_id>', methods=['DELETE'])
@jwt_required()
@permission_required(PERM_MANAGE_MODELS)
def delete_model(model_id):
    """
    Delete a face recognition model.
    Cannot delete the currently active model.
    """
    model = FaceModel.query.get_or_404(model_id)
    
    if model.is_active:
        return jsonify({
            'error': 'Cannot delete active model',
            'message': 'Please activate a different model before deleting this one'
        }), 400
    
    # Check if model has associated attendance records
    if model.attendance_records.count() > 0:
        return jsonify({
            'error': 'Cannot delete model with attendance records',
            'message': f'This model has {model.attendance_records.count()} attendance records'
        }), 400
    
    db.session.delete(model)
    db.session.commit()
    
    return jsonify({
        'message': f'Model {model.version} deleted successfully'
    }), 200


@training_bp.route('/status', methods=['GET'])
def training_status():
    """
    Get current training system status.
    Public endpoint for checking if the system is ready.
    """
    from face_utils import SVM_PATH
    
    active_model = FaceModel.query.filter_by(is_active=True).first()
    total_models = FaceModel.query.count()
    
    # Count students with embeddings
    enrolled_students = db.session.query(Student.id).join(
        FaceEmbedding, FaceEmbedding.student_id == Student.id
    ).filter(FaceEmbedding.is_active == True).distinct().count()
    
    total_embeddings = FaceEmbedding.query.filter_by(is_active=True).count()
    
    return jsonify({
        'model_ready': os.path.exists(SVM_PATH),
        'active_model': {
            'id': active_model.id,
            'version': active_model.version,
            'algorithm': active_model.algorithm,
            'trained_at': active_model.trained_at.isoformat(),
            'training_stats': active_model.training_stats
        } if active_model else None,
        'total_models': total_models,
        'enrolled_students': enrolled_students,
        'total_embeddings': total_embeddings,
        'system_status': 'ready' if active_model and os.path.exists(SVM_PATH) else 'needs_training'
    }), 200