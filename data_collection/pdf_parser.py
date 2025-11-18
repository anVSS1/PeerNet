import fitz  # PyMuPDF
import spacy
import requests
from typing import Dict, Optional, List
import logging
import re
from agents.gemini_agent import GeminiAgent

logger = logging.getLogger(__name__)

class PDFParser:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            logger.warning("spaCy model 'en_core_web_sm' not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        self.gemini_agent = GeminiAgent()

    def extract_text_and_metadata(self, pdf_path: str) -> Dict:
        """
        Extract full text, abstract, and sections from PDF.
        """
        try:
            doc = fitz.open(pdf_path)
            full_text = ""
            
            # Extract text from all pages
            pages_content = []
            for page in doc:
                full_text += page.get_text()
                if len(pages_content) == 0: # Only need the first page for layout analysis
                    pages_content.append(page.get_text("dict"))
            
            metadata = self._extract_metadata_with_gemini(full_text)

            # Fallback to other methods if Gemini fails
            if not metadata.get('title') or not metadata.get('author'):
                doc_metadata = self._extract_doc_metadata(doc)
                if not metadata.get('title'):
                    metadata['title'] = doc_metadata.get('title', '')
                if not metadata.get('author'):
                    metadata['author'] = doc_metadata.get('author', '')

            if not metadata.get('title') or not metadata.get('author'):
                layout_metadata = self._extract_title_and_authors_from_layout(pages_content)
                if not metadata.get('title'):
                    metadata['title'] = layout_metadata.get('title', '')
                if not metadata.get('author'):
                    metadata['author'] = layout_metadata.get('author', '')

            if metadata.get('title') and (not metadata.get('author') or not metadata.get('subject')):
                semantic_meta = self._fetch_metadata_from_semantic_scholar(metadata['title'])
                if semantic_meta:
                    if not metadata.get('author'):
                        metadata['author'] = semantic_meta.get('authors', '')
                    if not metadata.get('subject') and semantic_meta.get('abstract'):
                         metadata['subject'] = semantic_meta.get('abstract', '')

            doc.close()

            # Extract sections using spaCy if available
            sections = self._extract_sections(full_text) if self.nlp else {}

            return {
                'full_text': full_text,
                'metadata': metadata,
                'sections': sections
            }
        except Exception as e:
            logger.error(f"Error parsing PDF {pdf_path}: {str(e)}")
            raise

    def _extract_metadata_with_gemini(self, text: str) -> Dict:
        """Extracts metadata using the Gemini Agent."""
        if self.gemini_agent:
            return self.gemini_agent.extract_metadata_from_text(text)
        return {}

    def _extract_doc_metadata(self, doc: fitz.Document) -> Dict:
        """Extracts metadata from the PDF's properties."""
        if not doc.metadata:
            return {}
        return {
            'title': doc.metadata.get('title', ''),
            'author': doc.metadata.get('author', ''),
            'subject': doc.metadata.get('subject', ''),
            'creator': doc.metadata.get('creator', ''),
        }

    def _extract_title_and_authors_from_layout(self, pages_content: List[Dict]) -> Dict:
        """
        Extracts title and authors from the first page using layout analysis (font size, position).
        """
        if not pages_content:
            return {}

        first_page_blocks = pages_content[0].get("blocks", [])
        if not first_page_blocks:
            return {}

        text_blocks = []
        for block in first_page_blocks:
            if block['type'] == 0:  # Text block
                for line in block['lines']:
                    for span in line['spans']:
                        text_blocks.append({
                            "text": span['text'],
                            "size": span['size'],
                            "bbox": span['bbox'],
                        })

        if not text_blocks:
            return {}

        # Title extraction
        largest_size = max(block['size'] for block in text_blocks)
        title_candidates = []
        last_y = 0
        for block in sorted(text_blocks, key=lambda x: x['bbox'][1]):
            if abs(block['size'] - largest_size) < 1:
                if last_y != 0 and block['bbox'][1] - last_y > 20:  # Increased vertical gap
                    break
                title_candidates.append(block)
                last_y = block['bbox'][3]
            if len(title_candidates) > 5: # Limit to first 5 blocks
                break
        
        title = " ".join(candidate['text'] for candidate in title_candidates).strip()
        if len(title) > 300: # Increased length limit
            title = title[:300] + "..."

        # Author extraction
        title_y_pos = max(candidate['bbox'][3] for candidate in title_candidates) if title_candidates else 0
        author_candidates = []
        for block in text_blocks:
            if block['bbox'][1] > title_y_pos and block['size'] < largest_size:
                # Stop at abstract or introduction
                if any(keyword in block['text'].lower() for keyword in ['abstract', 'introduction', 'keywords']):
                    break
                author_candidates.append(block)
        
        authors_text = " ".join(candidate['text'].strip() for candidate in sorted(author_candidates, key=lambda x: x['bbox'][0])).strip()
        
        # Clean author string
        authors = []
        # Split by common delimiters and try to identify names
        potential_authors = re.split(r',| and ', authors_text)
        for author in potential_authors:
            author = author.strip()
            # Remove affiliations and other noise
            author = re.sub(r'\(.*?\)', '', author) # Remove anything in parentheses
            author = re.sub(r'\[.*?\]', '', author) # Remove anything in brackets
            author = re.sub(r'\d', '', author) # Remove numbers
            # A simple heuristic for names: at least two capitalized words
            if len(re.findall(r'[A-Z][a-z]+', author)) >= 2:
                authors.append(author)

        authors = ", ".join(authors)

        return {"title": title, "author": authors}


    def _fetch_metadata_from_semantic_scholar(self, title: str) -> Optional[Dict]:
        """Fetches metadata from the Semantic Scholar API based on the paper title."""
        if not title:
            return None
        try:
            response = requests.get(
                'https://api.semanticscholar.org/graph/v1/paper/search',
                params={'query': title, 'fields': 'authors,abstract'}
            )
            response.raise_for_status()
            data = response.json()
            if data.get('total', 0) > 0:
                paper_data = data['data'][0]
                authors = ", ".join(author['name'] for author in paper_data.get('authors', []))
                return {
                    'authors': authors,
                    'abstract': paper_data.get('abstract', '')
                }
        except requests.exceptions.RequestException as e:
            logger.warning(f"Semantic Scholar API request failed: {e}")
        return None

    def _extract_sections(self, text: str) -> Dict[str, str]:
        """
        Use spaCy to identify and extract paper sections.
        """
        if not self.nlp:
            return {}

        doc = self.nlp(text)
        sections = {}
        current_section = None
        section_text = []

        section_headers = {
            'abstract': ['abstract'],
            'introduction': ['introduction', 'intro'],
            'methods': ['methods', 'methodology', 'materials and methods'],
            'results': ['results', 'findings'],
            'discussion': ['discussion', 'conclusion', 'conclusions']
        }

        lines = text.split('\n')
        for line in lines:
            line_lower = line.lower().strip()
            found_section = False
            for section_name, keywords in section_headers.items():
                if any(line_lower.startswith(keyword) for keyword in keywords):
                    if current_section and section_text:
                        sections[current_section] = '\n'.join(section_text).strip()
                    current_section = section_name
                    section_text = [line]
                    found_section = True
                    break
            
            if not found_section and current_section:
                section_text.append(line)

        if current_section and section_text:
            sections[current_section] = '\n'.join(section_text).strip()

        return sections