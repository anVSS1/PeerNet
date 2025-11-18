from mongoengine import Document, StringField, DictField, DateTimeField, FloatField, ReferenceField
from datetime import datetime
from .papers import Paper

class BiasFlag(Document):
    paper = ReferenceField(Paper, required=True)
    flag_type = StringField(choices=['scoring_outlier', 'topic_bias', 'affiliation_bias', 'temporal_bias'], required=True)
    evidence = DictField()  # Details supporting the flag
    confidence = FloatField(min_value=0.0, max_value=1.0)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'bias_flags'}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self):
        try:
            return {
                'id': str(self.id),
                'paper_id': self.paper.paper_id if self.paper else None,
                'flag_type': self.flag_type,
                'evidence': self.evidence,
                'confidence': self.confidence,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            import logging
            logging.error("Error converting bias flag to dict: %s", str(e))
            return {'error': 'Failed to serialize bias flag'}
