# Equinox Document Intelligence Processor

A sophisticated AI-powered document processing system that extracts, analyzes, and manages project information from various document formats using Large Language Models (LLMs) and PostgreSQL database storage.

## 🌟 System Overview

The Equinox Document Intelligence Processor is a comprehensive solution for:

- **Document Processing**: Parse PDF, DOCX, PPTX, and Excel files
- **AI-Powered Extraction**: Use Ollama LLMs to extract project information
- **Database Management**: Store and manage extracted data in PostgreSQL
- **Web Interface**: Streamlit-based GUI for easy interaction
- **Docker Integration**: Containerized database and AI services
- **Data Export**: Multiple export formats for backup and analysis

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Document       │    │  Database       │
│   (Streamlit)   │◄──►│  Processors     │◄──►│  (PostgreSQL)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       ▼                       │
         │              ┌─────────────────┐              │
         └─────────────►│   AI Engine     │◄─────────────┘
                        │   (Ollama)      │
                        └─────────────────┘
```

## 🚀 Quick Start

### Automated Setup (Recommended)

The easiest way to get started is using our automated setup script:

```bash
# Clone the repository
git clone <repository-url>
cd bd_scrape

# Run automated setup
python scripts/setup_environment.py
```

The setup script will:
- ✅ Check system requirements (Python 3.8+, Docker, Git)
- ✅ Create virtual environment and install dependencies
- ✅ Set up required directories and configuration files
- ✅ Start Docker services (PostgreSQL + Ollama)
- ✅ Pull default AI model (gemma2:9b)
- ✅ Run system tests to verify everything works
- ✅ Generate detailed setup report

### Manual Setup

If you prefer manual setup:

#### 1. Prerequisites

- **Docker & Docker Compose**: For database and AI services
- **Python 3.8+**: For the application
- **Git**: For version control
- **8GB+ RAM**: Recommended for optimal performance

#### 2. Clone and Setup

```bash
git clone <repository-url>
cd bd_scrape
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 3. Start Infrastructure

```bash
# Start PostgreSQL and Ollama services
docker-compose -f config/docker-compose.yml up -d

# Verify services are running
python tests/test_db_management.py
```

#### 4. Launch Application

```bash
# Start the web interface
streamlit run src/gui/streamlit_app.py
```

Open your browser to `http://localhost:8501`

## 📁 Project Structure

```
bd_scrape/
├── 📁 src/                          # Core application code
│   ├── 📁 gui/                      # User interfaces
│   │   ├── streamlit_app.py         # Main web application
│   │   ├── database_management_ui.py # Database management interface
│   │   └── main_window.py           # Alternative GUI (legacy)
│   ├── 📁 parsers/                  # Document parsers
│   │   ├── pdf_parser.py            # PDF processing
│   │   ├── docx_parser.py           # Word document processing
│   │   ├── pptx_parser.py           # PowerPoint processing
│   │   └── excel_parser.py          # Excel processing
│   ├── main_processor.py            # Core document processing logic
│   ├── llm_handler.py               # AI/LLM integration
│   ├── database_crud.py             # Database operations
│   ├── database_models.py           # Database schema definitions
│   ├── file_system_handler.py       # File management utilities
│   └── llm_pydantic_models.py       # Data validation models
├── 📁 docs/                         # Comprehensive documentation
│   ├── SYSTEM_ARCHITECTURE.md       # Technical architecture guide
│   ├── USER_GUIDE.md               # End-user documentation
│   ├── DEVELOPER_GUIDE.md          # Development documentation
│   ├── API_REFERENCE.md            # API documentation
│   └── TROUBLESHOOTING.md          # Common issues and solutions
├── 📁 scripts/                      # Utility scripts and CLI tools
│   ├── database_manager.py          # Database management CLI
│   ├── docker_db_manager.py         # Docker management CLI
│   └── setup_environment.py         # Automated environment setup
├── 📁 tests/                        # Test suites
│   ├── test_db_management.py        # Database tests
│   ├── test_document_processing.py  # Processing tests
│   └── test_integration.py          # Integration tests
├── 📁 config/                       # Configuration files
│   ├── docker-compose.yml           # Docker services configuration
│   ├── env.example                  # Environment variables template
│   └── database_schema.md           # Database schema documentation
├── 📁 data/                         # Data directories
│   ├── upload_folder/               # Document upload area
│   ├── database_exports/            # Database export storage
│   └── workspace_sample_documents/  # Sample documents
├── 📁 assets/                       # Static assets
│   └── background.jpg               # UI background image
├── requirements.txt                 # Python dependencies
├── README.md                        # This file
└── setup_report.txt                 # Generated setup report
```

