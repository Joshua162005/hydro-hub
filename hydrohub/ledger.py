"""
Immutable ledger system for transaction tracking
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from hydrohub.db import get_session
from hydrohub.models import Ledger
from hydrohub.utils import get_current_time

def get_last_hash() -> str:
    """Get the hash of the last ledger entry"""
    session = get_session()
    try:
        last_entry = session.query(Ledger).order_by(Ledger.id.desc()).first()
        return last_entry.data_hash if last_entry else '0' * 64
    finally:
        session.close()

def create_data_hash(timestamp: str, prev_hash: str, actor_id: Optional[int], data_text: str) -> str:
    """Create hash for ledger entry"""
    payload = f"{timestamp}|{prev_hash}|{actor_id or ''}|{data_text}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def add_ledger_entry(
    actor_id: Optional[int],
    action_type: str,
    data_dict: Dict[str, Any],
    human_message: str = ""
) -> str:
    """
    Add an entry to the immutable ledger
    
    Args:
        actor_id: ID of the user performing the action (None for system actions)
        action_type: Type of action (e.g., 'refill', 'expense', 'inventory_adjust')
        data_dict: Dictionary containing action data
        human_message: Human-readable description of the action
    
    Returns:
        The hash of the created ledger entry
    """
    session = get_session()
    try:
        # Get previous hash
        prev_hash = get_last_hash()
        
        # Create timestamp in ISO format with timezone
        timestamp = datetime.utcnow().isoformat() + 'Z'
        
        # Create data structure
        ledger_data = {
            'action_type': action_type,
            'payload': data_dict,
            'human_message': human_message,
            'timestamp': timestamp
        }
        
        # Convert to JSON string
        data_text = json.dumps(ledger_data, sort_keys=True, separators=(',', ':'))
        
        # Create hash
        data_hash = create_data_hash(timestamp, prev_hash, actor_id, data_text)
        
        # Create ledger entry
        ledger_entry = Ledger(
            timestamp=timestamp,
            prev_hash=prev_hash,
            data_hash=data_hash,
            actor_id=actor_id,
            action_type=action_type,
            data_text=data_text
        )
        
        session.add(ledger_entry)
        session.commit()
        
        return data_hash
        
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def verify_ledger() -> List[Dict[str, Any]]:
    """
    Verify the integrity of the ledger chain
    
    Returns:
        List of inconsistencies found (empty list if ledger is intact)
    """
    session = get_session()
    try:
        entries = session.query(Ledger).order_by(Ledger.id.asc()).all()
        
        if not entries:
            return []  # Empty ledger is valid
        
        inconsistencies = []
        expected_prev_hash = '0' * 64
        
        for entry in entries:
            # Check if prev_hash matches expected
            if entry.prev_hash != expected_prev_hash:
                inconsistencies.append({
                    'entry_id': entry.id,
                    'error': 'prev_hash_mismatch',
                    'expected': expected_prev_hash,
                    'actual': entry.prev_hash
                })
            
            # Recompute hash and verify
            computed_hash = create_data_hash(
                entry.timestamp,
                entry.prev_hash,
                entry.actor_id,
                entry.data_text
            )
            
            if entry.data_hash != computed_hash:
                inconsistencies.append({
                    'entry_id': entry.id,
                    'error': 'hash_mismatch',
                    'expected': computed_hash,
                    'actual': entry.data_hash
                })
            
            # Verify JSON structure
            try:
                data = json.loads(entry.data_text)
                if 'action_type' not in data or 'payload' not in data:
                    inconsistencies.append({
                        'entry_id': entry.id,
                        'error': 'invalid_json_structure',
                        'data': entry.data_text[:100] + '...' if len(entry.data_text) > 100 else entry.data_text
                    })
            except json.JSONDecodeError:
                inconsistencies.append({
                    'entry_id': entry.id,
                    'error': 'invalid_json',
                    'data': entry.data_text[:100] + '...' if len(entry.data_text) > 100 else entry.data_text
                })
            
            # Set expected prev_hash for next iteration
            expected_prev_hash = entry.data_hash
        
        return inconsistencies
        
    finally:
        session.close()

def get_ledger_entries(
    limit: int = 100,
    offset: int = 0,
    action_type: Optional[str] = None,
    actor_id: Optional[int] = None
) -> List[Ledger]:
    """Get ledger entries with optional filtering"""
    session = get_session()
    try:
        # Simple query without relationships to avoid session issues
        query = session.query(Ledger).order_by(Ledger.id.desc())
        
        if action_type and action_type != "All":
            query = query.filter(Ledger.action_type == action_type)
        
        if actor_id and actor_id > 0:
            query = query.filter(Ledger.actor_id == actor_id)
        
        entries = query.offset(offset).limit(limit).all()
        
        # Create simple data objects to avoid session dependencies
        simple_entries = []
        for entry in entries:
            # Create a simple object with just the data we need
            simple_entry = type('SimpleEntry', (), {
                'id': entry.id,
                'timestamp': entry.timestamp,
                'action_type': entry.action_type,
                'actor_id': entry.actor_id,
                'prev_hash': entry.prev_hash,
                'data_hash': entry.data_hash,
                'data_text': entry.data_text
            })()
            simple_entries.append(simple_entry)
        
        return simple_entries
        
    except Exception as e:
        print(f"Error getting ledger entries: {e}")
        return []
    finally:
        session.close()

def get_ledger_stats() -> Dict[str, Any]:
    """Get ledger statistics"""
    session = get_session()
    try:
        total_entries = session.query(Ledger).count()
        
        # Get action type counts - fixed query
        action_counts = {}
        try:
            from sqlalchemy import func
            action_type_results = session.query(
                Ledger.action_type, 
                func.count(Ledger.action_type)
            ).group_by(Ledger.action_type).all()
            
            for action_type, count in action_type_results:
                action_counts[action_type] = count
        except Exception as e:
            print(f"Error getting action counts: {e}")
            action_counts = {}
        
        # Get first and last entry timestamps
        first_entry = session.query(Ledger).order_by(Ledger.id.asc()).first()
        last_entry = session.query(Ledger).order_by(Ledger.id.desc()).first()
        
        return {
            'total_entries': total_entries,
            'action_counts': action_counts,
            'first_entry_time': first_entry.timestamp if first_entry else None,
            'last_entry_time': last_entry.timestamp if last_entry else None,
            'last_hash': last_entry.data_hash if last_entry else '0' * 64
        }
        
    except Exception as e:
        print(f"Error getting ledger stats: {e}")
        return {
            'total_entries': 0,
            'action_counts': {},
            'first_entry_time': None,
            'last_entry_time': None,
            'last_hash': '0' * 64
        }
    finally:
        session.close()

def export_ledger_proof(start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict[str, Any]:
    """
    Export ledger proof for verification
    
    Args:
        start_date: Start date in ISO format (optional)
        end_date: End date in ISO format (optional)
    
    Returns:
        Dictionary containing ledger proof data
    """
    session = get_session()
    try:
        query = session.query(Ledger).order_by(Ledger.id.asc())
        
        if start_date:
            query = query.filter(Ledger.timestamp >= start_date)
        if end_date:
            query = query.filter(Ledger.timestamp <= end_date)
        
        entries = query.all()
        
        # Create proof structure
        proof = {
            'export_timestamp': datetime.utcnow().isoformat() + 'Z',
            'filter_start_date': start_date,
            'filter_end_date': end_date,
            'total_entries': len(entries),
            'entries': [],
            'verification_info': {
                'hash_algorithm': 'SHA-256',
                'payload_format': 'timestamp|prev_hash|actor_id|data_text'
            }
        }
        
        for entry in entries:
            proof['entries'].append({
                'id': entry.id,
                'timestamp': entry.timestamp,
                'prev_hash': entry.prev_hash,
                'data_hash': entry.data_hash,
                'actor_id': entry.actor_id,
                'action_type': entry.action_type,
                'data_text': entry.data_text
            })
        
        # Add verification hash of the entire proof
        proof_json = json.dumps(proof, sort_keys=True, separators=(',', ':'))
        proof['proof_hash'] = hashlib.sha256(proof_json.encode('utf-8')).hexdigest()
        
        return proof
        
    finally:
        session.close()

# Convenience functions for common ledger entries

def log_user_action(actor_id: int, action: str, details: Dict[str, Any]):
    """Log a user action"""
    return add_ledger_entry(
        actor_id=actor_id,
        action_type='user_action',
        data_dict={'action': action, 'details': details},
        human_message=f"User action: {action}"
    )

def log_refill_transaction(actor_id: int, transaction_id: int, transaction_data: Dict[str, Any]):
    """Log a refill transaction"""
    return add_ledger_entry(
        actor_id=actor_id,
        action_type='refill_transaction',
        data_dict={'transaction_id': transaction_id, **transaction_data},
        human_message=f"Refill transaction #{transaction_id}: {transaction_data.get('gallons_count', 0)} gallons, ₱{transaction_data.get('total_amount', 0):.2f}"
    )

def log_expense(actor_id: int, expense_id: int, expense_data: Dict[str, Any]):
    """Log an expense"""
    return add_ledger_entry(
        actor_id=actor_id,
        action_type='expense',
        data_dict={'expense_id': expense_id, **expense_data},
        human_message=f"Expense: {expense_data.get('category', 'Unknown')} - ₱{expense_data.get('amount', 0):.2f}"
    )

def log_inventory_change(actor_id: int, item_id: int, change_data: Dict[str, Any]):
    """Log an inventory change"""
    return add_ledger_entry(
        actor_id=actor_id,
        action_type='inventory_change',
        data_dict={'item_id': item_id, **change_data},
        human_message=f"Inventory change: {change_data.get('item_name', 'Unknown')} - {change_data.get('change_type', 'Unknown')}"
    )

def log_system_event(event_type: str, event_data: Dict[str, Any]):
    """Log a system event"""
    return add_ledger_entry(
        actor_id=None,
        action_type='system_event',
        data_dict={'event_type': event_type, **event_data},
        human_message=f"System event: {event_type}"
    )
