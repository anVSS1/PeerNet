import json
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class JSONHandler:
    @staticmethod
    def parse_paper_json(json_data: str) -> Optional[Dict]:
        """
        Parse JSON string or dict into paper data format.
        Expects OpenAlex-compatible format.
        """
        try:
            if isinstance(json_data, str):
                data = json.loads(json_data)
            elif isinstance(json_data, dict):
                data = json_data
            else:
                raise ValueError("Input must be JSON string or dict")

            # Normalize to our internal format
            paper_data = {
                'paper_id': data.get('id', data.get('paper_id', '')),
                'title': data.get('title', ''),
                'authors': data.get('authors', []),
                'year': str(data.get('year', data.get('publication_year', ''))),
                'abstract': data.get('abstract', ''),
                'doi': data.get('doi', ''),
                'full_text': data.get('full_text', ''),
                'sections': data.get('sections', {}),
                'keywords': data.get('keywords', []),
                'source': 'json'
            }

            # Clean up paper_id if it's a full URL
            if paper_data['paper_id'].startswith('https://openalex.org/'):
                paper_data['paper_id'] = paper_data['paper_id'].replace('https://openalex.org/', '')

            return paper_data

        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON format: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error parsing JSON data: {str(e)}")
            return None

    @staticmethod
    def validate_paper_data(paper_data: Dict) -> bool:
        """
        Validate that paper data has required fields.
        """
        required_fields = ['paper_id', 'title']
        for field in required_fields:
            if not paper_data.get(field):
                logger.error(f"Missing required field: {field}")
                return False
        return True
