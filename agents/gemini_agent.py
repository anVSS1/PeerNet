'''
PeerNet++ Gemini Agent (Legacy)
===============================
Legacy Gemini integration for metadata extraction from text.

Note: This agent is mostly superseded by:
- PDFParser (for PDF extraction with vision)
- ConsensusAgent (for review consensus)

Still used for:
- Fallback text-based metadata extraction
- Simple text analysis tasks

Model: Configured via GEMINI_MODEL in config
'''

import google.generativeai as genai
from config import Config
import logging
import re
import json

logger = logging.getLogger(__name__)

class GeminiAgent:
    def __init__(self):
        try:
            genai.configure(api_key=Config.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(Config.GEMINI_MODEL)
        except Exception as e:
            logger.error(f"Failed to initialize Gemini Agent: {e}")
            self.model = None

    def extract_metadata_from_text(self, text: str) -> dict:
        if not self.model:
            return {}

        prompt = f"""Extract the title, authors, and abstract from the following text. Return the result as a JSON object with keys 'title', 'authors', and 'abstract'.

Text:
{text}

JSON:
"""

        try:
            response = self.model.generate_content(prompt)
            # Use regex to find the JSON block
            json_match = re.search(r'```json\n({.*\n})```|({.*})', response.text, re.DOTALL)
            if json_match:
                json_str = json_match.group(1) or json_match.group(2)
                return json.loads(json_str)
            else:
                # Fallback for cases where the JSON is not in a code block
                return json.loads(response.text)
        except Exception as e:
            logger.error(f"Error during Gemini metadata extraction: {e}")
            return {}
