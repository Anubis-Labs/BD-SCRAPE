#!/usr/bin/env python3
"""
Test script for database management utilities
"""

import sys
import os
from pathlib import Path

# Correctly add project root to the path, so both 'src' and 'scripts' can be found
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'src')) # Ensure src is also in path for nested imports
sys.path.insert(0, str(project_root / 'scripts')) # And scripts

def test_database_manager():
    """Test the DatabaseManager class"""
    print("🧪 Testing DatabaseManager...")
    
    try:
        from database_manager import DatabaseManager
        
        db_manager = DatabaseManager()
        
        # Test database status check
        print("📊 Checking database status...")
        status = db_manager.check_database_status()
        print(f"Database status: {status}")
        
        # Test export directory creation
        print("📁 Testing export directory creation...")
        export_dir = db_manager.export_dir
        print(f"Export directory: {export_dir}")
        print(f"Export directory exists: {export_dir.exists()}")
        
        print("✅ DatabaseManager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ DatabaseManager test failed: {e}")
        return False

def test_docker_manager():
    """Test the DockerDBManager class"""
    print("\n🐳 Testing DockerDBManager...")
    
    try:
        from docker_db_manager import DockerDBManager
        
        docker_manager = DockerDBManager()
        
        # Test Docker status check
        print("🔍 Checking Docker status...")
        status = docker_manager.check_docker_status()
        print(f"Docker status: {status}")
        
        print("✅ DockerDBManager tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ DockerDBManager test failed: {e}")
        return False

def test_database_ui():
    """Test the database management UI components"""
    print("\n🖥️ Testing Database Management UI...")
    
    try:
        from src.gui.database_management_ui import DatabaseManagementUI
        
        # Test UI class instantiation
        db_ui = DatabaseManagementUI()
        print("✅ DatabaseManagementUI instantiated successfully!")
        
        # Test statistics method
        print("📈 Testing statistics gathering...")
        stats = db_ui.get_database_statistics()
        print(f"Database statistics: {stats}")
        
        print("✅ Database Management UI tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Database Management UI test failed: {e}")
        return False

def test_imports():
    """Test that all required modules can be imported"""
    print("\n📦 Testing imports...")
    
    modules_to_test = [
        'scripts.database_manager',
        'scripts.docker_db_manager',
        'src.database_crud',
        'src.database_models',
        'src.gui.database_management_ui'
    ]
    
    success_count = 0
    
    for module in modules_to_test:
        try:
            __import__(module)
            print(f"✅ {module} imported successfully")
            success_count += 1
        except ImportError as e:
            # Add a more descriptive error message
            print(f"❌ Failed to import {module}: {e}. Current sys.path: {sys.path}")
    
    print(f"\n📊 Import test results: {success_count}/{len(modules_to_test)} modules imported successfully")
    return success_count == len(modules_to_test)

def main():
    """Run all tests"""
    print("🚀 Starting Database Management Tests")
    print("=" * 50)
    
    test_results = []
    
    # Test imports first
    test_results.append(test_imports())
    
    # Test individual components
    test_results.append(test_database_manager())
    test_results.append(test_docker_manager())
    test_results.append(test_database_ui())
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    
    passed = sum(test_results)
    total = len(test_results)
    
    print(f"✅ Passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! Database management utilities are ready to use.")
    else:
        print("⚠️ Some tests failed. Please check the error messages above.")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 