"""
Ledger Management Page (Admin Only)
"""

import streamlit as st
import json
from datetime import datetime, date
from hydrohub.models import Ledger, User
from hydrohub.db import get_session
from hydrohub.ledger import verify_ledger, get_ledger_entries, export_ledger_proof, get_ledger_stats
from hydrohub.ui_components import (
    show_error_message, show_success_message, show_date_range_picker
)
from hydrohub.utils import format_datetime

def show_ledger_page(user, permissions):
    """Display ledger management page (Admin only)"""
    if not permissions['can_view_ledger']:
        show_error_message("Access Denied", "You don't have permission to view the ledger.")
        return
    
    st.header("🔗 Blockchain Ledger")
    st.caption("Immutable transaction log for transparency and audit trail")
    
    # Tabs for different ledger operations
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Recent Entries", "🔍 Verify Integrity", "📊 Statistics", "📤 Export"])
    
    with tab1:
        show_recent_entries()
    
    with tab2:
        show_verify_integrity()
    
    with tab3:
        show_ledger_statistics()
    
    with tab4:
        show_export_ledger(user)

def show_recent_entries():
    """Display recent ledger entries"""
    st.subheader("📋 Recent Ledger Entries")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        limit = st.selectbox("Show entries", [50, 100, 200, 500], index=1)
    
    with col2:
        action_filter = st.selectbox("Action Type", ["All", "refill_transaction", "expense", "inventory_change", "user_action", "system_event"])
    
    with col3:
        # Get users for actor filter
        session = get_session()
        try:
            users = session.query(User).all()
            user_options = ["All"] + [f"{u.username} (ID: {u.id})" for u in users]
            actor_filter = st.selectbox("Actor", user_options)
        finally:
            session.close()
    
    # Get filtered entries
    try:
        action_type = None if action_filter == "All" else action_filter
        actor_id = None
        
        if actor_filter != "All" and "ID: " in actor_filter:
            try:
                # Extract actor ID from selection
                actor_id = int(actor_filter.split("ID: ")[1].split(")")[0])
            except (ValueError, IndexError):
                actor_id = None
        
        entries = get_ledger_entries(
            limit=limit,
            action_type=action_type,
            actor_id=actor_id
        )
        
        if not entries:
            st.info("No ledger entries found matching the criteria.")
            return
        
        # Display entries
        for entry in entries:
            with st.expander(f"#{entry.id} - {entry.action_type} ({format_datetime(entry.timestamp)})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Entry ID:** {entry.id}")
                    st.write(f"**Timestamp:** {format_datetime(entry.timestamp)}")
                    st.write(f"**Action Type:** {entry.action_type}")
                    
                    # Handle actor information
                    if entry.actor_id:
                        st.write(f"**Actor:** User ID {entry.actor_id}")
                    else:
                        st.write("**Actor:** System")
                
                with col2:
                    st.write(f"**Previous Hash:** `{entry.prev_hash[:16]}...`")
                    st.write(f"**Data Hash:** `{entry.data_hash[:16]}...`")
                
                # Parse and display data
                try:
                    data = json.loads(entry.data_text)
                    st.write("**Data:**")
                    
                    if 'human_message' in data:
                        st.info(f"📝 {data['human_message']}")
                    
                    if 'payload' in data:
                        st.json(data['payload'])
                    else:
                        st.json(data)
                        
                except json.JSONDecodeError:
                    st.write("**Raw Data:**")
                    st.code(entry.data_text)
    
    except Exception as e:
        show_error_message("Failed to load ledger entries", str(e))

