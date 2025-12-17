'''
PeerNet++ Paper Model
=====================
MongoEngine model for academic papers.

Key Fields:
- paper_id: Unique identifier (UUID)
- title, authors, abstract: Core metadata
- full_text: Extracted text from PDF/source
- embedding: 768-dim vector for similarity search
- plagiarism_score: Max similarity to existing papers
- visual_analysis: Descriptions of figures from Gemini Vision
- status: processing, completed, rejected, error
'''

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
    
    # Visual Analysis from Gemini Vision (NEW)
    visual_analysis = ListField(DictField())  # Descriptions of figures, charts, diagrams
    document_assessment = DictField()  # Quality assessment from Gemini
    
    # Vector Embedding for Plagiarism Detection (NEW - 2025 Stack)
    # Using text-embedding-004 from Google (768 dimensions)
    embedding = ListField(FloatField())  # Vector for semantic similarity search
    
    # Legacy field (kept for backward compatibility)
    specter_embedding = ListField(FloatField())
    
    # Plagiarism check results (NEW - runs BEFORE review)
    plagiarism_checked = StringField(default='pending')  # pending, passed, rejected
    plagiarism_score = FloatField(default=0.0)  # Highest similarity found
    similar_papers = ListField(DictField())  # List of similar papers found
    
    user_id = ReferenceField('User', null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    meta = {
        'collection': 'papers',
        'indexes': [
            'paper_id',
            'title',
            'plagiarism_checked',
            # Note: For vector search, create index in MongoDB Atlas UI
        ]
    }

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
                'visual_analysis': self.visual_analysis,
                'document_assessment': self.document_assessment,
                'plagiarism_checked': self.plagiarism_checked,
                'plagiarism_score': self.plagiarism_score,
                'similar_papers': self.similar_papers,
                'has_embedding': len(self.embedding) > 0 if self.embedding else False,
                'created_at': self.created_at.isoformat() if hasattr(self.created_at, 'isoformat') and self.created_at else str(self.created_at) if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if hasattr(self.updated_at, 'isoformat') and self.updated_at else str(self.updated_at) if self.updated_at else None
            }
        except Exception as e:
            import logging
            logging.error("Error converting paper to dict: %s", str(e))
            return {'error': 'Failed to serialize paper'}
