"""
Plagiarism Detection using Vector Embeddings + Cosine Similarity
================================================================
This module performs FRONT-GATE plagiarism detection:
1. Runs BEFORE any reviewer touches the paper
2. Uses text-embedding-004 for vector generation
3. Compares against ALL papers in the database
4. KILL SWITCH: If similarity > 85%, instant reject (don't waste API calls)

No more Levenshtein distance or phrase matching.
We use semantic similarity via vector embeddings.
"""

from typing import Dict, Any, List, Optional, Tuple
import logging
from agents.base_agent import BaseAgent
from utils.embedding_generator import EmbeddingGenerator
from config import Config

logger = logging.getLogger(__name__)


class PlagiarismAgent(BaseAgent):
    """
    Vector-based plagiarism detection agent.
    This is the GATEKEEPER - runs before reviewers to save API costs.
    """
    
    def __init__(self, agent_id: str = "plagiarism_gatekeeper"):
        super().__init__(agent_id, "PlagiarismGatekeeper")
        self.embedding_generator = EmbeddingGenerator()
        self.similarity_threshold = Config.PLAGIARISM_SIMILARITY_THRESHOLD  # 0.85 = 85%
        self.log_activity("Plagiarism Gatekeeper initialized with vector search")
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main entry point - check paper against database.
        
        Args:
            input_data: {
                'paper': Dict with paper content,
                'paper_embedding': Optional pre-computed embedding,
                'comparison_embeddings': List of existing paper embeddings from DB
            }
            
        Returns:
            Dict with:
                - passed: bool (True if OK to proceed to review)
                - plagiarism_score: float (highest similarity found)
                - similar_papers: List of similar papers
                - recommendation: str
        """
        try:
            paper = input_data.get('paper', {})
            if not paper:
                return self._create_result(True, 0.0, [], "No paper data provided")
            
            self.log_activity(f"Checking plagiarism for: {paper.get('title', 'Unknown')[:50]}...")
            
            # Get or generate embedding for the new paper
            paper_embedding = input_data.get('paper_embedding')
            if not paper_embedding:
                paper_embedding = self.embedding_generator.generate_embedding(paper)
            
            if not paper_embedding:
                self.log_activity("Could not generate embedding - allowing paper through", "warning")
                return self._create_result(True, 0.0, [], "Could not generate embedding for comparison")
            
            # Get comparison embeddings (all papers in database)
            comparison_embeddings = input_data.get('comparison_embeddings', [])
            
            if not comparison_embeddings:
                self.log_activity("No existing papers to compare against - first paper in database")
                return self._create_result(True, 0.0, [], "First paper in database - no comparison needed")
            
            # Find similar papers
            similar_papers = self._find_similar_papers(paper_embedding, comparison_embeddings)
            
            # Get highest similarity score
            max_similarity = similar_papers[0]['similarity'] if similar_papers else 0.0
            
            # KILL SWITCH: Reject if too similar
            passed = max_similarity < self.similarity_threshold
            
            # Generate recommendation
            recommendation = self._generate_recommendation(passed, max_similarity, similar_papers)
            
            result = self._create_result(passed, max_similarity, similar_papers, recommendation)
            
            # Log outcome
            if passed:
                self.log_activity(f"✅ PASSED - Max similarity: {max_similarity:.2%}")
            else:
                self.log_activity(f"❌ REJECTED - Similarity {max_similarity:.2%} exceeds threshold {self.similarity_threshold:.2%}", "warning")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in plagiarism detection: {str(e)}")
            # On error, allow paper through (fail open) but flag it
            return self._create_result(True, 0.0, [], f"Detection error: {str(e)}")
    
    def _find_similar_papers(self, query_embedding: List[float], 
                            comparison_embeddings: List[Dict]) -> List[Dict]:
        """
        Find papers similar to the query using cosine similarity.
        
        Returns:
            List sorted by similarity (highest first), max 10 results
        """
        results = []
        
        for paper_data in comparison_embeddings:
            embedding = paper_data.get('embedding', [])
            if not embedding:
                continue
            
            similarity = self.embedding_generator.cosine_similarity(
                query_embedding, 
                embedding
            )
            
            # Only include papers with meaningful similarity
            if similarity > 0.3:  # 30% minimum to be considered
                results.append({
                    'paper_id': paper_data.get('paper_id', 'unknown'),
                    'title': paper_data.get('title', 'Unknown Title'),
                    'similarity': round(similarity, 4),
                    'authors': paper_data.get('authors', []),
                    'year': paper_data.get('year', '')
                })
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Return top 10
        return results[:10]
    
    def _generate_recommendation(self, passed: bool, 
                                 max_similarity: float,
                                 similar_papers: List[Dict]) -> str:
        """Generate human-readable recommendation."""
        
        if not passed:
            # REJECTED
            if similar_papers:
                top_match = similar_papers[0]
                return (
                    f"🚫 REJECTED: This paper has {max_similarity:.1%} similarity with "
                    f"'{top_match['title'][:60]}...' "
                    f"This exceeds the {self.similarity_threshold:.0%} threshold. "
                    f"The paper appears to be substantially similar to existing work. "
                    f"Review will not proceed."
                )
            return f"🚫 REJECTED: Similarity {max_similarity:.1%} exceeds threshold."
        
        # PASSED - but with different confidence levels
        if max_similarity >= 0.70:
            return (
                f"⚠️ CAUTION: High similarity ({max_similarity:.1%}) detected. "
                f"Paper is allowed to proceed but reviewers should verify originality. "
                f"Similar to: {similar_papers[0]['title'][:50]}..." if similar_papers else ""
            )
        elif max_similarity >= 0.50:
            return (
                f"📝 NOTE: Moderate similarity ({max_similarity:.1%}) with existing papers. "
                f"This is common in related work. Proceeding to review."
            )
        elif max_similarity >= 0.30:
            return f"✅ LOW SIMILARITY ({max_similarity:.1%}): Paper appears original. Proceeding to review."
        else:
            return "✅ UNIQUE: No significant similarity to existing papers. Proceeding to review."
    
    def _create_result(self, passed: bool, score: float, 
                       similar_papers: List[Dict], recommendation: str) -> Dict[str, Any]:
        """Create standardized result dictionary."""
        return {
            'agent_id': self.agent_id,
            'passed': passed,
            'plagiarism_score': score,
            'threshold': self.similarity_threshold,
            'similar_papers': similar_papers,
            'recommendation': recommendation,
            'action': 'proceed_to_review' if passed else 'reject_instant'
        }
    
    def check_paper_quick(self, paper: Dict, existing_papers: List[Dict]) -> Tuple[bool, float]:
        """
        Quick check - returns just pass/fail and score.
        Use this for fast pre-screening.
        """
        result = self.process({
            'paper': paper,
            'comparison_embeddings': existing_papers
        })
        return result['passed'], result['plagiarism_score']
    
    def generate_paper_embedding(self, paper: Dict) -> List[float]:
        """
        Generate embedding for a paper.
        Convenience method to access embedding generator.
        """
        return self.embedding_generator.generate_embedding(paper)


# Singleton instance for easy import
_gatekeeper_instance = None

def get_plagiarism_gatekeeper() -> PlagiarismAgent:
    """Get or create singleton plagiarism gatekeeper instance."""
    global _gatekeeper_instance
    if _gatekeeper_instance is None:
        _gatekeeper_instance = PlagiarismAgent()
    return _gatekeeper_instance
