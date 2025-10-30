"""
Inventory Management Page
"""

import streamlit as st
from datetime import datetime
from hydrohub.models import InventoryItem
from hydrohub.db import get_session
from hydrohub.validations import validate_inventory_item, ValidationError
from hydrohub.ledger import log_inventory_change
from hydrohub.ui_components import show_error_message, show_success_message, show_data_table
from hydrohub.utils import format_money, get_current_time

def show_inventory_page(user, permissions):
    """Display inventory management page"""
    st.header("📦 Inventory Management")
    
    # Tabs for different inventory operations
    tab1, tab2, tab3 = st.tabs(["📋 Current Inventory", "➕ Add Item", "🔄 Adjust Stock"])
    
    with tab1:
        show_current_inventory()
    
    with tab2:
        show_add_item_form(user)
    
    with tab3:
        show_adjust_stock_form(user)

def show_current_inventory():
    """Display current inventory status"""
    session = get_session()
    try:
        items = session.query(InventoryItem).all()
        
        if not items:
            st.info("No inventory items found. Add some items to get started.")
            return
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        
        total_items = len(items)
        total_value = sum(item.quantity * item.unit_cost for item in items)
        low_stock_items = [item for item in items if item.quantity <= 10]
        categories = len(set(item.category for item in items))
        
        with col1:
            st.metric("Total Items", total_items)
        with col2:
            st.metric("Total Value", format_money(total_value))
        with col3:
            st.metric("Low Stock Items", len(low_stock_items))
        with col4:
            st.metric("Categories", categories)
        
        # Low stock alerts
        if low_stock_items:
            st.warning("⚠️ **Low Stock Alert**")
            for item in low_stock_items:
                st.write(f"• {item.name}: {item.quantity} {item.category}")
        
        # Inventory table
        st.subheader("📋 Inventory Items")
        
        # Prepare data for display
        inventory_data = []
        for item in items:
            inventory_data.append({
                'ID': item.id,
                'Name': item.name,
                'Category': item.category,
                'Quantity': item.quantity,
                'Unit Cost': format_money(item.unit_cost),
                'Total Value': format_money(item.quantity * item.unit_cost),
                'Location': item.location or 'N/A',
                'Last Updated': item.last_updated.strftime('%Y-%m-%d %H:%M')
            })
        
        # Display table
        if inventory_data:
            st.dataframe(inventory_data, use_container_width=True)
        
        # Category breakdown chart
        if items:
            st.subheader("📊 Inventory by Category")
            category_data = {}
            for item in items:
                if item.category not in category_data:
                    category_data[item.category] = {'quantity': 0, 'value': 0}
                category_data[item.category]['quantity'] += item.quantity
                category_data[item.category]['value'] += item.quantity * item.unit_cost
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Quantity by Category**")
                for category, data in category_data.items():
                    st.write(f"• {category}: {data['quantity']} items")
            
            with col2:
                st.write("**Value by Category**")
                for category, data in category_data.items():
                    st.write(f"• {category}: {format_money(data['value'])}")
        
    finally:
        session.close()

def show_add_item_form(user):
    """Display add new inventory item form"""
    st.subheader("➕ Add New Inventory Item")
    
    with st.form("add_item_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Item Name*", placeholder="e.g., Water Filters")
            category = st.selectbox("Category*", [
                "Water", "Containers", "Equipment", "Supplies", "Filters", "Other"
            ])
            quantity = st.number_input("Initial Quantity*", min_value=0, step=1, value=0)
        
        with col2:
            unit_cost = st.number_input("Unit Cost (₱)*", min_value=0.0, step=0.25, value=0.0)
            location = st.text_input("Location", placeholder="e.g., Main Storage")
        
        submitted = st.form_submit_button("Add Item", type="primary")
        
        if submitted:
            try:
                # Validate data
                data = {
                    'name': name,
                    'category': category,
                    'quantity': quantity,
                    'unit_cost': unit_cost,
                    'location': location
                }
                validated_data = validate_inventory_item(data)
                
                # Save to database
                session = get_session()
                try:
                    item = InventoryItem(**validated_data)
                    session.add(item)
                    session.commit()
                    session.refresh(item)
                    
                    # Log to ledger
                    log_inventory_change(
                        actor_id=user['id'],
                        item_id=item.id,
                        change_data={
                            'item_name': item.name,
                            'change_type': 'item_added',
                            'quantity': item.quantity,
                            'unit_cost': item.unit_cost
                        }
                    )
                    
                    show_success_message(
                        f"✅ Item '{name}' added successfully!",
                        f"ID: {item.id} | Quantity: {quantity} | Value: {format_money(quantity * unit_cost)}"
                    )
                    
                finally:
                    session.close()
                    
            except ValidationError as e:
                show_error_message("Validation Error", str(e))
            except Exception as e:
                show_error_message("Failed to add item", str(e))

