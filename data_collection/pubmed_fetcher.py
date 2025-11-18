import requests
import xml.etree.ElementTree as ET
from typing import Dict, Optional
import re
from utils.logger import get_logger

logger = get_logger(__name__)

class PubmedFetcher:
    def __init__(self):
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def fetch_paper(self, paper_input: str) -> Optional[Dict]:
        """Fetch paper from PubMed API."""
        try:
            # Extract PMID
            pmid = self._extract_pmid(paper_input)
            if not pmid:
                logger.error(f"Invalid PubMed ID format: {paper_input}")
                return None
            
            # Fetch paper data
            params = {
                'db': 'pubmed',
                'id': pmid,
                'retmode': 'xml',
                'rettype': 'abstract'
            }
            
            response = requests.get(f"{self.base_url}/efetch.fcgi", params=params, timeout=10)
            response.raise_for_status()
            
            # Parse XML response
            root = ET.fromstring(response.content)
            articles = root.findall('.//PubmedArticle')
            
            if not articles:
                logger.error(f"No paper found for PMID: {pmid}")
                return None
            
            article = articles[0]
            paper_data = self._parse_article(article, pmid)
            return paper_data
            
        except Exception as e:
            logger.error(f"Error fetching from PubMed: {str(e)}")
            return None
    
    def _extract_pmid(self, paper_input: str) -> Optional[str]:
        """Extract PMID from various input formats."""
        paper_input = paper_input.strip()
        
        # PMC ID: PMC1234567
        if paper_input.startswith('PMC'):
            # Convert PMC to PMID using elink
            try:
                params = {
                    'dbfrom': 'pmc',
                    'db': 'pubmed',
                    'id': paper_input[3:],  # Remove PMC prefix
                    'retmode': 'xml'
                }
                response = requests.get(f"{self.base_url}/elink.fcgi", params=params, timeout=10)
                root = ET.fromstring(response.content)
                pmid_elem = root.find('.//Id')
                return pmid_elem.text if pmid_elem is not None else None
            except:
                return None
        
        # Direct PMID: 12345678
        if re.match(r'^\d{7,8}$', paper_input):
            return paper_input
        
        return None
    
    def _parse_article(self, article, pmid: str) -> Dict:
        """Parse XML article into paper data."""
        # Basic info
        title_elem = article.find('.//ArticleTitle')
        title = title_elem.text if title_elem is not None else 'Unknown Title'
        
        abstract_elem = article.find('.//AbstractText')
        abstract = abstract_elem.text if abstract_elem is not None else ''
        
        # Authors
        authors = []
        for author in article.findall('.//Author'):
            last_name = author.find('LastName')
            first_name = author.find('ForeName')
            if last_name is not None and first_name is not None:
                authors.append(f"{first_name.text} {last_name.text}")
        
        # Publication year
        year_elem = article.find('.//PubDate/Year')
        year = year_elem.text if year_elem is not None else ''
        
        # DOI
        doi = ''
        for article_id in article.findall('.//ArticleId'):
            if article_id.get('IdType') == 'doi':
                doi = article_id.text
                break
        
        # Keywords/MeSH terms
        keywords = []
        for mesh in article.findall('.//MeshHeading/DescriptorName'):
            keywords.append(mesh.text)
        
        return {
            'paper_id': f"pubmed_{pmid}",
            'title': title,
            'authors': authors,
            'year': year,
            'abstract': abstract,
            'doi': doi,
            'keywords': keywords,
            'source': 'pubmed',
            'source_id': pmid,
            'full_text': '',
            'sections': {}
        }