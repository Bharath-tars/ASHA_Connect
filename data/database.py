#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Database Module for ASHA Connect

This module handles database connections and provides a unified interface
for data access across the application. It supports both MongoDB for cloud
storage and SQLite for local offline storage.
"""

import os
import logging
import json
from typing import Dict, List, Optional, Any, Union

# MongoDB connection
try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# SQLite for offline storage
import sqlite3
from datetime import datetime

class Database:
    """Database connection and management for ASHA Connect."""
    
    def __init__(self):
        """Initialize database connections."""
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing Database Connection")
        
        # MongoDB connection settings
        self.mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/asha_connect')
        self.db_name = os.getenv('DB_NAME', 'asha_connect')
        
        # Local SQLite database for offline mode
        self.sqlite_path = os.getenv('SQLITE_PATH', 'data/local.db')
        
        # Initialize connections
        self.mongo_client = None
        self.mongo_db = None
        self.is_connected = False
        
        # Try to connect to MongoDB
        if MONGODB_AVAILABLE:
            self._connect_mongodb()
        else:
            self.logger.warning("MongoDB driver not available. Running in offline mode only.")
        
        # Initialize SQLite database
        self._init_sqlite()
        
        self.logger.info("Database initialization complete")
    
    def _connect_mongodb(self) -> bool:
        """Connect to MongoDB server.
        
        Returns:
            Boolean indicating connection success
        """
        try:
            self.logger.info(f"Connecting to MongoDB at {self.mongo_uri}")
            self.mongo_client = MongoClient(self.mongo_uri, serverSelectionTimeoutMS=5000)
            
            # Verify connection
            self.mongo_client.admin.command('ping')
            
            self.mongo_db = self.mongo_client[self.db_name]
            self.is_connected = True
            self.logger.info("Successfully connected to MongoDB")
            return True
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.warning(f"Failed to connect to MongoDB: {str(e)}")
            self.is_connected = False
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error connecting to MongoDB: {str(e)}")
            self.is_connected = False
            return False
    
    def _init_sqlite(self) -> None:
        """Initialize SQLite database for offline storage."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.sqlite_path), exist_ok=True)
            
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Create tables for core data types
            
            # Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    phone TEXT NOT NULL,
                    email TEXT,
                    location TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT,
                    updated_at TEXT,
                    updated_by TEXT,
                    last_login TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sync_status TEXT DEFAULT 'pending'
                )
            """)
            
            # Patients table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS patients (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    age INTEGER,
                    gender TEXT,
                    phone TEXT,
                    address TEXT,
                    village TEXT,
                    district TEXT,
                    state TEXT,
                    medical_history TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_at TEXT,
                    updated_by TEXT,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    sync_status TEXT DEFAULT 'pending'
                )
            """)
            
            # Health assessments table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS health_assessments (
                    id TEXT PRIMARY KEY,
                    patient_id TEXT NOT NULL,
                    symptoms TEXT NOT NULL,
                    assessment TEXT NOT NULL,
                    recommendations TEXT,
                    referral TEXT,
                    created_at TEXT NOT NULL,
                    created_by TEXT NOT NULL,
                    updated_at TEXT,
                    updated_by TEXT,
                    sync_status TEXT DEFAULT 'pending',
                    FOREIGN KEY (patient_id) REFERENCES patients (id)
                )
            """)
            
            # Create indexes
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_patients_village ON patients (village)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assessments_patient ON health_assessments (patient_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_sync_status ON health_assessments (sync_status)")
            
            conn.commit()
            conn.close()
            
            self.logger.info("SQLite database initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Error initializing SQLite database: {str(e)}")
            raise
    
    def is_online(self) -> bool:
        """Check if database is in online mode (connected to MongoDB).
        
        Returns:
            Boolean indicating online status
        """
        if not self.is_connected and MONGODB_AVAILABLE:
            # Try to reconnect if previously disconnected
            self._connect_mongodb()
        return self.is_connected
    
    def insert_one(self, collection: str, document: Dict) -> Dict:
        """Insert a single document into the specified collection.
        
        Args:
            collection: Collection name
            document: Document to insert
            
        Returns:
            Dict containing operation result
        """
        try:
            # Add timestamps
            if 'created_at' not in document:
                document['created_at'] = datetime.now().isoformat()
            
            # Try MongoDB if online
            if self.is_online():
                result = self.mongo_db[collection].insert_one(document)
                return {
                    'success': True,
                    'id': str(result.inserted_id),
                    'online': True
                }
            
            # Fall back to SQLite
            return self._sqlite_insert(collection, document)
            
        except Exception as e:
            self.logger.error(f"Error inserting document into {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_one(self, collection: str, query: Dict) -> Dict:
        """Find a single document matching the query.
        
        Args:
            collection: Collection name
            query: Query criteria
            
        Returns:
            Dict containing operation result and document if found
        """
        try:
            # Try MongoDB if online
            if self.is_online():
                document = self.mongo_db[collection].find_one(query)
                if document:
                    # Convert ObjectId to string
                    document['_id'] = str(document['_id'])
                    return {
                        'success': True,
                        'document': document,
                        'online': True
                    }
            
            # Fall back to SQLite
            return self._sqlite_find_one(collection, query)
            
        except Exception as e:
            self.logger.error(f"Error finding document in {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def find_many(self, collection: str, query: Dict, limit: int = 100, skip: int = 0, sort: List = None) -> Dict:
        """Find multiple documents matching the query.
        
        Args:
            collection: Collection name
            query: Query criteria
            limit: Maximum number of results
            skip: Number of results to skip
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            Dict containing operation result and documents if found
        """
        try:
            # Try MongoDB if online
            if self.is_online():
                cursor = self.mongo_db[collection].find(query).skip(skip).limit(limit)
                
                if sort:
                    cursor = cursor.sort(sort)
                
                documents = list(cursor)
                
                # Convert ObjectId to string
                for doc in documents:
                    doc['_id'] = str(doc['_id'])
                
                return {
                    'success': True,
                    'documents': documents,
                    'count': len(documents),
                    'online': True
                }
            
            # Fall back to SQLite
            return self._sqlite_find_many(collection, query, limit, skip, sort)
            
        except Exception as e:
            self.logger.error(f"Error finding documents in {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def update_one(self, collection: str, query: Dict, update: Dict) -> Dict:
        """Update a single document matching the query.
        
        Args:
            collection: Collection name
            query: Query criteria
            update: Update operations
            
        Returns:
            Dict containing operation result
        """
        try:
            # Add update timestamp
            if '$set' in update:
                update['$set']['updated_at'] = datetime.now().isoformat()
            else:
                update['$set'] = {'updated_at': datetime.now().isoformat()}
            
            # Try MongoDB if online
            if self.is_online():
                result = self.mongo_db[collection].update_one(query, update)
                return {
                    'success': True,
                    'matched_count': result.matched_count,
                    'modified_count': result.modified_count,
                    'online': True
                }
            
            # Fall back to SQLite
            return self._sqlite_update(collection, query, update)
            
        except Exception as e:
            self.logger.error(f"Error updating document in {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def delete_one(self, collection: str, query: Dict) -> Dict:
        """Delete a single document matching the query.
        
        Args:
            collection: Collection name
            query: Query criteria
            
        Returns:
            Dict containing operation result
        """
        try:
            # Try MongoDB if online
            if self.is_online():
                result = self.mongo_db[collection].delete_one(query)
                return {
                    'success': True,
                    'deleted_count': result.deleted_count,
                    'online': True
                }
            
            # Fall back to SQLite
            return self._sqlite_delete(collection, query)
            
        except Exception as e:
            self.logger.error(f"Error deleting document from {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sqlite_insert(self, collection: str, document: Dict) -> Dict:
        """Insert a document into SQLite.
        
        Args:
            collection: Table name
            document: Document to insert
            
        Returns:
            Dict containing operation result
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Ensure ID exists
            if '_id' not in document and 'id' not in document:
                document['id'] = str(datetime.now().timestamp())
            elif '_id' in document and 'id' not in document:
                document['id'] = document['_id']
                del document['_id']
            
            # Convert document to JSON for storage
            document_json = json.dumps(document)
            
            # Special handling for core tables
            if collection in ['users', 'patients', 'health_assessments']:
                # Extract fields and insert into structured table
                fields = ', '.join(document.keys())
                placeholders = ', '.join(['?'] * len(document))
                values = list(document.values())
                
                query = f"INSERT OR REPLACE INTO {collection} ({fields}) VALUES ({placeholders})"
                cursor.execute(query, values)
            else:
                # For other collections, use a generic approach with JSON storage
                cursor.execute(
                    f"CREATE TABLE IF NOT EXISTS {collection} (id TEXT PRIMARY KEY, data TEXT, sync_status TEXT)"
                )
                cursor.execute(
                    f"INSERT OR REPLACE INTO {collection} (id, data, sync_status) VALUES (?, ?, ?)",
                    (document['id'], document_json, 'pending')
                )
            
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'id': document['id'],
                'online': False
            }
            
        except Exception as e:
            self.logger.error(f"SQLite insert error for {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sqlite_find_one(self, collection: str, query: Dict) -> Dict:
        """Find a single document in SQLite.
        
        Args:
            collection: Table name
            query: Query criteria
            
        Returns:
            Dict containing operation result and document if found
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for named columns
            cursor = conn.cursor()
            
            # Special handling for core tables
            if collection in ['users', 'patients', 'health_assessments']:
                # Build WHERE clause from query
                where_clauses = []
                params = []
                
                for key, value in query.items():
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                cursor.execute(f"SELECT * FROM {collection} WHERE {where_clause} LIMIT 1", params)
                row = cursor.fetchone()
                
                if row:
                    # Convert row to dict
                    document = {key: row[key] for key in row.keys()}
                    conn.close()
                    return {
                        'success': True,
                        'document': document,
                        'online': False
                    }
            else:
                # For other collections, use generic approach with JSON storage
                # Simplified query - only supports querying by ID
                if 'id' in query or '_id' in query:
                    id_value = query.get('id', query.get('_id'))
                    cursor.execute(f"SELECT data FROM {collection} WHERE id = ?", (id_value,))
                    row = cursor.fetchone()
                    
                    if row:
                        document = json.loads(row[0])
                        conn.close()
                        return {
                            'success': True,
                            'document': document,
                            'online': False
                        }
            
            conn.close()
            return {
                'success': True,
                'document': None,
                'online': False
            }
            
        except Exception as e:
            self.logger.error(f"SQLite find_one error for {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sqlite_find_many(self, collection: str, query: Dict, limit: int, skip: int, sort: List) -> Dict:
        """Find multiple documents in SQLite.
        
        Args:
            collection: Table name
            query: Query criteria
            limit: Maximum number of results
            skip: Number of results to skip
            sort: List of (field, direction) tuples for sorting
            
        Returns:
            Dict containing operation result and documents if found
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for named columns
            cursor = conn.cursor()
            
            # Special handling for core tables
            if collection in ['users', 'patients', 'health_assessments']:
                # Build WHERE clause from query
                where_clauses = []
                params = []
                
                for key, value in query.items():
                    where_clauses.append(f"{key} = ?")
                    params.append(value)
                
                where_clause = " AND ".join(where_clauses) if where_clauses else "1=1"
                
                # Build ORDER BY clause from sort
                order_clause = ""
                if sort:
                    order_terms = []
                    for field, direction in sort:
                        direction_str = "ASC" if direction == 1 else "DESC"
                        order_terms.append(f"{field} {direction_str}")
                    order_clause = f"ORDER BY {', '.join(order_terms)}"
                
                query_str = f"SELECT * FROM {collection} WHERE {where_clause} {order_clause} LIMIT {limit} OFFSET {skip}"
                cursor.execute(query_str, params)
                
                rows = cursor.fetchall()
                documents = [{key: row[key] for key in row.keys()} for row in rows]
                
                conn.close()
                return {
                    'success': True,
                    'documents': documents,
                    'count': len(documents),
                    'online': False
                }
            else:
                # For other collections, use generic approach with JSON storage
                # Note: This is a simplified implementation with limited query support
                cursor.execute(f"SELECT data FROM {collection} LIMIT {limit} OFFSET {skip}")
                
                rows = cursor.fetchall()
                documents = [json.loads(row[0]) for row in rows]
                
                conn.close()
                return {
                    'success': True,
                    'documents': documents,
                    'count': len(documents),
                    'online': False
                }
            
        except Exception as e:
            self.logger.error(f"SQLite find_many error for {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sqlite_update(self, collection: str, query: Dict, update: Dict) -> Dict:
        """Update a document in SQLite.
        
        Args:
            collection: Table name
            query: Query criteria
            update: Update operations
            
        Returns:
            Dict containing operation result
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Special handling for core tables
            if collection in ['users', 'patients', 'health_assessments']:
                # Extract $set operations
                if '$set' not in update:
                    return {
                        'success': False,
                        'error': "Only $set operations are supported in SQLite"
                    }
                
                set_values = update['$set']
                
                # Build SET clause
                set_clauses = []
                set_params = []
                
                for key, value in set_values.items():
                    set_clauses.append(f"{key} = ?")
                    set_params.append(value)
                
                set_clause = ", ".join(set_clauses)
                
                # Build WHERE clause
                where_clauses = []
                where_params = []
                
                for key, value in query.items():
                    where_clauses.append(f"{key} = ?")
                    where_params.append(value)
                
                where_clause = " AND ".join(where_clauses)
                
                # Execute update
                cursor.execute(
                    f"UPDATE {collection} SET {set_clause} WHERE {where_clause}",
                    set_params + where_params
                )
                
                modified_count = cursor.rowcount
                conn.commit()
                conn.close()
                
                return {
                    'success': True,
                    'matched_count': modified_count,
                    'modified_count': modified_count,
                    'online': False
                }
            else:
                # For other collections, use generic approach with JSON storage
                # Simplified implementation - only supports updating by ID
                if 'id' in query or '_id' in query:
                    id_value = query.get('id', query.get('_id'))
                    
                    # Get current document
                    cursor.execute(f"SELECT data FROM {collection} WHERE id = ?", (id_value,))
                    row = cursor.fetchone()
                    
                    if row:
                        # Update document
                        document = json.loads(row[0])
                        
                        if '$set' in update:
                            for key, value in update['$set'].items():
                                document[key] = value
                        
                        # Save updated document
                        cursor.execute(
                            f"UPDATE {collection} SET data = ?, sync_status = ? WHERE id = ?",
                            (json.dumps(document), 'pending', id_value)
                        )
                        
                        modified_count = cursor.rowcount
                        conn.commit()
                        conn.close()
                        
                        return {
                            'success': True,
                            'matched_count': modified_count,
                            'modified_count': modified_count,
                            'online': False
                        }
                
                conn.close()
                return {
                    'success': True,
                    'matched_count': 0,
                    'modified_count': 0,
                    'online': False
                }
            
        except Exception as e:
            self.logger.error(f"SQLite update error for {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _sqlite_delete(self, collection: str, query: Dict) -> Dict:
        """Delete a document from SQLite.
        
        Args:
            collection: Table name
            query: Query criteria
            
        Returns:
            Dict containing operation result
        """
        try:
            conn = sqlite3.connect(self.sqlite_path)
            cursor = conn.cursor()
            
            # Build WHERE clause
            where_clauses = []
            params = []
            
            for key, value in query.items():
                where_clauses.append(f"{key} = ?")
                params.append(value)
            
            where_clause = " AND ".join(where_clauses)
            
            # Execute delete
            cursor.execute(f"DELETE FROM {collection} WHERE {where_clause}", params)
            
            deleted_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return {
                'success': True,
                'deleted_count': deleted_count,
                'online': False
            }
            
        except Exception as e:
            self.logger.error(f"SQLite delete error for {collection}: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }