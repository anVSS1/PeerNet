from transformers import AutoTokenizer, AutoModel
import torch
from typing import List, Dict, Optional
import logging
from config import Config

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    def __init__(self):
        self.model_name = Config.SPECTER_MODEL
        self.tokenizer = None
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the SPECTER model and tokenizer."""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModel.from_pretrained(self.model_name)
            logger.info(f"Loaded SPECTER model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load SPECTER model: {str(e)}")
            raise

    def generate_embedding(self, paper_data: Dict) -> List[float]:
        """
        Generate SPECTER embedding for a paper.
        Uses abstract + title, or full text if available.
        """
        try:
            # Prepare input text
            text = self._prepare_text_for_embedding(paper_data)

            if not text:
                logger.warning("No text available for embedding generation")
                return []

            # Tokenize
            inputs = self.tokenizer(text, return_tensors='pt', truncation=True, max_length=512, padding=True)

            # Generate embedding
            with torch.no_grad():
                outputs = self.model(**inputs)
                # Use [CLS] token embedding (first token)
                embedding = outputs.last_hidden_state[:, 0, :].squeeze().tolist()

            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return []

    def _prepare_text_for_embedding(self, paper_data: Dict) -> str:
        """
        Prepare text for embedding generation.
        Prioritizes: full_text > abstract + title > title only
        """
        if paper_data.get('full_text'):
            return paper_data['full_text'][:2000]  # Limit length

        text_parts = []
        if paper_data.get('title'):
            text_parts.append(paper_data['title'])
        if paper_data.get('abstract'):
            text_parts.append(paper_data['abstract'])

        return ' '.join(text_parts)[:2000] if text_parts else ""

    def generate_embeddings_batch(self, papers_data: List[Dict]) -> List[List[float]]:
        """
        Generate embeddings for multiple papers.
        """
        embeddings = []
        for paper_data in papers_data:
            embedding = self.generate_embedding(paper_data)
            embeddings.append(embedding)
        return embeddings
