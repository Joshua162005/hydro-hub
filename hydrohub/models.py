"""
SQLAlchemy database models for HydroHub
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, CheckConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from hydrohub.db import Base
from hydrohub.utils import get_current_time

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), nullable=False, default='staff')
    created_at = Column(DateTime, default=func.now())
    last_login = Column(DateTime, nullable=True)
    
    # Relationships
    refill_transactions = relationship("RefillTransaction", back_populates="staff")
    expenses = relationship("Expense", back_populates="staff")
    ledger_entries = relationship("Ledger", back_populates="actor")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("role IN ('admin', 'staff', 'public')", name='check_user_role'),
    )
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class RefillTransaction(Base):
    __tablename__ = 'refill_transactions'
    
    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String(100), nullable=True)
    gallons_count = Column(Integer, nullable=False)
    price_per_gallon = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    payment_type = Column(String(20), nullable=False, default='Cash')
    staff_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    receipt_path = Column(String(255), nullable=True)
    
    # Relationships
    staff = relationship("User", back_populates="refill_transactions")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("gallons_count >= 0", name='check_positive_gallons'),
        CheckConstraint("price_per_gallon >= 0", name='check_positive_price'),
        CheckConstraint("total_amount >= 0", name='check_positive_total'),
        CheckConstraint("payment_type IN ('Cash', 'GCash', 'PayMaya', 'Bank Transfer', 'On-account')", 
                       name='check_payment_type'),
    )
    
    def __repr__(self):
        return f"<RefillTransaction(id={self.id}, gallons={self.gallons_count}, total={self.total_amount})>"

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False, default=0)
    unit_cost = Column(Float, nullable=False, default=0.0)
    location = Column(String(100), nullable=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Constraints
    __table_args__ = (
        CheckConstraint("quantity >= 0", name='check_positive_quantity'),
        CheckConstraint("unit_cost >= 0", name='check_positive_unit_cost'),
    )
    
    def __repr__(self):
        return f"<InventoryItem(name='{self.name}', quantity={self.quantity})>"

class Expense(Base):
    __tablename__ = 'expenses'
    
    id = Column(Integer, primary_key=True, index=True)
    category = Column(String(50), nullable=False)
    amount = Column(Float, nullable=False)
    vendor = Column(String(100), nullable=True)
    note = Column(Text, nullable=True)
    staff_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = Column(DateTime, default=func.now(), index=True)
    receipt_path = Column(String(255), nullable=True)
    
    # Relationships
    staff = relationship("User", back_populates="expenses")
    
    # Constraints
    __table_args__ = (
        CheckConstraint("amount >= 0", name='check_positive_amount'),
    )
    
    def __repr__(self):
        return f"<Expense(category='{self.category}', amount={self.amount})>"

class Ledger(Base):
    __tablename__ = 'ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(String(30), nullable=False, index=True)  # ISO format with timezone
    prev_hash = Column(String(64), nullable=False)
    data_hash = Column(String(64), nullable=False, unique=True)
    actor_id = Column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    action_type = Column(String(50), nullable=False)
    data_text = Column(Text, nullable=False)  # JSON string
    
    # Relationships
    actor = relationship("User", back_populates="ledger_entries")
    
    def __repr__(self):
        return f"<Ledger(id={self.id}, action_type='{self.action_type}', hash='{self.data_hash[:16]}...')>"