def show_verify_integrity():
    """Display ledger integrity verification"""
    st.subheader("🔍 Verify Ledger Integrity")
    st.write("Check the cryptographic integrity of the entire ledger chain.")
    
    if st.button("🔍 Verify Ledger Chain", type="primary"):
        with st.spinner("Verifying ledger integrity..."):
            try:
                errors = verify_ledger()
                
                if not errors:
                    st.success("✅ **Ledger Integrity Verified!**")
                    st.info("All entries are cryptographically valid and the chain is intact.")
                    
                    # Show verification details
                    stats = get_ledger_stats()
                    st.write("**Verification Details:**")
                    st.write(f"• Total entries verified: {stats['total_entries']}")
                    st.write(f"• Chain head hash: `{stats['last_hash'][:32]}...`")
                    if stats['first_entry_time']:
                        st.write(f"• First entry: {format_datetime(stats['first_entry_time'])}")
                    if stats['last_entry_time']:
                        st.write(f"• Last entry: {format_datetime(stats['last_entry_time'])}")
                
                else:
                    st.error(f"❌ **Ledger Integrity Issues Found!** ({len(errors)} issues)")
                    st.warning("The ledger chain has been tampered with or corrupted.")
                    
                    # Show error details
                    st.write("**Issues Found:**")
                    for i, error in enumerate(errors, 1):
                        with st.expander(f"Issue #{i} - Entry ID {error['entry_id']}"):
                            st.write(f"**Error Type:** {error['error']}")
                            if 'expected' in error:
                                st.write(f"**Expected:** `{error['expected']}`")
                            if 'actual' in error:
                                st.write(f"**Actual:** `{error['actual']}`")
                            if 'data' in error:
                                st.code(error['data'])
                    
                    # Provide recommendations
                    st.write("**Recommended Actions:**")
                    st.write("1. 🚨 Stop all operations immediately")
                    st.write("2. 📞 Contact system administrator")
                    st.write("3. 💾 Create backup of current database")
                    st.write("4. 🔍 Investigate the source of tampering")
                    
            except Exception as e:
                show_error_message("Verification failed", str(e))
    
    # Additional verification tools
    st.subheader("🛠️ Advanced Verification")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 Generate Integrity Report"):
            try:
                stats = get_ledger_stats()
                errors = verify_ledger()
                
                st.write("**Ledger Integrity Report**")
                st.write(f"Generated: {format_datetime(datetime.utcnow())}")
                st.write("---")
                st.write(f"Total Entries: {stats['total_entries']}")
                st.write(f"Integrity Status: {'✅ VALID' if not errors else '❌ COMPROMISED'}")
                st.write(f"Issues Found: {len(errors)}")
                
                if stats['action_counts']:
                    st.write("\n**Action Type Distribution:**")
                    for action_type, count in stats['action_counts'].items():
                        st.write(f"• {action_type}: {count}")
                
            except Exception as e:
                show_error_message("Report generation failed", str(e))
    
    with col2:
        if st.button("🔗 Verify Specific Entry"):
            entry_id = st.number_input("Entry ID to verify", min_value=1, step=1)
            if entry_id:
                # This would implement single entry verification
                st.info("Single entry verification - Feature coming soon")

def show_ledger_statistics():
    """Display ledger statistics and analytics"""
    st.subheader("📊 Ledger Statistics")
    
    try:
        stats = get_ledger_stats()
        
        if stats['total_entries'] == 0:
            st.info("No ledger entries found.")
            return
        
        # Overview metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Entries", stats['total_entries'])
        
        with col2:
            if stats['first_entry_time'] and stats['last_entry_time']:
                first_time = datetime.fromisoformat(stats['first_entry_time'].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(stats['last_entry_time'].replace('Z', '+00:00'))
                days_active = (last_time - first_time).days + 1
                st.metric("Days Active", days_active)
            else:
                st.metric("Days Active", "N/A")
        
        with col3:
            if stats['total_entries'] > 0 and stats['first_entry_time'] and stats['last_entry_time']:
                first_time = datetime.fromisoformat(stats['first_entry_time'].replace('Z', '+00:00'))
                last_time = datetime.fromisoformat(stats['last_entry_time'].replace('Z', '+00:00'))
                hours = (last_time - first_time).total_seconds() / 3600
                entries_per_hour = stats['total_entries'] / hours if hours > 0 else 0
                st.metric("Entries/Hour", f"{entries_per_hour:.2f}")
            else:
                st.metric("Entries/Hour", "N/A")
        
        with col4:
            st.metric("Chain Head", f"{stats['last_hash'][:8]}...")
        
        # Action type breakdown
        if stats['action_counts']:
            st.subheader("📈 Activity Breakdown")
            
            # Create a simple bar chart using Streamlit
            action_data = []
            for action_type, count in stats['action_counts'].items():
                action_data.append({
                    'Action Type': action_type.replace('_', ' ').title(),
                    'Count': count,
                    'Percentage': (count / stats['total_entries']) * 100
                })
            
            # Sort by count
            action_data.sort(key=lambda x: x['Count'], reverse=True)
            
            for data in action_data:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"**{data['Action Type']}**")
                with col2:
                    st.write(f"{data['Count']}")
                with col3:
                    st.write(f"{data['Percentage']:.1f}%")
        
        # Timeline information
        st.subheader("⏰ Timeline")
        
        if stats['first_entry_time']:
            st.write(f"**First Entry:** {format_datetime(stats['first_entry_time'])}")
        if stats['last_entry_time']:
            st.write(f"**Last Entry:** {format_datetime(stats['last_entry_time'])}")
        
        # Hash information
        st.subheader("🔐 Cryptographic Info")
        st.write(f"**Current Chain Head:** `{stats['last_hash']}`")
        st.write("**Hash Algorithm:** SHA-256")
        st.write("**Chain Format:** timestamp|prev_hash|actor_id|data_text")
        
    except Exception as e:
        show_error_message("Failed to load statistics", str(e))

