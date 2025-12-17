'''
PeerNet++ WebSocket Event Handlers
==================================
Real-time communication handlers for the PeerNet++ platform.

Events:
- connect/disconnect: Client connection management
- join_user_room: Subscribe to personal notifications
- join_paper_room: Subscribe to paper-specific updates
- leave_*_room: Unsubscribe from rooms

Used by frontend JavaScript to receive:
- Upload progress updates
- Review generation status
- Consensus decisions
- Error notifications
'''

from flask_socketio import emit, join_room, leave_room
from extensions import socketio
from utils.logger import get_logger

logger = get_logger(__name__)

@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    logger.debug("Client connected")
    emit('connected', {'message': 'Connected to PeerNet++ real-time service'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    logger.debug("Client disconnected")

@socketio.on('join_user_room')
def handle_join_user_room(user_id):
    """Join user to their personal notification room."""
    try:
        join_room(user_id)
        logger.debug(f"User {user_id} joined their notification room")
        emit('room_joined', {'message': f'Joined notification room for user {user_id}'})
    except Exception as e:
        logger.error(f"Error joining user room: {str(e)}")

@socketio.on('leave_user_room')
def handle_leave_user_room(user_id):
    """Remove user from their personal notification room."""
    try:
        leave_room(user_id)
        logger.debug(f"User {user_id} left their notification room")
    except Exception as e:
        logger.error(f"Error leaving user room: {str(e)}")

@socketio.on('request_analysis_update')
def handle_request_analysis_update(data):
    """Handle client request for analysis status update."""
    try:
        paper_id = data.get('paper_id')
        user_id = data.get('user_id')
        logger.debug(f"Analysis update requested for paper {paper_id} by user {user_id}")
    except Exception as e:
        logger.error(f"Error handling analysis update request: {str(e)}")

def emit_analysis_progress(user_id, paper_id, step, progress, message, status='processing'):
    """
    Emit real-time analysis progress to a specific user.
    
    Args:
        user_id: User ID to send notification to
        paper_id: Paper being analyzed
        step: Current step name (e.g., 'extraction', 'metadata', 'embedding', 'review')
        progress: Progress percentage (0-100)
        message: Human-readable status message
        status: Status type ('processing', 'success', 'error', 'info')
    """
    try:
        socketio.emit('analysis_progress', {
            'paper_id': paper_id,
            'step': step,
            'progress': progress,
            'message': message,
            'status': status,
            'timestamp': str(logger.get_logger(__name__).handlers[0].formatter.formatTime(logger.handlers[0]))
        }, room=str(user_id))
        logger.debug(f"Analysis progress emitted for paper {paper_id}: {step} - {progress}%")
    except Exception as e:
        logger.error(f"Error emitting analysis progress: {str(e)}")