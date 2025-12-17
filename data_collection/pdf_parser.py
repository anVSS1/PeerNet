"""
PDF Parser with Multi-Provider Vision Support
==============================================
This module uses vision-capable AI models to:
1. Extract ALL text from PDFs (not line-by-line scraping)
2. Describe every figure, chart, and architecture diagram
3. Detect potentially fake graphs or stolen diagrams

Provider Priority:
1. Gemini 2.0 Flash Lite (primary)
2. Groq Llama 4 Scout Vision (fallback - FREE!)
3. PyPDF2/pdfplumber (basic text extraction only)
"""

import google.generativeai as genai
from typing import Dict, Optional, List
import logging
import json
import re
import base64
import httpx
from config import Config

# Fallback imports
try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

logger = logging.getLogger(__name__)


class PDFParser:
    """
    Gemini Vision-based PDF Parser.
    Sends entire PDF to Gemini 1.5 Flash for intelligent extraction.
    Uses vision capability to analyze figures, charts, and diagrams.
    """
    
    def __init__(self):
        """Initialize the Gemini Vision parser."""
        self.api_key = Config.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(Config.GEMINI_VISION_MODEL)
            logger.info(f"PDFParser initialized with {Config.GEMINI_VISION_MODEL}")
        else:
            self.model = None
            logger.warning("No Gemini API key found. PDF parsing will fail.")
    
    def extract_text_and_metadata(self, pdf_path: str) -> Dict:
        """
        Extract text, metadata, and visual descriptions from PDF using Gemini Vision.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Dict with keys: full_text, metadata, sections, visual_descriptions
        """
        if not self.model:
            raise ValueError("Gemini API not configured. Set GEMINI_API_KEY in environment.")
        
        try:
            logger.info(f"Processing PDF with Gemini Vision: {pdf_path}")
            
            # Upload PDF to Gemini
            pdf_file = genai.upload_file(pdf_path, mime_type='application/pdf')
            logger.info(f"PDF uploaded to Gemini: {pdf_file.name}")
            
            # Main extraction prompt - comprehensive
            extraction_prompt = """You are an expert academic paper analyzer. Analyze this PDF document and extract:

## TASK 1: METADATA EXTRACTION
Extract and return as JSON:
- title: The paper's title (exactly as written)
- authors: List of all authors (as array of strings)
- abstract: The full abstract text
- keywords: Any listed keywords (as array)
- year: Publication year if visible
- doi: DOI if present
- affiliations: Author affiliations if visible

## TASK 2: FULL TEXT EXTRACTION
Extract the complete text content of the paper, preserving:
- Section headers (Introduction, Methods, Results, Discussion, etc.)
- All paragraphs and body text
- Mathematical equations (describe them if not extractable)
- Table contents (as structured text)

## TASK 3: VISUAL ANALYSIS (CRITICAL)
For EVERY figure, chart, graph, and diagram:
1. Describe what it shows in detail
2. Note the figure number/caption
3. Analyze if the visualization appears legitimate:
   - Does the data look real or potentially fabricated?
   - Are axis labels and scales appropriate?
   - Does the figure style match academic standards?
4. For architecture diagrams: describe all components and connections

## OUTPUT FORMAT
Return a JSON object with this exact structure:
{
    "metadata": {
        "title": "...",
        "authors": ["..."],
        "abstract": "...",
        "keywords": ["..."],
        "year": "...",
        "doi": "...",
        "affiliations": ["..."]
    },
    "sections": {
        "introduction": "...",
        "methods": "...",
        "results": "...",
        "discussion": "...",
        "conclusion": "...",
        "references": "..."
    },
    "full_text": "Complete concatenated text...",
    "visual_analysis": [
        {
            "figure_id": "Figure 1",
            "type": "chart/graph/diagram/table/image",
            "description": "Detailed description...",
            "caption": "Original caption if present",
            "legitimacy_assessment": "Assessment of whether this appears authentic",
            "concerns": ["Any red flags noted"]
        }
    ],
    "document_assessment": {
        "overall_quality": "high/medium/low",
        "potential_issues": ["List any concerns about the document"]
    }
}"""

            # Call Gemini Vision API
            response = self.model.generate_content(
                [extraction_prompt, pdf_file],
                generation_config=genai.GenerationConfig(
                    temperature=0.1,  # Low temperature for accurate extraction
                    max_output_tokens=32000,  # Large output for full papers
                )
            )
            
            # Clean up uploaded file
            try:
                pdf_file.delete()
            except:
                pass  # Ignore cleanup errors
            
            # Parse response
            result = self._parse_gemini_response(response.text)
            
            logger.info(f"Successfully extracted paper: {result.get('metadata', {}).get('title', 'Unknown')}")
            return result
            
        except Exception as e:
            error_str = str(e).lower()
            # Check if it's a quota/rate limit error
            if '429' in error_str or 'quota' in error_str or 'resource_exhausted' in error_str or 'rate' in error_str:
                logger.warning(f"Gemini quota exhausted, trying Groq Vision fallback: {str(e)}")
                return self._groq_vision_fallback(pdf_path)
            logger.error(f"Error parsing PDF with Gemini Vision: {str(e)}")
            raise
    
    def _groq_vision_fallback(self, pdf_path: str) -> Dict:
        """
        Fallback using Groq Llama 4 Scout Vision when Gemini quota is exhausted.
        Converts PDF to images and sends to Groq vision API in batches of 5.
        """
        groq_api_key = Config.GROQ_API_KEY
        if not groq_api_key:
            logger.warning("No Groq API key, falling back to PyPDF2")
            return self._fallback_extract_pdf(pdf_path)
        
        # Check if pdf2image is available
        if not PDF2IMAGE_AVAILABLE:
            logger.warning("pdf2image not installed, falling back to PyPDF2")
            return self._fallback_extract_pdf(pdf_path)
        
        try:
            logger.info(f"Processing PDF with Groq Llama 4 Scout Vision: {pdf_path}")
            
            # Convert ALL PDF pages to images (will process in batches of 5)
            all_images = convert_from_path(pdf_path, dpi=150)
            total_pages = len(all_images)
            logger.info(f"Converted {total_pages} pages to images")
            
            # Process in batches of 5 (Groq's limit)
            batch_size = 5
            all_results = []
            
            for batch_start in range(0, total_pages, batch_size):
                batch_end = min(batch_start + batch_size, total_pages)
                batch_images = all_images[batch_start:batch_end]
                batch_num = (batch_start // batch_size) + 1
                total_batches = (total_pages + batch_size - 1) // batch_size
                
                logger.info(f"Processing batch {batch_num}/{total_batches} (pages {batch_start+1}-{batch_end})")
                
                # Encode batch images to base64
                import io
                image_data = []
                for i, img in enumerate(batch_images):
                    buffer = io.BytesIO()
                    img.save(buffer, format='JPEG', quality=85)
                    img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                    image_data.append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{img_base64}"
                        }
                    })
                
                # Build extraction prompt (different for first batch vs continuation)
                if batch_start == 0:
                    extraction_prompt = f"""You are an expert academic paper analyzer. Analyze these PDF page images (pages {batch_start+1}-{batch_end} of {total_pages}).

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation, no code blocks.

Extract and return this exact JSON structure:
{{
  "metadata": {{
    "title": "exact paper title",
    "authors": ["author1", "author2"],
    "affiliations": ["affiliation1"],
    "abstract": "full abstract text",
    "keywords": ["keyword1", "keyword2"],
    "year": "2024",
    "doi": "doi if visible"
  }},
  "sections": {{
    "introduction": "text...",
    "methods": "text...",
    "results": "text..."
  }},
  "full_text": "all text concatenated",
  "visual_analysis": [
    {{"figure": "Figure 1", "caption": "...", "description": "..."}}
  ]
}}

Extract ALL text from these pages. Return ONLY the JSON object, nothing else."""
                else:
                    extraction_prompt = f"""Continue analyzing this academic paper. Pages {batch_start+1}-{batch_end} of {total_pages}.

IMPORTANT: Return ONLY valid JSON, no markdown, no explanation.

Return this JSON structure:
{{
  "sections": {{"section_name": "text..."}},
  "full_text": "all text from these pages",
  "visual_analysis": [{{"figure": "Figure X", "caption": "...", "description": "..."}}]
}}

Extract ALL text. Return ONLY the JSON object."""

                # Build message content                # Build message content
                content = [{"type": "text", "text": extraction_prompt}]
                content.extend(image_data)
                
                # Call Groq API
                response = httpx.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                        "messages": [{"role": "user", "content": content}],
                        "temperature": 0.1,
                        "max_tokens": 8192
                    },
                    timeout=120.0
                )
                
                if response.status_code != 200:
                    error_data = response.json() if response.text else {}
                    logger.warning(f"Groq API error on batch {batch_num}: {response.status_code} - {error_data}")
                    # If first batch fails, fall back completely
                    if batch_start == 0:
                        return self._fallback_extract_pdf(pdf_path)
                    # Otherwise, just skip this batch
                    continue
                
                result_text = response.json()["choices"][0]["message"]["content"]
                logger.info(f"Batch {batch_num} extracted {len(result_text)} characters")
                all_results.append(result_text)
            
            # Combine all batch results
            combined_result = self._combine_groq_batch_results(all_results)
            return combined_result
            
        except Exception as e:
            logger.warning(f"Groq Vision fallback failed: {e}, using PyPDF2")
            return self._fallback_extract_pdf(pdf_path)
    
    def _combine_groq_batch_results(self, batch_results: List[str]) -> Dict:
        """Combine results from multiple Groq vision batches into one result."""
        if not batch_results:
            return self._empty_result()
        
        combined = {
            'metadata': {},
            'sections': {},
            'full_text': '',
            'visual_analysis': []
        }
        
        full_text_parts = []
        
        for i, result_text in enumerate(batch_results):
            try:
                parsed = self._parse_gemini_response(result_text)
                
                # First batch has metadata
                if i == 0:
                    combined['metadata'] = parsed.get('metadata', {})
                
                # Combine sections
                sections = parsed.get('sections', {})
                for key, value in sections.items():
                    if key in combined['sections']:
                        combined['sections'][key] += '\n' + value
                    else:
                        combined['sections'][key] = value
                
                # Combine full text
                if parsed.get('full_text'):
                    full_text_parts.append(parsed['full_text'])
                
                # Combine visual analysis
                visual = parsed.get('visual_analysis', [])
                if visual:
                    combined['visual_analysis'].extend(visual)
                    
            except Exception as e:
                logger.warning(f"Error parsing batch {i+1} result: {e}")
                # Still try to use raw text
                full_text_parts.append(result_text)
        
        combined['full_text'] = '\n\n'.join(full_text_parts)
        
        logger.info(f"Combined {len(batch_results)} batches: {len(combined['full_text'])} chars, {len(combined['visual_analysis'])} figures")
        
        return combined
    
    def _empty_result(self) -> Dict:
        """Return empty result structure."""
        return {
            'full_text': '',
            'metadata': {'title': '', 'author': '', 'authors_list': [], 'subject': '', 'keywords': []},
            'sections': {},
            'visual_analysis': []
        }
    
    def _parse_gemini_response(self, response_text: str) -> Dict:
        """Parse Gemini's JSON response into structured data."""
        try:
            # Try to extract JSON from response
            # Handle cases where JSON is wrapped in markdown code blocks
            text = response_text.strip()
            
            if text.startswith('```json'):
                text = text[7:]
            if text.startswith('```'):
                text = text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            text = text.strip()
            
            # Try to find JSON object boundaries (handle extra text after JSON)
            json_start = text.find('{')
            if json_start != -1:
                # Find matching closing brace
                brace_count = 0
                json_end = -1
                for i, char in enumerate(text[json_start:], json_start):
                    if char == '{':
                        brace_count += 1
                    elif char == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            json_end = i + 1
                            break
                
                if json_end != -1:
                    text = text[json_start:json_end]
            
            # Parse JSON
            data = json.loads(text)
            
            # Restructure for compatibility with rest of system
            metadata = data.get('metadata', {})
            sections = data.get('sections', {})
            full_text = data.get('full_text', '')
            visual_analysis = data.get('visual_analysis', [])
            
            # Build comprehensive full text if not provided
            if not full_text and sections:
                full_text = self._build_full_text(sections)
            
            return {
                'full_text': full_text,
                'metadata': {
                    'title': metadata.get('title', ''),
                    'author': ', '.join(metadata.get('authors', [])) if isinstance(metadata.get('authors'), list) else metadata.get('authors', ''),
                    'authors': metadata.get('authors', []),  # Array of author names
                    'authors_list': metadata.get('authors', []),  # Legacy key
                    'subject': metadata.get('abstract', ''),
                    'abstract': metadata.get('abstract', ''),  # Also provide as 'abstract'
                    'keywords': metadata.get('keywords', []),
                    'year': metadata.get('year', ''),
                    'doi': metadata.get('doi', ''),
                    'affiliations': metadata.get('affiliations', [])
                },
                'sections': sections,
                'visual_analysis': visual_analysis,
                'document_assessment': data.get('document_assessment', {})
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse JSON response, using fallback: {str(e)}")
            return self._fallback_parse(response_text)
    
    def _fallback_parse(self, text: str) -> Dict:
        """Fallback parser when JSON extraction fails. Tries to extract metadata from raw text."""
        
        # First, try to extract from JSON-like structure if present
        title = ''
        authors_list = []
        abstract = ''
        
        # Look for title in JSON-like format: "title": "actual title"
        json_title_match = re.search(r'"title"\s*:\s*"([^"]+)"', text)
        if json_title_match:
            title = json_title_match.group(1).strip()[:200]
        
        # Look for authors in JSON-like format
        json_authors_match = re.search(r'"authors"\s*:\s*\[([^\]]+)\]', text)
        if json_authors_match:
            authors_raw = json_authors_match.group(1)
            authors_list = [a.strip().strip('"').strip("'") for a in authors_raw.split(',') if a.strip()][:10]
        
        # Look for abstract in JSON-like format
        json_abstract_match = re.search(r'"abstract"\s*:\s*"([^"]{20,})"', text, re.DOTALL)
        if json_abstract_match:
            abstract = json_abstract_match.group(1).strip()[:2000]
        
        # If JSON extraction didn't work, try traditional patterns
        if not title:
            title_patterns = [
                r'(?i)(?<!["\'{\s])title[:\s]+["\']?([^"\'\n{]+)',  # title: "Something" but not "title":
                r'(?i)^#+\s*(.+?)$',  # Markdown header
                r'(?i)paper\s+title[:\s]+(.+?)(?:\n|$)',
            ]
            for pattern in title_patterns:
                match = re.search(pattern, text, re.MULTILINE)
                if match:
                    candidate = match.group(1).strip()[:200]
                    # Skip if it looks like JSON
                    if not candidate.startswith('{') and not candidate.startswith('"'):
                        title = candidate
                        break
        
        # If still no title, use first line that looks like a real title
        if not title:
            lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 10]
            for line in lines:
                # Skip JSON-like lines
                if not line.startswith('{') and not line.startswith('"') and not line.startswith('['):
                    title = line[:200]
                    break
        
        # Try to extract authors from text if not found in JSON
        if not authors_list:
            author_match = re.search(r'(?i)authors?[:\s]+(.+?)(?:\n\n|\n[A-Z]|\n\d)', text, re.DOTALL)
            if author_match:
                author_text = author_match.group(1)
                authors_list = [a.strip() for a in re.split(r'[,;]|\band\b', author_text) if a.strip() and len(a.strip()) > 2][:10]
        
        # Try to extract abstract if not found in JSON
        if not abstract:
            abstract_match = re.search(r'(?i)abstract[:\s]*\n?(.*?)(?:\n\n|introduction|keywords|\n[A-Z]{2,})', text, re.DOTALL)
            if abstract_match:
                abstract = abstract_match.group(1).strip()[:2000]
        
        logger.info(f"Fallback extracted - Title: '{title[:50]}...', Authors: {len(authors_list)}")
        
        return {
            'full_text': text,
            'metadata': {
                'title': title,
                'author': ', '.join(authors_list),
                'authors': authors_list,  # Array of author names
                'authors_list': authors_list,  # Legacy key
                'subject': abstract,
                'abstract': abstract,  # Also provide as 'abstract'
                'keywords': [],
                'year': '',
                'doi': '',
                'affiliations': []
            },
            'sections': {},
            'visual_analysis': [],
            'document_assessment': {'overall_quality': 'unknown', 'potential_issues': ['Failed to parse structured response']}
        }
    
    def _build_full_text(self, sections: Dict) -> str:
        """Build full text from sections."""
        parts = []
        section_order = ['abstract', 'introduction', 'background', 'related_work', 
                        'methods', 'methodology', 'experiments', 'results', 
                        'discussion', 'conclusion', 'references']
        
        for section in section_order:
            if section in sections and sections[section]:
                parts.append(f"\n\n## {section.upper()}\n\n{sections[section]}")
        
        # Add any sections not in standard order
        for section, content in sections.items():
            if section not in section_order and content:
                parts.append(f"\n\n## {section.upper()}\n\n{content}")
        
        return ''.join(parts).strip()
    
    def _fallback_extract_pdf(self, pdf_path: str) -> Dict:
        """
        Fallback PDF extraction using PyPDF2 or pdfplumber when Gemini quota is exhausted.
        Extracts text only - no vision analysis available.
        """
        logger.info(f"Using fallback PDF extraction for: {pdf_path}")
        
        full_text = ""
        metadata = {}
        
        # Try pdfplumber first (better text extraction)
        if PDFPLUMBER_AVAILABLE:
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    # Extract metadata
                    if pdf.metadata:
                        metadata = {
                            'title': pdf.metadata.get('Title', '') or pdf.metadata.get('/Title', ''),
                            'author': pdf.metadata.get('Author', '') or pdf.metadata.get('/Author', ''),
                            'subject': pdf.metadata.get('Subject', '') or pdf.metadata.get('/Subject', ''),
                        }
                    
                    # Extract text from all pages
                    pages_text = []
                    for page in pdf.pages:
                        text = page.extract_text()
                        if text:
                            pages_text.append(text)
                    full_text = "\n\n".join(pages_text)
                    logger.info(f"pdfplumber extracted {len(full_text)} characters from {len(pdf.pages)} pages")
            except Exception as e:
                logger.warning(f"pdfplumber extraction failed: {e}")
                full_text = ""
        
        # Fallback to PyPDF2 if pdfplumber failed or unavailable
        if not full_text and PYPDF2_AVAILABLE:
            try:
                reader = PdfReader(pdf_path)
                
                # Extract metadata
                if reader.metadata:
                    metadata = {
                        'title': reader.metadata.get('/Title', '') or '',
                        'author': reader.metadata.get('/Author', '') or '',
                        'subject': reader.metadata.get('/Subject', '') or '',
                    }
                
                # Extract text from all pages
                pages_text = []
                for page in reader.pages:
                    text = page.extract_text()
                    if text:
                        pages_text.append(text)
                full_text = "\n\n".join(pages_text)
                logger.info(f"PyPDF2 extracted {len(full_text)} characters from {len(reader.pages)} pages")
            except Exception as e:
                logger.error(f"PyPDF2 extraction failed: {e}")
        
        if not full_text:
            raise ValueError("Both pdfplumber and PyPDF2 failed to extract text. Please try again later when Gemini quota resets.")
        
        # Try to extract title from first lines if not in metadata
        title = metadata.get('title', '')
        if not title and full_text:
            # First non-empty line is often the title
            lines = [l.strip() for l in full_text.split('\n') if l.strip()]
            if lines:
                title = lines[0][:200]  # Limit title length
        
        # Try to detect abstract
        abstract = ""
        abstract_match = re.search(r'(?i)abstract[:\s]*\n?(.*?)(?:\n\n|introduction|keywords)', full_text, re.DOTALL)
        if abstract_match:
            abstract = abstract_match.group(1).strip()[:2000]  # Limit abstract length
        
        return {
            'full_text': full_text,
            'metadata': {
                'title': title,
                'author': metadata.get('author', ''),
                'authors_list': [a.strip() for a in metadata.get('author', '').split(',')] if metadata.get('author') else [],
                'subject': abstract or metadata.get('subject', ''),
                'keywords': [],
                'year': '',
                'doi': '',
                'affiliations': []
            },
            'sections': self._try_extract_sections(full_text),
            'visual_analysis': [],  # No vision analysis available in fallback mode
            'document_assessment': {
                'overall_quality': 'unknown',
                'potential_issues': ['Extracted using fallback parser (PyPDF2/pdfplumber) - no visual analysis available. Gemini quota was exhausted.']
            },
            '_fallback_mode': True  # Flag to indicate fallback was used
        }
    
    def _try_extract_sections(self, full_text: str) -> Dict:
        """Try to extract common paper sections from text."""
        sections = {}
        section_patterns = [
            ('introduction', r'(?i)\bintroduction\b'),
            ('methods', r'(?i)\b(?:methods?|methodology)\b'),
            ('results', r'(?i)\bresults?\b'),
            ('discussion', r'(?i)\bdiscussion\b'),
            ('conclusion', r'(?i)\bconclusions?\b'),
            ('references', r'(?i)\breferences\b'),
        ]
        
        # Find section positions
        positions = []
        for section_name, pattern in section_patterns:
            match = re.search(pattern, full_text)
            if match:
                positions.append((match.start(), section_name))
        
        # Sort by position
        positions.sort(key=lambda x: x[0])
        
        # Extract text between sections
        for i, (pos, name) in enumerate(positions):
            if i + 1 < len(positions):
                next_pos = positions[i + 1][0]
                sections[name] = full_text[pos:next_pos].strip()[:5000]  # Limit section length
            else:
                sections[name] = full_text[pos:pos+5000].strip()  # Last section
        
        return sections
    
    def analyze_visuals_only(self, pdf_path: str) -> List[Dict]:
        """
        Specialized analysis of just the visual elements in a PDF.
        Use this for deeper figure/chart analysis.
        """
        if not self.model:
            raise ValueError("Gemini API not configured.")
        
        try:
            pdf_file = genai.upload_file(pdf_path, mime_type='application/pdf')
            
            visual_prompt = """Analyze ONLY the visual elements in this academic paper.

For each figure, chart, graph, diagram, or table:

1. **Identification**: Figure number/label and type
2. **Content Description**: What does it show? Be very detailed.
3. **Data Analysis**: 
   - What trends or patterns are visible?
   - Are the scales appropriate?
   - Do the numbers make sense?
4. **Authenticity Check**:
   - Does this look like real data or potentially fabricated?
   - Are there any signs of image manipulation?
   - Does the style match the rest of the paper?
5. **Plagiarism Indicators**:
   - Does this look like it could be copied from another source?
   - Are there any watermarks, different fonts, or style inconsistencies?

Return as JSON array of visual analysis objects."""

            response = self.model.generate_content(
                [visual_prompt, pdf_file],
                generation_config=genai.GenerationConfig(temperature=0.1)
            )
            
            try:
                pdf_file.delete()
            except:
                pass
            
            # Parse response
            text = response.text.strip()
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3]
            
            return json.loads(text.strip())
            
        except Exception as e:
            logger.error(f"Error in visual analysis: {str(e)}")
            return []
