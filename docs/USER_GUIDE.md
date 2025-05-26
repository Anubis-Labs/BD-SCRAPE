# User Guide

## Welcome to Equinox Document Intelligence Processor

This guide will help you get started with the Equinox Document Intelligence Processor, a powerful AI-driven system for extracting and managing project information from documents.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Web Interface Overview](#web-interface-overview)
3. [Processing Documents](#processing-documents)
4. [Exploring Your Data](#exploring-your-data)
5. [Database Management](#database-management)
6. [Troubleshooting](#troubleshooting)
7. [Best Practices](#best-practices)

## Getting Started

### Prerequisites

Before you begin, ensure you have:
- A computer with Docker installed
- Python 3.8 or higher
- At least 8GB of RAM (16GB recommended for large documents)
- 10GB of free disk space

### Quick Setup

1. **Start the System**
   ```bash
   # Navigate to your project directory
   cd bd_scrape
   
   # Start the infrastructure
   docker-compose up -d
   
   # Launch the web interface
   streamlit run src/gui/streamlit_app.py
   ```

2. **Access the Application**
   - Open your web browser
   - Go to `http://localhost:8501`
   - You should see the Equinox Document Intelligence Processor interface

3. **Verify System Status**
   - Check that the database connection shows as "Connected"
   - Verify that Ollama models are available
   - Ensure Docker services are running

## Web Interface Overview

### Main Sections

The web interface is organized into several key sections:

#### 1. System Control Center
- **System Status**: Shows database and AI service connectivity
- **Processing Status**: Displays current processing activity
- **Live Metrics**: Real-time processing statistics

#### 2. Document Processing
- **Process Single File**: Upload and process individual documents
- **Process Folder**: Batch process multiple documents from a folder
- **Real-time Monitoring**: Live progress tracking and logs

#### 3. Knowledge Base Explorer
- **Browse All Projects**: View all processed projects
- **Project Details**: Detailed view of individual projects
- **Processed Documents**: Complete document inventory

#### 4. Database Management Center
- **Status & Overview**: Database statistics and health
- **Database Operations**: Export, reset, and maintenance tools
- **Docker Management**: Container and volume management

#### 5. Live Engineering Logs
- **Real-time Logs**: Live processing logs and system messages
- **Error Tracking**: Detailed error messages and resolution guidance
- **System Monitoring**: Performance metrics and status updates

## Processing Documents

### Single Document Processing

1. **Navigate to Document Processing Section**
   - Click on the "Process Single File" tab

2. **Upload Your Document**
   - Drag and drop a file into the upload area, or
   - Click "Browse files" to select a document
   - Supported formats: PDF, DOCX, PPTX, Excel (XLSX/XLS)

3. **Select AI Model**
   - Choose from available Ollama models
   - Recommended: `gemma2:9b` for balanced performance

4. **Start Processing**
   - Click "Process Uploaded File"
   - Monitor progress in real-time
   - View live logs for detailed processing information

5. **Review Results**
   - Check the Knowledge Base Explorer for extracted data
   - Review any error messages or warnings

### Batch Processing

1. **Prepare Your Documents**
   - Organize documents in a single folder
   - Ensure all files are in supported formats
   - Remove any corrupted or password-protected files

2. **Configure Batch Processing**
   - Navigate to "Process Folder" tab
   - Enter the full path to your document folder
   - Select your preferred AI model

3. **Start Batch Processing**
   - Click "Start Processing"
   - Monitor overall progress and individual file status
   - Use "Stop Processing" if you need to halt the operation

4. **Monitor Progress**
   - Watch the progress bar for overall completion
   - Review live logs for detailed processing information
   - Note any files that encounter errors

### Understanding Processing Stages

Each document goes through several stages:

1. **File Upload/Discovery**: System locates and validates files
2. **Parsing**: Extracts text and metadata from documents
3. **AI Analysis**: Uses LLMs to identify projects and extract information
4. **Verification**: AI verifies and enriches extracted data
5. **Database Storage**: Stores structured data in PostgreSQL

## Exploring Your Data

### Browse All Projects

1. **Access Project Browser**
   - Navigate to "Knowledge Base Explorer"
   - Click "Browse All Projects" tab

2. **Choose View Type**
   - **Simple View**: Shows latest extraction log only
   - **Comprehensive View**: Shows all gathered content

3. **Explore Project Data**
   - Use the interactive table to browse projects
   - Click column headers to sort data
   - Use search functionality to find specific projects

### Project Details

1. **Select a Project**
   - Choose a project from the dropdown menu
   - View comprehensive project information

2. **Review Extraction Logs**
   - Expand "View Full Extraction Log"
   - See AI processing history and decisions
   - Review confidence scores and reasoning

3. **Examine Documents**
   - View all documents associated with the project
   - See processing status and metadata
   - Access detailed key information extractions

### Document Inventory

1. **View All Processed Documents**
   - Navigate to "Processed Documents" tab
   - See complete inventory of processed files

2. **Search and Filter**
   - Use search box to find specific documents
   - Filter by file name, type, or project ID
   - Sort by various columns

3. **Document Details**
   - Review processing status and timestamps
   - See file metadata and statistics
   - Access associated project information

## Database Management

### Viewing Database Status

1. **Access Database Management**
   - Navigate to "Database Management Center"
   - Click "Status & Overview" tab

2. **Review Statistics**
   - See record counts for all data types
   - View recent activity and updates
   - Monitor database health metrics

3. **Check System Status**
   - Verify database connectivity
   - Review Docker container status
   - Monitor volume and persistence settings

### Exporting Data

1. **Choose Export Format**
   - Navigate to "Database Operations" → "Export Data"
   - Select from available formats:
     - **CSV Files**: For analysis and Excel import
     - **JSON Files**: For application integration
     - **SQL Dump**: For complete database backup
     - **All Formats**: Comprehensive export

2. **Configure Export**
   - Optionally specify custom export path
   - Review what will be included in export

3. **Start Export**
   - Click "Start Export"
   - Monitor progress and completion
   - Note export location for future reference

### Database Maintenance

1. **Database Reset** (⚠️ Use with caution)
   - Navigate to "Database Operations" → "Reset Database"
   - Type "CONFIRM RESET" to enable reset button
   - This permanently deletes all data while preserving schema

2. **Maintenance Tools**
   - Use "Analyze Database" for health checks
   - "Clear Cache" to refresh interface data
   - Review optimization suggestions

3. **Docker Management**
   - Start/stop/restart database containers
   - Create volume backups
   - Restore from backup files
   - Monitor container health

## Troubleshooting

### Common Issues

#### Database Connection Failed
**Symptoms**: Red "Database: Disconnected" status
**Solutions**:
1. Check if Docker containers are running: `docker ps`
2. Restart database: Navigate to Docker Management → "Start DB"
3. Verify docker-compose.yml configuration
4. Check Docker logs: `docker logs equinox_project_db_container`

#### No Ollama Models Available
**Symptoms**: Warning about missing models
**Solutions**:
1. Verify Ollama container is running
2. Pull required models: `docker exec equinox_ollama_container ollama pull gemma2:9b`
3. Check Ollama service health
4. Restart Ollama container if needed

#### Document Processing Fails
**Symptoms**: Error messages during processing
**Solutions**:
1. Check file format is supported
2. Verify file is not corrupted or password-protected
3. Review live logs for specific error details
4. Try processing a smaller test file first

#### Web Interface Not Loading
**Symptoms**: Browser cannot connect to localhost:8501
**Solutions**:
1. Verify Streamlit is running: Check terminal for startup messages
2. Try a different port: `streamlit run src/gui/streamlit_app.py --server.port 8502`
3. Check firewall settings
4. Try accessing from `127.0.0.1:8501` instead

### Getting Help

1. **Check Live Logs**: Real-time error messages and system status
2. **Review Documentation**: Comprehensive guides in `docs/` directory
3. **Run Tests**: `python tests/test_db_management.py` for system verification
4. **Check System Status**: Use built-in status monitoring tools

## Best Practices

### Document Preparation

1. **File Organization**
   - Organize documents in logical folder structures
   - Use descriptive file names
   - Remove duplicate or outdated files

2. **File Quality**
   - Ensure documents are not password-protected
   - Verify files are not corrupted
   - Use high-quality scans for PDF files

3. **Batch Size**
   - Process 10-50 documents at a time for optimal performance
   - Monitor system resources during large batch operations
   - Allow processing to complete before starting new batches

### System Maintenance

1. **Regular Backups**
   - Export database regularly using multiple formats
   - Create Docker volume backups before major operations
   - Store backups in secure, separate locations

2. **Performance Monitoring**
   - Monitor database size and performance
   - Check available disk space regularly
   - Review processing logs for optimization opportunities

3. **Updates and Maintenance**
   - Keep Docker images updated
   - Monitor for new Ollama model releases
   - Regularly clear old logs and temporary files

### Data Management

1. **Quality Control**
   - Review AI extraction results for accuracy
   - Verify project identifications are correct
   - Clean up duplicate or incorrect entries

2. **Organization**
   - Use consistent naming conventions
   - Maintain clear project categorizations
   - Document any manual corrections or additions

3. **Security**
   - Protect database credentials
   - Secure backup files appropriately
   - Monitor access to sensitive project information

### Performance Optimization

1. **Model Selection**
   - Choose appropriate AI models for your use case
   - Balance accuracy vs. processing speed
   - Test different models with sample documents

2. **Resource Management**
   - Monitor CPU and memory usage during processing
   - Adjust batch sizes based on system performance
   - Consider upgrading hardware for large-scale operations

3. **Database Optimization**
   - Regularly analyze database performance
   - Archive old extraction logs if database becomes large
   - Monitor query performance and optimize as needed

## Advanced Features

### Custom Processing Workflows

1. **Selective Processing**
   - Process specific document types separately
   - Use different AI models for different document categories
   - Implement custom validation rules

2. **Integration Options**
   - Export data for use in other systems
   - Develop custom scripts using the CLI tools
   - Integrate with existing document management systems

### Automation

1. **Scheduled Processing**
   - Set up automated document processing workflows
   - Use CLI tools for scripted operations
   - Implement monitoring and alerting

2. **Custom Scripts**
   - Develop custom processing scripts using the API
   - Automate data export and backup procedures
   - Create custom reporting and analysis tools

## Support and Resources

### Documentation
- **System Architecture**: Technical design and components
- **Developer Guide**: Development setup and contribution guidelines
- **API Reference**: Detailed API documentation
- **Troubleshooting**: Common issues and solutions

### Testing and Validation
- Run system tests: `python tests/test_db_management.py`
- Verify processing with sample documents
- Test backup and restore procedures

### Community and Support
- Review GitHub issues for known problems
- Contribute improvements and bug fixes
- Share best practices and use cases

---

This user guide provides comprehensive instructions for using the Equinox Document Intelligence Processor effectively. For technical details and development information, refer to the additional documentation in the `docs/` directory. 