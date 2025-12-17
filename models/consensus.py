'''
PeerNet++ Consensus Model
=========================
MongoEngine model for multi-agent consensus decisions.

Key Fields:
- paper: Reference to the reviewed Paper
- decision: Accept, Minor Revision, Major Revision, Reject
- negotiation_rounds: List of agent interactions
- final_scores: Aggregated scores across reviewers
- overall_explanation: Summary of decision rationale
'''

from mongoengine import Document, StringField, DictField, DateTimeField, ReferenceField, ListField, FloatField
from datetime import datetime
from .papers import Paper

class Consensus(Document):
    paper = ReferenceField(Paper, required=True)
    decision = StringField(choices=['Accept', 'Minor Revision', 'Major Revision', 'Reject'], required=True)
    negotiation_rounds = ListField(DictField())  # List of rounds with details
    final_scores = DictField()  # Aggregated scores
    confidence = FloatField(min_value=0.0, max_value=1.0)
    overall_explanation = StringField()  # Overall paper explanation
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'consensus'}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self):
        try:
            return {
                'id': str(self.id),
                'paper_id': self.paper.paper_id if self.paper else None,
                'decision': self.decision,
                'negotiation_rounds': self.negotiation_rounds,
                'final_scores': self.final_scores,
                'confidence': self.confidence,
                'overall_explanation': self.overall_explanation,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None
            }
        except Exception as e:
            import logging
            logging.error("Error converting consensus to dict: %s", str(e))
            return {'error': 'Failed to serialize consensus'}
