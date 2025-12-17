'''
PeerNet++ Semantic Scholar Fetcher
==================================
Fetch paper metadata from Semantic Scholar API.

Input Formats:
- S2 Paper ID: CorpusId:123456789
- DOI: 10.xxxx/xxxxx
- arXiv ID: arXiv:2312.12345
- Semantic Scholar URL

Semantic Scholar provides rich metadata including:
- Citations, references
- Influential citations count
- Fields of study
'''

import requests
from typing import Dict, Optional
import re
from utils.logger import get_logger

logger = get_logger(__name__)

class SemanticFetcher:
    def __init__(self):
        self.base_url = "https://api.semanticscholar.org/graph/v1/paper"
    
    def fetch_paper(self, paper_input: str) -> Optional[Dict]:
        """Fetch paper from Semantic Scholar API."""
        try:
            # Clean input
            paper_input = paper_input.strip()
            
            # Construct URL based on input type
            if self._is_doi(paper_input):
                url = f"{self.base_url}/DOI:{paper_input}"
            elif self._is_arxiv_id(paper_input):
                url = f"{self.base_url}/arXiv:{paper_input}"
            elif self._is_semantic_id(paper_input):
                url = f"{self.base_url}/{paper_input}"
            else:
                # Try as direct ID
                url = f"{self.base_url}/{paper_input}"
            
            # Add fields parameter
            params = {
                'fields': 'title,authors,year,abstract,citationCount,referenceCount,fieldsOfStudy,s2FieldsOfStudy,publicationDate,journal,externalIds'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            paper_data = self._parse_response(data, paper_input)
            return paper_data
            
        except Exception as e:
            logger.error(f"Error fetching from Semantic Scholar: {str(e)}")
            return None
    
    def _is_doi(self, text: str) -> bool:
        """Check if text is a DOI."""
        return re.match(r'^10\.\d+/.+', text) is not None
    
    def _is_arxiv_id(self, text: str) -> bool:
        """Check if text is an arXiv ID."""
        return re.match(r'^\d{4}\.\d{4,5}$', text) is not None
    
    def _is_semantic_id(self, text: str) -> bool:
        """Check if text is a Semantic Scholar paper ID."""
        return re.match(r'^[a-f0-9]{40}$', text) is not None
    
    def _parse_response(self, data: Dict, original_input: str) -> Dict:
        """Parse API response into paper data."""
        # Basic info
        title = data.get('title', 'Unknown Title')
        abstract = data.get('abstract', '')
        year = str(data.get('year', '')) if data.get('year') else ''
        
        # Authors
        authors = []
        for author in data.get('authors', []):
            authors.append(author.get('name', ''))
        
        # DOI
        doi = ''
        external_ids = data.get('externalIds', {})
        if external_ids:
            doi = external_ids.get('DOI', '')
        
        # Keywords from fields of study
        keywords = []
        fields = data.get('fieldsOfStudy', []) or []
        s2_fields = data.get('s2FieldsOfStudy', []) or []
        
        keywords.extend(fields)
        for field in s2_fields:
            if isinstance(field, dict) and 'category' in field:
                keywords.append(field['category'])
        
        # Generate paper ID
        paper_id = f"semantic_{data.get('paperId', abs(hash(original_input)))}"
        
        return {
            'paper_id': paper_id,
            'title': title,
            'authors': authors,
            'year': year,
            'abstract': abstract,
            'doi': doi,
            'keywords': list(set(keywords)),  # Remove duplicates
            'source': 'semantic_scholar',
            'source_id': data.get('paperId', ''),
            'citation_count': data.get('citationCount', 0),
            'reference_count': data.get('referenceCount', 0),
            'full_text': '',
            'sections': {}
        }