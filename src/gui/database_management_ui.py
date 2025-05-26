#!/usr/bin/env python3
"""
Database Management UI for Streamlit
Provides a comprehensive interface for database operations including:
- Database status monitoring
- Database wipe/reset functionality
- Data export in multiple formats (CSV, JSON, SQL)
- Docker container management
- Volume backup and restore
"""

import streamlit as st
import os
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

# Add parent directories to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))

from scripts.database_manager import DatabaseManager
from scripts.docker_db_manager import DockerDBManager
from database_crud import get_session, get_db_connection_status
from database_models import (
    Project, Client, Document, ProjectExtractionLog, 
    Technology, Partner, ProjectFinancial
)

class DatabaseManagementUI:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.docker_manager = DockerDBManager()
        
        # Initialize session state
        if 'db_export_status' not in st.session_state:
            st.session_state.db_export_status = {}
        if 'db_last_export' not in st.session_state:
            st.session_state.db_last_export = None
        if 'docker_status_cache' not in st.session_state:
            st.session_state.docker_status_cache = {}
        if 'db_stats_cache' not in st.session_state:
            st.session_state.db_stats_cache = {}
    
    def get_database_statistics(self) -> Dict[str, Any]:
        """Get comprehensive database statistics"""
        try:
            session = get_session()
            
            stats = {
                "projects": session.query(Project).count(),
                "clients": session.query(Client).count(),
                "documents": session.query(Document).count(),
                "extraction_logs": session.query(ProjectExtractionLog).count(),
                "technologies": session.query(Technology).count(),
                "partners": session.query(Partner).count(),
                "financials": session.query(ProjectFinancial).count(),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Get recent activity
            recent_projects = session.query(Project).order_by(Project.created_at.desc()).limit(5).all()
            recent_documents = session.query(Document).order_by(Document.last_processed_at.desc()).limit(5).all()
            
            stats["recent_projects"] = [
                {"name": p.project_name, "created": p.created_at.strftime("%Y-%m-%d") if p.created_at else "N/A"}
                for p in recent_projects
            ]
            
            stats["recent_documents"] = [
                {"name": d.file_name, "processed": d.last_processed_at.strftime("%Y-%m-%d") if d.last_processed_at else "N/A"}
                for d in recent_documents
            ]
            
            session.close()
            return stats
            
        except Exception as e:
            st.error(f"Error getting database statistics: {e}")
            return {
                "projects": 0, "clients": 0, "documents": 0, "extraction_logs": 0,
                "technologies": 0, "partners": 0, "financials": 0,
                "last_updated": "Error", "recent_projects": [], "recent_documents": []
            }
    
    def display_database_status(self):
        """Display comprehensive database status"""
        st.subheader("📊 Database Status & Statistics")
        
        # Connection status
        db_status, db_message = get_db_connection_status()
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if db_status:
                st.success("🟢 Database Connection: Active")
            else:
                st.error(f"🔴 Database Connection: {db_message}")
        
        with col2:
            if st.button("🔄 Refresh Status", key="refresh_db_status"):
                st.session_state.db_stats_cache = {}
                st.rerun()
        
        if db_status:
            # Get and display statistics
            if 'db_stats_cache' not in st.session_state or not st.session_state.db_stats_cache:
                with st.spinner("Loading database statistics..."):
                    st.session_state.db_stats_cache = self.get_database_statistics()
            
            stats = st.session_state.db_stats_cache
            
            # Statistics cards
            st.markdown("### 📈 Database Metrics")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Projects", stats["projects"])
                st.metric("Documents", stats["documents"])
            
            with col2:
                st.metric("Clients", stats["clients"])
                st.metric("Extraction Logs", stats["extraction_logs"])
            
            with col3:
                st.metric("Technologies", stats["technologies"])
                st.metric("Partners", stats["partners"])
            
            with col4:
                st.metric("Financial Records", stats["financials"])
                st.info(f"Last Updated: {stats['last_updated']}")
            
            # Recent activity
            if stats["recent_projects"] or stats["recent_documents"]:
                st.markdown("### 🕒 Recent Activity")
                
                activity_col1, activity_col2 = st.columns(2)
                
                with activity_col1:
                    st.markdown("**Recent Projects:**")
                    if stats["recent_projects"]:
                        for project in stats["recent_projects"]:
                            st.text(f"• {project['name']} ({project['created']})")
                    else:
                        st.text("No recent projects")
                
                with activity_col2:
                    st.markdown("**Recent Documents:**")
                    if stats["recent_documents"]:
                        for doc in stats["recent_documents"]:
                            st.text(f"• {doc['name']} ({doc['processed']})")
                    else:
                        st.text("No recent documents")
    
    def display_database_operations(self):
        """Display database operation controls"""
        st.subheader("🛠️ Database Operations")
        
        # Create tabs for different operations
        op_tab1, op_tab2, op_tab3 = st.tabs(["🗑️ Reset Database", "📤 Export Data", "🔧 Maintenance"])
        
        with op_tab1:
            self.display_database_reset()
        
        with op_tab2:
            self.display_data_export()
        
        with op_tab3:
            self.display_maintenance_tools()
    
    def display_database_reset(self):
        """Display database reset controls"""
        st.markdown("### ⚠️ Database Reset")
        st.warning("This will permanently delete ALL data in the database!")
        
        st.markdown("""
        **What this does:**
        - Drops all database tables
        - Recreates empty tables with the current schema
        - Preserves table structure but removes all data
        - Cannot be undone without a backup
        """)
        
        # Safety confirmation
        confirm_text = st.text_input(
            "Type 'CONFIRM RESET' to enable the reset button:",
            key="reset_confirm_text"
        )
        
        reset_enabled = confirm_text == "CONFIRM RESET"
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button(
                "🗑️ RESET DATABASE", 
                disabled=not reset_enabled,
                key="reset_database_btn",
                type="primary" if reset_enabled else "secondary"
            ):
                with st.spinner("Resetting database..."):
                    success = self.db_manager.wipe_database(confirm=True)
                    
                if success:
                    st.success("✅ Database reset successfully!")
                    st.session_state.db_stats_cache = {}  # Clear cache
                    st.balloons()
                else:
                    st.error("❌ Database reset failed!")
        
        with col2:
            st.info("💡 **Tip:** Export your data first if you want to keep a backup!")
    
    def display_data_export(self):
        """Display data export controls"""
        st.markdown("### 📤 Data Export")
        
        # Export format selection
        export_format = st.selectbox(
            "Select Export Format:",
            ["CSV Files", "JSON Files", "SQL Dump", "All Formats"],
            help="Choose the format for exporting your database"
        )
        
        # Export options
        col1, col2 = st.columns([2, 1])
        
        with col1:
            custom_path = st.text_input(
                "Custom Export Path (optional):",
                placeholder="Leave empty for automatic timestamped folder",
                help="Specify a custom directory for exports"
            )
        
        with col2:
            st.markdown("**Export will include:**")
            st.text("• All project data")
            st.text("• Documents & metadata")
            st.text("• Client information")
            st.text("• Extraction logs")
            st.text("• Financial records")
        
        # Export button
        if st.button("📤 Start Export", key="start_export_btn", type="primary"):
            export_path = custom_path.strip() if custom_path.strip() else None
            
            with st.spinner(f"Exporting data in {export_format} format..."):
                success = False
                
                try:
                    if export_format == "CSV Files":
                        success = self.db_manager.export_to_csv(export_path)
                    elif export_format == "JSON Files":
                        success = self.db_manager.export_to_json(export_path)
                    elif export_format == "SQL Dump":
                        success = self.db_manager.export_sql_dump(export_path)
                    elif export_format == "All Formats":
                        success = self.db_manager.export_all_formats()
                    
                    if success:
                        st.success(f"✅ Export completed successfully!")
                        st.session_state.db_last_export = {
                            "format": export_format,
                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "path": export_path or "Auto-generated"
                        }
                        st.balloons()
                    else:
                        st.error("❌ Export failed!")
                        
                except Exception as e:
                    st.error(f"❌ Export error: {e}")
        
        # Show last export info
        if st.session_state.db_last_export:
            st.markdown("### 📋 Last Export")
            last_export = st.session_state.db_last_export
            st.info(f"**Format:** {last_export['format']} | **Time:** {last_export['timestamp']} | **Path:** {last_export['path']}")
    
    def display_maintenance_tools(self):
        """Display database maintenance tools"""
        st.markdown("### 🔧 Maintenance Tools")
        
        # Database analysis
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Analyze Database", key="analyze_db_btn"):
                with st.spinner("Analyzing database..."):
                    stats = self.db_manager.check_database_status()
                    
                st.markdown("**Database Analysis Results:**")
                for key, value in stats.items():
                    if key == "connection":
                        if "Connected" in str(value):
                            st.success(f"{key.title()}: {value}")
                        else:
                            st.error(f"{key.title()}: {value}")
                    else:
                        st.info(f"{key.replace('_', ' ').title()}: {value}")
        
        with col2:
            if st.button("🧹 Clear Cache", key="clear_cache_btn"):
                st.session_state.db_stats_cache = {}
                st.session_state.docker_status_cache = {}
                st.success("✅ Cache cleared!")
        
        # Database optimization suggestions
        st.markdown("### 💡 Optimization Suggestions")
        
        if st.session_state.db_stats_cache:
            stats = st.session_state.db_stats_cache
            
            suggestions = []
            
            if stats["extraction_logs"] > 10000:
                suggestions.append("Consider archiving old extraction logs to improve performance")
            
            if stats["documents"] > 1000:
                suggestions.append("Large number of documents - consider implementing pagination in views")
            
            if not suggestions:
                suggestions.append("Database is well-optimized!")
            
            for suggestion in suggestions:
                st.info(f"💡 {suggestion}")
    
    def display_docker_management(self):
        """Display Docker container management"""
        st.subheader("🐳 Docker Database Management")
        
        # Get Docker status
        if st.button("🔄 Refresh Docker Status", key="refresh_docker_status"):
            st.session_state.docker_status_cache = {}
        
        if 'docker_status_cache' not in st.session_state or not st.session_state.docker_status_cache:
            with st.spinner("Checking Docker status..."):
                st.session_state.docker_status_cache = self.docker_manager.check_docker_status()
        
        docker_status = st.session_state.docker_status_cache
        
        # Docker status display
        st.markdown("### 🔍 Docker Status")
        
        status_col1, status_col2, status_col3 = st.columns(3)
        
        with status_col1:
            if docker_status.get("docker_running", False):
                st.success("🟢 Docker: Running")
            else:
                st.error("🔴 Docker: Not Running")
            
            if docker_status.get("compose_file_exists", False):
                st.success("🟢 Compose File: Found")
            else:
                st.error("🔴 Compose File: Missing")
        
        with status_col2:
            if docker_status.get("container_exists", False):
                st.success("🟢 Container: Exists")
            else:
                st.warning("🟡 Container: Not Found")
            
            if docker_status.get("container_running", False):
                st.success("🟢 Container: Running")
            else:
                st.warning("🟡 Container: Stopped")
        
        with status_col3:
            if docker_status.get("volume_exists", False):
                st.success("🟢 Volume: Exists")
            else:
                st.error("🔴 Volume: Missing")
        
        # Docker operations
        if docker_status.get("docker_running", False):
            st.markdown("### 🎛️ Container Operations")
            
            op_col1, op_col2, op_col3, op_col4 = st.columns(4)
            
            with op_col1:
                if st.button("▶️ Start DB", key="start_db_btn"):
                    with st.spinner("Starting database..."):
                        success = self.docker_manager.start_database()
                    if success:
                        st.success("✅ Database started!")
                        st.session_state.docker_status_cache = {}
                    else:
                        st.error("❌ Failed to start database!")
            
            with op_col2:
                if st.button("⏹️ Stop DB", key="stop_db_btn"):
                    with st.spinner("Stopping database..."):
                        success = self.docker_manager.stop_database()
                    if success:
                        st.success("✅ Database stopped!")
                        st.session_state.docker_status_cache = {}
                    else:
                        st.error("❌ Failed to stop database!")
            
            with op_col3:
                if st.button("🔄 Restart DB", key="restart_db_btn"):
                    with st.spinner("Restarting database..."):
                        success = self.docker_manager.restart_database()
                    if success:
                        st.success("✅ Database restarted!")
                        st.session_state.docker_status_cache = {}
                    else:
                        st.error("❌ Failed to restart database!")
            
            with op_col4:
                if st.button("🔧 Check Persistence", key="check_persistence_btn"):
                    with st.spinner("Checking persistence..."):
                        success = self.docker_manager.ensure_persistence()
                    if success:
                        st.success("✅ Persistence configured!")
                    else:
                        st.error("❌ Persistence issues found!")
        
        # Volume management
        if docker_status.get("volume_exists", False):
            st.markdown("### 💾 Volume Management")
            
            vol_col1, vol_col2 = st.columns(2)
            
            with vol_col1:
                if st.button("💾 Backup Volume", key="backup_volume_btn"):
                    with st.spinner("Creating volume backup..."):
                        success = self.docker_manager.backup_volume()
                    if success:
                        st.success("✅ Volume backup created!")
                    else:
                        st.error("❌ Volume backup failed!")
            
            with vol_col2:
                # Volume restore
                backup_file = st.file_uploader(
                    "Upload backup file to restore:",
                    type=['tar'],
                    key="volume_restore_upload"
                )
                
                if backup_file and st.button("📥 Restore Volume", key="restore_volume_btn"):
                    # Save uploaded file temporarily
                    temp_path = Path("temp_backup.tar")
                    with open(temp_path, "wb") as f:
                        f.write(backup_file.getbuffer())
                    
                    with st.spinner("Restoring volume..."):
                        success = self.docker_manager.restore_volume(str(temp_path))
                    
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()
                    
                    if success:
                        st.success("✅ Volume restored!")
                        st.session_state.docker_status_cache = {}
                    else:
                        st.error("❌ Volume restore failed!")
    
    def display_complete_interface(self):
        """Display the complete database management interface"""
        st.header("🗄️ Database Management Center")
        
        # Create main tabs
        main_tab1, main_tab2, main_tab3 = st.tabs([
            "📊 Status & Overview", 
            "🛠️ Database Operations", 
            "🐳 Docker Management"
        ])
        
        with main_tab1:
            self.display_database_status()
        
        with main_tab2:
            self.display_database_operations()
        
        with main_tab3:
            self.display_docker_management()


# Convenience function for easy integration
def render_database_management_ui():
    """Render the complete database management UI"""
    db_ui = DatabaseManagementUI()
    db_ui.display_complete_interface()


# For standalone testing
if __name__ == "__main__":
    st.set_page_config(
        page_title="Database Management", 
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    render_database_management_ui() 