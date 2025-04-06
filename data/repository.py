#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Repository Module for ASHA Connect

This module provides repository classes for data access operations including:
- CRUD operations for all data models
- Query functionality with filtering
- Support for both online and offline data access

These repositories abstract the database implementation details from the service layer.
"""

import logging
from typing import Dict, List, Optional, Any, Union, TypeVar, Generic
from datetime import datetime

# Import models
from data.models import Patient, HealthAssessment, User, SyncRecord

# Type variable for generic repository
T = TypeVar('T')

class Repository(Generic[T]):
    """Generic repository for data access operations."""
    
    def __init__(self, db, collection_name: str):
        """Initialize the repository with database connection.
        
        Args:
            db: Database connection instance
            collection_name: Name of the collection/table
        """
        self.logger = logging.getLogger(__name__)
        self.db = db
        self.collection_name = collection_name
    
    async def create(self, item: T) -> str:
        """Create a new record in the database.
        
        Args:
            item: The item to create
            
        Returns:
            The ID of the created item
        """
        try:
            # Convert to dictionary if it has to_dict method
            if hasattr(item, 'to_dict'):
                data = item.to_dict()
            else:
                data = item
                
            # Insert into database
            result = await self.db.insert_one(self.collection_name, data)
            return result
        except Exception as e:
            self.logger.error(f"Error creating {self.collection_name}: {str(e)}")
            raise
    
    async def get_by_id(self, id_field: str, id_value: str) -> Optional[Dict]:
        """Get a record by its ID.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to search for
            
        Returns:
            The record if found, None otherwise
        """
        try:
            query = {id_field: id_value}
            result = await self.db.find_one(self.collection_name, query)
            return result
        except Exception as e:
            self.logger.error(f"Error getting {self.collection_name} by ID: {str(e)}")
            raise
    
    async def get_all(self, query: Optional[Dict] = None, limit: int = 100, skip: int = 0) -> List[Dict]:
        """Get all records matching the query.
        
        Args:
            query: Optional query filter
            limit: Maximum number of records to return
            skip: Number of records to skip
            
        Returns:
            List of matching records
        """
        try:
            result = await self.db.find(self.collection_name, query or {}, limit=limit, skip=skip)
            return result
        except Exception as e:
            self.logger.error(f"Error getting all {self.collection_name}: {str(e)}")
            raise
    
    async def update(self, id_field: str, id_value: str, data: Dict) -> bool:
        """Update a record by its ID.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to update
            data: The data to update
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = {id_field: id_value}
            # Add updated_at timestamp if not present
            if 'updated_at' not in data:
                data['updated_at'] = datetime.now()
                
            result = await self.db.update_one(self.collection_name, query, {'$set': data})
            return result
        except Exception as e:
            self.logger.error(f"Error updating {self.collection_name}: {str(e)}")
            raise
    
    async def delete(self, id_field: str, id_value: str) -> bool:
        """Delete a record by its ID.
        
        Args:
            id_field: The field name that contains the ID
            id_value: The ID value to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            query = {id_field: id_value}
            result = await self.db.delete_one(self.collection_name, query)
            return result
        except Exception as e:
            self.logger.error(f"Error deleting {self.collection_name}: {str(e)}")
            raise
    
    async def count(self, query: Optional[Dict] = None) -> int:
        """Count records matching the query.
        
        Args:
            query: Optional query filter
            
        Returns:
            Number of matching records
        """
        try:
            result = await self.db.count(self.collection_name, query or {})
            return result
        except Exception as e:
            self.logger.error(f"Error counting {self.collection_name}: {str(e)}")
            raise


class PatientRepository(Repository[Patient]):
    """Repository for Patient data access operations."""
    
    def __init__(self, db):
        """Initialize the Patient repository.
        
        Args:
            db: Database connection instance
        """
        super().__init__(db, 'patients')
    
    async def get_by_patient_id(self, patient_id: str) -> Optional[Patient]:
        """Get a patient by their patient_id.
        
        Args:
            patient_id: The patient's unique ID
            
        Returns:
            Patient object if found, None otherwise
        """
        result = await self.get_by_id('patient_id', patient_id)
        if result:
            return Patient.from_dict(result)
        return None
    
    async def get_by_name(self, name: str, limit: int = 10) -> List[Patient]:
        """Search for patients by name (partial match).
        
        Args:
            name: The name to search for
            limit: Maximum number of results
            
        Returns:
            List of matching Patient objects
        """
        try:
            # Case-insensitive search with regex
            query = {'name': {'$regex': name, '$options': 'i'}}
            results = await self.get_all(query, limit=limit)
            return [Patient.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error searching patients by name: {str(e)}")
            raise
    
    async def get_by_village(self, village: str, limit: int = 50) -> List[Patient]:
        """Get patients from a specific village.
        
        Args:
            village: The village name
            limit: Maximum number of results
            
        Returns:
            List of matching Patient objects
        """
        try:
            query = {'village': village, 'active': True}
            results = await self.get_all(query, limit=limit)
            return [Patient.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting patients by village: {str(e)}")
            raise
    
    async def create_patient(self, patient: Patient) -> str:
        """Create a new patient record.
        
        Args:
            patient: The Patient object to create
            
        Returns:
            The patient_id of the created patient
        """
        return await self.create(patient)
    
    async def update_patient(self, patient: Patient) -> bool:
        """Update an existing patient record.
        
        Args:
            patient: The Patient object with updated data
            
        Returns:
            True if successful, False otherwise
        """
        patient.updated_at = datetime.now()
        return await self.update('patient_id', patient.patient_id, patient.to_dict())
    
    async def deactivate_patient(self, patient_id: str) -> bool:
        """Deactivate a patient record (soft delete).
        
        Args:
            patient_id: The patient's unique ID
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('patient_id', patient_id, {'active': False, 'updated_at': datetime.now()})


