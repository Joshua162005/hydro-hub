"""
Staff Management Page (Admin Only)
"""

import streamlit as st
from datetime import datetime, date
from hydrohub.models import User, RefillTransaction, Expense
from hydrohub.db import get_session
from hydrohub.auth import create_user, delete_user, update_user_password
from hydrohub.validations import validate_user_data, ValidationError
from hydrohub.ledger import log_user_action
from hydrohub.ui_components import (
    show_error_message, show_success_message, show_confirmation_modal,
    show_role_badge, show_date_range_picker
)
from hydrohub.utils import format_money, format_datetime

def show_staff_page(user, permissions):
    """Display staff management page (Admin only)"""
    if not permissions['can_manage_users']:
        show_error_message("Access Denied", "You don't have permission to manage staff.")
        return
    
    st.header("👥 Staff Management")
    
    # Tabs for different staff operations
    tab1, tab2, tab3, tab4 = st.tabs(["👤 All Staff", "➕ Add Staff", "📊 Performance", "🔧 Manage"])
    
    with tab1:
        show_all_staff()
    
    with tab2:
        show_add_staff_form(user)
    
    with tab3:
        show_staff_performance()
    
    with tab4:
        show_manage_staff(user)

def show_all_staff():
    """Display all staff members"""
    st.subheader("👤 All Staff Members")
    
    session = get_session()
    try:
        staff_members = session.query(User).all()
        
        if not staff_members:
            st.info("No staff members found.")
            return
        
        # Summary metrics
        total_staff = len(staff_members)
        admin_count = len([u for u in staff_members if u.role == 'admin'])
        staff_count = len([u for u in staff_members if u.role == 'staff'])
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Users", total_staff)
        with col2:
            st.metric("Administrators", admin_count)
        with col3:
            st.metric("Staff Members", staff_count)
        
        # Staff table
        st.subheader("📋 Staff Directory")
        
        for staff in staff_members:
            with st.expander(f"{staff.username} - {show_role_badge(staff.role)}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Username:** {staff.username}")
                    st.write(f"**Role:** {show_role_badge(staff.role)}")
                    st.write(f"**User ID:** {staff.id}")
                
                with col2:
                    st.write(f"**Created:** {format_datetime(staff.created_at)}")
                    if staff.last_login:
                        st.write(f"**Last Login:** {format_datetime(staff.last_login)}")
                    else:
                        st.write("**Last Login:** Never")
                
                # Quick stats for this staff member
                transactions = session.query(RefillTransaction).filter(RefillTransaction.staff_id == staff.id).count()
                expenses = session.query(Expense).filter(Expense.staff_id == staff.id).count()
                
                st.write(f"**Activity:** {transactions} transactions, {expenses} expenses recorded")
        
    finally:
        session.close()

