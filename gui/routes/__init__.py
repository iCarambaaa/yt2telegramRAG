"""Route blueprints for the GUI application."""
from .main import main_bp
from .api import api_bp
from .channels import channels_bp
from .database import database_bp
from .statistics import statistics_bp
from .system import system_bp

__all__ = ['main_bp', 'api_bp', 'channels_bp', 'database_bp', 'statistics_bp', 'system_bp']