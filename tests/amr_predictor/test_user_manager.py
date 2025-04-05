"""Tests for the User Manager and Authentication."""

import pytest
import jwt
import time
from datetime import datetime, timedelta

from amr_predictor.auth.user_manager import UserManager, UserManagerError
from amr_predictor.auth.models import UserCreate, User


def test_create_user(user_manager):
    """Test creating a new user."""
    # Create user data
    user_data = UserCreate(
        username="newuser",
        password="password123",
        email="new@example.com"
    )
    
    # Create the user
    user = user_manager.create_user(user_data)
    
    # Verify user was created
    assert user is not None
    assert user.username == "newuser"
    assert user.email == "new@example.com"
    
    # Password should not be returned
    assert not hasattr(user, "password")
    assert not hasattr(user, "password_hash")
    
    # Verify user is in database
    retrieved_user = user_manager.get_user_by_username("newuser")
    assert retrieved_user is not None
    assert retrieved_user.username == "newuser"


def test_create_duplicate_user(user_manager, test_user):
    """Test creating a user with a duplicate username."""
    # Create user data with same username
    user_data = UserCreate(
        username=test_user.username,
        password="password123",
        email="another@example.com"
    )
    
    # Try to create the user, should raise error
    with pytest.raises(UserManagerError) as excinfo:
        user_manager.create_user(user_data)
    
    # Verify error message
    assert "already exists" in str(excinfo.value)


def test_authenticate_user_success(user_manager, test_user):
    """Test successful user authentication."""
    # Authenticate with correct password
    authenticated_user = user_manager.authenticate_user(
        username=test_user.username,
        password="testpassword"  # This is the password we set in the fixture
    )
    
    # Verify authentication succeeded
    assert authenticated_user is not None
    assert authenticated_user.username == test_user.username


def test_authenticate_user_wrong_password(user_manager, test_user):
    """Test authentication with wrong password."""
    # Try to authenticate with wrong password
    authenticated_user = user_manager.authenticate_user(
        username=test_user.username,
        password="wrongpassword"
    )
    
    # Verify authentication failed
    assert authenticated_user is None


def test_authenticate_nonexistent_user(user_manager):
    """Test authentication with nonexistent username."""
    # Try to authenticate nonexistent user
    authenticated_user = user_manager.authenticate_user(
        username="nonexistentuser",
        password="anypassword"
    )
    
    # Verify authentication failed
    assert authenticated_user is None


def test_create_access_token(user_manager, test_user):
    """Test creating an access token."""
    # Create access token
    access_token = user_manager.create_access_token(
        data={"sub": test_user.username}
    )
    
    # Verify token is created
    assert access_token is not None
    
    # Decode token to verify contents
    token_data = jwt.decode(
        access_token,
        user_manager.jwt_secret_key,
        algorithms=[user_manager.algorithm]
    )
    
    # Verify token contains expected data
    assert token_data["sub"] == test_user.username
    
    # Verify expiration is in the future
    assert "exp" in token_data
    expiration = datetime.fromtimestamp(token_data["exp"])
    assert expiration > datetime.now()


def test_get_current_user(user_manager, test_user):
    """Test getting current user from token."""
    # Create access token
    access_token = user_manager.create_access_token(
        data={"sub": test_user.username}
    )
    
    # Get current user from token
    current_user = user_manager.get_current_user(access_token)
    
    # Verify correct user was returned
    assert current_user is not None
    assert current_user.username == test_user.username


def test_get_current_user_invalid_token(user_manager):
    """Test getting current user with invalid token."""
    # Try to get user with invalid token
    with pytest.raises(UserManagerError):
        user_manager.get_current_user("invalid-token")


def test_get_current_user_expired_token(user_manager, test_user):
    """Test getting current user with expired token."""
    # Create expired token
    expired_token = user_manager.create_access_token(
        data={"sub": test_user.username},
        expires_delta=timedelta(seconds=-1)  # Expired 1 second ago
    )
    
    # Wait a moment to ensure token is expired
    time.sleep(0.1)
    
    # Try to get user with expired token
    with pytest.raises(UserManagerError) as excinfo:
        user_manager.get_current_user(expired_token)
    
    # Verify error message
    assert "expired" in str(excinfo.value).lower()


def test_get_current_user_nonexistent_user(user_manager):
    """Test getting current user with token for nonexistent user."""
    # Create token for nonexistent user
    token = user_manager.create_access_token(
        data={"sub": "nonexistentuser"}
    )
    
    # Try to get user
    with pytest.raises(UserManagerError) as excinfo:
        user_manager.get_current_user(token)
    
    # Verify error message
    assert "not found" in str(excinfo.value).lower()


def test_update_user(user_manager, test_user):
    """Test updating a user."""
    # Update user email
    updated_user = user_manager.update_user(
        test_user.username,
        {"email": "updated@example.com"}
    )
    
    # Verify update was successful
    assert updated_user is not None
    assert updated_user.email == "updated@example.com"
    
    # Retrieve user to confirm update
    retrieved_user = user_manager.get_user_by_username(test_user.username)
    assert retrieved_user.email == "updated@example.com"


def test_update_nonexistent_user(user_manager):
    """Test updating a nonexistent user."""
    # Try to update nonexistent user
    with pytest.raises(UserManagerError) as excinfo:
        user_manager.update_user(
            "nonexistentuser",
            {"email": "any@example.com"}
        )
    
    # Verify error message
    assert "not found" in str(excinfo.value).lower()


def test_change_password(user_manager, test_user):
    """Test changing a user's password."""
    # Change password
    user_manager.change_password(
        test_user.username,
        new_password="newpassword123"
    )
    
    # Try to authenticate with new password
    authenticated_user = user_manager.authenticate_user(
        username=test_user.username,
        password="newpassword123"
    )
    
    # Verify authentication succeeds with new password
    assert authenticated_user is not None
    assert authenticated_user.username == test_user.username
    
    # Try to authenticate with old password (should fail)
    authenticated_user = user_manager.authenticate_user(
        username=test_user.username,
        password="testpassword"
    )
    
    # Verify authentication fails with old password
    assert authenticated_user is None
