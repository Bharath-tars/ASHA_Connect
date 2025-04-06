#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Voice Routes for ASHA Connect

This module defines API endpoints for voice-related functionality including:
- Speech-to-text conversion
- Text-to-speech conversion
- Language detection and management
- Voice interaction handling
"""

import os
import logging
from flask import Blueprint, request, jsonify, g, send_file
from functools import wraps

# Import services
from services.voice_service import VoiceService
from services.user_service import UserService
from data.database import Database

# Create blueprint
voice_bp = Blueprint('voice', __name__)

# Initialize services
db = Database()
voice_service = VoiceService()
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

@voice_bp.route('/speech-to-text', methods=['POST'])
@token_required
def speech_to_text():
    """Convert speech to text.
    
    Expects:
        - Audio file in request data
        - Optional language parameter
    
    Returns:
        JSON with transcribed text
    """
    try:
        # Check if file is in request
        if 'audio' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No audio file provided'
            }), 400
        
        audio_file = request.files['audio']
        
        # Get language preference
        language = request.form.get('language')
        
        # Save audio file temporarily
        temp_path = f"temp_{g.user['id']}_{int(time.time())}.wav"
        audio_file.save(temp_path)
        
        # Convert speech to text
        result = voice_service.speech_to_text(temp_path, language)
        
        # Clean up temporary file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Speech-to-text error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_bp.route('/text-to-speech', methods=['POST'])
@token_required
def text_to_speech():
    """Convert text to speech.
    
    Expects:
        - JSON with text to convert
        - Optional language parameter
    
    Returns:
        Audio file or JSON with error
    """
    try:
        data = request.json
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        # Get text and language
        text = data['text']
        language = data.get('language')
        
        # Convert text to speech
        result = voice_service.text_to_speech(text, language)
        
        if result['success']:
            # Return audio file
            return send_file(
                result['audio_path'],
                mimetype='audio/mpeg',
                as_attachment=True,
                attachment_filename='speech.mp3'
            )
        else:
            return jsonify(result), 400
            
    except Exception as e:
        logger.error(f"Text-to-speech error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_bp.route('/detect-language', methods=['POST'])
@token_required
def detect_language():
    """Detect the language of the given text.
    
    Expects:
        - JSON with text to analyze
    
    Returns:
        JSON with detected language
    """
    try:
        data = request.json
        
        if not data or 'text' not in data:
            return jsonify({
                'success': False,
                'error': 'No text provided'
            }), 400
        
        # Detect language
        language_code = voice_service.detect_language(data['text'])
        
        # Get language name
        language_name = voice_service.language_map.get(language_code, 'Unknown')
        
        return jsonify({
            'success': True,
            'language_code': language_code,
            'language_name': language_name
        }), 200
            
    except Exception as e:
        logger.error(f"Language detection error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_bp.route('/languages', methods=['GET'])
@token_required
def get_languages():
    """Get list of supported languages.
    
    Returns:
        JSON with list of supported languages
    """
    try:
        # Get supported languages
        languages = voice_service.get_supported_languages()
        
        return jsonify({
            'success': True,
            'languages': languages
        }), 200
            
    except Exception as e:
        logger.error(f"Get languages error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_bp.route('/set-language', methods=['POST'])
@token_required
def set_language():
    """Set the current language for voice interactions.
    
    Expects:
        - JSON with language code
    
    Returns:
        JSON with result
    """
    try:
        data = request.json
        
        if not data or 'language' not in data:
            return jsonify({
                'success': False,
                'error': 'No language provided'
            }), 400
        
        # Set language
        success = voice_service.set_language(data['language'])
        
        if success:
            return jsonify({
                'success': True,
                'message': f"Language set to {voice_service.language_map.get(data['language'], data['language'])}"
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Unsupported language'
            }), 400
            
    except Exception as e:
        logger.error(f"Set language error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@voice_bp.route('/conversation', methods=['POST'])
@token_required
def handle_conversation():
    """Handle a voice conversation turn.
    
    Expects:
        - Audio file or text input
        - Conversation context
    
    Returns:
        JSON with response and/or audio file
    """
    try:
        # Check if input is audio or text
        if 'audio' in request.files:
            # Process audio input
            audio_file = request.files['audio']
            
            # Save audio file temporarily
            temp_path = f"temp_{g.user['id']}_{int(time.time())}.wav"
            audio_file.save(temp_path)
            
            # Get language preference
            language = request.form.get('language')
            
            # Convert speech to text
            stt_result = voice_service.speech_to_text(temp_path, language)
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            if not stt_result['success']:
                return jsonify(stt_result), 400
                
            input_text = stt_result['text']
            detected_language = stt_result['language']
            
        elif request.json and 'text' in request.json:
            # Process text input
            input_text = request.json['text']
            detected_language = voice_service.detect_language(input_text)
            
        else:
            return jsonify({
                'success': False,
                'error': 'No input provided'
            }), 400
        
        # Get conversation context
        context = request.json.get('context', {}) if request.json else {}
        
        # In a real implementation, this would process the conversation
        # through a dialogue manager and generate a response
        # Simplified implementation for demonstration
        
        # Mock response
        response = {
            'text': f"I received your message: {input_text}",
            'language': detected_language,
            'context': context,
            'actions': []
        }
        
        # Convert response to speech if requested
        if request.json and request.json.get('speech_response', False):
            tts_result = voice_service.text_to_speech(response['text'], detected_language)
            
            if tts_result['success']:
                response['audio_path'] = tts_result['audio_path']
        
        return jsonify({
            'success': True,
            'response': response
        }), 200
            
    except Exception as e:
        logger.error(f"Conversation error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500