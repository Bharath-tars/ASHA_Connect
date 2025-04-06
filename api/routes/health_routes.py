#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health Routes for ASHA Connect

This module defines API endpoints for health-related functionality including:
- Health assessments
- Condition information
- Treatment recommendations
- Referral management
"""

import os
import logging
from flask import Blueprint, request, jsonify, g
from functools import wraps

# Import services
from services.health_service import HealthService
from services.user_service import UserService
from data.database import Database

# Create blueprint
health_bp = Blueprint('health', __name__)

# Initialize services
db = Database()
health_service = HealthService()
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

# Permission middleware
def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            # Check if user has permission
            if not user_service.check_permission(g.user['id'], permission):
                return jsonify({
                    'success': False,
                    'error': 'Permission denied'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated
    
    return decorator

@health_bp.route('/assess', methods=['POST'])
@token_required
@permission_required('health:assess')
def assess_health():
    """Perform health assessment based on symptoms and patient information.
    
    Expects:
        - JSON with symptoms and patient information
    
    Returns:
        JSON with assessment results
    """
    try:
        data = request.json
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        if 'symptoms' not in data:
            return jsonify({
                'success': False,
                'error': 'Symptoms are required'
            }), 400
            
        if 'patient_info' not in data:
            return jsonify({
                'success': False,
                'error': 'Patient information is required'
            }), 400
        
        # Get language preference
        language = data.get('language', 'en')
        
        # Perform health assessment
        result = health_service.assess_health(
            data['symptoms'],
            data['patient_info'],
            language
        )
        
        if result['success']:
            # Save assessment to database if patient_id is provided
            if 'patient_id' in data['patient_info']:
                # In a real implementation, save to database
                pass
                
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Health assessment error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/conditions/<condition_id>', methods=['GET'])
@token_required
@permission_required('health:view')
def get_condition(condition_id):
    """Get detailed information about a specific health condition.
    
    Args:
        condition_id: ID of the health condition
    
    Query parameters:
        - language: Language code (default: 'en')
    
    Returns:
        JSON with condition information
    """
    try:
        # Get language preference
        language = request.args.get('language', 'en')
        
        # Get condition information
        result = health_service.get_condition_info(condition_id, language)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 404
            
    except Exception as e:
        logger.error(f"Get condition error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/referrals', methods=['GET'])
@token_required
@permission_required('health:view')
def get_referral_facilities():
    """Get recommended healthcare facilities for referral.
    
    Query parameters:
        - conditions: Comma-separated list of condition IDs
        - latitude: Patient location latitude
        - longitude: Patient location longitude
        - urgency: Urgency level (high, medium, low)
    
    Returns:
        JSON with recommended facilities
    """
    try:
        # Get query parameters
        conditions_str = request.args.get('conditions', '')
        latitude = float(request.args.get('latitude', 0))
        longitude = float(request.args.get('longitude', 0))
        urgency = request.args.get('urgency', 'medium')
        
        # Parse condition IDs
        condition_ids = [c.strip() for c in conditions_str.split(',')] if conditions_str else []
        
        # Get location
        location = {
            'latitude': latitude,
            'longitude': longitude
        }
        
        # Get referral facilities
        facilities = health_service.get_referral_facilities(condition_ids, location, urgency)
        
        return jsonify({
            'success': True,
            'facilities': facilities
        }), 200
            
    except Exception as e:
        logger.error(f"Get referral facilities error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@health_bp.route('/history/<patient_id>', methods=['GET'])
@token_required
@permission_required('health:view')
def get_assessment_history(patient_id):
    """Get health assessment history for a patient.
    
    Args:
        patient_id: ID of the patient
    
    Query parameters:
        - limit: Maximum number of results (default: 10)
        - offset: Number of results to skip (default: 0)
    
    Returns:
        JSON with assessment history
    """
    try:
        # Get query parameters
        limit = int(request.args.get('limit', 10))
        offset = int(request.args.get('offset', 0))
        
        # In a real implementation, this would query the database
        # Simplified implementation for demonstration
        
        # Mock assessment history
        assessments = [
            {
                'id': '1',
                'patient_id': patient_id,
                'symptoms': ['fever', 'headache', 'chills'],
                'assessment': [
                    {
                        'id': 'malaria',
                        'name': 'Malaria',
                        'confidence': 85,
                        'requires_referral': True
                    }
                ],
                'recommendations': {
                    'medications': ['artemisinin-based combination therapy'],
                    'home_care': ['rest', 'fluids', 'fever management'],
                    'follow_up': '3 days',
                    'warning_signs': ['severe headache', 'confusion', 'difficulty breathing']
                },
                'referral': {
                    'is_required': True,
                    'urgency': 'urgent',
                    'reason': 'High likelihood of Malaria',
                    'facility_type': 'phc'
                },
                'created_at': '2023-06-15T10:30:00',
                'created_by': g.user['id']
            },
            {
                'id': '2',
                'patient_id': patient_id,
                'symptoms': ['cough', 'fever', 'difficulty breathing'],
                'assessment': [
                    {
                        'id': 'pneumonia',
                        'name': 'Pneumonia',
                        'confidence': 78,
                        'requires_referral': True
                    }
                ],
                'recommendations': {
                    'medications': ['antibiotics as prescribed'],
                    'home_care': ['rest', 'fluids', 'fever management'],
                    'follow_up': '3 days',
                    'warning_signs': ['difficulty breathing', 'bluish lips or face', 'chest pain']
                },
                'referral': {
                    'is_required': True,
                    'urgency': 'urgent',
                    'reason': 'High likelihood of Pneumonia',
                    'facility_type': 'phc'
                },
                'created_at': '2023-05-20T14:15:00',
                'created_by': g.user['id']
            }
        ]
        
        return jsonify({
            'success': True,
            'assessments': assessments,
            'count': len(assessments),
            'total': 2
        }), 200
            
    except Exception as e:
        logger.error(f"Get assessment history error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500