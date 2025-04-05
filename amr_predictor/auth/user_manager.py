#!/usr/bin/env python3
"""
User management for authentication.

This module handles user registration, authentication, and session management.
"""
import os
import uuid
import logging
import sqlite3
import jwt
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union
from passlib.context import CryptContext

from amr_predictor.auth.models import User, UserInDB, TokenData, UserCreate
from amr_predictor.bakta.database import DatabaseManager, BaktaDatabaseError

# Configure logging
logger = logging.getLogger("user-manager")

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "development_secret_key")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 8  # 8 hours

class UserManagerError(Exception):
    """Base exception for user management errors"""
    pass

class UserManager:
    """
    Handles user management and authentication.
    """
    
    def __init__(self, db_path: str = None, db_manager: DatabaseManager = None):
        """
        Initialize the UserManager.
        
        Args:
            db_path: Path to SQLite database (optional)
            db_manager: Existing DatabaseManager instance (optional)
        """
        if db_manager:
            self.db_manager = db_manager
        else:
            self.db_manager = DatabaseManager(db_path)
            
        # Create user tables if they don't exist
        self._create_user_tables()
        
    def _create_user_tables(self):
        """Create user authentication tables if they don't exist"""
        try:
            conn = self.db_manager._get_connection()
            
            # Create users table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE,
                    full_name TEXT,
                    password_hash TEXT NOT NULL,
                    disabled INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            
            # Create sessions table for token tracking (optional, for token revocation)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_sessions (
                    token_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    revoked INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            
            # Create indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)")
            
            conn.commit()
            logger.info("User tables created or verified")
            
        except sqlite3.Error as e:
            error_msg = f"Failed to create user tables: {str(e)}"
            logger.error(error_msg)
            raise UserManagerError(error_msg)
    
    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a hash"""
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}")
            return False
    
    def _get_password_hash(self, password: str) -> str:
        """Generate a password hash"""
        return pwd_context.hash(password)
    
    def create_user(self, user_data: UserCreate) -> User:
        """
        Create a new user.
        
        Args:
            user_data: User creation data
            
        Returns:
            The created user
            
        Raises:
            UserManagerError: If the user could not be created
        """
        try:
            # Generate ID
            user_id = str(uuid.uuid4())
            
            # Get current timestamp
            created_at = datetime.now()
            
            # Hash password
            password_hash = self._get_password_hash(user_data.password)
            
            # Insert user
            conn = self.db_manager._get_connection()
            conn.execute(
                """
                INSERT INTO users 
                (id, username, email, full_name, password_hash, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    user_data.username,
                    user_data.email,
                    user_data.full_name,
                    password_hash,
                    created_at.isoformat()
                )
            )
            
            conn.commit()
            logger.info(f"Created user {user_data.username}")
            
            # Return user without password hash
            return User(
                id=user_id,
                username=user_data.username,
                email=user_data.email,
                full_name=user_data.full_name,
                created_at=created_at
            )
            
        except sqlite3.IntegrityError as e:
            if "UNIQUE constraint failed: users.username" in str(e):
                error_msg = f"Username '{user_data.username}' already exists"
            elif "UNIQUE constraint failed: users.email" in str(e):
                error_msg = f"Email '{user_data.email}' already registered"
            else:
                error_msg = f"User creation failed: {str(e)}"
                
            logger.error(error_msg)
            raise UserManagerError(error_msg)
            
        except sqlite3.Error as e:
            error_msg = f"Database error creating user: {str(e)}"
            logger.error(error_msg)
            raise UserManagerError(error_msg)
            
        except Exception as e:
            error_msg = f"Failed to create user: {str(e)}"
            logger.error(error_msg)
            raise UserManagerError(error_msg)
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.
        
        Args:
            username: The username
            password: The password
            
        Returns:
            The authenticated user or None if authentication failed
        """
        user = self.get_user_by_username(username)
        if not user:
            return None
            
        # Check if user is UserInDB with password hash
        if not isinstance(user, UserInDB):
            logger.error(f"User {username} found but without password hash")
            return None
            
        if not self._verify_password(password, user.password_hash):
            return None
            
        if user.disabled:
            return None
            
        # Return user without password hash
        return User(
            id=user.id,
            username=user.username,
            email=user.email,
            full_name=user.full_name,
            disabled=user.disabled,
            created_at=user.created_at
        )
    
    def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """
        Get a user by username.
        
        Args:
            username: The username
            
        Returns:
            The user or None if not found
        """
        try:
            conn = self.db_manager._get_connection()
            
            cursor = conn.execute(
                """
                SELECT * FROM users WHERE username = ?
                """,
                (username,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            user_dict = dict(row)
            return UserInDB(
                id=user_dict["id"],
                username=user_dict["username"],
                email=user_dict.get("email"),
                full_name=user_dict.get("full_name"),
                disabled=bool(user_dict.get("disabled", 0)),
                created_at=datetime.fromisoformat(user_dict["created_at"]),
                password_hash=user_dict["password_hash"]
            )
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting user: {str(e)}")
            return None
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """
        Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            The user or None if not found
        """
        try:
            conn = self.db_manager._get_connection()
            
            cursor = conn.execute(
                """
                SELECT * FROM users WHERE id = ?
                """,
                (user_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            user_dict = dict(row)
            return User.from_db_row(user_dict)
            
        except sqlite3.Error as e:
            logger.error(f"Database error getting user: {str(e)}")
            return None
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """
        Create a JWT access token.
        
        Args:
            data: The data to encode in the token
            expires_delta: Optional token expiration override
            
        Returns:
            The JWT token string
        """
        to_encode = data.copy()
        
        # Set expiration
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        
        # Generate token
        token = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        
        # Store in sessions table (optional, for token revocation)
        try:
            conn = self.db_manager._get_connection()
            
            token_id = str(uuid.uuid4())
            conn.execute(
                """
                INSERT INTO user_sessions
                (token_id, user_id, expires_at, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    token_id,
                    data["sub"],
                    expire.isoformat(),
                    datetime.utcnow().isoformat()
                )
            )
            
            conn.commit()
        except sqlite3.Error as e:
            logger.warning(f"Failed to store token in sessions: {str(e)}")
        
        return token
    
    def get_token_data(self, token: str) -> Optional[TokenData]:
        """
        Decode and validate a JWT token.
        
        Args:
            token: The JWT token
            
        Returns:
            The token data or None if invalid
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            
            # Extract data
            user_id = payload.get("sub")
            username = payload.get("username")
            expires_at = payload.get("exp")
            
            if user_id is None or username is None:
                return None
                
            return TokenData(
                user_id=user_id,
                username=username,
                expires_at=expires_at
            )
            
        except jwt.PyJWTError as e:
            logger.warning(f"Token validation failed: {str(e)}")
            return None
    
    def revoke_all_user_tokens(self, user_id: str) -> int:
        """
        Revoke all tokens for a user (logout from all devices).
        
        Args:
            user_id: The user ID
            
        Returns:
            Number of tokens revoked
        """
        try:
            conn = self.db_manager._get_connection()
            
            cursor = conn.execute(
                """
                UPDATE user_sessions
                SET revoked = 1
                WHERE user_id = ? AND revoked = 0
                """,
                (user_id,)
            )
            
            conn.commit()
            return cursor.rowcount
            
        except sqlite3.Error as e:
            logger.error(f"Failed to revoke tokens: {str(e)}")
            return 0
