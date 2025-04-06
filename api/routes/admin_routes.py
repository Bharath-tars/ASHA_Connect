#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Admin Routes for ASHA Connect

This module defines API endpoints for admin-related functionality including:
- User management
- System configuration
- Reporting and analytics
"""

import os
import logging
from flask import Blueprint, request, jsonify, g
from functools import wraps

# Import services
from services.user_service import UserService
from services.sync_service import SyncService
from data.database import Database

# Create blueprint
admin_bp = Blueprint('admin', __name__)

# Initialize services
db = Database()
user_service = UserService(db)
sync_service = SyncService(db)

# Configure logging
logger = logging.getLogger(__name__)

# Authentication middleware from user_routes
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Get token from header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({
                'success': False,
                'error': 'Token is missing'
            }), 401
        
        # Verify token
        result = user_service.verify_token(token)
        
        if not result['success']:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Invalid token')
            }), 401
        
        # Store user in request context
        g.user = result['user']
        
        return f(*args, **kwargs)
    
    return decorated

# Admin permission middleware
def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if user is admin
        if g.user['role'] != 'admin':
            return jsonify({
                'success': False,
                'error': 'Admin privileges required'
            }), 403
        
        return f(*args, **kwargs)
    
    return decorated

@admin_bp.route('/users', methods=['GET'])
@token_required
@admin_required
def list_users():
    """List all users with optional filtering and pagination.
    
    Query parameters:
        - page: Page number (default: 1)
        - limit: Results per page (default: 20)
        - role: Filter by role
        - is_active: Filter by active status
    
    Returns:
        JSON with list of users and pagination info
    """
    try:
        # Get query parameters
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        # Build filters
        filters = {}
        
        if 'role' in request.args:
            filters['role'] = request.args.get('role')
            
        if 'is_active' in request.args:
            filters['is_active'] = request.args.get('is_active').lower() == 'true'
        
        # Get users
        result = user_service.list_users(filters, page, limit)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"List users error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/users/<user_id>', methods=['GET'])
@token_required
@admin_required
def get_user(user_id):
    """Get detailed information about a specific user.
    
    Args:
        user_id: ID of the user to retrieve
    
    Returns:
        JSON with user information
    """
    try:
        # Get user
        result = user_service.get_user(user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/users', methods=['POST'])
@token_required
@admin_required
def create_user():
    """Create a new user.
    
    Expects:
        - JSON with user information
    
    Returns:
        JSON with created user information
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Create user
        result = user_service.create_user(data, g.user['id'])
        
        if result['success']:
            return jsonify(result), 201
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Create user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/users/<user_id>', methods=['PUT'])
@token_required
@admin_required
def update_user(user_id):
    """Update an existing user.
    
    Args:
        user_id: ID of the user to update
    
    Expects:
        - JSON with updated user information
    
    Returns:
        JSON with updated user information
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Update user
        result = user_service.update_user(user_id, data, g.user['id'])
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Update user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/users/<user_id>', methods=['DELETE'])
@token_required
@admin_required
def delete_user(user_id):
    """Delete a user.
    
    Args:
        user_id: ID of the user to delete
    
    Returns:
        JSON with deletion result
    """
    try:
        # Delete user
        result = user_service.delete_user(user_id, g.user['id'])
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Delete user error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/sync/status', methods=['GET'])
@token_required
@admin_required
def get_sync_status():
    """Get the current synchronization status.
    
    Returns:
        JSON with sync status information
    """
    try:
        # Get sync status
        result = sync_service.get_sync_status()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Get sync status error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/sync/trigger', methods=['POST'])
@token_required
@admin_required
def trigger_sync():
    """Trigger data synchronization.
    
    Returns:
        JSON with sync result
    """
    try:
        # Trigger sync
        result = sync_service.sync_data(force=True)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Trigger sync error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/sync/retry-failed', methods=['POST'])
@token_required
@admin_required
def retry_failed_sync():
    """Retry failed synchronization items.
    
    Returns:
        JSON with retry result
    """
    try:
        # Retry failed sync
        result = sync_service.retry_failed_sync()
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Retry failed sync error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/system/info', methods=['GET'])
@token_required
@admin_required
def get_system_info():
    """Get system information.
    
    Returns:
        JSON with system information
    """
    try:
        # Get system information
        import platform
        import psutil
        from datetime import datetime
        
        # Application info
        app_info = {
            'name': os.getenv('APP_NAME', 'ASHA Connect'),
            'version': os.getenv('APP_VERSION', '1.0.0'),
            'environment': os.getenv('FLASK_ENV', 'production'),
            'start_time': datetime.now().isoformat()
        }
        
        # System info
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(),
            'memory_total': psutil.virtual_memory().total,
            'memory_available': psutil.virtual_memory().available
        }
        
        # Database info
        db_info = {
            'online': db.is_online(),
            'type': 'MongoDB' if db.is_online() else 'SQLite (offline)',
            'connection_string': db.mongo_uri if db.is_online() else db.sqlite_path
        }
        
        return jsonify({
            'success': True,
            'app': app_info,
            'system': system_info,
            'database': db_info
        }), 200
            
    except Exception as e:
        logger.error(f"Get system info error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/system/logs', methods=['GET'])
@token_required
@admin_required
def get_logs():
    """Get application logs.
    
    Query parameters:
        - lines: Number of lines to retrieve (default: 100)
        - level: Minimum log level (default: 'INFO')
    
    Returns:
        JSON with log entries
    """
    try:
        # Get query parameters
        lines = int(request.args.get('lines', 100))
        level = request.args.get('level', 'INFO').upper()
        
        # Get log file path
        log_file = 'logs/app.log'
        
        if not os.path.exists(log_file):
            return jsonify({
                'success': False,
                'error': 'Log file not found'
            }), 404
        
        # Read log file
        with open(log_file, 'r') as f:
            log_lines = f.readlines()
        
        # Filter by level and limit lines
        log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        min_level_index = log_levels.index(level) if level in log_levels else 0
        
        filtered_logs = []
        for line in reversed(log_lines):
            for log_level in log_levels[min_level_index:]:
                if f' - {log_level} - ' in line:
                    filtered_logs.append(line.strip())
                    break
            
            if len(filtered_logs) >= lines:
                break
        
        return jsonify({
            'success': True,
            'logs': filtered_logs,
            'count': len(filtered_logs)
        }), 200
            
    except Exception as e:
        logger.error(f"Get logs error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@admin_bp.route('/reports/usage', methods=['GET'])
@token_required
@admin_required
def get_usage_report():
    """Get system usage report.
    
    Query parameters:
        - period: Time period (day, week, month) (default: 'week')
        - start_date: Start date (YYYY-MM-DD) (optional)
        - end_date: End date (YYYY-MM-DD) (optional)
    
    Returns:
        JSON with usage statistics
    """
    try:
        # Get query parameters
        period = request.args.get('period', 'week')
        
        # In a real implementation, this would query usage data from the database
        # Simplified implementation for demonstration
        
        # Mock usage data
        usage_data = {
            'assessments_count': 120,
            'patients_count': 45,
            'active_users': 8,
            'offline_usage_percent': 35,
            'average_assessment_time': 180,  # seconds
            'referrals_count': 18,
            'by_condition': {
                'malaria': 22,
                'dengue': 15,
                'diarrhea': 38,
                'pneumonia': 25,
                'anemia': 20
            },
            'by_village': {
                'Rajpur': 35,
                'Chandpur': 28,
                'Nayagaon': 42,
                'Sundarpur': 15
            }
        }
        
        return jsonify({
            'success': True,
            'period': period,
            'data': usage_data
        }), 200
            
    except Exception as e:
        logger.error(f"Get usage report error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500