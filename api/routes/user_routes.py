#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
User Routes for ASHA Connect

This module defines API endpoints for user-related functionality including:
- User authentication (login/logout)
- User profile management
- Password management
- User preferences
"""

import os
import logging
import time
from flask import Blueprint, request, jsonify, g
from functools import wraps

# Import services
from services.user_service import UserService
from data.database import Database

# Create blueprint
user_bp = Blueprint('user', __name__)

# Initialize services
db = Database()
user_service = UserService(db)

# Configure logging
logger = logging.getLogger(__name__)

# Authentication middleware
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

@user_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user and generate token.
    
    Expects:
        - JSON with username and password
    
    Returns:
        JSON with authentication result and token if successful
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Check required fields
        if 'username' not in data or 'password' not in data:
            return jsonify({
                'success': False,
                'error': 'Username and password are required'
            }), 400
        
        # Authenticate user
        result = user_service.authenticate(data['username'], data['password'])
        
        if result['success']:
            # Update last login time
            user_service.update_last_login(result['user']['id'])
            return jsonify(result), 200
        else:
            return jsonify(result), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Authentication failed'
        }), 500

@user_bp.route('/profile', methods=['GET'])
@token_required
def get_profile():
    """Get user profile information.
    
    Returns:
        JSON with user profile information
    """
    try:
        # Get user from context (set by token_required)
        user = g.user
        
        return jsonify({
            'success': True,
            'user': user
        }), 200
            
    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_bp.route('/profile', methods=['PUT'])
@token_required
def update_profile():
    """Update user profile information.
    
    Expects:
        - JSON with updated profile information
    
    Returns:
        JSON with updated user profile
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Get user from context
        user_id = g.user['id']
        
        # Update user profile
        result = user_service.update_user(user_id, data, user_id)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Update profile error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_bp.route('/change-password', methods=['POST'])
@token_required
def change_password():
    """Change user password.
    
    Expects:
        - JSON with current password and new password
    
    Returns:
        JSON with result
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Check required fields
        if 'current_password' not in data or 'new_password' not in data:
            return jsonify({
                'success': False,
                'error': 'Current password and new password are required'
            }), 400
        
        # Get user from context
        user_id = g.user['id']
        
        # Verify current password
        auth_result = user_service.authenticate(g.user['username'], data['current_password'])
        
        if not auth_result['success']:
            return jsonify({
                'success': False,
                'error': 'Current password is incorrect'
            }), 401
        
        # Update password
        update_data = {'password': data['new_password']}
        result = user_service.update_user(user_id, update_data, user_id)
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Password changed successfully'
            }), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Change password error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_bp.route('/preferences', methods=['GET'])
@token_required
def get_preferences():
    """Get user preferences.
    
    Returns:
        JSON with user preferences
    """
    try:
        # In a real implementation, this would fetch preferences from the database
        # Simplified implementation for demonstration
        
        # Mock preferences
        preferences = {
            'language': 'hi-IN',
            'notifications_enabled': True,
            'theme': 'light',
            'font_size': 'medium'
        }
        
        return jsonify({
            'success': True,
            'preferences': preferences
        }), 200
            
    except Exception as e:
        logger.error(f"Get preferences error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@user_bp.route('/preferences', methods=['PUT'])
@token_required
def update_preferences():
    """Update user preferences.
    
    Expects:
        - JSON with updated preferences
    
    Returns:
        JSON with updated preferences
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # In a real implementation, this would update preferences in the database
        # Simplified implementation for demonstration
        
        # Mock updated preferences
        preferences = data
        
        return jsonify({
            'success': True,
            'preferences': preferences,
            'message': 'Preferences updated successfully'
        }), 200
            
    except Exception as e:
        logger.error(f"Update preferences error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500