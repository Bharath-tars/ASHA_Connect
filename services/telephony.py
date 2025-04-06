#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Telephony Service for ASHA Connect

This module handles telephony integration for voice-based interactions including:
- Incoming and outgoing call management
- Interactive Voice Response (IVR) functionality
- Call recording and transcription
- Voice-based health assessments

It supports multiple Indian languages and works in offline mode when needed.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union
import time
from datetime import datetime
import tempfile

# Import voice service for speech processing
from services.voice_service import VoiceService

class TelephonyService:
    """Service for handling telephony interactions in ASHA Connect."""
    
    def __init__(self, voice_service: VoiceService):
        """Initialize the telephony service with necessary components.
        
        Args:
            voice_service: Voice service instance for speech processing
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Telephony Service")
        
        self.voice_service = voice_service
        
        # Load telephony configuration
        self.config = self._load_config()
        
        # Initialize call tracking
        self.active_calls = {}
        self.call_history = []
        
        self.logger.info("Telephony Service initialized successfully")
    
    def _load_config(self) -> Dict:
        """Load telephony configuration.
        
        Returns:
            Dictionary with configuration settings
        """
        config_path = os.getenv('TELEPHONY_CONFIG_PATH', 'config/telephony.json')
        default_config = {
            "ivr_enabled": True,
            "recording_enabled": True,
            "max_call_duration": 1800,  # 30 minutes
            "default_language": "hi-IN",
            "supported_languages": ["hi-IN", "bn-IN", "te-IN", "ta-IN", "mr-IN"],
            "offline_mode": {
                "enabled": True,
                "max_offline_calls": 50,
                "storage_path": "data/calls"
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    return loaded_config
            else:
                self.logger.warning(f"Telephony config not found at {config_path}, using default config")
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading telephony config: {str(e)}")
            return default_config
    
    def handle_incoming_call(self, call_data: Dict) -> Dict:
        """Handle an incoming call.
        
        Args:
            call_data: Dictionary with call information
            
        Returns:
            Dictionary with call handling result
        """
        try:
            call_id = call_data.get('call_id', str(int(time.time())))
            caller_number = call_data.get('caller_number', 'unknown')
            language = call_data.get('language', self.config['default_language'])
            
            self.logger.info(f"Handling incoming call: {call_id} from {caller_number}")
            
            # Create call record
            call_record = {
                'call_id': call_id,
                'caller_number': caller_number,
                'direction': 'incoming',
                'start_time': datetime.now(),
                'end_time': None,
                'duration': 0,
                'language': language,
                'status': 'active',
                'recording_path': None,
                'transcription': [],
                'assessment_id': None
            }
            
            # Store in active calls
            self.active_calls[call_id] = call_record
            
            # Start recording if enabled
            recording_path = None
            if self.config['recording_enabled']:
                recording_path = self._start_recording(call_id)
                call_record['recording_path'] = recording_path
            
            # Prepare welcome message
            welcome_message = self._get_welcome_message(language)
            
            # Convert to speech
            audio_data = self.voice_service.text_to_speech(welcome_message, language)
            
            return {
                'success': True,
                'call_id': call_id,
                'action': 'welcome',
                'audio_data': audio_data,
                'next_action': 'collect_input'
            }
        except Exception as e:
            self.logger.error(f"Error handling incoming call: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_welcome_message(self, language: str) -> str:
        """Get welcome message in the specified language.
        
        Args:
            language: Language code
            
        Returns:
            Welcome message text
        """
        # In a real system, these would be loaded from a translation database
        welcome_messages = {
            'hi-IN': "नमस्ते, आशा कनेक्ट में आपका स्वागत है। मैं आपकी स्वास्थ्य आकलन में सहायता कर सकता हूं।",
            'bn-IN': "নমস্কার, আশা কানেক্টে আপনাকে স্বাগতম। আমি আপনার স্বাস্থ্য মূল্যায়নে সাহায্য করতে পারি।",
            'te-IN': "నమస్కారం, ఆశా కనెక్ట్‌కి స్వాగతం. నేను మీ ఆరోగ్య అంచనాలో సహాయం చేయగలను.",
            'ta-IN': "வணக்கம், ஆஷா கனெக்ட்டிற்கு வரவேற்கிறோம். நான் உங்கள் சுகாதார மதிப்பீட்டில் உதவ முடியும்.",
            'mr-IN': "नमस्कार, आशा कनेक्टमध्ये आपले स्वागत आहे. मी आपल्या आरोग्य मूल्यांकनात मदत करू शकतो."
        }
        
        return welcome_messages.get(language, welcome_messages['hi-IN'])
    
    def _start_recording(self, call_id: str) -> str:
        """Start recording a call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            Path to the recording file
        """
        try:
            # Create recordings directory if it doesn't exist
            recordings_dir = os.path.join(self.config['offline_mode']['storage_path'], 'recordings')
            os.makedirs(recordings_dir, exist_ok=True)
            
            # Generate recording filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            recording_path = os.path.join(recordings_dir, f"{call_id}_{timestamp}.wav")
            
            self.logger.info(f"Started recording call {call_id} to {recording_path}")
            
            return recording_path
        except Exception as e:
            self.logger.error(f"Error starting call recording: {str(e)}")
            return None
    
    def process_speech_input(self, call_id: str, audio_data: bytes) -> Dict:
        """Process speech input from a call.
        
        Args:
            call_id: Unique call identifier
            audio_data: Raw audio data bytes
            
        Returns:
            Dictionary with processing result
        """
        try:
            if call_id not in self.active_calls:
                raise ValueError(f"Call {call_id} not found in active calls")
            
            call_record = self.active_calls[call_id]
            language = call_record['language']
            
            # Convert speech to text
            text = self.voice_service.speech_to_text(audio_data, language)
            
            # Add to transcription
            timestamp = datetime.now().strftime('%H:%M:%S')
            call_record['transcription'].append({
                'timestamp': timestamp,
                'speaker': 'caller',
                'text': text
            })
            
            self.logger.info(f"Processed speech input for call {call_id}: {text}")
            
            return {
                'success': True,
                'call_id': call_id,
                'text': text
            }
        except Exception as e:
            self.logger.error(f"Error processing speech input: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_speech_output(self, call_id: str, text: str) -> Dict:
        """Send speech output to a call.
        
        Args:
            call_id: Unique call identifier
            text: Text to convert to speech
            
        Returns:
            Dictionary with result
        """
        try:
            if call_id not in self.active_calls:
                raise ValueError(f"Call {call_id} not found in active calls")
            
            call_record = self.active_calls[call_id]
            language = call_record['language']
            
            # Convert text to speech
            audio_data = self.voice_service.text_to_speech(text, language)
            
            # Add to transcription
            timestamp = datetime.now().strftime('%H:%M:%S')
            call_record['transcription'].append({
                'timestamp': timestamp,
                'speaker': 'system',
                'text': text
            })
            
            self.logger.info(f"Sent speech output for call {call_id}")
            
            return {
                'success': True,
                'call_id': call_id,
                'audio_data': audio_data
            }
        except Exception as e:
            self.logger.error(f"Error sending speech output: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def end_call(self, call_id: str, reason: str = 'normal') -> Dict:
        """End an active call.
        
        Args:
            call_id: Unique call identifier
            reason: Reason for ending the call
            
        Returns:
            Dictionary with result
        """
        try:
            if call_id not in self.active_calls:
                raise ValueError(f"Call {call_id} not found in active calls")
            
            call_record = self.active_calls[call_id]
            
            # Update call record
            call_record['end_time'] = datetime.now()
            call_record['duration'] = (call_record['end_time'] - call_record['start_time']).total_seconds()
            call_record['status'] = 'completed'
            
            # Stop recording if enabled
            if self.config['recording_enabled'] and call_record['recording_path']:
                self._stop_recording(call_id)
            
            # Move from active calls to history
            self.call_history.append(call_record)
            del self.active_calls[call_id]
            
            self.logger.info(f"Ended call {call_id}, duration: {call_record['duration']} seconds, reason: {reason}")
            
            return {
                'success': True,
                'call_id': call_id,
                'duration': call_record['duration'],
                'reason': reason
            }
        except Exception as e:
            self.logger.error(f"Error ending call: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _stop_recording(self, call_id: str) -> bool:
        """Stop recording a call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            call_record = self.active_calls.get(call_id)
            if not call_record or not call_record['recording_path']:
                return False
            
            self.logger.info(f"Stopped recording call {call_id}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error stopping call recording: {str(e)}")
            return False
    
    def make_outgoing_call(self, phone_number: str, language: str = None) -> Dict:
        """Make an outgoing call.
        
        Args:
            phone_number: Phone number to call
            language: Language for the call
            
        Returns:
            Dictionary with call result
        """
        try:
            # Generate call ID
            call_id = f"out_{int(time.time())}"
            
            # Use default language if not specified
            if not language:
                language = self.config['default_language']
            
            self.logger.info(f"Making outgoing call: {call_id} to {phone_number}")
            
            # Create call record
            call_record = {
                'call_id': call_id,
                'phone_number': phone_number,
                'direction': 'outgoing',
                'start_time': datetime.now(),
                'end_time': None,
                'duration': 0,
                'language': language,
                'status': 'dialing',
                'recording_path': None,
                'transcription': [],
                'assessment_id': None
            }
            
            # Store in active calls
            self.active_calls[call_id] = call_record
            
            # In a real system, this would initiate the actual call
            # For simulation, we'll just return the call information
            
            return {
                'success': True,
                'call_id': call_id,
                'status': 'dialing'
            }
        except Exception as e:
            self.logger.error(f"Error making outgoing call: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_call_history(self, limit: int = 50, offset: int = 0) -> List[Dict]:
        """Get call history.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of call history records
        """
        try:
            # Sort by start time (newest first)
            sorted_history = sorted(
                self.call_history,
                key=lambda x: x['start_time'],
                reverse=True
            )
            
            # Apply pagination
            paginated_history = sorted_history[offset:offset+limit]
            
            return paginated_history
        except Exception as e:
            self.logger.error(f"Error getting call history: {str(e)}")
            return []
    
    def get_active_calls(self) -> List[Dict]:
        """Get list of active calls.
        
        Returns:
            List of active call records
        """
        try:
            return list(self.active_calls.values())
        except Exception as e:
            self.logger.error(f"Error getting active calls: {str(e)}")
            return []
    
    def get_call_details(self, call_id: str) -> Optional[Dict]:
        """Get detailed information about a specific call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            Call details dictionary or None if not found
        """
        try:
            # Check active calls first
            if call_id in self.active_calls:
                return self.active_calls[call_id]
            
            # Then check call history
            for call in self.call_history:
                if call['call_id'] == call_id:
                    return call
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting call details: {str(e)}")
            return None
    
    def get_call_transcript(self, call_id: str) -> List[Dict]:
        """Get transcript for a specific call.
        
        Args:
            call_id: Unique call identifier
            
        Returns:
            List of transcript entries
        """
        try:
            call_details = self.get_call_details(call_id)
            if not call_details:
                return []
            
            return call_details.get('transcription', [])
        except Exception as e:
            self.logger.error(f"Error getting call transcript: {str(e)}")
            return []
    
    def change_call_language(self, call_id: str, language: str) -> bool:
        """Change the language for an active call.
        
        Args:
            call_id: Unique call identifier
            language: New language code
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if call_id not in self.active_calls:
                return False
            
            # Verify language is supported
            if language not in self.config['supported_languages']:
                self.logger.warning(f"Unsupported language: {language}")
                return False
            
            # Update language
            self.active_calls[call_id]['language'] = language
            
            self.logger.info(f"Changed language for call {call_id} to {language}")
            
            return True
        except Exception as e:
            self.logger.error(f"Error changing call language: {str(e)}")
            return False