from mongoengine import Document, StringField, DictField, DateTimeField, FloatField, ReferenceField
from datetime import datetime
from .papers import Paper

class Review(Document):
    paper = ReferenceField(Paper, required=True)
    reviewer_id = StringField(required=True)  # Agent ID
    scores = DictField()  # e.g., {"novelty": 7, "clarity": 8, "methodology": 6, "relevance": 8, "overall": 7.25}
    written_feedback = StringField()
    confidence = FloatField(min_value=0.0, max_value=1.0)
    logs = StringField()  # Debugging/logs
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'reviews'}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self):
        try:
            return {
                'id': str(self.id),
                'paper_id': self.paper.paper_id if self.paper else None,
                'reviewer_id': self.reviewer_id,
                'scores': self.scores,
                'written_feedback': self.written_feedback,
                'confidence': self.confidence,
                'logs': self.logs,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            import logging
            logging.error("Error converting review to dict: %s", str(e))
            return {'error': 'Failed to serialize review'}
