import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import Dict, List, Optional, Union
from data_collection.pdf_parser import PDFParser
from data_collection.openalex_fetcher import OpenAlexFetcher
from data_collection.json_handler import JSONHandler
from data_collection.arxiv_fetcher import ArxivFetcher
from data_collection.pubmed_fetcher import PubmedFetcher
from data_collection.semantic_fetcher import SemanticFetcher

from models.papers import Paper
from utils.embedding_generator import EmbeddingGenerator
from utils.logger import get_logger

logger = get_logger(__name__)

class PaperIntake:
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.openalex_fetcher = OpenAlexFetcher()
        self.json_handler = JSONHandler()
        self.arxiv_fetcher = ArxivFetcher()
        self.pubmed_fetcher = PubmedFetcher()
        self.semantic_fetcher = SemanticFetcher()

        # Disable embedding generator for now to avoid crashes
        logger.info("Embedding generator disabled for development")
        self.embedding_generator = None

    def intake_single_paper(self, source: str, data: Union[str, Dict], user_id: str = None, num_reviewers: int = None, custom_reviewer_ids: List[str] = None) -> Optional[Paper]:
        """
        Intake a single paper from various sources.
        source: 'pdf', 'openalex', 'json'
        data: file path for PDF, paper ID for OpenAlex, JSON string/dict for JSON
        user_id: ID of the user creating the paper
        """
        auto_review = True # Default to auto-reviewing
        
        # Load user's saved reviewer preferences if user_id is provided and no explicit reviewers specified
        if user_id and not custom_reviewer_ids:
            from models.users import User
            try:
                user = User.objects(id=user_id).first()
                if user and user.preferences and 'reviewer_config' in user.preferences:
                    reviewer_config = user.preferences['reviewer_config']
                    num_reviewers = reviewer_config.get('num_reviewers', num_reviewers)
                    custom_reviewer_ids = reviewer_config.get('selected_reviewers', [])
                    logger.info(f"Loaded user reviewer preferences: {num_reviewers} reviewers, IDs: {custom_reviewer_ids}")
            except Exception as e:
                logger.warning(f"Could not load user reviewer preferences: {str(e)}")
        
        try:
            if source == 'pdf':
                paper_data = self._process_pdf(data)
            elif source == 'arxiv':
                paper_data = self._process_arxiv(data)
            elif source == 'pubmed':
                paper_data = self._process_pubmed(data)
            elif source == 'semantic':
                paper_data = self._process_semantic(data)
            elif source == 'openalex':
                paper_data = self._process_openalex(data)
            elif source == 'json':
                paper_data = self._process_json(data)
            elif source == 'form': # Handling form data from single PDF upload
                paper_data = self._process_pdf(data['file_path'])
                auto_review = data.get('auto_review', 'true').lower() == 'true'
                num_reviewers = data.get('num_reviewers')
                custom_reviewer_ids = data.get('custom_reviewer_ids')
            else:
                raise ValueError(f"Unsupported source: {source}")

            if not paper_data:
                return None

            # Set user_id if provided
            if user_id:
                paper_data['user_id'] = user_id

            # Generate embeddings (optional)
            if self.embedding_generator:
                try:
                    embedding = self.embedding_generator.generate_embedding(paper_data)
                    paper_data['specter_embedding'] = embedding
                except Exception as e:
                    logger.warning(f"Failed to generate embedding: {str(e)}")
                    paper_data['specter_embedding'] = []
            else:
                paper_data['specter_embedding'] = []

            # Check if paper already exists
            existing_paper = Paper.objects(paper_id=paper_data['paper_id']).first()
            if existing_paper:
                logger.info("Paper already exists: %s", paper_data['paper_id'])
                return existing_paper

            # Emit processing notification
            from extensions import socketio
            socketio.emit('upload_progress', {
                'paper_id': paper_data['paper_id'],
                'paper_title': paper_data.get('title', 'Unknown'),
                'status': 'processing',
                'message': 'Paper is being processed...'
            })
            
            # Create and save Paper document
            paper = Paper(**paper_data)
            paper.save()
            logger.info("Successfully intaken paper: %s", paper.paper_id)
            
            # Emit success notification
            socketio.emit('upload_progress', {
                'paper_id': paper.paper_id,
                'paper_title': paper.title,
                'status': 'success',
                'message': 'Paper uploaded successfully'
            })
            
            # Auto-trigger review simulation if enabled
            if auto_review:
                try:
                    from simulation.review_simulation import ReviewSimulation
                    simulation = ReviewSimulation()
                    simulation.simulate_paper_review(paper, num_reviewers=num_reviewers, custom_reviewer_ids=custom_reviewer_ids)
                    logger.info("Auto-review completed for paper: %s", paper.paper_id)
                except Exception as e:
                    logger.error("Auto-review failed for paper %s: %s", paper.paper_id, str(e))
                    # Emit error notification for review failure
                    from extensions import socketio
                    socketio.emit('upload_progress', {
                        'paper_id': paper.paper_id,
                        'paper_title': paper.title,
                        'status': 'error',
                        'message': f'Auto-review failed: {str(e)}'
                    })
            
            return paper

        except Exception as e:
            logger.error("Error intaking paper: %s", str(e))
            # Emit error notification
            from extensions import socketio
            try:
                socketio.emit('upload_progress', {
                    'paper_id': paper_data.get('paper_id', 'unknown') if 'paper_data' in locals() else 'unknown',
                    'paper_title': paper_data.get('title', 'Unknown') if 'paper_data' in locals() else 'Unknown',
                    'status': 'error',
                    'message': str(e)
                })
            except:
                pass
            raise e

    def intake_batch_papers(self, papers: List[Dict], num_reviewers: int = None, custom_reviewer_ids: List[str] = None) -> List[Paper]:
        """
        Intake multiple papers.
        papers: List of dicts with 'source' and 'data' keys
        """
        results = []
        for paper_spec in papers:
            user_id = paper_spec.get('user_id')
            paper = self.intake_single_paper(
                paper_spec['source'],
                paper_spec['data'],
                user_id=user_id,
                num_reviewers=num_reviewers,
                custom_reviewer_ids=custom_reviewer_ids
            )
            if paper:
                results.append(paper)
        return results

    def _process_pdf(self, file_path: str) -> Optional[Dict]:
        """Process PDF file using AI metadata extraction."""
        extracted = self.pdf_parser.extract_text_and_metadata(file_path)

        # Validate file path to prevent path traversal
        import os.path
        if not os.path.isfile(file_path) or '..' in file_path:
            raise ValueError("Invalid file path")
        
        # Use AI-extracted metadata directly
        metadata = extracted['metadata']
        
        paper_data = {
            'paper_id': "pdf_%s" % abs(hash(file_path)),
            'title': metadata.get('title', 'Unknown Title'),
            'authors': metadata.get('authors', []),
            'year': metadata.get('year', ''),
            'abstract': metadata.get('abstract', ''),
            'doi': '',
            'full_text': extracted['full_text'][:10000] if extracted['full_text'] else '',
            'sections': extracted['sections'],
            'keywords': metadata.get('keywords', []),
            'source': 'pdf'
        }

        return paper_data

    def _process_openalex(self, data: Union[str, Dict]) -> Optional[Dict]:
        """Process OpenAlex paper ID or form data."""
        return self.openalex_fetcher.fetch_paper(data)

    def _process_json(self, json_data: Union[str, Dict]) -> Optional[Dict]:
        """Process JSON data."""
        paper_data = self.json_handler.parse_paper_json(json_data)
        if paper_data and self.json_handler.validate_paper_data(paper_data):
            return paper_data
        return None
    
    def _process_arxiv(self, paper_id: str) -> Optional[Dict]:
        """Process arXiv paper ID."""
        return self.arxiv_fetcher.fetch_paper(paper_id)
    
    def _process_pubmed(self, paper_id: str) -> Optional[Dict]:
        """Process PubMed paper ID."""
        return self.pubmed_fetcher.fetch_paper(paper_id)
    
    def _process_semantic(self, paper_id: str) -> Optional[Dict]:
        """Process Semantic Scholar paper ID."""
        return self.semantic_fetcher.fetch_paper(paper_id)
    

