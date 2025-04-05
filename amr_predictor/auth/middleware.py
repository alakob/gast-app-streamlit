#!/usr/bin/env python3
"""
Authentication middleware for FastAPI.

This module provides middleware for handling authentication in FastAPI applications.
"""
import logging
from typing import Optional, Callable
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, HTTPBearer, HTTPAuthorizationCredentials

from amr_predictor.auth.user_manager import UserManager
from amr_predictor.auth.models import User, TokenData

# Configure logging
logger = logging.getLogger("auth-middleware")

# OAuth2 for Swagger UI
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# Bearer for direct token validation
bearer_scheme = HTTPBearer(auto_error=False)

class AuthDependencies:
    """
    Authentication dependencies for FastAPI.
    
    This class provides dependencies for authenticating users in FastAPI.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize authentication dependencies.
        
        Args:
            db_path: Path to the SQLite database
        """
        self.user_manager = UserManager(db_path=db_path)
    
    async def get_token(self, token: str = Depends(oauth2_scheme), 
                      credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> Optional[str]:
        """
        Get the token from OAuth2 or Bearer.
        
        This dependency tries both OAuth2 and Bearer authentication schemes
        to support different client types.
        
        Args:
            token: Token from OAuth2
            credentials: Credentials from Bearer
            
        Returns:
            The token or None if not provided
        """
        if token:
            return token
        elif credentials:
            return credentials.credentials
        else:
            return None
    
    async def get_current_user(self, token: str = Depends(get_token)) -> User:
        """
        Get the current authenticated user.
        
        Args:
            token: The authentication token
            
        Returns:
            The authenticated user
            
        Raises:
            HTTPException: If authentication fails
        """
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        token_data = self.user_manager.get_token_data(token)
        if not token_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        user = self.user_manager.get_user_by_id(token_data.user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        if user.disabled:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        return user
    
    async def get_current_user_optional(self, token: Optional[str] = Depends(get_token)) -> Optional[User]:
        """
        Get the current user if authenticated, otherwise None.
        
        This is useful for endpoints that work with or without authentication.
        
        Args:
            token: The authentication token
            
        Returns:
            The authenticated user or None
        """
        if not token:
            return None
            
        token_data = self.user_manager.get_token_data(token)
        if not token_data:
            return None
            
        user = self.user_manager.get_user_by_id(token_data.user_id)
        if not user or user.disabled:
            return None
            
        return user