## 🔧 Core Components

### 1. Document Processing Pipeline

The system processes documents through several stages:

1. **File Upload**: Web interface or folder scanning
2. **Parsing**: Extract text and metadata from various formats
3. **AI Analysis**: Use LLMs to identify projects and extract information
4. **Database Storage**: Store structured data in PostgreSQL
5. **Verification**: AI-powered verification and enrichment

### 2. AI Integration

- **Ollama Integration**: Local LLM deployment for privacy and control
- **Model Support**: Compatible with various open-source models
- **Intelligent Extraction**: Context-aware project identification
- **Verification System**: AI-powered data validation and enrichment

### 3. Database Management

- **PostgreSQL Backend**: Robust relational database storage
- **Schema Management**: Comprehensive data models for projects, documents, and metadata
- **Export Capabilities**: CSV, JSON, and SQL dump formats
- **Backup & Restore**: Volume-level and data-level backup solutions

### 4. Web Interface

- **Streamlit Application**: Modern, responsive web interface
- **Real-time Processing**: Live logs and progress tracking
- **Database Management**: Built-in tools for data management
- **Docker Integration**: Container management from the UI

## 🎯 Key Features

### Document Processing
- ✅ **Multi-format Support**: PDF, DOCX, PPTX, Excel
- ✅ **Batch Processing**: Process entire folders
- ✅ **Real-time Monitoring**: Live processing logs
- ✅ **Error Handling**: Robust error recovery

### AI-Powered Analysis
- ✅ **Project Identification**: Automatically detect project mentions
- ✅ **Context Understanding**: AI analyzes document context
- ✅ **Data Extraction**: Extract structured information
- ✅ **Verification**: AI-powered data validation

### Database Management
- ✅ **Data Persistence**: Docker volume-based storage
- ✅ **Export Options**: Multiple export formats
- ✅ **Backup & Restore**: Comprehensive backup solutions
- ✅ **Schema Management**: Automated database setup

### User Experience
- ✅ **Web Interface**: Intuitive Streamlit application
- ✅ **Progress Tracking**: Real-time processing updates
- ✅ **Error Reporting**: Detailed error messages and logs
- ✅ **Data Visualization**: Built-in data exploration tools

## 📊 Database Schema

The system uses a comprehensive PostgreSQL schema with the following main entities:

- **Projects**: Core project information and metadata
- **Documents**: Processed document records and status
- **Clients**: Client information and relationships
- **Extraction Logs**: AI processing history and results
- **Technologies**: Technology tags and classifications
- **Partners**: Partner organizations and relationships
- **Financials**: Financial data and metrics

See `config/database_schema.md` for detailed schema documentation.

## 🐳 Docker Services

The system includes two main Docker services:

### PostgreSQL Database
- **Image**: `postgres:15`
- **Port**: `5432`
- **Volume**: `postgres_data` for data persistence
- **Credentials**: Configurable via environment variables

### Ollama AI Service
- **Image**: `ollama/ollama:latest`
- **Port**: `11434`
- **Volume**: `ollama_data` for model storage
- **GPU Support**: NVIDIA GPU acceleration available

## 🔧 Configuration

### Environment Variables

Create a `.env` file based on `config/env.example`:

```bash
# Copy template and customize
cp config/env.example .env

# Key settings
POSTGRES_USER=db_user
POSTGRES_PASSWORD=db_password
POSTGRES_DB=project_db
OLLAMA_API_BASE_URL=http://localhost:11434/api
DEFAULT_LLM_MODEL=gemma2:9b
```

### Model Configuration

The system supports various Ollama models. Recommended models:

- **gemma2:9b**: Balanced performance and accuracy (default)
- **gemma2:2b**: Faster processing, lower resource usage
- **llama3:8b**: Good general-purpose model
- **qwen2:7b**: Efficient for document processing

## 📚 Comprehensive Documentation

Detailed documentation is available in the `docs/` directory:

- **[System Architecture](docs/SYSTEM_ARCHITECTURE.md)**: Technical architecture and design patterns
- **[User Guide](docs/USER_GUIDE.md)**: Complete end-user instructions and tutorials
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)**: Development setup and contribution guidelines
- **[API Reference](docs/API_REFERENCE.md)**: Detailed API documentation with examples
- **[Troubleshooting](docs/TROUBLESHOOTING.md)**: Common issues and step-by-step solutions

