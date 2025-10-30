"""
File storage system for receipts and documents
"""

import os
import hashlib
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path
from hydrohub.validations import validate_file_upload

# Configuration
RECEIPTS_DIR = os.getenv('RECEIPTS_DIR', 'data/receipts')
MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', '5'))
ALLOWED_EXTENSIONS = ['pdf', 'jpg', 'jpeg', 'png']

def ensure_receipts_directory():
    """Ensure receipts directory exists"""
    Path(RECEIPTS_DIR).mkdir(parents=True, exist_ok=True)

def generate_file_hash(file_content: bytes) -> str:
    """Generate SHA-256 hash of file content"""
    return hashlib.sha256(file_content).hexdigest()

def generate_filename(original_filename: str, file_hash: str) -> str:
    """Generate unique filename based on hash and timestamp"""
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    extension = original_filename.split('.')[-1].lower() if '.' in original_filename else 'bin'
    return f"{timestamp}_{file_hash[:16]}.{extension}"

def save_receipt(file_obj) -> Tuple[str, str]:
    """
    Save uploaded receipt file
    
    Args:
        file_obj: Streamlit uploaded file object
    
    Returns:
        Tuple of (file_path, file_hash)
    """
    # Validate file
    validate_file_upload(file_obj, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB)
    
    # Ensure directory exists
    ensure_receipts_directory()
    
    # Read file content
    file_content = file_obj.read()
    file_obj.seek(0)  # Reset file pointer
    
    # Generate hash
    file_hash = generate_file_hash(file_content)
    
    # Generate filename
    filename = generate_filename(file_obj.name, file_hash)
    file_path = os.path.join(RECEIPTS_DIR, filename)
    
    # Check if file already exists (same hash)
    if os.path.exists(file_path):
        return file_path, file_hash
    
    # Save file
    with open(file_path, 'wb') as f:
        f.write(file_content)
    
    return file_path, file_hash

def get_file_info(file_path: str) -> Optional[dict]:
    """Get information about a stored file"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    try:
        stat = os.stat(file_path)
        return {
            'path': file_path,
            'filename': os.path.basename(file_path),
            'size': stat.st_size,
            'created': datetime.fromtimestamp(stat.st_ctime),
            'modified': datetime.fromtimestamp(stat.st_mtime),
            'exists': True
        }
    except Exception:
        return None

def delete_file(file_path: str) -> bool:
    """Delete a stored file"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception:
        return False

def get_file_url(file_path: str) -> Optional[str]:
    """Get URL for accessing file (for future web serving)"""
    if not file_path or not os.path.exists(file_path):
        return None
    
    # For now, return relative path
    # In production, this could return a signed URL for cloud storage
    return file_path.replace('\\', '/')

def verify_file_integrity(file_path: str, expected_hash: str) -> bool:
    """Verify file integrity using hash"""
    try:
        if not os.path.exists(file_path):
            return False
        
        with open(file_path, 'rb') as f:
            content = f.read()
        
        actual_hash = generate_file_hash(content)
        return actual_hash == expected_hash
        
    except Exception:
        return False

def cleanup_orphaned_files():
    """Clean up files that are not referenced in database"""
    # This would require database access to check which files are referenced
    # Implementation would depend on specific cleanup policy
    pass

def get_storage_stats() -> dict:
    """Get storage statistics"""
    try:
        ensure_receipts_directory()
        
        total_files = 0
        total_size = 0
        
        for root, dirs, files in os.walk(RECEIPTS_DIR):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += size
                except Exception:
                    continue
        
        return {
            'total_files': total_files,
            'total_size_bytes': total_size,
            'total_size_mb': round(total_size / (1024 * 1024), 2),
            'receipts_directory': RECEIPTS_DIR
        }
        
    except Exception as e:
        return {
            'error': str(e),
            'total_files': 0,
            'total_size_bytes': 0,
            'total_size_mb': 0,
            'receipts_directory': RECEIPTS_DIR
        }
