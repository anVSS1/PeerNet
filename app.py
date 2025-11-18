import sys
import os
import warnings
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Suppress spaCy compatibility warnings
warnings.filterwarnings("ignore", message=".*was trained with spaCy.*")

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
    
    # Session configuration
    app.config['SESSION_PERMANENT'] = False
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hour
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

    # Initialize extensions
    Bootstrap4(app)
    # Initialize SocketIO
    socketio.init_app(app, async_mode='threading')

    # Connect to MongoDB
    try:
        connect(
            db=app.config['MONGODB_DB'],
            host=app.config['MONGODB_HOST'],
            port=app.config['MONGODB_PORT'],
            username=app.config.get('MONGODB_USERNAME'),
            password=app.config.get('MONGODB_PASSWORD'),
            authentication_source='admin' if app.config.get('MONGODB_USERNAME') else None
        )
    except Exception as e:
        logger = get_logger(__name__)
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
    app.register_blueprint(ledger_bp, url_prefix='/api')
    app.register_blueprint(batch_bp, url_prefix='/api/batch')
    app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
    app.register_blueprint(search_bp, url_prefix='/api/search')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(reviewers_bp, url_prefix='/api/reviewers')
    app.register_blueprint(prompts_bp, url_prefix='/api/prompts')
    app.register_blueprint(dashboard_bp)

    logger.info("All blueprints registered successfully")
    logger.info("Application started - sessions will expire on restart")

    return app

if __name__ == '__main__':
    try:
        app = create_app()
        
        # Enable debug logging
        logging.basicConfig(level=logging.INFO)
        app.logger.setLevel(logging.INFO)
        
        # Add request logging
        @app.before_request
        def log_request_info():
            from flask import request
            app.logger.debug('Request: %s %s', request.method, request.url)
            if request.get_json(silent=True):
                app.logger.debug('Request JSON: %s', request.get_json())
        
        @app.after_request
        def log_response_info(response):
            app.logger.debug('Response: %s %s', response.status_code, response.status)
            return response
        
        print("\nStarting PeerNet++ in DEBUG mode")
        print(f"Main Dashboard: http://127.0.0.1:5000")
        print(f"Upload Papers: http://127.0.0.1:5000/upload")
        print(f"View Papers: http://127.0.0.1:5000/papers")
        print("\nFeatures: Auto-processing, Beautiful UI, Real-time Analytics")
        print("Debug logging enabled - check console for detailed logs\n")

        socketio.run(app, debug=True, host='127.0.0.1', port=5000, use_reloader=False, allow_unsafe_werkzeug=True)
    except Exception as e:
        import logging
        logging.error("Failed to start application: %s", str(e))
        sys.exit(1)