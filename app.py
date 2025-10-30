"""
HydroHub - Main Streamlit Application
Cantilan Water Refill Station Management System
"""

import streamlit as st
import os
from datetime import datetime, date
from hydrohub.db import init_db
from hydrohub.auth import authenticate_user, is_session_valid, get_user_permissions
from hydrohub.ui_components import (
    show_header, show_user_info, show_logout_button, show_navigation_menu,
    show_error_message, show_success_message
)
from hydrohub.utils import get_current_time

# Initialize database
init_db()

# Streamlit configuration
st.set_page_config(
    page_title="HydroHub Cantilan",
    page_icon="💧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None
if 'login_time' not in st.session_state:
    st.session_state.login_time = None

def show_login_page():
    """Display login page"""
    show_header()
    
    st.markdown("### 🔐 Login to HydroHub")
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        login_button = st.form_submit_button("Login", type="primary")
        
        if login_button:
            if not username or not password:
                show_error_message("Please enter both username and password")
                return
            
            try:
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = {
                        'id': user.id,
                        'username': user.username,
                        'role': user.role,
                        'last_login': user.last_login
                    }
                    st.session_state.login_time = get_current_time()
                    show_success_message(f"Welcome back, {user.username}!")
                    st.rerun()
                else:
                    show_error_message("Invalid username or password")
            except Exception as e:
                show_error_message("Login failed", str(e))
    
    # Show default credentials info
    with st.expander("ℹ️ Default Credentials"):
        st.info("""
        **Default Admin Account:**
        - Username: `admin`
        - Password: `admin123`
        
        ⚠️ **Important:** Change the default password immediately after first login!
        """)

def check_session_validity():
    """Check if current session is valid"""
    if not st.session_state.user or not st.session_state.login_time:
        return False
    
    if not is_session_valid(st.session_state.login_time):
        st.session_state.user = None
        st.session_state.login_time = None
        show_error_message("Session expired. Please login again.")
        return False
    
    return True

def show_dashboard(user, permissions):
    """Show dashboard page"""
    from hydrohub.reports import get_daily_sales_data, get_inventory_report
    from hydrohub.utils import format_money
    import matplotlib.pyplot as plt
    
    st.header("📊 Dashboard")
    
    # Quick stats
    col1, col2, col3, col4 = st.columns(4)
    
    # Get today's data
    daily_data = get_daily_sales_data(1)
    today_data = daily_data[0] if daily_data else {'revenue': 0, 'gallons': 0, 'expenses': 0, 'profit': 0}
    
    with col1:
        st.metric("Today's Revenue", format_money(today_data['revenue']))
    with col2:
        st.metric("Gallons Sold", today_data['gallons'])
    with col3:
        st.metric("Today's Expenses", format_money(today_data['expenses']))
    with col4:
        st.metric("Net Profit", format_money(today_data['profit']))
    
    # Charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Last 7 Days Sales")
        weekly_data = get_daily_sales_data(7)
        if weekly_data:
            dates = [d['date'].strftime('%m-%d') for d in weekly_data]
            revenues = [d['revenue'] for d in weekly_data]
            
            fig, ax = plt.subplots()
            ax.plot(dates, revenues, marker='o')
            ax.set_title('Daily Revenue')
            ax.set_ylabel('Revenue (₱)')
            plt.xticks(rotation=45)
            st.pyplot(fig)
    
    with col2:
        st.subheader("📦 Inventory Status")
        inventory_report = get_inventory_report()
        if inventory_report['all_items']:
            categories = list(inventory_report['category_breakdown'].keys())
            values = [inventory_report['category_breakdown'][cat]['value'] for cat in categories]
            
            fig, ax = plt.subplots()
            ax.pie(values, labels=categories, autopct='%1.1f%%')
            ax.set_title('Inventory Value by Category')
            st.pyplot(fig)

def show_simple_refill_page(user, permissions):
    """Simple refill recording page"""
    from hydrohub.models import RefillTransaction
    from hydrohub.db import get_session
    from hydrohub.validations import validate_refill_transaction
    from hydrohub.ledger import log_refill_transaction
    from hydrohub.utils import get_business_config, format_money
    
    st.header("💧 Record Refill Transaction")
    
    config = get_business_config()
    
    with st.form("refill_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            customer_name = st.text_input("Customer Name (Optional)")
            gallons = st.number_input("Number of Gallons", min_value=1, step=1, value=1)
        
        with col2:
            price_per_gallon = st.number_input(
                "Price per Gallon (₱)", 
                min_value=0.01, 
                step=0.25, 
                value=config['default_price_per_gallon']
            )
            payment_type = st.selectbox(
                "Payment Method", 
                ["Cash", "GCash", "PayMaya", "Bank Transfer", "On-account"]
            )
        
        total_amount = gallons * price_per_gallon
        st.info(f"**Total Amount: {format_money(total_amount)}**")
        
        submitted = st.form_submit_button("Record Refill", type="primary")
        
        if submitted:
            try:
                # Validate data
                data = {
                    'customer_name': customer_name,
                    'gallons_count': gallons,
                    'price_per_gallon': price_per_gallon,
                    'payment_type': payment_type,
                    'staff_id': user['id']
                }
                validated_data = validate_refill_transaction(data)
                
                # Save to database
                session = get_session()
                try:
                    transaction = RefillTransaction(**validated_data)
                    session.add(transaction)
                    session.commit()
                    session.refresh(transaction)
                    
                    # Log to ledger
                    log_refill_transaction(
                        actor_id=user['id'],
                        transaction_id=transaction.id,
                        transaction_data=validated_data
                    )
                    
                    show_success_message(
                        f"✅ Refill recorded successfully!",
                        f"Transaction ID: {transaction.id} | Total: {format_money(total_amount)}"
                    )
                    
                finally:
                    session.close()
                    
            except Exception as e:
                show_error_message("Failed to record refill", str(e))

def show_simple_reports_page(user, permissions):
    """Simple reports page"""
    from hydrohub.reports import get_profit_loss_report, export_transactions_csv
    from hydrohub.ui_components import show_date_range_picker
    from hydrohub.utils import format_money
    
    st.header("📊 Reports")
    
    # Date range picker
    start_date, end_date = show_date_range_picker()
    
    if st.button("Generate P&L Report"):
        try:
            report = get_profit_loss_report(start_date, end_date)
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Revenue", format_money(report['revenue']))
            with col2:
                st.metric("Expenses", format_money(report['expenses']))
            with col3:
                st.metric("Profit", format_money(report['gross_profit']))
            
            st.subheader("📈 Profit Margin")
            st.write(f"**{report['gross_margin_percent']:.1f}%**")
            
        except Exception as e:
            show_error_message("Failed to generate report", str(e))
    
    # Export options
    st.subheader("📤 Export Data")
    if st.button("Export Transactions (CSV)"):
        try:
            csv_data = export_transactions_csv(start_date, end_date, user['id'])
            st.download_button(
                "Download CSV",
                csv_data,
                f"transactions_{start_date}_to_{end_date}.csv",
                "text/csv"
            )
        except Exception as e:
            show_error_message("Export failed", str(e))

def main():
    """Main application logic"""
    # Check if user is logged in and session is valid
    if not st.session_state.user or not check_session_validity():
        show_login_page()
        return
    
    # User is logged in - show main application
    user = st.session_state.user
    permissions = get_user_permissions(user['role'])
    
    # Sidebar
    show_user_info(user)
    show_logout_button()
    
    # Navigation
    page = show_navigation_menu(user['role'])
    
    # Main content area
    if page == "Dashboard":
        show_dashboard(user, permissions)
    
    elif page == "Record Refill":
        if permissions['can_record_transactions']:
            show_simple_refill_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to record transactions")
    
    elif page == "Inventory":
        if permissions['can_manage_inventory']:
            from pages.inventory import show_inventory_page
            show_inventory_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to manage inventory")
    
    elif page == "Expenses":
        if permissions['can_manage_expenses']:
            from pages.expenses import show_expenses_page
            show_expenses_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to manage expenses")
    
    elif page == "Reports":
        if permissions['can_view_reports']:
            show_simple_reports_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to view reports")
    
    elif page == "Staff Management":
        if permissions['can_manage_users']:
            from pages.staff import show_staff_page
            show_staff_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to manage staff")
    
    elif page == "Ledger":
        if permissions['can_view_ledger']:
            from pages.ledger import show_ledger_page
            show_ledger_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to view ledger")
    
    elif page == "Settings":
        if permissions['can_manage_settings']:
            from pages.settings import show_settings_page
            show_settings_page(user, permissions)
        else:
            show_error_message("Access denied", "You don't have permission to manage settings")

if __name__ == "__main__":
    main()
