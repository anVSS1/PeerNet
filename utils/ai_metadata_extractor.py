import google.generativeai as genai
import json
import re
from typing import Dict, Optional
from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class AIMetadataExtractor:
    def __init__(self):
        if Config.GEMINI_API_KEY:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel('gemma-7b-it')
        else:
            self.model = None
            logger.warning("Gemini API key not found - AI metadata extraction disabled")

    def extract_metadata(self, text: str) -> Dict:
        """Extract structured metadata from PDF text using AI."""
        if not self.model:
            return self._fallback_extraction(text)
        
        try:
            # Limit text to first 3000 characters for better processing
            text_sample = text[:3000] if len(text) > 3000 else text
            
            prompt = f"""
Extract the following information from this academic paper text and return ONLY a valid JSON object:

{{
    "title": "paper title here",
    "authors": ["author1", "author2"],
    "year": "publication year",
    "abstract": "abstract text here",
    "keywords": ["keyword1", "keyword2"]
}}

Paper text:
{text_sample}

Return only the JSON object, no other text:
"""
            
            response = self.model.generate_content(prompt)
            
            if response and hasattr(response, 'text') and response.text and response.text.strip():
                # Extract JSON from response
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    try:
                        metadata = json.loads(json_match.group())
                        logger.info("AI metadata extraction successful")
                        return self._clean_metadata(metadata)
                    except json.JSONDecodeError:
                        pass
            
            logger.info("AI extraction failed, using fallback")
            
            logger.warning("AI extraction failed, using fallback")
            return self._fallback_extraction(text)
            
        except Exception as e:
            logger.info(f"AI extraction failed: {type(e).__name__}")
            return self._fallback_extraction(text)

    def _clean_metadata(self, metadata: Dict) -> Dict:
        """Clean and validate extracted metadata."""
        cleaned = {
            'title': str(metadata.get('title', 'Unknown Title'))[:200],
            'authors': metadata.get('authors', [])[:5] if isinstance(metadata.get('authors'), list) else [],
            'year': str(metadata.get('year', ''))[:4],
            'abstract': str(metadata.get('abstract', ''))[:1000],
            'keywords': metadata.get('keywords', [])[:10] if isinstance(metadata.get('keywords'), list) else []
        }
        
        # Ensure authors is a list of strings
        if isinstance(cleaned['authors'], str):
            cleaned['authors'] = [cleaned['authors']]
        cleaned['authors'] = [str(author)[:50] for author in cleaned['authors']]
        
        # Ensure keywords is a list of strings
        if isinstance(cleaned['keywords'], str):
            cleaned['keywords'] = [cleaned['keywords']]
        cleaned['keywords'] = [str(kw)[:30] for kw in cleaned['keywords']]
        
        return cleaned

    def _fallback_extraction(self, text: str) -> Dict:
        """Simple fallback extraction if AI fails."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        title = "Unknown Title"
        authors = []
        year = ""
        abstract = ""
        keywords = []
        
        # Find title - first substantial line
        for i, line in enumerate(lines[:15]):
            if len(line) > 15 and not any(skip in line.lower() for skip in ['abstract', 'keywords', 'doi', 'email', '@']):
                title = line[:150]
                
                # Look for authors in next few lines
                for j in range(i+1, min(i+5, len(lines))):
                    author_line = lines[j]
                    if len(author_line) > 5 and len(author_line) < 100:
                        # Simple name pattern check
                        if re.search(r'[A-Z][a-z]+ [A-Z]', author_line):
                            authors = [author_line[:50]]
                            break
                break
        
        # Look for year
        year_match = re.search(r'20\d{2}', text[:2000])
        if year_match:
            year = year_match.group()
        
        # Look for abstract
        abstract_start = text.lower().find('abstract')
        if abstract_start > -1:
            abstract_text = text[abstract_start:abstract_start+500]
            abstract = abstract_text.split('\n')[0][:300] if abstract_text else ""
        
        return {
            'title': title,
            'authors': authors,
            'year': year,
            'abstract': abstract,
            'keywords': keywords
        }