#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Offline Manager for ASHA Connect

This module handles offline functionality including:
- Local data storage and management
- Prioritized data synchronization
- Conflict resolution
- Resource management for offline operation

It ensures the application can function effectively in areas with limited connectivity.
"""

import os
import logging
import json
import time
import sqlite3
import shutil
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import threading

# Import data models
from data.models import Patient, HealthAssessment, SyncRecord

class OfflineManager:
    """Manager for offline functionality in ASHA Connect."""
    
    def __init__(self, db):
        """Initialize the offline manager with necessary components.
        
        Args:
            db: Database connection instance
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Offline Manager")
        
        self.db = db
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize local storage
        self.local_db_path = self.config['local_db_path']
        self._init_local_storage()
        
        # Initialize sync tracking
        self.last_sync_time = None
        self.sync_in_progress = False
        
        # Start background resource management if enabled
        if self.config['auto_resource_management']:
            self._start_resource_manager()
        
        self.logger.info("Offline Manager initialized successfully")
    
    def _load_config(self) -> Dict:
        """Load offline manager configuration.
        
        Returns:
            Dictionary with configuration settings
        """
        config_path = os.getenv('OFFLINE_CONFIG_PATH', 'config/offline.json')
        default_config = {
            "local_db_path": os.getenv('LOCAL_DB_PATH', 'data/local.db'),
            "max_offline_days": int(os.getenv('MAX_OFFLINE_DAYS', 30)),
            "sync_interval": int(os.getenv('SYNC_INTERVAL', 3600)),  # 1 hour
            "max_storage_size_mb": int(os.getenv('MAX_STORAGE_SIZE_MB', 500)),
            "auto_resource_management": True,
            "critical_battery_level": 15,
            "sync_priorities": {
                "health_assessments": 10,
                "patients": 5,
                "call_records": 3,
                "user_activity": 1
            }
        }
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    loaded_config = json.load(f)
                    return loaded_config
            else:
                self.logger.warning(f"Offline config not found at {config_path}, using default config")
                return default_config
        except Exception as e:
            self.logger.error(f"Error loading offline config: {str(e)}")
            return default_config
    
    def _init_local_storage(self) -> None:
        """Initialize local storage for offline operation."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
            
            # Initialize SQLite database if it doesn't exist
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Create tables if they don't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS patients (
                    patient_id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    synced INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS health_assessments (
                    assessment_id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    synced INTEGER DEFAULT 0,
                    FOREIGN KEY (patient_id) REFERENCES patients (patient_id)
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_queue (
                    sync_id TEXT PRIMARY KEY,
                    record_type TEXT NOT NULL,
                    record_id TEXT NOT NULL,
                    data TEXT NOT NULL,
                    priority INTEGER DEFAULT 1,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_attempt TEXT,
                    error_message TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS resources (
                    resource_id TEXT PRIMARY KEY,
                    resource_type TEXT NOT NULL,
                    file_path TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0
                )
            ''')
            
            conn.commit()
            conn.close()
            
            self.logger.info("Local storage initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing local storage: {str(e)}")
            raise
    
    def save_patient_offline(self, patient: Patient) -> bool:
        """Save patient data to local storage.
        
        Args:
            patient: Patient object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Convert patient to JSON
            patient_data = json.dumps(patient.to_dict())
            now = datetime.now().isoformat()
            
            # Check if patient already exists
            cursor.execute("SELECT patient_id FROM patients WHERE patient_id = ?", (patient.patient_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing patient
                cursor.execute(
                    "UPDATE patients SET data = ?, updated_at = ?, synced = 0 WHERE patient_id = ?",
                    (patient_data, now, patient.patient_id)
                )
            else:
                # Insert new patient
                cursor.execute(
                    "INSERT INTO patients (patient_id, data, created_at, updated_at, synced) VALUES (?, ?, ?, ?, 0)",
                    (patient.patient_id, patient_data, now, now)
                )
            
            # Add to sync queue
            self._add_to_sync_queue("patient", patient.patient_id, patient_data, self.config['sync_priorities']['patients'])
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Saved patient {patient.patient_id} to local storage")
            return True
        except Exception as e:
            self.logger.error(f"Error saving patient offline: {str(e)}")
            return False
    
    def save_assessment_offline(self, assessment: HealthAssessment) -> bool:
        """Save health assessment data to local storage.
        
        Args:
            assessment: HealthAssessment object to save
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Convert assessment to JSON
            assessment_data = json.dumps(assessment.to_dict())
            now = datetime.now().isoformat()
            
            # Check if assessment already exists
            cursor.execute("SELECT assessment_id FROM health_assessments WHERE assessment_id = ?", (assessment.assessment_id,))
            exists = cursor.fetchone()
            
            if exists:
                # Update existing assessment
                cursor.execute(
                    "UPDATE health_assessments SET data = ?, synced = 0 WHERE assessment_id = ?",
                    (assessment_data, assessment.assessment_id)
                )
            else:
                # Insert new assessment
                cursor.execute(
                    "INSERT INTO health_assessments (assessment_id, patient_id, data, created_at, synced) VALUES (?, ?, ?, ?, 0)",
                    (assessment.assessment_id, assessment.patient_id, assessment_data, now)
                )
            
            # Add to sync queue with high priority
            self._add_to_sync_queue("health_assessment", assessment.assessment_id, assessment_data, 
                                   self.config['sync_priorities']['health_assessments'])
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Saved assessment {assessment.assessment_id} to local storage")
            return True
        except Exception as e:
            self.logger.error(f"Error saving assessment offline: {str(e)}")
            return False
    
    def _add_to_sync_queue(self, record_type: str, record_id: str, data: str, priority: int = 1) -> bool:
        """Add a record to the sync queue.
        
        Args:
            record_type: Type of record (patient, health_assessment, etc.)
            record_id: ID of the record
            data: JSON string of the record data
            priority: Sync priority (higher = more important)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            sync_id = f"{record_type}_{record_id}_{int(time.time())}"
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT INTO sync_queue (sync_id, record_type, record_id, data, priority, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                (sync_id, record_type, record_id, data, priority, now)
            )
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            self.logger.error(f"Error adding to sync queue: {str(e)}")
            return False
    
    def get_patient_offline(self, patient_id: str) -> Optional[Patient]:
        """Get patient data from local storage.
        
        Args:
            patient_id: ID of the patient to retrieve
            
        Returns:
            Patient object if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM patients WHERE patient_id = ?", (patient_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                patient_data = json.loads(result[0])
                return Patient.from_dict(patient_data)
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting patient offline: {str(e)}")
            return None
    
    def get_assessment_offline(self, assessment_id: str) -> Optional[HealthAssessment]:
        """Get health assessment data from local storage.
        
        Args:
            assessment_id: ID of the assessment to retrieve
            
        Returns:
            HealthAssessment object if found, None otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM health_assessments WHERE assessment_id = ?", (assessment_id,))
            result = cursor.fetchone()
            
            conn.close()
            
            if result:
                assessment_data = json.loads(result[0])
                return HealthAssessment.from_dict(assessment_data)
            
            return None
        except Exception as e:
            self.logger.error(f"Error getting assessment offline: {str(e)}")
            return None
    
    def get_patient_assessments_offline(self, patient_id: str) -> List[HealthAssessment]:
        """Get all health assessments for a patient from local storage.
        
        Args:
            patient_id: ID of the patient
            
        Returns:
            List of HealthAssessment objects
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT data FROM health_assessments WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,))
            results = cursor.fetchall()
            
            conn.close()
            
            assessments = []
            for result in results:
                assessment_data = json.loads(result[0])
                assessments.append(HealthAssessment.from_dict(assessment_data))
            
            return assessments
        except Exception as e:
            self.logger.error(f"Error getting patient assessments offline: {str(e)}")
            return []
    
    def search_patients_offline(self, query: str, limit: int = 20) -> List[Patient]:
        """Search for patients in local storage.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            
        Returns:
            List of matching Patient objects
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # SQLite doesn't support JSON search directly, so we'll load all and filter
            cursor.execute("SELECT data FROM patients LIMIT ?", (limit * 10,))  # Get more than needed for filtering
            results = cursor.fetchall()
            
            conn.close()
            
            # Filter results by searching in the JSON data
            query = query.lower()
            matching_patients = []
            
            for result in results:
                patient_data = json.loads(result[0])
                
                # Check if query matches any of these fields
                if (query in patient_data.get('name', '').lower() or
                    query in patient_data.get('village', '').lower() or
                    query in str(patient_data.get('age', '')).lower() or
                    query in patient_data.get('contact', '').lower()):
                    
                    matching_patients.append(Patient.from_dict(patient_data))
                    
                    # Stop if we have enough results
                    if len(matching_patients) >= limit:
                        break
            
            return matching_patients
        except Exception as e:
            self.logger.error(f"Error searching patients offline: {str(e)}")
            return []
    
    def sync_data(self) -> Dict:
        """Synchronize offline data with the central database.
        
        Returns:
            Dictionary with sync results
        """
        if self.sync_in_progress:
            return {
                'success': False,
                'message': 'Sync already in progress',
                'synced_records': 0
            }
        
        self.sync_in_progress = True
        
        try:
            self.logger.info("Starting data synchronization")
            
            # Check if we have connectivity to the central database
            if not self._check_connectivity():
                self.sync_in_progress = False
                return {
                    'success': False,
                    'message': 'No connectivity to central database',
                    'synced_records': 0
                }
            
            # Get records from sync queue, ordered by priority
            records_to_sync = self._get_sync_queue_records()
            
            synced_count = 0
            failed_count = 0
            
            for record in records_to_sync:
                try:
                    # Attempt to sync the record
                    if self._sync_record(record):
                        synced_count += 1
                    else:
                        failed_count += 1
                except Exception as e:
                    self.logger.error(f"Error syncing record {record['sync_id']}: {str(e)}")
                    failed_count += 1
                    self._update_sync_record_status(record['sync_id'], False, str(e))
            
            self.last_sync_time = datetime.now()
            
            self.logger.info(f"Sync completed: {synced_count} synced, {failed_count} failed")
            
            return {
                'success': True,
                'message': f"Sync completed: {synced_count} synced, {failed_count} failed",
                'synced_records': synced_count,
                'failed_records': failed_count,
                'sync_time': self.last_sync_time.isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error during sync: {str(e)}")
            return {
                'success': False,
                'message': f"Sync error: {str(e)}",
                'synced_records': 0
            }
        finally:
            self.sync_in_progress = False
    
    def _check_connectivity(self) -> bool:
        """Check if we have connectivity to the central database.
        
        Returns:
            True if connected, False otherwise
        """
        try:
            # Try to connect to the central database
            return self.db.is_connected
        except Exception:
            return False
    
    def _get_sync_queue_records(self, limit: int = 50) -> List[Dict]:
        """Get records from the sync queue, ordered by priority.
        
        Args:
            limit: Maximum number of records to retrieve
            
        Returns:
            List of records to sync
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row  # This enables column access by name
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM sync_queue ORDER BY priority DESC, retry_count ASC, created_at ASC LIMIT ?",
                (limit,)
            )
            
            results = cursor.fetchall()
            conn.close()
            
            # Convert to list of dictionaries
            records = [dict(row) for row in results]
            
            return records
        except Exception as e:
            self.logger.error(f"Error getting sync queue records: {str(e)}")
            return []
    
    def _sync_record(self, record: Dict) -> bool:
        """Sync a single record to the central database.
        
        Args:
            record: Record to sync
            
        Returns:
            True if successful, False otherwise
        """
        try:
            record_type = record['record_type']
            record_id = record['record_id']
            data = json.loads(record['data'])
            
            self.logger.info(f"Syncing {record_type} {record_id}")
            
            # Update retry information
            self._update_sync_attempt(record['sync_id'])
            
            # Sync based on record type
            if record_type == 'patient':
                result = self._sync_patient(record_id, data)
            elif record_type == 'health_assessment':
                result = self._sync_assessment(record_id, data)
            else:
                self.logger.warning(f"Unknown record type: {record_type}")
                return False
            
            if result:
                # Mark as synced and remove from queue
                self._update_sync_record_status(record['sync_id'], True)
                self._mark_record_synced(record_type, record_id)
                return True
            else:
                return False
        except Exception as e:
            self.logger.error(f"Error syncing record: {str(e)}")
            self._update_sync_record_status(record['sync_id'], False, str(e))
            return False
    
    def _sync_patient(self, patient_id: str, data: Dict) -> bool:
        """Sync a patient record to the central database.
        
        Args:
            patient_id: Patient ID
            data: Patient data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if patient exists in central DB
            central_patient = self.db.find_one('patients', {'patient_id': patient_id})
            
            if central_patient:
                # Update existing patient
                # Handle conflict resolution if needed
                if self._resolve_conflict('patient', central_patient, data):
                    result = self.db.update_one('patients', {'patient_id': patient_id}, {'$set': data})
                else:
                    # Skip update if conflict resolution determined central data is newer
                    self.logger.info(f"Skipping patient update due to conflict resolution: {patient_id}")
                    return True
            else:
                # Insert new patient
                result = self.db.insert_one('patients', data)
            
            return result is not None
        except Exception as e:
            self.logger.error(f"Error syncing patient: {str(e)}")
            return False
    
    def _sync_assessment(self, assessment_id: str, data: Dict) -> bool:
        """Sync a health assessment record to the central database.
        
        Args:
            assessment_id: Assessment ID
            data: Assessment data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if assessment exists in central DB
            central_assessment = self.db.find_one('health_assessments', {'assessment_id': assessment_id})
            
            if central_assessment:
                # Update existing assessment
                result = self.db.update_one('health_assessments', {'assessment_id': assessment_id}, {'$set': data})
            else:
                # Insert new assessment
                result = self.db.insert_one('health_assessments', data)
            
            return result is not None
        except Exception as e:
            self.logger.error(f"Error syncing assessment: {str(e)}")
            return False
    
    def _resolve_conflict(self, record_type: str, central_data: Dict, local_data: Dict) -> bool:
        """Resolve conflicts between central and local data.
        
        Args:
            record_type: Type of record
            central_data: Data from central database
            local_data: Data from local storage
            
        Returns:
            True if local data should be used, False if central data is newer
        """
        try:
            # Simple timestamp-based conflict resolution
            # In a real system, this would be more sophisticated
            
            # Get timestamps
            central_time = central_data.get('updated_at')
            local_time = local_data.get('updated_at')
            
            if not central_time or not local_time:
                # If either timestamp is missing, use local data
                return True
            
            # Parse timestamps
            if isinstance(central_time, str):
                central_time = datetime.fromisoformat(central_time.replace('Z', '+00:00'))
            
            if isinstance(local_time, str):
                local_time = datetime.fromisoformat(local_time.replace('Z', '+00:00'))
            
            # Compare timestamps
            return local_time > central_time
        except Exception as e:
            self.logger.error(f"Error resolving conflict: {str(e)}")
            # Default to using local data in case of error
            return True
    
    def _update_sync_attempt(self, sync_id: str) -> None:
        """Update sync attempt information.
        
        Args:
            sync_id: Sync record ID
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            cursor.execute(
                "UPDATE sync_queue SET retry_count = retry_count + 1, last_attempt = ? WHERE sync_id = ?",
                (now, sync_id)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error updating sync attempt: {str(e)}")
    
    def _update_sync_record_status(self, sync_id: str, success: bool, error_message: str = None) -> None:
        """Update sync record status.
        
        Args:
            sync_id: Sync record ID
            success: Whether sync was successful
            error_message: Error message if sync failed
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            if success:
                # Remove from queue if successful
                cursor.execute("DELETE FROM sync_queue WHERE sync_id = ?", (sync_id,))
            else:
                # Update error message if failed
                cursor.execute(
                    "UPDATE sync_queue SET error_message = ? WHERE sync_id = ?",
                    (error_message, sync_id)
                )
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error updating sync record status: {str(e)}")
    
    def _mark_record_synced(self, record_type: str, record_id: str) -> None:
        """Mark a record as synced in local storage.
        
        Args:
            record_type: Type of record
            record_id: Record ID
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            if record_type == 'patient':
                cursor.execute("UPDATE patients SET synced = 1 WHERE patient_id = ?", (record_id,))
            elif record_type == 'health_assessment':
                cursor.execute("UPDATE health_assessments SET synced = 1 WHERE assessment_id = ?", (record_id,))
            
            conn.commit()
            conn.close()
        except Exception as e:
            self.logger.error(f"Error marking record as synced: {str(e)}")
    
    def _start_resource_manager(self) -> None:
        """Start the background resource management thread."""
        try:
            thread = threading.Thread(target=self._resource_management_loop)
            thread.daemon = True  # Thread will exit when main program exits
            thread.start()
            
            self.logger.info("Resource management thread started")
        except Exception as e:
            self.logger.error(f"Error starting resource manager: {str(e)}")
    
    def _resource_management_loop(self) -> None:
        """Background loop for resource management."""
        while True:
            try:
                # Check storage usage
                self._manage_storage()
                
                # Sleep for a while before next check
                time.sleep(3600)  # Check every hour
            except Exception as e:
                self.logger.error(f"Error in resource management loop: {str(e)}")
                time.sleep(3600)  # Sleep and try again
    
    def _manage_storage(self) -> None:
        """Manage local storage to prevent exceeding limits."""
        try:
            # Get current storage size
            db_size = os.path.getsize(self.local_db_path) / (1024 * 1024)  # Convert to MB
            
            # Check if we're approaching the limit
            if db_size > self.config['max_storage_size_mb'] * 0.9:
                self.logger.warning(f"Local storage approaching limit: {db_size:.2f}MB / {self.config['max_storage_size_mb']}MB")
                
                # Clean up old synced records
                self._clean_old_synced_records()
            
            # Check for old resources that can be removed
            self._clean_old_resources()
        except Exception as e:
            self.logger.error(f"Error managing storage: {str(e)}")
    
    def _clean_old_synced_records(self) -> None:
        """Clean up old synced records to free up space."""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Get cutoff date (records older than max_offline_days that are synced)
            cutoff_date = (datetime.now() - timedelta(days=self.config['max_offline_days'])).isoformat()
            
            # Delete old synced health assessments
            cursor.execute(
                "DELETE FROM health_assessments WHERE synced = 1 AND created_at < ?",
                (cutoff_date,)
            )
            
            # For patients, we need to be more careful - only delete if no recent assessments
            # First, get patients with recent assessments
            cursor.execute(
                """SELECT DISTINCT patient_id FROM health_assessments 
                   WHERE created_at >= ?""",
                (cutoff_date,)
            )
            
            recent_patient_ids = [row[0] for row in cursor.fetchall()]
            
            # Then delete old synced patients that don't have recent assessments
            if recent_patient_ids:
                placeholders = ','.join(['?'] * len(recent_patient_ids))
                cursor.execute(
                    f"""DELETE FROM patients 
                       WHERE synced = 1 AND updated_at < ? 
                       AND patient_id NOT IN ({placeholders})""",
                    [cutoff_date] + recent_patient_ids
                )
            else:
                cursor.execute(
                    "DELETE FROM patients WHERE synced = 1 AND updated_at < ?",
                    (cutoff_date,)
                )
            
            conn.commit()
            conn.close()
            
            self.logger.info("Cleaned up old synced records")
        except Exception as e:
            self.logger.error(f"Error cleaning old synced records: {str(e)}")
    
    def _clean_old_resources(self) -> None:
        """Clean up old resources to free up space."""
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Get resources ordered by last accessed time (oldest first) and access count (lowest first)
            cursor.execute(
                """SELECT resource_id, resource_type, file_path, size_bytes 
                   FROM resources 
                   ORDER BY last_accessed ASC, access_count ASC"""
            )
            
            resources = cursor.fetchall()
            
            # Calculate total size
            total_size_mb = sum(res[3] for res in resources) / (1024 * 1024)
            
            # If we're over 80% of the limit, start removing resources
            if total_size_mb > self.config['max_storage_size_mb'] * 0.8:
                self.logger.info(f"Resource storage at {total_size_mb:.2f}MB, cleaning up old resources")
                
                # Calculate how much we need to remove
                target_size_mb = self.config['max_storage_size_mb'] * 0.6  # Target 60% usage
                to_remove_mb = total_size_mb - target_size_mb
                removed_mb = 0
                
                for res in resources:
                    resource_id, resource_type, file_path, size_bytes = res
                    size_mb = size_bytes / (1024 * 1024)
                    
                    # Skip essential resources
                    if resource_type in ['essential', 'system']:
                        continue
                    
                    # Remove the resource file if it exists
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            self.logger.info(f"Removed resource file: {file_path}")
                        except Exception as e:
                            self.logger.error(f"Error removing resource file {file_path}: {str(e)}")
                            continue
                    
                    # Remove from database
                    cursor.execute("DELETE FROM resources WHERE resource_id = ?", (resource_id,))
                    
                    # Update removed size
                    removed_mb += size_mb
                    
                    # Stop if we've removed enough
                    if removed_mb >= to_remove_mb:
                        break
                
                conn.commit()
                self.logger.info(f"Removed {removed_mb:.2f}MB of resources")
            
            conn.close()
        except Exception as e:
            self.logger.error(f"Error cleaning old resources: {str(e)}")
    
    def register_resource(self, resource_type: str, file_path: str) -> str:
        """Register a resource in the resource tracking system.
        
        Args:
            resource_type: Type of resource (audio, image, model, etc.)
            file_path: Path to the resource file
            
        Returns:
            Resource ID if successful, None otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Resource file does not exist: {file_path}")
                return None
            
            # Generate resource ID
            resource_id = f"{resource_type}_{int(time.time())}_{os.path.basename(file_path)}"
            
            # Get file size
            size_bytes = os.path.getsize(file_path)
            
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            now = datetime.now().isoformat()
            
            # Insert resource record
            cursor.execute(
                """INSERT INTO resources 
                   (resource_id, resource_type, file_path, size_bytes, created_at, last_accessed, access_count) 
                   VALUES (?, ?, ?, ?, ?, ?, 0)""",
                (resource_id, resource_type, file_path, size_bytes, now, now)
            )
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Registered resource: {resource_id}, size: {size_bytes/1024:.2f}KB")
            
            return resource_id
        except Exception as e:
            self.logger.error(f"Error registering resource: {str(e)}")
            return None
    
    def access_resource(self, resource_id: str) -> str:
        """Record access to a resource and return its file path.
        
        Args:
            resource_id: Resource ID
            
        Returns:
            File path if successful, None otherwise
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Get resource information
            cursor.execute("SELECT file_path FROM resources WHERE resource_id = ?", (resource_id,))
            result = cursor.fetchone()
            
            if not result:
                conn.close()
                self.logger.warning(f"Resource not found: {resource_id}")
                return None
            
            file_path = result[0]
            
            # Update access information
            now = datetime.now().isoformat()
            cursor.execute(
                "UPDATE resources SET last_accessed = ?, access_count = access_count + 1 WHERE resource_id = ?",
                (now, resource_id)
            )
            
            conn.commit()
            conn.close()
            
            return file_path
        except Exception as e:
            self.logger.error(f"Error accessing resource: {str(e)}")
            return None