def show_adjust_stock_form(user):
    """Display stock adjustment form"""
    st.subheader("🔄 Adjust Stock Levels")
    
    # Get current items for selection
    session = get_session()
    try:
        items = session.query(InventoryItem).all()
        
        if not items:
            st.info("No inventory items available. Add some items first.")
            return
        
        # Create item selection options
        item_options = {f"{item.name} (Current: {item.quantity})": item.id for item in items}
        
        with st.form("adjust_stock_form"):
            selected_item_key = st.selectbox("Select Item*", list(item_options.keys()))
            selected_item_id = item_options[selected_item_key]
            
            # Get current item details
            selected_item = session.query(InventoryItem).filter(InventoryItem.id == selected_item_id).first()
            
            if selected_item:
                st.info(f"**Current Stock:** {selected_item.quantity} | **Unit Cost:** {format_money(selected_item.unit_cost)}")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    adjustment_type = st.selectbox("Adjustment Type*", [
                        "Add Stock", "Remove Stock", "Set Quantity", "Mark Damaged"
                    ])
                
                with col2:
                    if adjustment_type == "Set Quantity":
                        new_quantity = st.number_input("New Quantity*", min_value=0, step=1, value=selected_item.quantity)
                        adjustment_amount = new_quantity - selected_item.quantity
                    else:
                        adjustment_amount = st.number_input("Adjustment Amount*", min_value=1, step=1, value=1)
                        if adjustment_type == "Remove Stock" or adjustment_type == "Mark Damaged":
                            adjustment_amount = -adjustment_amount
                        new_quantity = selected_item.quantity + adjustment_amount
                
                reason = st.text_area("Reason for Adjustment", placeholder="e.g., Received new shipment, Damaged items, etc.")
                
                # Show preview
                st.write(f"**Preview:** {selected_item.quantity} → {max(0, new_quantity)}")
                
                submitted = st.form_submit_button("Apply Adjustment", type="primary")
                
                if submitted:
                    try:
                        if new_quantity < 0:
                            show_error_message("Invalid adjustment", "Resulting quantity cannot be negative")
                            return
                        
                        # Update database
                        session = get_session()
                        try:
                            item = session.query(InventoryItem).filter(InventoryItem.id == selected_item_id).first()
                            old_quantity = item.quantity
                            item.quantity = max(0, new_quantity)
                            item.last_updated = get_current_time()
                            session.commit()
                            
                            # Log to ledger
                            log_inventory_change(
                                actor_id=user['id'],
                                item_id=item.id,
                                change_data={
                                    'item_name': item.name,
                                    'change_type': adjustment_type.lower().replace(' ', '_'),
                                    'old_quantity': old_quantity,
                                    'new_quantity': item.quantity,
                                    'adjustment_amount': adjustment_amount,
                                    'reason': reason
                                }
                            )
                            
                            show_success_message(
                                f"✅ Stock adjusted successfully!",
                                f"{item.name}: {old_quantity} → {item.quantity} ({adjustment_amount:+d})"
                            )
                            
                        finally:
                            session.close()
                            
                    except Exception as e:
                        show_error_message("Failed to adjust stock", str(e))
        
    finally:
        session.close()
