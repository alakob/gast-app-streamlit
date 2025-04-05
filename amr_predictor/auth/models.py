#!/usr/bin/env python3
"""
User authentication models.

This module defines models for user authentication and session management.
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, EmailStr

class User(BaseModel):
    """User model for authentication"""
    id: str
    username: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: bool = False
    created_at: datetime
    
    @classmethod
    def from_db_row(cls, row: Dict[str, Any]) -> "User":
        """Create a User instance from a database row"""
        return cls(
            id=row["id"],
            username=row["username"],
            email=row.get("email"),
            full_name=row.get("full_name"),
            disabled=bool(row.get("disabled", 0)),
            created_at=datetime.fromisoformat(row["created_at"])
        )

class UserInDB(User):
    """User model with password hash"""
    password_hash: str

class Token(BaseModel):
    """Token model for authentication responses"""
    access_token: str
    token_type: str = "bearer"
    expires_at: int  # Unix timestamp
    
class TokenData(BaseModel):
    """Token data for validation"""
    user_id: str
    username: str
    expires_at: int

class UserCreate(BaseModel):
    """Model for user registration"""
    username: str
    password: str
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None

class LoginRequest(BaseModel):
    """Model for login requests"""
    username: str
    password: str
