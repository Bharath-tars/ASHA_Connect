#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Health Service for ASHA Connect

This module handles all health assessment functionality including:
- Symptom analysis
- Health condition identification
- Treatment recommendations
- Referral decisions

It integrates with Llama 3 and other AI models for advanced reasoning.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Tuple, Union
import time

# AI model integration
from llama_cpp import Llama
import numpy as np

class HealthService:
    """Service for handling health assessments in ASHA Connect."""
    
    def __init__(self):
        """Initialize the health service with necessary components."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Health Service")
        
        # Load health assessment model
        self.model_path = os.getenv('MODEL_PATH', 'models/llama/llama-3-8b-instruct.gguf')
        self.model_temp = float(os.getenv('MODEL_TEMP', '0.7'))
        self.model_max_tokens = int(os.getenv('MODEL_MAX_TOKENS', '512'))
        
        # Initialize Llama model if available
        self.llm = self._initialize_llm()
        
        # Load health conditions database
        self.conditions_db = self._load_conditions_database()
        
        # Load treatment protocols
        self.treatment_protocols = self._load_treatment_protocols()
        
        # Load referral guidelines
        self.referral_guidelines = self._load_referral_guidelines()
        
        self.logger.info("Health Service initialized successfully")
    
    def assess_health(self, symptoms: List[str], patient_info: Dict, language: str = 'en') -> Dict:
        """Perform health assessment based on symptoms and patient information.
        
        Args:
            symptoms: List of reported symptoms
            patient_info: Dictionary containing patient information
            language: Language code for the response
            
        Returns:
            Dict containing assessment results
        """
        self.logger.info(f"Performing health assessment for {len(symptoms)} symptoms")
        
        try:
            # Normalize symptoms
            normalized_symptoms = self._normalize_symptoms(symptoms)
            
            # Get potential conditions
            potential_conditions = self._identify_potential_conditions(normalized_symptoms, patient_info)
            
            # Use LLM for advanced reasoning if available
            if self.llm is not None:
                llm_assessment = self._llm_assessment(normalized_symptoms, patient_info)
                # Merge LLM assessment with rule-based assessment
                final_assessment = self._merge_assessments(potential_conditions, llm_assessment)
            else:
                final_assessment = potential_conditions
            
            # Determine if referral is needed
            referral_decision = self._determine_referral(final_assessment, patient_info)
            
            # Get treatment recommendations
            treatment_recommendations = self._get_treatment_recommendations(
                final_assessment, patient_info, referral_decision
            )
            
            # Translate response if needed
            if language != 'en':
                final_assessment = self._translate_assessment(final_assessment, language)
                treatment_recommendations = self._translate_recommendations(treatment_recommendations, language)
            
            return {
                'success': True,
                'assessment': final_assessment,
                'referral': referral_decision,
                'recommendations': treatment_recommendations,
                'timestamp': time.time()
            }
            
        except Exception as e:
            self.logger.error(f"Health assessment error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_condition_info(self, condition_id: str, language: str = 'en') -> Dict:
        """Get detailed information about a specific health condition.
        
        Args:
            condition_id: ID of the health condition
            language: Language code for the response
            
        Returns:
            Dict containing condition information
        """
        if condition_id in self.conditions_db:
            condition_info = self.conditions_db[condition_id].copy()
            
            # Translate if needed
            if language != 'en':
                condition_info = self._translate_condition_info(condition_info, language)
                
            return {
                'success': True,
                'condition': condition_info
            }
        else:
            return {
                'success': False,
                'error': f"Condition {condition_id} not found"
            }
    
    def get_referral_facilities(self, condition_ids: List[str], location: Dict, urgency: str) -> List[Dict]:
        """Get recommended healthcare facilities for referral.
        
        Args:
            condition_ids: List of condition IDs
            location: Dictionary with latitude and longitude
            urgency: Urgency level (high, medium, low)
            
        Returns:
            List of recommended facilities
        """
        # This would connect to a database of healthcare facilities
        # Simplified implementation for demonstration
        return [
            {
                'id': 'facility1',
                'name': 'Primary Health Center, Rajpur',
                'type': 'PHC',
                'distance': '3.2 km',
                'address': 'Main Road, Rajpur Village',
                'phone': '+91 9876543210',
                'services': ['general medicine', 'maternal care', 'vaccinations'],
                'wait_time': '30 minutes'
            },
            {
                'id': 'facility2',
                'name': 'District Hospital',
                'type': 'Hospital',
                'distance': '12.5 km',
                'address': 'Hospital Road, District Center',
                'phone': '+91 9876543211',
                'services': ['emergency', 'surgery', 'pediatrics', 'obstetrics'],
                'wait_time': '60 minutes'
            }
        ]
    
    def _initialize_llm(self) -> Optional[Llama]:
        """Initialize the Llama language model.
        
        Returns:
            Llama model instance or None if initialization fails
        """
        try:
            if os.path.exists(self.model_path):
                self.logger.info(f"Loading Llama model from {self.model_path}")
                model = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,
                    n_batch=512,
                    verbose=False
                )
                self.logger.info("Llama model loaded successfully")
                return model
            else:
                self.logger.warning(f"Model file not found at {self.model_path}")
                return None
        except Exception as e:
            self.logger.error(f"Failed to initialize Llama model: {str(e)}")
            return None
    
    def _load_conditions_database(self) -> Dict:
        """Load database of health conditions.
        
        Returns:
            Dictionary of health conditions
        """
        # In a real implementation, this would load from a database or file
        # Simplified implementation for demonstration
        return {
            'malaria': {
                'id': 'malaria',
                'name': 'Malaria',
                'symptoms': ['fever', 'chills', 'headache', 'nausea', 'body aches'],
                'risk_factors': ['recent mosquito exposure', 'travel to endemic area'],
                'severity': 'high',
                'requires_referral': True,
                'common_in_children': True,
                'common_in_elderly': True,
                'common_in_pregnant': True
            },
            'dengue': {
                'id': 'dengue',
                'name': 'Dengue Fever',
                'symptoms': ['high fever', 'severe headache', 'pain behind eyes', 'joint pain', 'rash'],
                'risk_factors': ['mosquito exposure', 'previous dengue infection'],
                'severity': 'high',
                'requires_referral': True,
                'common_in_children': True,
                'common_in_elderly': True,
                'common_in_pregnant': True
            },
            'diarrhea': {
                'id': 'diarrhea',
                'name': 'Diarrhea',
                'symptoms': ['loose stools', 'abdominal pain', 'nausea', 'vomiting', 'fever'],
                'risk_factors': ['contaminated water', 'poor sanitation'],
                'severity': 'medium',
                'requires_referral': False,
                'common_in_children': True,
                'common_in_elderly': True,
                'common_in_pregnant': False
            },
            'pneumonia': {
                'id': 'pneumonia',
                'name': 'Pneumonia',
                'symptoms': ['cough', 'fever', 'difficulty breathing', 'chest pain', 'fatigue'],
                'risk_factors': ['weakened immune system', 'smoking', 'COPD'],
                'severity': 'high',
                'requires_referral': True,
                'common_in_children': True,
                'common_in_elderly': True,
                'common_in_pregnant': False
            },
            'anemia': {
                'id': 'anemia',
                'name': 'Anemia',
                'symptoms': ['fatigue', 'weakness', 'pale skin', 'shortness of breath', 'dizziness'],
                'risk_factors': ['poor nutrition', 'pregnancy', 'menstruation'],
                'severity': 'medium',
                'requires_referral': False,
                'common_in_children': True,
                'common_in_elderly': True,
                'common_in_pregnant': True
            }
        }
    
    def _load_treatment_protocols(self) -> Dict:
        """Load treatment protocols for various conditions.
        
        Returns:
            Dictionary of treatment protocols
        """
        # In a real implementation, this would load from a database or file
        # Simplified implementation for demonstration
        return {
            'malaria': {
                'medications': ['artemisinin-based combination therapy'],
                'home_care': ['rest', 'fluids', 'fever management'],
                'follow_up': '3 days',
                'warning_signs': ['severe headache', 'confusion', 'difficulty breathing']
            },
            'dengue': {
                'medications': ['acetaminophen (paracetamol)'],
                'home_care': ['rest', 'fluids', 'fever management'],
                'follow_up': '2 days',
                'warning_signs': ['severe abdominal pain', 'persistent vomiting', 'bleeding']
            },
            'diarrhea': {
                'medications': ['oral rehydration solution'],
                'home_care': ['hydration', 'bland diet', 'hand hygiene'],
                'follow_up': '2 days if not improving',
                'warning_signs': ['blood in stool', 'severe dehydration', 'high fever']
            },
            'pneumonia': {
                'medications': ['antibiotics as prescribed'],
                'home_care': ['rest', 'fluids', 'fever management'],
                'follow_up': '3 days',
                'warning_signs': ['difficulty breathing', 'bluish lips or face', 'chest pain']
            },
            'anemia': {
                'medications': ['iron supplements', 'folic acid'],
                'home_care': ['iron-rich diet', 'vitamin C with meals'],
                'follow_up': '2 weeks',
                'warning_signs': ['severe fatigue', 'dizziness', 'shortness of breath']
            }
        }
    
    def _load_referral_guidelines(self) -> Dict:
        """Load referral guidelines for various conditions.
        
        Returns:
            Dictionary of referral guidelines
        """
        # In a real implementation, this would load from a database or file
        # Simplified implementation for demonstration
        return {
            'emergency': {
                'symptoms': ['unconsciousness', 'severe bleeding', 'chest pain', 'difficulty breathing'],
                'facility_type': 'hospital',
                'transport': 'ambulance'
            },
            'urgent': {
                'symptoms': ['high fever', 'severe dehydration', 'severe pain'],
                'facility_type': 'phc',
                'transport': 'any available'
            },
            'routine': {
                'symptoms': ['mild symptoms', 'chronic conditions', 'follow-up'],
                'facility_type': 'phc',
                'transport': 'self'
            }
        }
    
    def _normalize_symptoms(self, symptoms: List[str]) -> List[str]:
        """Normalize symptom descriptions to standard terms.
        
        Args:
            symptoms: List of reported symptoms
            
        Returns:
            List of normalized symptoms
        """
        # Symptom normalization mapping
        normalization_map = {
            'feeling hot': 'fever',
            'hot': 'fever',
            'high temperature': 'fever',
            'shaking': 'chills',
            'cold': 'chills',
            'shivering': 'chills',
            'throwing up': 'vomiting',
            'sick': 'nausea',
            'feeling sick': 'nausea',
            'tummy pain': 'abdominal pain',
            'stomach pain': 'abdominal pain',
            'stomach ache': 'abdominal pain',
            'loose motion': 'diarrhea',
            'watery stool': 'diarrhea',
            'runny tummy': 'diarrhea',
            'tired': 'fatigue',
            'no energy': 'fatigue',
            'exhausted': 'fatigue',
            'hard to breathe': 'difficulty breathing',
            'breathless': 'difficulty breathing',
            'can\'t breathe properly': 'difficulty breathing'
        }
        
        normalized = []
        for symptom in symptoms:
            symptom = symptom.lower().strip()
            if symptom in normalization_map:
                normalized.append(normalization_map[symptom])
            else:
                normalized.append(symptom)
                
        return normalized
    
    def _identify_potential_conditions(self, symptoms: List[str], patient_info: Dict) -> List[Dict]:
        """Identify potential health conditions based on symptoms.
        
        Args:
            symptoms: List of normalized symptoms
            patient_info: Dictionary containing patient information
            
        Returns:
            List of potential conditions with confidence scores
        """
        potential_conditions = []
        
        for condition_id, condition in self.conditions_db.items():
            # Calculate match score based on symptoms
            matching_symptoms = set(symptoms).intersection(set(condition['symptoms']))
            if matching_symptoms:
                # Basic scoring algorithm
                score = len(matching_symptoms) / len(condition['symptoms'])
                
                # Adjust score based on patient factors
                if 'age' in patient_info:
                    age = patient_info['age']
                    if age < 5 and condition['common_in_children']:
                        score += 0.1
                    elif age > 65 and condition['common_in_elderly']:
                        score += 0.1
                        
                if 'is_pregnant' in patient_info and patient_info['is_pregnant'] and condition['common_in_pregnant']:
                    score += 0.1
                    
                # Add to potential conditions if score is significant
                if score > 0.3:  # Threshold for consideration
                    potential_conditions.append({
                        'id': condition_id,
                        'name': condition['name'],
                        'confidence': round(score * 100),
                        'matching_symptoms': list(matching_symptoms),
                        'severity': condition['severity'],
                        'requires_referral': condition['requires_referral']
                    })
        
        # Sort by confidence score
        potential_conditions.sort(key=lambda x: x['confidence'], reverse=True)
        
        return potential_conditions
    
    def _llm_assessment(self, symptoms: List[str], patient_info: Dict) -> List[Dict]:
        """Use LLM for advanced health assessment reasoning.
        
        Args:
            symptoms: List of normalized symptoms
            patient_info: Dictionary containing patient information
            
        Returns:
            List of potential conditions with confidence scores
        """
        if self.llm is None:
            return []
            
        try:
            # Construct prompt for the LLM
            age = patient_info.get('age', 'unknown')
            gender = patient_info.get('gender', 'unknown')
            is_pregnant = 'Yes' if patient_info.get('is_pregnant', False) else 'No'
            
            symptoms_text = ', '.join(symptoms)
            
            prompt = f"""You are a medical AI assistant helping ASHA workers in rural India. 
            Assess the following patient:
            
            Patient Information:
            - Age: {age}
            - Gender: {gender}
            - Pregnant: {is_pregnant}
            
            Reported Symptoms: {symptoms_text}
            
            Based on these symptoms and patient information, what are the most likely health conditions? 
            For each condition, provide:
            1. Condition name
            2. Confidence level (0-100)
            3. Whether immediate medical referral is recommended
            4. Brief explanation
            
            Format your response as a structured list.
            """
            
            # Generate response from LLM
            response = self.llm(prompt, max_tokens=self.model_max_tokens, temperature=self.model_temp, stop=["\n\n"])
            llm_text = response['choices'][0]['text']
            
            # Parse LLM response (in a real system, use more robust parsing)
            conditions = self._parse_llm_response(llm_text)
            
            return conditions
            
        except Exception as e:
            self.logger.error(f"LLM assessment error: {str(e)}")
            return []
    
    def _parse_llm_response(self, llm_text: str) -> List[Dict]:
        """Parse the LLM response to extract structured condition information.
        
        Args:
            llm_text: Text response from the LLM
            
        Returns:
            List of conditions extracted from the response
        """
        # This is a simplified parser
        # In a production system, use more robust parsing techniques
        conditions = []
        
        try:
            lines = llm_text.split('\n')
            current_condition = {}
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                # Check if this is a new condition
                if line.startswith('1.') or line.startswith('2.') or line.startswith('3.') or line.startswith('- '):
                    # Save previous condition if it exists
                    if current_condition and 'name' in current_condition:
                        conditions.append(current_condition)
                    current_condition = {'llm_generated': True}
                
                # Extract condition name
                if 'name' not in current_condition and (':' in line or line.startswith('Condition')):
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        current_condition['name'] = parts[1].strip()
                    else:
                        current_condition['name'] = line.replace('Condition', '').strip()
                
                # Extract confidence
                if 'confidence' not in current_condition and ('confidence' in line.lower() or 'level' in line.lower()):
                    # Extract number from text
                    import re
                    numbers = re.findall(r'\d+', line)
                    if numbers:
                        current_condition['confidence'] = int(numbers[0])
                
                # Extract referral recommendation
                if 'requires_referral' not in current_condition and 'referral' in line.lower():
                    current_condition['requires_referral'] = 'yes' in line.lower() or 'recommend' in line.lower()
                
                # Extract explanation
                if 'explanation' not in current_condition and 'explanation' in line.lower():
                    parts = line.split(':', 1)
                    if len(parts) > 1:
                        current_condition['explanation'] = parts[1].strip()
            
            # Add the last condition
            if current_condition and 'name' in current_condition:
                conditions.append(current_condition)
            
            # Ensure all conditions have required fields
            for condition in conditions:
                if 'confidence' not in condition:
                    condition['confidence'] = 50  # Default confidence
                if 'requires_referral' not in condition:
                    condition['requires_referral'] = False  # Default referral
                if 'explanation' not in condition:
                    condition['explanation'] = "Based on symptom pattern"  # Default explanation
                # Generate an ID
                condition['id'] = condition['name'].lower().replace(' ', '_')
                
            return conditions
            
        except Exception as e:
            self.logger.error(f"Error parsing LLM response: {str(e)}")
            return []
    
    def _merge_assessments(self, rule_based: List[Dict], llm_based: List[Dict]) -> List[Dict]:
        """Merge rule-based and LLM-based assessments.
        
        Args:
            rule_based: List of conditions from rule-based assessment
            llm_based: List of conditions from LLM-based assessment
            
        Returns:
            Merged list of conditions
        """
        merged = {}
        
        # Add rule-based conditions
        for condition in rule_based:
            condition_id = condition['id']
            merged[condition_id] = condition
        
        # Add or update with LLM-based conditions
        for condition in llm_based:
            condition_id = condition['id']
            if condition_id in merged:
                # Average the confidence scores
                merged[condition_id]['confidence'] = round((merged[condition_id]['confidence'] + condition['confidence']) / 2)
                # Take the more cautious approach for referral
                merged[condition_id]['requires_referral'] = merged[condition_id]['requires_referral'] or condition['requires_referral']
                # Add LLM explanation if available
                if 'explanation' in condition:
                    merged[condition_id]['explanation'] = condition['explanation']
            else:
                merged[condition_id] = condition
        
        # Convert back to list and sort by confidence
        result = list(merged.values())
        result.sort(key=lambda x: x['confidence'], reverse=True)
        
        return result
    
    def _determine_referral(self, conditions: List[Dict], patient_info: Dict) -> Dict:
        """Determine if patient needs referral to healthcare facility.
        
        Args:
            conditions: List of potential conditions
            patient_info: Dictionary containing patient information
            
        Returns:
            Dictionary with referral decision and details
        """
        # Default to no referral
        referral = {
            'is_required': False,
            'urgency': 'routine',
            'reason': '',
            'facility_type': 'phc'
        }
        
        # Check high-confidence conditions that require referral
        for condition in conditions:
            if condition['confidence'] >= 70 and condition['requires_referral']:
                referral['is_required'] = True
                referral['reason'] = f"High likelihood of {condition['name']}"
                
                # Determine urgency based on severity
                if condition['severity'] == 'high':
                    referral['urgency'] = 'urgent'
                break
        
        # Check for emergency symptoms
        emergency_symptoms = self.referral_guidelines['emergency']['symptoms']
        urgent_symptoms = self.referral_guidelines['urgent']['symptoms']
        
        for symptom in emergency_symptoms:
            if symptom in patient_info.get('symptoms', []):
                referral['is_required'] = True
                referral['urgency'] = 'emergency'
                referral['reason'] = f"Emergency symptom: {symptom}"
                referral['facility_type'] = 'hospital'
                break
                
        # If not emergency, check for urgent symptoms
        if referral['urgency'] != 'emergency':
            for symptom in urgent_symptoms:
                if symptom in patient_info.get('symptoms', []):
                    referral['is_required'] = True
                    referral['urgency'] = 'urgent'
                    referral['reason'] = f"Urgent symptom: {symptom}"
                    break
        
        # Special considerations for vulnerable groups
        age = patient_info.get('age', 30)
        is_pregnant = patient_info.get('is_pregnant', False)
        
        if (age < 5 or age > 65 or is_pregnant) and conditions:
            # Lower threshold for referral for vulnerable groups
            if conditions[0]['confidence'] >= 50 and conditions[0]['severity'] != 'low':
                referral['is_required'] = True
                if referral['urgency'] == 'routine':
                    referral['urgency'] = 'urgent'
                if not referral['reason']:
                    vulnerable_group = 'child' if age < 5 else 'elderly' if age > 65 else 'pregnant woman'
                    referral['reason'] = f"Patient is a {vulnerable_group} with significant symptoms"
        
        return referral
    
    def _get_treatment_recommendations(self, conditions: List[Dict], patient_info: Dict, referral: Dict) -> Dict:
        """Get treatment recommendations based on conditions.
        
        Args:
            conditions: List of potential conditions
            patient_info: Dictionary containing patient information
            referral: Referral decision
            
        Returns:
            Dictionary with treatment recommendations
        """
        recommendations = {
            'medications': [],
            'home_care': [],
            'follow_up': '',
            'warning_signs': [],
            'prevention': []
        }
        
        # If referral is required with emergency or urgent status, focus on immediate care
        if referral['is_required'] and referral['urgency'] in ['emergency', 'urgent']:
            recommendations['home_care'] = [
                'Seek medical attention immediately',
                'Keep patient comfortable and hydrated if conscious',
                'Monitor vital signs until medical help arrives'
            ]
            recommendations['follow_up'] = 'As advised by healthcare provider'
            return recommendations
        
        # Get recommendations for top conditions
        top_conditions = conditions[:2]  # Consider top 2 conditions
        
        for condition in top_conditions:
            condition_id = condition['id']
            if condition_id in self.treatment_protocols:
                protocol = self.treatment_protocols[condition_id]
                
                # Add medications if not already included
                for med in protocol['medications']:
                    if med not in recommendations['medications']:
                        recommendations['medications'].append(med)
                
                # Add home care instructions if not already included
                for care in protocol['home_care']:
                    if care not in recommendations['home_care']:
                        recommendations['home_care'].append(care)
                
                # Set follow-up to the earliest recommended
                if not recommendations['follow_up'] or protocol['follow_up'] < recommendations['follow_up']:
                    recommendations['follow_up'] = protocol['follow_up']
                
                # Add warning signs if not already included
                for sign in protocol['warning_signs']:
                    if sign not in recommendations['warning_signs']:
                        recommendations['warning_signs'].append(sign)
        
        # Add general prevention advice
        recommendations['prevention'] = [
            'Maintain good hygiene',
            'Use mosquito nets if in malaria-prone area',
            'Drink clean, boiled water',
            'Eat a balanced diet',
            'Get regular check-ups'
        ]
        
        return recommendations
    
    def _translate_assessment(self, assessment: List[Dict], language: str) -> List[Dict]:
        """Translate assessment to the specified language.
        
        Args:
            assessment: List of conditions
            language: Target language code
            
        Returns:
            Translated assessment
        """
        # In a real implementation, this would use a translation service
        # Simplified implementation returns the original assessment
        return assessment
    
    def _translate_recommendations(self, recommendations: Dict, language: str) -> Dict:
        """Translate recommendations to the specified language.
        
        Args:
            recommendations: Dictionary with recommendations
            language: Target language code
            
        Returns:
            Translated recommendations
        """
        # In a real implementation, this would use a translation service
        # Simplified implementation returns the original recommendations
        return recommendations
    
    def _translate_condition_info(self, condition_info: Dict, language: str) -> Dict:
        """Translate condition information to the specified language.
        
        Args:
            condition_info: Dictionary with condition information
            language: Target language code
            
        Returns:
            Translated condition information
        """
        # In a real implementation, this would use a translation service
        # Simplified implementation returns the original condition information
        return condition_info