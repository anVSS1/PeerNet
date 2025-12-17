'''
PeerNet++ Authentication API
============================
REST API endpoints for user authentication.

Endpoints:
- POST /auth/register: Create new user account
- POST /auth/login: Authenticate and create session
- POST /auth/logout: Destroy current session
- GET /auth/me: Get current user info

Security:
- Passwords hashed with bcrypt
- Session-based authentication
- CSRF protection via Flask-WTF
'''

from flask import Blueprint, request, jsonify, session
from models.users import User
from utils.logger import get_logger

auth_bp = Blueprint('auth', __name__)
logger = get_logger(__name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        
        if not all([username, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400
        
        if User.objects(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400
        
        if User.objects(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400
        
        user = User(username=username, email=email)
        user.set_password(password)
        user.save()
        
        session['user_id'] = str(user.id)
        return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not all([username, password]):
            return jsonify({'error': 'Missing username or password'}), 400
        
        user = User.objects(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session['user_id'] = str(user.id)
        return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200
        
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@auth_bp.route('/logout', methods=['POST'])
def logout():
    session.clear()
    logger.info("User logged out successfully")
    return jsonify({'message': 'Logged out successfully'}), 200

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = User.objects(id=user_id).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user.to_dict()}), 200