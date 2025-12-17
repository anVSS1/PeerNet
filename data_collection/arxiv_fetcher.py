'''
PeerNet++ ArXiv Fetcher
=======================
Fetch paper metadata from arXiv.org API.

Input Formats:
- arXiv ID: 2312.12345 or arXiv:2312.12345
- arXiv URL: https://arxiv.org/abs/2312.12345

Returns standardized paper dict with:
- title, authors, abstract, year
- source: 'arxiv'
- source_id: arXiv ID
'''

import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import re
from utils.logger import get_logger

logger = get_logger(__name__)

class ArxivFetcher:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
    
    def fetch_paper(self, paper_input: str) -> Optional[Dict]:
        """Fetch paper from arXiv API."""
        try:
            # Extract arXiv ID from various formats
            arxiv_id = self._extract_arxiv_id(paper_input)
            if not arxiv_id:
                logger.error(f"Invalid arXiv ID format: {paper_input}")
                return None
            
            # Query arXiv API
            params = {
                'id_list': arxiv_id,
                'max_results': 1
            }
            
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            entries = root.findall('{http://www.w3.org/2005/Atom}entry')
            
            if not entries:
                logger.error(f"No paper found for arXiv ID: {arxiv_id}")
                return None
            
            entry = entries[0]
            
            # Extract paper data
            paper_data = self._parse_entry(entry, arxiv_id)
            return paper_data
            
        except Exception as e:
            logger.error(f"Error fetching from arXiv: {str(e)}")
            return None
    
    def _extract_arxiv_id(self, paper_input: str) -> Optional[str]:
        """Extract arXiv ID from various input formats."""
        paper_input = paper_input.strip()
        
        # Full URL: https://arxiv.org/abs/2301.12345
        url_match = re.search(r'arxiv\.org/abs/([^/?]+)', paper_input)
        if url_match:
            return url_match.group(1)
        
        # Direct ID: 2301.12345 or cs.AI/0301001
        if re.match(r'^\d{4}\.\d{4,5}$', paper_input) or re.match(r'^[a-z-]+(\.[A-Z]{2})?/\d{7}$', paper_input):
            return paper_input
        
        return None
    
    def _parse_entry(self, entry, arxiv_id: str) -> Dict:
        """Parse XML entry into paper data."""
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        # Basic info
        title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
        summary = entry.find('atom:summary', ns).text.strip().replace('\n', ' ')
        
        # Authors
        authors = []
        for author in entry.findall('atom:author', ns):
            name = author.find('atom:name', ns).text
            authors.append(name)
        
        # Published date
        published = entry.find('atom:published', ns).text
        year = published[:4] if published else ''
        
        # Categories
        categories = []
        for category in entry.findall('atom:category', ns):
            categories.append(category.get('term'))
        
        # PDF link
        pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
        
        return {
            'paper_id': f"arxiv_{arxiv_id}",
            'title': title,
            'authors': authors,
            'year': year,
            'abstract': summary,
            'doi': '',
            'keywords': categories,
            'source': 'arxiv',
            'source_id': arxiv_id,
            'pdf_url': pdf_url,
            'full_text': '',
            'sections': {}
        }