def show_export_ledger(user):
    """Display ledger export options"""
    st.subheader("📤 Export Ledger")
    st.write("Export ledger entries for external verification or backup.")
    
    # Export options
    col1, col2 = st.columns(2)
    
    with col1:
        export_format = st.selectbox("Export Format", ["CSV", "JSON"])
        include_proof = st.checkbox("Include Cryptographic Proof", value=True)
    
    with col2:
        # Date range for export
        use_date_filter = st.checkbox("Filter by Date Range")
        
        if use_date_filter:
            start_date, end_date = show_date_range_picker("export")
        else:
            start_date = end_date = None
    
    if st.button("📤 Export Ledger", type="primary"):
        try:
            with st.spinner("Generating export..."):
                if export_format == "JSON":
                    # Export as JSON with proof
                    start_iso = start_date.isoformat() + 'T00:00:00Z' if start_date else None
                    end_iso = end_date.isoformat() + 'T23:59:59Z' if end_date else None
                    
                    proof = export_ledger_proof(start_iso, end_iso)
                    
                    if include_proof:
                        export_data = json.dumps(proof, indent=2)
                        filename = f"ledger_proof_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    else:
                        # Export just the entries
                        entries_only = {
                            'export_timestamp': proof['export_timestamp'],
                            'total_entries': proof['total_entries'],
                            'entries': proof['entries']
                        }
                        export_data = json.dumps(entries_only, indent=2)
                        filename = f"ledger_entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    
                    st.download_button(
                        "💾 Download JSON",
                        export_data,
                        filename,
                        "application/json"
                    )
                
                else:  # CSV format
                    from hydrohub.reports import export_ledger_csv
                    
                    csv_data = export_ledger_csv(start_date, end_date, user['id'])
                    filename = f"ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                    
                    st.download_button(
                        "💾 Download CSV",
                        csv_data,
                        filename,
                        "text/csv"
                    )
                
                st.success("✅ Export generated successfully!")
                
                # Show export summary
                if 'proof' in locals():
                    st.info(f"📊 Exported {proof['total_entries']} entries")
                    if include_proof:
                        st.info(f"🔐 Proof hash: `{proof['proof_hash'][:32]}...`")
        
        except Exception as e:
            show_error_message("Export failed", str(e))
    
    # Export instructions
    st.subheader("📋 Export Information")
    
    with st.expander("ℹ️ About Ledger Exports"):
        st.write("""
        **CSV Export:**
        - Human-readable format
        - Suitable for spreadsheet analysis
        - Includes all entry details
        
        **JSON Export:**
        - Machine-readable format
        - Preserves exact data structure
        - Can include cryptographic proof
        
        **Cryptographic Proof:**
        - Enables independent verification
        - Contains hash chain validation data
        - Proves ledger integrity at export time
        
        **Verification:**
        - Exported data can be verified independently
        - Hash chains can be reconstructed and validated
        - Tamper detection is preserved in exports
        """)
    
    # Verification tools
    st.subheader("🔍 Verify Exported Data")
    
    uploaded_file = st.file_uploader("Upload Ledger Export for Verification", type=['json', 'csv'])
    
    if uploaded_file and st.button("🔍 Verify Upload"):
        try:
            if uploaded_file.name.endswith('.json'):
                import json
                data = json.load(uploaded_file)
                
                if 'proof_hash' in data and 'entries' in data:
                    # Verify the proof hash
                    entries_json = json.dumps({
                        'export_timestamp': data['export_timestamp'],
                        'filter_start_date': data.get('filter_start_date'),
                        'filter_end_date': data.get('filter_end_date'),
                        'total_entries': data['total_entries'],
                        'entries': data['entries'],
                        'verification_info': data['verification_info']
                    }, sort_keys=True, separators=(',', ':'))
                    
                    import hashlib
                    computed_hash = hashlib.sha256(entries_json.encode('utf-8')).hexdigest()
                    
                    if computed_hash == data['proof_hash']:
                        st.success("✅ Export verification successful!")
                        st.info(f"📊 Verified {data['total_entries']} entries")
                    else:
                        st.error("❌ Export verification failed - data may be corrupted")
                else:
                    st.warning("⚠️ No cryptographic proof found in export")
            else:
                st.info("📄 CSV verification - basic format check only")
                # Basic CSV validation could be added here
                
        except Exception as e:
            show_error_message("Verification failed", str(e))
