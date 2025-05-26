# API Reference

## Overview

This document provides comprehensive API reference for the Equinox Document Intelligence Processor. The system exposes several APIs for document processing, database management, AI integration, and system administration.

## Table of Contents

1. [Core Processing APIs](#core-processing-apis)
2. [Database APIs](#database-apis)
3. [AI/LLM APIs](#aillm-apis)
4. [File System APIs](#file-system-apis)
5. [Database Management APIs](#database-management-apis)
6. [Docker Management APIs](#docker-management-apis)
7. [CLI Tools](#cli-tools)
8. [Data Models](#data-models)
9. [Error Handling](#error-handling)

## Core Processing APIs

### DocumentProcessor Class

The main document processing orchestrator.

#### `process_single_file(file_path, model_name, callback=None)`

Process a single document file.

**Parameters:**
- `file_path` (str): Path to the document file
- `model_name` (str): Name of the Ollama model to use
- `callback` (callable, optional): Progress callback function

**Returns:**
- `dict`: Processing results with success status and extracted data

**Example:**
```python
from src.main_processor import process_single_file

result = process_single_file(
    file_path="document.pdf",
    model_name="gemma2:9b",
    callback=lambda msg: print(f"Progress: {msg}")
)

if result['success']:
    print(f"Extracted {len(result['projects'])} projects")
else:
    print(f"Error: {result['error']}")
```

#### `process_folder(folder_path, model_name, callback=None)`

Process all supported documents in a folder.

**Parameters:**
- `folder_path` (str): Path to the folder containing documents
- `model_name` (str): Name of the Ollama model to use
- `callback` (callable, optional): Progress callback function

**Returns:**
- `dict`: Processing results with statistics and error information

**Example:**
```python
from src.main_processor import process_folder

result = process_folder(
    folder_path="./documents",
    model_name="gemma2:9b",
    callback=progress_handler
)

print(f"Processed {result['total_files']} files")
print(f"Success: {result['successful_files']}")
print(f"Errors: {result['failed_files']}")
```

### Document Processing Functions

#### `process_documents(selected_llm_model, filename=None, upload_dir=None)`

Legacy function for document processing.

**Parameters:**
- `selected_llm_model` (str): LLM model name
- `filename` (str, optional): Specific filename to process
- `upload_dir` (str, optional): Upload directory path

**Returns:**
- `bool`: Success status

## Database APIs

### Session Management

#### `get_db_session()`

Get a database session context manager.

**Returns:**
- `contextlib.contextmanager`: Database session

**Example:**
```python
from src.database_crud import get_db_session

with get_db_session() as session:
    # Perform database operations
    projects = session.query(Project).all()
```

### Project Operations

#### `create_project(session, project_data)`

Create a new project in the database.

**Parameters:**
- `session`: Database session
- `project_data` (dict): Project information

**Returns:**
- `int`: Project ID if successful, None otherwise

**Example:**
```python
project_data = {
    'name': 'New Project',
    'description': 'Project description',
    'client_id': 1,
    'status': 'active'
}

with get_db_session() as session:
    project_id = create_project(session, project_data)
```

#### `get_all_projects(session, simple_view=False)`

Retrieve all projects from the database.

**Parameters:**
- `session`: Database session
- `simple_view` (bool): Return simplified view if True

**Returns:**
- `list`: List of project dictionaries

#### `get_project_by_id(session, project_id)`

Get a specific project by ID.

**Parameters:**
- `session`: Database session
- `project_id` (int): Project ID

**Returns:**
- `dict`: Project data or None if not found

#### `update_project(session, project_id, update_data)`

Update an existing project.

**Parameters:**
- `session`: Database session
- `project_id` (int): Project ID
- `update_data` (dict): Fields to update

**Returns:**
- `bool`: Success status

#### `delete_project(session, project_id)`

Delete a project and related data.

**Parameters:**
- `session`: Database session
- `project_id` (int): Project ID

**Returns:**
- `bool`: Success status

### Document Operations

#### `create_document(session, document_data)`

Create a new document record.

**Parameters:**
- `session`: Database session
- `document_data` (dict): Document information

**Returns:**
- `int`: Document ID if successful

**Example:**
```python
document_data = {
    'filename': 'report.pdf',
    'file_path': '/path/to/report.pdf',
    'file_size': 1024000,
    'project_id': 1,
    'status': 'processed'
}

with get_db_session() as session:
    doc_id = create_document(session, document_data)
```

#### `get_all_documents(session)`

Retrieve all documents.

**Returns:**
- `list`: List of document dictionaries

#### `get_documents_by_project(session, project_id)`

Get documents for a specific project.

**Parameters:**
- `session`: Database session
- `project_id` (int): Project ID

**Returns:**
- `list`: List of document dictionaries

### Extraction Log Operations

#### `log_extraction(session, log_data)`

Create an extraction log entry.

**Parameters:**
- `session`: Database session
- `log_data` (dict): Log information

**Returns:**
- `int`: Log ID if successful

**Example:**
```python
log_data = {
    'project_id': 1,
    'document_id': 1,
    'llm_model': 'gemma2:9b',
    'extraction_content': 'Extracted project information...',
    'confidence_score': 0.95,
    'processing_time': 5.2
}

with get_db_session() as session:
    log_id = log_extraction(session, log_data)
```

#### `get_extraction_logs(session, project_id=None)`

Retrieve extraction logs.

**Parameters:**
- `session`: Database session
- `project_id` (int, optional): Filter by project ID

**Returns:**
- `list`: List of extraction log dictionaries

### Client Operations

#### `create_client(session, client_data)`

Create a new client.

**Parameters:**
- `session`: Database session
- `client_data` (dict): Client information

**Returns:**
- `int`: Client ID if successful

#### `get_all_clients(session)`

Retrieve all clients.

**Returns:**
- `list`: List of client dictionaries

## AI/LLM APIs

### Model Management

#### `get_available_ollama_models()`

Get list of available Ollama models.

**Returns:**
- `list`: List of model names

**Example:**
```python
from src.llm_handler import get_available_ollama_models

models = get_available_ollama_models()
print(f"Available models: {models}")
```

#### `check_ollama_connection()`

Check if Ollama service is available.

**Returns:**
- `bool`: True if connected, False otherwise

### Text Processing

#### `get_project_names_from_text(text, model_name)`

Extract project names from text using AI.

**Parameters:**
- `text` (str): Input text to analyze
- `model_name` (str): Ollama model to use

**Returns:**
- `list`: List of extracted project names

**Example:**
```python
from src.llm_handler import get_project_names_from_text

text = "This document discusses Project Alpha and Project Beta implementations."
projects = get_project_names_from_text(text, "gemma2:9b")
print(f"Found projects: {projects}")
```

#### `enrich_and_verify_project_context(project_name, text, model_name)`

Enrich project information using AI analysis.

**Parameters:**
- `project_name` (str): Project name to analyze
- `text` (str): Context text
- `model_name` (str): Ollama model to use

**Returns:**
- `dict`: Enriched project information

**Example:**
```python
from src.llm_handler import enrich_and_verify_project_context

enriched = enrich_and_verify_project_context(
    project_name="Project Alpha",
    text="Project Alpha is a renewable energy initiative...",
    model_name="gemma2:9b"
)

print(f"Project type: {enriched.get('project_type')}")
print(f"Confidence: {enriched.get('confidence_score')}")
```

#### `extract_all_document_data_verbatim(text, model_name)`

Extract comprehensive data from document text.

**Parameters:**
- `text` (str): Document text
- `model_name` (str): Ollama model to use

**Returns:**
- `dict`: Extracted data including projects, technologies, partners, etc.

### Prompt Management

#### `create_extraction_prompt(text, extraction_type)`

Create structured prompts for AI extraction.

**Parameters:**
- `text` (str): Input text
- `extraction_type` (str): Type of extraction ('projects', 'technologies', etc.)

**Returns:**
- `str`: Formatted prompt

## File System APIs

### File Discovery

#### `find_supported_files(directory_path)`

Find all supported document files in a directory.

**Parameters:**
- `directory_path` (str): Directory to scan

**Returns:**
- `list`: List of file paths

**Example:**
```python
from src.file_system_handler import find_supported_files

files = find_supported_files("./documents")
print(f"Found {len(files)} supported files")
```

#### `is_supported_file(file_path)`

Check if a file format is supported.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
- `bool`: True if supported, False otherwise

### File Operations

#### `get_file_metadata(file_path)`

Extract metadata from a file.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
- `dict`: File metadata including size, creation date, etc.

#### `validate_file_access(file_path)`

Validate that a file can be accessed and read.

**Parameters:**
- `file_path` (str): Path to file

**Returns:**
- `bool`: True if accessible, False otherwise

## Database Management APIs

### DatabaseManager Class

Comprehensive database management utilities.

#### `__init__(export_dir="data/database_exports")`

Initialize database manager.

**Parameters:**
- `export_dir` (str): Directory for exports

#### `wipe_database(confirm=False)`

Wipe all data from the database while preserving schema.

**Parameters:**
- `confirm` (bool): Confirmation flag for safety

**Returns:**
- `bool`: Success status

**Example:**
```python
from scripts.database_manager import DatabaseManager

manager = DatabaseManager()
success = manager.wipe_database(confirm=True)
```

#### `export_to_csv(output_dir=None)`

Export database to CSV files.

**Parameters:**
- `output_dir` (str, optional): Output directory

**Returns:**
- `bool`: Success status

#### `export_to_json(output_dir=None)`

Export database to JSON files.

**Parameters:**
- `output_dir` (str, optional): Output directory

**Returns:**
- `bool`: Success status

#### `export_sql_dump(output_file=None)`

Create SQL dump of the database.

**Parameters:**
- `output_file` (str, optional): Output file path

**Returns:**
- `bool`: Success status

#### `export_all_formats()`

Export database in all available formats.

**Returns:**
- `bool`: Success status

#### `get_database_stats()`

Get comprehensive database statistics.

**Returns:**
- `dict`: Database statistics

**Example:**
```python
stats = manager.get_database_stats()
print(f"Projects: {stats['projects']}")
print(f"Documents: {stats['documents']}")
print(f"Last updated: {stats['last_updated']}")
```

#### `check_database_status()`

Check database connection and health.

**Returns:**
- `dict`: Status information

## Docker Management APIs

### DockerDBManager Class

Docker container and volume management.

#### `__init__()`

Initialize Docker manager.

#### `get_docker_status()`

Get comprehensive Docker status.

**Returns:**
- `dict`: Docker status information

**Example:**
```python
from scripts.docker_db_manager import DockerDBManager

docker_manager = DockerDBManager()
status = docker_manager.get_docker_status()
print(f"Docker running: {status['docker_running']}")
print(f"Container running: {status['container_running']}")
```

#### `start_database_container()`

Start the database container.

**Returns:**
- `bool`: Success status

#### `stop_database_container()`

Stop the database container.

**Returns:**
- `bool`: Success status

#### `restart_database_container()`

Restart the database container.

**Returns:**
- `bool`: Success status

#### `backup_volume(output_path=None)`

Create a backup of the database volume.

**Parameters:**
- `output_path` (str, optional): Backup file path

**Returns:**
- `bool`: Success status

#### `restore_volume(backup_path)`

Restore database volume from backup.

**Parameters:**
- `backup_path` (str): Path to backup file

**Returns:**
- `bool`: Success status

#### `wipe_volume(confirm=False)`

Completely wipe the database volume.

**Parameters:**
- `confirm` (bool): Confirmation flag

**Returns:**
- `bool`: Success status

## CLI Tools

### Database Manager CLI

Command-line interface for database operations.

#### Usage

```bash
python scripts/database_manager.py [command] [options]
```

#### Commands

- `export`: Export database
  ```bash
  python scripts/database_manager.py export --format csv --output ./exports
  ```

- `wipe`: Wipe database
  ```bash
  python scripts/database_manager.py wipe --confirm
  ```

- `stats`: Show database statistics
  ```bash
  python scripts/database_manager.py stats
  ```

- `status`: Check database status
  ```bash
  python scripts/database_manager.py status
  ```

### Docker Manager CLI

Command-line interface for Docker operations.

#### Usage

```bash
python scripts/docker_db_manager.py [command] [options]
```

#### Commands

- `status`: Check Docker status
  ```bash
  python scripts/docker_db_manager.py status
  ```

- `start`: Start database container
  ```bash
  python scripts/docker_db_manager.py start
  ```

- `stop`: Stop database container
  ```bash
  python scripts/docker_db_manager.py stop
  ```

- `restart`: Restart database container
  ```bash
  python scripts/docker_db_manager.py restart
  ```

- `backup`: Backup database volume
  ```bash
  python scripts/docker_db_manager.py backup --output ./backups/backup.tar
  ```

- `restore`: Restore database volume
  ```bash
  python scripts/docker_db_manager.py restore --backup ./backups/backup.tar
  ```

## Data Models

### Project Model

```python
{
    'id': int,
    'name': str,
    'description': str,
    'client_id': int,
    'status': str,
    'created_at': datetime,
    'updated_at': datetime
}
```

### Document Model

```python
{
    'id': int,
    'filename': str,
    'file_path': str,
    'file_size': int,
    'file_type': str,
    'project_id': int,
    'status': str,
    'processed_at': datetime,
    'created_at': datetime
}
```

### Extraction Log Model

```python
{
    'id': int,
    'project_id': int,
    'document_id': int,
    'llm_model': str,
    'extraction_content': str,
    'confidence_score': float,
    'processing_time': float,
    'created_at': datetime
}
```

### Client Model

```python
{
    'id': int,
    'name': str,
    'description': str,
    'contact_info': str,
    'created_at': datetime,
    'updated_at': datetime
}
```

## Error Handling

### Exception Types

#### `DatabaseConnectionError`

Raised when database connection fails.

```python
try:
    with get_db_session() as session:
        # Database operations
        pass
except DatabaseConnectionError as e:
    print(f"Database connection failed: {e}")
```

#### `DocumentProcessingError`

Raised when document processing fails.

```python
try:
    result = process_single_file("document.pdf", "gemma2:9b")
except DocumentProcessingError as e:
    print(f"Processing failed: {e}")
```

#### `OllamaConnectionError`

Raised when Ollama service is unavailable.

```python
try:
    models = get_available_ollama_models()
except OllamaConnectionError as e:
    print(f"Ollama service unavailable: {e}")
```

### Error Response Format

All API functions return consistent error information:

```python
{
    'success': False,
    'error': 'Error message',
    'error_type': 'ErrorType',
    'details': {
        'additional': 'error details'
    }
}
```

### Success Response Format

Successful API calls return:

```python
{
    'success': True,
    'data': {
        # Response data
    },
    'message': 'Operation completed successfully'
}
```

## Rate Limiting and Performance

### AI API Limits

- Ollama requests are limited by model capacity
- Large documents may require chunking
- Processing time varies by model and document size

### Database Limits

- Connection pool size: 20 connections
- Query timeout: 30 seconds
- Maximum export size: 1GB

### File Processing Limits

- Maximum file size: 100MB
- Supported formats: PDF, DOCX, PPTX, XLSX, XLS
- Concurrent processing: 5 files maximum

## Authentication and Security

### Database Security

- PostgreSQL authentication required
- Configurable credentials via environment variables
- Connection encryption available

### File Security

- Local file processing only
- No external data transmission
- Temporary file cleanup

### API Security

- Local-only access by default
- No built-in authentication (add as needed)
- Input validation and sanitization

## Versioning

### API Version

Current API version: `1.0.0`

### Compatibility

- Backward compatibility maintained for major versions
- Deprecation notices provided for breaking changes
- Migration guides available for version upgrades

---

This API reference provides comprehensive documentation for all available interfaces in the Equinox Document Intelligence Processor. For implementation examples and tutorials, refer to the User Guide and Developer Guide. 