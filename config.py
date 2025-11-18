import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # MongoDB settings
    try:
        MONGODB_HOST = os.getenv('MONGODB_HOST', 'localhost')
        MONGODB_PORT = int(os.getenv('MONGODB_PORT', 27017))
        MONGODB_DB = os.getenv('MONGODB_DB', 'peernet_plus')
    except ValueError as e:
        raise ValueError("Invalid MongoDB configuration: %s" % str(e))

    # Hugging Face settings
    HF_API_KEY = os.getenv('HF_API_KEY')
    HF_INFERENCE_URL = 'https://api-inference.huggingface.co/models/grok-2'
    SPECTER_MODEL = 'allenai/specter'
    
    # Gemini API settings
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    GEMINI_MODEL = 'gemma-3-27b-it'  # Using Gemma 7B instruction-tuned

    # Review settings
    try:
        MIN_REVIEWERS = int(os.getenv('MIN_REVIEWERS', 3))
        MAX_REVIEWERS = int(os.getenv('MAX_REVIEWERS', 5))
    except ValueError as e:
        MIN_REVIEWERS = 3
        MAX_REVIEWERS = 5

    # OpenAlex API
    OPENALEX_API_URL = 'https://api.openalex.org/works/'

    # Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'

    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
