from mongoengine import Document, StringField, ReferenceField, FloatField, DateTimeField, DictField
from datetime import datetime
from models.users import User

class CustomReviewer(Document):
    user = ReferenceField(User, required=True)
    name = StringField(required=True, max_length=100)
    avatar = StringField(default='default')
    
    # Personality traits (0.0 to 1.0)
    strictness = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    detail_focus = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    innovation_bias = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    writing_standards = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    methodology_rigor = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    optimism = FloatField(min_value=0.0, max_value=1.0, default=0.5)
    
    # Expertise areas
    expertise = StringField(choices=['methodology', 'novelty', 'clarity', 'theory', 'application'], default='methodology')
    
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {'collection': 'custom_reviewers'}
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    def to_dict(self):
        return {
            'id': str(self.id),
            'name': self.name,
            'avatar': self.avatar,
            'strictness': self.strictness,
            'detail_focus': self.detail_focus,
            'innovation_bias': self.innovation_bias,
            'writing_standards': self.writing_standards,
            'methodology_rigor': self.methodology_rigor,
            'optimism': self.optimism,
            'expertise': self.expertise,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }