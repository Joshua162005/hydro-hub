"""
Reporting and data export functionality
"""

import csv
import json
import pandas as pd
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from io import StringIO, BytesIO
from sqlalchemy import func, and_
from hydrohub.db import get_session
from hydrohub.models import RefillTransaction, Expense, InventoryItem, User, Ledger
from hydrohub.utils import format_money, get_current_time, get_business_config
from hydrohub.ledger import add_ledger_entry, export_ledger_proof

def get_sales_summary(start_date: date, end_date: date) -> Dict[str, Any]:
    """Get sales summary for date range"""
    session = get_session()
    try:
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get transactions in date range
        transactions = session.query(RefillTransaction).filter(
            and_(
                RefillTransaction.created_at >= start_datetime,
                RefillTransaction.created_at <= end_datetime
            )
        ).all()
        
        # Calculate summary
        total_transactions = len(transactions)
        total_gallons = sum(t.gallons_count for t in transactions)
        total_revenue = sum(t.total_amount for t in transactions)
        
        # Average calculations
        avg_gallons_per_transaction = total_gallons / total_transactions if total_transactions > 0 else 0
        avg_revenue_per_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
        avg_price_per_gallon = total_revenue / total_gallons if total_gallons > 0 else 0
        
        # Payment method breakdown
        payment_breakdown = {}
        for transaction in transactions:
            payment_type = transaction.payment_type
            if payment_type not in payment_breakdown:
                payment_breakdown[payment_type] = {'count': 0, 'amount': 0}
            payment_breakdown[payment_type]['count'] += 1
            payment_breakdown[payment_type]['amount'] += transaction.total_amount
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days + 1
            },
            'transactions': {
                'total_count': total_transactions,
                'total_gallons': total_gallons,
                'total_revenue': total_revenue,
                'avg_gallons_per_transaction': avg_gallons_per_transaction,
                'avg_revenue_per_transaction': avg_revenue_per_transaction,
                'avg_price_per_gallon': avg_price_per_gallon
            },
            'payment_breakdown': payment_breakdown,
            'raw_transactions': transactions
        }
        
    finally:
        session.close()

def get_expense_summary(start_date: date, end_date: date) -> Dict[str, Any]:
    """Get expense summary for date range"""
    session = get_session()
    try:
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get expenses in date range
        expenses = session.query(Expense).filter(
            and_(
                Expense.created_at >= start_datetime,
                Expense.created_at <= end_datetime
            )
        ).all()
        
        # Calculate summary
        total_expenses = len(expenses)
        total_amount = sum(e.amount for e in expenses)
        
        # Category breakdown
        category_breakdown = {}
        for expense in expenses:
            category = expense.category
            if category not in category_breakdown:
                category_breakdown[category] = {'count': 0, 'amount': 0}
            category_breakdown[category]['count'] += 1
            category_breakdown[category]['amount'] += expense.amount
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date,
                'days': (end_date - start_date).days + 1
            },
            'expenses': {
                'total_count': total_expenses,
                'total_amount': total_amount,
                'avg_amount_per_expense': total_amount / total_expenses if total_expenses > 0 else 0
            },
            'category_breakdown': category_breakdown,
            'raw_expenses': expenses
        }
        
    finally:
        session.close()

def get_profit_loss_report(start_date: date, end_date: date) -> Dict[str, Any]:
    """Generate profit and loss report"""
    sales_summary = get_sales_summary(start_date, end_date)
    expense_summary = get_expense_summary(start_date, end_date)
    
    revenue = sales_summary['transactions']['total_revenue']
    expenses = expense_summary['expenses']['total_amount']
    gross_profit = revenue - expenses
    
    # Calculate margins
    gross_margin = (gross_profit / revenue * 100) if revenue > 0 else 0
    
    return {
        'period': sales_summary['period'],
        'revenue': revenue,
        'expenses': expenses,
        'gross_profit': gross_profit,
        'gross_margin_percent': gross_margin,
        'sales_summary': sales_summary,
        'expense_summary': expense_summary
    }

