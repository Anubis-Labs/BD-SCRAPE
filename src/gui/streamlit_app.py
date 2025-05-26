import streamlit as st
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import html  # Add this import at the top with other imports
import json
import base64
import time

# Add src directory to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main_processor import process_documents
from llm_handler import get_available_ollama_models
from database_crud import (
    get_db_connection_status, get_primary_sectors, get_project_sub_categories, 
    get_project_statuses,
    get_simple_project_list,
    get_comprehensive_project_list,
    get_projects_for_display,
    get_documents_for_project,
    get_key_info_for_document,
    get_project_extraction_logs,
    get_session,
    get_processed_documents
)
from file_system_handler import list_files_in_upload_folder, clear_upload_folder, get_file_stats, UPLOAD_FOLDER, find_project_files

# Import database management UI
try:
    from database_management_ui import render_database_management_ui
    DATABASE_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    DATABASE_MANAGEMENT_AVAILABLE = False
    print(f"Database management UI not available: {e}")

# --- Enhanced Real-Time Logging System ---
class AdvancedStreamlitLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)
        if 'live_logs' not in st.session_state:
            st.session_state.live_logs = []
        if 'log_counter' not in st.session_state:
            st.session_state.log_counter = 0

    def emit(self, record):
        log_entry = self.format(record)
        st.session_state.log_counter += 1
        
        # Enhanced log entry with styling
        enhanced_log = {
            "id": st.session_state.log_counter,
            "level": record.levelname,
            "msg": log_entry,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],  # Include milliseconds
            "module": record.name,
            "raw_message": record.getMessage()
        }
        
        st.session_state.live_logs.append(enhanced_log)
        
        # Keep only last 150 logs for performance
        if len(st.session_state.live_logs) > 150:
            st.session_state.live_logs = st.session_state.live_logs[-150:]
        
        # Force immediate update during processing
        if st.session_state.get('processing_active', False):
            # Use session state to trigger updates without full rerun
            st.session_state.last_log_update = datetime.now().timestamp()


# Configure root logger
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# Get root logger
logger = logging.getLogger() 
logger.setLevel(logging.INFO) # Set global logging level

# Remove existing handlers to avoid duplicate logs in console if any were auto-configured
for handler in logger.handlers[:]:
    logger.removeHandler(handler)

# Add Streamlit handler
streamlit_handler = AdvancedStreamlitLogHandler()
streamlit_handler.setFormatter(log_formatter)
logger.addHandler(streamlit_handler)

# Add console handler for debugging in terminal
console_handler = logging.StreamHandler(sys.stdout) # Use sys.stdout
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

# ENHANCED LOGGING SETUP - Ensure all module loggers are captured
module_loggers = [
    'main_processor',
    'llm_handler', 
    'database_crud',
    'file_system_handler',
    'src.main_processor',
    'src.llm_handler',
    'src.database_crud', 
    'src.file_system_handler',
    '__main__'
]

for module_name in module_loggers:
    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(logging.INFO)
    # Add handlers to each module logger to ensure capture
    if streamlit_handler not in module_logger.handlers:
        module_logger.addHandler(streamlit_handler)
    if console_handler not in module_logger.handlers:
        module_logger.addHandler(console_handler)
    # Ensure propagation to root logger
    module_logger.propagate = True

# Force all loggers to propagate to root
logging.getLogger().propagate = True

# Set logging level for common third-party libraries to reduce noise
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('streamlit').setLevel(logging.WARNING)

# Only log initialization once to prevent spam
if 'logging_initialized' not in st.session_state:
    logger.info("🔧 Enhanced logging system initialized - capturing all module logs")
    st.session_state.logging_initialized = True
# --- End Custom Logging Setup ---

# --- Streamlit Page Configuration ---
st.set_page_config(
    page_title="Equinox Document Intelligence Processor", 
    layout="wide",
    initial_sidebar_state="expanded"  # Show sidebar by default to display all new features
)

# Disable automatic rerun on file changes and reduce refresh frequency
# This helps prevent the dimming screen during processing
if hasattr(st, 'config'):
    try:
        st.config.set_option('global.developmentMode', False)
        st.config.set_option('server.runOnSave', False)
    except:
        pass  # Ignore if options don't exist in this Streamlit version

# --- Global Variables & Session State ---
if 'processing_stopped' not in st.session_state:
    st.session_state.processing_stopped = False
if 'processing_active' not in st.session_state:
    st.session_state.processing_active = False
if 'auto_show_logs' not in st.session_state:
    st.session_state.auto_show_logs = False
if 'live_logs' not in st.session_state:
    st.session_state.live_logs = []
if 'log_counter' not in st.session_state:
    st.session_state.log_counter = 0
if 'last_log_update' not in st.session_state:
    st.session_state.last_log_update = 0
if 'ollama_models' not in st.session_state:
    st.session_state.ollama_models = get_available_ollama_models()
if 'current_doc_name' not in st.session_state:
    st.session_state.current_doc_name = ""
if 'processed_files_count' not in st.session_state:
    st.session_state.processed_files_count = 0
if 'total_files_to_process' not in st.session_state:
    st.session_state.total_files_to_process = 0

# Update upload folder path
UPLOAD_FOLDER = "data/upload_folder"

# --- Custom Background Styling ---

