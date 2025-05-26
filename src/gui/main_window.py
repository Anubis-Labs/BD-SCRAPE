import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QLineEdit, QComboBox, QTextEdit, QFileDialog,
    QProgressBar, QTableWidget, QTableWidgetItem
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QHeaderView

# Adjust import paths for backend modules
# This assumes that the script will be run with the project root in PYTHONPATH
# or using python -m src.gui.main_window
import os
# Add project root to sys.path to allow for absolute imports from src
# This is a common way to handle imports when running scripts in subdirectories
# For a more robust solution, especially for packaging, consider using setuptools.
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR)) # Moves up two levels (gui -> src -> project_root)
sys.path.insert(0, PROJECT_ROOT)

try:
    from src import llm_handler
    from src import main_processor
    from src import database_crud 
except ImportError as e:
    print(f"Error importing backend modules: {e}")
    print(f"Ensure PYTHONPATH is set correctly or run as a module (e.g., python -m src.gui.main_window)")
    print(f"Current sys.path: {sys.path}")
    # Fallback for direct execution if imports fail, good for dev but not production
    # This is tricky because of relative vs absolute imports. 
    # The above sys.path modification should handle it if run as 'python src/gui/main_window.py' from project root.
    # If running 'python main_window.py' from 'src/gui', the paths would need to be different.
    # For now, we'll assume it's run in a way that src.module works.
    llm_handler = None
    main_processor = None
    database_crud = None


class ProcessingThread(QThread):
    """
    Runs the document processing in a separate thread to keep the GUI responsive.
    """
    progress_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, root_folder, selected_model, db_session_factory):
        super().__init__()
        self.root_folder = root_folder
        self.selected_model = selected_model
        self.db_session_factory = db_session_factory # Pass factory, create session in thread

    def run(self):
        self.progress_signal.emit("Processing started...")
        db_session = None
        original_stdout = sys.stdout # Store original stdout
        log_stream = None
        try:
            if not main_processor or not database_crud:
                raise ImportError("Backend modules (main_processor, database_crud) not loaded.")

            db_session = self.db_session_factory()
            # Note: main_processor.process_documents_workflow needs to be adapted
            # to potentially yield progress updates if we want finer-grained progress.
            # For now, we just get start/finish/error.
            # We also need a way to stream its print() statements to our GUI log.
            
            class QtLogStream:
                def __init__(self, signal_emitter):
                    self.signal_emitter = signal_emitter
                def write(self, text):
                    stripped_text = text.strip()
                    if stripped_text: # Only emit if there's content
                        self.signal_emitter.emit(stripped_text)
                def flush(self):
                    pass # sys.stdout has a flush method, so we need one too.
            
            log_stream = QtLogStream(self.progress_signal)
            sys.stdout = log_stream

            main_processor.process_documents_workflow(
                root_folder_to_scan=self.root_folder,
                selected_llm_model=self.selected_model,
                db_session=db_session,
                force_reprocess_all=False # Or make this a GUI option
            )
            
            sys.stdout = original_stdout # Restore stdout
            # ---

            self.finished_signal.emit("Processing completed successfully!")
        except ImportError as e:
            self.error_signal.emit(f"Import error during processing: {str(e)}.")
        except Exception as e:
            self.error_signal.emit(f"Error during processing: {str(e)}")
        finally:
            sys.stdout = original_stdout # Always restore stdout
            if db_session:
                db_session.close()


class EquinoxKnowledgeApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Equinox Project Knowledge Extractor")
        self.setGeometry(100, 100, 1200, 800) # Increased window size slightly

        # Apply a dark theme
        self.set_dark_theme()

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)

        self._create_folder_selection_ui()
        self._create_model_selection_ui()
        self._create_controls_ui()
        self._create_log_output_ui()
        self._create_data_display_ui() # New UI section
        
        self.db_session_factory = database_crud.get_session if database_crud else None
        self.processing_thread = None

        self.load_ollama_models()
        self.load_and_display_project_data() # Load data on startup

    def set_dark_theme(self):
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(42, 42, 42))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(66, 66, 66))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        dark_palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(120,120,120))

        QApplication.instance().setPalette(dark_palette)
        
        # Font settings can also be applied more globally if desired
        # font = QFont()
        # font.setPointSize(16)
        # QApplication.instance().setFont(font)

        stylesheet = """
            QWidget {
                font-size: 16pt; /* Base font size */
            }
            QTableWidget { /* Specific font for table if needed, or inherits */
                /* font-size: 14pt; */ 
                alternate-background-color: #3a3a3a; /* Slightly different for rows */
            }
            QHeaderView::section {
                background-color: #424242;
                padding: 4px;
                border: 1px solid #4f4f4f;
                font-size: 14pt; /* Font for headers */
            }
            QPushButton {
                border: 1px solid #4f4f4f;
                border-radius: 4px;
                padding: 8px; /* Increased padding */
                min-width: 100px; /* Increased min-width */
            }
            QPushButton:hover {
                background-color: #4f4f4f;
            }
            QPushButton:pressed {
                background-color: #3e3e3e;
            }
            QLineEdit, QTextEdit, QComboBox {
                border: 1px solid #4f4f4f;
                border-radius: 4px;
                padding: 6px; /* Increased padding */
                background-color: #2a2a2a;
            }
            QComboBox::drop-down {
                border: none;
            }
            QLabel {
                padding: 2px;
            }
        """
        self.setStyleSheet(stylesheet)


    def _create_folder_selection_ui(self):
        layout = QHBoxLayout()
        self.folder_label = QLabel("Project Documents Folder:")
        self.folder_path_edit = QLineEdit()
        self.folder_path_edit.setPlaceholderText("Select folder containing project documents...")
        self.browse_button = QPushButton("Browse...")
        self.browse_button.clicked.connect(self.browse_folder)
        
        layout.addWidget(self.folder_label)
        layout.addWidget(self.folder_path_edit, 1) # Add stretch factor
        layout.addWidget(self.browse_button)
        self.main_layout.addLayout(layout)

    def _create_model_selection_ui(self):
        layout = QHBoxLayout()
        self.model_label = QLabel("Select LLM Model:")
        self.model_combo = QComboBox()
        
        layout.addWidget(self.model_label)
        layout.addWidget(self.model_combo, 1) # Add stretch factor
        self.main_layout.addLayout(layout)

    def _create_controls_ui(self):
        layout = QHBoxLayout()
        self.start_button = QPushButton("Start Processing")
        self.start_button.clicked.connect(self.start_processing)
        # self.progress_bar = QProgressBar() # Add later if fine-grained progress is implemented
        # self.progress_bar.setTextVisible(False)
        # layout.addWidget(self.progress_bar, 1)
        layout.addStretch(1) # Push button to the left
        layout.addWidget(self.start_button)
        self.main_layout.addLayout(layout)
        
    def _create_log_output_ui(self):
        self.log_output_label = QLabel("Processing Log:")
        self.log_output_text = QTextEdit()
        self.log_output_text.setReadOnly(True)
        self.main_layout.addWidget(self.log_output_label)
        self.main_layout.addWidget(self.log_output_text, 1) # Add stretch factor for vertical space

    def _create_data_display_ui(self):
        data_area_layout = QVBoxLayout()
        
        controls_layout = QHBoxLayout()
        self.data_display_label = QLabel("Project Data Overview:")
        controls_layout.addWidget(self.data_display_label)
        controls_layout.addStretch(1)
        self.refresh_data_button = QPushButton("Refresh Data")
        self.refresh_data_button.clicked.connect(self.load_and_display_project_data)
        controls_layout.addWidget(self.refresh_data_button)
        data_area_layout.addLayout(controls_layout)

        self.project_table = QTableWidget()
        self.project_table.setColumnCount(5) # Initial column count
        self.project_table.setHorizontalHeaderLabels(["Project ID", "Equinox #", "Project Name", "Client(s)", "Description Snippet"])
        self.project_table.setAlternatingRowColors(True)
        self.project_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers) # Read-only
        self.project_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.project_table.verticalHeader().setVisible(False) # Hide row numbers by default
        
        # Column stretching behavior
        header = self.project_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents) # Project ID
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents) # Equinox #
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Project Name
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Client(s)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Description
        self.project_table.setMinimumHeight(200) # Ensure it has some initial height

        data_area_layout.addWidget(self.project_table)
        self.main_layout.addLayout(data_area_layout) # Add this new section to main layout

    def browse_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.folder_path_edit.setText(folder_path)

    def load_ollama_models(self):
        self.log_output_text.append("Loading available Ollama models...")
        if not llm_handler:
            self.log_output_text.append("Error: LLM Handler not available. Cannot fetch models.")
            return
            
        try:
            models = llm_handler.get_available_ollama_models()
            if models:
                self.model_combo.clear()
                self.model_combo.addItems(models)
                self.log_output_text.append(f"Available models loaded: {', '.join(models)}")
                # Select a default if possible
                if main_processor and main_processor.DEFAULT_LLM_MODEL in models:
                    self.model_combo.setCurrentText(main_processor.DEFAULT_LLM_MODEL)
                elif models:
                     self.model_combo.setCurrentIndex(0) # Select first one
            else:
                self.log_output_text.append("No Ollama models found. Ensure Ollama is running and models are pulled.")
        except Exception as e:
            self.log_output_text.append(f"Error loading Ollama models: {str(e)}")

    def start_processing(self):
        root_folder = self.folder_path_edit.text().strip()
        selected_model = self.model_combo.currentText()

        if not root_folder:
            self.log_output_text.append("Error: Please select a root folder for documents.")
            return
        if not selected_model:
            self.log_output_text.append("Error: Please select an Ollama model.")
            return
        if not self.db_session_factory:
            self.log_output_text.append("Error: Database session factory not initialized. Backend modules might be missing.")
            return

        self.log_output_text.clear()
        self.log_output_text.append(f"Starting processing for folder: {root_folder}")
        self.log_output_text.append(f"Using LLM model: {selected_model}")
        
        self.start_button.setEnabled(False)
        
        self.processing_thread = ProcessingThread(root_folder, selected_model, self.db_session_factory)
        self.processing_thread.progress_signal.connect(self.update_log)
        self.processing_thread.finished_signal.connect(self.processing_finished)
        self.processing_thread.error_signal.connect(self.processing_error)
        self.processing_thread.start()

    def update_log(self, message):
        self.log_output_text.append(message)

    def processing_finished(self, message):
        self.log_output_text.append(message)
        self.start_button.setEnabled(True)
        self.processing_thread = None # Clear thread

    def processing_error(self, message):
        self.log_output_text.append(f"ERROR: {message}")
        self.start_button.setEnabled(True)
        self.processing_thread = None # Clear thread

    def load_and_display_project_data(self):
        self.log_output_text.append("Loading project data from database...")
        if not self.db_session_factory:
            self.log_output_text.append("Error: Database session factory not available.")
            return

        db_session = None
        try:
            db_session = self.db_session_factory()
            # Fetch projects with their clients for display
            # This query needs to be implemented in database_crud.py or constructed here
            projects_with_clients = database_crud.get_projects_with_client_info(db_session) # Assuming this function will be created

            if not projects_with_clients:
                self.log_output_text.append("No projects found in the database.")
                self.project_table.setRowCount(0) # Clear table
                return

            self.project_table.setRowCount(len(projects_with_clients))
            for row_idx, project_data in enumerate(projects_with_clients):
                project = project_data["project"]
                client_names = project_data["client_names"] # e.g., "Client A, Client B"
                
                self.project_table.setItem(row_idx, 0, QTableWidgetItem(str(project.project_id)))
                self.project_table.setItem(row_idx, 1, QTableWidgetItem(project.equinox_project_number or "N/A"))
                self.project_table.setItem(row_idx, 2, QTableWidgetItem(project.project_name or "N/A"))
                self.project_table.setItem(row_idx, 3, QTableWidgetItem(client_names or "N/A"))
                description_snippet = (project.project_description_short or "")[:100] + "..." if project.project_description_short and len(project.project_description_short)>100 else (project.project_description_short or "N/A")
                self.project_table.setItem(row_idx, 4, QTableWidgetItem(description_snippet))
            
            self.project_table.resizeColumnsToContents() # Adjust column sizes after populating
            # Re-apply stretch where needed after resizeColumnsToContents
            header = self.project_table.horizontalHeader()
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch) # Project Name
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch) # Client(s)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch) # Description

            self.log_output_text.append(f"Displayed {len(projects_with_clients)} projects.")

        except AttributeError as ae:
             if 'get_projects_with_client_info' in str(ae):
                 self.log_output_text.append("Error: `get_projects_with_client_info` function not found in database_crud. It needs to be implemented.")
                 print("TODO: Implement get_projects_with_client_info in database_crud.py") # For console log
             else:
                 self.log_output_text.append(f"Attribute error loading data: {str(ae)}")
        except Exception as e:
            self.log_output_text.append(f"Error loading project data: {str(e)}")
        finally:
            if db_session:
                db_session.close()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    
    backend_modules_loaded = True
    if not database_crud:
        print("CRITICAL: database_crud module failed to load.")
        backend_modules_loaded = False
    if not llm_handler:
        print("CRITICAL: llm_handler module failed to load.")
        backend_modules_loaded = False
    if not main_processor:
        print("CRITICAL: main_processor module failed to load.")
        backend_modules_loaded = False

    if not backend_modules_loaded:
        error_dialog = QTextEdit() # Need QApplication before QWidget
        error_dialog.setReadOnly(True)
        error_text = ("Critical backend modules failed to load.\n\n"
                      "Please check your Python environment, PYTHONPATH, and ensure all dependencies are installed. "
                      "Run from the project root directory (e.g., python -m src.gui.main_window).\n\n"
                      "See console for specific missing modules.")
        error_dialog.setText(error_text.replace("\\n", "\n")) 
        error_dialog.setWindowTitle("Initialization Error")
        error_dialog.resize(450,180)
        error_dialog.show()
        # It's important that app.exec() is called for the dialog to be shown and interactive.
        # However, the main app shouldn't proceed.
        # One way: show dialog then exit, or structure to not create main_app.
        # For now, we'll let app.exec() run but main_app won't show if error_dialog is the focus.
        # A cleaner way is to exit directly IF no GUI error display is paramount.
        # Let's try exiting after showing dialog to make failure clear.
        app.exec() # Show the error dialog
        sys.exit(1) # Exit with an error code
    
    main_app = EquinoxKnowledgeApp()
    main_app.show()
    sys.exit(app.exec()) 