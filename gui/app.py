"""Flask application factory for the GUI management interface."""
import os
from flask import Flask
from flask_socketio import SocketIO

from .config import config

# Initialize extensions
socketio = SocketIO()

def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    socketio.init_app(
        app,
        async_mode=app.config['SOCKETIO_ASYNC_MODE'],
        cors_allowed_origins=app.config['SOCKETIO_CORS_ALLOWED_ORIGINS']
    )
    
    # Register blueprints
    from .routes import main_bp, api_bp, channels_bp, database_bp, statistics_bp, system_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(channels_bp, url_prefix='/channels')
    app.register_blueprint(database_bp, url_prefix='/database')
    app.register_blueprint(statistics_bp, url_prefix='/statistics')
    app.register_blueprint(system_bp, url_prefix='/system')
    
    # Register WebSocket events
    from . import websocket_events
    
    return app