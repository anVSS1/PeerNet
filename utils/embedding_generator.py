"""
Embedding Generator using Google's text-embedding-004
======================================================
This module generates vector embeddings for papers using Google's 
text-embedding-004 model. These embeddings are used for:
1. Plagiarism detection (cosine similarity)
2. Semantic search
3. Paper clustering/recommendation

No more SPECTER or local transformer models.
We use Google's API for consistent, high-quality embeddings.
"""

import google.generativeai as genai
from typing import List, Dict, Optional
import logging
import numpy as np
from config import Config

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Google text-embedding-004 based embedding generator.
    Produces 768-dimensional vectors optimized for semantic similarity.
    """
    
    def __init__(self):
        """Initialize the embedding generator with Google API."""
        self.api_key = Config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model_name = Config.GEMINI_EMBEDDING_MODEL
            logger.info(f"EmbeddingGenerator initialized with {self.model_name}")
        else:
            logger.warning("No Gemini API key found. Embeddings will fail.")
            self.model_name = None
    
    def generate_embedding(self, paper_data: Dict) -> List[float]:
        """
        Generate embedding vector for a single paper.
        
        Args:
            paper_data: Dict with keys like 'title', 'abstract', 'full_text'
            
        Returns:
            List of floats (768-dimensional vector)
        """
        if not self.model_name:
            logger.error("Embedding model not configured")
            return []
        
        try:
            # Prepare text for embedding
            text = self._prepare_text_for_embedding(paper_data)
            
            if not text:
                logger.warning("No text available for embedding generation")
                return []
            
            # Call Google's embedding API
            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=text,
                task_type="SEMANTIC_SIMILARITY"  # Optimized for similarity comparison
            )
            
            # Handle both dict and object response types
            if hasattr(result, 'get'):
                embedding = result['embedding']
            elif hasattr(result, 'embedding'):
                embedding = result.embedding
            else:
                embedding = result.get('embedding', []) if isinstance(result, dict) else []
            logger.debug(f"Generated embedding with {len(embedding)} dimensions")
            
            return embedding
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return []
    
    def generate_embedding_for_text(self, text: str) -> List[float]:
        """
        Generate embedding for raw text (not paper data).
        Useful for query embedding in search.
        """
        if not self.model_name or not text:
            return []
        
        try:
            result = genai.embed_content(
                model=f"models/{self.model_name}",
                content=text[:10000],  # Limit to 10k chars
                task_type="SEMANTIC_SIMILARITY"
            )
            # Handle both dict and object response types
            if hasattr(result, 'get'):
                return result.get('embedding', [])
            elif hasattr(result, 'embedding'):
                return result.embedding
            else:
                return []
        except Exception as e:
            logger.error(f"Error generating text embedding: {str(e)}")
            return []
    
    def _prepare_text_for_embedding(self, paper_data: Dict) -> str:
        """
        Prepare text for embedding generation.
        Combines title + abstract + key sections for best representation.
        """
        parts = []
        
        # Title is most important
        if paper_data.get('title'):
            parts.append(f"Title: {paper_data['title']}")
        
        # Abstract provides core summary
        if paper_data.get('abstract'):
            parts.append(f"Abstract: {paper_data['abstract']}")
        
        # Include introduction if available (key contributions)
        sections = paper_data.get('sections', {})
        if sections.get('introduction'):
            intro = sections['introduction'][:2000]  # Limit length
            parts.append(f"Introduction: {intro}")
        
        # Include conclusion if available
        if sections.get('conclusion'):
            conclusion = sections['conclusion'][:1000]
            parts.append(f"Conclusion: {conclusion}")
        
        # Fallback to full text if nothing else
        if not parts and paper_data.get('full_text'):
            return paper_data['full_text'][:8000]
        
        combined = '\n\n'.join(parts)
        
        # Limit total length (embedding models have limits)
        return combined[:10000] if combined else ""
    
    def generate_embeddings_batch(self, papers_data: List[Dict]) -> List[List[float]]:
        """
        Generate embeddings for multiple papers.
        
        Args:
            papers_data: List of paper dictionaries
            
        Returns:
            List of embedding vectors
        """
        embeddings = []
        for i, paper_data in enumerate(papers_data):
            logger.debug(f"Generating embedding {i+1}/{len(papers_data)}")
            embedding = self.generate_embedding(paper_data)
            embeddings.append(embedding)
        return embeddings
    
    @staticmethod
    def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Similarity score between 0 and 1 (1 = identical)
        """
        if not vec1 or not vec2:
            return 0.0
        
        try:
            a = np.array(vec1)
            b = np.array(vec2)
            
            # Handle dimension mismatch
            if len(a) != len(b):
                logger.warning(f"Embedding dimension mismatch: {len(a)} vs {len(b)}")
                return 0.0
            
            # Cosine similarity formula
            dot_product = np.dot(a, b)
            norm_a = np.linalg.norm(a)
            norm_b = np.linalg.norm(b)
            
            if norm_a == 0 or norm_b == 0:
                return 0.0
            
            similarity = dot_product / (norm_a * norm_b)
            
            # Clamp to [0, 1] range (handle floating point errors)
            return float(max(0.0, min(1.0, similarity)))
            
        except Exception as e:
            logger.error(f"Error calculating cosine similarity: {str(e)}")
            return 0.0
    
    def find_similar_papers(self, query_embedding: List[float], 
                           paper_embeddings: List[Dict],
                           top_k: int = 5) -> List[Dict]:
        """
        Find most similar papers based on embedding similarity.
        
        Args:
            query_embedding: Vector of the query paper
            paper_embeddings: List of {paper_id, embedding, title} dicts
            top_k: Number of results to return
            
        Returns:
            List of {paper_id, title, similarity} sorted by similarity
        """
        if not query_embedding:
            return []
        
        results = []
        for paper in paper_embeddings:
            embedding = paper.get('embedding', [])
            if embedding:
                similarity = self.cosine_similarity(query_embedding, embedding)
                results.append({
                    'paper_id': paper.get('paper_id'),
                    'title': paper.get('title', 'Unknown'),
                    'similarity': round(similarity, 4)
                })
        
        # Sort by similarity (highest first)
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        return results[:top_k]
