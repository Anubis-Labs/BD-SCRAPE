# System Architecture

## Overview

The Equinox Document Intelligence Processor is a sophisticated multi-tier application designed for AI-powered document processing and information extraction. The system follows a modular architecture with clear separation of concerns.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Streamlit     │  │   Database      │  │   CLI Tools     │  │
│  │   Web App       │  │   Management    │  │   & Scripts     │  │
│  │                 │  │   Interface     │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                        Business Logic Layer                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Document      │  │   AI/LLM        │  │   Database      │  │
│  │   Processing    │  │   Handler       │  │   CRUD          │  │
│  │   Pipeline      │  │                 │  │   Operations    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   File System   │  │   Data          │  │   Validation    │  │
│  │   Handler       │  │   Models        │  │   & Schemas     │  │
│  │                 │  │   (Pydantic)    │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                        Data Access Layer                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   SQLAlchemy    │  │   Document      │  │   File System   │  │
│  │   ORM           │  │   Parsers       │  │   Storage       │  │
│  │                 │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
┌─────────────────────────────────────────────────────────────────┐
│                        Infrastructure Layer                     │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   PostgreSQL    │  │   Ollama        │  │   Docker        │  │
│  │   Database      │  │   AI Engine     │  │   Containers    │  │
│  │                 │  │                 │  │                 │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Presentation Layer

#### Streamlit Web Application (`src/gui/streamlit_app.py`)
- **Purpose**: Primary user interface for the system
- **Features**:
  - Document upload and processing
  - Real-time processing logs
  - Database exploration and management
  - System status monitoring
- **Technology**: Streamlit framework with custom CSS styling
- **Key Capabilities**:
  - Drag-and-drop file upload
  - Live progress tracking
  - Interactive data visualization
  - Background processing with real-time updates

#### Database Management Interface (`src/gui/database_management_ui.py`)
- **Purpose**: Specialized interface for database operations
- **Features**:
  - Database reset and wipe functionality
  - Multi-format data export (CSV, JSON, SQL)
  - Docker container management
  - Volume backup and restore
- **Integration**: Embedded within main Streamlit app

#### CLI Tools and Scripts (`scripts/`)
- **Purpose**: Command-line automation and scripting
- **Components**:
  - `database_manager.py`: Database operations CLI
  - `docker_db_manager.py`: Docker management CLI
  - `database_management_example.py`: Usage examples

### 2. Business Logic Layer

#### Document Processing Pipeline (`src/main_processor.py`)
- **Purpose**: Core document processing orchestration
- **Workflow**:
  1. File discovery and validation
  2. Document parsing and text extraction
  3. AI-powered project identification
  4. Data verification and enrichment
  5. Database storage and logging
- **Key Features**:
  - Multi-format document support
  - Batch processing capabilities
  - Error handling and recovery
  - Progress tracking and callbacks

#### AI/LLM Handler (`src/llm_handler.py`)
- **Purpose**: Integration with Ollama AI services
- **Capabilities**:
  - Model discovery and selection
  - Project name extraction from text
  - Context-aware verification
  - Structured data extraction
- **Key Functions**:
  - `get_available_ollama_models()`: Model enumeration
  - `get_project_names_from_text()`: Project identification
  - `enrich_and_verify_project_context()`: AI verification
  - `extract_all_document_data_verbatim()`: Comprehensive extraction

#### Database CRUD Operations (`src/database_crud.py`)
- **Purpose**: Database interaction layer
- **Features**:
  - Session management
  - CRUD operations for all entities
  - Query optimization
  - Connection pooling
- **Key Operations**:
  - Project and document management
  - Extraction log handling
  - Audit trail maintenance
  - Data export utilities

#### File System Handler (`src/file_system_handler.py`)
- **Purpose**: File management and discovery
- **Capabilities**:
  - Recursive file scanning
  - Format validation
  - Upload folder management
  - File metadata extraction

### 3. Data Access Layer

#### SQLAlchemy ORM (`src/database_models.py`)
- **Purpose**: Database schema definition and ORM mapping
- **Entities**:
  - `Project`: Core project information
  - `Document`: Document metadata and status
  - `Client`: Client information
  - `ProjectExtractionLog`: AI processing history
  - `Technology`, `Partner`, `ProjectFinancial`: Related entities
- **Features**:
  - Relationship mapping
  - Constraint enforcement
  - Migration support

#### Document Parsers (`src/parsers/`)
- **Purpose**: Format-specific document processing
- **Components**:
  - `pdf_parser.py`: PDF text and metadata extraction
  - `docx_parser.py`: Word document processing
  - `pptx_parser.py`: PowerPoint slide processing
  - `excel_parser.py`: Excel spreadsheet processing
- **Common Interface**: Standardized parsing output format

### 4. Infrastructure Layer

#### PostgreSQL Database
- **Purpose**: Primary data storage
- **Configuration**:
  - Docker container deployment
  - Volume-based persistence
  - Connection pooling
  - Backup and restore capabilities
- **Schema**: Comprehensive relational model with referential integrity

#### Ollama AI Engine
- **Purpose**: Local LLM deployment
- **Features**:
  - Multiple model support
  - GPU acceleration (optional)
  - API-based interaction
  - Model management
- **Models**: Support for various open-source LLMs

#### Docker Infrastructure
- **Purpose**: Containerized deployment
- **Services**:
  - PostgreSQL database container
  - Ollama AI service container
- **Features**:
  - Volume persistence
  - Service orchestration
  - Environment isolation

## Data Flow

