'''
PeerNet++ Reviewer Model
========================
Registry of AI reviewer agents.

Key Fields:
- reviewer_id: Unique agent identifier
- name: Human-readable name
- expertise: List of topic keywords

Used to track which agents reviewed which papers.
'''

from mongoengine import Document, StringField, DateTimeField, ListField
from datetime import datetime

class Reviewer(Document):
    reviewer_id = StringField(required=True, unique=True)
    name = StringField()
    expertise = ListField(StringField())  # Keywords or topics
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'reviewers'}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self):
        return {
            'reviewer_id': self.reviewer_id,
            'name': self.name,
            'expertise': self.expertise,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