# Function to encode image to base64
@st.cache_data
def get_base64_of_bin_file(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

# Get base64 string of background image
try:
    # Use the correct path to assets/background.jpg
    background_image_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'background.jpg')
    # Alternative: Use current working directory approach
    if not os.path.exists(background_image_path):
        background_image_path = os.path.join(os.getcwd(), 'assets', 'background.jpg')
    
    if os.path.exists(background_image_path):
        background_base64 = get_base64_of_bin_file(background_image_path)
        # Only log once on first load, not every refresh
        if 'background_loaded_logged' not in st.session_state:
            logger.info(f"✅ Background image loaded successfully from: {background_image_path}")
            st.session_state.background_loaded_logged = True
        
        # === COMPREHENSIVE SIDEBAR ===
        with st.sidebar:
            st.markdown("# ⚙️ Control Center")
            st.markdown("---")
            
            # === BACKGROUND SETTINGS ===
            st.markdown("### 🎨 Background Settings")
            opacity_level = st.slider(
                "Background Opacity", 
                min_value=0.0, 
                max_value=1.0, 
                value=0.85, 
                step=0.05,
                help="Higher values = more subtle background, Lower values = more visible background"
            )
            
            # Background theme selector
            bg_theme = st.selectbox(
                "Background Theme",
                ["Default Image", "Dark Gradient", "Blue Gradient", "Purple Gradient"],
                help="Choose background theme"
            )
            
            st.markdown("---")
            
            # === SYSTEM STATUS ===
            st.markdown("### 📊 System Status")
            
            # Database status
            db_status, db_message = get_db_connection_status()
            if db_status:
                st.success("🟢 Database: Connected")
            else:
                st.error("🔴 Database: Disconnected")
            
            # Ollama status
            if st.session_state.ollama_models:
                st.success(f"🤖 AI Models: {len(st.session_state.ollama_models)} available")
                with st.expander("View Models"):
                    for model in st.session_state.ollama_models:
                        st.text(f"• {model}")
            else:
                st.warning("⚠️ AI Models: None available")
            
            # Processing status
            if st.session_state.get('processing_active', False):
                st.info("⚙️ Processing: ACTIVE")
                current_file = st.session_state.get('current_doc_name', 'N/A')
                processed = st.session_state.get('processed_files_count', 0)
                total = st.session_state.get('total_files_to_process', 0)
                st.text(f"File: {current_file[:20]}...")
                if total > 0:
                    progress = processed / total
                    st.progress(progress, text=f"{processed}/{total}")
            else:
                st.info("◯ Processing: IDLE")
            
            st.markdown("---")
            
            # === QUICK ACTIONS ===
            st.markdown("### ⚡ Quick Actions")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Models", help="Refresh Ollama models list"):
                    st.session_state.ollama_models = get_available_ollama_models()
                    st.rerun()
            
            with col2:
                if st.button("🧹 Clear Logs", help="Clear live logs"):
                    st.session_state.live_logs = []
                    st.session_state.log_counter = 0
                    st.rerun()
            
            # Emergency stop
            if st.session_state.get('processing_active', False):
                if st.button("🛑 EMERGENCY STOP", type="primary", help="Stop all processing immediately"):
                    st.session_state.processing_stopped = True
                    st.session_state.processing_active = False
                    logger.warning("🛑 Emergency stop activated by user")
                    st.rerun()
            
            st.markdown("---")
            
            # === DATABASE MANAGEMENT ===
            st.markdown("### 🗄️ Database Management")
            
            if DATABASE_MANAGEMENT_AVAILABLE:
                # Database statistics
                try:
                    session = get_session()
                    if session:
                        from database_models import Project, Document, Client
                        project_count = session.query(Project).count()
                        document_count = session.query(Document).count()
                        client_count = session.query(Client).count()
                        session.close()
                        
                        st.metric("Projects", project_count)
                        st.metric("Documents", document_count)
                        st.metric("Clients", client_count)
                    else:
                        st.error("Database connection failed")
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}...")
                
                # Database operations
                st.markdown("**Database Operations:**")
                if st.button("📤 Export All Data", help="Export database to CSV/JSON"):
                    try:
                        from scripts.database_manager import DatabaseManager
                        db_manager = DatabaseManager()
                        success = db_manager.export_all_formats()
                        if success:
                            st.success("✅ Export completed!")
                        else:
                            st.error("❌ Export failed")
                    except Exception as e:
                        st.error(f"Export error: {e}")
                
                if st.button("📊 Database Stats", help="Show detailed statistics"):
                    st.session_state.show_db_stats = True
                    st.rerun()
                
                # Danger zone - simplified
                st.markdown("**⚠️ Danger Zone:**")
                st.warning("Destructive operations - use with caution!")
                
                confirm_wipe = st.checkbox("I understand this will delete ALL data")
                if st.button("🗑️ Wipe Database", disabled=not confirm_wipe, help="Delete all data"):
                    if confirm_wipe:
                        try:
                            from scripts.database_manager import DatabaseManager
                            db_manager = DatabaseManager()
                            success = db_manager.wipe_database(confirm=True)
                            if success:
                                st.success("✅ Database wiped successfully")
                            else:
                                st.error("❌ Wipe operation failed")
                        except Exception as e:
                            st.error(f"Wipe error: {e}")
            else:
                st.warning("Database management not available")
                st.text("Missing required modules")
            
            st.markdown("---")
            
            # === DOCKER MANAGEMENT ===
            st.markdown("### 🐳 Docker Management")
            
            try:
                from scripts.docker_db_manager import DockerDBManager
                docker_manager = DockerDBManager()
                docker_status = docker_manager.get_docker_status()
                
                # Docker status indicators
                if docker_status.get('docker_running', False):
                    st.success("🟢 Docker: Running")
                else:
                    st.error("🔴 Docker: Not running")
                
                if docker_status.get('container_running', False):
                    st.success("🟢 DB Container: Running")
                else:
                    st.warning("🟡 DB Container: Stopped")
                
                # Docker operations - flattened to avoid nested expanders
                st.markdown("**Container Operations:**")
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("▶️ Start DB", help="Start database container"):
                        try:
                            success = docker_manager.start_database_container()
                            if success:
                                st.success("✅ Container started")
                            else:
                                st.error("❌ Start failed")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                with col2:
                    if st.button("⏹️ Stop DB", help="Stop database container"):
                        try:
                            success = docker_manager.stop_database_container()
                            if success:
                                st.success("✅ Container stopped")
                            else:
                                st.error("❌ Stop failed")
                        except Exception as e:
                            st.error(f"Error: {e}")
                
                if st.button("🔄 Restart DB", help="Restart database container"):
                    try:
                        success = docker_manager.restart_database_container()
                        if success:
                            st.success("✅ Container restarted")
                        else:
                            st.error("❌ Restart failed")
                    except Exception as e:
                        st.error(f"Error: {e}")
                
                # Backup operations - simplified
                st.markdown("**Backup Operations:**")
                if st.button("💾 Backup Volume", help="Create database backup"):
                    try:
                        backup_path = f"backups/db_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tar"
                        success = docker_manager.backup_volume(backup_path)
                        if success:
                            st.success(f"✅ Backup created: {backup_path}")
                        else:
                            st.error("❌ Backup failed")
                    except Exception as e:
                        st.error(f"Backup error: {e}")
                        
            except Exception as e:
                st.error("Docker management not available")
                st.text(f"Error: {str(e)[:50]}...")
            
            st.markdown("---")
            
            # === SYSTEM INFO ===
            st.markdown("### ℹ️ System Info")
            
            with st.expander("📋 System Details"):
                st.text(f"Python: {sys.version.split()[0]}")
                st.text(f"Streamlit: {st.__version__}")
                st.text(f"Working Dir: {os.getcwd()}")
                st.text(f"Upload Folder: {UPLOAD_FOLDER}")
                
                # File system info
                try:
                    import shutil
                    total, used, free = shutil.disk_usage("/")
                    st.text(f"Disk Free: {free // (1024**3)} GB")
                except:
                    st.text("Disk info: N/A")
            
            # Version info
            st.markdown("---")
            st.caption("🔧 Equinox Document Intelligence Processor")
            st.caption("Version 1.0.0 | © 2024")
        
        # Apply background theme
        if bg_theme == "Dark Gradient":
            background_css = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
        background-size: cover !important;
    }}
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }}
    html, body {{
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }}
</style>
"""
        elif bg_theme == "Blue Gradient":
            background_css = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, #1e3c72, #2a5298, #1e3c72) !important;
        background-size: cover !important;
    }}
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, #1e3c72, #2a5298, #1e3c72) !important;
    }}
    html, body {{
        background: linear-gradient(135deg, #1e3c72, #2a5298, #1e3c72) !important;
    }}
</style>
"""
        elif bg_theme == "Purple Gradient":
            background_css = f"""
<style>
    .stApp {{
        background: linear-gradient(135deg, #667eea, #764ba2, #667eea) !important;
        background-size: cover !important;
    }}
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(135deg, #667eea, #764ba2, #667eea) !important;
    }}
    html, body {{
        background: linear-gradient(135deg, #667eea, #764ba2, #667eea) !important;
    }}
</style>
"""
        else:  # Default Image
            # Enhanced background implementation - multiple approaches for better compatibility
            background_css = f"""
<style>
    /* Primary background implementation */
    .stApp {{
        background: linear-gradient(rgba(0, 0, 0, {opacity_level}), rgba(0, 0, 0, {opacity_level})), 
                    url("data:image/jpeg;base64,{background_base64}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
    
    /* Secondary implementation for different Streamlit versions */
    [data-testid="stAppViewContainer"] {{
        background: linear-gradient(rgba(0, 0, 0, {opacity_level}), rgba(0, 0, 0, {opacity_level})), 
                    url("data:image/jpeg;base64,{background_base64}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
    
    /* Fallback for main container */
    .main {{
        background: transparent !important;
    }}
    
    /* Make header transparent */
    [data-testid="stHeader"] {{
        background-color: rgba(0,0,0,0) !important;
    }}
    
    /* Ensure containers are transparent to show background */
    [data-testid="stAppViewContainer"] .main {{
        background-color: transparent !important;
    }}
    
    /* Root level background enforcement */
    html, body {{
        background: linear-gradient(rgba(0, 0, 0, {opacity_level}), rgba(0, 0, 0, {opacity_level})), 
                    url("data:image/jpeg;base64,{background_base64}") !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        background-attachment: fixed !important;
    }}
</style>
"""
    else:
        logger.warning(f"❌ Background image not found at: {background_image_path}")
        # Fallback if image not found - use gradient background
        background_css = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }
    html, body {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }
</style>
"""
        st.warning("⚠️ Background image not found, using gradient background.")
except Exception as e:
    logger.error(f"❌ Error loading background image: {e}")
    # Fallback in case of any errors
    background_css = """
<style>
    .stApp {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }
    [data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0f0f23, #1a1a2e, #16213e) !important;
    }