### Document Processing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   File      │───►│   Parser    │───►│   Text      │
│   Upload    │    │   Selection │    │   Extraction│
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Database  │◄───│   AI        │◄───│   Project   │
│   Storage   │    │   Verification│   │   Detection │
└─────────────┘    └─────────────┘    └─────────────┘
```

### AI Processing Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Document  │───►│   LLM       │───►│   Project   │
│   Text      │    │   Analysis  │    │   Names     │
└─────────────┘    └─────────────┘    └─────────────┘
                                              │
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Verified  │◄───│   Context   │◄───│   Database  │
│   Projects  │    │   Enrichment│    │   Lookup    │
└─────────────┘    └─────────────┘    └─────────────┘
```

## Security Architecture

### Data Security
- **Local Processing**: All AI processing occurs locally via Ollama
- **Database Security**: PostgreSQL with configurable authentication
- **File Security**: Local file processing without external transmission
- **Network Security**: Services bound to localhost by default

### Access Control
- **Database**: Role-based access through PostgreSQL
- **File System**: OS-level file permissions
- **Web Interface**: No built-in authentication (add as needed)
- **API**: Local-only access by default

## Scalability Considerations

### Horizontal Scaling
- **Database**: PostgreSQL supports read replicas and sharding
- **AI Processing**: Multiple Ollama instances can be deployed
- **Web Interface**: Streamlit can be deployed behind load balancers

### Vertical Scaling
- **Memory**: Configurable for large document processing
- **CPU**: Multi-threaded processing support
- **Storage**: Volume-based storage with expansion capabilities

### Performance Optimization
- **Database**: Indexing and query optimization
- **AI Processing**: Model selection based on performance requirements
- **Caching**: Session-based caching for UI components
- **Batch Processing**: Efficient bulk operations

## Deployment Architecture

### Development Environment
```
┌─────────────────────────────────────────────────────────────────┐
│                        Developer Machine                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Python        │  │   Docker        │  │   Git           │  │
│  │   Application   │  │   Containers    │  │   Repository    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### Production Environment
```
┌─────────────────────────────────────────────────────────────────┐
│                        Production Server                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Load          │  │   Application   │  │   Database      │  │
│  │   Balancer      │  │   Containers    │  │   Cluster       │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   Monitoring    │  │   Backup        │  │   Security      │  │
│  │   & Logging     │  │   Storage       │  │   Layer         │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend Technologies
- **Python 3.8+**: Core application language
- **SQLAlchemy 2.0**: ORM and database abstraction
- **Pydantic 2.0**: Data validation and serialization
- **PostgreSQL**: Primary database
- **Docker**: Containerization platform

### AI/ML Technologies
- **Ollama**: Local LLM deployment platform
- **Various LLMs**: Gemma2, Llama3, Qwen2, etc.
- **Custom Prompting**: Structured AI interaction patterns

### Frontend Technologies
- **Streamlit**: Web application framework
- **HTML/CSS**: Custom styling and layouts
- **JavaScript**: Enhanced interactivity (via Streamlit)

### Document Processing
- **python-pptx**: PowerPoint processing
- **python-docx**: Word document processing
- **pdfplumber**: PDF text extraction
- **PyMuPDF**: Advanced PDF processing
- **openpyxl**: Excel spreadsheet processing

### DevOps & Utilities
- **Docker Compose**: Service orchestration
- **pytest**: Testing framework
- **Git**: Version control
- **Virtual Environments**: Dependency isolation

## Configuration Management

### Environment Variables
```bash
# Database Configuration
POSTGRES_USER=db_user
POSTGRES_PASSWORD=db_password
POSTGRES_DB=project_db
POSTGRES_HOST=localhost
POSTGRES_PORT=5432

# AI Configuration
OLLAMA_API_BASE_URL=http://localhost:11434/api
DEFAULT_LLM_MODEL=gemma2:9b

# Application Configuration
UPLOAD_FOLDER=data/upload_folder
EXPORT_FOLDER=data/database_exports
```

### Configuration Files
- `config/docker-compose.yml`: Docker service definitions
- `requirements.txt`: Python dependencies
- `.env`: Environment variables (create from `.env.example`)

## Monitoring and Logging

### Application Logging
- **Structured Logging**: Consistent log format across components
- **Real-time Logs**: Live log streaming in web interface
- **Log Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **Module-specific Loggers**: Separate loggers for each component

### System Monitoring
- **Database Health**: Connection status and performance metrics
- **Docker Status**: Container and volume monitoring
- **AI Service Health**: Ollama service availability
- **Processing Metrics**: Document processing statistics

### Error Handling
- **Graceful Degradation**: System continues operating with reduced functionality
- **Error Recovery**: Automatic retry mechanisms for transient failures
- **User Feedback**: Clear error messages and resolution guidance
- **Audit Trail**: Comprehensive logging of all operations

## Future Architecture Considerations

### Microservices Migration
- **Service Decomposition**: Split into focused microservices
- **API Gateway**: Centralized API management
- **Service Discovery**: Dynamic service registration
- **Inter-service Communication**: Message queues and event streaming

### Cloud Native Deployment
- **Kubernetes**: Container orchestration
- **Cloud Databases**: Managed PostgreSQL services
- **Object Storage**: Document storage in cloud storage
- **Auto-scaling**: Dynamic resource allocation

### Advanced AI Integration
- **Model Serving**: Dedicated AI inference services
- **Model Management**: Version control and A/B testing
- **Fine-tuning**: Custom model training capabilities
- **Multi-modal Processing**: Support for images and other media types

---

This architecture provides a solid foundation for the current system while allowing for future growth and enhancement. The modular design ensures maintainability and extensibility as requirements evolve. 