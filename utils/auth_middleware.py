from functools import wraps
from flask import session, redirect, url_for, request
from models.users import User

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('dashboard.login_page'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return User.objects(id=user_id).first()

def check_auth():
    """Check if user is authenticated"""
    return 'user_id' in session

def require_auth():
    """Redirect to login if not authenticated"""
    if not check_auth():
        return redirect(url_for('dashboard.login_page'))
    return None