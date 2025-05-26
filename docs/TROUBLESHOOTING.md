# Troubleshooting Guide

## Overview

This guide helps you diagnose and resolve common issues with the Equinox Document Intelligence Processor. Issues are organized by category with step-by-step solutions.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Database Issues](#database-issues)
3. [Docker Problems](#docker-problems)
4. [AI/Ollama Issues](#aiollama-issues)
5. [Document Processing Problems](#document-processing-problems)
6. [Web Interface Issues](#web-interface-issues)
7. [Performance Problems](#performance-problems)
8. [File System Issues](#file-system-issues)
9. [Network and Connectivity](#network-and-connectivity)
10. [Advanced Troubleshooting](#advanced-troubleshooting)

## Quick Diagnostics

### System Health Check

Run this comprehensive test to identify issues:

```bash
# Navigate to project directory
cd bd_scrape

# Run system tests
python tests/test_db_management.py

# Check Docker status
docker ps

# Verify services
python -c "from src.database_crud import get_db_session; print('Database: OK')"
python -c "from src.llm_handler import get_available_ollama_models; print('Ollama: OK')"
```

### Quick Status Check

1. **Web Interface**: Go to `http://localhost:8501`
2. **Database Status**: Look for "Database: Connected" in the interface
3. **Ollama Status**: Check if models are listed in the dropdown
4. **Docker Status**: Verify containers are running

## Database Issues

### Database Connection Failed

**Symptoms:**
- Red "Database: Disconnected" status in web interface
- Error messages about database connection
- Tests fail with connection errors

**Solutions:**

#### 1. Check Docker Container Status
```bash
# Check if database container is running
docker ps | grep postgres

# If not running, start it
docker-compose -f config/docker-compose.yml up -d postgres

# Check container logs
docker logs equinox_project_db_container
```

#### 2. Verify Database Configuration
```bash
# Check environment variables
echo $POSTGRES_USER
echo $POSTGRES_PASSWORD
echo $POSTGRES_DB

# Verify docker-compose.yml settings
cat config/docker-compose.yml
```

#### 3. Reset Database Container
```bash
# Stop and remove container
docker stop equinox_project_db_container
docker rm equinox_project_db_container

# Restart with docker-compose
docker-compose -f config/docker-compose.yml up -d postgres
```

#### 4. Check Port Conflicts
```bash
# Check if port 5432 is in use
netstat -an | grep 5432

# If port is occupied, modify docker-compose.yml
# Change "5432:5432" to "5433:5432" and update connection settings
```

### Database Schema Issues

**Symptoms:**
- Table doesn't exist errors
- Column not found errors
- Foreign key constraint failures

**Solutions:**

#### 1. Recreate Database Schema
```python
# Run database initialization
python src/database_crud.py

# Or use the database manager
python scripts/database_manager.py init
```

#### 2. Check Schema Version
```python
from src.database_crud import get_db_session
from src.database_models import Project

with get_db_session() as session:
    # This will fail if schema is incorrect
    projects = session.query(Project).first()
    print("Schema is correct")
```

### Database Performance Issues

**Symptoms:**
- Slow query responses
- Timeouts during operations
- High memory usage

**Solutions:**

#### 1. Analyze Database Size
```python
from scripts.database_manager import DatabaseManager

manager = DatabaseManager()
stats = manager.get_database_stats()
print(f"Database size: {stats}")
```

#### 2. Optimize Database
```bash
# Connect to database and run optimization
docker exec -it equinox_project_db_container psql -U db_user -d project_db

# Run in PostgreSQL:
VACUUM ANALYZE;
REINDEX DATABASE project_db;
```

## Docker Problems

### Docker Service Not Running

**Symptoms:**
- "Docker is not running" errors
- Cannot connect to Docker daemon
- Containers not starting

**Solutions:**

#### 1. Start Docker Service
```bash
# Windows
net start com.docker.service

# Linux
sudo systemctl start docker

# macOS
open /Applications/Docker.app
```

#### 2. Check Docker Installation
```bash
# Verify Docker is installed and working
docker --version
docker-compose --version

# Test Docker functionality
docker run hello-world
```

### Container Startup Issues

**Symptoms:**
- Containers exit immediately
- Port binding errors
- Volume mount failures

**Solutions:**

#### 1. Check Container Logs
```bash
# View container logs
docker logs equinox_project_db_container
docker logs equinox_ollama_container

# Follow logs in real-time
docker logs -f equinox_project_db_container
```

#### 2. Check Port Conflicts
```bash
# Check if ports are already in use
netstat -an | grep 5432  # PostgreSQL
netstat -an | grep 11434 # Ollama

# Kill processes using the ports if necessary
# Windows: taskkill /PID <pid> /F
# Linux/Mac: kill -9 <pid>
```

#### 3. Volume Permission Issues
```bash
# Check volume permissions (Linux/Mac)
ls -la /var/lib/docker/volumes/

# Fix permissions if needed
sudo chown -R $USER:$USER ./data/
```

### Docker Compose Issues

**Symptoms:**
- Services fail to start together
- Network connectivity issues between containers
- Volume mounting problems

**Solutions:**

#### 1. Recreate Docker Compose Stack
```bash
# Stop all services
docker-compose -f config/docker-compose.yml down

# Remove volumes (⚠️ This deletes data)
docker-compose -f config/docker-compose.yml down -v

# Restart services
docker-compose -f config/docker-compose.yml up -d
```

#### 2. Check Docker Compose File
```bash
# Validate docker-compose.yml syntax
docker-compose -f config/docker-compose.yml config

# Check for syntax errors
yamllint config/docker-compose.yml
```

## AI/Ollama Issues

### Ollama Service Not Available

**Symptoms:**
- "No Ollama models available" warning
- Connection refused errors to Ollama
- Empty model dropdown in interface

**Solutions:**

#### 1. Check Ollama Container
```bash
# Verify Ollama container is running
docker ps | grep ollama

# Start Ollama container if not running
docker-compose -f config/docker-compose.yml up -d ollama

# Check Ollama logs
docker logs equinox_ollama_container
```

#### 2. Test Ollama Connection
```bash
# Test Ollama API directly
curl http://localhost:11434/api/tags

# Or use Python
python -c "from src.llm_handler import get_available_ollama_models; print(get_available_ollama_models())"
```

#### 3. Pull Required Models
```bash
# Pull a model manually
docker exec equinox_ollama_container ollama pull gemma2:9b

# List available models
docker exec equinox_ollama_container ollama list
```

### Model Loading Issues

**Symptoms:**
- Models fail to load
- Out of memory errors
- Slow model responses

**Solutions:**

#### 1. Check System Resources
```bash
# Check available memory
free -h  # Linux
wmic OS get TotalVisibleMemorySize,FreePhysicalMemory  # Windows

# Check GPU availability (if using GPU)
nvidia-smi
```

#### 2. Use Smaller Models
```bash
# Pull smaller models for testing
docker exec equinox_ollama_container ollama pull gemma2:2b
docker exec equinox_ollama_container ollama pull qwen2:1.5b
```

#### 3. Restart Ollama Service
```bash
# Restart Ollama container
docker restart equinox_ollama_container

# Wait for service to be ready
sleep 30
```

### AI Processing Errors

**Symptoms:**
- AI extraction returns empty results
- JSON parsing errors from AI responses
- Inconsistent AI outputs

**Solutions:**

#### 1. Test with Simple Documents
```python
# Test with a simple text document
from src.llm_handler import get_project_names_from_text

test_text = "This document describes Project Alpha implementation."
result = get_project_names_from_text(test_text, "gemma2:9b")
print(f"Result: {result}")
```

#### 2. Check Model Performance
```bash
# Test model directly
docker exec -it equinox_ollama_container ollama run gemma2:9b "Extract project names from: Project Alpha and Project Beta are mentioned."
```

#### 3. Adjust Prompts
```python
# Modify prompts in src/llm_handler.py for better results
# Test different prompt strategies
```

## Document Processing Problems

### File Upload Issues

**Symptoms:**
- Files fail to upload
- "File not supported" errors
- Upload progress stalls

**Solutions:**

#### 1. Check File Format Support
```python
# Verify file is supported
from src.file_system_handler import is_supported_file

supported = is_supported_file("document.pdf")
print(f"File supported: {supported}")
```

#### 2. Check File Permissions
```bash
# Verify file is readable
ls -la document.pdf

# Fix permissions if needed
chmod 644 document.pdf
```

#### 3. Check File Size
```bash
# Check file size (max 100MB recommended)
ls -lh document.pdf

# For large files, try splitting or compressing
```

### Parsing Errors

**Symptoms:**
- "Failed to parse document" errors
- Empty text extraction
- Corrupted file warnings

**Solutions:**

#### 1. Test Individual Parsers
```python
# Test PDF parser
from src.parsers.pdf_parser import parse_document
result = parse_document("document.pdf")
print(f"Error: {result.get('error')}")
print(f"Text length: {len(result.get('text', ''))}")
```

#### 2. Check Document Integrity
```bash
# For PDF files, try opening with different tools
# For Office files, try opening with LibreOffice/Office
```

#### 3. Convert Document Format
```bash
# Convert problematic files to supported formats
# PDF: Use PDF repair tools
# Office: Save as newer format versions
```

### Processing Timeouts

**Symptoms:**
- Processing hangs indefinitely
- Timeout errors during AI analysis
- Memory usage keeps increasing

**Solutions:**

#### 1. Process Smaller Batches
```python
# Reduce batch size for folder processing
# Process 5-10 files at a time instead of entire folders
```

#### 2. Monitor Resource Usage
```bash
# Monitor CPU and memory usage
top  # Linux/Mac
taskmgr  # Windows

# Check Docker container resources
docker stats
```

#### 3. Restart Services
```bash
# Restart all services
docker-compose -f config/docker-compose.yml restart
```

## Web Interface Issues

### Streamlit Not Loading

**Symptoms:**
- Browser cannot connect to localhost:8501
- "This site can't be reached" errors
- Blank page loads

**Solutions:**

#### 1. Check Streamlit Process
```bash
# Verify Streamlit is running
ps aux | grep streamlit  # Linux/Mac
tasklist | findstr streamlit  # Windows

# Start Streamlit if not running
streamlit run src/gui/streamlit_app.py
```

#### 2. Try Different Port
```bash
# Use alternative port
streamlit run src/gui/streamlit_app.py --server.port 8502

# Access via http://localhost:8502
```

#### 3. Check Firewall Settings
```bash
# Temporarily disable firewall for testing
# Windows: Windows Defender Firewall
# Linux: sudo ufw disable
# macOS: System Preferences > Security & Privacy > Firewall
```

### Interface Loading Slowly

**Symptoms:**
- Pages take long time to load
- Buttons don't respond quickly
- Database queries are slow

**Solutions:**

#### 1. Clear Browser Cache
- Clear browser cache and cookies
- Try incognito/private browsing mode
- Try different browser

#### 2. Optimize Database Queries
```python
# Check database performance
from scripts.database_manager import DatabaseManager

manager = DatabaseManager()
stats = manager.get_database_stats()
print(f"Database performance: {stats}")
```

#### 3. Restart Streamlit
```bash
# Stop Streamlit (Ctrl+C)
# Restart with fresh session
streamlit run src/gui/streamlit_app.py
```

### Session State Issues

**Symptoms:**
- Settings don't persist
- Uploaded files disappear
- Interface resets unexpectedly

**Solutions:**

#### 1. Clear Streamlit Cache
```python
# Add to your script or run in interface
import streamlit as st
st.cache_data.clear()
st.cache_resource.clear()
```

#### 2. Check Session State
```python
# Debug session state in Streamlit
import streamlit as st
st.write("Session state:", st.session_state)
```

## Performance Problems

### Slow Document Processing

**Symptoms:**
- Processing takes very long time
- High CPU/memory usage
- System becomes unresponsive

**Solutions:**

#### 1. Optimize Processing Settings
```python
# Use faster AI models
models = ["gemma2:2b", "qwen2:1.5b"]  # Smaller, faster models

# Process smaller batches
batch_size = 5  # Instead of processing entire folders
```

#### 2. Monitor System Resources
```bash
# Check system resources
htop  # Linux
Activity Monitor  # macOS
Task Manager  # Windows

# Check Docker resource usage
docker stats
```

#### 3. Optimize Database
```sql
-- Connect to database and optimize
docker exec -it equinox_project_db_container psql -U db_user -d project_db

-- Run optimization commands
VACUUM ANALYZE;
REINDEX DATABASE project_db;
```

### Memory Issues

**Symptoms:**
- Out of memory errors
- System swap usage high
- Docker containers killed

**Solutions:**

#### 1. Increase Docker Memory Limits
```yaml
# In docker-compose.yml, add memory limits
services:
  postgres:
    mem_limit: 2g
  ollama:
    mem_limit: 4g
```

#### 2. Process Files Individually
```python
# Instead of batch processing, process one file at a time
# Clear memory between files
import gc
gc.collect()
```

#### 3. Use Smaller AI Models
```bash
# Pull and use smaller models
docker exec equinox_ollama_container ollama pull gemma2:2b
```

## File System Issues

### Permission Denied Errors

**Symptoms:**
- Cannot read/write files
- Upload folder access denied
- Export operations fail

**Solutions:**

#### 1. Fix File Permissions
```bash
# Fix permissions for data directories
chmod -R 755 data/
chown -R $USER:$USER data/

# For Windows, check folder properties and security settings
```

#### 2. Check Disk Space
```bash
# Check available disk space
df -h  # Linux/Mac
dir  # Windows

# Clean up old exports if needed
rm -rf data/database_exports/old_exports/
```

#### 3. Verify Paths
```python
# Check if paths exist and are accessible
import os
print(f"Upload folder exists: {os.path.exists('data/upload_folder')}")
print(f"Export folder exists: {os.path.exists('data/database_exports')}")
```

### File Not Found Errors

**Symptoms:**
- Cannot find uploaded files
- Missing configuration files
- Import/export path errors

**Solutions:**

#### 1. Verify File Paths
```python
# Check current working directory
import os
print(f"Current directory: {os.getcwd()}")
print(f"Files in directory: {os.listdir('.')}")
```

#### 2. Use Absolute Paths
```python
# Use absolute paths instead of relative paths
import os
upload_folder = os.path.abspath("data/upload_folder")
```

#### 3. Recreate Missing Directories
```bash
# Recreate required directories
mkdir -p data/upload_folder
mkdir -p data/database_exports
mkdir -p data/workspace_sample_documents
```

## Network and Connectivity

### Port Conflicts

**Symptoms:**
- "Port already in use" errors
- Cannot bind to port
- Services fail to start

**Solutions:**

#### 1. Find Process Using Port
```bash
# Find what's using the port
lsof -i :5432  # Linux/Mac
netstat -ano | findstr :5432  # Windows

# Kill the process if safe to do so
kill -9 <PID>  # Linux/Mac
taskkill /PID <PID> /F  # Windows
```

#### 2. Use Different Ports
```yaml
# Modify docker-compose.yml
services:
  postgres:
    ports:
      - "5433:5432"  # Use port 5433 instead
  ollama:
    ports:
      - "11435:11434"  # Use port 11435 instead
```

#### 3. Update Connection Settings
```python
# Update database connection settings
POSTGRES_PORT = 5433  # Match new port
OLLAMA_PORT = 11435   # Match new port
```

### Network Connectivity Issues

**Symptoms:**
- Cannot connect between containers
- External network access blocked
- DNS resolution failures

**Solutions:**

#### 1. Check Docker Network
```bash
# List Docker networks
docker network ls

# Inspect network configuration
docker network inspect equinox_network
```

#### 2. Test Container Connectivity
```bash
# Test connectivity between containers
docker exec equinox_project_db_container ping equinox_ollama_container
```

#### 3. Restart Docker Network
```bash
# Recreate Docker network
docker-compose -f config/docker-compose.yml down
docker network prune
docker-compose -f config/docker-compose.yml up -d
```

## Advanced Troubleshooting

### Debug Mode

Enable debug logging for detailed troubleshooting:

```python
# Add to your Python scripts
import logging
logging.basicConfig(level=logging.DEBUG)

# Or set environment variable
export DEBUG=True
```

### System Information Collection

Collect comprehensive system information:

```bash
# Create system info script
cat > debug_info.sh << 'EOF'
#!/bin/bash
echo "=== System Information ==="
uname -a
python --version
docker --version
docker-compose --version

echo "=== Docker Status ==="
docker ps -a
docker images
docker volume ls

echo "=== Network Status ==="
netstat -an | grep -E "(5432|11434|8501)"

echo "=== Disk Space ==="
df -h

echo "=== Memory Usage ==="
free -h

echo "=== Process List ==="
ps aux | grep -E "(python|docker|streamlit)"
EOF

chmod +x debug_info.sh
./debug_info.sh > system_debug.txt
```

### Log Analysis

Analyze logs for patterns:

```bash
# Collect all relevant logs
mkdir debug_logs
docker logs equinox_project_db_container > debug_logs/postgres.log 2>&1
docker logs equinox_ollama_container > debug_logs/ollama.log 2>&1

# Search for error patterns
grep -i error debug_logs/*.log
grep -i "connection refused" debug_logs/*.log
grep -i "timeout" debug_logs/*.log
```

### Database Debugging

Deep database analysis:

```sql
-- Connect to database
docker exec -it equinox_project_db_container psql -U db_user -d project_db

-- Check database size and statistics
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats
WHERE schemaname = 'public';

-- Check for locks
SELECT * FROM pg_locks WHERE NOT granted;

-- Check active connections
SELECT * FROM pg_stat_activity;
```

### Performance Profiling

Profile application performance:

```python
# Add profiling to your code
import cProfile
import pstats

def profile_function():
    # Your function to profile
    pass

# Run profiler
cProfile.run('profile_function()', 'profile_stats')
stats = pstats.Stats('profile_stats')
stats.sort_stats('cumulative').print_stats(10)
```

## Getting Help

### Before Seeking Help

1. **Run System Tests**: `python tests/test_db_management.py`
2. **Check Logs**: Review Docker and application logs
3. **Verify Configuration**: Ensure all settings are correct
4. **Try Minimal Example**: Test with simple, known-good data

### Information to Provide

When seeking help, include:

1. **System Information**: OS, Python version, Docker version
2. **Error Messages**: Complete error messages and stack traces
3. **Steps to Reproduce**: Exact steps that cause the issue
4. **Configuration**: Relevant configuration files and settings
5. **Logs**: Relevant log excerpts (sanitize sensitive information)

### Common Solutions Summary

| Issue Type | Quick Fix | Full Solution |
|------------|-----------|---------------|
| Database Connection | Restart containers | Check configuration, recreate containers |
| Ollama Not Available | Pull models | Restart Ollama, check resources |
| File Upload Fails | Check permissions | Verify file format, check disk space |
| Slow Processing | Use smaller models | Optimize database, increase resources |
| Interface Not Loading | Restart Streamlit | Check ports, clear cache |
| Memory Issues | Restart services | Increase limits, optimize processing |

---

This troubleshooting guide covers the most common issues you may encounter. For additional help, refer to the system logs and consider running the comprehensive test suite to identify specific problems. 