def get_inventory_report() -> Dict[str, Any]:
    """Get current inventory report"""
    session = get_session()
    try:
        items = session.query(InventoryItem).all()
        
        total_items = len(items)
        total_value = sum(item.quantity * item.unit_cost for item in items)
        
        # Category breakdown
        category_breakdown = {}
        for item in items:
            category = item.category
            if category not in category_breakdown:
                category_breakdown[category] = {'count': 0, 'quantity': 0, 'value': 0}
            category_breakdown[category]['count'] += 1
            category_breakdown[category]['quantity'] += item.quantity
            category_breakdown[category]['value'] += item.quantity * item.unit_cost
        
        # Low stock items (assuming threshold of 10)
        low_stock_threshold = 10
        low_stock_items = [item for item in items if item.quantity <= low_stock_threshold]
        
        return {
            'summary': {
                'total_items': total_items,
                'total_value': total_value,
                'low_stock_count': len(low_stock_items)
            },
            'category_breakdown': category_breakdown,
            'low_stock_items': low_stock_items,
            'all_items': items
        }
        
    finally:
        session.close()

def get_staff_performance_report(start_date: date, end_date: date) -> Dict[str, Any]:
    """Get staff performance report"""
    session = get_session()
    try:
        # Convert dates to datetime for comparison
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        
        # Get staff with their transactions
        staff_performance = {}
        
        staff_members = session.query(User).filter(User.role.in_(['admin', 'staff'])).all()
        
        for staff in staff_members:
            transactions = session.query(RefillTransaction).filter(
                and_(
                    RefillTransaction.staff_id == staff.id,
                    RefillTransaction.created_at >= start_datetime,
                    RefillTransaction.created_at <= end_datetime
                )
            ).all()
            
            expenses = session.query(Expense).filter(
                and_(
                    Expense.staff_id == staff.id,
                    Expense.created_at >= start_datetime,
                    Expense.created_at <= end_datetime
                )
            ).all()
            
            staff_performance[staff.username] = {
                'user_id': staff.id,
                'role': staff.role,
                'transactions': {
                    'count': len(transactions),
                    'total_gallons': sum(t.gallons_count for t in transactions),
                    'total_revenue': sum(t.total_amount for t in transactions)
                },
                'expenses': {
                    'count': len(expenses),
                    'total_amount': sum(e.amount for e in expenses)
                }
            }
        
        return {
            'period': {
                'start_date': start_date,
                'end_date': end_date
            },
            'staff_performance': staff_performance
        }
        
    finally:
        session.close()

def export_transactions_csv(start_date: date, end_date: date, actor_id: int) -> str:
    """Export transactions to CSV format"""
    sales_summary = get_sales_summary(start_date, end_date)
    transactions = sales_summary['raw_transactions']
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    config = get_business_config()
    writer.writerow([f"{config['name']} - Transaction Report"])
    writer.writerow([f"Period: {start_date} to {end_date}"])
    writer.writerow([f"Generated: {get_current_time()}"])
    writer.writerow([])
    
    # Write transaction data
    writer.writerow([
        'ID', 'Date', 'Customer', 'Gallons', 'Price per Gallon',
        'Total Amount', 'Payment Type', 'Staff', 'Receipt'
    ])
    
    for transaction in transactions:
        writer.writerow([
            transaction.id,
            transaction.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            transaction.customer_name or 'Walk-in',
            transaction.gallons_count,
            transaction.price_per_gallon,
            transaction.total_amount,
            transaction.payment_type,
            transaction.staff.username if transaction.staff else 'Unknown',
            'Yes' if transaction.receipt_path else 'No'
        ])
    
    # Write summary
    writer.writerow([])
    writer.writerow(['SUMMARY'])
    writer.writerow(['Total Transactions', len(transactions)])
    writer.writerow(['Total Gallons', sum(t.gallons_count for t in transactions)])
    writer.writerow(['Total Revenue', sum(t.total_amount for t in transactions)])
    
    csv_content = output.getvalue()
    output.close()
    
    # Log export to ledger
    add_ledger_entry(
        actor_id=actor_id,
        action_type='export_transactions',
        data_dict={
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'transaction_count': len(transactions),
            'format': 'CSV'
        },
        human_message=f"Exported {len(transactions)} transactions to CSV for period {start_date} to {end_date}"
    )
    
    return csv_content

