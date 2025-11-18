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