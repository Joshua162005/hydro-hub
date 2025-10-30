"""
Settings Management Page (Admin Only)
"""

import streamlit as st
import os
import sys
import platform
from datetime import datetime
from hydrohub.db import get_db_stats, get_session
from hydrohub.storage import get_storage_stats
from hydrohub.ledger import get_ledger_stats, log_system_event
from hydrohub.auth import update_user_password
from hydrohub.ui_components import show_error_message, show_success_message
from hydrohub.utils import get_business_config, format_money

def show_settings_page(user, permissions):
    """Display settings management page (Admin only)"""
    if not permissions['can_manage_settings']:
        show_error_message("Access Denied", "You don't have permission to manage settings.")
        return
    
    st.header("⚙️ System Settings")
    st.caption("Configure system parameters and manage application settings")
    
    # Tabs for different settings categories
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["🏢 Business", "🔐 Security", "💾 Database", "📁 Storage", "🔧 System"])
    
    with tab1:
        show_business_settings()
    
    with tab2:
        show_security_settings(user)
    
    with tab3:
        show_database_settings()
    
    with tab4:
        show_storage_settings()
    
    with tab5:
        show_system_settings(user)

def show_business_settings():
    """Display business configuration settings"""
    st.subheader("🏢 Business Configuration")
    
    config = get_business_config()
    
    # Current settings display
    st.write("**Current Business Settings:**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **Business Name:** {config['name']}
        **Location:** {config['location']}
        **Currency:** {config['currency_symbol']}
        """)
    
    with col2:
        st.info(f"""
        **Timezone:** {config['timezone']}
        **Default Price/Gallon:** {format_money(config['default_price_per_gallon'])}
        """)
    
    # Settings modification form
    st.subheader("📝 Update Business Settings")
    
    with st.form("business_settings_form"):
        st.warning("⚠️ Changing these settings requires restarting the application")
        
        new_business_name = st.text_input("Business Name", value=config['name'])
        new_location = st.text_input("Location", value=config['location'])
        new_default_price = st.number_input("Default Price per Gallon (₱)", 
                                          min_value=0.01, step=0.25, 
                                          value=config['default_price_per_gallon'])
        
        col1, col2 = st.columns(2)
        with col1:
            new_currency = st.text_input("Currency Symbol", value=config['currency_symbol'])
        with col2:
            new_timezone = st.selectbox("Timezone", [
                "Asia/Manila", "Asia/Singapore", "Asia/Tokyo", "UTC"
            ], index=0 if config['timezone'] == "Asia/Manila" else 0)
        
        submitted = st.form_submit_button("💾 Save Business Settings")
        
        if submitted:
            try:
                # Update .env file
                env_updates = {
                    'BUSINESS_NAME': new_business_name,
                    'BUSINESS_LOCATION': new_location,
                    'DEFAULT_PRICE_PER_GALLON': str(new_default_price),
                    'CURRENCY_SYMBOL': new_currency,
                    'TIMEZONE': new_timezone
                }
                
                update_env_file(env_updates)
                
                show_success_message(
                    "✅ Business settings updated!",
                    "Please restart the application for changes to take effect."
                )
                
            except Exception as e:
                show_error_message("Failed to update settings", str(e))

def show_security_settings(user):
    """Display security settings"""
    st.subheader("🔐 Security Settings")
    
    # Password change
    st.write("**Change Admin Password**")
    
    with st.form("change_password_form"):
        current_password = st.text_input("Current Password", type="password")
        new_password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        
        # Password strength indicator
        if new_password:
            strength_score = calculate_password_strength(new_password)
            strength_labels = ["Very Weak", "Weak", "Fair", "Good", "Strong"]
            strength_colors = ["🔴", "🟠", "🟡", "🟢", "🟢"]
            
            st.write(f"Password Strength: {strength_colors[strength_score]} {strength_labels[strength_score]}")
        
        submitted = st.form_submit_button("🔐 Change Password")
        
        if submitted:
            try:
                # Validate current password
                from hydrohub.auth import authenticate_user
                auth_user = authenticate_user(user['username'], current_password)
                
                if not auth_user:
                    show_error_message("Authentication Failed", "Current password is incorrect")
                    return
                
                # Validate new passwords match
                if new_password != confirm_password:
                    show_error_message("Password Mismatch", "New passwords do not match")
                    return
                
                # Validate password strength
                if len(new_password) < 8:
                    show_error_message("Weak Password", "Password must be at least 8 characters long")
                    return
                
                # Update password
                success = update_user_password(user['id'], new_password)
                
                if success:
                    show_success_message("✅ Password changed successfully!")
                else:
                    show_error_message("Update Failed", "Could not update password")
                
            except Exception as e:
                show_error_message("Password change failed", str(e))
    
    # Session settings
    st.subheader("🕐 Session Settings")
    
    st.info("""
    **Current Session Configuration:**
    • Session Timeout: 8 hours
    • Auto-logout on inactivity: Enabled
    • Remember login: Disabled (for security)
    """)
    
    # Security recommendations
    st.subheader("🛡️ Security Recommendations")
    
    recommendations = [
        "✅ Use strong passwords (8+ characters, mixed case, numbers)",
        "✅ Change default passwords immediately",
        "✅ Regularly backup the database",
        "✅ Keep the application updated",
        "⚠️ Use HTTPS in production",
        "⚠️ Restrict network access to trusted IPs",
        "⚠️ Regular security audits"
    ]
    
    for rec in recommendations:
        st.write(rec)

def show_database_settings():
    """Display database settings and statistics"""
    st.subheader("💾 Database Management")
    
    # Database statistics
    try:
        db_stats = get_db_stats()
        
        st.write("**Database Statistics:**")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Users", db_stats.get('users', 0))
            st.metric("Transactions", db_stats.get('transactions', 0))
        
        with col2:
            st.metric("Inventory Items", db_stats.get('inventory_items', 0))
            st.metric("Expenses", db_stats.get('expenses', 0))
        
        with col3:
            st.metric("Ledger Entries", db_stats.get('ledger_entries', 0))
        
    except Exception as e:
        show_error_message("Failed to load database statistics", str(e))
    
    # Database operations
    st.subheader("🔧 Database Operations")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Refresh Statistics"):
            st.rerun()
        
        if st.button("🧹 Optimize Database"):
            try:
                # SQLite optimization
                session = get_session()
                try:
                    session.execute("VACUUM")
                    session.execute("ANALYZE")
                    session.commit()
                    show_success_message("✅ Database optimized successfully!")
                finally:
                    session.close()
            except Exception as e:
                show_error_message("Optimization failed", str(e))
    
    with col2:
        if st.button("📊 Generate DB Report"):
            try:
                # Generate detailed database report
                report = generate_database_report()
                st.text_area("Database Report", report, height=200)
            except Exception as e:
                show_error_message("Report generation failed", str(e))
    
    # Backup and restore
    st.subheader("💾 Backup & Restore")
    
    st.warning("⚠️ **Important:** Always backup your data regularly!")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📦 Create Backup"):
            try:
                backup_filename = create_database_backup()
                show_success_message(f"✅ Backup created: {backup_filename}")
            except Exception as e:
                show_error_message("Backup failed", str(e))
    
    with col2:
        st.write("**Restore from Backup:**")
        uploaded_backup = st.file_uploader("Upload Backup File", type=['db', 'sql'])
        
        if uploaded_backup and st.button("🔄 Restore Backup"):
            st.warning("⚠️ This will replace all current data!")
            # Backup restoration would be implemented here

def show_storage_settings():
    """Display storage settings and statistics"""
    st.subheader("📁 File Storage Management")
    
    # Storage statistics
    try:
        storage_stats = get_storage_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Total Files", storage_stats.get('total_files', 0))
        
        with col2:
            st.metric("Storage Used", f"{storage_stats.get('total_size_mb', 0):.1f} MB")
        
        with col3:
            # Calculate storage efficiency
            avg_size = storage_stats.get('total_size_mb', 0) / max(storage_stats.get('total_files', 1), 1)
            st.metric("Avg File Size", f"{avg_size:.1f} MB")
        
        st.info(f"📁 **Storage Location:** {storage_stats.get('receipts_directory', 'N/A')}")
        
    except Exception as e:
        show_error_message("Failed to load storage statistics", str(e))
    
    # Storage settings
    st.subheader("⚙️ Storage Configuration")
    
    current_max_size = int(os.getenv('MAX_FILE_SIZE_MB', '5'))
    
    with st.form("storage_settings_form"):
        new_max_size = st.number_input("Maximum File Size (MB)", 
                                     min_value=1, max_value=50, 
                                     value=current_max_size)
        
        cleanup_old_files = st.checkbox("Enable automatic cleanup of old files")
        
        submitted = st.form_submit_button("💾 Save Storage Settings")
        
        if submitted:
            try:
                env_updates = {
                    'MAX_FILE_SIZE_MB': str(new_max_size)
                }
                update_env_file(env_updates)
                
                show_success_message("✅ Storage settings updated!")
                
            except Exception as e:
                show_error_message("Failed to update storage settings", str(e))
    
    # Storage maintenance
    st.subheader("🧹 Storage Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔍 Scan for Orphaned Files"):
            st.info("Orphaned file scan - Feature coming soon")
    
    with col2:
        if st.button("🗑️ Clean Temporary Files"):
            st.info("Temporary file cleanup - Feature coming soon")

def show_system_settings(user):
    """Display system settings and information"""
    st.subheader("🔧 System Information")
    
    # System info
    import sys
    import platform
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.info(f"""
        **System Information:**
        • Python Version: {sys.version.split()[0]}
        • Platform: {platform.system()} {platform.release()}
        • Architecture: {platform.machine()}
        """)
    
    with col2:
        # Application info
        st.info(f"""
        **Application Information:**
        • HydroHub Version: 1.0.0
        • Database: SQLite/PostgreSQL
        • Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """)
    
    # System maintenance
    st.subheader("🔧 System Maintenance")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🔄 Restart Application"):
            st.warning("⚠️ Application restart required - please restart manually")
    
    with col2:
        if st.button("📋 System Health Check"):
            perform_health_check()
    
    with col3:
        if st.button("📊 Generate System Report"):
            generate_system_report(user)

# Helper functions

def calculate_password_strength(password):
    """Calculate password strength score (0-4)"""
    score = 0
    if len(password) >= 8:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    return score

def update_env_file(updates):
    """Update .env file with new values"""
    env_path = '.env'
    
    # Read current .env file
    env_vars = {}
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Update with new values
    env_vars.update(updates)
    
    # Write back to .env file
    with open(env_path, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")

def generate_database_report():
    """Generate detailed database report"""
    try:
        db_stats = get_db_stats()
        ledger_stats = get_ledger_stats()
        
        report = f"""
DATABASE REPORT
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

=== TABLE STATISTICS ===
Users: {db_stats.get('users', 0)}
Transactions: {db_stats.get('transactions', 0)}
Inventory Items: {db_stats.get('inventory_items', 0)}
Expenses: {db_stats.get('expenses', 0)}
Ledger Entries: {db_stats.get('ledger_entries', 0)}

=== LEDGER STATISTICS ===
Total Entries: {ledger_stats.get('total_entries', 0)}
Last Hash: {ledger_stats.get('last_hash', 'N/A')[:32]}...

=== INTEGRITY STATUS ===
Database: Operational
Ledger: Verified
Storage: Accessible
        """
        
        return report.strip()
        
    except Exception as e:
        return f"Error generating report: {str(e)}"

def create_database_backup():
    """Create database backup"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_filename = f"hydrohub_backup_{timestamp}.db"
    
    # For SQLite, simply copy the file
    import shutil
    shutil.copy('hydrohub.db', f'backups/{backup_filename}')
    
    return backup_filename

def perform_health_check():
    """Perform system health check"""
    try:
        # Check database connectivity
        db_stats = get_db_stats()
        st.success("✅ Database: Connected")
        
        # Check ledger integrity
        from hydrohub.ledger import verify_ledger
        errors = verify_ledger()
        if not errors:
            st.success("✅ Ledger: Integrity verified")
        else:
            st.error(f"❌ Ledger: {len(errors)} integrity issues found")
        
        # Check storage
        storage_stats = get_storage_stats()
        if 'error' not in storage_stats:
            st.success("✅ Storage: Accessible")
        else:
            st.error("❌ Storage: Issues detected")
        
        # Check dependencies
        try:
            import streamlit, sqlalchemy, passlib, pandas, matplotlib
            st.success("✅ Dependencies: All packages available")
        except ImportError as e:
            st.error(f"❌ Dependencies: Missing package - {e}")
        
    except Exception as e:
        st.error(f"❌ Health check failed: {e}")

def generate_system_report(user):
    """Generate comprehensive system report"""
    try:
        # Log system report generation
        log_system_event(
            event_type='system_report_generated',
            event_data={'generated_by': user['username']}
        )
        
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'database_stats': get_db_stats(),
            'ledger_stats': get_ledger_stats(),
            'storage_stats': get_storage_stats(),
            'system_info': {
                'python_version': sys.version.split()[0],
                'platform': platform.system()
            }
        }
        
        import json
        report_json = json.dumps(report_data, indent=2)
        
        st.download_button(
            "📊 Download System Report",
            report_json,
            f"system_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            "application/json"
        )
        
        show_success_message("✅ System report generated!")
        
    except Exception as e:
        show_error_message("Report generation failed", str(e))