def export_expenses_csv(start_date: date, end_date: date, actor_id: int) -> str:
    """Export expenses to CSV format"""
    expense_summary = get_expense_summary(start_date, end_date)
    expenses = expense_summary['raw_expenses']
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    config = get_business_config()
    writer.writerow([f"{config['name']} - Expense Report"])
    writer.writerow([f"Period: {start_date} to {end_date}"])
    writer.writerow([f"Generated: {get_current_time()}"])
    writer.writerow([])
    
    # Write expense data
    writer.writerow([
        'ID', 'Date', 'Category', 'Amount', 'Vendor', 'Note', 'Staff', 'Receipt'
    ])
    
    for expense in expenses:
        writer.writerow([
            expense.id,
            expense.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            expense.category,
            expense.amount,
            expense.vendor or '',
            expense.note or '',
            expense.staff.username if expense.staff else 'Unknown',
            'Yes' if expense.receipt_path else 'No'
        ])
    
    # Write summary
    writer.writerow([])
    writer.writerow(['SUMMARY'])
    writer.writerow(['Total Expenses', len(expenses)])
    writer.writerow(['Total Amount', sum(e.amount for e in expenses)])
    
    csv_content = output.getvalue()
    output.close()
    
    # Log export to ledger
    add_ledger_entry(
        actor_id=actor_id,
        action_type='export_expenses',
        data_dict={
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'expense_count': len(expenses),
            'format': 'CSV'
        },
        human_message=f"Exported {len(expenses)} expenses to CSV for period {start_date} to {end_date}"
    )
    
    return csv_content

def export_profit_loss_csv(start_date: date, end_date: date, actor_id: int) -> str:
    """Export profit & loss report to CSV"""
    pl_report = get_profit_loss_report(start_date, end_date)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    config = get_business_config()
    writer.writerow([f"{config['name']} - Profit & Loss Report"])
    writer.writerow([f"Period: {start_date} to {end_date}"])
    writer.writerow([f"Generated: {get_current_time()}"])
    writer.writerow([])
    
    # Write P&L data
    writer.writerow(['PROFIT & LOSS STATEMENT'])
    writer.writerow([])
    writer.writerow(['Revenue', pl_report['revenue']])
    writer.writerow(['Expenses', pl_report['expenses']])
    writer.writerow(['Gross Profit', pl_report['gross_profit']])
    writer.writerow(['Gross Margin %', f"{pl_report['gross_margin_percent']:.2f}%"])
    writer.writerow([])
    
    # Sales breakdown
    writer.writerow(['SALES BREAKDOWN'])
    sales = pl_report['sales_summary']['transactions']
    writer.writerow(['Total Transactions', sales['total_count']])
    writer.writerow(['Total Gallons Sold', sales['total_gallons']])
    writer.writerow(['Average Price per Gallon', sales['avg_price_per_gallon']])
    writer.writerow([])
    
    # Expense breakdown
    writer.writerow(['EXPENSE BREAKDOWN'])
    for category, data in pl_report['expense_summary']['category_breakdown'].items():
        writer.writerow([f"{category} Expenses", data['amount']])
    
    csv_content = output.getvalue()
    output.close()
    
    # Log export to ledger
    add_ledger_entry(
        actor_id=actor_id,
        action_type='export_profit_loss',
        data_dict={
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'revenue': pl_report['revenue'],
            'expenses': pl_report['expenses'],
            'profit': pl_report['gross_profit'],
            'format': 'CSV'
        },
        human_message=f"Exported P&L report to CSV for period {start_date} to {end_date}"
    )
    
    return csv_content

