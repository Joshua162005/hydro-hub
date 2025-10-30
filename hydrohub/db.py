"""
Database configuration and session management
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///hydrohub.db')

# Create engine
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {}
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()

def get_session():
    """Get database session"""
    session = SessionLocal()
    try:
        return session
    except Exception:
        session.close()
        raise

def init_db():
    """Initialize database tables"""
    from hydrohub.models import User, RefillTransaction, InventoryItem, Expense, Ledger
    from hydrohub.auth import create_default_admin
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create default admin user
    create_default_admin()
    
    # Create default inventory items
    create_default_inventory()

def create_default_inventory():
    """Create default inventory items"""
    session = get_session()
    try:
        from hydrohub.models import InventoryItem
        
        # Check if inventory already exists
        existing = session.query(InventoryItem).first()
        if existing:
            return
        
        # Create default inventory items
        default_items = [
            {
                'name': 'Full Gallons',
                'category': 'Water',
                'quantity': 100,
                'unit_cost': 20.00,
                'location': 'Main Storage'
            },
            {
                'name': 'Empty Gallons',
                'category': 'Containers',
                'quantity': 50,
                'unit_cost': 0.00,
                'location': 'Main Storage'
            },
            {
                'name': 'Water Filters',
                'category': 'Equipment',
                'quantity': 10,
                'unit_cost': 150.00,
                'location': 'Equipment Room'
            },
            {
                'name': 'Bottle Caps',
                'category': 'Supplies',
                'quantity': 500,
                'unit_cost': 0.50,
                'location': 'Supply Cabinet'
            }
        ]
        
        for item_data in default_items:
            item = InventoryItem(**item_data)
            session.add(item)
        
        session.commit()
        
    except Exception as e:
        session.rollback()
        print(f"Error creating default inventory: {e}")
    finally:
        session.close()

def get_db_stats():
    """Get database statistics"""
    session = get_session()
    try:
        from hydrohub.models import User, RefillTransaction, InventoryItem, Expense, Ledger
        
        stats = {
            'users': session.query(User).count(),
            'transactions': session.query(RefillTransaction).count(),
            'inventory_items': session.query(InventoryItem).count(),
            'expenses': session.query(Expense).count(),
            'ledger_entries': session.query(Ledger).count()
        }
        
        return stats
        
    except Exception as e:
        print(f"Error getting database stats: {e}")
        return {}
    finally:
        session.close()
