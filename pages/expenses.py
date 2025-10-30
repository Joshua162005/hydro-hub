"""
Expense Management Page
"""

import streamlit as st
from datetime import datetime, date
from hydrohub.models import Expense, User
from hydrohub.db import get_session
from hydrohub.validations import validate_expense_data, ValidationError
from hydrohub.ledger import log_expense
from hydrohub.storage import save_receipt
from hydrohub.ui_components import (
    show_error_message, show_success_message, show_file_uploader, 
    show_date_range_picker, show_receipt_preview
)
from hydrohub.utils import format_money, format_datetime

def show_expenses_page(user, permissions):
    """Display expense management page"""
    st.header("💰 Expense Management")
    
    # Tabs for different expense operations
    tab1, tab2, tab3 = st.tabs(["📋 Recent Expenses", "➕ Add Expense", "📊 Expense Analysis"])
    
    with tab1:
        show_recent_expenses()
    
    with tab2:
        show_add_expense_form(user)
    
    with tab3:
        show_expense_analysis()

def show_recent_expenses():
    """Display recent expenses"""
    st.subheader("📋 Recent Expenses")
    
    # Date filter
    col1, col2, col3 = st.columns([2, 2, 1])
    
    with col1:
        start_date = st.date_input("From Date", value=date.today().replace(day=1))
    with col2:
        end_date = st.date_input("To Date", value=date.today())
    with col3:
        category_filter = st.selectbox("Category", ["All"] + [
            "Water Supply", "Filters", "Containers", "Equipment Maintenance",
            "Transportation", "Supplies", "Other"
        ])
    
    # Get expenses
    session = get_session()
    try:
        query = session.query(Expense).join(User, Expense.staff_id == User.id, isouter=True)
        
        # Apply date filter
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())
        query = query.filter(Expense.created_at >= start_datetime, Expense.created_at <= end_datetime)
        
        # Apply category filter
        if category_filter != "All":
            query = query.filter(Expense.category == category_filter)
        
        expenses = query.order_by(Expense.created_at.desc()).all()
        
        if not expenses:
            st.info("No expenses found for the selected criteria.")
            return
        
        # Summary metrics
        total_amount = sum(e.amount for e in expenses)
        avg_amount = total_amount / len(expenses) if expenses else 0
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Expenses", format_money(total_amount))
        with col2:
            st.metric("Number of Expenses", len(expenses))
        with col3:
            st.metric("Average Amount", format_money(avg_amount))
        
        # Expenses table
        st.subheader("💸 Expense Details")
        
        for expense in expenses:
            with st.expander(f"{expense.category} - {format_money(expense.amount)} ({format_datetime(expense.created_at)})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Amount:** {format_money(expense.amount)}")
                    st.write(f"**Category:** {expense.category}")
                    st.write(f"**Vendor:** {expense.vendor or 'N/A'}")
                    st.write(f"**Staff:** {expense.staff.username if expense.staff else 'Unknown'}")
                
                with col2:
                    st.write(f"**Date:** {format_datetime(expense.created_at)}")
                    if expense.note:
                        st.write(f"**Note:** {expense.note}")
                    
                    # Show receipt if available
                    if expense.receipt_path:
                        show_receipt_preview(expense.receipt_path)
        
    finally:
        session.close()

