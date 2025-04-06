#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
ASHA Connect: Main Application Entry Point

This module serves as the entry point for the ASHA Connect application,
which provides AI-powered healthcare support for ASHA workers in rural India.
"""

import os
import logging
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# Import services
from services.voice_service import VoiceService
from services.health_service import HealthService
from services.user_service import UserService
from services.sync_service import SyncService

# Import data layer
from data.database import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/app.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Initialize Flask application
app = Flask(__name__)

# Initialize services
db = Database()
voice_service = VoiceService()
health_service = HealthService()
user_service = UserService(db)
sync_service = SyncService(db)

# Import and register API routes
from api.routes.voice_routes import voice_bp
from api.routes.health_routes import health_bp
from api.routes.user_routes import user_bp
from api.routes.admin_routes import admin_bp

app.register_blueprint(voice_bp, url_prefix='/api/voice')
app.register_blueprint(health_bp, url_prefix='/api/health')
app.register_blueprint(user_bp, url_prefix='/api/users')
app.register_blueprint(admin_bp, url_prefix='/api/admin')

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'version': os.getenv('APP_VERSION', '1.0.0')
    })

# Main entry point
if __name__ == '__main__':
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')
        
    # Start the application
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV', 'production') == 'development'
    
    logger.info(f"Starting ASHA Connect on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)