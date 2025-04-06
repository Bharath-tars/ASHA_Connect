#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Data Models for ASHA Connect

This module defines the data models used throughout the application including:
- Patient information
- Health assessment data
- User profiles
- Sync records

These models provide a consistent structure for data storage and retrieval.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

class Patient:
    """Patient data model for ASHA Connect."""
    
    def __init__(self, 
                 name: str, 
                 age: int, 
                 gender: str, 
                 village: str,
                 contact: Optional[str] = None,
                 patient_id: Optional[str] = None,
                 created_by: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 updated_at: Optional[datetime] = None,
                 medical_history: Optional[List[Dict]] = None,
                 active: bool = True):
        """Initialize a new Patient record.
        
        Args:
            name: Patient's full name
            age: Patient's age in years
            gender: Patient's gender (M/F/Other)
            village: Patient's village or locality
            contact: Optional contact number
            patient_id: Unique identifier (generated if not provided)
            created_by: ID of the ASHA worker who created the record
            created_at: Timestamp of creation
            updated_at: Timestamp of last update
            medical_history: List of previous medical conditions
            active: Whether the patient record is active
        """
        self.patient_id = patient_id or str(uuid.uuid4())
        self.name = name
        self.age = age
        self.gender = gender
        self.village = village
        self.contact = contact
        self.created_by = created_by
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.medical_history = medical_history or []
        self.active = active
    
    def to_dict(self) -> Dict:
        """Convert patient object to dictionary for storage."""
        return {
            'patient_id': self.patient_id,
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'village': self.village,
            'contact': self.contact,
            'created_by': self.created_by,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'medical_history': self.medical_history,
            'active': self.active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Patient':
        """Create a Patient object from dictionary data."""
        return cls(
            patient_id=data.get('patient_id'),
            name=data.get('name'),
            age=data.get('age'),
            gender=data.get('gender'),
            village=data.get('village'),
            contact=data.get('contact'),
            created_by=data.get('created_by'),
            created_at=data.get('created_at'),
            updated_at=data.get('updated_at'),
            medical_history=data.get('medical_history', []),
            active=data.get('active', True)
        )


class HealthAssessment:
    """Health assessment data model for ASHA Connect."""
    
    def __init__(self,
                 patient_id: str,
                 symptoms: List[str],
                 assessment_id: Optional[str] = None,
                 conducted_by: Optional[str] = None,
                 assessment_date: Optional[datetime] = None,
                 vital_signs: Optional[Dict] = None,
                 diagnosis: Optional[str] = None,
                 severity: Optional[str] = None,
                 recommendations: Optional[List[str]] = None,
                 referral_needed: bool = False,
                 referral_facility: Optional[str] = None,
                 notes: Optional[str] = None,
                 synced: bool = False):
        """Initialize a new Health Assessment record.
        
        Args:
            patient_id: ID of the patient being assessed
            symptoms: List of reported symptoms
            assessment_id: Unique identifier (generated if not provided)
            conducted_by: ID of the ASHA worker conducting assessment
            assessment_date: Date and time of assessment
            vital_signs: Dictionary of vital measurements
            diagnosis: Identified health condition
            severity: Severity level (Low/Medium/High)
            recommendations: List of care recommendations
            referral_needed: Whether specialist referral is needed
            referral_facility: Recommended healthcare facility
            notes: Additional assessment notes
            synced: Whether record has been synced to central database
        """
        self.assessment_id = assessment_id or str(uuid.uuid4())
        self.patient_id = patient_id
        self.symptoms = symptoms
        self.conducted_by = conducted_by
        self.assessment_date = assessment_date or datetime.now()
        self.vital_signs = vital_signs or {}
        self.diagnosis = diagnosis
        self.severity = severity
        self.recommendations = recommendations or []
        self.referral_needed = referral_needed
        self.referral_facility = referral_facility
        self.notes = notes
        self.synced = synced
    
    def to_dict(self) -> Dict:
        """Convert assessment object to dictionary for storage."""
        return {
            'assessment_id': self.assessment_id,
            'patient_id': self.patient_id,
            'symptoms': self.symptoms,
            'conducted_by': self.conducted_by,
            'assessment_date': self.assessment_date,
            'vital_signs': self.vital_signs,
            'diagnosis': self.diagnosis,
            'severity': self.severity,
            'recommendations': self.recommendations,
            'referral_needed': self.referral_needed,
            'referral_facility': self.referral_facility,
            'notes': self.notes,
            'synced': self.synced
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'HealthAssessment':
        """Create a HealthAssessment object from dictionary data."""
        return cls(
            assessment_id=data.get('assessment_id'),
            patient_id=data.get('patient_id'),
            symptoms=data.get('symptoms', []),
            conducted_by=data.get('conducted_by'),
            assessment_date=data.get('assessment_date'),
            vital_signs=data.get('vital_signs', {}),
            diagnosis=data.get('diagnosis'),
            severity=data.get('severity'),
            recommendations=data.get('recommendations', []),
            referral_needed=data.get('referral_needed', False),
            referral_facility=data.get('referral_facility'),
            notes=data.get('notes'),
            synced=data.get('synced', False)
        )


class User:
    """User data model for ASHA Connect."""
    
    def __init__(self,
                 username: str,
                 password_hash: str,
                 full_name: str,
                 role: str,
                 user_id: Optional[str] = None,
                 email: Optional[str] = None,
                 phone: Optional[str] = None,
                 district: Optional[str] = None,
                 health_facility: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 last_login: Optional[datetime] = None,
                 active: bool = True,
                 preferences: Optional[Dict] = None):
        """Initialize a new User record.
        
        Args:
            username: Unique username for login
            password_hash: Hashed password (never store plaintext)
            full_name: User's full name
            role: User role (asha/supervisor/admin)
            user_id: Unique identifier (generated if not provided)
            email: User's email address
            phone: User's phone number
            district: User's assigned district
            health_facility: User's associated health facility
            created_at: Account creation timestamp
            last_login: Last login timestamp
            active: Whether the account is active
            preferences: User preferences and settings
        """
        self.user_id = user_id or str(uuid.uuid4())
        self.username = username
        self.password_hash = password_hash
        self.full_name = full_name
        self.role = role
        self.email = email
        self.phone = phone
        self.district = district
        self.health_facility = health_facility
        self.created_at = created_at or datetime.now()
        self.last_login = last_login
        self.active = active
        self.preferences = preferences or {}
    
    def to_dict(self) -> Dict:
        """Convert user object to dictionary for storage."""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'password_hash': self.password_hash,
            'full_name': self.full_name,
            'role': self.role,
            'email': self.email,
            'phone': self.phone,
            'district': self.district,
            'health_facility': self.health_facility,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'active': self.active,
            'preferences': self.preferences
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Create a User object from dictionary data."""
        return cls(
            user_id=data.get('user_id'),
            username=data.get('username'),
            password_hash=data.get('password_hash'),
            full_name=data.get('full_name'),
            role=data.get('role'),
            email=data.get('email'),
            phone=data.get('phone'),
            district=data.get('district'),
            health_facility=data.get('health_facility'),
            created_at=data.get('created_at'),
            last_login=data.get('last_login'),
            active=data.get('active', True),
            preferences=data.get('preferences', {})
        )


class SyncRecord:
    """Sync record data model for ASHA Connect."""
    
    def __init__(self,
                 record_type: str,
                 record_id: str,
                 data: Dict,
                 sync_id: Optional[str] = None,
                 user_id: Optional[str] = None,
                 created_at: Optional[datetime] = None,
                 synced_at: Optional[datetime] = None,
                 sync_status: str = 'pending',
                 priority: int = 1,
                 retry_count: int = 0,
                 error_message: Optional[str] = None):
        """Initialize a new Sync Record.
        
        Args:
            record_type: Type of record (patient/assessment/etc)
            record_id: ID of the original record
            data: Full record data to be synced
            sync_id: Unique identifier for sync record
            user_id: ID of user who created/modified the record
            created_at: When the sync record was created
            synced_at: When the record was successfully synced
            sync_status: Current sync status (pending/synced/failed)
            priority: Sync priority (higher numbers = higher priority)
            retry_count: Number of sync attempts
            error_message: Last sync error message if failed
        """
        self.sync_id = sync_id or str(uuid.uuid4())
        self.record_type = record_type
        self.record_id = record_id
        self.data = data
        self.user_id = user_id
        self.created_at = created_at or datetime.now()
        self.synced_at = synced_at
        self.sync_status = sync_status
        self.priority = priority
        self.retry_count = retry_count
        self.error_message = error_message
    
    def to_dict(self) -> Dict:
        """Convert sync record object to dictionary for storage."""
        return {
            'sync_id': self.sync_id,
            'record_type': self.record_type,
            'record_id': self.record_id,
            'data': self.data,
            'user_id': self.user_id,
            'created_at': self.created_at,
            'synced_at': self.synced_at,
            'sync_status': self.sync_status,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'error_message': self.error_message
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'SyncRecord':
        """Create a SyncRecord object from dictionary data."""
        return cls(
            sync_id=data.get('sync_id'),
            record_type=data.get('record_type'),
            record_id=data.get('record_id'),
            data=data.get('data', {}),
            user_id=data.get('user_id'),
            created_at=data.get('created_at'),
            synced_at=data.get('synced_at'),
            sync_status=data.get('sync_status', 'pending'),
            priority=data.get('priority', 1),
            retry_count=data.get('retry_count', 0),
            error_message=data.get('error_message')
        )