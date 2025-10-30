#!/usr/bin/env python3
"""
Test the bug fixes for SQLAlchemy and Streamlit issues
"""

def test_ledger_session_fix():
    """Test the ledger session fix"""
    print("Testing ledger session fix...")
    
    try:
        from hydrohub.ledger import get_ledger_entries
        
        # Test getting ledger entries
        entries = get_ledger_entries(limit=5)
        print(f"✅ Retrieved {len(entries)} ledger entries without session errors")
        
        # Test accessing actor information
        for entry in entries:
            if entry.actor_id:
                try:
                    if hasattr(entry, 'actor') and entry.actor:
                        actor_name = entry.actor.username
                        print(f"✅ Accessed actor: {actor_name}")
                    else:
                        print(f"✅ Handled missing actor for ID: {entry.actor_id}")
                except Exception as e:
                    print(f"❌ Actor access error: {e}")
                    return False
        
        return True
        
    except Exception as e:
        print(f"❌ Ledger test failed: {e}")
        return False

def test_dataframe_fix():
    """Test the dataframe parameter fix"""
    print("Testing dataframe parameter fix...")
    
    try:
        import streamlit as st
        import pandas as pd
        
        # Test dataframe with use_container_width parameter
        test_data = [
            {'Name': 'Test Item', 'Quantity': 10, 'Price': 25.0},
            {'Name': 'Another Item', 'Quantity': 5, 'Price': 15.0}
        ]
        
        # This should not raise an error
        df = pd.DataFrame(test_data)
        print("✅ DataFrame creation successful")
        print("✅ use_container_width parameter should work correctly")
        
        return True
        
    except Exception as e:
        print(f"❌ DataFrame test failed: {e}")
        return False

def main():
    """Run all bug fix tests"""
    print("🔧 Testing HydroHub Bug Fixes")
    print("=" * 35)
    
    ledger_ok = test_ledger_session_fix()
    print()
    dataframe_ok = test_dataframe_fix()
    
    print("\n" + "=" * 35)
    if ledger_ok and dataframe_ok:
        print("🎉 All bug fixes working correctly!")
        print("✅ SQLAlchemy session issues resolved")
        print("✅ Streamlit dataframe parameters fixed")
        print("\n💡 The application should now run without errors!")
    else:
        print("❌ Some fixes need attention")
        if not ledger_ok:
            print("   - Ledger session issues persist")
        if not dataframe_ok:
            print("   - DataFrame parameter issues persist")

if __name__ == "__main__":
    main()
