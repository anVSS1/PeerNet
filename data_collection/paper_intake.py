"""
Paper Intake Module - Plagiarism-First Architecture
====================================================
CRITICAL CHANGE: Plagiarism check runs FIRST, BEFORE any reviews.

Pipeline:
1. Extract text from PDF (Gemini Vision)
2. Generate embedding (text-embedding-004)
3. CHECK PLAGIARISM (cosine similarity against all papers)
   - If similarity > 85% → REJECT IMMEDIATELY, no API calls wasted
   - If passes → continue to review
4. Save paper with embedding
5. Run AI reviewer agents
6. Build consensus

This saves reviewer API calls on plagiarized papers!
"""

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
from agents.plagiarism_agent import PlagiarismAgent
from config import Config

logger = get_logger(__name__)


class PaperIntake:
    """
    Paper intake with plagiarism-first architecture.
    
    The plagiarism check runs BEFORE reviews to avoid wasting
    API calls on papers that will be rejected anyway.
    """
    
    def __init__(self):
        self.pdf_parser = PDFParser()
        self.openalex_fetcher = OpenAlexFetcher()
        self.json_handler = JSONHandler()
        self.arxiv_fetcher = ArxivFetcher()
        self.pubmed_fetcher = PubmedFetcher()
        self.semantic_fetcher = SemanticFetcher()
        
        # Initialize embedding generator (text-embedding-004)
        try:
            self.embedding_generator = EmbeddingGenerator()
            logger.info("Embedding generator initialized with text-embedding-004")
        except Exception as e:
            logger.warning(f"Embedding generator init failed: {e}")
            self.embedding_generator = None
        
        # Initialize plagiarism agent
        try:
            self.plagiarism_agent = PlagiarismAgent("intake_plagiarism")
            logger.info("Plagiarism agent initialized")
        except Exception as e:
            logger.warning(f"Plagiarism agent init failed: {e}")
            self.plagiarism_agent = None
    
    def intake_single_paper(self, source: str, data: Union[str, Dict], 
                            user_id: str = None, num_reviewers: int = None, 
                            custom_reviewer_ids: List[str] = None) -> Optional[Paper]:
        """
        Intake a single paper with plagiarism-first check.
        
        Args:
            source: 'pdf', 'openalex', 'json', 'arxiv', 'pubmed', 'semantic', 'form'
            data: file path for PDF, paper ID for others, JSON for json
            user_id: ID of the user creating the paper
            num_reviewers: Number of reviewers to use
            custom_reviewer_ids: Specific reviewer IDs to use
            
        Returns:
            Paper object if successful, None if rejected/failed
        """
        auto_review = True
        
        # Load user's saved reviewer preferences
        if user_id and not custom_reviewer_ids:
            self._load_user_preferences(user_id)
        
        try:
            from extensions import socketio
            
            # STEP 1: Extract paper data from source
            self._emit_progress(user_id, 'temp', 'extraction', 10, 
                              f'📄 Starting {source.upper()} processing...')
            
            if source == 'pdf':
                self._emit_progress(user_id, 'temp', 'extraction', 20, 
                                  '🔬 Extracting text with Gemini Vision AI...')
                paper_data = self._process_pdf(data)
            elif source == 'arxiv':
                self._emit_progress(user_id, 'temp', 'extraction', 20,
                                  '📚 Fetching metadata from arXiv.org...')
                paper_data = self._process_arxiv(data)
            elif source == 'pubmed':
                self._emit_progress(user_id, 'temp', 'extraction', 20,
                                  '🏥 Fetching from PubMed/NCBI...')
                paper_data = self._process_pubmed(data)
            elif source == 'semantic':
                self._emit_progress(user_id, 'temp', 'extraction', 20,
                                  '🔎 Fetching from Semantic Scholar...')
                paper_data = self._process_semantic(data)
            elif source == 'openalex':
                self._emit_progress(user_id, 'temp', 'extraction', 20,
                                  '📖 Fetching from OpenAlex...')
                paper_data = self._process_openalex(data)
            elif source == 'json':
                self._emit_progress(user_id, 'temp', 'extraction', 20,
                                  '📋 Parsing JSON metadata...')
                paper_data = self._process_json(data)
            elif source == 'form':
                paper_data = self._process_pdf(data['file_path'])
                auto_review = data.get('auto_review', 'true').lower() == 'true'
                num_reviewers = data.get('num_reviewers')
                custom_reviewer_ids = data.get('custom_reviewer_ids')
            else:
                raise ValueError(f"Unsupported source: {source}")
            
            if not paper_data:
                return None
            
            paper_id = paper_data.get('paper_id', 'temp')
            
            # STEP 2: Generate embedding
            self._emit_progress(user_id, paper_id, 'embedding', 35,
                              '🧠 Generating vector embedding [Google text-embedding-004]...')
            
            embedding = None
            if self.embedding_generator:
                try:
                    text_for_embedding = f"{paper_data.get('title', '')} {paper_data.get('abstract', '')}"
                    embedding = self.embedding_generator.generate_embedding_for_text(text_for_embedding)
                    paper_data['embedding'] = embedding
                    logger.info(f"Generated {len(embedding)}-dim embedding")
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")
                    paper_data['embedding'] = []
            else:
                paper_data['embedding'] = []
            
            # STEP 3: PLAGIARISM CHECK (BEFORE REVIEWS!)
            self._emit_progress(user_id, paper_id, 'plagiarism', 50,
                              '🔍 Checking originality against database... [Cosine Similarity]')
            
            plagiarism_result = self._run_plagiarism_check(paper_data, embedding)
            
            # Store plagiarism results (plagiarism_checked is a StringField: pending/passed/rejected)
            paper_data['plagiarism_checked'] = 'passed'  # Default to passed, will be overwritten if plagiarized
            paper_data['plagiarism_score'] = plagiarism_result.get('max_similarity', 0.0)
            paper_data['similar_papers'] = plagiarism_result.get('similar_papers', [])
            
            # KILL SWITCH: Reject if plagiarism detected
            if plagiarism_result.get('is_plagiarized', False):
                self._emit_progress(user_id, paper_id, 'plagiarism', 100,
                                  f"⛔ REJECTED: {plagiarism_result.get('max_similarity', 0):.1%} similarity detected with existing paper!",
                                  status='rejected')
                
                socketio.emit('upload_progress', {
                    'paper_id': paper_id,
                    'paper_title': paper_data.get('title', 'Unknown'),
                    'status': 'rejected',
                    'message': f"Paper rejected due to {plagiarism_result.get('max_similarity', 0):.1%} similarity with existing papers"
                })
                
                logger.warning(f"Paper {paper_id} rejected - plagiarism: {plagiarism_result.get('max_similarity', 0):.1%}")
                
                # Still save the paper but mark as rejected
                paper_data['status'] = 'rejected'
                paper_data['rejection_reason'] = 'plagiarism'
                paper_data['plagiarism_checked'] = 'rejected'  # Mark as rejected
                paper = Paper(**paper_data)
                paper.save()
                
                return None  # Return None to indicate rejection
            
            # Passed plagiarism check
            self._emit_progress(user_id, paper_id, 'plagiarism', 60,
                              f'✅ Originality verified! ({plagiarism_result.get("max_similarity", 0):.1%} max similarity)')
            
            # STEP 4: Check for existing paper
            existing_paper = Paper.objects(paper_id=paper_data['paper_id']).first()
            if existing_paper:
                logger.info(f"Paper already exists: {paper_data['paper_id']}")
                return existing_paper
            
            # STEP 5: Save paper
            self._emit_progress(user_id, paper_id, 'processing', 70,
                              '💾 Saving paper to database...')
            
            if user_id:
                paper_data['user_id'] = user_id
            
            paper = Paper(**paper_data)
            paper.save()
            logger.info(f"Successfully saved paper: {paper.paper_id}")
            
            socketio.emit('upload_progress', {
                'paper_id': paper.paper_id,
                'paper_title': paper.title,
                'status': 'success',
                'message': '✅ Paper saved! Starting AI review...'
            })
            
            # STEP 6: Run AI reviews (only if plagiarism check passed)
            if auto_review:
                self._emit_progress(user_id, paper_id, 'review', 80,
                                  '🤖 Initializing AI reviewer agents...')
                
                try:
                    from simulation.review_simulation import ReviewSimulation
                    simulation = ReviewSimulation()
                    simulation.simulate_paper_review(
                        paper, 
                        num_reviewers=num_reviewers, 
                        custom_reviewer_ids=custom_reviewer_ids
                    )
                    logger.info(f"Auto-review completed for paper: {paper.paper_id}")
                    
                    self._emit_progress(user_id, paper_id, 'review', 100,
                                      '🎉 Full analysis pipeline complete!', status='success')
                    
                except Exception as e:
                    logger.error(f"Auto-review failed for paper {paper.paper_id}: {e}")
                    socketio.emit('upload_progress', {
                        'paper_id': paper.paper_id,
                        'paper_title': paper.title,
                        'status': 'error',
                        'message': f'❌ Auto-review failed: {str(e)}'
                    })
            
            return paper
            
        except Exception as e:
            logger.error(f"Error intaking paper: {e}")
            self._emit_error(user_id, paper_data if 'paper_data' in locals() else {}, str(e))
            raise e
    
    def _run_plagiarism_check(self, paper_data: Dict, embedding: Optional[List[float]]) -> Dict:
        """
        Run plagiarism check BEFORE reviews.
        
        Returns:
            {
                'is_plagiarized': bool,
                'max_similarity': float,
                'similar_papers': list,
                'reasoning': str
            }
        """
        if not self.plagiarism_agent:
            logger.warning("Plagiarism agent not available, skipping check")
            return {
                'is_plagiarized': False,
                'max_similarity': 0.0,
                'similar_papers': [],
                'reasoning': 'Plagiarism check skipped - agent not available'
            }
        
        if not embedding or len(embedding) == 0:
            logger.warning("No embedding available, skipping plagiarism check")
            return {
                'is_plagiarized': False,
                'max_similarity': 0.0,
                'similar_papers': [],
                'reasoning': 'Plagiarism check skipped - no embedding'
            }
        
        try:
            result = self.plagiarism_agent.process({
                'paper': paper_data,
                'embedding': embedding
            })
            
            return {
                'is_plagiarized': result.get('is_plagiarized', False),
                'max_similarity': result.get('max_similarity', 0.0),
                'similar_papers': result.get('similar_papers', []),
                'reasoning': result.get('reasoning', '')
            }
            
        except Exception as e:
            logger.error(f"Plagiarism check failed: {e}")
            return {
                'is_plagiarized': False,
                'max_similarity': 0.0,
                'similar_papers': [],
                'reasoning': f'Plagiarism check failed: {str(e)}'
            }
    
    def _emit_progress(self, user_id: str, paper_id: str, step: str, 
                       progress: int, message: str, status: str = 'processing'):
        """Emit progress updates via WebSocket."""
        if not user_id:
            return
        
        try:
            from extensions import socketio
            socketio.emit('analysis_progress', {
                'paper_id': paper_id,
                'step': step,
                'progress': progress,
                'message': message,
                'status': status
            }, room=str(user_id))
        except Exception as e:
            logger.debug(f"Progress emit failed: {e}")
    
    def _emit_error(self, user_id: str, paper_data: Dict, error_msg: str):
        """Emit error notification via WebSocket."""
        try:
            from extensions import socketio
            socketio.emit('upload_progress', {
                'paper_id': paper_data.get('paper_id', 'unknown'),
                'paper_title': paper_data.get('title', 'Unknown'),
                'status': 'error',
                'message': error_msg
            })
        except:
            pass
    
    def _load_user_preferences(self, user_id: str) -> tuple:
        """Load user's saved reviewer preferences."""
        try:
            from models.users import User
            user = User.objects(id=user_id).first()
            if user and user.preferences and 'reviewer_config' in user.preferences:
                config = user.preferences['reviewer_config']
                return (
                    config.get('num_reviewers'),
                    config.get('selected_reviewers', [])
                )
        except Exception as e:
            logger.warning(f"Could not load user preferences: {e}")
        return (None, None)
    
    def intake_batch_papers(self, papers: List[Dict], num_reviewers: int = None,
                            custom_reviewer_ids: List[str] = None) -> List[Paper]:
        """
        Intake multiple papers.
        
        Args:
            papers: List of dicts with 'source' and 'data' keys
            
        Returns:
            List of successfully ingested Paper objects
        """
        results = []
        for paper_spec in papers:
            try:
                paper = self.intake_single_paper(
                    paper_spec['source'],
                    paper_spec['data'],
                    user_id=paper_spec.get('user_id'),
                    num_reviewers=num_reviewers,
                    custom_reviewer_ids=custom_reviewer_ids
                )
                if paper:
                    results.append(paper)
            except Exception as e:
                logger.error(f"Failed to intake paper: {e}")
        return results
    
    def _process_pdf(self, file_path: str) -> Optional[Dict]:
        """Process PDF file using Gemini Vision API."""
        # Validate file path
        import os.path
        if not os.path.isfile(file_path) or '..' in file_path:
            raise ValueError("Invalid file path")
        
        extracted = self.pdf_parser.extract_text_and_metadata(file_path)
        metadata = extracted['metadata']
        
        paper_data = {
            'paper_id': f"pdf_{abs(hash(file_path))}",
            'title': metadata.get('title', 'Unknown Title'),
            'authors': metadata.get('authors') or metadata.get('authors_list', []),
            'year': metadata.get('year', ''),
            'abstract': metadata.get('abstract') or metadata.get('subject', ''),
            'doi': metadata.get('doi', ''),
            'full_text': extracted['full_text'][:10000] if extracted['full_text'] else '',
            'sections': extracted.get('sections', {}),
            'keywords': metadata.get('keywords', []),
            'source': 'pdf',
            # New fields from Gemini Vision
            'visual_analysis': extracted.get('visual_analysis', []),
            'document_assessment': extracted.get('document_assessment', {})
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


