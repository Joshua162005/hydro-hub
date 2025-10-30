"""
Authentication system with bcrypt password hashing
"""

import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from hydrohub.db import get_session
from hydrohub.models import User
from hydrohub.utils import get_current_time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Password hashing context - Complete bcrypt compatibility fix
import warnings
import os
import sys

# Suppress all bcrypt-related warnings
warnings.filterwarnings("ignore", category=UserWarning, module="passlib")
warnings.filterwarnings("ignore", message=".*bcrypt.*")
warnings.filterwarnings("ignore", message=".*__about__.*")

# Set environment variable to disable passlib bcrypt version checking
os.environ['PASSLIB_BCRYPT_BACKEND'] = 'bcrypt'

# Direct bcrypt implementation to avoid passlib issues
import bcrypt as _bcrypt

class DirectBcryptContext:
    """Direct bcrypt implementation bypassing passlib version issues"""
    
    def hash(self, password):
        """Hash password using bcrypt directly"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        # Ensure password length is within bcrypt limits
        if len(password) > 72:
            password = password[:72]
        salt = _bcrypt.gensalt()
        return _bcrypt.hashpw(password, salt).decode('utf-8')
    
    def verify(self, password, hashed):
        """Verify password against hash using bcrypt directly"""
        if isinstance(password, str):
            password = password.encode('utf-8')
        if isinstance(hashed, str):
            hashed = hashed.encode('utf-8')
        # Ensure password length is within bcrypt limits
        if len(password) > 72:
            password = password[:72]
        try:
            return _bcrypt.checkpw(password, hashed)
        except Exception:
            return False

# Use direct bcrypt implementation
pwd_context = DirectBcryptContext()

# Session timeout (hours)
SESSION_TIMEOUT_HOURS = 8

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    # Ensure password is not too long for bcrypt (72 bytes max)
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_user(username: str, password: str, role: str = 'staff') -> User:
    """Create a new user"""
    session = get_session()
    try:
        # Check if user already exists
        existing_user = session.query(User).filter(User.username == username).first()
        if existing_user:
            raise ValueError(f"User '{username}' already exists")
        
        # Validate role
        if role not in ['admin', 'staff', 'public']:
            raise ValueError(f"Invalid role: {role}")
        
        # Create new user
        hashed_password = hash_password(password)
        user = User(
            username=username,
            password_hash=hashed_password,
            role=role,
            created_at=get_current_time()
        )
        
        session.add(user)
        session.commit()
        session.refresh(user)
        
        return user
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def authenticate_user(username: str, password: str) -> User:
    """Authenticate a user with username and password"""
    session = get_session()
    try:
        user = session.query(User).filter(User.username == username).first()
        
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        # Update last login
        user.last_login = get_current_time()
        session.commit()
        session.refresh(user)
        
        return user
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_user_by_id(user_id: int) -> User:
    """Get user by ID"""
    session = get_session()
    try:
        return session.query(User).filter(User.id == user_id).first()
    finally:
        session.close()

def get_all_users() -> list:
    """Get all users (admin only)"""
    session = get_session()
    try:
        return session.query(User).all()
    finally:
        session.close()

def update_user_password(user_id: int, new_password: str) -> bool:
    """Update user password"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        user.password_hash = hash_password(new_password)
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def delete_user(user_id: int) -> bool:
    """Delete a user (admin only)"""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        # Don't delete the last admin
        if user.role == 'admin':
            admin_count = session.query(User).filter(User.role == 'admin').count()
            if admin_count <= 1:
                raise ValueError("Cannot delete the last admin user")
        
        session.delete(user)
        session.commit()
        return True
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def create_default_admin():
    """Create default admin user if none exists"""
    session = get_session()
    try:
        # Check if any admin exists
        admin_exists = session.query(User).filter(User.role == 'admin').first()
        if admin_exists:
            return
        
        # Create default admin
        admin_password = os.getenv('ADMIN_PASSWORD', 'admin123')
        admin = User(
            username='admin',
            password_hash=hash_password(admin_password),
            role='admin',
            created_at=get_current_time()
        )
        
        session.add(admin)
        session.commit()
        
        print(f"Default admin created with password: {admin_password}")
        print("Please change the admin password immediately!")
        
    except Exception as e:
        session.rollback()
        print(f"Error creating default admin: {e}")
    finally:
        session.close()

def is_session_valid(login_time: datetime) -> bool:
    """Check if session is still valid"""
    if not login_time:
        return False
    
    current_time = get_current_time()
    # Handle timezone-naive datetime
    if login_time.tzinfo is None:
        login_time = login_time.replace(tzinfo=current_time.tzinfo)
    
    time_diff = current_time - login_time
    return time_diff < timedelta(hours=SESSION_TIMEOUT_HOURS)

def require_role(user_role: str, required_roles: list) -> bool:
    """Check if user has required role"""
    return user_role in required_roles

def get_user_permissions(role: str) -> dict:
    """Get user permissions based on role"""
    permissions = {
        'admin': {
            'can_manage_users': True,
            'can_view_ledger': True,
            'can_export_data': True,
            'can_manage_inventory': True,
            'can_record_transactions': True,
            'can_manage_expenses': True,
            'can_view_reports': True,
            'can_manage_settings': True
        },
        'staff': {
            'can_manage_users': False,
            'can_view_ledger': False,
            'can_export_data': False,
            'can_manage_inventory': True,
            'can_record_transactions': True,
            'can_manage_expenses': True,
            'can_view_reports': True,
            'can_manage_settings': False
        },
        'public': {
            'can_manage_users': False,
            'can_view_ledger': False,
            'can_export_data': False,
            'can_manage_inventory': False,
            'can_record_transactions': False,
            'can_manage_expenses': False,
            'can_view_reports': True,
            'can_manage_settings': False
        }
    }
    
    return permissions.get(role, permissions['public'])
