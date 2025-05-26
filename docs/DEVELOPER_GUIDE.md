# Developer Guide

## Welcome to Equinox Document Intelligence Processor Development

This guide provides comprehensive information for developers who want to understand, modify, extend, or contribute to the Equinox Document Intelligence Processor.

## Table of Contents

1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Core Components](#core-components)
4. [Development Workflow](#development-workflow)
5. [Testing](#testing)
6. [API Reference](#api-reference)
7. [Contributing](#contributing)
8. [Deployment](#deployment)

## Development Environment Setup

### Prerequisites

- **Python 3.8+**: Core development language
- **Docker & Docker Compose**: Container orchestration
- **Git**: Version control
- **IDE/Editor**: VS Code, PyCharm, or similar
- **System Requirements**: 8GB RAM minimum, 16GB recommended

### Initial Setup

1. **Clone and Navigate**
   ```bash
   git clone <repository-url>
   cd bd_scrape
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Start Infrastructure**
   ```bash
   # Start database and AI services
   docker-compose -f config/docker-compose.yml up -d
   
   # Verify services are running
   docker ps
   ```

5. **Initialize Database**
   ```bash
   # Run database initialization
   python src/database_crud.py
   ```

6. **Verify Installation**
   ```bash
   # Run comprehensive tests
   python tests/test_db_management.py
   ```

### Development Tools Setup

#### VS Code Configuration

Create `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"],
    "files.exclude": {
        "**/__pycache__": true,
        "**/*.pyc": true,
        ".pytest_cache": true
    }
}
```

#### Git Configuration

Create `.gitignore`:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env

# Database
*.db
*.sqlite3
data/database_exports/
data/upload_folder/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Docker
.docker/
```

## Project Structure

### Directory Organization

```
bd_scrape/
├── src/                          # Core application code
│   ├── gui/                      # User interface components
│   │   ├── streamlit_app.py      # Main web application
│   │   └── database_management_ui.py  # Database management interface
│   ├── parsers/                  # Document parsing modules
│   │   ├── pdf_parser.py         # PDF processing
│   │   ├── docx_parser.py        # Word document processing
│   │   ├── pptx_parser.py        # PowerPoint processing
│   │   └── excel_parser.py       # Excel processing
│   ├── database_crud.py          # Database operations
│   ├── database_models.py        # SQLAlchemy models
│   ├── llm_handler.py           # AI/LLM integration
│   ├── main_processor.py        # Core processing pipeline
│   └── file_system_handler.py   # File management
├── scripts/                      # Utility scripts and CLI tools
│   ├── database_manager.py      # Database management CLI
│   ├── docker_db_manager.py     # Docker management CLI
│   └── database_management_example.py  # Usage examples
├── tests/                        # Test suite
│   └── test_db_management.py    # Comprehensive tests
├── config/                       # Configuration files
│   ├── docker-compose.yml       # Docker services
│   ├── database_schema.md       # Database documentation
│   └── project_categorization_schema.md  # Project schemas
├── data/                         # Data storage
│   ├── upload_folder/           # Document uploads
│   ├── database_exports/        # Export outputs
│   └── workspace_sample_documents/  # Sample files
├── docs/                         # Documentation
│   ├── SYSTEM_ARCHITECTURE.md   # Technical architecture
│   ├── USER_GUIDE.md            # User documentation
│   ├── DEVELOPER_GUIDE.md       # This file
│   └── API_REFERENCE.md         # API documentation
├── assets/                       # Static assets
│   └── background.jpg           # UI assets
├── requirements.txt              # Python dependencies
└── README.md                    # Project overview
```

### Key Files and Their Purposes

#### Core Application Files

- **`src/main_processor.py`**: Central orchestration of document processing
- **`src/database_crud.py`**: Database abstraction layer and CRUD operations
- **`src/llm_handler.py`**: AI model integration and prompt management
- **`src/database_models.py`**: SQLAlchemy ORM models and relationships

#### User Interface Files

- **`src/gui/streamlit_app.py`**: Main web application with all user interfaces
- **`src/gui/database_management_ui.py`**: Specialized database management interface

#### Parser Modules

- **`src/parsers/pdf_parser.py`**: PDF text extraction using pdfplumber and PyMuPDF
- **`src/parsers/docx_parser.py`**: Word document processing with python-docx
- **`src/parsers/pptx_parser.py`**: PowerPoint slide processing
- **`src/parsers/excel_parser.py`**: Excel spreadsheet processing

#### Utility Scripts

- **`scripts/database_manager.py`**: Command-line database operations
- **`scripts/docker_db_manager.py`**: Docker container and volume management
- **`scripts/database_management_example.py`**: API usage examples

## Core Components

### Database Layer

#### Models (`src/database_models.py`)

```python
# Key model relationships
Project (1) ←→ (N) Document
Project (1) ←→ (N) ProjectExtractionLog
Project (1) ←→ (N) Technology
Project (1) ←→ (N) Partner
Project (1) ←→ (N) ProjectFinancial
Client (1) ←→ (N) Project
```

#### CRUD Operations (`src/database_crud.py`)

```python
# Core functions
def get_db_session()                    # Session management
def create_project(session, project_data)  # Project creation
def get_all_projects(session)           # Project retrieval
def create_document(session, doc_data)  # Document management
def log_extraction(session, log_data)   # Processing logs
```

### Document Processing Pipeline

#### Main Processor (`src/main_processor.py`)

```python
class DocumentProcessor:
    def process_single_file(file_path, model_name, callback=None)
    def process_folder(folder_path, model_name, callback=None)
    def _process_document(file_path, model_name)
    def _extract_text_from_file(file_path)
    def _get_projects_from_text(text, model_name)
```

#### Parser Interface

All parsers implement a common interface:

```python
def parse_document(file_path: str) -> Dict[str, Any]:
    """
    Returns:
    {
        'text': str,           # Extracted text content
        'metadata': dict,      # File metadata
        'pages': int,          # Page count (if applicable)
        'error': str or None   # Error message if parsing failed
    }
    """
```

### AI Integration

#### LLM Handler (`src/llm_handler.py`)

```python
# Core AI functions
def get_available_ollama_models() -> List[str]
def get_project_names_from_text(text: str, model_name: str) -> List[str]
def enrich_and_verify_project_context(project_name: str, text: str, model_name: str) -> Dict
def extract_all_document_data_verbatim(text: str, model_name: str) -> Dict
```

#### Prompt Engineering

The system uses structured prompts for consistent AI responses:

```python
# Example prompt structure
EXTRACTION_PROMPT = """
You are an expert at extracting project information from documents.

TASK: Extract project names from the following text.

RULES:
1. Only extract actual project names, not company names
2. Return as JSON array: ["Project 1", "Project 2"]
3. If no projects found, return empty array: []

TEXT:
{text}

RESPONSE:
"""
```

### User Interface Architecture

#### Streamlit Application Structure

```python
# Main app structure
def main():
    setup_page_config()
    display_header()
    
    # Main sections
    with st.container():
        system_control_center()
        document_processing_section()
        knowledge_base_explorer()
        database_management_center()
        live_engineering_logs()
```

#### Component Organization

- **Modular Design**: Each major feature is a separate function
- **State Management**: Uses Streamlit session state for persistence
- **Real-time Updates**: Implements callbacks for live progress tracking
- **Error Handling**: Comprehensive error display and recovery

## Development Workflow

### Setting Up for Development

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Follow PEP 8 style guidelines
   - Add comprehensive docstrings
   - Include type hints where appropriate

3. **Test Changes**
   ```bash
   # Run all tests
   python tests/test_db_management.py
   
   # Test specific functionality
   python -m pytest tests/ -v
   
   # Manual testing
   streamlit run src/gui/streamlit_app.py
   ```

4. **Commit and Push**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   git push origin feature/your-feature-name
   ```

### Code Style Guidelines

#### Python Style

```python
# Use type hints
def process_document(file_path: str, model_name: str) -> Dict[str, Any]:
    """
    Process a single document and extract project information.
    
    Args:
        file_path: Path to the document file
        model_name: Name of the AI model to use
        
    Returns:
        Dictionary containing processing results
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ProcessingError: If processing fails
    """
    pass

# Use descriptive variable names
extraction_results = process_document(document_path, selected_model)
project_names = extract_project_names(document_text)

# Handle errors gracefully
try:
    result = risky_operation()
except SpecificException as e:
    logger.error(f"Operation failed: {e}")
    return {"error": str(e)}
```

#### Database Operations

```python
# Always use context managers for database sessions
def create_new_project(project_data: Dict[str, Any]) -> Optional[int]:
    """Create a new project in the database."""
    with get_db_session() as session:
        try:
            project = Project(**project_data)
            session.add(project)
            session.commit()
            return project.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create project: {e}")
            return None
```

#### Error Handling

```python
# Comprehensive error handling
def safe_document_processing(file_path: str) -> Dict[str, Any]:
    """Process document with comprehensive error handling."""
    try:
        # Validate input
        if not os.path.exists(file_path):
            return {"error": "File not found", "success": False}
            
        # Process document
        result = process_document(file_path)
        return {"data": result, "success": True}
        
    except PermissionError:
        return {"error": "Permission denied", "success": False}
    except Exception as e:
        logger.exception("Unexpected error in document processing")
        return {"error": f"Processing failed: {str(e)}", "success": False}
```

### Adding New Features

#### Adding a New Document Parser

1. **Create Parser Module**
   ```python
   # src/parsers/new_format_parser.py
   def parse_document(file_path: str) -> Dict[str, Any]:
       """Parse new document format."""
       try:
           # Implement parsing logic
           text = extract_text(file_path)
           metadata = extract_metadata(file_path)
           
           return {
               'text': text,
               'metadata': metadata,
               'pages': get_page_count(file_path),
               'error': None
           }
       except Exception as e:
           return {
               'text': '',
               'metadata': {},
               'pages': 0,
               'error': str(e)
           }
   ```

2. **Register Parser**
   ```python
   # src/file_system_handler.py
   SUPPORTED_EXTENSIONS = {
       '.pdf': 'pdf_parser',
       '.docx': 'docx_parser',
       '.pptx': 'pptx_parser',
       '.xlsx': 'excel_parser',
       '.new': 'new_format_parser',  # Add new format
   }
   ```

3. **Add Tests**
   ```python
   # tests/test_new_parser.py
   def test_new_format_parser():
       result = parse_document('test_file.new')
       assert result['error'] is None
       assert len(result['text']) > 0
   ```

#### Adding New AI Models

1. **Update Model Discovery**
   ```python
   # src/llm_handler.py
   def get_available_ollama_models() -> List[str]:
       """Get list of available models including new ones."""
       # Implementation handles dynamic model discovery
   ```

2. **Add Model-Specific Prompts**
   ```python
   # Model-specific prompt optimization
   MODEL_PROMPTS = {
       'gemma2:9b': STANDARD_PROMPT,
       'llama3:8b': OPTIMIZED_PROMPT,
       'new_model:7b': NEW_MODEL_PROMPT,
   }
   ```

#### Extending Database Schema

1. **Add New Model**
   ```python
   # src/database_models.py
   class NewEntity(Base):
       __tablename__ = 'new_entities'
       
       id = Column(Integer, primary_key=True)
       name = Column(String(255), nullable=False)
       project_id = Column(Integer, ForeignKey('projects.id'))
       
       # Relationship
       project = relationship("Project", back_populates="new_entities")
   ```

2. **Update Existing Models**
   ```python
   # Add relationship to Project model
   class Project(Base):
       # ... existing fields ...
       new_entities = relationship("NewEntity", back_populates="project")
   ```

3. **Create Migration Script**
   ```python
   # scripts/migrate_database.py
   def add_new_entity_table():
       """Add new entity table to existing database."""
       # Implementation for schema migration
   ```

## Testing

### Test Structure

The project uses a comprehensive testing approach:

```python
# tests/test_db_management.py
def test_database_connectivity():
    """Test database connection and basic operations."""
    
def test_document_processing():
    """Test document parsing and AI extraction."""
    
def test_ui_components():
    """Test Streamlit interface components."""
    
def test_docker_integration():
    """Test Docker container management."""
```

### Running Tests

```bash
# Run all tests
python tests/test_db_management.py

# Run with verbose output
python tests/test_db_management.py -v

# Run specific test categories
python -c "from tests.test_db_management import *; test_database_connectivity()"
```

### Writing New Tests

```python
def test_new_feature():
    """Test new feature functionality."""
    # Arrange
    test_data = setup_test_data()
    
    # Act
    result = new_feature_function(test_data)
    
    # Assert
    assert result['success'] is True
    assert 'expected_field' in result
    
    # Cleanup
    cleanup_test_data()
```

### Integration Testing

```python
def test_full_processing_pipeline():
    """Test complete document processing workflow."""
    # Test file upload → parsing → AI extraction → database storage
    test_file = 'tests/sample_document.pdf'
    
    # Process document
    result = process_single_file(test_file, 'gemma2:9b')
    
    # Verify results
    assert result['success'] is True
    assert len(result['projects']) > 0
    
    # Verify database storage
    with get_db_session() as session:
        projects = get_all_projects(session)
        assert len(projects) > 0
```

## API Reference

### Core APIs

#### Document Processing API

```python
from src.main_processor import DocumentProcessor

processor = DocumentProcessor()

# Process single file
result = processor.process_single_file(
    file_path="document.pdf",
    model_name="gemma2:9b",
    callback=progress_callback
)

# Process folder
result = processor.process_folder(
    folder_path="documents/",
    model_name="gemma2:9b",
    callback=progress_callback
)
```

#### Database API

```python
from src.database_crud import *

# Get database session
with get_db_session() as session:
    # Create project
    project_id = create_project(session, {
        'name': 'New Project',
        'description': 'Project description',
        'client_id': 1
    })
    
    # Retrieve projects
    projects = get_all_projects(session)
    
    # Create document
    doc_id = create_document(session, {
        'filename': 'document.pdf',
        'file_path': '/path/to/document.pdf',
        'project_id': project_id
    })
```

#### AI/LLM API

```python
from src.llm_handler import *

# Get available models
models = get_available_ollama_models()

# Extract project names
projects = get_project_names_from_text(
    text="Document content...",
    model_name="gemma2:9b"
)

# Enrich project data
enriched = enrich_and_verify_project_context(
    project_name="Project Alpha",
    text="Document content...",
    model_name="gemma2:9b"
)
```

#### Database Management API

```python
from scripts.database_manager import DatabaseManager

manager = DatabaseManager()

# Export data
manager.export_data(
    format='csv',
    output_path='exports/'
)

# Reset database
manager.wipe_database()

# Get statistics
stats = manager.get_database_stats()
```

### CLI Tools

#### Database Manager

```bash
# Export database
python scripts/database_manager.py export --format csv --output exports/

# Reset database
python scripts/database_manager.py wipe --confirm

# Show statistics
python scripts/database_manager.py stats
```

#### Docker Manager

```bash
# Backup volume
python scripts/docker_db_manager.py backup --output backups/

# Restore volume
python scripts/docker_db_manager.py restore --backup backups/backup.tar

# Check status
python scripts/docker_db_manager.py status
```

## Contributing

### Contribution Guidelines

1. **Fork the Repository**
   - Create your own fork of the project
   - Clone your fork locally

2. **Create Feature Branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

3. **Make Changes**
   - Follow coding standards
   - Add tests for new functionality
   - Update documentation

4. **Test Thoroughly**
   ```bash
   python tests/test_db_management.py
   ```

5. **Submit Pull Request**
   - Provide clear description of changes
   - Reference any related issues
   - Ensure all tests pass

### Code Review Process

1. **Automated Checks**
   - Code style validation
   - Test suite execution
   - Documentation generation

2. **Manual Review**
   - Code quality assessment
   - Architecture compliance
   - Security considerations

3. **Integration Testing**
   - Full system testing
   - Performance validation
   - Compatibility verification

### Development Best Practices

#### Version Control

```bash
# Commit message format
feat: add new document parser for XYZ format
fix: resolve database connection timeout issue
docs: update API documentation
test: add integration tests for AI processing
refactor: improve error handling in parser modules
```

#### Documentation

- Update relevant documentation for any changes
- Include docstrings for all new functions and classes
- Add examples for new APIs or features
- Update user guide for interface changes

#### Performance Considerations

- Profile code for performance bottlenecks
- Optimize database queries
- Consider memory usage for large documents
- Implement caching where appropriate

## Deployment

### Development Deployment

```bash
# Start development environment
docker-compose -f config/docker-compose.yml up -d
streamlit run src/gui/streamlit_app.py --server.port 8501
```

### Production Deployment

#### Docker-based Deployment

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8501:8501"
    environment:
      - POSTGRES_HOST=db
      - OLLAMA_HOST=ollama
    depends_on:
      - db
      - ollama
      
  db:
    image: postgres:15
    environment:
      POSTGRES_DB: project_db
      POSTGRES_USER: db_user
      POSTGRES_PASSWORD: secure_password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      
  ollama:
    image: ollama/ollama:latest
    volumes:
      - ollama_data:/root/.ollama

volumes:
  postgres_data:
  ollama_data:
```

#### Environment Configuration

```bash
# .env.production
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=project_db
POSTGRES_USER=db_user
POSTGRES_PASSWORD=secure_password

OLLAMA_API_BASE_URL=http://localhost:11434/api
DEFAULT_LLM_MODEL=gemma2:9b

UPLOAD_FOLDER=data/upload_folder
EXPORT_FOLDER=data/database_exports

# Security settings
SECRET_KEY=your-secret-key
DEBUG=False
```

### Monitoring and Maintenance

#### Health Checks

```python
# health_check.py
def check_system_health():
    """Comprehensive system health check."""
    checks = {
        'database': check_database_connection(),
        'ollama': check_ollama_service(),
        'docker': check_docker_status(),
        'disk_space': check_disk_space(),
        'memory': check_memory_usage()
    }
    return checks
```

#### Logging Configuration

```python
# logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
```

### Backup and Recovery

#### Automated Backups

```bash
#!/bin/bash
# backup_script.sh

# Database backup
python scripts/database_manager.py export --format sql --output backups/

# Volume backup
python scripts/docker_db_manager.py backup --output backups/

# Cleanup old backups
find backups/ -name "*.tar" -mtime +30 -delete
```

#### Recovery Procedures

```bash
# Restore from backup
python scripts/docker_db_manager.py restore --backup backups/latest.tar

# Verify restoration
python tests/test_db_management.py
```

---

This developer guide provides comprehensive information for working with the Equinox Document Intelligence Processor. For additional technical details, refer to the System Architecture documentation and API Reference. 