def show_add_expense_form(user):
    """Display add expense form"""
    st.subheader("➕ Add New Expense")
    
    with st.form("add_expense_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            category = st.selectbox("Category*", [
                "Water Supply", "Filters", "Containers", "Equipment Maintenance",
                "Transportation", "Supplies", "Other"
            ])
            amount = st.number_input("Amount (₱)*", min_value=0.01, step=0.25, value=0.01)
            vendor = st.text_input("Vendor/Supplier", placeholder="e.g., Filter Supply Co., Water District")
        
        with col2:
            note = st.text_area("Description/Note", placeholder="Brief description of the expense")
            receipt_file = show_file_uploader("Receipt (Optional)", "expense_receipt")
        
        submitted = st.form_submit_button("Add Expense", type="primary")
        
        if submitted:
            try:
                # Validate data
                data = {
                    'category': category,
                    'amount': amount,
                    'vendor': vendor,
                    'note': note,
                    'staff_id': user['id']
                }
                validated_data = validate_expense_data(data)
                
                # Handle receipt upload
                receipt_path = None
                receipt_hash = None
                if receipt_file:
                    try:
                        receipt_path, receipt_hash = save_receipt(receipt_file)
                        validated_data['receipt_path'] = receipt_path
                    except Exception as e:
                        show_error_message("Receipt upload failed", str(e))
                        return
                
                # Save to database
                session = get_session()
                try:
                    expense = Expense(**validated_data)
                    session.add(expense)
                    session.commit()
                    session.refresh(expense)
                    
                    # Log to ledger
                    ledger_data = validated_data.copy()
                    if receipt_hash:
                        ledger_data['receipt_hash'] = receipt_hash
                    
                    log_expense(
                        actor_id=user['id'],
                        expense_id=expense.id,
                        expense_data=ledger_data
                    )
                    
                    show_success_message(
                        f"✅ Expense recorded successfully!",
                        f"ID: {expense.id} | {category}: {format_money(amount)}"
                    )
                    
                finally:
                    session.close()
                    
            except ValidationError as e:
                show_error_message("Validation Error", str(e))
            except Exception as e:
                show_error_message("Failed to record expense", str(e))

def show_expense_analysis():
    """Display expense analysis and charts"""
    st.subheader("📊 Expense Analysis")
    
    # Date range for analysis
    start_date, end_date = show_date_range_picker("analysis")
    
    if st.button("Generate Analysis"):
        session = get_session()
        try:
            # Get expenses in date range
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            expenses = session.query(Expense).filter(
                Expense.created_at >= start_datetime,
                Expense.created_at <= end_datetime
            ).all()
            
            if not expenses:
                st.info("No expenses found for the selected period.")
                return
            
            # Category breakdown
            category_totals = {}
            for expense in expenses:
                if expense.category not in category_totals:
                    category_totals[expense.category] = 0
                category_totals[expense.category] += expense.amount
            
            # Display analysis
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**📋 Category Breakdown**")
                for category, total in sorted(category_totals.items(), key=lambda x: x[1], reverse=True):
                    percentage = (total / sum(category_totals.values())) * 100
                    st.write(f"• {category}: {format_money(total)} ({percentage:.1f}%)")
            
            with col2:
                st.write("**📈 Summary Statistics**")
                total_expenses = sum(category_totals.values())
                avg_expense = total_expenses / len(expenses)
                days = (end_date - start_date).days + 1
                daily_avg = total_expenses / days if days > 0 else 0
                
                st.write(f"• Total Expenses: {format_money(total_expenses)}")
                st.write(f"• Number of Expenses: {len(expenses)}")
                st.write(f"• Average per Expense: {format_money(avg_expense)}")
                st.write(f"• Daily Average: {format_money(daily_avg)}")
            
            # Charts using matplotlib
            if category_totals:
                import matplotlib.pyplot as plt
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Pie chart
                    fig, ax = plt.subplots(figsize=(8, 6))
                    categories = list(category_totals.keys())
                    amounts = list(category_totals.values())
                    
                    ax.pie(amounts, labels=categories, autopct='%1.1f%%', startangle=90)
                    ax.set_title('Expenses by Category')
                    st.pyplot(fig)
                
                with col2:
                    # Bar chart
                    fig, ax = plt.subplots(figsize=(8, 6))
                    categories = list(category_totals.keys())
                    amounts = list(category_totals.values())
                    
                    ax.bar(categories, amounts)
                    ax.set_title('Expense Amounts by Category')
                    ax.set_ylabel('Amount (₱)')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    st.pyplot(fig)
            
            # Top expenses
            st.subheader("💸 Largest Expenses")
            top_expenses = sorted(expenses, key=lambda x: x.amount, reverse=True)[:10]
            
            for i, expense in enumerate(top_expenses, 1):
                st.write(f"{i}. **{expense.category}** - {format_money(expense.amount)} ({format_datetime(expense.created_at)})")
                if expense.vendor:
                    st.write(f"   Vendor: {expense.vendor}")
                if expense.note:
                    st.write(f"   Note: {expense.note}")
        
        finally:
            session.close()
