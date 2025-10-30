"""
Data validation functions for HydroHub
"""

import re
from typing import Any, List

class ValidationError(Exception):
    """Custom validation error"""
    pass

def required_non_empty_str(field_name: str, value: Any) -> str:
    """Validate that a field is a non-empty string"""
    if not value or not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{field_name} is required and cannot be empty")
    return value.strip()

def validate_positive_int(field_name: str, value: Any, min_value: int = 0) -> int:
    """Validate that a field is a positive integer"""
    try:
        int_value = int(value)
        if int_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        return int_value
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid integer")

def validate_positive_decimal(field_name: str, value: Any, min_value: float = 0.0) -> float:
    """Validate that a field is a positive decimal"""
    try:
        float_value = float(value)
        if float_value < min_value:
            raise ValidationError(f"{field_name} must be at least {min_value}")
        return float_value
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a valid number")

def validate_payment_type(payment_type: str) -> str:
    """Validate payment type"""
    allowed_types = ['Cash', 'GCash', 'PayMaya', 'Bank Transfer', 'On-account']
    if payment_type not in allowed_types:
        raise ValidationError(f"Payment type must be one of: {', '.join(allowed_types)}")
    return payment_type

def validate_user_role(role: str) -> str:
    """Validate user role"""
    allowed_roles = ['admin', 'staff', 'public']
    if role not in allowed_roles:
        raise ValidationError(f"Role must be one of: {', '.join(allowed_roles)}")
    return role

def validate_username(username: str) -> str:
    """Validate username format"""
    username = required_non_empty_str("Username", username)
    
    # Check length
    if len(username) < 3:
        raise ValidationError("Username must be at least 3 characters long")
    if len(username) > 50:
        raise ValidationError("Username must be no more than 50 characters long")
    
    # Check format (alphanumeric and underscore only)
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        raise ValidationError("Username can only contain letters, numbers, and underscores")
    
    return username

def validate_password(password: str) -> str:
    """Validate password strength"""
    if not password:
        raise ValidationError("Password is required")
    
    if len(password) < 6:
        raise ValidationError("Password must be at least 6 characters long")
    
    if len(password) > 128:
        raise ValidationError("Password must be no more than 128 characters long")
    
    return password

def validate_customer_name(name: str) -> str:
    """Validate customer name (optional field)"""
    if not name:
        return ""
    
    name = name.strip()
    if len(name) > 100:
        raise ValidationError("Customer name must be no more than 100 characters long")
    
    return name

def validate_expense_category(category: str) -> str:
    """Validate expense category"""
    category = required_non_empty_str("Category", category)
    
    # Water refill station specific categories
    valid_categories = [
        'Water Supply', 'Filters', 'Containers', 'Equipment Maintenance',
        'Transportation', 'Supplies', 'Other'
    ]
    
    if category not in valid_categories:
        raise ValidationError(f"Category must be one of: {', '.join(valid_categories)}")
    
    if len(category) > 50:
        raise ValidationError("Category must be no more than 50 characters long")
    
    return category

def validate_inventory_category(category: str) -> str:
    """Validate inventory category"""
    category = required_non_empty_str("Category", category)
    
    # Common inventory categories
    suggested_categories = [
        'Water', 'Containers', 'Equipment', 'Supplies', 'Chemicals', 'Other'
    ]
    
    if len(category) > 50:
        raise ValidationError("Category must be no more than 50 characters long")
    
    return category

def validate_file_upload(file_obj, allowed_extensions: List[str] = None, max_size_mb: int = 5):
    """Validate uploaded file"""
    if not file_obj:
        return None
    
    # Check file size
    if hasattr(file_obj, 'size') and file_obj.size > max_size_mb * 1024 * 1024:
        raise ValidationError(f"File size must be less than {max_size_mb}MB")
    
    # Check file extension
    if allowed_extensions:
        file_extension = file_obj.name.split('.')[-1].lower() if '.' in file_obj.name else ''
        if file_extension not in [ext.lower() for ext in allowed_extensions]:
            raise ValidationError(f"File type must be one of: {', '.join(allowed_extensions)}")
    
    return file_obj

def validate_refill_transaction(data: dict) -> dict:
    """Validate refill transaction data"""
    validated = {}
    
    # Customer name (optional)
    validated['customer_name'] = validate_customer_name(data.get('customer_name', ''))
    
    # Gallons count (required, positive integer)
    validated['gallons_count'] = validate_positive_int('Gallons count', data.get('gallons_count'), min_value=1)
    
    # Price per gallon (required, positive decimal)
    validated['price_per_gallon'] = validate_positive_decimal('Price per gallon', data.get('price_per_gallon'), min_value=0.01)
    
    # Payment type (required)
    validated['payment_type'] = validate_payment_type(data.get('payment_type', 'Cash'))
    
    # Calculate total amount
    validated['total_amount'] = validated['gallons_count'] * validated['price_per_gallon']
    
    # Staff ID (should be provided by session)
    if 'staff_id' in data:
        validated['staff_id'] = validate_positive_int('Staff ID', data['staff_id'], min_value=1)
    
    return validated

def validate_expense_data(data: dict) -> dict:
    """Validate expense data"""
    validated = {}
    
    # Category (required)
    validated['category'] = validate_expense_category(data.get('category'))
    
    # Amount (required, positive decimal)
    validated['amount'] = validate_positive_decimal('Amount', data.get('amount'), min_value=0.01)
    
    # Vendor (optional)
    vendor = data.get('vendor', '').strip()
    if vendor and len(vendor) > 100:
        raise ValidationError("Vendor name must be no more than 100 characters long")
    validated['vendor'] = vendor
    
    # Note (optional)
    note = data.get('note', '').strip()
    if note and len(note) > 500:
        raise ValidationError("Note must be no more than 500 characters long")
    validated['note'] = note
    
    # Staff ID (should be provided by session)
    if 'staff_id' in data:
        validated['staff_id'] = validate_positive_int('Staff ID', data['staff_id'], min_value=1)
    
    return validated

def validate_inventory_item(data: dict) -> dict:
    """Validate inventory item data"""
    validated = {}
    
    # Name (required)
    validated['name'] = required_non_empty_str('Item name', data.get('name'))
    if len(validated['name']) > 100:
        raise ValidationError("Item name must be no more than 100 characters long")
    
    # Category (required)
    validated['category'] = validate_inventory_category(data.get('category'))
    
    # Quantity (required, non-negative integer)
    validated['quantity'] = validate_positive_int('Quantity', data.get('quantity'), min_value=0)
    
    # Unit cost (required, non-negative decimal)
    validated['unit_cost'] = validate_positive_decimal('Unit cost', data.get('unit_cost'), min_value=0.0)
    
    # Location (optional)
    location = data.get('location', '').strip()
    if location and len(location) > 100:
        raise ValidationError("Location must be no more than 100 characters long")
    validated['location'] = location
    
    return validated

def validate_user_data(data: dict) -> dict:
    """Validate user data"""
    validated = {}
    
    # Username (required)
    validated['username'] = validate_username(data.get('username'))
    
    # Password (required for new users)
    if 'password' in data:
        validated['password'] = validate_password(data.get('password'))
    
    # Role (required)
    validated['role'] = validate_user_role(data.get('role', 'staff'))
    
    return validated