</style>
"""
    st.error(f"Error loading background image: {e}")

st.markdown(background_css, unsafe_allow_html=True)

# --- Enhanced Real-Time Log Display System ---
def display_live_streaming_logs():
    """Revolutionary real-time log streaming with beautiful engineering aesthetics."""
    with st.container():
        # Dynamic header based on processing state with animations
        if st.session_state.get('processing_active', False):
            st.markdown(
                '<h3><span class="processing-gear">⚙</span> <span class="processing-active">Live Engineering Logs - Streaming</span> <span class="float-icon">●</span></h3>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown(
                '<h3>▦ Engineering Process Logs</h3>', 
                unsafe_allow_html=True
            )
        
        # Enhanced live status dashboard
        if st.session_state.get('processing_active', False):
            status_col1, status_col2, status_col3, status_col4 = st.columns(4)
            
            with status_col1:
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div style="text-align: center;">'
                    f'<span class="float-icon">▤</span><br>'
                    f'<strong>Current File</strong><br>'
                    f'<span style="color: #2196F3;">{st.session_state.get("current_doc_name", "N/A")[:20]}{"..." if len(st.session_state.get("current_doc_name", "")) > 20 else ""}</span>'
                    f'</div></div>', 
                    unsafe_allow_html=True
                )
            
            with status_col2:
                files_processed = st.session_state.get('processed_files_count', 0)
                total_files = st.session_state.get('total_files_to_process', 0)
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div style="text-align: center;">'
                    f'<span class="processing-active">▲</span><br>'
                    f'<strong>Progress</strong><br>'
                    f'<span style="color: #4CAF50;">{files_processed}</span>/<span style="color: #2196F3;">{total_files}</span>'
                    f'</div></div>', 
                    unsafe_allow_html=True
                )
            
            with status_col3:
                if total_files > 0:
                    progress_pct = int((files_processed / total_files) * 100)
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div style="text-align: center;">'
                        f'<span class="processing-gear">◉</span><br>'
                        f'<strong>Completion</strong><br>'
                        f'<span style="color: #03DAC6; font-size: 1.2em;">{progress_pct}%</span>'
                        f'</div></div>', 
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(
                        f'<div class="metric-card">'
                        f'<div style="text-align: center;">'
                        f'<span class="float-icon">◉</span><br>'
                        f'<strong>Completion</strong><br>'
                        f'<span style="color: #03DAC6;">Ready</span>'
                        f'</div></div>', 
                        unsafe_allow_html=True
                    )
            
            with status_col4:
                log_count = len(st.session_state.get('live_logs', []))
                st.markdown(
                    f'<div class="metric-card">'
                    f'<div style="text-align: center;">'
                    f'<span class="processing-active">▦</span><br>'
                    f'<strong>Log Entries</strong><br>'
                    f'<span style="color: #FF9800;">{log_count}</span>'
                    f'</div></div>', 
                    unsafe_allow_html=True
                )
        
        # OVERALL STATUS DASHBOARD - Always visible
        st.markdown('<div class="overall-status-dashboard">', unsafe_allow_html=True)
        
        # Create columns for horizontal layout
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            # System Status
            db_status, db_message = get_db_connection_status()
            db_icon = "◉" if db_status else "◯"
            db_color = "#4CAF50" if db_status else "#F44336"
            db_status_text = "Connected" if db_status else "Disconnected"
            
            st.markdown(
                f'<div class="overall-status-card">'
                f'<span style="color: {db_color};">{db_icon}</span><br>'
                f'<strong>Database</strong><br>'
                f'<span style="color: {db_color};">{db_status_text}</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        
        with col2:
            # Models Status
            models_count = len(st.session_state.get('ollama_models', []))
            model_icon = "⬢" if models_count > 0 else "△"
            model_color = "#4CAF50" if models_count > 0 else "#FF9800"
            
            st.markdown(
                f'<div class="overall-status-card">'
                f'<span style="color: {model_color};">{model_icon}</span><br>'
                f'<strong>AI Models</strong><br>'
                f'<span style="color: {model_color};">{models_count} Available</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        
        with col3:
            # Processing Status
            if st.session_state.get('processing_active', False):
                processing_icon = "⚙"
                processing_color = "#00FFFF"
                processing_text = "ACTIVE"
                processing_class = "processing-active"
            else:
                processing_icon = "◯"
                processing_color = "#9E9E9E"
                processing_text = "IDLE"
                processing_class = ""
            
            st.markdown(
                f'<div class="overall-status-card">'
                f'<span class="{processing_class}" style="color: {processing_color};">{processing_icon}</span><br>'
                f'<strong>Processing</strong><br>'
                f'<span class="{processing_class}" style="color: {processing_color};">{processing_text}</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        
        with col4:
            # Live Logs Status
            log_count = len(st.session_state.get('live_logs', []))
            log_icon = "▦"
            log_color = "#FF9800" if log_count > 0 else "#9E9E9E"
            
            st.markdown(
                f'<div class="overall-status-card">'
                f'<span style="color: {log_color};">{log_icon}</span><br>'
                f'<strong>Live Logs</strong><br>'
                f'<span style="color: {log_color};">{log_count} Entries</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Real-time streaming log container (NO TABLES!)
        st.markdown('<div class="live-log-container">', unsafe_allow_html=True)
        
        if not st.session_state.get('live_logs'):
            st.markdown(
                '<div class="stream-message">'
                '<span class="float-icon">◉</span> <strong>Stream Ready</strong> - Engineering logs will appear here in real-time during processing...'
                '</div>', 
                unsafe_allow_html=True
            )
            st.markdown('</div>', unsafe_allow_html=True)
            return

        # STREAMING LOG DISPLAY - Show logs one by one, newest first
        recent_logs = st.session_state.live_logs[-30:]  # Show last 30 logs for performance
        
        for i, log_entry in enumerate(reversed(recent_logs)):
            timestamp = log_entry['timestamp']
            level = log_entry['level']
            raw_message = log_entry.get('raw_message', log_entry['msg'])
            
            # Enhanced level indicators with animations
            level_styles = {
                'INFO': '<span class="log-level-info">◉ INFO</span>',
                'WARNING': '<span class="log-level-warning">△ WARN</span>', 
                'ERROR': '<span class="log-level-error">◯ ERROR</span>',
                'DEBUG': '<span class="log-level-debug">▣ DEBUG</span>',
                'CRITICAL': '<span class="log-level-critical">■ CRITICAL</span>'
            }
            
            level_display = level_styles.get(level, f'<span class="log-level-default">▣ {level}</span>')
            
            # Extract clean message
            message_parts = raw_message.split(' - ', 2) if ' - ' in raw_message else [raw_message]
            actual_message = message_parts[-1] if len(message_parts) > 1 else raw_message
            
            # Create streaming log entry with fade-in animation
            log_opacity = max(0.4, 1.0 - (i * 0.05))  # Fade older logs
            st.markdown(
                f'<div class="stream-log-entry" style="opacity: {log_opacity}; animation-delay: {i * 0.1}s;">'
                f'<span class="log-timestamp">{timestamp}</span> '
                f'{level_display} '
                f'<span class="log-message">{html.escape(actual_message)}</span>'
                f'</div>', 
                unsafe_allow_html=True
            )
        
        # Streaming controls
        st.markdown('<br>', unsafe_allow_html=True)
        ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2, 1, 1, 1])
        
        with ctrl_col1:
            # Debug logging test
            if st.button("🧪 Test Logging", key="test_logging"):
                logger.info("🧪 Test log entry from Streamlit UI")
                logger.warning("⚠️ Test warning message")
                logger.error("❌ Test error message") 
                # Also test module loggers
                import logging
                for module_name in ['main_processor', 'llm_handler', 'database_crud']:
                    test_logger = logging.getLogger(module_name)
                    test_logger.info(f"🔧 Test from {module_name} module")
                st.session_state.last_log_update = datetime.now().timestamp()
                st.rerun()
        
        with ctrl_col2:
            if st.button("⟲ Refresh", key="refresh_live_logs"):
                st.rerun()
        
        with ctrl_col3:
            if st.button("▣ Clear", key="clear_live_logs"):
                st.session_state.live_logs = []
                st.session_state.log_counter = 0
                st.rerun()
        
        with ctrl_col4:
            if st.session_state.get('processing_active', False):
                st.markdown(
                    '<div class="live-indicator"><span class="processing-active">● LIVE</span></div>', 
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div class="idle-indicator"><span style="color: #9E9E9E;">◯ IDLE</span></div>', 
                    unsafe_allow_html=True
                )
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Auto-refresh during active processing with smoother updates
        if st.session_state.get('processing_active', False):
            current_time = datetime.now().timestamp()
            last_update = st.session_state.get('last_log_update', 0)
            
            # More aggressive real-time updates - check for new logs every 0.1 seconds
            if current_time - last_update < 1 or len(st.session_state.get('live_logs', [])) > 0:
                # Use Streamlit's built-in rerun for immediate updates
                st.rerun()
        
        # Also auto-refresh if there are recent logs even when not processing
        elif len(st.session_state.get('live_logs', [])) > 0:
            current_time = datetime.now().timestamp()
            last_update = st.session_state.get('last_log_update', 0)
            
            # Refresh if logs were added in the last 2 seconds
            if current_time - last_update < 2:
                time.sleep(0.2)  # Brief pause to batch updates
                st.rerun()

# --- Main App Layout ---
# st.title("∎ Equinox Document Intelligence Processor")

# === SECTION 1: SYSTEM STATUS & PROCESSING ===
with st.container():
    # st.header("⚙ System Control Center")
    
    # System Status Row
    status_col1, status_col2 = st.columns([1, 1])
    
    with status_col1:
        st.subheader("▣ System Status")
        db_status, db_message = get_db_connection_status()
        
        if db_status:
            st.success("◉ Database: Connected")
        else:
            st.error(f"◯ Database: {db_message}")
            
        if st.session_state.ollama_models:
            st.success(f"⬢ Ollama Models: {', '.join(st.session_state.ollama_models)}")
        else:
            st.warning("△ Ollama Models: None found - Check Ollama server")
    
    with status_col2:
        st.subheader("▦ Processing Status")
        
        # Live processing metrics
        if st.session_state.get('processing_active', False):
            current_file = st.session_state.get('current_doc_name', 'N/A')
            processed = st.session_state.get('processed_files_count', 0)
            total = st.session_state.get('total_files_to_process', 0)
            
            st.markdown(f"""
            <div class="metric-card">
                <span class="processing-active">▲ PROCESSING ACTIVE</span><br>
                <strong>Current:</strong> {current_file}<br>
                <strong>Progress:</strong> {processed}/{total}
            </div>
            """, unsafe_allow_html=True)
            
            if total > 0:
                progress_pct = int((processed / total) * 100)
                st.progress(progress_pct, text=f"Processing: {current_file}")
        else:
            st.info("◉ System Ready - No active processing")

# === SECTION 2: DOCUMENT PROCESSING ===
st.markdown("---")
with st.container():
    st.header("▤ Document Processing")
    
    # Processing tabs
    process_tab1, process_tab2 = st.tabs(["⚙ Process Single File", "▲ Process Folder"])
    
    with process_tab1:
        st.markdown("### 📁 Drag and Drop File Upload")
        st.markdown("Upload a single document (.pdf, .docx, or .pptx) for processing:")
        
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'docx', 'pptx', 'xlsx', 'xls'],
            help="Upload a single document to process. Supported formats: PDF, DOCX, PPTX, Excel"
        )

        if uploaded_file is not None:
            # Create a temporary directory for the uploaded file if it doesn't exist
            temp_dir = Path(UPLOAD_FOLDER) / "temp_uploads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Save the uploaded file
            file_path = temp_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            if st.session_state.ollama_models:
                selected_model = st.selectbox(
                    "Select Ollama Model for Processing:", 
                    st.session_state.ollama_models, 
                    index=0, 
                    key="selected_model_single",
                    help="Choose the LLM model to use for document analysis and information extraction"
                )

                if st.button("⚙ Process Uploaded File", key="process_single_file"):
                    st.session_state.processing_stopped = False
                    st.session_state.processing_active = True
                    st.session_state.auto_show_logs = True
                    st.session_state.live_logs = []  # Clear logs from previous runs
                    
                    logger.info(f"Starting single file processing for: {uploaded_file.name} with model: {selected_model}")
                    
                    # Create beautiful status containers with engineering theme
                    status_col1, status_col2 = st.columns([2, 1])
                    with status_col1:
                        status_container = st.empty()
                        status_container.markdown(
                            f'<div class="processing-status-card">'
                            f'<span class="processing-gear">⚙</span> '
                            f'<span class="processing-active">Initializing {uploaded_file.name}...</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                    with status_col2:
                        progress_container = st.empty()
                        progress_container.markdown(
                            '<div class="progress-status-card">'
                            '<span class="float-icon">🚀</span> <strong class="processing-active">ACTIVE</strong>'
                            '</div>', 
                            unsafe_allow_html=True
                        )
                    
                    try:
                        # Update status during processing with better animations
                        status_container.markdown(
                            f'<div class="processing-status-card">'
                            f'<span class="processing-gear">⚙</span> '
                            f'<span class="processing-active">🧠 AI Analyzing {uploaded_file.name}...</span>'
                            f'</div>', 
                            unsafe_allow_html=True
                        )
                        
                        progress_container.markdown(
                            '<div class="progress-status-card">'
                            '<span class="processing-gear">◉</span> <strong class="processing-active">PROCESSING</strong>'
                            '</div>', 
                            unsafe_allow_html=True
                        )
                        
                        process_documents(
                            selected_llm_model=selected_model,
                            filename=uploaded_file.name,
                            upload_dir=str(temp_dir)
                        )
                        logger.info(f"Successfully processed: {uploaded_file.name}")
                        
                        # Beautiful success animation
                        status_container.markdown(
                            f'<div class="glass-card">✅ <span style="color: #4CAF50; font-weight: bold;">Successfully processed: {uploaded_file.name}</span></div>', 
                            unsafe_allow_html=True
                        )
                        progress_container.markdown(
                            '<div class="glass-card"><span class="float-icon">🎉</span> <strong style="color: #4CAF50;">Complete!</strong></div>', 
                            unsafe_allow_html=True
                        )
                        
                        # Clean up the temporary file after processing
                        try:
                            file_path.unlink()
                            logger.info(f"Cleaned up temporary file: {file_path}")
                        except Exception as e:
                            logger.warning(f"Could not clean up temporary file {file_path}: {e}")
                            
                    except Exception as e:
                        logger.error(f"Error processing {uploaded_file.name}: {e}", exc_info=True)
                        status_container.markdown(
                            f'<div class="glass-card">❌ <span style="color: #F44336; font-weight: bold;">Error processing {uploaded_file.name}: {str(e)}</span></div>', 
                            unsafe_allow_html=True
                        )
                    finally:
                        st.session_state.processing_active = False
            else:
                st.warning("No Ollama models available. Cannot process file.")
    
    with process_tab2:
        st.markdown("### 📂 Process Multiple Files from Folder")
        custom_folder_path = st.text_input(
            "Enter full path to document folder:", 
            key="custom_folder_path", 
            placeholder="e.g., C:\\Users\\YourUser\\Documents\\ProjectFiles or /mnt/network_share/docs"
        )

        if st.session_state.ollama_models:
            selected_model = st.selectbox(
                "Select Ollama Model for Processing:", 
                st.session_state.ollama_models, 
                index=0, 
                key="selected_model_folder",
                help="Choose the LLM model to use for document analysis and information extraction"
            )

            # Processing control buttons
            col1, col2 = st.columns([1, 1])
            
            with col1:
                start_button_disabled = not bool(custom_folder_path.strip()) if custom_folder_path else True
                if st.button("▲ Start Processing", key="start_processing", disabled=start_button_disabled):
                    st.session_state.processing_stopped = False
                    st.session_state.processing_active = True
                    st.session_state.auto_show_logs = True
                    st.session_state.live_logs = [] # Clear logs from previous runs
                    
                    user_provided_path = custom_folder_path.strip()
                    logger.info(f"Starting document processing with model: {selected_model}, folder: {user_provided_path}")
                    
                    discovered_files_info = find_project_files(user_provided_path, force_reprocess=True)
                    
                    if not discovered_files_info:
                        logger.warning(f"No supported files found in the specified folder: {user_provided_path}")
                        st.warning(f"No supported files (.pptx, .pdf, .docx) found in: {user_provided_path}")
                        st.session_state.processing_active = False
                    else:
                        files_to_process_details = discovered_files_info
                        st.session_state.total_files_to_process = len(files_to_process_details)
                        st.session_state.processed_files_count = 0
                        logger.info(f"Found {st.session_state.total_files_to_process} files to process in {user_provided_path}")

                        # Create containers for live updates (no dimming)
                        progress_container = st.empty()
                        status_container = st.empty()
                        
                        def stop_processing_callback():
                            return st.session_state.processing_stopped

                        for i, file_info_dict in enumerate(files_to_process_details):
                            if st.session_state.processing_stopped:
                                logger.info("Processing stopped by user.")
                                break
                            
                            file_path_obj = file_info_dict["file_path"]
                            filename = file_path_obj.name
                            directory_of_file = str(file_path_obj.parent)

                            st.session_state.current_doc_name = filename
                            logger.info(f"Processing document: {filename} ({i+1}/{st.session_state.total_files_to_process})")
                            
                            st.session_state.processed_files_count = i + 1
                            progress_percent = int((st.session_state.processed_files_count / st.session_state.total_files_to_process) * 100)
                            
                            # Update progress and status without dimming
                            progress_container.progress(progress_percent, text=f"Processing: {filename}")
                            status_container.info(f'🚀 Processing {filename} ({i+1}/{st.session_state.total_files_to_process})...')

                            try:
                                process_documents(
                                    selected_llm_model=selected_model, 
                                    filename=filename, 
                                    stop_callback=stop_processing_callback,
                                    upload_dir=directory_of_file
                                )
                                logger.info(f"Successfully processed: {filename}")
                                status_container.success(f"✅ Completed: {filename}")
                            except Exception as e:
                                logger.error(f"Error processing {filename}: {e}", exc_info=True)
                                status_container.error(f"❌ Error: {filename}")
                        
                        progress_container.empty()
                        status_container.empty()
                        st.session_state.current_doc_name = ""
                        st.session_state.processing_active = False
                        if not st.session_state.processing_stopped:
                            logger.info(f"All documents processed from {user_provided_path}.")
                            st.success("◆ All documents processed successfully!")

            with col2:
                if st.button("■ Stop Processing", key="stop_processing"):
                    st.session_state.processing_stopped = True
                    st.session_state.processing_active = False
                    logger.warning("Stop signal received. Processing will halt after the current file.")
        else:
            st.warning("No Ollama models available. Cannot start processing.")

# === SECTION 3: LIVE LOGS (Prominent Display) ===
st.markdown("---")
with st.container():
    st.header("▦ Live Engineering Logs")
    
    # Make logs always visible, not just in tabs
    with st.expander("● Real-Time Process Logs", expanded=st.session_state.get('processing_active', False)):
        display_live_streaming_logs()

# === SECTION 4: KNOWLEDGE BASE EXPLORER ===
st.markdown("---")
with st.container():
    st.header("▧ Knowledge Base Explorer")

    # Create tabs for the explorer
    kb_tab1, kb_tab2, kb_tab3 = st.tabs(["▤ Browse All Projects", "▣ Project Details", "▦ Processed Documents"])

    with kb_tab1: # All Projects Tab
        st.subheader("All Processed Projects")
        
        # Add toggle for view type
        col1, col2 = st.columns([2, 1])
        with col1:
            view_type = st.radio(
                "Choose view type:",
                ["▦ Simple View (Latest Log Only)", "⬢ Comprehensive View (All Content)"],
                horizontal=True,
                key="project_view_type"
            )
        with col2:
            if st.button("⟲ Refresh Project List", key="refresh_projects_simple"):
                if 'simple_projects_list' in st.session_state:
                    del st.session_state.simple_projects_list
                if 'comprehensive_projects_list' in st.session_state:
                    del st.session_state.comprehensive_projects_list

        # Determine which data to show
        use_comprehensive = "Comprehensive" in view_type
        
        if use_comprehensive:
            # Comprehensive view
            if 'comprehensive_projects_list' not in st.session_state:
                db_sess = None
                try:
                    db_sess = get_session()
                    st.session_state.comprehensive_projects_list = get_comprehensive_project_list(db_sess)
                except Exception as e:
                    st.error(f"Error fetching comprehensive projects: {e}")
                    st.session_state.comprehensive_projects_list = []
                finally:
                    if db_sess: db_sess.close()
            
            projects_data = st.session_state.comprehensive_projects_list
            if projects_data:
                # Optimized column configuration for comprehensive view
                st.dataframe(
                    projects_data, 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", width="small"),
                        "Project Name": st.column_config.TextColumn("Project Name", width="medium"),
                        "Created At": st.column_config.TextColumn("Created", width="small"),
                        "Updated At": st.column_config.TextColumn("Updated", width="small"),
                        "Total Logs": st.column_config.NumberColumn("Total Logs", width="small"),
                        "All Log Titles": st.column_config.TextColumn("All Log Titles", width="medium"),
                        "Comprehensive Content": st.column_config.TextColumn("Comprehensive Content", width="large")
                    }
                )
                st.caption(f"⬢ **Comprehensive View**: Showing {len(projects_data)} projects with ALL extraction content aggregated. This includes data from all processed documents for each project.")
            else:
                st.info("No projects found in the database, or an error occurred.")
                
        else:
            # Simple view (existing functionality)
            if 'simple_projects_list' not in st.session_state:
                db_sess = None
                try:
                    db_sess = get_session()
                    st.session_state.simple_projects_list = get_simple_project_list(db_sess)
                except Exception as e:
                    st.error(f"Error fetching projects: {e}")
                    st.session_state.simple_projects_list = []
                finally:
                    if db_sess: db_sess.close()
            
            projects_data = st.session_state.simple_projects_list
            if projects_data:
                # Optimized column configuration for simple view
                st.dataframe(
                    projects_data, 
                    use_container_width=True, 
                    height=500,
                    column_config={
                        "ID": st.column_config.NumberColumn("ID", width="small"),
                        "Project Name": st.column_config.TextColumn("Project Name", width="medium"),
                        "Created At": st.column_config.TextColumn("Created", width="small"),
                        "Updated At": st.column_config.TextColumn("Updated", width="small"),
                        "Latest Log Title": st.column_config.TextColumn("Latest Log Title", width="medium"),
                        "Latest Log Content": st.column_config.TextColumn("Latest Log Content", width="large")
                    }
                )
                st.caption(f"▦ **Simple View**: Showing {len(projects_data)} projects with latest extraction log only. Switch to Comprehensive View to see all gathered content.")
            else:
                st.info("No projects found in the database, or an error occurred.")

    with kb_tab2: # Project Details Tab
        st.subheader("Detailed View: Project → Documents → Key Information")

        # Fetch projects for dropdown if not already fetched by tab1 (or if tab1 failed)
        if 'all_projects_data' not in st.session_state or not st.session_state.all_projects_data:
            db_sess_tab2 = None
            try:
                db_sess_tab2 = get_session()
                st.session_state.all_projects_data_tab2 = get_projects_for_display(db_sess_tab2) # Use a different key if needed or rely on tab1
            except Exception as e:
                st.error(f"Error fetching projects for selection: {e}")
                st.session_state.all_projects_data_tab2 = []
            finally:
                if db_sess_tab2: db_sess_tab2.close()
        else: # Use data possibly fetched by tab1 to avoid re-fetch unless forced
            st.session_state.all_projects_data_tab2 = st.session_state.all_projects_data

        if st.session_state.get('all_projects_data_tab2'):
            project_names_map = {p["Project Name"]: p["ID"] for p in st.session_state.all_projects_data_tab2}
            if not project_names_map: 
                st.info("No projects available to select.")
            else:
                selected_project_name = st.selectbox(
                    "Select a Project:", 
                    options=list(project_names_map.keys()), 
                    key="selected_project_for_details"
                )

                if selected_project_name:
                    selected_project_id = project_names_map[selected_project_name]
                    st.markdown(f"**Displaying details for Project: {selected_project_name} (ID: {selected_project_id})**")

                    # --- Display Project Extraction Log ---
                    st.markdown("---")
                    st.markdown("### Project Extraction Log")
                    log_expander = st.expander("View Full Extraction Log", expanded=False)
                    with log_expander:
                        if st.button("⟲ Refresh Extraction Log", key=f"refresh_extraction_log_{selected_project_id}"):
                            session_key_log = f"extraction_log_for_project_{selected_project_id}"
                            if session_key_log in st.session_state:
                                del st.session_state[session_key_log]

                        session_key_log = f"extraction_log_for_project_{selected_project_id}"
                        if session_key_log not in st.session_state:
                            db_sess_log = None
                            try:
                                db_sess_log = get_session()
                                st.session_state[session_key_log] = get_project_extraction_logs(db_sess_log, selected_project_id)
                            except Exception as e:
                                st.error(f"Error fetching extraction log for project {selected_project_name}: {e}")
                                st.session_state[session_key_log] = []
                            finally:
                                if db_sess_log: db_sess_log.close()
                        
                        extraction_log_data = st.session_state.get(session_key_log, [])
                        if extraction_log_data:
                            # Prepare data for st.dataframe
                            logs_for_df = []
                            for log_item in extraction_log_data:
                                logs_for_df.append({
                                    "Timestamp": log_item.log_entry_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z') if log_item.log_entry_timestamp else 'N/A',
                                    "Title": log_item.log_entry_title or 'N/A',
                                    "Source Document": log_item.source_document_name or 'N/A',
                                    "LLM Action": log_item.llm_verification_action or 'N/A',
                                    "LLM Confidence": f"{log_item.llm_verification_confidence:.2f}" if log_item.llm_verification_confidence is not None else 'N/A',
                                    "LLM Reasoning": log_item.llm_verification_reasoning or 'N/A',
                                    "Content": log_item.log_entry_content # Full content
                                })
                            
                            if logs_for_df:
                                st.dataframe(logs_for_df, use_container_width=True)
                            else:
                                st.info("No extraction log entries to display in table format.")
                        else:
                            st.info("No extraction log entries found for this project.")

                    # Display Documents for the selected project
                    st.markdown("---")
                    st.markdown("**Documents in this Project:**")
                    if st.button("⟲ Refresh Documents", key=f"refresh_docs_{selected_project_id}"):
                        session_key_docs = f'documents_for_project_{selected_project_id}'
                        if session_key_docs in st.session_state: del st.session_state[session_key_docs]

                    session_key_docs = f'documents_for_project_{selected_project_id}'
                    if session_key_docs not in st.session_state:
                        db_sess_docs = None
                        try:
                            db_sess_docs = get_session()
                            st.session_state[session_key_docs] = get_documents_for_project(db_sess_docs, selected_project_id)
                        except Exception as e:
                            st.error(f"Error fetching documents for project {selected_project_name}: {e}")
                            st.session_state[session_key_docs] = []
                        finally:
                            if db_sess_docs: db_sess_docs.close()
                    
                    documents_data = st.session_state.get(session_key_docs, [])
                    if documents_data:
                        docs_df = st.dataframe(documents_data, use_container_width=True, key=f"docs_df_{selected_project_id}")
                        
                        doc_names_map = {d["File Name"]: d["document_id"] for d in documents_data}
                        if doc_names_map:
                            selected_doc_name = st.selectbox(
                                "Select a Document to view its Key Information:",
                                options=list(doc_names_map.keys()),
                                key=f"selected_doc_for_key_info_{selected_project_id}"
                            )
                            if selected_doc_name:
                                selected_doc_id = doc_names_map[selected_doc_name]
                                
                                st.markdown(f"**Extracted Key Information from: {selected_doc_name} (Doc ID: {selected_doc_id})**")
                                st.warning("▣ **Note:** Detailed structured key information (from the `ProjectKeyInformation` table) is currently suspended. Raw LLM outputs for this document (and others for this project) are captured in the 'Project Extraction Log' displayed above.", icon="▣")
                                
                                if st.button("⟲ Refresh Key Info (Old System)", key=f"refresh_keyinfo_{selected_doc_id}"):
                                    session_key_ki = f'keyinfo_for_doc_{selected_doc_id}'
                                    if session_key_ki in st.session_state: del st.session_state[session_key_ki]

                                session_key_ki = f'keyinfo_for_doc_{selected_doc_id}'
                                if session_key_ki not in st.session_state:
                                    db_sess_ki = None
                                    try:
                                        db_sess_ki = get_session()
                                        st.session_state[session_key_ki] = get_key_info_for_document(db_sess_ki, selected_doc_id)
                                    except Exception as e:
                                        st.error(f"Error fetching key info for document {selected_doc_name}: {e}")
                                        st.session_state[session_key_ki] = []
                                    finally:
                                        if db_sess_ki: db_sess_ki.close()
                                
                                key_info_data = st.session_state.get(session_key_ki, [])
                                if key_info_data:
                                    st.dataframe(key_info_data, use_container_width=True, key=f"keyinfo_df_{selected_doc_id}")
                                else:
                                    st.info("No key information extracted or found for this document.")
                        else:
                            st.info("No documents available to select key info from.")
                    else:
                        st.info("No documents found for this project.")
        else:
            st.info("No projects available to select from. Process some documents first or check database connection.")

    with kb_tab3: # View Processed Documents Tab
        st.subheader("All Processed Documents")

        col1, col2 = st.columns([3,1])
        with col1:
            search_term = st.text_input("Search Processed Documents (by File Name, Type, or Project ID):", key="processed_docs_search")
        with col2:
            if st.button("⟲ Refresh List", key="refresh_processed_docs_new_button"):
                st.session_state.processed_docs_list = None # Clear cache to force refresh

        if 'processed_docs_list' not in st.session_state or st.session_state.processed_docs_list is None:
            db_session = None
            try:
                db_session = get_session()
                if db_session:
                    st.session_state.processed_docs_list = get_processed_documents(db_session)
                else:
                    st.session_state.processed_docs_list = []
                    st.error("Failed to connect to the database to fetch processed documents.")
                    st.session_state.db_connection_error_processed_docs = True
            except Exception as e:
                st.session_state.processed_docs_list = []
                logger.error(f"Error fetching processed documents: {e}", exc_info=True)
                st.error(f"An error occurred while fetching processed documents: {e}")
                st.session_state.db_connection_error_processed_docs = True
            finally:
                if db_session:
                    db_session.close()
        
        if 'db_connection_error_processed_docs' not in st.session_state:
            st.session_state.db_connection_error_processed_docs = False

        processed_docs_full_list = st.session_state.get('processed_docs_list', [])
        
        filtered_docs = processed_docs_full_list
        if search_term:
            search_term_lower = search_term.lower()
            filtered_docs = [
                doc for doc in processed_docs_full_list
                if search_term_lower in str(doc.get("File Name", "")).lower() or \
                   search_term_lower in str(doc.get("Type", "")).lower() or \
                   search_term_lower in str(doc.get("Project ID", "")).lower()
            ]

        if filtered_docs:
            st.dataframe(
                filtered_docs, 
                use_container_width=True, 
                height=600,
                column_config={
                    "document_id": st.column_config.NumberColumn("Doc ID", width="small"),
                    "File Name": st.column_config.TextColumn("File Name", width="large"),
                    "Type": st.column_config.TextColumn("Type", width="small"),
                    "Extraction Status": st.column_config.TextColumn("Status", width="medium"),
                    "Processed At": st.column_config.TextColumn("Processed At", width="medium"),
                    "Pages/Slides": st.column_config.NumberColumn("Pages", width="small"),
                    "Project ID": st.column_config.NumberColumn("Project ID", width="small")
                }
            )
            st.caption(f"Showing {len(filtered_docs)} of {len(processed_docs_full_list)} processed documents. Click column headers to sort.")
        elif search_term and not filtered_docs:
            st.info(f"No processed documents found matching your search term: '{search_term}'.")
        elif not processed_docs_full_list and not st.session_state.db_connection_error_processed_docs:
            st.info("No processed documents found in the database.")
        elif not processed_docs_full_list and st.session_state.db_connection_error_processed_docs:
            pass

# === SECTION 5: DATABASE MANAGEMENT ===
st.markdown("---")
with st.container():
    if DATABASE_MANAGEMENT_AVAILABLE:
        try:
            render_database_management_ui()
        except Exception as e:
            st.error(f"Error loading database management interface: {e}")
            st.markdown("### 🗄️ Database Management (Error)")
            st.warning("The database management interface encountered an error. Please check the logs.")
    else:
        st.header("🗄️ Database Management")
        st.warning("Database management interface is not available. Please ensure all required modules are installed.")
        
        # Fallback basic database info
        st.subheader("📊 Basic Database Status")
        db_status, db_message = get_db_connection_status()
        if db_status:
            st.success("🟢 Database Connection: Active")
            
            # Basic statistics
            try:
                session = get_session()
                from database_models import Project, Document, Client
                
                project_count = session.query(Project).count()
                document_count = session.query(Document).count()
                client_count = session.query(Client).count()
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Projects", project_count)
                with col2:
                    st.metric("Documents", document_count)
                with col3:
                    st.metric("Clients", client_count)
                
                session.close()
            except Exception as e:
                st.error(f"Error getting database statistics: {e}")
        else:
            st.error(f"🔴 Database Connection: {db_message}")

# Footer or other sections
st.markdown("---")
st.caption("▣ Equinox Engineering Ltd. - Document Processing Tool")

# --- Example: How to use logger elsewhere ---
# import logging
# logger = logging.getLogger(__name__) # Get logger for the current module
# logger.info("This is an info message from streamlit_app.")
# logger.warning("This is a warning.")
# logger.error("This is an error.")

if __name__ == '__main__':
    # When running with `streamlit run src/gui/streamlit_app.py`,
    # the script executes from top to bottom, and Streamlit handles the app lifecycle.
    # The UI is constructed by the direct calls to st.title, display_status, etc., above.
    # No explicit run_app() call is needed here for that execution model.
    
    # The conditional check for ollama_models was likely an attempt to gate execution,
    # but the UI itself already handles the display based on model availability.
    pass

# logger.error("This is an error.") 

# Add custom CSS to improve the UI and reduce gray overlay prominence
st.markdown(f"""
<style>
    /* Cache buster: {datetime.now().timestamp()} */
    
    /* SIDE MARGIN LAYOUT - RESTORED */
    .main .block-container {{
        max-width: 80% !important;
        width: 80% !important;
        margin: 0 auto !important;
        padding: 1rem !important;
    }}
    
    /* Alternative targeting for different Streamlit versions */
    [data-testid="stAppViewContainer"] {{
        padding-left: 10% !important;
        padding-right: 10% !important;
        box-sizing: border-box !important;
    }}
    
    /* Force container width constraints */
    [data-testid="stAppViewContainer"] .main {{
        max-width: 80% !important;
        width: 80% !important;
        margin-left: 10% !important;
        margin-right: 10% !important;
    }}
    
    div[data-testid="main"] {{
        max-width: 80% !important;
        width: 80% !important;
        margin: 0 auto !important;
        margin-left: 10% !important;
        margin-right: 10% !important;
    }}
    
    /* Import futuristic fonts */
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Exo+2:wght@300;400;600;700&display=swap');
    
    /* DISABLE STREAMLIT DIMMING AND SPINNERS */
    .stSpinner, .stSpinner > div, .stSpinner > div > div {{
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
    }}
    
    .stApp [data-stale="true"] {{
        opacity: 1 !important;
    }}
    
    /* Hide processing notifications */
    .stAlert[data-testid*="running"] {{
        display: none !important;
    }}
    
    /* COMPACT LAYOUT */
    .stContainer, .element-container {{
        padding: 0.4rem !important;
        margin: 0.3rem 0 !important;
    }}
    
    div[data-testid="stVerticalBlock"] {{
        gap: 0.5rem !important;
    }}
    
    .stColumn {{
        padding: 0 0.5rem !important;
    }}
    
    /* ANIMATIONS */
    @keyframes pulse {{
        0% {{ transform: scale(1); opacity: 1; }}
        50% {{ transform: scale(1.02); opacity: 0.9; }}
        100% {{ transform: scale(1); opacity: 1; }}
    }}
    
    @keyframes rotate {{
        from {{ transform: rotate(0deg); }}
        to {{ transform: rotate(360deg); }}
    }}
    
    @keyframes gradientShift {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}
    
    @keyframes float {{
        0%, 100% {{ transform: translateY(0px); }}
        50% {{ transform: translateY(-2px); }}
    }}
    
    /* TITLE STYLING */
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Orbitron', monospace !important;
        background: linear-gradient(45deg, #00FFFF, #0080FF, #FF00FF, #00FFFF) !important;
        background-size: 300% 300% !important;
        -webkit-background-clip: text !important;
        -webkit-text-fill-color: transparent !important;
        background-clip: text !important;
        animation: gradientShift 3s ease-in-out infinite !important;
        margin-top: 0.3rem !important;
        margin-bottom: 0.2rem !important;
        padding: 0 !important;
        font-weight: 600 !important;
        letter-spacing: 1px !important;
        line-height: 1.2 !important;
        text-align: left !important;
    }}
    
    h1::after, h2::after {{
        display: none !important;
    }}
    
    h1 {{
        font-size: 1.8rem !important;
        font-weight: 700 !important;
        margin-bottom: 0.5rem !important;
        letter-spacing: 2px !important;
    }}
    
    h2 {{
        font-size: 1.3rem !important;
        margin-top: 0.5rem !important;
        margin-bottom: 0.3rem !important;
    }}
    
    h3 {{
        font-size: 1.1rem !important;
        margin-top: 0.2rem !important;
        margin-bottom: 0.1rem !important;
    }}
    
    /* BUTTON STYLING */
    .stButton > button {{
        font-family: 'Exo 2', sans-serif !important;
        background: linear-gradient(135deg, #1f77b4, #2196F3, #00FFFF) !important;
        background-size: 200% 200% !important;
        color: white !important;
        border: none !important;
        border-radius: 4px !important;
        padding: 0.4rem 0.8rem !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
        transition: all 0.2s ease !important;
        box-shadow: 0 2px 8px rgba(31, 119, 180, 0.3) !important;
        margin: 0.1rem !important;
        animation: gradientShift 3s ease infinite !important;
    }}
    
    .stButton > button:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(31, 119, 180, 0.4) !important;
        background: linear-gradient(135deg, #2196F3, #00FFFF, #FF00FF) !important;
    }}
    
    /* TAB STYLING */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 3px !important;
        background: rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(10px) !important;
        padding: 3px !important;
        border-radius: 4px !important;
        margin-bottom: 0.5rem !important;
        border: 1px solid rgba(0, 255, 255, 0.3) !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
    }}
    
    .stTabs [data-baseweb="tab"] {{
        font-family: 'Exo 2', sans-serif !important;
        border-radius: 4px !important;
        padding: 0.4rem 0.8rem !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
        background: rgba(255, 255, 255, 0.1) !important;
        color: white !important;
    }}
    
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.8), rgba(0, 255, 255, 0.3)) !important;
        color: #00FFFF !important;
        box-shadow: 0 2px 8px rgba(0, 255, 255, 0.3) !important;
    }}
    
    /* TEXT STYLING */
    .stMarkdown, .stText, p, span, div {{
        font-family: 'Exo 2', sans-serif !important;
        color: white !important;
        background: transparent !important;
        padding: 0 !important;
        margin: 0.1rem 0 !important;
        line-height: 1.3 !important;
        font-size: 0.9rem !important;
    }}
    
    /* DATAFRAME STYLING */
    .stDataFrame {{
        background: rgba(0, 0, 0, 0.6) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 4px !important;
        border: 1px solid rgba(0, 255, 255, 0.3) !important;
        margin: 0.2rem 0 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        overflow-x: auto !important;
        max-width: 100% !important;
    }}
    
    .stDataFrame table {{
        background: rgba(0, 0, 0, 0.8) !important;
        font-size: 0.85rem !important;
        min-width: 100% !important;
    }}
    
    .stDataFrame th {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.7), rgba(0, 255, 255, 0.3)) !important;
        color: white !important;
        padding: 0.4rem !important;
        font-size: 0.85rem !important;
        white-space: nowrap !important;
    }}
    
    .stDataFrame td {{
        padding: 0.3rem !important;
        border: none !important;
        font-size: 0.8rem !important;
        white-space: nowrap !important;
        color: white !important;
        background: rgba(0, 0, 0, 0.4) !important;
    }}
    
    .stDataFrame td:hover,
    .stDataFrame tr:hover td {{
        background: rgba(0, 255, 255, 0.2) !important;
        color: #00FFFF !important;
    }}
    
    /* METRIC CARDS */
    .metric-card {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.3), rgba(0, 255, 255, 0.1)) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 4px !important;
        padding: 0.4rem !important;
        border: 1px solid rgba(0, 255, 255, 0.4) !important;
        margin: 0.1rem !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3) !important;
        font-size: 0.85rem !important;
        line-height: 1.2 !important;
    }}
    
    /* PROCESSING INDICATORS */
    .processing-active {{
        animation: pulse 2s ease-in-out infinite !important;
        color: #00FFFF !important;
        font-family: 'Exo 2', sans-serif !important;
    }}
    
    .processing-gear {{
        animation: rotate 2s linear infinite !important;
        display: inline-block !important;
        color: white !important;
    }}
    
    .float-icon {{
        animation: float 3s ease-in-out infinite !important;
        color: white !important;
    }}
    
    /* STATUS CARDS */
    .processing-status-card {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.3), rgba(0, 255, 255, 0.2)) !important;
        backdrop-filter: blur(15px) !important;
        border-radius: 6px !important;
        border: 2px solid rgba(0, 255, 255, 0.5) !important;
        padding: 0.8rem !important;
        margin: 0.3rem 0 !important;
        box-shadow: 0 4px 12px rgba(0, 255, 255, 0.3) !important;
        font-size: 1rem !important;
        animation: pulse 2s ease-in-out infinite !important;
        text-align: center !important;
    }}
    
    /* LOG CONTAINER */
    .live-log-container {{
        background: transparent !important;
        border-radius: 4px !important;
        border: 1px solid rgba(0, 255, 255, 0.3) !important;
        padding: 0.5rem !important;
        margin: 0.3rem 0 !important;
        max-height: 500px !important;
        height: 500px !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }}
    
    .live-log-container::-webkit-scrollbar {{
        width: 8px !important;
    }}
    
    .live-log-container::-webkit-scrollbar-track {{
        background: rgba(0, 0, 0, 0.2) !important;
        border-radius: 4px !important;
    }}
    
    .live-log-container::-webkit-scrollbar-thumb {{
        background: linear-gradient(45deg, #00FFFF, #0080FF) !important;
        border-radius: 4px !important;
    }}
    
    /* LOG ENTRIES */
    .stream-log-entry {{
        display: block !important;
        padding: 0.3rem 0.5rem !important;
        margin: 0.2rem 0 !important;
        background: rgba(0, 0, 0, 0.4) !important;
        border-left: 2px solid rgba(0, 255, 255, 0.5) !important;
        border-radius: 3px !important;
        font-family: 'Exo 2', monospace !important;
        font-size: 0.85rem !important;
        line-height: 1.3 !important;
    }}
    
    .stream-log-entry:hover {{
        background: rgba(0, 255, 255, 0.1) !important;
        border-left-color: #00FFFF !important;
    }}
    
    /* LOG LEVELS */
    .log-level-info {{ color: #4CAF50 !important; font-weight: 600 !important; }}
    .log-level-warning {{ color: #FF9800 !important; font-weight: 600 !important; }}
    .log-level-error {{ color: #F44336 !important; font-weight: 700 !important; }}
    .log-level-debug {{ color: #9E9E9E !important; font-weight: 400 !important; }}
    .log-level-critical {{ color: #FF1744 !important; font-weight: 700 !important; }}
    .log-level-default {{ color: #03DAC6 !important; font-weight: 500 !important; }}
    
    .log-timestamp {{ color: #B0BEC5 !important; font-size: 0.8rem !important; margin-right: 0.5rem !important; }}
    .log-message {{ color: white !important; word-wrap: break-word !important; }}
    
    /* HORIZONTAL STATUS DASHBOARD - FIXED */
    .overall-status-dashboard {{
        display: flex !important;
        flex-direction: row !important;
        justify-content: space-evenly !important;
        align-items: center !important;
        gap: 1rem !important;
        margin: 1rem 0 !important;
        padding: 1rem !important;
        width: 100% !important;
        background: rgba(0, 0, 0, 0.3) !important;
        border-radius: 6px !important;
        border: 1px solid rgba(0, 255, 255, 0.2) !important;
    }}
    
    .overall-status-card {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.2), rgba(0, 255, 255, 0.1)) !important;
        backdrop-filter: blur(10px) !important;
        border-radius: 4px !important;
        padding: 0.6rem !important;
        border: 1px solid rgba(0, 255, 255, 0.3) !important;
        text-align: center !important;
        font-size: 0.9rem !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2) !important;
        flex: 1 !important;
        min-width: 120px !important;
        max-width: 200px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }}
    
    /* STREAMLIT STATUS ELEMENTS */
    .stSuccess, .stError, .stWarning, .stInfo {{
        margin: 0.3rem 0 !important;
        padding: 0.5rem !important;
        border-radius: 4px !important;
        font-family: 'Exo 2', sans-serif !important;
        font-size: 0.9rem !important;
    }}
    
    .stSuccess {{
        background: rgba(76, 175, 80, 0.2) !important;
        border: 1px solid rgba(76, 175, 80, 0.5) !important;
        color: #4CAF50 !important;
    }}
    
    .stError {{
        background: rgba(244, 67, 54, 0.2) !important;
        border: 1px solid rgba(244, 67, 54, 0.5) !important;
        color: #F44336 !important;
    }}
    
    .stWarning {{
        background: rgba(255, 152, 0, 0.2) !important;
        border: 1px solid rgba(255, 152, 0, 0.5) !important;
        color: #FF9800 !important;
    }}
    
    .stInfo {{
        background: rgba(33, 150, 243, 0.2) !important;
        border: 1px solid rgba(33, 150, 243, 0.5) !important;
        color: #2196F3 !important;
    }}
    
    /* SIDEBAR STYLING - FIXED WIDTH CONSTRAINTS */
    .css-1d391kg, .css-1lcbmhc, .css-1outpf7, [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.8)) !important;
        backdrop-filter: blur(15px) !important;
        border-right: 2px solid rgba(0, 255, 255, 0.3) !important;
        box-shadow: 2px 0 10px rgba(0, 0, 0, 0.5) !important;
        max-width: 300px !important;
        min-width: 250px !important;
        width: 280px !important;
        position: fixed !important;
        left: 0 !important;
        top: 0 !important;
        height: 100vh !important;
        z-index: 999 !important;
        overflow-y: auto !important;
        overflow-x: hidden !important;
    }}
    
    /* Ensure sidebar doesn't expand beyond its container */
    .css-1d391kg .stContainer, .css-1lcbmhc .stContainer, [data-testid="stSidebar"] .stContainer {{
        max-width: 100% !important;
        width: 100% !important;
        padding: 0.5rem !important;
        margin: 0 !important;
    }}
    
    /* Sidebar content styling */
    .css-1d391kg .stMarkdown, .css-1lcbmhc .stMarkdown, [data-testid="stSidebar"] .stMarkdown {{
        color: white !important;
        font-family: 'Exo 2', sans-serif !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
    }}
    
    .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3, 
    .css-1lcbmhc h1, .css-1lcbmhc h2, .css-1lcbmhc h3,
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {{
        color: #00FFFF !important;
        font-family: 'Orbitron', monospace !important;
        font-size: 1rem !important;
        margin: 0.5rem 0 !important;
        text-shadow: 0 0 10px rgba(0, 255, 255, 0.5) !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
    }}
    
    .css-1d391kg .stButton > button, .css-1lcbmhc .stButton > button, [data-testid="stSidebar"] .stButton > button {{
        background: linear-gradient(135deg, rgba(31, 119, 180, 0.8), rgba(0, 255, 255, 0.3)) !important;
        border: 1px solid rgba(0, 255, 255, 0.5) !important;
        color: white !important;
        font-size: 0.8rem !important;
        padding: 0.3rem 0.6rem !important;
        margin: 0.2rem 0 !important;
        border-radius: 4px !important;
        transition: all 0.2s ease !important;
        width: 100% !important;
        max-width: 100% !important;
        box-sizing: border-box !important;
    }}
    
    .css-1d391kg .stButton > button:hover, .css-1lcbmhc .stButton > button:hover, [data-testid="stSidebar"] .stButton > button:hover {{
        background: linear-gradient(135deg, rgba(0, 255, 255, 0.6), rgba(31, 119, 180, 0.8)) !important;
        box-shadow: 0 0 15px rgba(0, 255, 255, 0.4) !important;
        transform: translateY(-1px) !important;
    }}
    
    .css-1d391kg .stSelectbox, .css-1lcbmhc .stSelectbox, [data-testid="stSidebar"] .stSelectbox {{
        background: rgba(0, 0, 0, 0.5) !important;
        border-radius: 4px !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stSlider, .css-1lcbmhc .stSlider, [data-testid="stSidebar"] .stSlider {{
        background: transparent !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stMetric, .css-1lcbmhc .stMetric, [data-testid="stSidebar"] .stMetric {{
        background: rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(0, 255, 255, 0.2) !important;
        border-radius: 4px !important;
        padding: 0.5rem !important;
        margin: 0.2rem 0 !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stExpander, .css-1lcbmhc .stExpander, [data-testid="stSidebar"] .stExpander {{
        background: rgba(0, 0, 0, 0.4) !important;
        border: 1px solid rgba(0, 255, 255, 0.2) !important;
        border-radius: 4px !important;
        margin: 0.3rem 0 !important;
        max-width: 100% !important;
    }}
    
    /* Sidebar text styling */
    .css-1d391kg .stText, .css-1lcbmhc .stText, [data-testid="stSidebar"] .stText,
    .css-1d391kg p, .css-1lcbmhc p, [data-testid="stSidebar"] p {{
        color: #E0E0E0 !important;
        font-size: 0.85rem !important;
        line-height: 1.3 !important;
        max-width: 100% !important;
        word-wrap: break-word !important;
    }}
    
    /* Sidebar success/error/warning styling */
    .css-1d391kg .stSuccess, .css-1lcbmhc .stSuccess, [data-testid="stSidebar"] .stSuccess {{
        background: rgba(76, 175, 80, 0.2) !important;
        border: 1px solid rgba(76, 175, 80, 0.5) !important;
        color: #4CAF50 !important;
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
        margin: 0.2rem 0 !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stError, .css-1lcbmhc .stError, [data-testid="stSidebar"] .stError {{
        background: rgba(244, 67, 54, 0.2) !important;
        border: 1px solid rgba(244, 67, 54, 0.5) !important;
        color: #F44336 !important;
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
        margin: 0.2rem 0 !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stWarning, .css-1lcbmhc .stWarning, [data-testid="stSidebar"] .stWarning {{
        background: rgba(255, 152, 0, 0.2) !important;
        border: 1px solid rgba(255, 152, 0, 0.5) !important;
        color: #FF9800 !important;
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
        margin: 0.2rem 0 !important;
        max-width: 100% !important;
    }}
    
    .css-1d391kg .stInfo, .css-1lcbmhc .stInfo, [data-testid="stSidebar"] .stInfo {{
        background: rgba(33, 150, 243, 0.2) !important;
        border: 1px solid rgba(33, 150, 243, 0.5) !important;
        color: #2196F3 !important;
        font-size: 0.8rem !important;
        padding: 0.3rem !important;
        margin: 0.2rem 0 !important;
        max-width: 100% !important;
    }}
    
    /* Ensure main content doesn't overlap with fixed sidebar */
    .main {{
        margin-left: 300px !important;
        padding-left: 1rem !important;
    }}
    
    /* COMPACT LAYOUT */
</style>
""", unsafe_allow_html=True) 