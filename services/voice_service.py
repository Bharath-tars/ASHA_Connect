#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Voice Service for ASHA Connect

This module handles all voice-related functionality including:
- Speech-to-text conversion
- Text-to-speech conversion
- Language detection and translation
- Voice interaction management

It supports multiple Indian languages and works in offline mode when needed.
"""

import os
import logging
import tempfile
from typing import Dict, List, Optional, Tuple, Union

# Speech recognition and synthesis
import speech_recognition as sr
import pyttsx3

# For offline mode
import pickle
import numpy as np

class VoiceService:
    """Service for handling voice interactions in ASHA Connect."""
    
    def __init__(self):
        """Initialize the voice service with necessary components."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Voice Service")
        
        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()
        
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        
        # Set default language
        self.current_language = os.getenv('VOICE_LANGUAGE', 'hi-IN')
        
        # Language mapping for supported languages
        self.language_map = {
            'hi-IN': 'Hindi',
            'bn-IN': 'Bengali',
            'te-IN': 'Telugu',
            'ta-IN': 'Tamil',
            'mr-IN': 'Marathi',
            'gu-IN': 'Gujarati',
            'kn-IN': 'Kannada',
            'ml-IN': 'Malayalam',
            'pa-IN': 'Punjabi',
            'en-IN': 'English'
        }
        
        # Load offline models if available
        self.offline_models = self._load_offline_models()
        
        self.logger.info(f"Voice Service initialized with default language: {self.language_map[self.current_language]}")
    
    def speech_to_text(self, audio_data: Union[bytes, str], language: Optional[str] = None) -> Dict:
        """Convert speech to text.
        
        Args:
            audio_data: Audio data as bytes or path to audio file
            language: Language code (e.g., 'hi-IN' for Hindi)
            
        Returns:
            Dict containing text and confidence score
        """
        if language is None:
            language = self.current_language
            
        self.logger.info(f"Converting speech to text in {self.language_map.get(language, language)}")
        
        try:
            # If online, use cloud-based recognition
            if self._is_online():
                return self._online_speech_to_text(audio_data, language)
            else:
                # Fall back to offline recognition
                return self._offline_speech_to_text(audio_data, language)
                
        except Exception as e:
            self.logger.error(f"Speech-to-text error: {str(e)}")
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }
    
    def text_to_speech(self, text: str, language: Optional[str] = None) -> Dict:
        """Convert text to speech.
        
        Args:
            text: Text to convert to speech
            language: Language code (e.g., 'hi-IN' for Hindi)
            
        Returns:
            Dict containing path to audio file or audio data
        """
        if language is None:
            language = self.current_language
            
        self.logger.info(f"Converting text to speech in {self.language_map.get(language, language)}")
        
        try:
            # Create temporary file for audio output
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp3')
            temp_filename = temp_file.name
            temp_file.close()
            
            # Set voice properties
            voices = self.tts_engine.getProperty('voices')
            gender = os.getenv('VOICE_GENDER', 'female').lower()
            
            # Select appropriate voice based on language and gender
            for voice in voices:
                if language in voice.id and (gender in voice.id.lower() or gender in voice.name.lower()):
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', 150)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.9)  # Volume (0.0 to 1.0)
            
            # Convert text to speech
            self.tts_engine.save_to_file(text, temp_filename)
            self.tts_engine.runAndWait()
            
            return {
                'success': True,
                'audio_path': temp_filename,
                'language': language
            }
            
        except Exception as e:
            self.logger.error(f"Text-to-speech error: {str(e)}")
            return {
                'success': False,
                'audio_path': '',
                'error': str(e)
            }
    
    def detect_language(self, text: str) -> str:
        """Detect the language of the given text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Detected language code
        """
        # This is a simplified implementation
        # In a production system, use a proper language detection library
        
        # Common words/patterns in different Indian languages
        language_patterns = {
            'hi-IN': ['नमस्ते', 'आप', 'है', 'मैं', 'और'],
            'bn-IN': ['নমস্কার', 'আপনি', 'আমি', 'এবং'],
            'te-IN': ['నమస్కారం', 'మీరు', 'నేను', 'మరియు'],
            'ta-IN': ['வணக்கம்', 'நீங்கள்', 'நான்', 'மற்றும்'],
            'en-IN': ['hello', 'you', 'are', 'is', 'and']
        }
        
        # Count matches for each language
        scores = {lang: 0 for lang in language_patterns}
        
        for lang, patterns in language_patterns.items():
            for pattern in patterns:
                if pattern.lower() in text.lower():
                    scores[lang] += 1
        
        # Return the language with the highest score, default to current language
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return self.current_language
    
    def set_language(self, language: str) -> bool:
        """Set the current language for voice interactions.
        
        Args:
            language: Language code to set
            
        Returns:
            Boolean indicating success
        """
        if language in self.language_map:
            self.current_language = language
            self.logger.info(f"Language set to {self.language_map[language]}")
            return True
        else:
            self.logger.warning(f"Unsupported language: {language}")
            return False
    
    def get_supported_languages(self) -> List[Dict]:
        """Get list of supported languages.
        
        Returns:
            List of dictionaries with language codes and names
        """
        return [{'code': code, 'name': name} for code, name in self.language_map.items()]
    
    def _is_online(self) -> bool:
        """Check if the system is online.
        
        Returns:
            Boolean indicating online status
        """
        # Simple implementation - in production, implement proper connectivity check
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=1)
            return True
        except OSError:
            return False
    
    def _load_offline_models(self) -> Dict:
        """Load offline speech recognition models.
        
        Returns:
            Dictionary of loaded models
        """
        models = {}
        model_dir = os.path.join('models', 'speech')
        
        if os.path.exists(model_dir):
            for lang_code in self.language_map.keys():
                model_path = os.path.join(model_dir, f"{lang_code}_model.pkl")
                if os.path.exists(model_path):
                    try:
                        with open(model_path, 'rb') as f:
                            models[lang_code] = pickle.load(f)
                        self.logger.info(f"Loaded offline model for {self.language_map[lang_code]}")
                    except Exception as e:
                        self.logger.error(f"Failed to load offline model for {lang_code}: {str(e)}")
        
        return models
    
    def _online_speech_to_text(self, audio_data: Union[bytes, str], language: str) -> Dict:
        """Use online service for speech-to-text conversion.
        
        Args:
            audio_data: Audio data or path
            language: Language code
            
        Returns:
            Dict with recognition results
        """
        with sr.AudioFile(audio_data) if isinstance(audio_data, str) else sr.AudioData(audio_data) as source:
            audio = self.recognizer.record(source)
            
        try:
            text = self.recognizer.recognize_google(audio, language=language)
            return {
                'success': True,
                'text': text,
                'confidence': 0.9,  # Google doesn't provide confidence scores
                'language': language
            }
        except sr.UnknownValueError:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': 'Speech not understood'
            }
        except sr.RequestError as e:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': f'Request error: {str(e)}'
            }
    
    def _offline_speech_to_text(self, audio_data: Union[bytes, str], language: str) -> Dict:
        """Use offline models for speech-to-text conversion.
        
        Args:
            audio_data: Audio data or path
            language: Language code
            
        Returns:
            Dict with recognition results
        """
        # Check if we have an offline model for this language
        if language not in self.offline_models:
            return {
                'success': False,
                'text': '',
                'confidence': 0.0,
                'error': f'No offline model available for {self.language_map.get(language, language)}'
            }
        
        # In a real implementation, this would use the offline model to process audio
        # This is a simplified placeholder
        return {
            'success': True,
            'text': 'Offline speech recognition placeholder',
            'confidence': 0.7,
            'language': language,
            'offline': True
        }