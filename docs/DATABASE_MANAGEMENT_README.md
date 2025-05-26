# Database Management System

This document describes the comprehensive database management system for the Equinox Document Processor project.

## 🌟 Features Overview

The database management system provides:

- **Database Reset/Wipe**: Safely reset the database while preserving schema
- **Multi-format Export**: Export data in CSV, JSON, and SQL dump formats
- **Docker Integration**: Manage PostgreSQL containers and volumes
- **Volume Backup/Restore**: Create and restore database volume backups
- **Real-time Monitoring**: Live database statistics and status monitoring
- **Web Interface**: Complete Streamlit-based GUI for all operations
- **Command Line Tools**: CLI utilities for automation and scripting

## 📁 File Structure

```
├── database_manager.py          # Core database management utilities
├── docker_db_manager.py         # Docker container and volume management
├── src/gui/database_management_ui.py  # Streamlit web interface
├── test_db_management.py        # Test suite for all components
└── DATABASE_MANAGEMENT_README.md # This documentation
```

## 🚀 Quick Start

### 1. Web Interface (Recommended)

The easiest way to manage your database is through the web interface:

```bash
# Start the Streamlit app
streamlit run src/gui/streamlit_app.py
```

Navigate to the **"Database Management Center"** section in the web interface.

### 2. Command Line Interface

For automation and scripting, use the CLI tools:

```bash
# Check database status
python database_manager.py status

# Wipe database (with confirmation)
python database_manager.py wipe

# Export data in all formats
python database_manager.py export all

# Export specific format
python database_manager.py export csv --output ./my_export

# Docker operations
python docker_db_manager.py status
python docker_db_manager.py start
python docker_db_manager.py backup
```

## 🗄️ Database Operations

### Database Reset/Wipe

**⚠️ WARNING: This permanently deletes all data!**

**Web Interface:**
1. Go to "Database Operations" → "Reset Database" tab
2. Type `CONFIRM RESET` in the confirmation field
3. Click "RESET DATABASE"

**Command Line:**
```bash
# Interactive confirmation
python database_manager.py wipe

# Skip confirmation (for scripts)
python database_manager.py wipe --confirm
```

**What it does:**
- Drops all database tables
- Recreates empty tables with current schema
- Preserves table structure but removes all data
- Cannot be undone without a backup

### Data Export

Export your database in multiple formats for backup, analysis, or migration.

#### Export Formats

1. **CSV Files** - Individual CSV files for each table
   - Best for: Data analysis, Excel import, reporting
   - Output: Multiple `.csv` files + summary

2. **JSON Files** - Structured JSON data
   - Best for: Application import, API integration
   - Output: Individual JSON files + complete database JSON

3. **SQL Dump** - PostgreSQL dump file
   - Best for: Complete database restoration, migration
   - Output: `.sql` file + restore script

4. **All Formats** - Complete export in all formats
   - Best for: Comprehensive backup
   - Output: Organized folder with all formats

#### Export Examples

**Web Interface:**
1. Go to "Database Operations" → "Export Data" tab
2. Select export format
3. Optionally specify custom path
4. Click "Start Export"

**Command Line:**
```bash
# Export all formats with timestamp
python database_manager.py export all

# Export CSV to specific directory
python database_manager.py export csv --output ./backups/csv_export

# Export SQL dump
python database_manager.py export sql --output ./backups/database_backup.sql

# Export JSON
python database_manager.py export json
```

#### Export Output Structure

```
database_exports/
├── complete_export_20241201_143022/
│   ├── csv/
│   │   ├── projects.csv
│   │   ├── documents.csv
│   │   ├── clients.csv
│   │   └── export_summary.txt
│   ├── json/
│   │   ├── complete_database.json
│   │   ├── projects.json
│   │   ├── documents.json
│   │   └── export_metadata.json
│   ├── database_dump.sql
│   ├── restore_dump.sh
│   └── EXPORT_SUMMARY.md
```

## 🐳 Docker Management

Manage your PostgreSQL Docker container and ensure data persistence.

### Container Operations

**Web Interface:**
- Go to "Docker Management" tab
- Use the container operation buttons

**Command Line:**
```bash
# Check Docker and container status
python docker_db_manager.py status

# Start the database
python docker_db_manager.py start

# Stop the database
python docker_db_manager.py stop

# Restart the database
python docker_db_manager.py restart

# Ensure persistence is configured
python docker_db_manager.py ensure-persistence
```

### Volume Management

PostgreSQL data is stored in Docker volumes for persistence.

#### Volume Backup

**Web Interface:**
1. Go to "Docker Management" → "Volume Management"
2. Click "Backup Volume"

**Command Line:**
```bash
# Create volume backup with timestamp
python docker_db_manager.py backup

# Create backup with custom name
python docker_db_manager.py backup --output ./backups/my_volume_backup.tar
```

#### Volume Restore

**Web Interface:**
1. Go to "Docker Management" → "Volume Management"
2. Upload backup file
3. Click "Restore Volume"

**Command Line:**
```bash
# Restore from backup file
python docker_db_manager.py restore ./backups/volume_backup_20241201.tar
```

