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

import re as _re
from flask import Blueprint, request, jsonify, session
from models.users import User
from utils.security import SecurityManager
from utils.logger import get_logger

auth_bp = Blueprint('auth', __name__)
logger = get_logger(__name__)

# Shared SecurityManager for rate limiting
_security = SecurityManager()

# ── Password policy ──────────────────────────────────────────────
_MIN_PASSWORD_LENGTH = 8

def _validate_password(password: str) -> str | None:
    """Return an error message if the password is too weak, else None."""
    if len(password) < _MIN_PASSWORD_LENGTH:
        return f'Password must be at least {_MIN_PASSWORD_LENGTH} characters'
    if not _re.search(r'[A-Z]', password):
        return 'Password must contain at least one uppercase letter'
    if not _re.search(r'[a-z]', password):
        return 'Password must contain at least one lowercase letter'
    if not _re.search(r'[0-9]', password):
        return 'Password must contain at least one digit'
    return None

@auth_bp.route('/register', methods=['POST'])
@_security.rate_limit(max_requests=5, window_minutes=15)
def register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        username = (data.get('username') or '').strip()
        email = (data.get('email') or '').strip()
        password = data.get('password') or ''

        if not all([username, email, password]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Username validation
        if not _re.match(r'^[a-zA-Z0-9_]{3,30}$', username):
            return jsonify({'error': 'Username must be 3-30 alphanumeric characters or underscores'}), 400

        # Email validation
        if not _re.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', email):
            return jsonify({'error': 'Invalid email format'}), 400

        # Password strength check
        pw_error = _validate_password(password)
        if pw_error:
            return jsonify({'error': pw_error}), 400

        if User.objects(username=username).first():
            return jsonify({'error': 'Username already exists'}), 400

        if User.objects(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        user = User(username=username, email=email)
        user.set_password(password)
        user.save()

        # Prevent session fixation: clear old session data before setting new identity
        session.clear()
        session['user_id'] = str(user.id)
        return jsonify({'message': 'User created successfully', 'user': user.to_dict()}), 201

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed. Please try again.'}), 500

@auth_bp.route('/login', methods=['POST'])
@_security.rate_limit(max_requests=10, window_minutes=15)
def login():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Invalid request body'}), 400

        username = (data.get('username') or '').strip()
        password = data.get('password') or ''

        if not all([username, password]):
            return jsonify({'error': 'Missing username or password'}), 400

        user = User.objects(username=username).first()
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401

        # Prevent session fixation: regenerate session on login
        session.clear()
        session['user_id'] = str(user.id)
        return jsonify({'message': 'Login successful', 'user': user.to_dict()}), 200

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed. Please try again.'}), 500

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