#!/usr/bin/env python3
"""
Database Manager for Project Database
Provides functionality to:
- Wipe/reset the database
- Export data in multiple formats (CSV, JSON, SQL dump)
- Manage database operations
- Ensure data persistence
"""

import os
import sys
import json
import csv
import subprocess
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import pandas as pd

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.database_crud import get_session
from src.database_models import (
    Base, Project, Client, ProjectClient, Document, Location,
    ProjectKeyInformation, Technology, ProjectTechnology,
    ProjectPersonnelRole, Partner, ProjectPartner, ProjectFinancial,
    ProjectPhaseMilestone, ProjectRiskOrChallenge, ProjectPhaseService,
    PrimarySector, ProjectSubCategory, ProjectCategoryAssignment,
    ProjectExtractionLog, ProjectExtractionLogTag, DocumentProcessingAuditLog,
    get_db_engine
)

class DatabaseManager:
    def __init__(self, export_dir: str = "data/database_exports"):
        """
        Initialize DatabaseManager with export directory.
        
        Args:
            export_dir: Directory for database exports (default: data/database_exports)
        """
        self.export_dir = Path(export_dir)
        self.ensure_export_directory()
    
    def ensure_export_directory(self):
        """Ensure the export directory exists"""
        self.export_dir.mkdir(parents=True, exist_ok=True)
    
    def get_db_url(self):
        """Get the database URL from environment or default"""
        return os.getenv('DATABASE_URL', 'postgresql://postgres:password@localhost:5432/project_db')
        
    def get_session(self):
        """Get a database session"""
        return get_session()
    
    def wipe_database(self, confirm: bool = False) -> bool:
        """
        Completely wipe the database by dropping and recreating all tables
        
        Args:
            confirm: If True, skip confirmation prompt
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not confirm:
            response = input("⚠️  WARNING: This will permanently delete ALL data in the database. Type 'CONFIRM' to proceed: ")
            if response != 'CONFIRM':
                print("❌ Database wipe cancelled.")
                return False
        
        try:
            print("🗑️  Wiping database...")
            engine = get_db_engine()
            
            # Drop all tables
            Base.metadata.drop_all(engine)
            print("✅ All tables dropped successfully")
            
            # Recreate all tables
            Base.metadata.create_all(engine)
            print("✅ All tables recreated successfully")
            
            print("🎉 Database wipe completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error wiping database: {e}")
            return False
    
    def export_to_csv(self, output_dir: Optional[str] = None) -> bool:
        """
        Export all database tables to CSV files
        
        Args:
            output_dir: Directory to save CSV files (defaults to database_exports/csv_TIMESTAMP)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if output_dir is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = self.export_dir / f"csv_{timestamp}"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            session = self.get_session()
            
            # Define all tables to export
            tables_to_export = [
                (Project, "projects"),
                (Client, "clients"),
                (ProjectClient, "project_clients"),
                (Document, "documents"),
                (Location, "locations"),
                (ProjectKeyInformation, "project_key_information"),
                (Technology, "technologies"),
                (ProjectTechnology, "project_technologies"),
                (ProjectPersonnelRole, "project_personnel_roles"),
                (Partner, "partners"),
                (ProjectPartner, "project_partners"),
                (ProjectFinancial, "project_financials"),
                (ProjectPhaseMilestone, "project_phase_milestones"),
                (ProjectRiskOrChallenge, "project_risks_challenges"),
                (ProjectPhaseService, "project_phase_services"),
                (PrimarySector, "primary_sectors"),
                (ProjectSubCategory, "project_sub_categories"),
                (ProjectCategoryAssignment, "project_category_assignments"),
                (ProjectExtractionLog, "project_extraction_logs"),
                (ProjectExtractionLogTag, "project_extraction_log_tags"),
                (DocumentProcessingAuditLog, "document_processing_audit_log")
            ]
            
            exported_files = []
            
            for model_class, filename in tables_to_export:
                try:
                    # Query all records from the table
                    records = session.query(model_class).all()
                    
                    if records:
                        # Convert to list of dictionaries
                        data = []
                        for record in records:
                            record_dict = {}
                            for column in model_class.__table__.columns:
                                value = getattr(record, column.name)
                                # Handle datetime objects
                                if hasattr(value, 'isoformat'):
                                    value = value.isoformat()
                                record_dict[column.name] = value
                            data.append(record_dict)
                        
                        # Write to CSV
                        csv_file = output_dir / f"{filename}.csv"
                        df = pd.DataFrame(data)
                        df.to_csv(csv_file, index=False)
                        exported_files.append(csv_file)
                        print(f"✅ Exported {len(records)} records to {csv_file}")
                    else:
                        print(f"⚠️  No records found in {filename}")
                        
                except Exception as e:
                    print(f"❌ Error exporting {filename}: {e}")
            
            session.close()
            
            # Create a summary file
            summary_file = output_dir / "export_summary.txt"
            with open(summary_file, 'w') as f:
                f.write(f"Database Export Summary\n")
                f.write(f"Export Date: {datetime.now().isoformat()}\n")
                f.write(f"Database URL: {self.get_db_url()}\n")
                f.write(f"Export Format: CSV\n")
                f.write(f"Files Exported: {len(exported_files)}\n\n")
                f.write("Exported Files:\n")
                for file in exported_files:
                    f.write(f"- {file.name}\n")
            
            print(f"🎉 CSV export completed! Files saved to: {output_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Error during CSV export: {e}")
            return False
    
    def export_to_json(self, output_dir: Optional[str] = None) -> bool:
        """
        Export all database tables to JSON files
        
        Args:
            output_dir: Directory to save JSON files (defaults to database_exports/json_TIMESTAMP)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if output_dir is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_dir = self.export_dir / f"json_{timestamp}"
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            session = self.get_session()
            
            # Define all tables to export
            tables_to_export = [
                (Project, "projects"),
                (Client, "clients"),
                (ProjectClient, "project_clients"),
                (Document, "documents"),
                (Location, "locations"),
                (ProjectKeyInformation, "project_key_information"),
                (Technology, "technologies"),
                (ProjectTechnology, "project_technologies"),
                (ProjectPersonnelRole, "project_personnel_roles"),
                (Partner, "partners"),
                (ProjectPartner, "project_partners"),
                (ProjectFinancial, "project_financials"),
                (ProjectPhaseMilestone, "project_phase_milestones"),
                (ProjectRiskOrChallenge, "project_risks_challenges"),
                (ProjectPhaseService, "project_phase_services"),
                (PrimarySector, "primary_sectors"),
                (ProjectSubCategory, "project_sub_categories"),
                (ProjectCategoryAssignment, "project_category_assignments"),
                (ProjectExtractionLog, "project_extraction_logs"),
                (ProjectExtractionLogTag, "project_extraction_log_tags"),
                (DocumentProcessingAuditLog, "document_processing_audit_log")
            ]
            
            all_data = {}
            exported_tables = []
            
            for model_class, table_name in tables_to_export:
                try:
                    # Query all records from the table
                    records = session.query(model_class).all()
                    
                    if records:
                        # Convert to list of dictionaries
                        data = []
                        for record in records:
                            record_dict = {}
                            for column in model_class.__table__.columns:
                                value = getattr(record, column.name)
                                # Handle datetime objects
                                if hasattr(value, 'isoformat'):
                                    value = value.isoformat()
                                # Handle Decimal objects
                                elif hasattr(value, '__float__'):
                                    value = float(value)
                                record_dict[column.name] = value
                            data.append(record_dict)
                        
                        all_data[table_name] = data
                        exported_tables.append(table_name)
                        print(f"✅ Prepared {len(records)} records from {table_name}")
                    else:
                        print(f"⚠️  No records found in {table_name}")
                        all_data[table_name] = []
                        
                except Exception as e:
                    print(f"❌ Error processing {table_name}: {e}")
                    all_data[table_name] = []
            
            session.close()
            
            # Write complete database to single JSON file
            json_file = output_dir / "complete_database.json"
            with open(json_file, 'w') as f:
                json.dump(all_data, f, indent=2, default=str)
            
            # Also write individual table files
            for table_name, data in all_data.items():
                if data:  # Only write if there's data
                    table_file = output_dir / f"{table_name}.json"
                    with open(table_file, 'w') as f:
                        json.dump(data, f, indent=2, default=str)
            
            # Create metadata file
            metadata = {
                "export_date": datetime.now().isoformat(),
                "database_url": self.get_db_url(),
                "export_format": "JSON",
                "tables_exported": exported_tables,
                "total_tables": len(tables_to_export)
            }
            
            metadata_file = output_dir / "export_metadata.json"
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            print(f"🎉 JSON export completed! Files saved to: {output_dir}")
            return True
            
        except Exception as e:
            print(f"❌ Error during JSON export: {e}")
            return False
    
    def export_sql_dump(self, output_file: Optional[str] = None) -> bool:
        """
        Create a PostgreSQL dump file that can be used to restore the database
        
        Args:
            output_file: Path to save the SQL dump (defaults to database_exports/dump_TIMESTAMP.sql)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if output_file is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.export_dir / f"dump_{timestamp}.sql"
            else:
                output_file = Path(output_file)
            
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Extract connection details from URL
            # Format: postgresql://user:password@host:port/database
            url_parts = self.get_db_url().replace("postgresql://", "").split("/")
            db_name = url_parts[1]
            user_host_port = url_parts[0].split("@")
            user_pass = user_host_port[0].split(":")
            host_port = user_host_port[1].split(":")
            
            user = user_pass[0]
            password = user_pass[1]
            host = host_port[0]
            port = host_port[1] if len(host_port) > 1 else "5432"
            
            # Set environment variable for password
            env = os.environ.copy()
            env['PGPASSWORD'] = password
            
            # Run pg_dump
            cmd = [
                'pg_dump',
                '-h', host,
                '-p', port,
                '-U', user,
                '-d', db_name,
                '--clean',  # Include DROP statements
                '--create', # Include CREATE DATABASE statement
                '--if-exists', # Use IF EXISTS for DROP statements
                '-f', str(output_file)
            ]
            
            print(f"🔄 Creating SQL dump...")
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✅ SQL dump created successfully: {output_file}")
                
                # Create a restore script
                restore_script = output_file.parent / f"restore_{output_file.stem}.sh"
                with open(restore_script, 'w') as f:
                    f.write("#!/bin/bash\n")
                    f.write("# Restore script for PostgreSQL database\n")
                    f.write("# Usage: ./restore_script.sh\n\n")
                    f.write("# Set these variables according to your target database\n")
                    f.write(f"HOST=\"{host}\"\n")
                    f.write(f"PORT=\"{port}\"\n")
                    f.write(f"USER=\"{user}\"\n")
                    f.write(f"DATABASE=\"{db_name}\"\n")
                    f.write(f"DUMP_FILE=\"{output_file.name}\"\n\n")
                    f.write("# Restore the database\n")
                    f.write("echo \"Restoring database from $DUMP_FILE...\"\n")
                    f.write("psql -h $HOST -p $PORT -U $USER -d postgres -f $DUMP_FILE\n")
                    f.write("echo \"Restore completed!\"\n")
                
                # Make restore script executable
                restore_script.chmod(0o755)
                print(f"✅ Restore script created: {restore_script}")
                
                return True
            else:
                print(f"❌ Error creating SQL dump: {result.stderr}")
                return False
                
        except FileNotFoundError:
            print("❌ Error: pg_dump not found. Please ensure PostgreSQL client tools are installed.")
            return False
        except Exception as e:
            print(f"❌ Error during SQL dump: {e}")
            return False
    
    def export_all_formats(self) -> bool:
        """
        Export database in all available formats
        
        Returns:
            bool: True if all exports successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_base_dir = self.export_dir / f"complete_export_{timestamp}"
        export_base_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"🚀 Starting complete database export to: {export_base_dir}")
        
        success_count = 0
        
        # CSV Export
        print("\n📊 Exporting to CSV...")
        if self.export_to_csv(export_base_dir / "csv"):
            success_count += 1
        
        # JSON Export
        print("\n📄 Exporting to JSON...")
        if self.export_to_json(export_base_dir / "json"):
            success_count += 1
        
        # SQL Dump Export
        print("\n🗃️  Creating SQL dump...")
        if self.export_sql_dump(export_base_dir / "database_dump.sql"):
            success_count += 1
        
        # Create overall summary
        summary_file = export_base_dir / "EXPORT_SUMMARY.md"
        with open(summary_file, 'w') as f:
            f.write("# Database Export Summary\n\n")
            f.write(f"**Export Date:** {datetime.now().isoformat()}\n")
            f.write(f"**Database URL:** {self.get_db_url()}\n")
            f.write(f"**Export Location:** {export_base_dir}\n")
            f.write(f"**Successful Exports:** {success_count}/3\n\n")
            f.write("## Export Formats\n\n")
            f.write("### CSV Files\n")
            f.write("- Location: `csv/` directory\n")
            f.write("- Format: Individual CSV files for each table\n")
            f.write("- Use: Data analysis, Excel import, etc.\n\n")
            f.write("### JSON Files\n")
            f.write("- Location: `json/` directory\n")
            f.write("- Format: Individual JSON files + complete database JSON\n")
            f.write("- Use: Application import, API data, etc.\n\n")
            f.write("### SQL Dump\n")
            f.write("- Location: `database_dump.sql`\n")
            f.write("- Format: PostgreSQL dump file\n")
            f.write("- Use: Complete database restoration\n")
            f.write("- Restore: Use the provided restore script\n\n")
            f.write("## Restoration\n\n")
            f.write("To restore the database:\n")
            f.write("1. **From SQL dump:** Use the restore script or `psql -f database_dump.sql`\n")
            f.write("2. **From JSON:** Use custom import scripts\n")
            f.write("3. **From CSV:** Import individual tables as needed\n")
        
        if success_count == 3:
            print(f"\n🎉 Complete export successful! All formats exported to: {export_base_dir}")
            return True
        else:
            print(f"\n⚠️  Partial export completed. {success_count}/3 formats successful.")
            return False
    
    def check_database_status(self) -> Dict[str, Any]:
        """
        Check database connection and get basic statistics
        
        Returns:
            Dict containing database status information
        """
        try:
            session = self.get_session()
            
            # Count records in main tables
            stats = {
                "connection": "✅ Connected",
                "projects": session.query(Project).count(),
                "documents": session.query(Document).count(),
                "clients": session.query(Client).count(),
                "extraction_logs": session.query(ProjectExtractionLog).count(),
            }
            
            session.close()
            return stats
            
        except Exception as e:
            return {
                "connection": f"❌ Failed: {e}",
                "projects": 0,
                "documents": 0,
                "clients": 0,
                "extraction_logs": 0,
            }


def main():
    parser = argparse.ArgumentParser(description="Database Manager for Project Database")
    parser.add_argument("--db-url", default="postgresql://db_user:db_password@localhost:5432/project_db",
                       help="Database URL")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Wipe command
    wipe_parser = subparsers.add_parser("wipe", help="Wipe the database")
    wipe_parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    # Export commands
    export_parser = subparsers.add_parser("export", help="Export database")
    export_parser.add_argument("format", choices=["csv", "json", "sql", "all"], 
                              help="Export format")
    export_parser.add_argument("--output", help="Output directory or file")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check database status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    db_manager = DatabaseManager(args.db_url)
    
    if args.command == "wipe":
        db_manager.wipe_database(args.confirm)
    
    elif args.command == "export":
        if args.format == "csv":
            db_manager.export_to_csv(args.output)
        elif args.format == "json":
            db_manager.export_to_json(args.output)
        elif args.format == "sql":
            db_manager.export_sql_dump(args.output)
        elif args.format == "all":
            db_manager.export_all_formats()
    
    elif args.command == "status":
        stats = db_manager.check_database_status()
        print("\n📊 Database Status:")
        print(f"Connection: {stats['connection']}")
        print(f"Projects: {stats['projects']}")
        print(f"Documents: {stats['documents']}")
        print(f"Clients: {stats['clients']}")
        print(f"Extraction Logs: {stats['extraction_logs']}")


if __name__ == "__main__":
    main() 