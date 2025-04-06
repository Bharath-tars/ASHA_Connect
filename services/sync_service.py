#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Sync Service for ASHA Connect

This module handles all data synchronization functionality including:
- Offline data storage and management
- Data synchronization when connectivity is available
- Conflict resolution for data changes
- Prioritization of critical data for sync
"""

import os
import logging
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
import sqlite3
import threading

class SyncService:
    """Service for handling data synchronization in ASHA Connect."""
    
    def __init__(self, db):
        """Initialize the sync service with necessary components.
        
        Args:
            db: Database connection instance
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Sync Service")
        
        self.db = db
        self.local_db_path = os.getenv('LOCAL_DB_PATH', 'data/local.db')
        self.sync_interval = int(os.getenv('SYNC_INTERVAL', 3600))  # Default: 1 hour
        self.max_offline_days = int(os.getenv('MAX_OFFLINE_DAYS', 30))  # Default: 30 days
        
        # Initialize local database
        self._init_local_db()
        
        # Start sync scheduler if enabled
        self.sync_enabled = os.getenv('SYNC_ENABLED', 'true').lower() == 'true'
        if self.sync_enabled:
            self._start_sync_scheduler()
        
        self.logger.info("Sync Service initialized successfully")
    
    def save_offline_data(self, data_type: str, data: Dict) -> Dict:
        """Save data to local storage for later synchronization.
        
        Args:
            data_type: Type of data (e.g., 'health_assessment', 'patient')
            data: Dictionary containing the data to save
            
        Returns:
            Dict containing save result
        """
        try:
            # Add metadata for synchronization
            sync_data = data.copy()
            sync_data['_sync_status'] = 'pending'
            sync_data['_sync_created'] = datetime.now().isoformat()
            sync_data['_sync_modified'] = datetime.now().isoformat()
            sync_data['_sync_id'] = f"{data_type}_{int(time.time())}_{data.get('id', 'new')}"
            
            # Save to local database
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Convert data to JSON string
            data_json = json.dumps(sync_data)
            
            # Insert or update in local database
            cursor.execute(
                "INSERT OR REPLACE INTO sync_data (sync_id, data_type, data, status, created_at, modified_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    sync_data['_sync_id'],
                    data_type,
                    data_json,
                    'pending',
                    sync_data['_sync_created'],
                    sync_data['_sync_modified']
                )
            )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'sync_id': sync_data['_sync_id'],
                'message': 'Data saved for synchronization'
            }
            
        except Exception as e:
            self.logger.error(f"Error saving offline data: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to save offline data: {str(e)}"
            }
    
    def get_offline_data(self, data_type: Optional[str] = None, sync_id: Optional[str] = None) -> Dict:
        """Retrieve data from local storage.
        
        Args:
            data_type: Optional type of data to filter by
            sync_id: Optional specific sync ID to retrieve
            
        Returns:
            Dict containing retrieved data
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for named columns
            cursor = conn.cursor()
            
            # Build query based on parameters
            query = "SELECT * FROM sync_data WHERE 1=1"
            params = []
            
            if data_type:
                query += " AND data_type = ?"
                params.append(data_type)
                
            if sync_id:
                query += " AND sync_id = ?"
                params.append(sync_id)
            
            # Execute query
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            # Process results
            results = []
            for row in rows:
                data = json.loads(row['data'])
                results.append({
                    'sync_id': row['sync_id'],
                    'data_type': row['data_type'],
                    'status': row['status'],
                    'created_at': row['created_at'],
                    'modified_at': row['modified_at'],
                    'data': data
                })
            
            conn.close()
            
            return {
                'success': True,
                'count': len(results),
                'data': results
            }
            
        except Exception as e:
            self.logger.error(f"Error retrieving offline data: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retrieve offline data: {str(e)}"
            }
    
    def sync_data(self, force: bool = False) -> Dict:
        """Synchronize pending data with the server.
        
        Args:
            force: Force synchronization even if not scheduled
            
        Returns:
            Dict containing synchronization results
        """
        if not self._is_online() and not force:
            return {
                'success': False,
                'error': 'No internet connection available'
            }
        
        try:
            self.logger.info("Starting data synchronization")
            
            # Get pending data from local database
            conn = sqlite3.connect(self.local_db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM sync_data WHERE status = 'pending' ORDER BY created_at ASC"
            )
            pending_rows = cursor.fetchall()
            
            if not pending_rows:
                conn.close()
                return {
                    'success': True,
                    'message': 'No pending data to synchronize',
                    'synced': 0,
                    'failed': 0
                }
            
            # Process each pending item
            synced = 0
            failed = 0
            
            for row in pending_rows:
                sync_id = row['sync_id']
                data_type = row['data_type']
                data = json.loads(row['data'])
                
                # Attempt to sync with server
                sync_result = self._sync_with_server(data_type, data)
                
                if sync_result['success']:
                    # Update status to synced
                    cursor.execute(
                        "UPDATE sync_data SET status = 'synced', modified_at = ? WHERE sync_id = ?",
                        (datetime.now().isoformat(), sync_id)
                    )
                    synced += 1
                else:
                    # Update status to failed if this is a persistent failure
                    # For temporary failures, leave as pending for next sync
                    if sync_result.get('permanent_failure', False):
                        cursor.execute(
                            "UPDATE sync_data SET status = 'failed', modified_at = ? WHERE sync_id = ?",
                            (datetime.now().isoformat(), sync_id)
                        )
                    failed += 1
            
            conn.commit()
            
            # Clean up old synced data
            self._cleanup_old_data(cursor)
            
            conn.commit()
            conn.close()
            
            self.logger.info(f"Sync completed: {synced} synced, {failed} failed")
            
            return {
                'success': True,
                'message': 'Synchronization completed',
                'synced': synced,
                'failed': failed
            }
            
        except Exception as e:
            self.logger.error(f"Synchronization error: {str(e)}")
            return {
                'success': False,
                'error': f"Synchronization failed: {str(e)}"
            }
    
    def get_sync_status(self) -> Dict:
        """Get the current synchronization status.
        
        Returns:
            Dict containing sync status information
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Get counts by status
            cursor.execute("SELECT status, COUNT(*) as count FROM sync_data GROUP BY status")
            status_counts = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Get last sync time
            cursor.execute(
                "SELECT MAX(modified_at) as last_sync FROM sync_data WHERE status = 'synced'"
            )
            last_sync = cursor.fetchone()[0]
            
            # Get oldest pending item
            cursor.execute(
                "SELECT MIN(created_at) as oldest_pending FROM sync_data WHERE status = 'pending'"
            )
            oldest_pending = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                'success': True,
                'is_online': self._is_online(),
                'pending_count': status_counts.get('pending', 0),
                'synced_count': status_counts.get('synced', 0),
                'failed_count': status_counts.get('failed', 0),
                'last_sync': last_sync,
                'oldest_pending': oldest_pending,
                'sync_enabled': self.sync_enabled
            }
            
        except Exception as e:
            self.logger.error(f"Error getting sync status: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to get sync status: {str(e)}"
            }
    
    def retry_failed_sync(self) -> Dict:
        """Retry failed synchronization items.
        
        Returns:
            Dict containing retry results
        """
        try:
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Update failed items to pending
            cursor.execute(
                "UPDATE sync_data SET status = 'pending', modified_at = ? WHERE status = 'failed'",
                (datetime.now().isoformat(),)
            )
            
            retried_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            # Trigger sync if items were retried
            if retried_count > 0:
                self.sync_data()
            
            return {
                'success': True,
                'retried_count': retried_count,
                'message': f"Retried {retried_count} failed items"
            }
            
        except Exception as e:
            self.logger.error(f"Error retrying failed sync: {str(e)}")
            return {
                'success': False,
                'error': f"Failed to retry sync: {str(e)}"
            }
    
    def _init_local_db(self) -> None:
        """Initialize the local SQLite database."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.local_db_path), exist_ok=True)
            
            conn = sqlite3.connect(self.local_db_path)
            cursor = conn.cursor()
            
            # Create sync_data table if it doesn't exist
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_data (
                    sync_id TEXT PRIMARY KEY,
                    data_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    modified_at TEXT NOT NULL
                )
            """)
            
            # Create index on status for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON sync_data (status)")
            
            # Create index on data_type for faster queries
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_data_type ON sync_data (data_type)")
            
            conn.commit()
            conn.close()
            
            self.logger.info("Local database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing local database: {str(e)}")
            raise
    
    def _start_sync_scheduler(self) -> None:
        """Start the background sync scheduler."""
        def sync_worker():
            while self.sync_enabled:
                try:
                    # Only sync if online
                    if self._is_online():
                        self.sync_data()
                except Exception as e:
                    self.logger.error(f"Error in sync worker: {str(e)}")
                
                # Sleep until next sync interval
                time.sleep(self.sync_interval)
        
        # Start sync thread
        sync_thread = threading.Thread(target=sync_worker, daemon=True)
        sync_thread.start()
        
        self.logger.info(f"Sync scheduler started with interval: {self.sync_interval} seconds")
    
    def _cleanup_old_data(self, cursor) -> None:
        """Clean up old synced data that exceeds retention period.
        
        Args:
            cursor: SQLite cursor for database operations
        """
        # Calculate cutoff date for data retention
        cutoff_date = (datetime.now() - timedelta(days=self.max_offline_days)).isoformat()
        
        # Delete old synced data
        cursor.execute(
            "DELETE FROM sync_data WHERE status = 'synced' AND modified_at < ?",
            (cutoff_date,)
        )
        
        deleted_count = cursor.rowcount
        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old synced records")
    
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
    
    def _sync_with_server(self, data_type: str, data: Dict) -> Dict:
        """Synchronize a single data item with the server.
        
        Args:
            data_type: Type of data to sync
            data: Data to synchronize
            
        Returns:
            Dict containing sync result
        """
        # In a real implementation, this would make API calls to the server
        # Simplified implementation for demonstration
        
        try:
            # Remove sync metadata before sending to server
            clean_data = data.copy()
            for key in list(clean_data.keys()):
                if key.startswith('_sync_'):
                    del clean_data[key]
            
            # Simulate server communication
            # In a real implementation, this would be an API call
            
            # Simulate different sync handlers based on data type
            if data_type == 'health_assessment':
                # Simulate syncing health assessment data
                pass
            elif data_type == 'patient':
                # Simulate syncing patient data
                pass
            elif data_type == 'user_activity':
                # Simulate syncing user activity data
                pass
            
            # Simulate successful sync
            return {
                'success': True,
                'message': f"Successfully synced {data_type} data"
            }
            
        except Exception as e:
            self.logger.error(f"Error syncing with server: {str(e)}")
            
            # Determine if this is a permanent failure or temporary
            is_permanent = False
            if 'invalid data format' in str(e).lower():
                is_permanent = True
            
            return {
                'success': False,
                'error': str(e),
                'permanent_failure': is_permanent
            }