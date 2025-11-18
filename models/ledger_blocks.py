from mongoengine import Document, StringField, DictField, DateTimeField, ReferenceField
from datetime import datetime
from .papers import Paper
import hashlib

class LedgerBlock(Document):
    paper = ReferenceField(Paper, required=True)
    previous_hash = StringField()
    data = DictField()  # The event data (review, consensus, etc.)
    timestamp = DateTimeField(default=datetime.now)
    hash = StringField()

    meta = {'collection': 'ledger_blocks'}

    def calculate_hash(self):
        from utils.ledger import LedgerHasher # Import here to avoid circular dependency if utils.ledger imports models
        return LedgerHasher.create_block_hash(
            self.previous_hash,
            self.timestamp,
            self.data
        )

    def save(self, *args, **kwargs):
        try:
            if not self.hash:
                self.hash = self.calculate_hash()
            return super().save(*args, **kwargs)
        except Exception as e:
            import logging
            logging.error("Error saving ledger block: %s", str(e))
            raise

    def to_dict(self):
        return {
            'id': str(self.id),
            'paper_id': self.paper.paper_id,
            'previous_hash': self.previous_hash,
            'data': self.data,
            'timestamp': self.timestamp.isoformat(),
            'hash': self.hash
        }
