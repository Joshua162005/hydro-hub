"""
Reusable Streamlit UI components
"""

import streamlit as st
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from hydrohub.utils import format_money, format_datetime, get_business_config

def show_header():
    """Display application header"""
    config = get_business_config()
    st.title(f"💧 {config['name']}")
    st.caption(f"📍 {config['location']} | Timezone: {config['timezone']}")

def show_user_info(user: Dict[str, Any]):
    """Display user information in sidebar"""
    st.sidebar.success(f"👤 {user['username']}")
    st.sidebar.caption(f"Role: {user['role'].title()}")
    if user.get('last_login'):
        st.sidebar.caption(f"Last login: {format_datetime(user['last_login'])}")

def show_logout_button():
    """Display logout button"""
    if st.sidebar.button("🚪 Logout", type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

def show_navigation_menu(user_role: str) -> str:
    """Display navigation menu based on user role"""
    # Base menu items available to all users
    menu_items = ["Dashboard"]
    
    # Role-based menu items
    if user_role in ['admin', 'staff']:
        menu_items.extend(["Record Refill", "Inventory", "Expenses"])
    
    if user_role in ['admin', 'staff', 'public']:
        menu_items.append("Reports")
    
    if user_role == 'admin':
        menu_items.extend(["Staff Management", "Ledger", "Settings"])
    
    return st.sidebar.radio("Navigation", menu_items)

def show_confirmation_modal(title: str, message: str, key: str) -> bool:
    """Show confirmation modal dialog"""
    if f"show_modal_{key}" not in st.session_state:
        st.session_state[f"show_modal_{key}"] = False
    
    if st.session_state[f"show_modal_{key}"]:
        with st.container():
            st.warning(f"**{title}**")
            st.write(message)
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Confirm", key=f"confirm_{key}"):
                    st.session_state[f"show_modal_{key}"] = False
                    return True
            with col2:
                if st.button("❌ Cancel", key=f"cancel_{key}"):
                    st.session_state[f"show_modal_{key}"] = False
                    return False
    
    return False

def show_success_message(message: str, details: Optional[str] = None):
    """Show success message with optional details"""
    st.success(message)
    if details:
        st.info(details)

def show_error_message(message: str, details: Optional[str] = None):
    """Show error message with optional details"""
    st.error(message)
    if details:
        with st.expander("Error Details"):
            st.code(details)

def show_metric_card(title: str, value: str, delta: Optional[str] = None, help_text: Optional[str] = None):
    """Display metric card"""
    st.metric(
        label=title,
        value=value,
        delta=delta,
        help=help_text
    )

def show_data_table(data: List[Dict], columns: List[str], key: str = "table"):
    """Display data table with optional actions"""
    if not data:
        st.info("No data available")
        return
    
    # Convert to display format
    display_data = []
    for item in data:
        row = {}
        for col in columns:
            value = item.get(col, "")
            # Format specific column types
            if col.endswith('_at') or col.endswith('_time'):
                value = format_datetime(value) if value else ""
            elif col.endswith('_amount') or col.endswith('_cost') or col.endswith('_price'):
                value = format_money(value) if value is not None else ""
            row[col] = value
        display_data.append(row)
    
    st.dataframe(display_data, use_container_width=True, key=key)

def show_date_range_picker(key: str = "date_range") -> tuple:
    """Date range picker component"""
    col1, col2 = st.columns(2)
    
    with col1:
        start_date = st.date_input(
            "Start Date",
            value=date.today().replace(day=1),  # First day of current month
            key=f"{key}_start"
        )
    
    with col2:
        end_date = st.date_input(
            "End Date",
            value=date.today(),
            key=f"{key}_end"
        )
    
    return start_date, end_date

def show_file_uploader(label: str, key: str, help_text: Optional[str] = None):
    """File uploader component for receipts"""
    return st.file_uploader(
        label,
        type=['pdf', 'jpg', 'jpeg', 'png'],
        help=help_text or "Upload receipt (PDF, JPG, PNG - Max 5MB)",
        key=key
    )

def show_status_badge(status: str) -> str:
    """Display status badge with appropriate color"""
    status_colors = {
        'active': '🟢',
        'inactive': '🔴',
        'pending': '🟡',
        'completed': '✅',
        'cancelled': '❌',
        'approved': '✅',
        'rejected': '❌'
    }
    
    color = status_colors.get(status.lower(), '⚪')
    return f"{color} {status.title()}"

def show_role_badge(role: str) -> str:
    """Display role badge"""
    role_icons = {
        'admin': '👑',
        'staff': '👤',
        'public': '👁️'
    }
    
    icon = role_icons.get(role.lower(), '👤')
    return f"{icon} {role.title()}"

def show_loading_spinner(message: str = "Loading..."):
    """Show loading spinner"""
    with st.spinner(message):
        return True

def show_progress_bar(progress: float, text: str = ""):
    """Show progress bar"""
    st.progress(progress, text=text)

def show_info_box(title: str, content: str, type: str = "info"):
    """Show information box"""
    if type == "info":
        st.info(f"**{title}**\n\n{content}")
    elif type == "warning":
        st.warning(f"**{title}**\n\n{content}")
    elif type == "error":
        st.error(f"**{title}**\n\n{content}")
    elif type == "success":
        st.success(f"**{title}**\n\n{content}")

def show_expandable_section(title: str, content_func, expanded: bool = False):
    """Show expandable section"""
    with st.expander(title, expanded=expanded):
        content_func()

def format_currency_input(amount: float) -> str:
    """Format currency for input display"""
    config = get_business_config()
    return f"{config['currency_symbol']}{amount:.2f}"

def show_quick_actions(actions: List[Dict[str, Any]]):
    """Show quick action buttons"""
    if not actions:
        return
    
    st.subheader("Quick Actions")
    
    # Create columns for actions
    cols = st.columns(len(actions))
    
    for i, action in enumerate(actions):
        with cols[i]:
            if st.button(
                action['label'],
                key=action.get('key', f"action_{i}"),
                help=action.get('help'),
                type=action.get('type', 'secondary')
            ):
                if 'callback' in action:
                    action['callback']()

def show_kpi_dashboard(kpis: List[Dict[str, Any]]):
    """Show KPI dashboard"""
    if not kpis:
        return
    
    # Create columns for KPIs
    cols = st.columns(len(kpis))
    
    for i, kpi in enumerate(kpis):
        with cols[i]:
            show_metric_card(
                title=kpi['title'],
                value=kpi['value'],
                delta=kpi.get('delta'),
                help_text=kpi.get('help')
            )

def show_receipt_preview(receipt_path: str):
    """Show receipt preview if available"""
    if not receipt_path:
        return
    
    try:
        import os
        if os.path.exists(receipt_path):
            with st.expander("📄 Receipt"):
                if receipt_path.lower().endswith(('.jpg', '.jpeg', '.png')):
                    st.image(receipt_path, caption="Receipt", use_column_width=True)
                else:
                    st.write(f"Receipt file: {os.path.basename(receipt_path)}")
                    st.download_button(
                        "Download Receipt",
                        data=open(receipt_path, 'rb').read(),
                        file_name=os.path.basename(receipt_path),
                        mime="application/octet-stream"
                    )
    except Exception as e:
        st.warning(f"Could not load receipt: {e}")

def show_printable_receipt(transaction_data: Dict[str, Any]):
    """Show printable receipt"""
    config = get_business_config()
    
    with st.container():
        st.markdown("---")
        st.markdown("### 🧾 Receipt")
        
        # Receipt header
        st.markdown(f"""
        **{config['name']}**  
        {config['location']}  
        
        **Transaction ID:** {transaction_data.get('id', 'N/A')}  
        **Date:** {format_datetime(transaction_data.get('created_at', datetime.now()))}  
        **Staff:** {transaction_data.get('staff_name', 'N/A')}  
        """)
        
        # Transaction details
        st.markdown("**Transaction Details:**")
        st.markdown(f"""
        - Customer: {transaction_data.get('customer_name', 'Walk-in')}
        - Gallons: {transaction_data.get('gallons_count', 0)}
        - Price per gallon: {format_money(transaction_data.get('price_per_gallon', 0))}
        - Payment method: {transaction_data.get('payment_type', 'Cash')}
        """)
        
        # Total
        st.markdown(f"**Total Amount: {format_money(transaction_data.get('total_amount', 0))}**")
        
        st.markdown("---")
        st.caption("Thank you for your business! 💧")
        
        # Print button (placeholder - would need browser print functionality)
        if st.button("🖨️ Print Receipt"):
            st.info("Use your browser's print function (Ctrl+P) to print this receipt.")