#### Volume Wipe

**⚠️ WARNING: This permanently deletes the entire volume!**

```bash
# Interactive confirmation
python docker_db_manager.py wipe-volume

# Skip confirmation (for scripts)
python docker_db_manager.py wipe-volume --confirm
```

## 📊 Monitoring & Status

### Database Statistics

The system provides comprehensive database statistics:

- **Record Counts**: Projects, documents, clients, etc.
- **Recent Activity**: Latest projects and documents
- **Connection Status**: Real-time database connectivity
- **Performance Metrics**: Optimization suggestions

### Docker Status

Monitor your Docker setup:

- **Docker Engine**: Running status
- **Container Status**: Exists, running state
- **Volume Status**: Exists, size, mount point
- **Compose File**: Configuration validation

## 🔧 Maintenance Tools

### Database Analysis

```bash
# Analyze database health
python database_manager.py status
```

Provides:
- Connection status
- Record counts by table
- Performance recommendations

### Cache Management

The web interface uses caching for performance. Clear cache when needed:

**Web Interface:**
- Go to "Database Operations" → "Maintenance" tab
- Click "Clear Cache"

### Optimization Suggestions

The system automatically provides optimization suggestions:
- Archive old extraction logs (>10,000 records)
- Implement pagination for large document sets (>1,000 documents)
- Performance tuning recommendations

## 🛡️ Data Persistence

### Ensuring Persistence

Your Docker setup uses named volumes for data persistence:

```yaml
# docker-compose.yml
volumes:
  - pgdata_vol:/var/lib/postgresql/data

volumes:
  pgdata_vol: {}
```

### Verification

```bash
# Check persistence configuration
python docker_db_manager.py ensure-persistence
```

This verifies:
- Volume mount configuration
- Named volume declaration
- Container restart policy

### Best Practices

1. **Regular Backups**: Create both volume backups and SQL dumps
2. **Test Restores**: Periodically test backup restoration
3. **Monitor Space**: Check volume size regularly
4. **Version Control**: Keep docker-compose.yml in version control

## 🚨 Troubleshooting

### Common Issues

#### Database Connection Failed
```bash
# Check if container is running
python docker_db_manager.py status

# Start the database if stopped
python docker_db_manager.py start

# Check logs
docker logs equinox_project_db_container
```

#### Export Failed
```bash
# Check disk space
df -h

# Check permissions
ls -la database_exports/

# Test database connection
python database_manager.py status
```

#### Volume Issues
```bash
# Check volume exists
docker volume ls | grep pgdata_vol

# Inspect volume
docker volume inspect bd_scrape_pgdata_vol

# Check container mounts
docker inspect equinox_project_db_container
```

### Recovery Procedures

#### Complete Data Loss Recovery
1. Stop the database: `python docker_db_manager.py stop`
2. Restore volume: `python docker_db_manager.py restore backup.tar`
3. Start the database: `python docker_db_manager.py start`

#### Partial Data Recovery
1. Export current data: `python database_manager.py export all`
2. Reset database: `python database_manager.py wipe --confirm`
3. Import from SQL dump: `psql -f backup.sql`

## 🔒 Security Considerations

### Database Credentials

Default credentials (change in production):
- **User**: `db_user`
- **Password**: `db_password`
- **Database**: `project_db`

### Access Control

- Database is only accessible on localhost:5432
- Web interface has no authentication (add if needed)
- File exports are stored locally

### Backup Security

- Volume backups contain all database data
- SQL dumps are plain text
- Store backups securely
- Consider encryption for sensitive data

## 📝 API Reference

### DatabaseManager Class

```python
from database_manager import DatabaseManager

db_manager = DatabaseManager()

# Check status
status = db_manager.check_database_status()

# Wipe database
success = db_manager.wipe_database(confirm=True)

# Export data
success = db_manager.export_to_csv()
success = db_manager.export_to_json()
success = db_manager.export_sql_dump()
success = db_manager.export_all_formats()
```

### DockerDBManager Class

```python
from docker_db_manager import DockerDBManager

docker_manager = DockerDBManager()

# Check status
status = docker_manager.check_docker_status()

# Container operations
docker_manager.start_database()
docker_manager.stop_database()
docker_manager.restart_database()

# Volume operations
docker_manager.backup_volume()
docker_manager.restore_volume("backup.tar")
docker_manager.wipe_volume(confirm=True)
```

## 🧪 Testing

Run the test suite to verify everything works:

```bash
python test_db_management.py
```

Tests include:
- Module imports
- Database connectivity
- Docker status checks
- UI component loading
- Export functionality

## 📞 Support

For issues or questions:

1. Check the troubleshooting section above
2. Run the test suite to identify problems
3. Check Docker and database logs
4. Verify all dependencies are installed

## 🔄 Updates

When updating the system:

1. **Backup first**: Create full export and volume backup
2. **Test in development**: Use test database
3. **Update dependencies**: Check requirements.txt
4. **Verify functionality**: Run test suite
5. **Update documentation**: Keep this README current

---

**Last Updated**: December 2024  
**Version**: 1.0.0 