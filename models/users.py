'''
PeerNet++ User Model
====================
User authentication and profile data.

Key Fields:
- username: Unique login name
- email: Unique email address
- password_hash: Werkzeug hashed password
- preferences: User settings dict
- is_active: Account enabled flag

Methods:
- set_password(): Hash and store password
- check_password(): Verify password hash
'''

from mongoengine import Document, StringField, EmailField, DateTimeField, BooleanField, DictField
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(Document):
    username = StringField(required=True, unique=True, max_length=50)
    email = EmailField(required=True, unique=True)
    password_hash = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    is_active = BooleanField(default=True)
    preferences = DictField(default=dict)
    
    meta = {'collection': 'users'}
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'username': self.username,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_active': self.is_active,
            'preferences': self.preferences
        }