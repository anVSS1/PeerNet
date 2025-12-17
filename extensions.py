'''
PeerNet++ Flask Extensions
==========================
Shared Flask extensions used across the application.
Contains the SocketIO instance for real-time WebSocket communication.

Used by:
- app.py: Initializes the SocketIO with Flask app
- socketio_events.py: Defines WebSocket event handlers
- paper_intake.py: Emits real-time progress updates
- review_simulation.py: Emits review status updates
'''

from flask_socketio import SocketIO

# Create a SocketIO instance to be initialized in the app factory
socketio = SocketIO()