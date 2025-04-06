#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
User Service for ASHA Connect

This module handles all user-related functionality including:
- User authentication and authorization
- User profile management
- Role-based access control
- User preferences and settings
"""

import os
import logging
import json
import time
import hashlib
import uuid
from typing import Dict, List, Optional, Tuple, Union

# JWT for token-based authentication
import jwt
from datetime import datetime, timedelta

class UserService:
    """Service for handling user management in ASHA Connect."""
    
    def __init__(self, db):
        """Initialize the user service with necessary components.
        
        Args:
            db: Database connection instance
        """
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing User Service")
        
        self.db = db
        self.secret_key = os.getenv('JWT_SECRET_KEY', 'default-secret-key')
        self.token_expiry = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 86400))  # 24 hours default
        
        # User roles and permissions
        self.roles = {
            'asha': {
                'permissions': [
                    'health:assess',
                    'health:view',
                    'patient:create',
                    'patient:view',
                    'patient:update'
                ]
            },
            'supervisor': {
                'permissions': [
                    'health:assess',
                    'health:view',
                    'patient:create',
                    'patient:view',
                    'patient:update',
                    'user:view',
                    'reports:view'
                ]
            },
            'admin': {
                'permissions': [
                    'health:assess',
                    'health:view',
                    'patient:create',
                    'patient:view',
                    'patient:update',
                    'user:create',
                    'user:view',
                    'user:update',
                    'user:delete',
                    'reports:view',
                    'reports:create',
                    'system:configure'
                ]
            }
        }
        
        self.logger.info("User Service initialized successfully")
    
    def authenticate(self, username: str, password: str) -> Dict:
        """Authenticate a user with username and password.
        
        Args:
            username: User's username or phone number
            password: User's password
            
        Returns:
            Dict containing authentication result and token if successful
        """
        self.logger.info(f"Authentication attempt for user: {username}")
        
        try:
            # In a real implementation, this would query the database
            # Simplified implementation for demonstration
            user = self._get_user_by_username(username)
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Check password
            hashed_password = self._hash_password(password, user.get('salt', ''))
            if hashed_password != user.get('password'):
                return {
                    'success': False,
                    'error': 'Invalid password'
                }
            
            # Generate token
            token = self._generate_token(user)
            
            return {
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'permissions': self.roles[user['role']]['permissions']
                },
                'token': token
            }
            
        except Exception as e:
            self.logger.error(f"Authentication error: {str(e)}")
            return {
                'success': False,
                'error': 'Authentication failed'
            }
    
    def verify_token(self, token: str) -> Dict:
        """Verify a JWT token and return user information.
        
        Args:
            token: JWT token to verify
            
        Returns:
            Dict containing verification result and user info if successful
        """
        try:
            # Decode and verify token
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            
            # Check if token is expired
            if 'exp' in payload and payload['exp'] < time.time():
                return {
                    'success': False,
                    'error': 'Token expired'
                }
            
            # Get user from database to ensure they still exist and have same permissions
            user = self._get_user_by_id(payload['user_id'])
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            return {
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'permissions': self.roles[user['role']]['permissions']
                }
            }
            
        except jwt.ExpiredSignatureError:
            return {
                'success': False,
                'error': 'Token expired'
            }
        except jwt.InvalidTokenError:
            return {
                'success': False,
                'error': 'Invalid token'
            }
        except Exception as e:
            self.logger.error(f"Token verification error: {str(e)}")
            return {
                'success': False,
                'error': 'Token verification failed'
            }
    
    def create_user(self, user_data: Dict, created_by: str) -> Dict:
        """Create a new user in the system.
        
        Args:
            user_data: Dictionary containing user information
            created_by: ID of the user creating this user
            
        Returns:
            Dict containing creation result and user info if successful
        """
        try:
            # Validate required fields
            required_fields = ['username', 'password', 'name', 'role', 'phone']
            for field in required_fields:
                if field not in user_data:
                    return {
                        'success': False,
                        'error': f"Missing required field: {field}"
                    }
            
            # Check if username already exists
            existing_user = self._get_user_by_username(user_data['username'])
            if existing_user:
                return {
                    'success': False,
                    'error': 'Username already exists'
                }
            
            # Check if role is valid
            if user_data['role'] not in self.roles:
                return {
                    'success': False,
                    'error': f"Invalid role: {user_data['role']}"
                }
            
            # Generate salt and hash password
            salt = uuid.uuid4().hex
            hashed_password = self._hash_password(user_data['password'], salt)
            
            # Create user object
            new_user = {
                'id': str(uuid.uuid4()),
                'username': user_data['username'],
                'password': hashed_password,
                'salt': salt,
                'name': user_data['name'],
                'role': user_data['role'],
                'phone': user_data['phone'],
                'email': user_data.get('email', ''),
                'location': user_data.get('location', {}),
                'created_at': datetime.now().isoformat(),
                'created_by': created_by,
                'last_login': None,
                'is_active': True
            }
            
            # Save to database
            # In a real implementation, this would save to the database
            # Simplified implementation for demonstration
            success = self._save_user(new_user)
            
            if success:
                return {
                    'success': True,
                    'user': {
                        'id': new_user['id'],
                        'username': new_user['username'],
                        'name': new_user['name'],
                        'role': new_user['role'],
                        'phone': new_user['phone'],
                        'email': new_user['email'],
                        'created_at': new_user['created_at']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to save user'
                }
                
        except Exception as e:
            self.logger.error(f"User creation error: {str(e)}")
            return {
                'success': False,
                'error': 'User creation failed'
            }
    
    def get_user(self, user_id: str) -> Dict:
        """Get user information by ID.
        
        Args:
            user_id: ID of the user to retrieve
            
        Returns:
            Dict containing user information
        """
        try:
            user = self._get_user_by_id(user_id)
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            return {
                'success': True,
                'user': {
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'phone': user['phone'],
                    'email': user.get('email', ''),
                    'location': user.get('location', {}),
                    'created_at': user['created_at'],
                    'last_login': user['last_login'],
                    'is_active': user['is_active']
                }
            }
            
        except Exception as e:
            self.logger.error(f"Get user error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to retrieve user'
            }
    
    def update_user(self, user_id: str, user_data: Dict, updated_by: str) -> Dict:
        """Update user information.
        
        Args:
            user_id: ID of the user to update
            user_data: Dictionary containing updated user information
            updated_by: ID of the user making the update
            
        Returns:
            Dict containing update result and updated user info if successful
        """
        try:
            # Get existing user
            user = self._get_user_by_id(user_id)
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # Update fields
            updatable_fields = ['name', 'role', 'phone', 'email', 'location', 'is_active']
            for field in updatable_fields:
                if field in user_data:
                    user[field] = user_data[field]
            
            # Update password if provided
            if 'password' in user_data and user_data['password']:
                salt = uuid.uuid4().hex
                hashed_password = self._hash_password(user_data['password'], salt)
                user['password'] = hashed_password
                user['salt'] = salt
            
            # Add update metadata
            user['updated_at'] = datetime.now().isoformat()
            user['updated_by'] = updated_by
            
            # Save to database
            # In a real implementation, this would update the database
            # Simplified implementation for demonstration
            success = self._update_user(user)
            
            if success:
                return {
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username'],
                        'name': user['name'],
                        'role': user['role'],
                        'phone': user['phone'],
                        'email': user.get('email', ''),
                        'location': user.get('location', {}),
                        'is_active': user['is_active'],
                        'updated_at': user['updated_at']
                    }
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to update user'
                }
                
        except Exception as e:
            self.logger.error(f"Update user error: {str(e)}")
            return {
                'success': False,
                'error': 'User update failed'
            }
    
    def delete_user(self, user_id: str, deleted_by: str) -> Dict:
        """Delete a user from the system.
        
        Args:
            user_id: ID of the user to delete
            deleted_by: ID of the user performing the deletion
            
        Returns:
            Dict containing deletion result
        """
        try:
            # Get existing user
            user = self._get_user_by_id(user_id)
            
            if not user:
                return {
                    'success': False,
                    'error': 'User not found'
                }
            
            # In a real implementation, consider soft delete instead of hard delete
            # Soft delete: mark as inactive but keep in database
            user['is_active'] = False
            user['deleted_at'] = datetime.now().isoformat()
            user['deleted_by'] = deleted_by
            
            # Save to database
            # In a real implementation, this would update the database
            # Simplified implementation for demonstration
            success = self._update_user(user)
            
            if success:
                return {
                    'success': True,
                    'message': 'User deleted successfully'
                }
            else:
                return {
                    'success': False,
                    'error': 'Failed to delete user'
                }
                
        except Exception as e:
            self.logger.error(f"Delete user error: {str(e)}")
            return {
                'success': False,
                'error': 'User deletion failed'
            }
    
    def list_users(self, filters: Dict = None, page: int = 1, limit: int = 20) -> Dict:
        """List users with optional filtering and pagination.
        
        Args:
            filters: Dictionary containing filter criteria
            page: Page number for pagination
            limit: Number of results per page
            
        Returns:
            Dict containing list of users and pagination info
        """
        try:
            # In a real implementation, this would query the database with filters and pagination
            # Simplified implementation for demonstration
            users = self._get_all_users()
            
            # Apply filters if provided
            if filters:
                filtered_users = []
                for user in users:
                    match = True
                    for key, value in filters.items():
                        if key in user and user[key] != value:
                            match = False
                            break
                    if match:
                        filtered_users.append(user)
                users = filtered_users
            
            # Apply pagination
            total = len(users)
            start = (page - 1) * limit
            end = start + limit
            paginated_users = users[start:end]
            
            # Format user data for response
            formatted_users = []
            for user in paginated_users:
                formatted_users.append({
                    'id': user['id'],
                    'username': user['username'],
                    'name': user['name'],
                    'role': user['role'],
                    'phone': user['phone'],
                    'email': user.get('email', ''),
                    'is_active': user['is_active'],
                    'created_at': user['created_at'],
                    'last_login': user['last_login']
                })
            
            return {
                'success': True,
                'users': formatted_users,
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                }
            }
            
        except Exception as e:
            self.logger.error(f"List users error: {str(e)}")
            return {
                'success': False,
                'error': 'Failed to list users'
            }
    
    def check_permission(self, user_id: str, permission: str) -> bool:
        """Check if a user has a specific permission.
        
        Args:
            user_id: ID of the user to check
            permission: Permission to check for
            
        Returns:
            Boolean indicating if user has the permission
        """
        try:
            user = self._get_user_by_id(user_id)
            
            if not user or not user['is_active']:
                return False
            
            role = user['role']
            if role not in self.roles:
                return False
            
            return permission in self.roles[role]['permissions']
            
        except Exception as e:
            self.logger.error(f"Permission check error: {str(e)}")
            return False
    
    def update_last_login(self, user_id: str) -> bool:
        """Update the last login timestamp for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Boolean indicating success
        """
        try:
            user = self._get_user_by_id(user_id)
            
            if not user:
                return False
            
            user['last_login'] = datetime.now().isoformat()
            
            return self._update_user(user)
            
        except Exception as e:
            self.logger.error(f"Update last login error: {str(e)}")
            return False
    
    def _hash_password(self, password: str, salt: str) -> str:
        """Hash a password with the given salt.
        
        Args:
            password: Password to hash
            salt: Salt to use in hashing
            
        Returns:
            Hashed password
        """
        # Use a secure hashing algorithm (SHA-256 in this example)
        # In production, consider using more specialized password hashing libraries
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    def _generate_token(self, user: Dict) -> str:
        """Generate a JWT token for a user.
        
        Args:
            user: User dictionary
            
        Returns:
            JWT token string
        """
        payload = {
            'user_id': user['id'],
            'username': user['username'],
            'role': user['role'],
            'exp': datetime.now() + timedelta(seconds=self.token_expiry)
        }
        
        return jwt.encode(payload, self.secret_key, algorithm='HS256')
    
    # Database access methods (simplified for demonstration)
    def _get_user_by_username(self, username: str) -> Optional[Dict]:
        """Get a user by username from the database.
        
        Args:
            username: Username to search for
            
        Returns:
            User dictionary or None if not found
        """
        # In a real implementation, this would query the database
        # Simplified implementation for demonstration
        
        # Mock data for demonstration
        if username == 'asha1':
            return {
                'id': '1',
                'username': 'asha1',
                'password': self._hash_password('password123', 'salt1'),
                'salt': 'salt1',
                'name': 'Asha Worker 1',
                'role': 'asha',
                'phone': '+919876543210',
                'email': 'asha1@example.com',
                'location': {'village': 'Rajpur', 'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        elif username == 'supervisor1':
            return {
                'id': '2',
                'username': 'supervisor1',
                'password': self._hash_password('password123', 'salt2'),
                'salt': 'salt2',
                'name': 'Supervisor 1',
                'role': 'supervisor',
                'phone': '+919876543211',
                'email': 'supervisor1@example.com',
                'location': {'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        elif username == 'admin':
            return {
                'id': '3',
                'username': 'admin',
                'password': self._hash_password('password123', 'salt3'),
                'salt': 'salt3',
                'name': 'Admin User',
                'role': 'admin',
                'phone': '+919876543212',
                'email': 'admin@example.com',
                'location': {},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        
        return None
    
    def _get_user_by_id(self, user_id: str) -> Optional[Dict]:
        """Get a user by ID from the database.
        
        Args:
            user_id: User ID to search for
            
        Returns:
            User dictionary or None if not found
        """
        # In a real implementation, this would query the database
        # Simplified implementation for demonstration
        
        # Mock data for demonstration
        if user_id == '1':
            return {
                'id': '1',
                'username': 'asha1',
                'password': self._hash_password('password123', 'salt1'),
                'salt': 'salt1',
                'name': 'Asha Worker 1',
                'role': 'asha',
                'phone': '+919876543210',
                'email': 'asha1@example.com',
                'location': {'village': 'Rajpur', 'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        elif user_id == '2':
            return {
                'id': '2',
                'username': 'supervisor1',
                'password': self._hash_password('password123', 'salt2'),
                'salt': 'salt2',
                'name': 'Supervisor 1',
                'role': 'supervisor',
                'phone': '+919876543211',
                'email': 'supervisor1@example.com',
                'location': {'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        elif user_id == '3':
            return {
                'id': '3',
                'username': 'admin',
                'password': self._hash_password('password123', 'salt3'),
                'salt': 'salt3',
                'name': 'Admin User',
                'role': 'admin',
                'phone': '+919876543212',
                'email': 'admin@example.com',
                'location': {},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        
        return None
    
    def _get_all_users(self) -> List[Dict]:
        """Get all users from the database.
        
        Returns:
            List of user dictionaries
        """
        # In a real implementation, this would query the database
        # Simplified implementation for demonstration
        
        # Mock data for demonstration
        return [
            {
                'id': '1',
                'username': 'asha1',
                'name': 'Asha Worker 1',
                'role': 'asha',
                'phone': '+919876543210',
                'email': 'asha1@example.com',
                'location': {'village': 'Rajpur', 'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            },
            {
                'id': '2',
                'username': 'supervisor1',
                'name': 'Supervisor 1',
                'role': 'supervisor',
                'phone': '+919876543211',
                'email': 'supervisor1@example.com',
                'location': {'district': 'Example District'},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            },
            {
                'id': '3',
                'username': 'admin',
                'name': 'Admin User',
                'role': 'admin',
                'phone': '+919876543212',
                'email': 'admin@example.com',
                'location': {},
                'created_at': '2023-01-01T00:00:00',
                'last_login': None,
                'is_active': True
            }
        ]
    
    def _save_user(self, user: Dict) -> bool:
        """Save a new user to the database.
        
        Args:
            user: User dictionary to save
            
        Returns:
            Boolean indicating success
        """
        # In a real implementation, this would save to the database
        # Simplified implementation for demonstration
        return True
    
    def _update_user(self, user: Dict) -> bool:
        """Update an existing user in the database.
        
        Args:
            user: User dictionary to update
            
        Returns:
            Boolean indicating success
        """
        # In a real implementation, this would update the database
        # Simplified implementation for demonstration
        return True