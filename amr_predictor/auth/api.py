#!/usr/bin/env python3
"""
Authentication API endpoints.

This module provides FastAPI endpoints for authentication.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from amr_predictor.auth.user_manager import UserManager, JWT_ACCESS_TOKEN_EXPIRE_MINUTES
from amr_predictor.auth.models import User, UserCreate, Token, LoginRequest
from amr_predictor.auth.middleware import AuthDependencies

# Configure logging
logger = logging.getLogger("auth-api")

# Create router
router = APIRouter(tags=["authentication"])

def get_auth_router(db_path: str = None) -> APIRouter:
    """
    Get authentication router with configured dependencies.
    
    Args:
        db_path: Path to SQLite database
        
    Returns:
        Configured router
    """
    # Create dependencies
    auth_deps = AuthDependencies(db_path)
    user_manager = auth_deps.user_manager
    
    @router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
    async def register_user(user_data: UserCreate) -> User:
        """
        Register a new user.
        
        Args:
            user_data: User registration data
            
        Returns:
            The created user
            
        Raises:
            HTTPException: If registration fails
        """
        try:
            return user_manager.create_user(user_data)
        except Exception as e:
            logger.error(f"User registration failed: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
    
    @router.post("/token", response_model=Token)
    async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()) -> Token:
        """
        Get an access token using OAuth2 password flow.
        
        This endpoint is compatible with Swagger UI and standard OAuth2 clients.
        
        Args:
            form_data: OAuth2 form data
            
        Returns:
            Access token
            
        Raises:
            HTTPException: If authentication fails
        """
        user = user_manager.authenticate_user(form_data.username, form_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create token
        expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": user.id,
            "username": user.username
        }
        access_token = user_manager.create_access_token(token_data, expires_delta)
        
        # Get expiration timestamp
        expires_at = int((datetime.utcnow() + expires_delta).timestamp())
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_at=expires_at
        )
    
    @router.post("/login", response_model=Token)
    async def login(login_data: LoginRequest) -> Token:
        """
        Login with username and password.
        
        This is a more direct login endpoint that doesn't use OAuth2 form submission.
        
        Args:
            login_data: Login credentials
            
        Returns:
            Access token
            
        Raises:
            HTTPException: If authentication fails
        """
        user = user_manager.authenticate_user(login_data.username, login_data.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Create token
        expires_delta = timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        token_data = {
            "sub": user.id,
            "username": user.username
        }
        access_token = user_manager.create_access_token(token_data, expires_delta)
        
        # Get expiration timestamp
        expires_at = int((datetime.utcnow() + expires_delta).timestamp())
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_at=expires_at
        )
    
    @router.get("/me", response_model=User)
    async def get_current_user_info(current_user: User = Depends(auth_deps.get_current_user)) -> User:
        """
        Get current user information.
        
        Args:
            current_user: The authenticated user
            
        Returns:
            User information
        """
        return current_user
    
    @router.post("/logout")
    async def logout(current_user: User = Depends(auth_deps.get_current_user)) -> Dict[str, Any]:
        """
        Logout (revoke current user's tokens).
        
        Args:
            current_user: The authenticated user
            
        Returns:
            Status message
        """
        revoked = user_manager.revoke_all_user_tokens(current_user.id)
        return {"message": "Successfully logged out", "tokens_revoked": revoked}
    
    return router