def show_add_staff_form(user):
    """Display add new staff form"""
    st.subheader("➕ Add New Staff Member")
    
    with st.form("add_staff_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            username = st.text_input("Username*", placeholder="Enter unique username")
            password = st.text_input("Password*", type="password", placeholder="Enter secure password")
        
        with col2:
            role = st.selectbox("Role*", ["staff", "admin"])
            confirm_password = st.text_input("Confirm Password*", type="password", placeholder="Confirm password")
        
        # Password strength indicator
        if password:
            strength_score = 0
            if len(password) >= 8:
                strength_score += 1
            if any(c.isupper() for c in password):
                strength_score += 1
            if any(c.islower() for c in password):
                strength_score += 1
            if any(c.isdigit() for c in password):
                strength_score += 1
            
            strength_labels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
            strength_colors = ["🔴", "🟠", "🟡", "🟢", "🟢"]
            
            st.write(f"Password Strength: {strength_colors[strength_score]} {strength_labels[strength_score]}")
        
        submitted = st.form_submit_button("Create Staff Account", type="primary")
        
        if submitted:
            try:
                # Validate passwords match
                if password != confirm_password:
                    show_error_message("Password Mismatch", "Passwords do not match")
                    return
                
                # Validate data
                data = {
                    'username': username,
                    'password': password,
                    'role': role
                }
                validated_data = validate_user_data(data)
                
                # Create user
                new_user = create_user(
                    username=validated_data['username'],
                    password=validated_data['password'],
                    role=validated_data['role']
                )
                
                # Log to ledger
                log_user_action(
                    actor_id=user['id'],
                    action='create_user',
                    details={
                        'new_user_id': new_user.id,
                        'new_username': new_user.username,
                        'new_role': new_user.role
                    }
                )
                
                show_success_message(
                    f"✅ Staff account created successfully!",
                    f"Username: {username} | Role: {role.title()}"
                )
                
            except ValidationError as e:
                show_error_message("Validation Error", str(e))
            except ValueError as e:
                show_error_message("Creation Failed", str(e))
            except Exception as e:
                show_error_message("Failed to create staff account", str(e))

def show_staff_performance():
    """Display staff performance metrics"""
    st.subheader("📊 Staff Performance Analysis")
    
    # Date range for analysis
    start_date, end_date = show_date_range_picker("performance")
    
    if st.button("Generate Performance Report"):
        session = get_session()
        try:
            # Get all staff members
            staff_members = session.query(User).filter(User.role.in_(['admin', 'staff'])).all()
            
            if not staff_members:
                st.info("No staff members found.")
                return
            
            # Date range for queries
            start_datetime = datetime.combine(start_date, datetime.min.time())
            end_datetime = datetime.combine(end_date, datetime.max.time())
            
            performance_data = []
            
            for staff in staff_members:
                # Get transactions
                transactions = session.query(RefillTransaction).filter(
                    RefillTransaction.staff_id == staff.id,
                    RefillTransaction.created_at >= start_datetime,
                    RefillTransaction.created_at <= end_datetime
                ).all()
                
                # Get expenses
                expenses = session.query(Expense).filter(
                    Expense.staff_id == staff.id,
                    Expense.created_at >= start_datetime,
                    Expense.created_at <= end_datetime
                ).all()
                
                # Calculate metrics
                total_sales = sum(t.total_amount for t in transactions)
                total_gallons = sum(t.gallons_count for t in transactions)
                total_expenses = sum(e.amount for e in expenses)
                
                performance_data.append({
                    'staff': staff,
                    'transactions_count': len(transactions),
                    'total_sales': total_sales,
                    'total_gallons': total_gallons,
                    'expenses_count': len(expenses),
                    'total_expenses': total_expenses,
                    'net_contribution': total_sales - total_expenses
                })
            
            # Sort by total sales
            performance_data.sort(key=lambda x: x['total_sales'], reverse=True)
            
            # Display performance table
            st.subheader("🏆 Performance Rankings")
            
            for i, data in enumerate(performance_data, 1):
                staff = data['staff']
                
                with st.expander(f"#{i} {staff.username} - {format_money(data['total_sales'])} sales"):
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.write("**Sales Performance**")
                        st.write(f"• Transactions: {data['transactions_count']}")
                        st.write(f"• Total Sales: {format_money(data['total_sales'])}")
                        st.write(f"• Gallons Sold: {data['total_gallons']}")
                    
                    with col2:
                        st.write("**Expense Management**")
                        st.write(f"• Expenses Recorded: {data['expenses_count']}")
                        st.write(f"• Total Expenses: {format_money(data['total_expenses'])}")
                    
                    with col3:
                        st.write("**Net Contribution**")
                        net_contribution = data['net_contribution']
                        color = "🟢" if net_contribution >= 0 else "🔴"
                        st.write(f"• {color} {format_money(net_contribution)}")
                        
                        if data['transactions_count'] > 0:
                            avg_sale = data['total_sales'] / data['transactions_count']
                            st.write(f"• Avg Sale: {format_money(avg_sale)}")
            
            # Summary statistics
            st.subheader("📈 Team Summary")
            
            total_team_sales = sum(d['total_sales'] for d in performance_data)
            total_team_transactions = sum(d['transactions_count'] for d in performance_data)
            total_team_expenses = sum(d['total_expenses'] for d in performance_data)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Team Sales", format_money(total_team_sales))
            with col2:
                st.metric("Team Transactions", total_team_transactions)
            with col3:
                st.metric("Team Net", format_money(total_team_sales - total_team_expenses))
        
        finally:
            session.close()

def show_manage_staff(user):
    """Display staff management tools"""
    st.subheader("🔧 Manage Staff Accounts")
    
    session = get_session()
    try:
        staff_members = session.query(User).all()
        
        if not staff_members:
            st.info("No staff members to manage.")
            return
        
        # Select staff member to manage
        staff_options = {f"{s.username} ({s.role})": s.id for s in staff_members}
        selected_staff_key = st.selectbox("Select Staff Member", list(staff_options.keys()))
        selected_staff_id = staff_options[selected_staff_key]
        
        selected_staff = session.query(User).filter(User.id == selected_staff_id).first()
        
        if not selected_staff:
            return
        
        st.write(f"**Managing:** {selected_staff.username} ({selected_staff.role})")
        
        # Management options
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔑 Reset Password")
            
            with st.form(f"reset_password_{selected_staff_id}"):
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                
                reset_submitted = st.form_submit_button("Reset Password")
                
                if reset_submitted:
                    if new_password != confirm_new_password:
                        show_error_message("Password Mismatch", "Passwords do not match")
                    elif len(new_password) < 6:
                        show_error_message("Password Too Short", "Password must be at least 6 characters")
                    else:
                        try:
                            success = update_user_password(selected_staff_id, new_password)
                            if success:
                                # Log to ledger
                                log_user_action(
                                    actor_id=user['id'],
                                    action='reset_password',
                                    details={
                                        'target_user_id': selected_staff_id,
                                        'target_username': selected_staff.username
                                    }
                                )
                                
                                show_success_message("✅ Password reset successfully!")
                            else:
                                show_error_message("Reset Failed", "Could not reset password")
                        except Exception as e:
                            show_error_message("Reset Failed", str(e))
        
        with col2:
            st.subheader("🗑️ Delete Account")
            
            # Prevent deleting own account or last admin
            can_delete = True
            delete_warning = ""
            
            if selected_staff_id == user['id']:
                can_delete = False
                delete_warning = "Cannot delete your own account"
            elif selected_staff.role == 'admin':
                admin_count = session.query(User).filter(User.role == 'admin').count()
                if admin_count <= 1:
                    can_delete = False
                    delete_warning = "Cannot delete the last admin account"
            
            if not can_delete:
                st.warning(f"⚠️ {delete_warning}")
            else:
                st.warning("⚠️ **Danger Zone** - This action cannot be undone!")
                
                if st.button(f"🗑️ Delete {selected_staff.username}", type="secondary"):
                    # Use confirmation modal
                    if show_confirmation_modal(
                        "Confirm Deletion",
                        f"Are you sure you want to delete the account '{selected_staff.username}'? This action cannot be undone.",
                        f"delete_staff_{selected_staff_id}"
                    ):
                        try:
                            success = delete_user(selected_staff_id)
                            if success:
                                # Log to ledger
                                log_user_action(
                                    actor_id=user['id'],
                                    action='delete_user',
                                    details={
                                        'deleted_user_id': selected_staff_id,
                                        'deleted_username': selected_staff.username,
                                        'deleted_role': selected_staff.role
                                    }
                                )
                                
                                show_success_message(f"✅ Account '{selected_staff.username}' deleted successfully!")
                                st.rerun()
                            else:
                                show_error_message("Deletion Failed", "Could not delete account")
                        except Exception as e:
                            show_error_message("Deletion Failed", str(e))
    
    finally:
        session.close()
