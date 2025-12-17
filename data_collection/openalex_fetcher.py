'''
PeerNet++ OpenAlex Fetcher
==========================
Fetch paper metadata from OpenAlex API (https://openalex.org).

Input Formats:
- DOI: 10.xxxx/xxxxx or https://doi.org/10.xxxx/xxxxx
- OpenAlex ID: W1234567890
- OpenAlex URL: https://openalex.org/works/W1234567890

OpenAlex is a free, open catalog of scholarly papers, authors,
institutions, and more. No API key required!
'''

import requests
from typing import Dict, Optional
import logging
from config import Config

logger = logging.getLogger(__name__)

class OpenAlexFetcher:
    def __init__(self):
        self.base_url = Config.OPENALEX_API_URL

    def fetch_paper(self, paper_input) -> Optional[Dict]:
        """
        Fetch paper metadata from OpenAlex API.
        paper_input can be a string (paper_id) or dict (form data).
        """
        try:
            # Handle form data input
            if isinstance(paper_input, dict):
                paper_id = paper_input.get('paper_id', paper_input.get('openalex_id', ''))
            else:
                paper_id = str(paper_input)
            
            if not paper_id:
                logger.error("No paper ID provided")
                return None
            
            # Ensure proper format
            if not paper_id.startswith('https://openalex.org/'):
                paper_id = f"https://openalex.org/{paper_id}"

            url = f"{self.base_url}{paper_id.replace('https://openalex.org/', '')}"

            response = requests.get(url)
            response.raise_for_status()

            data = response.json()

            # Extract relevant fields
            paper_data = {
                'paper_id': data.get('id', '').replace('https://openalex.org/', ''),
                'title': data.get('title', ''),
                'authors': [author.get('author', {}).get('display_name', '') for author in data.get('authorships', [])],
                'year': str(data.get('publication_year', '')),
                'abstract': data.get('abstract_inverted_index', {}) and self._reconstruct_abstract(data.get('abstract_inverted_index', {})) or data.get('abstract', '') or 'No abstract available',
                'doi': data.get('doi', ''),
                'keywords': [concept.get('display_name', '') for concept in data.get('concepts', []) if concept.get('score', 0) > 0.5],
                'source': 'openalex'
            }

            # If no abstract, provide a default
            if not paper_data['abstract']:
                logger.info(f"No abstract found for paper {paper_id}, using title as fallback")
                paper_data['abstract'] = f"Abstract not available. Title: {paper_data['title']}"

            return paper_data

        except requests.RequestException as e:
            logger.error(f"Error fetching paper {paper_id} from OpenAlex: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching paper {paper_input}: {str(e)}")
            return None
    
    def _reconstruct_abstract(self, inverted_index: Dict) -> str:
        """Reconstruct abstract from OpenAlex inverted index format."""
        try:
            word_positions = []
            for word, positions in inverted_index.items():
                for pos in positions:
                    word_positions.append((pos, word))
            
            # Sort by position and join words
            word_positions.sort(key=lambda x: x[0])
            return ' '.join([word for _, word in word_positions])
        except Exception as e:
            logger.error(f"Error reconstructing abstract: {str(e)}")
            return "Abstract reconstruction failed"