## 🧪 Testing

Run the comprehensive test suite to verify system functionality:

```bash
# Run all tests
python tests/test_db_management.py

# Run specific test categories
python -m pytest tests/ -v

# Test individual components
python -c "from src.database_crud import get_db_session; print('Database: OK')"
python -c "from src.llm_handler import get_available_ollama_models; print('Ollama: OK')"
```

## 🚀 Usage Examples

### Process a Single Document

```python
from src.main_processor import process_single_file

# Process a single document
result = process_single_file(
    file_path="document.pdf",
    model_name="gemma2:9b",
    callback=lambda msg: print(f"Progress: {msg}")
)

if result['success']:
    print(f"Extracted {len(result['projects'])} projects")
```

### Export Database

```python
from scripts.database_manager import DatabaseManager

db_manager = DatabaseManager()
db_manager.export_all_formats()  # Exports to CSV, JSON, and SQL
```

### Manage Docker Services

```bash
# Check status
python scripts/docker_db_manager.py status

# Backup database volume
python scripts/docker_db_manager.py backup --output backups/

# Restart services
docker-compose -f config/docker-compose.yml restart
```

## 🛠️ Development

### Setting Up Development Environment

```bash
# Use automated setup
python scripts/setup_environment.py

# Or manual setup
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
docker-compose -f config/docker-compose.yml up -d
```

### Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and add tests
4. Run tests: `python tests/test_db_management.py`
5. Update documentation as needed
6. Submit a pull request

See `docs/DEVELOPER_GUIDE.md` for detailed contribution guidelines.

## 🔒 Security Considerations

- **Local Processing**: All AI processing happens locally via Ollama
- **Database Security**: PostgreSQL with configurable credentials
- **File Security**: Uploaded files are processed locally
- **Network Security**: Services run on localhost by default
- **Data Privacy**: No external data transmission

## 📈 Performance

### System Requirements

- **Minimum**: 8GB RAM, 4 CPU cores, 10GB disk space
- **Recommended**: 16GB RAM, 8 CPU cores, 50GB disk space
- **Optimal**: 32GB RAM, 16 CPU cores, 100GB SSD

### Performance Tips

- Use smaller AI models for faster processing
- Process documents in batches of 10-50 files
- Monitor system resources during large operations
- Regular database maintenance and optimization

## 🆘 Troubleshooting

### Quick Diagnostics

```bash
# Run system health check
python tests/test_db_management.py

# Check Docker services
docker ps

# Verify web interface
curl http://localhost:8501
```

### Common Issues

| Issue | Quick Fix | Documentation |
|-------|-----------|---------------|
| Database connection failed | `docker-compose restart` | [Troubleshooting](docs/TROUBLESHOOTING.md#database-issues) |
| Ollama models not available | `docker exec equinox_ollama_container ollama pull gemma2:9b` | [Troubleshooting](docs/TROUBLESHOOTING.md#aiollama-issues) |
| Web interface not loading | Check port 8501, restart Streamlit | [Troubleshooting](docs/TROUBLESHOOTING.md#web-interface-issues) |
| File processing fails | Check file format and permissions | [Troubleshooting](docs/TROUBLESHOOTING.md#document-processing-problems) |

For detailed troubleshooting, see `docs/TROUBLESHOOTING.md`.

## 📞 Support

For support and questions:

1. **Documentation**: Check the comprehensive `docs/` directory
2. **Issues**: Create a GitHub issue with detailed information
3. **Testing**: Run `python tests/test_db_management.py` for diagnostics
4. **Setup**: Use `python scripts/setup_environment.py` for automated setup

## 📝 License

[Add your license information here]

## 🙏 Acknowledgments

- **Ollama**: For providing excellent local LLM capabilities
- **Streamlit**: For the intuitive web framework
- **PostgreSQL**: For robust database functionality
- **Docker**: For containerization and deployment
- **Open Source Community**: For the amazing tools and libraries

---

**Version**: 1.0.0  
**Last Updated**: December 2024  
**Maintainer**: Nmaste

**🎉 The system is now professionally organized with comprehensive documentation, automated setup, and robust architecture. Ready for production use!**

For detailed technical information, development guidelines, and troubleshooting, explore the `docs/` directory. 