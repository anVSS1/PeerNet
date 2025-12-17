"""
PeerNet++ V3 Configuration
==========================
Multi-Provider AI Setup:
- Gemini: Vision (PDF) + Embeddings
- Groq: Reviewers + Bias Detection + Consensus (Llama 3.3 70B)
"""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # ============================================
    # MONGODB CONFIGURATION
    # ============================================
    # MongoDB Atlas (recommended for production)
    MONGODB_URI = os.getenv('MONGODB_URI', '')
    MONGODB_DB = os.getenv('MONGODB_DB', 'peernet_plus')
    
    # Local MongoDB fallback
    MONGODB_HOST = os.getenv('MONGODB_HOST', 'localhost')
    try:
        MONGODB_PORT = int(os.getenv('MONGODB_PORT', 27017))
    except ValueError:
        MONGODB_PORT = 27017
    MONGODB_USERNAME = os.getenv('MONGODB_USERNAME', '')
    MONGODB_PASSWORD = os.getenv('MONGODB_PASSWORD', '')
    MONGODB_AUTH_DB = os.getenv('MONGODB_AUTH_DB', 'admin')

    # ============================================
    # GEMINI API (Vision + Embeddings)
    # ============================================
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    
    # PDF Vision Model (for figure extraction)
    GEMINI_VISION_MODEL = os.getenv('GEMINI_VISION_MODEL', 'gemini-2.0-flash-lite')
    
    # Embedding Model (for plagiarism vector search)
    GEMINI_EMBEDDING_MODEL = os.getenv('GEMINI_EMBEDDING_MODEL', 'text-embedding-004')
    
    # ============================================
    # GROQ API (Reviewers - Llama 3.1 8B)
    # ============================================
    GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.1-8b-instant')
    GROQ_API_URL = 'https://api.groq.com/openai/v1'
    
    # ============================================
    # OPENROUTER API (Gemma 3 Fallback - FREE)
    # ============================================
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY', '')
    OPENROUTER_MODEL = os.getenv('OPENROUTER_MODEL', 'google/gemma-3-27b-it:free')
    OPENROUTER_API_URL = 'https://openrouter.ai/api/v1'
    
    # ============================================
    # GEMINI THINKING MODEL (Consensus)
    # ============================================
    GEMINI_THINKING_MODEL = os.getenv('GEMINI_THINKING_MODEL', 'gemini-2.5-flash')
    
    # ============================================
    # PLAGIARISM DETECTION
    # ============================================
    try:
        PLAGIARISM_SIMILARITY_THRESHOLD = float(os.getenv('PLAGIARISM_SIMILARITY_THRESHOLD', 0.85))
    except ValueError:
        PLAGIARISM_SIMILARITY_THRESHOLD = 0.85
    
    # ============================================
    # REVIEWER CONFIGURATION
    # ============================================
    try:
        MIN_REVIEWERS = int(os.getenv('MIN_REVIEWERS', 3))
        MAX_REVIEWERS = int(os.getenv('MAX_REVIEWERS', 5))
        REVIEWER_COUNT = int(os.getenv('REVIEWER_COUNT', 4))
    except ValueError:
        MIN_REVIEWERS = 3
        MAX_REVIEWERS = 5
        REVIEWER_COUNT = 4

    # ============================================
    # EXTERNAL APIS
    # ============================================
    OPENALEX_API_URL = os.getenv('OPENALEX_API_URL', 'https://api.openalex.org/works/')
    HF_API_KEY = os.getenv('HF_API_KEY', '')
    HF_MODEL_ZEPHYR = os.getenv('HF_MODEL_ZEPHYR', 'HuggingFaceH4/zephyr-7b-beta')

    # ============================================
    # FLASK SETTINGS
    # ============================================
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    try:
        PORT = int(os.getenv('PORT', 5000))
    except ValueError:
        PORT = 5000

    # ============================================
    # LOGGING
    # ============================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/peernet.log')
