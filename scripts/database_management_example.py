#!/usr/bin/env python3
"""
Database Management Example Script
Demonstrates how to use the database management utilities programmatically
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

def example_database_operations():
    """Example of database operations"""
    print("🗄️ Database Management Example")
    print("=" * 50)
    
    from database_manager import DatabaseManager
    
    # Initialize database manager
    db_manager = DatabaseManager()
    
    # 1. Check database status
    print("\n📊 Checking database status...")
    status = db_manager.check_database_status()
    print(f"Connection: {status['connection']}")
    print(f"Projects: {status['projects']}")
    print(f"Documents: {status['documents']}")
    print(f"Extraction Logs: {status['extraction_logs']}")
    
    # 2. Export data (example - CSV format)
    print("\n📤 Exporting data to CSV...")
    export_success = db_manager.export_to_csv()
    if export_success:
        print("✅ CSV export completed successfully!")
    else:
        print("❌ CSV export failed!")
    
    # 3. Show export directory contents
    print(f"\n📁 Export directory contents:")
    export_dir = db_manager.export_dir
    if export_dir.exists():
        for item in export_dir.iterdir():
            if item.is_dir():
                print(f"  📂 {item.name}/")
            else:
                print(f"  📄 {item.name}")
    else:
        print("  (No exports yet)")

def example_docker_operations():
    """Example of Docker operations"""
    print("\n🐳 Docker Management Example")
    print("=" * 50)
    
    from docker_db_manager import DockerDBManager
    
    # Initialize Docker manager
    docker_manager = DockerDBManager()
    
    # 1. Check Docker status
    print("\n🔍 Checking Docker status...")
    status = docker_manager.check_docker_status()
    
    print(f"Docker Running: {'✅' if status['docker_running'] else '❌'}")
    print(f"Container Exists: {'✅' if status['container_exists'] else '❌'}")
    print(f"Container Running: {'✅' if status['container_running'] else '❌'}")
    print(f"Volume Exists: {'✅' if status['volume_exists'] else '❌'}")
    print(f"Compose File: {'✅' if status['compose_file_exists'] else '❌'}")
    
    # 2. Get volume information (if volume exists)
    if status['volume_exists']:
        print("\n💾 Volume information...")
        volume_info = docker_manager.get_volume_info()
        if volume_info:
            print(f"Volume Name: {volume_info.get('name', 'Unknown')}")
            print(f"Volume Size: {volume_info.get('size', 'Unknown')}")
            print(f"Mount Point: {volume_info.get('mountpoint', 'Unknown')}")
    
    # 3. Check persistence configuration
    print("\n🔧 Checking persistence configuration...")
    persistence_ok = docker_manager.ensure_persistence()
    if persistence_ok:
        print("✅ Persistence is properly configured!")
    else:
        print("⚠️ Persistence configuration issues detected!")

def example_web_interface_info():
    """Information about the web interface"""
    print("\n🖥️ Web Interface Information")
    print("=" * 50)
    
    print("""
To use the web interface:

1. Start the Streamlit app:
   streamlit run src/gui/streamlit_app.py

2. Open your browser to: http://localhost:8501

3. Navigate to the "Database Management Center" section

4. Use the tabs to:
   - 📊 View database status and statistics
   - 🛠️ Perform database operations (reset, export, maintenance)
   - 🐳 Manage Docker containers and volumes

The web interface provides:
- Real-time database statistics
- Safe database reset with confirmation
- Multi-format data export (CSV, JSON, SQL)
- Docker container management
- Volume backup and restore
- Maintenance tools and optimization suggestions
""")

def example_command_line_usage():
    """Show command line usage examples"""
    print("\n💻 Command Line Usage Examples")
    print("=" * 50)
    
    print("""
Database Management:
  python database_manager.py status              # Check database status
  python database_manager.py wipe                # Wipe database (with confirmation)
  python database_manager.py export csv          # Export to CSV
  python database_manager.py export json         # Export to JSON
  python database_manager.py export sql          # Export SQL dump
  python database_manager.py export all          # Export all formats

Docker Management:
  python docker_db_manager.py status             # Check Docker status
  python docker_db_manager.py start              # Start database
  python docker_db_manager.py stop               # Stop database
  python docker_db_manager.py restart            # Restart database
  python docker_db_manager.py backup             # Backup volume
  python docker_db_manager.py restore backup.tar # Restore volume
  python docker_db_manager.py ensure-persistence # Check persistence

Testing:
  python test_db_management.py                   # Run test suite
""")

def main():
    """Run all examples"""
    print("🚀 Database Management Utilities - Example Usage")
    print("=" * 60)
    
    try:
        # Run examples
        example_database_operations()
        example_docker_operations()
        example_web_interface_info()
        example_command_line_usage()
        
        print("\n" + "=" * 60)
        print("🎉 Example completed successfully!")
        print("\nNext steps:")
        print("1. Try the web interface: streamlit run src/gui/streamlit_app.py")
        print("2. Explore the command line tools")
        print("3. Read DATABASE_MANAGEMENT_README.md for full documentation")
        
    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("Please ensure:")
        print("- Database is running")
        print("- Docker is available")
        print("- All dependencies are installed")

if __name__ == "__main__":
    main() 