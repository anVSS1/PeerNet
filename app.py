"""
PeerNet++ V3 - SOTA AI Academic Peer Review Platform
=====================================================
2025 Stack:
- Gemini 2.5 Flash-Lite for PDF vision + reviews
- Gemini 2.0 Flash Thinking for consensus
- text-embedding-004 for plagiarism detection
- DSPy for optimized reviewer prompts
- MongoDB Atlas for cloud storage with embeddings

Plagiarism runs FIRST, reviews run SECOND.
"""

import sys
import os
import warnings
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Suppress deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

from flask import Flask
from flask_bootstrap import Bootstrap4
from flask_socketio import SocketIO
from mongoengine import connect
import logging

from extensions import socketio
from config import Config
from utils.logger import setup_logging, get_logger

# Import SocketIO events
import socketio_events

# Import blueprints
from api.papers import papers_bp
from api.reviews import reviews_bp
from api.consensus import consensus_bp
from api.bias_flags import bias_flags_bp
from api.ledger import ledger_bp
from api.batch import batch_bp
from api.analytics import analytics_bp
from api.search import search_bp
from api.auth import auth_bp
from api.reviewers import reviewers_bp
from api.prompts import prompts_bp
from dashboard.routes import dashboard_bp

def create_app(config_class=Config):
    """
    Application factory function.
    """
    app = Flask(__name__, template_folder='dashboard/templates')
    app.config.from_object(config_class)

    # ── SECRET KEY CHECK ──────────────────────────────────────
    if app.config.get('SECRET_KEY') in (None, '', 'dev-secret-key-change-in-production'):
        import secrets as _sec
        generated = _sec.token_hex(32)
        app.config['SECRET_KEY'] = generated
        import warnings
        warnings.warn(
            "SECRET_KEY is not set or is using the insecure default. "
            "A random key has been generated for this run. "
            "Set SECRET_KEY in your .env for stable sessions across restarts.",
            RuntimeWarning,
            stacklevel=2
        )

    # ── Session & cookie hardening ────────────────────────────
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = not app.config.get('DEBUG', False)  # HTTPS in prod

    # Initialize extensions
    Bootstrap4(app)
    # Initialize SocketIO
    socketio.init_app(app, async_mode='threading')

    # Connect to MongoDB (supports both local and Atlas)
    logger = get_logger(__name__)
    try:
        mongodb_uri = app.config.get('MONGODB_URI')
        
        if mongodb_uri:
            # MongoDB Atlas connection (recommended for production)
            logger.info("Connecting to MongoDB Atlas...")
            connect(host=mongodb_uri)
            logger.info("✓ Connected to MongoDB Atlas")
        else:
            # Local MongoDB fallback
            logger.info("Connecting to local MongoDB...")
            connect(
                db=app.config['MONGODB_DB'],
                host=app.config['MONGODB_HOST'],
                port=app.config['MONGODB_PORT'],
                username=app.config.get('MONGODB_USERNAME'),
                password=app.config.get('MONGODB_PASSWORD'),
                authentication_source='admin' if app.config.get('MONGODB_USERNAME') else None
            )
            logger.info("✓ Connected to local MongoDB")
    except Exception as e:
        logger.error("Failed to connect to MongoDB: %s", str(e))
        raise

    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    logger.info("PeerNet++ application starting up")

    # Register blueprints
    app.register_blueprint(papers_bp, url_prefix='/api/papers')
    app.register_blueprint(reviews_bp, url_prefix='/api')
    app.register_blueprint(consensus_bp, url_prefix='/api')
    app.register_blueprint(bias_flags_bp, url_prefix='/api')
    app.register_blueprint(ledger_bp, url_prefix='/api/ledger')  # Fixed: was '/api' — now properly namespaced
    app.register_blueprint(batch_bp, url_prefix='/api/batch')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(reviewers_bp, url_prefix='/api/reviewers')
    app.register_blueprint(prompts_bp, url_prefix='/api/prompts')
    app.register_blueprint(dashboard_bp)

    # ── Security headers (after_request) ──────────────────────
    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'geolocation=(), camera=(), microphone=()'
        # Cache-control for authenticated pages
        if 'text/html' in response.content_type:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
        return response

    logger.info("All blueprints registered successfully")
    logger.info("Security headers enabled")
    logger.info("Application started - sessions will expire on restart")

    return app

if __name__ == '__main__':
    try:
        app = create_app()
        
        # Use INFO level – avoids flooding the terminal with every request
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        app.logger.setLevel(logging.INFO)
        
        print("\n" + "="*60)
        print("🚀 PeerNet++ V3 - SOTA AI Peer Review Platform")
        print("="*60)
        print("\n📊 2025 Multi-Provider Stack:")
        print("   • Gemini 2.0 Flash Lite (PDF Vision - Primary)")
        print("   • Groq Llama 4 Scout (PDF Vision - Fallback)")
        print("   • Groq Llama 3.1 8B (Reviewers - 560 tps)")
        print("   • Gemini 2.5 Flash (Consensus Reasoning)")
        print("   • text-embedding-004 (Plagiarism Detection)")
        print("   • DSPy (Optimized Prompts)")
        print("   • MongoDB Atlas (Cloud Database)")
        print("\n🔒 Plagiarism Check: Runs FIRST (85% threshold)")
        print("\n🌐 URLs:")
        print(f"   Dashboard: http://127.0.0.1:5000")
        print(f"   Upload:    http://127.0.0.1:5000/upload")
        print(f"   Papers:    http://127.0.0.1:5000/papers")
        print("\n" + "="*60 + "\n")

        socketio.run(app, debug=True, host='127.0.0.1', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        import logging
        logging.error("Failed to start application: %s", str(e))
        sys.exit(1)