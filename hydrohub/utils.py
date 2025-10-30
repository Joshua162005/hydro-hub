"""
Utility functions for HydroHub application
"""

import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration constants
TIMEZONE = os.getenv('TIMEZONE', 'Asia/Manila')
CURRENCY_SYMBOL = os.getenv('CURRENCY_SYMBOL', '₱')
BUSINESS_NAME = os.getenv('BUSINESS_NAME', 'HydroHub Cantilan')
BUSINESS_LOCATION = os.getenv('BUSINESS_LOCATION', 'Cantilan, Surigao del Sur, Philippines')

def get_manila_timezone():
    """Get Manila timezone object"""
    return pytz.timezone(TIMEZONE)

def get_current_time():
    """Get current time in Manila timezone"""
    manila_tz = get_manila_timezone()
    return datetime.now(manila_tz)

def get_current_date():
    """Get current date in Manila timezone"""
    return get_current_time().date()

def format_money(amount):
    """Format amount as Philippine peso"""
    if amount is None:
        return f"{CURRENCY_SYMBOL}0.00"
    return f"{CURRENCY_SYMBOL}{amount:,.2f}"

def format_datetime(dt):
    """Format datetime for display"""
    if isinstance(dt, str):
        # Parse ISO string
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    # Convert to Manila timezone if needed
    manila_tz = get_manila_timezone()
    if dt.tzinfo is None:
        dt = pytz.utc.localize(dt)
    
    dt_manila = dt.astimezone(manila_tz)
    return dt_manila.strftime('%Y-%m-%d %I:%M %p')

def format_date(date_obj):
    """Format date for display"""
    if isinstance(date_obj, str):
        date_obj = datetime.fromisoformat(date_obj).date()
    return date_obj.strftime('%Y-%m-%d')

def get_business_config():
    """Get business configuration"""
    return {
        'name': BUSINESS_NAME,
        'location': BUSINESS_LOCATION,
        'currency_symbol': CURRENCY_SYMBOL,
        'timezone': TIMEZONE,
        'default_price_per_gallon': float(os.getenv('DEFAULT_PRICE_PER_GALLON', '25.00'))
    }

def validate_positive_number(value, field_name):
    """Validate that a number is positive"""
    if value is None or value <= 0:
        raise ValueError(f"{field_name} must be a positive number")
    return True

def safe_float(value, default=0.0):
    """Safely convert value to float"""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default

def safe_int(value, default=0):
    """Safely convert value to int"""
    try:
        return int(value) if value is not None else default
    except (ValueError, TypeError):
        return default