def export_inventory_csv(actor_id: int) -> str:
    """Export inventory to CSV"""
    inventory_report = get_inventory_report()
    items = inventory_report['all_items']
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    config = get_business_config()
    writer.writerow([f"{config['name']} - Inventory Report"])
    writer.writerow([f"Generated: {get_current_time()}"])
    writer.writerow([])
    
    # Write inventory data
    writer.writerow([
        'ID', 'Name', 'Category', 'Quantity', 'Unit Cost', 'Total Value', 'Location', 'Last Updated'
    ])
    
    for item in items:
        writer.writerow([
            item.id,
            item.name,
            item.category,
            item.quantity,
            item.unit_cost,
            item.quantity * item.unit_cost,
            item.location or '',
            item.last_updated.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    # Write summary
    writer.writerow([])
    writer.writerow(['SUMMARY'])
    writer.writerow(['Total Items', len(items)])
    writer.writerow(['Total Value', sum(item.quantity * item.unit_cost for item in items)])
    
    csv_content = output.getvalue()
    output.close()
    
    # Log export to ledger
    add_ledger_entry(
        actor_id=actor_id,
        action_type='export_inventory',
        data_dict={
            'item_count': len(items),
            'total_value': sum(item.quantity * item.unit_cost for item in items),
            'format': 'CSV'
        },
        human_message=f"Exported inventory report to CSV ({len(items)} items)"
    )
    
    return csv_content

def export_ledger_csv(start_date: Optional[date], end_date: Optional[date], actor_id: int) -> str:
    """Export ledger entries to CSV"""
    # Convert dates to ISO format if provided
    start_iso = start_date.isoformat() + 'T00:00:00Z' if start_date else None
    end_iso = end_date.isoformat() + 'T23:59:59Z' if end_date else None
    
    # Get ledger proof
    proof = export_ledger_proof(start_iso, end_iso)
    
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    config = get_business_config()
    writer.writerow([f"{config['name']} - Ledger Export"])
    writer.writerow([f"Period: {start_date or 'All'} to {end_date or 'All'}"])
    writer.writerow([f"Generated: {get_current_time()}"])
    writer.writerow([f"Proof Hash: {proof['proof_hash']}"])
    writer.writerow([])
    
    # Write ledger data
    writer.writerow([
        'ID', 'Timestamp', 'Previous Hash', 'Data Hash', 'Actor ID', 'Action Type', 'Data'
    ])
    
    for entry in proof['entries']:
        writer.writerow([
            entry['id'],
            entry['timestamp'],
            entry['prev_hash'],
            entry['data_hash'],
            entry['actor_id'] or '',
            entry['action_type'],
            entry['data_text']
        ])
    
    csv_content = output.getvalue()
    output.close()
    
    # Log export to ledger
    add_ledger_entry(
        actor_id=actor_id,
        action_type='export_ledger',
        data_dict={
            'start_date': start_date.isoformat() if start_date else None,
            'end_date': end_date.isoformat() if end_date else None,
            'entry_count': len(proof['entries']),
            'proof_hash': proof['proof_hash'],
            'format': 'CSV'
        },
        human_message=f"Exported ledger to CSV ({len(proof['entries'])} entries)"
    )
    
    return csv_content

def get_daily_sales_data(days: int = 7) -> List[Dict[str, Any]]:
    """Get daily sales data for charts"""
    session = get_session()
    try:
        # Get data for the last N days
        end_date = date.today()
        start_date = date.fromordinal(end_date.toordinal() - days + 1)
        
        daily_data = []
        
        for i in range(days):
            current_date = date.fromordinal(start_date.toordinal() + i)
            start_datetime = datetime.combine(current_date, datetime.min.time())
            end_datetime = datetime.combine(current_date, datetime.max.time())
            
            # Get transactions for this day
            transactions = session.query(RefillTransaction).filter(
                and_(
                    RefillTransaction.created_at >= start_datetime,
                    RefillTransaction.created_at <= end_datetime
                )
            ).all()
            
            # Get expenses for this day
            expenses = session.query(Expense).filter(
                and_(
                    Expense.created_at >= start_datetime,
                    Expense.created_at <= end_datetime
                )
            ).all()
            
            daily_revenue = sum(t.total_amount for t in transactions)
            daily_expenses = sum(e.amount for e in expenses)
            daily_gallons = sum(t.gallons_count for t in transactions)
            
            daily_data.append({
                'date': current_date,
                'revenue': daily_revenue,
                'expenses': daily_expenses,
                'profit': daily_revenue - daily_expenses,
                'gallons': daily_gallons,
                'transactions': len(transactions)
            })
        
        return daily_data
        
    finally:
        session.close()
