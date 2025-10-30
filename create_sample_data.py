#!/usr/bin/env python3
"""
Simple sample data creator for HydroHub
"""

from datetime import datetime, timedelta
import random
from hydrohub.db import get_session
from hydrohub.models import User, RefillTransaction, Expense
from hydrohub.auth import create_user

def create_sample_data():
    """Create sample data for demonstration"""
    print("Creating sample data...")
    
    session = get_session()
    try:
        # Create sample staff users
        try:
            staff1 = create_user("juan_staff", "staff123", "staff")
            print(f"✅ Created user: {staff1.username}")
        except:
            print("⚠️ User juan_staff already exists")
        
        try:
            staff2 = create_user("maria_staff", "staff123", "staff")
            print(f"✅ Created user: {staff2.username}")
        except:
            print("⚠️ User maria_staff already exists")
        
        # Get all staff for transactions
        staff_users = session.query(User).filter(User.role.in_(['admin', 'staff'])).all()
        
        if not staff_users:
            print("❌ No staff users found")
            return
        
        # Create sample transactions
        customers = ["Juan Cruz", "Maria Santos", "Pedro Garcia", "Ana Lopez", "Carlos Silva"]
        
        transactions_created = 0
        for i in range(20):  # Create 20 transactions
            days_ago = random.randint(0, 7)  # Last 7 days
            transaction_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 10))
            
            transaction = RefillTransaction(
                customer_name=random.choice(customers + [None, None]),  # Some walk-ins
                gallons_count=random.randint(1, 5),
                price_per_gallon=25.0,
                total_amount=random.randint(1, 5) * 25.0,
                payment_type=random.choice(["Cash", "GCash", "Cash", "Cash"]),
                staff_id=random.choice(staff_users).id,
                created_at=transaction_time
            )
            
            session.add(transaction)
            transactions_created += 1
        
        # Create sample expenses - Water refill station specific
        expenses_created = 0
        water_station_expenses = [
            {"category": "Water Supply", "amounts": [200, 250, 300], "vendors": ["Cantilan Water District", "Local Water Supplier"]},
            {"category": "Filters", "amounts": [150, 180, 220], "vendors": ["Filter Supply Co.", "Aqua Parts Store"]},
            {"category": "Containers", "amounts": [100, 120, 150], "vendors": ["Container Supplier", "Plastic Depot"]},
            {"category": "Equipment Maintenance", "amounts": [300, 400, 500], "vendors": ["Equipment Service", "Repair Shop"]},
            {"category": "Transportation", "amounts": [50, 80, 100], "vendors": ["Delivery Service", "Tricycle Fare"]},
            {"category": "Supplies", "amounts": [30, 50, 75], "vendors": ["Local Store", "Office Supplies"]}
        ]
        
        for i in range(8):  # Create 8 water station specific expenses
            days_ago = random.randint(0, 14)  # Last 14 days
            expense_time = datetime.now() - timedelta(days=days_ago, hours=random.randint(0, 10))
            
            expense_type = random.choice(water_station_expenses)
            
            expense = Expense(
                category=expense_type["category"],
                amount=random.choice(expense_type["amounts"]),
                vendor=random.choice(expense_type["vendors"]),
                note=f"Water station {expense_type['category'].lower()} expense",
                staff_id=random.choice(staff_users).id,
                created_at=expense_time
            )
            
            session.add(expense)
            expenses_created += 1
        
        session.commit()
        
        print(f"✅ Created {transactions_created} transactions")
        print(f"✅ Created {expenses_created} expenses")
        print("🎉 Sample data creation completed!")
        
    except Exception as e:
        session.rollback()
        print(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    create_sample_data()
