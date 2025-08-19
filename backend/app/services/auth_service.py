"""
Authentication service for API key management and JWT tokens
"""

import secrets
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from jose import JWTError, jwt
from fastapi import HTTPException, status

from app.config import settings
from app.models.user import User
from app.models.api_key import APIKey

logger = logging.getLogger(__name__)


class AuthService:
    """Service for handling authentication and authorization"""
    
    def __init__(self):
        self.secret_key = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.access_token_expire_minutes = settings.jwt_expiration_minutes
    
    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT access token"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire_minutes)
        
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
        return encoded_jwt
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode a JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
    
    def authenticate_user(self, db: Session, email: str, password: str) -> Optional[User]:
        """Authenticate a user with email and password"""
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return None
        if not user.verify_password(password):
            return None
        return user
    
    def create_user(self, db: Session, email: str, username: str, password: str, full_name: str = None) -> User:
        """Create a new user"""
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email or username already exists"
            )
        
        # Create new user
        user = User(
            email=email,
            username=username,
            full_name=full_name,
            subscription_tier="free"
        )
        user.set_password(password)
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        logger.info(f"Created new user: {user.email}")
        return user
    
    def generate_api_key(self, db: Session, user_id: int, key_name: str, permissions: list = None) -> str:
        """Generate a new API key for a user"""
        # Generate the key
        api_key = APIKey.generate_key()
        
        # Create API key record
        key_record = APIKey(
            user_id=user_id,
            key_name=key_name,
            permissions=permissions or ["read", "write"]
        )
        key_record.set_key(api_key)
        
        db.add(key_record)
        db.commit()
        
        logger.info(f"Generated API key for user {user_id}: {key_name}")
        return api_key
    
    def verify_api_key(self, db: Session, api_key: str) -> Optional[APIKey]:
        """Verify an API key and return the key record"""
        if not api_key:
            return None
        
        # Get the key prefix for faster lookup
        key_prefix = APIKey.get_key_prefix(api_key)
        
        # Find the key record
        key_record = db.query(APIKey).filter(
            APIKey.key_prefix == key_prefix,
            APIKey.is_active == True
        ).first()
        
        if not key_record:
            return None
        
        # Verify the key
        if not key_record.verify_key(api_key):
            return None
        
        # Check if key is expired
        if key_record.is_expired():
            return None
        
        # Update last used timestamp
        key_record.update_last_used()
        db.commit()
        
        return key_record
    
    def get_user_by_api_key(self, db: Session, api_key: str) -> Optional[User]:
        """Get user by API key"""
        key_record = self.verify_api_key(db, api_key)
        if not key_record:
            return None
        
        return db.query(User).filter(User.id == key_record.user_id).first()
    
    def revoke_api_key(self, db: Session, user_id: int, key_id: int) -> bool:
        """Revoke an API key"""
        key_record = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not key_record:
            return False
        
        key_record.is_active = False
        db.commit()
        
        logger.info(f"Revoked API key {key_id} for user {user_id}")
        return True
    
    def rotate_api_key(self, db: Session, user_id: int, key_id: int) -> Optional[str]:
        """Rotate an API key and return the new key"""
        key_record = db.query(APIKey).filter(
            APIKey.id == key_id,
            APIKey.user_id == user_id
        ).first()
        
        if not key_record:
            return None
        
        # Generate new key
        new_key = key_record.rotate_key()
        db.commit()
        
        logger.info(f"Rotated API key {key_id} for user {user_id}")
        return new_key
    
    def get_user_api_keys(self, db: Session, user_id: int) -> list:
        """Get all API keys for a user"""
        keys = db.query(APIKey).filter(
            APIKey.user_id == user_id
        ).all()
        
        return [
            {
                "id": key.id,
                "name": key.key_name,
                "prefix": key.key_prefix,
                "is_active": key.is_active,
                "permissions": key.get_permissions(),
                "created_at": key.created_at,
                "last_used_at": key.last_used_at,
                "expires_at": key.expires_at
            }
            for key in keys
        ]
    
    def check_permission(self, api_key: APIKey, permission: str) -> bool:
        """Check if an API key has a specific permission"""
        return api_key.has_permission(permission)
    
    def check_ip_restriction(self, api_key: APIKey, client_ip: str) -> bool:
        """Check if a client IP is allowed for an API key"""
        return api_key.is_ip_allowed(client_ip)
    
    def create_password_reset_token(self, user_id: int) -> str:
        """Create a password reset token"""
        data = {"sub": str(user_id), "type": "password_reset"}
        return self.create_access_token(data, timedelta(hours=1))
    
    def verify_password_reset_token(self, token: str) -> Optional[int]:
        """Verify a password reset token and return user ID"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            if payload.get("type") != "password_reset":
                return None
            return int(payload.get("sub"))
        except JWTError:
            return None
    
    def reset_password(self, db: Session, user_id: int, new_password: str) -> bool:
        """Reset a user's password"""
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.set_password(new_password)
        db.commit()
        
        logger.info(f"Reset password for user {user_id}")
        return True


# Global auth service instance
auth_service = AuthService()
