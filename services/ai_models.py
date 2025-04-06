#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
AI Models for ASHA Connect

This module provides AI model integration for health assessments including:
- Llama 3 integration for advanced reasoning
- Symptom analysis models
- Health condition identification
- Treatment recommendation generation

These models support the core health assessment functionality of ASHA Connect.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union
import time
import numpy as np

# AI model integration
from llama_cpp import Llama

class AIModelManager:
    """Manager for AI models used in ASHA Connect."""
    
    def __init__(self):
        """Initialize the AI model manager with necessary components."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing AI Model Manager")
        
        # Load model configurations
        self.model_path = os.getenv('MODEL_PATH', 'models/llama/llama-3-8b-instruct.gguf')
        self.model_temp = float(os.getenv('MODEL_TEMP', '0.7'))
        self.model_max_tokens = int(os.getenv('MODEL_MAX_TOKENS', '512'))
        
        # Initialize Llama model if available
        self.llm = self._initialize_llm()
        
        # Load health assessment prompts
        self.prompts = self._load_prompts()
        
        self.logger.info("AI Model Manager initialized successfully")
    
    def _initialize_llm(self) -> Optional[Llama]:
        """Initialize the Llama model if available.
        
        Returns:
            Llama model instance or None if not available
        """
        try:
            if os.path.exists(self.model_path):
                self.logger.info(f"Loading Llama model from {self.model_path}")
                model = Llama(
                    model_path=self.model_path,
                    n_ctx=2048,  # Context window size
                    n_threads=4   # Number of CPU threads to use
                )
                self.logger.info("Llama model loaded successfully")
                return model
            else:
                self.logger.warning(f"Llama model not found at {self.model_path}")
                return None
        except Exception as e:
            self.logger.error(f"Error loading Llama model: {str(e)}")
            return None
    
    def _load_prompts(self) -> Dict[str, str]:
        """Load prompt templates for health assessments.
        
        Returns:
            Dictionary of prompt templates
        """
        prompts_path = os.getenv('PROMPTS_PATH', 'data/prompts.json')
        default_prompts = {
            "symptom_analysis": """You are a healthcare assistant helping ASHA workers in rural India.
                Based on the following symptoms, analyze what might be the potential health conditions:
                Symptoms: {symptoms}
                Patient Information: Age: {age}, Gender: {gender}
                Medical History: {medical_history}
                Provide a detailed analysis of the symptoms and potential conditions.""",
            
            "treatment_recommendation": """You are a healthcare assistant helping ASHA workers in rural India.
                Based on the following diagnosis, recommend appropriate treatments and care instructions:
                Diagnosis: {diagnosis}
                Severity: {severity}
                Patient Information: Age: {age}, Gender: {gender}
                Medical History: {medical_history}
                Provide detailed treatment recommendations and care instructions.""",
            
            "referral_decision": """You are a healthcare assistant helping ASHA workers in rural India.
                Based on the following information, determine if the patient needs to be referred to a healthcare facility:
                Diagnosis: {diagnosis}
                Severity: {severity}
                Symptoms: {symptoms}
                Patient Information: Age: {age}, Gender: {gender}
                Medical History: {medical_history}
                Provide a clear recommendation on whether referral is needed and the urgency level."""
        }
        
        try:
            if os.path.exists(prompts_path):
                with open(prompts_path, 'r') as f:
                    loaded_prompts = json.load(f)
                    return loaded_prompts
            else:
                self.logger.warning(f"Prompts file not found at {prompts_path}, using default prompts")
                return default_prompts
        except Exception as e:
            self.logger.error(f"Error loading prompts: {str(e)}")
            return default_prompts
    
    def analyze_symptoms(self, symptoms: List[str], patient_data: Dict) -> Dict:
        """Analyze symptoms to identify potential health conditions.
        
        Args:
            symptoms: List of reported symptoms
            patient_data: Patient information including age, gender, medical history
            
        Returns:
            Dictionary with analysis results
        """
        self.logger.info(f"Analyzing symptoms: {symptoms}")
        
        # Prepare prompt with patient data
        prompt = self.prompts["symptom_analysis"].format(
            symptoms=", ".join(symptoms),
            age=patient_data.get('age', 'Unknown'),
            gender=patient_data.get('gender', 'Unknown'),
            medical_history=patient_data.get('medical_history', 'None')
        )
        
        # Use Llama model if available, otherwise use fallback logic
        if self.llm:
            try:
                start_time = time.time()
                response = self.llm(prompt, 
                                   max_tokens=self.model_max_tokens, 
                                   temperature=self.model_temp,
                                   stop=["\n\n"])
                analysis = response['choices'][0]['text'].strip()
                processing_time = time.time() - start_time
                
                self.logger.info(f"Symptom analysis completed in {processing_time:.2f} seconds")
                
                # Extract potential conditions from the analysis
                # This is a simplified extraction - in a real system, this would be more sophisticated
                conditions = self._extract_conditions(analysis)
                
                return {
                    "analysis": analysis,
                    "potential_conditions": conditions,
                    "processing_time": processing_time
                }
            except Exception as e:
                self.logger.error(f"Error in symptom analysis with Llama: {str(e)}")
                return self._fallback_symptom_analysis(symptoms, patient_data)
        else:
            return self._fallback_symptom_analysis(symptoms, patient_data)
    
    def _fallback_symptom_analysis(self, symptoms: List[str], patient_data: Dict) -> Dict:
        """Fallback method for symptom analysis when Llama is not available.
        
        Args:
            symptoms: List of reported symptoms
            patient_data: Patient information
            
        Returns:
            Dictionary with basic analysis results
        """
        self.logger.info("Using fallback symptom analysis")
        
        # Simple rule-based analysis
        # This is a very simplified example - a real system would have more comprehensive rules
        analysis = "Based on the symptoms, here is a basic analysis:\n"
        potential_conditions = []
        
        # Simple symptom mapping
        symptom_condition_map = {
            "fever": ["Common Cold", "Influenza", "Malaria", "Typhoid"],
            "cough": ["Common Cold", "Bronchitis", "Pneumonia", "Tuberculosis"],
            "headache": ["Tension Headache", "Migraine", "Sinusitis"],
            "abdominal pain": ["Gastritis", "Appendicitis", "Intestinal Infection"],
            "diarrhea": ["Gastroenteritis", "Food Poisoning", "Intestinal Infection"],
            "rash": ["Allergic Reaction", "Chickenpox", "Measles"],
            "joint pain": ["Arthritis", "Rheumatic Fever", "Injury"],
            "fatigue": ["Anemia", "Hypothyroidism", "Depression"],
            "dizziness": ["Low Blood Pressure", "Anemia", "Inner Ear Problem"],
            "chest pain": ["Angina", "Muscle Strain", "Respiratory Infection"]
        }
        
        # Check each symptom against the map
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for key, conditions in symptom_condition_map.items():
                if key in symptom_lower:
                    analysis += f"\n- {symptom}: May indicate {', '.join(conditions)}"
                    potential_conditions.extend(conditions)
        
        # Remove duplicates from potential conditions
        potential_conditions = list(set(potential_conditions))
        
        # Add age and gender specific considerations
        age = patient_data.get('age', 0)
        gender = patient_data.get('gender', '').lower()
        
        if age < 5 and "fever" in [s.lower() for s in symptoms]:
            analysis += "\n\nNote: Fever in children under 5 requires careful monitoring."
            
        if gender == 'f' and age > 12 and "abdominal pain" in [s.lower() for s in symptoms]:
            analysis += "\n\nNote: Consider gynecological causes for abdominal pain in female patients."
        
        return {
            "analysis": analysis,
            "potential_conditions": potential_conditions,
            "processing_time": 0.1  # Placeholder for processing time
        }
    
    def _extract_conditions(self, analysis: str) -> List[str]:
        """Extract potential health conditions from the analysis text.
        
        Args:
            analysis: The full analysis text
            
        Returns:
            List of potential health conditions
        """
        # This is a simplified extraction method
        # In a real system, this would use more sophisticated NLP techniques
        conditions = []
        
        # Look for common patterns in the text that indicate conditions
        indicators = [
            "may indicate", "suggests", "points to", "could be", "likely",
            "possibility of", "symptoms of", "consistent with", "characteristic of"
        ]
        
        lines = analysis.split("\n")
        for line in lines:
            for indicator in indicators:
                if indicator in line.lower():
                    # Extract the text after the indicator
                    parts = line.lower().split(indicator, 1)
                    if len(parts) > 1:
                        # Split by common separators and clean up
                        condition_text = parts[1].strip()
                        for sep in [",", ";", ".", "and", "or"]:
                            condition_text = condition_text.replace(sep, "#")
                        
                        # Extract individual conditions
                        for cond in condition_text.split("#"):
                            cond = cond.strip()
                            if cond and len(cond) > 3:  # Avoid very short strings
                                # Capitalize the condition name
                                conditions.append(cond.title())
        
        # Remove duplicates and limit to top 5
        unique_conditions = list(set(conditions))[:5]
        
        return unique_conditions
    
    def generate_treatment_recommendations(self, diagnosis: str, severity: str, patient_data: Dict) -> Dict:
        """Generate treatment recommendations based on diagnosis.
        
        Args:
            diagnosis: The identified health condition
            severity: Severity level (Low/Medium/High)
            patient_data: Patient information
            
        Returns:
            Dictionary with treatment recommendations
        """
        self.logger.info(f"Generating treatment recommendations for {diagnosis} (Severity: {severity})")
        
        # Prepare prompt with diagnosis and patient data
        prompt = self.prompts["treatment_recommendation"].format(
            diagnosis=diagnosis,
            severity=severity,
            age=patient_data.get('age', 'Unknown'),
            gender=patient_data.get('gender', 'Unknown'),
            medical_history=patient_data.get('medical_history', 'None')
        )
        
        # Use Llama model if available, otherwise use fallback logic
        if self.llm:
            try:
                start_time = time.time()
                response = self.llm(prompt, 
                                   max_tokens=self.model_max_tokens, 
                                   temperature=self.model_temp,
                                   stop=["\n\n"])
                recommendations = response['choices'][0]['text'].strip()
                processing_time = time.time() - start_time
                
                self.logger.info(f"Treatment recommendations generated in {processing_time:.2f} seconds")
                
                # Extract specific recommendations as a list
                recommendation_list = self._extract_recommendations(recommendations)
                
                return {
                    "full_recommendations": recommendations,
                    "recommendation_list": recommendation_list,
                    "processing_time": processing_time
                }
            except Exception as e:
                self.logger.error(f"Error generating treatment recommendations with Llama: {str(e)}")
                return self._fallback_treatment_recommendations(diagnosis, severity, patient_data)
        else:
            return self._fallback_treatment_recommendations(diagnosis, severity, patient_data)
    
    def _fallback_treatment_recommendations(self, diagnosis: str, severity: str, patient_data: Dict) -> Dict:
        """Fallback method for treatment recommendations when Llama is not available.
        
        Args:
            diagnosis: The identified health condition
            severity: Severity level
            patient_data: Patient information
            
        Returns:
            Dictionary with basic treatment recommendations
        """
        self.logger.info("Using fallback treatment recommendations")
        
        # Simple rule-based recommendations
        # This is a very simplified example - a real system would have more comprehensive guidelines
        recommendations = f"Basic recommendations for {diagnosis} (Severity: {severity}):\n"
        recommendation_list = []
        
        # Common recommendations for various conditions
        common_conditions = {
            "common cold": [
                "Rest and stay hydrated",
                "Take paracetamol for fever or pain if needed",
                "Use saline nasal drops for congestion",
                "Seek medical attention if symptoms worsen or persist beyond 7 days"
            ],
            "influenza": [
                "Rest and stay hydrated",
                "Take paracetamol for fever or pain",
                "Avoid contact with others to prevent spread",
                "Seek immediate medical attention if breathing difficulty occurs"
            ],
            "diarrhea": [
                "Stay hydrated with ORS (Oral Rehydration Solution)",
                "Continue eating small, frequent meals",
                "Avoid dairy products and spicy foods",
                "Seek medical attention if blood in stool or severe dehydration"
            ],
            "headache": [
                "Rest in a quiet, dark room",
                "Take paracetamol as directed",
                "Stay hydrated",
                "Seek medical attention if severe or persistent"
            ],
            "fever": [
                "Take paracetamol as directed",
                "Stay cool and hydrated",
                "Rest",
                "Seek medical attention if very high fever or persists beyond 3 days"
            ]
        }
        
        # Check if diagnosis matches any known condition
        diagnosis_lower = diagnosis.lower()
        matched = False
        
        for condition, recs in common_conditions.items():
            if condition in diagnosis_lower:
                recommendation_list = recs.copy()
                for rec in recs:
                    recommendations += f"\n- {rec}"
                matched = True
                break
        
        # If no match, provide general recommendations
        if not matched:
            general_recs = [
                "Rest and stay hydrated",
                "Take medications only as prescribed",
                "Monitor symptoms closely",
                "Seek medical attention if symptoms worsen"
            ]
            recommendation_list = general_recs
            for rec in general_recs:
                recommendations += f"\n- {rec}"
        
        # Add severity-specific advice
        if severity.lower() == "high":
            urgent_advice = "Due to HIGH severity, immediate medical attention is recommended."
            recommendations += f"\n\n{urgent_advice}"
            recommendation_list.insert(0, urgent_advice)
        
        return {
            "full_recommendations": recommendations,
            "recommendation_list": recommendation_list,
            "processing_time": 0.1  # Placeholder for processing time
        }
    
    def _extract_recommendations(self, recommendations: str) -> List[str]:
        """Extract specific recommendations from the full text.
        
        Args:
            recommendations: The full recommendations text
            
        Returns:
            List of specific recommendations
        """
        # Extract recommendations that are formatted as bullet points or numbered lists
        rec_list = []
        
        lines = recommendations.split("\n")
        for line in lines:
            # Check for bullet points, numbers, or similar formatting
            line = line.strip()
            if line.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "0.")):
                # Clean up the line
                clean_line = line.lstrip("-*•0123456789. ")
                if clean_line:
                    rec_list.append(clean_line)
        
        # If no bullet points found, try to split by sentences
        if not rec_list:
            sentences = recommendations.replace("\n", " ").split(". ")
            for sentence in sentences:
                clean_sentence = sentence.strip()
                if clean_sentence and len(clean_sentence) > 10:  # Avoid very short sentences
                    if not clean_sentence.endswith("."):
                        clean_sentence += "."
                    rec_list.append(clean_sentence)
        
        return rec_list
    
    def determine_referral_need(self, diagnosis: str, severity: str, symptoms: List[str], patient_data: Dict) -> Dict:
        """Determine if the patient needs to be referred to a healthcare facility.
        
        Args:
            diagnosis: The identified health condition
            severity: Severity level
            symptoms: List of reported symptoms
            patient_data: Patient information
            
        Returns:
            Dictionary with referral decision and details
        """
        self.logger.info(f"Determining referral need for {diagnosis} (Severity: {severity})")
        
        # Prepare prompt with diagnosis, symptoms, and patient data
        prompt = self.prompts["referral_decision"].format(
            diagnosis=diagnosis,
            severity=severity,
            symptoms=", ".join(symptoms),
            age=patient_data.get('age', 'Unknown'),
            gender=patient_data.get('gender', 'Unknown'),
            medical_history=patient_data.get('medical_history', 'None')
        )
        
        # Use Llama model if available, otherwise use fallback logic
        if self.llm:
            try:
                start_time = time.time()
                response = self.llm(prompt, 
                                   max_tokens=self.model_max_tokens, 
                                   temperature=self.model_temp,
                                   stop=["\n\n"])
                referral_text = response['choices'][0]['text'].strip()
                processing_time = time.time() - start_time
                
                self.logger.info(f"Referral determination completed in {processing_time:.2f} seconds")
                
                # Extract referral decision
                referral_needed, urgency, facility_type = self._extract_referral_decision(referral_text)
                
                return {
                    "referral_needed": referral_needed,
                    "urgency": urgency,
                    "facility_type": facility_type,
                    "full_recommendation": referral_text,
                    "processing_time": processing_time
                }
            except Exception as e:
                self.logger.error(f"Error determining referral need with Llama: {str(e)}")
                return self._fallback_referral_determination(diagnosis, severity, symptoms, patient_data)
        else:
            return self._fallback_referral_determination(diagnosis, severity, symptoms, patient_data)
    
    def _fallback_referral_determination(self, diagnosis: str, severity: str, symptoms: List[str], patient_data: Dict) -> Dict:
        """Fallback method for referral determination when Llama is not available.
        
        Args:
            diagnosis: The identified health condition
            severity: Severity level
            symptoms: List of reported symptoms
            patient_data: Patient information
            
        Returns:
            Dictionary with basic referral decision
        """
        self.logger.info("Using fallback referral determination")
        
        # Simple rule-based referral logic
        # This is a very simplified example - a real system would have more comprehensive guidelines
        referral_needed = False
        urgency = "non-urgent"
        facility_type = "primary health center"
        recommendation = f"Referral recommendation for {diagnosis} (Severity: {severity}):\n"
        
        # High severity always needs referral
        if severity.lower() == "high":
            referral_needed = True
            urgency = "urgent"
            recommendation += "\nReferral is URGENTLY needed due to high severity."
        
        # Check for emergency symptoms
        emergency_symptoms = [
            "difficulty breathing", "chest pain", "severe bleeding", 
            "unconscious", "seizure", "stroke", "heart attack",
            "severe abdominal pain", "head injury"
        ]
        
        for symptom in symptoms:
            symptom_lower = symptom.lower()
            for emergency in emergency_symptoms:
                if emergency in symptom_lower:
                    referral_needed = True
                    urgency = "emergency"
                    facility_type = "hospital"
                    recommendation += f"\nEMERGENCY referral needed due to {symptom}."
                    break
        
        # Check age-specific conditions
        age = patient_data.get('age', 0)
        
        # For infants and young children
        if age < 5 and any(s.lower() == "fever" for s in symptoms):
            referral_needed = True
            urgency = "urgent"
            recommendation += "\nReferral recommended for young child with fever."
        
        # For elderly patients
        if age > 65 and severity.lower() in ["medium", "high"]:
            referral_needed = True
            urgency = "urgent"
            recommendation += "\nReferral recommended due to patient age and condition severity."
        
        # Medium severity conditions often need referral
        if severity.lower() == "medium" and not referral_needed:
            referral_needed = True
            recommendation += "\nReferral recommended for further evaluation of medium severity condition."
        
        # If no referral needed
        if not referral_needed:
            recommendation += "\nNo referral needed at this time. Provide home care as recommended."
        
        return {
            "referral_needed": referral_needed,
            "urgency": urgency,
            "facility_type": facility_type,
            "full_recommendation": recommendation,
            "processing_time": 0.1  # Placeholder for processing time
        }
    
    def _extract_referral_decision(self, referral_text: str) -> tuple:
        """Extract referral decision from the recommendation text.
        
        Args:
            referral_text: The full referral recommendation text
            
        Returns:
            Tuple of (referral_needed, urgency, facility_type)
        """
        # Default values
        referral_needed = False
        urgency = "non-urgent"
        facility_type = "primary health center"
        
        # Check for referral indicators in the text
        referral_indicators = [
            "refer", "referral", "send to", "visit", "go to", "consult", "see a"
        ]
        
        no_referral_indicators = [
            "no referral", "referral is not", "does not need", "don't refer", 
            "no need for referral", "can be managed", "home care"
        ]
        
        # Check for explicit no-referral statements first
        for indicator in no_referral_indicators:
            if indicator in referral_text.lower():
                return False, urgency, facility_type
        
        # Then check for referral indicators
        for indicator in referral_indicators:
            if indicator in referral_text.lower():
                referral_needed = True
                break
        
        # If referral is needed, determine urgency
        if referral_needed:
            # Check for emergency/urgent language
            if any(word in referral_text.lower() for word in ["emergency", "immediate", "urgently", "right away"]):
                urgency = "emergency"
            elif any(word in referral_text.lower() for word in ["urgent", "soon", "promptly", "without delay"]):
                urgency = "urgent"
            
            # Determine facility type
            if "hospital" in referral_text.lower():
                facility_type = "hospital"
            elif any(facility in referral_text.lower() for facility in ["specialist", "doctor", "physician"]):
                facility_type = "specialist"
        
        return referral_needed, urgency, facility_type