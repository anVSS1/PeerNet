from mongoengine import Document, StringField, ListField, DictField, DateTimeField, FloatField, ReferenceField
from datetime import datetime

class Paper(Document):
    paper_id = StringField(required=True, unique=True)
    title = StringField(required=True)
    authors = ListField(StringField())
    year = StringField()
    abstract = StringField()
    doi = StringField()
    full_text = StringField()
    sections = DictField()  # e.g., {"introduction": "...", "methods": "..."}
    keywords = ListField(StringField())
    source = StringField(choices=['pdf', 'arxiv', 'pubmed', 'semantic_scholar', 'json'])
    source_id = StringField()  # Original ID from the source (e.g., arXiv ID)
    pdf_url = StringField()   # URL to the PDF file
    specter_embedding = ListField(FloatField())
    user_id = ReferenceField('User', null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {'collection': 'papers'}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

    def to_dict(self):
        try:
            return {
                'paper_id': self.paper_id,
                'title': self.title,
                'authors': self.authors,
                'year': self.year,
                'abstract': self.abstract,
                'doi': self.doi,
                'full_text': self.full_text,
                'sections': self.sections,
                'keywords': self.keywords,
                'source': self.source,
                'source_id': self.source_id,
                'pdf_url': self.pdf_url,
                'specter_embedding': self.specter_embedding,
                'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') and self.created_at else str(self.created_at) if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') and self.updated_at else str(self.updated_at) if self.updated_at else None
            }
        except Exception as e:
            import logging
            logging.error("Error converting paper to dict: %s", str(e))
            return {'error': 'Failed to serialize paper'}
