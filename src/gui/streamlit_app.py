import streamlit as st
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
import html
import json
import base64
import time
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import pandas as pd

# --- Streamlit Page Configuration ---
# MUST be the first Streamlit command called.
st.set_page_config(
    page_title="Equinox Document Intelligence Processor", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state variables at the very top
if 'live_logs' not in st.session_state:
    st.session_state.live_logs = []
if 'log_counter' not in st.session_state:
    st.session_state.log_counter = 0

# --- Enhanced Real-Time Logging System ---
class QueueLogHandler(logging.Handler):
    """A logging handler that puts records into a queue."""
    def __init__(self, log_queue: Queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(record)

class AdvancedStreamlitLogHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        log_entry = self.format(record)
        st.session_state.log_counter += 1
        
        enhanced_log = {
            "id": st.session_state.log_counter,
            "level": record.levelname,
            "msg": log_entry,
            "timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
            "module": record.name,
            "raw_message": record.getMessage()
        }
        
        st.session_state.live_logs.append(enhanced_log)
        
        if len(st.session_state.live_logs) > 150:
            st.session_state.live_logs = st.session_state.live_logs[-150:]
        
        if st.session_state.get('processing_active', False):
            st.session_state.last_log_update = datetime.now().timestamp()

# Configure root logger
log_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger() 
logger.setLevel(logging.INFO)

for handler in logger.handlers[:]:
    logger.removeHandler(handler)

streamlit_handler = AdvancedStreamlitLogHandler()
streamlit_handler.setFormatter(log_formatter)
logger.addHandler(streamlit_handler)

console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

module_loggers = [
    'main_processor', 'llm_handler', 'database_crud', 'file_system_handler',
    'src.main_processor', 'src.llm_handler', 'src.database_crud', 
    'src.file_system_handler', '__main__'
]

for module_name in module_loggers:
    module_logger = logging.getLogger(module_name)
    module_logger.setLevel(logging.INFO)
    if streamlit_handler not in module_logger.handlers:
        module_logger.addHandler(streamlit_handler)
    if console_handler not in module_logger.handlers:
        module_logger.addHandler(console_handler)
    module_logger.propagate = True

logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('requests').setLevel(logging.WARNING)
logging.getLogger('streamlit').setLevel(logging.WARNING)

if 'logging_initialized' not in st.session_state:
    logger.info("🔧 Enhanced logging system initialized - capturing all module logs")
    st.session_state.logging_initialized = True

from src.main_processor import process_documents
from src.llm_handler import get_available_ollama_models
from src.db_logic import (
    get_db_connection_status,
    get_session,
    get_all_project_names,
    get_project_data
)
from src.database_models import create_tables, get_db_engine, Project
from sqlalchemy import inspect
from src.file_system_handler import list_files_in_upload_folder, clear_upload_folder, get_file_stats, UPLOAD_FOLDER, find_project_files

# --- DATABASE INITIALIZATION CHECK ---
def ensure_database_initialized():
    """
    Checks if the database tables exist and creates them if they don't.
    This makes the app more robust and removes dependency on running setup scripts.
    """
    if 'db_initialized' not in st.session_state or not st.session_state.db_initialized:
        try:
            logger.info("Verifying database initialization...")
            engine = get_db_engine()
            inspector = inspect(engine)
            
            if not inspector.has_table("Projects"):
                logger.warning("Database tables not found! Initializing database...")
                st.toast("🔧 First-time setup: Initializing database tables...", icon="🎉")
                create_tables(engine)
                logger.info("✅ Database tables created successfully.")
                st.toast("✅ Database ready!", icon="🚀")
                st.session_state.db_initialized = True
            else:
                logger.info("Database is already initialized.")
                st.session_state.db_initialized = True
        except Exception as e:
            logger.error(f"❌ Database initialization check failed: {e}", exc_info=True)
            st.error(f"A critical error occurred while checking database status: {e}")
            st.stop()

# Call the initialization check at the start of the app
ensure_database_initialized()

try:
    from src.gui.database_management_ui import render_database_management_ui
    DATABASE_MANAGEMENT_AVAILABLE = True
except ImportError as e:
    DATABASE_MANAGEMENT_AVAILABLE = False

# --- DATABASE SESSION MANAGER ---
class DatabaseSessionManager:
    """
    Manages database sessions for Streamlit app to prevent 'too many clients' errors.
    Uses connection pooling and proper session lifecycle management.
    """
    
    def __init__(self):
        self.session_pool = {}
        self.max_sessions = 5  # Limit concurrent sessions
        self.session_timeout = 300  # 5 minutes timeout
        
    @contextmanager
    def get_managed_session(self, session_key: str = "default"):
        """
        Context manager that provides a database session with automatic cleanup.
        Uses session pooling to prevent too many connections.
        """
        session = None
        try:
            # Check if we have a cached session
            if session_key in st.session_state.get('db_sessions', {}):
                session_info = st.session_state.db_sessions[session_key]
                # Check if session is still valid and not timed out
                if (datetime.now() - session_info['created']).seconds < self.session_timeout:
                    session = session_info['session']
                    # Test if session is still alive
                    try:
                        session.execute("SELECT 1")
                        yield session
                        return
                    except Exception:
                        # Session is dead, remove it and create new one
                        try:
                            session.close()
                        except:
                            pass
                        del st.session_state.db_sessions[session_key]
                        session = None
                else:
                    # Session timed out, clean it up
                    try:
                        session_info['session'].close()
                    except:
                        pass
                    del st.session_state.db_sessions[session_key]
                    session = None
            
            # Create new session if needed
            if session is None:
                session = get_session()
                
                # Initialize session cache if needed
                if 'db_sessions' not in st.session_state:
                    st.session_state.db_sessions = {}
                
                # Clean up old sessions if we have too many
                if len(st.session_state.db_sessions) >= self.max_sessions:
                    oldest_key = min(st.session_state.db_sessions.keys(), 
                                   key=lambda k: st.session_state.db_sessions[k]['created'])
                    try:
                        st.session_state.db_sessions[oldest_key]['session'].close()
                    except:
                        pass
                    del st.session_state.db_sessions[oldest_key]
                
                # Cache the new session
                st.session_state.db_sessions[session_key] = {
                    'session': session,
                    'created': datetime.now()
                }
            
            yield session
            
        except Exception as e:
            if session:
                try:
                    session.rollback()
                except:
                    pass
            raise e
        finally:
            # Don't close the session here - let it be reused
            pass
    
    def cleanup_all_sessions(self):
        """Clean up all cached database sessions."""
        if 'db_sessions' in st.session_state:
            for session_info in st.session_state.db_sessions.values():
                try:
                    session_info['session'].close()
                except:
                    pass
            st.session_state.db_sessions = {}

# Initialize the session manager
if 'db_session_manager' not in st.session_state:
    st.session_state.db_session_manager = DatabaseSessionManager()

db_manager = st.session_state.db_session_manager

# --- Global Variables & Session State ---
if 'processing_stopped' not in st.session_state:
    st.session_state.processing_stopped = False
if 'processing_active' not in st.session_state:
    st.session_state.processing_active = False
if 'auto_show_logs' not in st.session_state:
    st.session_state.auto_show_logs = False
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
                    with db_manager.get_managed_session("sidebar_stats") as session:
                        project_count = session.query(Project).count()
                        # document_count = session.query(Document).count() # Obsolete
                        # client_count = session.query(Client).count() # Obsolete
                        
                        st.metric("Projects", project_count)
                        # st.metric("Documents", document_count)
                        # st.metric("Clients", client_count)
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}...")
                
                # Database operations
                st.markdown("**Database Operations:**")
                if st.button("📤 Export All Data", help="Export database to CSV/JSON"):
                    try:
                        from src.scripts.database_manager import DatabaseManager
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
                            from src.scripts.database_manager import DatabaseManager
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
                from src.scripts.docker_db_manager import DockerDBManager
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
            temp_dir = Path(UPLOAD_FOLDER) / "temp_uploads"
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            file_path = temp_dir / uploaded_file.name
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            if st.session_state.ollama_models:
                # Set the desired default model
                preferred_model = "gemma3:12b"
                model_options = st.session_state.ollama_models
                default_index = 0
                if preferred_model in model_options:
                    default_index = model_options.index(preferred_model)

                selected_model = st.selectbox(
                    "Select Ollama Model for Processing:", 
                    model_options, 
                    index=default_index, 
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
                        
                        # Use the managed session from the UI for processing
                        with db_manager.get_managed_session("single_file_processing") as process_session:
                            process_documents(
                                selected_llm_model=selected_model,
                                filename=uploaded_file.name,
                                upload_dir=str(temp_dir),
                                db_session=process_session # Pass the session here
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
        st.markdown("Select a folder containing documents (.pdf, .docx, .pptx) for batch processing.")

        if 'custom_folder_path' not in st.session_state:
            st.session_state.custom_folder_path = ""

        custom_folder_path = st.text_input(
            "Enter full path to document folder:",
            value=st.session_state.custom_folder_path,
            key="folder_path_input",
            placeholder="e.g., C:\\Users\\YourUser\\Documents\\ProjectFiles"
        )
        st.session_state.custom_folder_path = custom_folder_path

        if custom_folder_path and not Path(custom_folder_path).is_dir():
            st.error("❌ The provided path is not a valid directory. Please check the path and try again.", icon="🚨")
        elif custom_folder_path:
            st.success(f"✅ Valid folder selected: {custom_folder_path}")

            if st.session_state.ollama_models:
                col1, col2 = st.columns([2,1])
                with col1:
                    # Set the desired default model
                    preferred_model = "gemma3:12b"
                    model_options = st.session_state.ollama_models
                    default_index = 0
                    if preferred_model in model_options:
                        default_index = model_options.index(preferred_model)

                    selected_model = st.selectbox(
                        "Select Ollama Model for Processing:",
                        model_options,
                        index=default_index,
                        key="selected_model_folder",
                        help="Choose the LLM model for document analysis."
                    )
                with col2:
                    num_workers = st.slider(
                        "Parallel Processing Workers:", 
                        min_value=1, 
                        max_value=10, 
                        value=4, 
                        key="num_workers",
                        help="Number of files to process in parallel. Increase for faster processing, but be mindful of system resources."
                    )

                def run_batch_processing(folder_path, model, workers):
                    """Encapsulates the logic for running the batch processing."""
                    st.session_state.processing_stopped = False
                    st.session_state.processing_active = True
                    st.session_state.live_logs = []
                    log_queue = Queue()

                    user_provided_path = folder_path.strip()
                    logger.info(f"Starting batch processing with model: {model}, folder: {user_provided_path}, workers: {workers}")

                    path_to_scan = Path(user_provided_path)
                    if not path_to_scan.is_dir():
                        st.error(f"Error: The provided path is not a valid directory or is not accessible: {user_provided_path}", icon="🚫")
                        logger.error(f"User provided an invalid or inaccessible directory: {user_provided_path}")
                        st.session_state.processing_active = False
                        return

                    try:
                        with st.spinner("Discovering processable files in the folder..."):
                            files_to_process = find_project_files(user_provided_path, force_reprocess=True)
                    except Exception as e:
                        logger.error(f"An error occurred during file discovery in {user_provided_path}: {e}", exc_info=True)
                        st.error(f"An unexpected error occurred while scanning the folder: {e}. Check logs for details.", icon="🔥")
                        st.session_state.processing_active = False
                        return

                    if not files_to_process:
                        st.warning(f"No supported files (.pptx, .pdf, .docx) found in: {user_provided_path}", icon="ℹ️")
                        logger.warning(f"No supported files found in: {user_provided_path}")
                        st.session_state.processing_active = False
                        return
                    
                    st.session_state.total_files_to_process = len(files_to_process)
                    st.session_state.processed_files_count = 0
                    st.session_state.processing_errors = []
                    logger.info(f"Found {st.session_state.total_files_to_process} files to process.")

                    progress_container = st.empty()
                    status_container = st.empty()
                    
                    def process_single_doc_worker(file_info, log_queue, db_session):
                        if st.session_state.get('processing_stopped', False):
                            return "Skipped"
                        
                        file_path_obj = file_info["file_path"]
                        filename = file_path_obj.name
                        directory = str(file_path_obj.parent)

                        # Reconfigure logging for this thread to be thread-safe
                        root_logger = logging.getLogger()
                        original_handlers = root_logger.handlers[:]
                        
                        # The main streamlit handler is not thread-safe, so we remove it
                        # and use a queue handler to pass logs back to the main thread.
                        thread_handlers = [h for h in original_handlers if h is not streamlit_handler]
                        thread_handlers.append(QueueLogHandler(log_queue))
                        root_logger.handlers = thread_handlers
                        
                        try:
                            logger.info(f"Starting processing for: {filename}")
                            # Pass the single, managed session to the processor
                            process_documents(
                                selected_llm_model=model,
                                filename=filename,
                                upload_dir=directory,
                                db_session=db_session
                            )
                            logger.info(f"Successfully processed: {filename}")
                            return "Success"
                        except Exception as e:
                            logger.error(f"Error processing {filename}: {e}", exc_info=True)
                            st.session_state.processing_errors.append(filename)
                            return "Error"
                        finally:
                            # Restore the original logging configuration for the root logger
                            root_logger.handlers = original_handlers

                    # Acquire a single session to be shared by all threads in the pool
                    with db_manager.get_managed_session("batch_processing") as shared_db_session:
                        with ThreadPoolExecutor(max_workers=workers) as executor:
                            # Pass the shared session to each worker
                            future_to_file = {executor.submit(process_single_doc_worker, file_info, log_queue, shared_db_session): file_info for file_info in files_to_process}
                            
                            for future in as_completed(future_to_file):
                                # Process any logs that have been queued from the worker threads
                                while not log_queue.empty():
                                    try:
                                        record = log_queue.get_nowait()
                                        streamlit_handler.emit(record)
                                    except Exception as e:
                                        print(f"Error processing log queue: {e}")

                                if st.session_state.get('processing_stopped', False):
                                    break
                                
                                file_info = future_to_file[future]
                                filename = file_info["file_path"].name
                                st.session_state.processed_files_count += 1
                                
                                progress = st.session_state.processed_files_count / st.session_state.total_files_to_process
                                progress_container.progress(progress, text=f"Processing: {filename} ({st.session_state.processed_files_count}/{st.session_state.total_files_to_process})")
                                
                                try:
                                    result = future.result()
                                    if result == "Success":
                                        status_container.success(f"✅ Completed: {filename}", icon="🚀")
                                    elif result == "Error":
                                        status_container.warning(f"⚠️ Error processing: {filename}. See logs for details.", icon="🔥")
                                except Exception as exc:
                                    logger.error(f'{filename} generated an exception: {exc}')
                                    status_container.error(f"❌ Critical error processing {filename}. Check logs.")

                    st.session_state.processing_active = False
                    total_processed = st.session_state.processed_files_count
                    total_errors = len(st.session_state.processing_errors)
                    
                    st.balloons()
                    st.success(f"🎉 **Batch Processing Complete!** 🎉")
                    st.markdown(f"- **Total Files Processed:** {total_processed}")
                    st.markdown(f"- **Successful:** {total_processed - total_errors}")
                    if total_errors > 0:
                        st.error(f"- **Errors:** {total_errors}")
                        with st.expander("Files with errors:"):
                            st.json(st.session_state.processing_errors)
                    
                    st.session_state.total_files_to_process = 0
                    st.session_state.processed_files_count = 0
                    st.session_state.processing_errors = []

                # Processing control buttons
                start_button_disabled = not bool(custom_folder_path.strip())
                if st.button("🚀 Start Batch Processing", key="start_processing", disabled=start_button_disabled, use_container_width=True):
                    run_batch_processing(custom_folder_path, selected_model, num_workers)

            else:
                st.warning("No Ollama models available. Cannot process folder.")
                
            with col2:
                if st.session_state.get('processing_active', False):
                    if st.button("🛑 Stop Processing", key="stop_processing", use_container_width=True):
                        st.session_state.processing_stopped = True
                        logger.warning("Stop processing signal received. Will stop after current files complete.")
                        st.warning("🛑 Stopping... please wait for active files to finish.")

# === SECTION 3: LIVE LOGS (Prominent Display) ===
st.markdown("---")
with st.container():
    st.header("▦ Live Engineering Logs")
    
    # Make logs always visible, not just in tabs
    with st.expander("● Real-Time Process Logs", expanded=st.session_state.get('processing_active', False)):
        display_live_streaming_logs()

# === SECTION 4: PROJECT DATA VIEWER (REFACTORED) ===
st.markdown("---")
with st.container():
    st.header("▧ Project Data Viewer")
    st.markdown("Browse the aggregated text snippets for each project.")

    try:
        with db_manager.get_managed_session("project_viewer") as session:
            
            projects = session.query(Project).order_by(Project.category, Project.project_name).all()

            col1, col2 = st.columns([3, 1])
            with col2:
                if st.button("⟲ Refresh Project List", key="refresh_projects_new_view", use_container_width=True):
                    st.rerun()

            if not projects:
                st.info("No projects found in the database. Process documents using the 'Document Processing' section above to get started.", icon="ℹ️")
            else:
                # Create two columns for cascading dropdowns
                cat_select_col, proj_select_col = st.columns(2)

                # Get unique categories, sorting them and placing "Uncategorized" at the end.
                all_categories = sorted(list(set(p.category for p in projects if p.category)))
                if any(p.category is None for p in projects):
                    all_categories.append("Uncategorized")
                
                with cat_select_col:
                    selected_category = st.selectbox(
                        "Filter by Category",
                        options=all_categories
                    )

                # Filter projects based on the selected category
                if selected_category == "Uncategorized":
                    projects_in_category = [p for p in projects if p.category is None]
                else:
                    projects_in_category = [p for p in projects if p.category == selected_category]

                project_map = {p.project_name: p for p in projects_in_category}

                with proj_select_col:
                    # Only show project dropdown if there are projects in the selected category
                    if project_map:
                        selected_project_name = st.selectbox(
                            "Select Project",
                            options=list(project_map.keys())
                        )
                    else:
                        selected_project_name = None
                        st.write("No projects in this category.")

                # Get the selected project object
                if selected_project_name:
                    selected_project = project_map[selected_project_name]
                    
                    # Display the full categorization for the selected project
                    st.markdown("---")
                    cat_disp_col, sub_cat_col, scope_col = st.columns(3)
                    with cat_disp_col:
                        st.metric("Category", selected_project.category or "N/A")
                    with sub_cat_col:
                        st.metric("Sub-Category", selected_project.sub_category or "N/A")
                    with scope_col:
                        st.metric("Project Scope", selected_project.project_scope or "N/A")
                    st.markdown("---")

                    project_data = selected_project.aggregated_data
                    
                    st.markdown(f"####  Aggregated Data for: **{selected_project.project_name}**")
                    st.text_area(
                        label="Scroll through the collected text snippets below.",
                        value=project_data or "No data has been aggregated for this project yet.",
                        height=600,
                        disabled=True,
                        key=f"data_for_{selected_project.project_name}"
                    )
    except Exception as e:
        logger.error(f"Failed to load Project Data Viewer: {e}", exc_info=True)
        st.error(f"An error occurred while loading project data: {e}", icon="🔥")

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
                with db_manager.get_managed_session("fallback_stats") as session:
                    project_count = session.query(Project).count()
                    # document_count = session.query(Document).count() # Obsolete
                    # client_count = session.query(Client).count() # Obsolete
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Projects", project_count)
                    with col2:
                        st.metric("Documents", 0) # Placeholder
                    with col3:
                        st.metric("Clients", 0) # Placeholder
            except Exception as e:
                st.error(f"Error getting database statistics: {e}")
        else:
            st.error(f"🔴 Database Connection: {db_message}")

# --- DEBUGGING SECTION ---
st.markdown("---")
with st.expander("🔬 Debug & System Info"):
    st.subheader("Raw Project Database View")
    try:
        with db_manager.get_managed_session("debug_raw_view") as session:
            all_projects_data = session.query(Project).all()
            if all_projects_data:
                # Convert to a list of dictionaries for pandas
                data_for_df = [
                    {
                        "ID": p.project_id,
                        "Name": p.project_name,
                        "Category": p.category,
                        "Sub-Category": p.sub_category,
                        "Scope": p.project_scope,
                        "Updated": p.updated_at.strftime('%Y-%m-%d %H:%M:%S')
                    }
                    for p in all_projects_data
                ]
                import pandas as pd
                df = pd.DataFrame(data_for_df)
                st.dataframe(df)
            else:
                st.write("No projects in the database to display.")
    except Exception as e:
        st.error(f"Error loading debug view: {e}")


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