class HealthAssessmentRepository(Repository[HealthAssessment]):
    """Repository for HealthAssessment data access operations."""
    
    def __init__(self, db):
        """Initialize the HealthAssessment repository.
        
        Args:
            db: Database connection instance
        """
        super().__init__(db, 'health_assessments')
    
    async def get_by_assessment_id(self, assessment_id: str) -> Optional[HealthAssessment]:
        """Get an assessment by its assessment_id.
        
        Args:
            assessment_id: The assessment's unique ID
            
        Returns:
            HealthAssessment object if found, None otherwise
        """
        result = await self.get_by_id('assessment_id', assessment_id)
        if result:
            return HealthAssessment.from_dict(result)
        return None
    
    async def get_by_patient_id(self, patient_id: str, limit: int = 20) -> List[HealthAssessment]:
        """Get assessments for a specific patient.
        
        Args:
            patient_id: The patient's unique ID
            limit: Maximum number of results
            
        Returns:
            List of HealthAssessment objects
        """
        try:
            query = {'patient_id': patient_id}
            results = await self.get_all(query, limit=limit)
            return [HealthAssessment.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting assessments by patient ID: {str(e)}")
            raise
    
    async def get_unsynced_assessments(self, limit: int = 50) -> List[HealthAssessment]:
        """Get assessments that haven't been synced yet.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of unsynced HealthAssessment objects
        """
        try:
            query = {'synced': False}
            results = await self.get_all(query, limit=limit)
            return [HealthAssessment.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting unsynced assessments: {str(e)}")
            raise
    
    async def create_assessment(self, assessment: HealthAssessment) -> str:
        """Create a new health assessment record.
        
        Args:
            assessment: The HealthAssessment object to create
            
        Returns:
            The assessment_id of the created assessment
        """
        return await self.create(assessment)
    
    async def update_assessment(self, assessment: HealthAssessment) -> bool:
        """Update an existing health assessment record.
        
        Args:
            assessment: The HealthAssessment object with updated data
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('assessment_id', assessment.assessment_id, assessment.to_dict())
    
    async def mark_as_synced(self, assessment_id: str) -> bool:
        """Mark an assessment as synced to the central database.
        
        Args:
            assessment_id: The assessment's unique ID
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('assessment_id', assessment_id, {'synced': True})


class UserRepository(Repository[User]):
    """Repository for User data access operations."""
    
    def __init__(self, db):
        """Initialize the User repository.
        
        Args:
            db: Database connection instance
        """
        super().__init__(db, 'users')
    
    async def get_by_user_id(self, user_id: str) -> Optional[User]:
        """Get a user by their user_id.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            User object if found, None otherwise
        """
        result = await self.get_by_id('user_id', user_id)
        if result:
            return User.from_dict(result)
        return None
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """Get a user by their username.
        
        Args:
            username: The user's username
            
        Returns:
            User object if found, None otherwise
        """
        try:
            query = {'username': username, 'active': True}
            result = await self.db.find_one(self.collection_name, query)
            if result:
                return User.from_dict(result)
            return None
        except Exception as e:
            self.logger.error(f"Error getting user by username: {str(e)}")
            raise
    
    async def get_by_role(self, role: str, limit: int = 50) -> List[User]:
        """Get users with a specific role.
        
        Args:
            role: The role to filter by
            limit: Maximum number of results
            
        Returns:
            List of User objects with the specified role
        """
        try:
            query = {'role': role, 'active': True}
            results = await self.get_all(query, limit=limit)
            return [User.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting users by role: {str(e)}")
            raise
    
    async def create_user(self, user: User) -> str:
        """Create a new user record.
        
        Args:
            user: The User object to create
            
        Returns:
            The user_id of the created user
        """
        return await self.create(user)
    
    async def update_user(self, user: User) -> bool:
        """Update an existing user record.
        
        Args:
            user: The User object with updated data
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('user_id', user.user_id, user.to_dict())
    
    async def update_last_login(self, user_id: str) -> bool:
        """Update the last_login timestamp for a user.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('user_id', user_id, {'last_login': datetime.now()})
    
    async def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account (soft delete).
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            True if successful, False otherwise
        """
        return await self.update('user_id', user_id, {'active': False})


class SyncRepository(Repository[SyncRecord]):
    """Repository for SyncRecord data access operations."""
    
    def __init__(self, db):
        """Initialize the SyncRecord repository.
        
        Args:
            db: Database connection instance
        """
        super().__init__(db, 'sync_records')
    
    async def get_by_sync_id(self, sync_id: str) -> Optional[SyncRecord]:
        """Get a sync record by its sync_id.
        
        Args:
            sync_id: The sync record's unique ID
            
        Returns:
            SyncRecord object if found, None otherwise
        """
        result = await self.get_by_id('sync_id', sync_id)
        if result:
            return SyncRecord.from_dict(result)
        return None
    
    async def get_pending_records(self, limit: int = 50) -> List[SyncRecord]:
        """Get pending sync records ordered by priority.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of pending SyncRecord objects
        """
        try:
            query = {'sync_status': 'pending'}
            # Sort by priority (descending) and created_at (ascending)
            sort = [('priority', -1), ('created_at', 1)]
            results = await self.db.find(self.collection_name, query, limit=limit, sort=sort)
            return [SyncRecord.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting pending sync records: {str(e)}")
            raise
    
    async def get_failed_records(self, limit: int = 50) -> List[SyncRecord]:
        """Get failed sync records.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of failed SyncRecord objects
        """
        try:
            query = {'sync_status': 'failed'}
            results = await self.get_all(query, limit=limit)
            return [SyncRecord.from_dict(r) for r in results]
        except Exception as e:
            self.logger.error(f"Error getting failed sync records: {str(e)}")
            raise
    
    async def create_sync_record(self, record: SyncRecord) -> str:
        """Create a new sync record.
        
        Args:
            record: The SyncRecord object to create
            
        Returns:
            The sync_id of the created record
        """
        return await self.create(record)
    
    async def mark_as_synced(self, sync_id: str) -> bool:
        """Mark a sync record as successfully synced.
        
        Args:
            sync_id: The sync record's unique ID
            
        Returns:
            True if successful, False otherwise
        """
        update_data = {
            'sync_status': 'synced',
            'synced_at': datetime.now()
        }
        return await self.update('sync_id', sync_id, update_data)
    
    async def mark_as_failed(self, sync_id: str, error_message: str) -> bool:
        """Mark a sync record as failed with error message.
        
        Args:
            sync_id: The sync record's unique ID
            error_message: The error message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get current record to increment retry count
            record = await self.get_by_sync_id(sync_id)
            if not record:
                return False
                
            update_data = {
                'sync_status': 'failed',
                'retry_count': record.retry_count + 1,
                'error_message': error_message
            }
            return await self.update('sync_id', sync_id, update_data)
        except Exception as e:
            self.logger.error(f"Error marking sync record as failed: {str(e)}")
            raise