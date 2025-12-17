'''
PeerNet++ Reviewers API
=======================
REST API endpoints for custom reviewer management.

Endpoints:
- GET /reviewers: List available reviewer templates
- GET /reviewers/custom: List user's custom reviewers
- POST /reviewers/custom: Create custom reviewer
- PUT /reviewers/custom/<id>: Update custom reviewer
- DELETE /reviewers/custom/<id>: Delete custom reviewer

Custom reviewers allow users to define their own
AI reviewer personalities with specific traits.
'''

from flask import Blueprint, request, jsonify, session
from models.custom_reviewers import CustomReviewer
from models.users import User
from utils.logger import get_logger
from api.prompts import reviewer_templates

reviewers_bp = Blueprint('reviewers', __name__)
logger = get_logger(__name__)

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.objects(id=user_id).first()

@reviewers_bp.route('', methods=['GET'])
def get_user_reviewers():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    reviewers = CustomReviewer.objects(user=user)
    return jsonify({'reviewers': [r.to_dict() for r in reviewers]}), 200

@reviewers_bp.route('', methods=['POST'])
def create_reviewer():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        
        reviewer = CustomReviewer(
            user=user,
            name=data.get('name', 'Unnamed Reviewer'),
            avatar=data.get('avatar', 'default'),
            strictness=float(data.get('strictness', 0.5)),
            detail_focus=float(data.get('detail_focus', 0.5)),
            innovation_bias=float(data.get('innovation_bias', 0.5)),
            writing_standards=float(data.get('writing_standards', 0.5)),
            methodology_rigor=float(data.get('methodology_rigor', 0.5)),
            optimism=float(data.get('optimism', 0.5)),
            expertise=data.get('expertise', 'methodology')
        )
        reviewer.save()
        
        return jsonify({'message': 'Reviewer created', 'reviewer': reviewer.to_dict()}), 201
        
    except Exception as e:
        logger.error(f"Error creating reviewer: {str(e)}")
        return jsonify({'error': 'Failed to create reviewer'}), 500

@reviewers_bp.route('/<reviewer_id>', methods=['PUT'])
def update_reviewer(reviewer_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        reviewer = CustomReviewer.objects(id=reviewer_id, user=user).first()
        if not reviewer:
            return jsonify({'error': 'Reviewer not found'}), 404
        
        data = request.get_json()
        
        reviewer.name = data.get('name', reviewer.name)
        reviewer.avatar = data.get('avatar', reviewer.avatar)
        reviewer.strictness = float(data.get('strictness', reviewer.strictness))
        reviewer.detail_focus = float(data.get('detail_focus', reviewer.detail_focus))
        reviewer.innovation_bias = float(data.get('innovation_bias', reviewer.innovation_bias))
        reviewer.writing_standards = float(data.get('writing_standards', reviewer.writing_standards))
        reviewer.methodology_rigor = float(data.get('methodology_rigor', reviewer.methodology_rigor))
        reviewer.optimism = float(data.get('optimism', reviewer.optimism))
        reviewer.expertise = data.get('expertise', reviewer.expertise)
        reviewer.save()
        
        return jsonify({'message': 'Reviewer updated', 'reviewer': reviewer.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Error updating reviewer: {str(e)}")
        return jsonify({'error': 'Failed to update reviewer'}), 500

@reviewers_bp.route('/<reviewer_id>', methods=['DELETE'])
def delete_reviewer(reviewer_id):
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        reviewer = CustomReviewer.objects(id=reviewer_id, user=user).first()
        if not reviewer:
            return jsonify({'error': 'Reviewer not found'}), 404
        
        reviewer.delete()
        return jsonify({'message': 'Reviewer deleted'}), 200
        
    except Exception as e:
        logger.error(f"Error deleting reviewer: {str(e)}")
        return jsonify({'error': 'Failed to delete reviewer'}), 500

@reviewers_bp.route('/templates', methods=['GET'])
def get_default_templates():
    return jsonify({'templates': reviewer_templates}), 200

@reviewers_bp.route('/preferences', methods=['GET'])
def get_reviewer_preferences():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    prefs = user.preferences.get('reviewer_config', {
        'num_reviewers': 5,
        'selected_reviewers': []
    })
    return jsonify({'preferences': prefs}), 200

@reviewers_bp.route('/preferences', methods=['POST'])
def save_reviewer_preferences():
    user = get_current_user()
    if not user:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        data = request.get_json()
        
        if not user.preferences:
            user.preferences = {}
        
        user.preferences['reviewer_config'] = {
            'num_reviewers': int(data.get('num_reviewers', 5)),
            'selected_reviewers': data.get('selected_reviewers', [])
        }
        user.save()
        
        return jsonify({'message': 'Preferences saved successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error saving preferences: {str(e)}")
        return jsonify({'error': 'Failed to save preferences'}), 500