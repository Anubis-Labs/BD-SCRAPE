#!/usr/bin/env python3
"""
Docker Database Manager
Manages PostgreSQL database running in Docker with volume persistence
"""

import subprocess
import json
import argparse
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

class DockerDBManager:
    def __init__(self, compose_file: str = "docker-compose.yml"):
        self.compose_file = compose_file
        self.container_name = "equinox_project_db_container"
        self.volume_name = "bd_scrape_pgdata_vol"  # From docker-compose.yml
        
    def run_command(self, cmd: List[str], capture_output: bool = True) -> subprocess.CompletedProcess:
        """Run a command and return the result"""
        try:
            result = subprocess.run(cmd, capture_output=capture_output, text=True, check=False)
            return result
        except Exception as e:
            print(f"❌ Error running command {' '.join(cmd)}: {e}")
            return subprocess.CompletedProcess(cmd, 1, "", str(e))
    
    def check_docker_status(self) -> Dict[str, Any]:
        """Check Docker and container status"""
        status = {
            "docker_running": False,
            "container_exists": False,
            "container_running": False,
            "volume_exists": False,
            "compose_file_exists": Path(self.compose_file).exists()
        }
        
        # Check if Docker is running
        result = self.run_command(["docker", "version"])
        status["docker_running"] = result.returncode == 0
        
        if not status["docker_running"]:
            return status
        
        # Check if container exists
        result = self.run_command(["docker", "ps", "-a", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"])
        status["container_exists"] = self.container_name in result.stdout
        
        # Check if container is running
        result = self.run_command(["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Names}}"])
        status["container_running"] = self.container_name in result.stdout
        
        # Check if volume exists
        result = self.run_command(["docker", "volume", "ls", "--filter", f"name={self.volume_name}", "--format", "{{.Name}}"])
        status["volume_exists"] = self.volume_name in result.stdout
        
        return status
    
    def start_database(self) -> bool:
        """Start the PostgreSQL database using Docker Compose"""
        print("🚀 Starting PostgreSQL database...")
        
        if not Path(self.compose_file).exists():
            print(f"❌ Docker Compose file not found: {self.compose_file}")
            return False
        
        # Start the database service
        result = self.run_command(["docker-compose", "-f", self.compose_file, "up", "-d", "postgres_db"])
        
        if result.returncode == 0:
            print("✅ PostgreSQL database started successfully")
            return True
        else:
            print(f"❌ Failed to start database: {result.stderr}")
            return False
    
    def stop_database(self) -> bool:
        """Stop the PostgreSQL database"""
        print("🛑 Stopping PostgreSQL database...")
        
        result = self.run_command(["docker-compose", "-f", self.compose_file, "stop", "postgres_db"])
        
        if result.returncode == 0:
            print("✅ PostgreSQL database stopped successfully")
            return True
        else:
            print(f"❌ Failed to stop database: {result.stderr}")
            return False
    
    def restart_database(self) -> bool:
        """Restart the PostgreSQL database"""
        print("🔄 Restarting PostgreSQL database...")
        
        result = self.run_command(["docker-compose", "-f", self.compose_file, "restart", "postgres_db"])
        
        if result.returncode == 0:
            print("✅ PostgreSQL database restarted successfully")
            return True
        else:
            print(f"❌ Failed to restart database: {result.stderr}")
            return False
    
    def backup_volume(self, backup_path: Optional[str] = None) -> bool:
        """Create a backup of the PostgreSQL data volume"""
        if backup_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"database_backups/volume_backup_{timestamp}.tar"
        
        backup_file = Path(backup_path)
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        
        print(f"💾 Creating volume backup: {backup_file}")
        
        # Create a temporary container to backup the volume
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.volume_name}:/data",
            "-v", f"{backup_file.parent.absolute()}:/backup",
            "alpine",
            "tar", "czf", f"/backup/{backup_file.name}", "-C", "/data", "."
        ]
        
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print(f"✅ Volume backup created: {backup_file}")
            return True
        else:
            print(f"❌ Failed to create volume backup: {result.stderr}")
            return False
    
    def restore_volume(self, backup_path: str) -> bool:
        """Restore PostgreSQL data volume from backup"""
        backup_file = Path(backup_path)
        
        if not backup_file.exists():
            print(f"❌ Backup file not found: {backup_file}")
            return False
        
        print(f"📥 Restoring volume from backup: {backup_file}")
        
        # Stop the database first
        self.stop_database()
        
        # Remove existing volume data
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.volume_name}:/data",
            "alpine",
            "sh", "-c", "rm -rf /data/* /data/.*"
        ]
        self.run_command(cmd)
        
        # Restore from backup
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.volume_name}:/data",
            "-v", f"{backup_file.parent.absolute()}:/backup",
            "alpine",
            "tar", "xzf", f"/backup/{backup_file.name}", "-C", "/data"
        ]
        
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            print(f"✅ Volume restored from backup")
            # Start the database
            self.start_database()
            return True
        else:
            print(f"❌ Failed to restore volume: {result.stderr}")
            return False
    
    def wipe_volume(self, confirm: bool = False) -> bool:
        """Completely wipe the PostgreSQL data volume"""
        if not confirm:
            response = input("⚠️  WARNING: This will permanently delete ALL data in the PostgreSQL volume. Type 'CONFIRM' to proceed: ")
            if response != 'CONFIRM':
                print("❌ Volume wipe cancelled.")
                return False
        
        print("🗑️  Wiping PostgreSQL data volume...")
        
        # Stop the database first
        self.stop_database()
        
        # Remove the volume
        result = self.run_command(["docker", "volume", "rm", self.volume_name])
        
        if result.returncode == 0:
            print("✅ PostgreSQL data volume wiped successfully")
            # Start the database to recreate the volume
            self.start_database()
            return True
        else:
            print(f"❌ Failed to wipe volume: {result.stderr}")
            return False
    
    def get_volume_info(self) -> Dict[str, Any]:
        """Get information about the PostgreSQL data volume"""
        result = self.run_command(["docker", "volume", "inspect", self.volume_name])
        
        if result.returncode == 0:
            try:
                volume_info = json.loads(result.stdout)[0]
                return {
                    "name": volume_info["Name"],
                    "driver": volume_info["Driver"],
                    "mountpoint": volume_info["Mountpoint"],
                    "created": volume_info["CreatedAt"],
                    "size": self._get_volume_size()
                }
            except (json.JSONDecodeError, IndexError, KeyError) as e:
                print(f"❌ Error parsing volume info: {e}")
                return {}
        else:
            print(f"❌ Failed to get volume info: {result.stderr}")
            return {}
    
    def _get_volume_size(self) -> str:
        """Get the size of the PostgreSQL data volume"""
        cmd = [
            "docker", "run", "--rm",
            "-v", f"{self.volume_name}:/data",
            "alpine",
            "du", "-sh", "/data"
        ]
        
        result = self.run_command(cmd)
        
        if result.returncode == 0:
            return result.stdout.split()[0]
        else:
            return "Unknown"
    
    def ensure_persistence(self) -> bool:
        """Ensure database persistence is properly configured"""
        print("🔧 Checking database persistence configuration...")
        
        status = self.check_docker_status()
        
        if not status["compose_file_exists"]:
            print(f"❌ Docker Compose file not found: {self.compose_file}")
            return False
        
        if not status["docker_running"]:
            print("❌ Docker is not running")
            return False
        
        # Check if volume is properly configured in docker-compose.yml
        try:
            with open(self.compose_file, 'r') as f:
                compose_content = f.read()
                
            if "pgdata_vol:/var/lib/postgresql/data" in compose_content:
                print("✅ Volume mount is properly configured")
            else:
                print("⚠️  Volume mount may not be properly configured")
                return False
                
            if "pgdata_vol: {}" in compose_content:
                print("✅ Named volume is properly declared")
            else:
                print("⚠️  Named volume may not be properly declared")
                return False
                
        except Exception as e:
            print(f"❌ Error reading docker-compose.yml: {e}")
            return False
        
        # Start database if not running
        if not status["container_running"]:
            print("🚀 Starting database to ensure persistence...")
            self.start_database()
        
        print("✅ Database persistence is properly configured")
        return True
    
    def show_status(self):
        """Show comprehensive status of Docker database setup"""
        print("\n📊 Docker Database Status:")
        print("=" * 50)
        
        status = self.check_docker_status()
        
        print(f"Docker Running: {'✅' if status['docker_running'] else '❌'}")
        print(f"Compose File: {'✅' if status['compose_file_exists'] else '❌'} ({self.compose_file})")
        print(f"Container Exists: {'✅' if status['container_exists'] else '❌'} ({self.container_name})")
        print(f"Container Running: {'✅' if status['container_running'] else '❌'}")
        print(f"Volume Exists: {'✅' if status['volume_exists'] else '❌'} ({self.volume_name})")
        
        if status['volume_exists']:
            volume_info = self.get_volume_info()
            if volume_info:
                print(f"\n📁 Volume Information:")
                print(f"  Name: {volume_info.get('name', 'Unknown')}")
                print(f"  Size: {volume_info.get('size', 'Unknown')}")
                print(f"  Mount Point: {volume_info.get('mountpoint', 'Unknown')}")
                print(f"  Created: {volume_info.get('created', 'Unknown')}")


def main():
    parser = argparse.ArgumentParser(description="Docker Database Manager")
    parser.add_argument("--compose-file", default="docker-compose.yml", help="Docker Compose file path")
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Status command
    subparsers.add_parser("status", help="Show database status")
    
    # Start/Stop/Restart commands
    subparsers.add_parser("start", help="Start the database")
    subparsers.add_parser("stop", help="Stop the database")
    subparsers.add_parser("restart", help="Restart the database")
    
    # Volume management commands
    backup_parser = subparsers.add_parser("backup", help="Backup database volume")
    backup_parser.add_argument("--output", help="Backup file path")
    
    restore_parser = subparsers.add_parser("restore", help="Restore database volume")
    restore_parser.add_argument("backup_file", help="Backup file to restore from")
    
    wipe_parser = subparsers.add_parser("wipe-volume", help="Wipe database volume")
    wipe_parser.add_argument("--confirm", action="store_true", help="Skip confirmation prompt")
    
    # Persistence command
    subparsers.add_parser("ensure-persistence", help="Ensure database persistence is configured")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    manager = DockerDBManager(args.compose_file)
    
    if args.command == "status":
        manager.show_status()
    
    elif args.command == "start":
        manager.start_database()
    
    elif args.command == "stop":
        manager.stop_database()
    
    elif args.command == "restart":
        manager.restart_database()
    
    elif args.command == "backup":
        manager.backup_volume(args.output)
    
    elif args.command == "restore":
        manager.restore_volume(args.backup_file)
    
    elif args.command == "wipe-volume":
        manager.wipe_volume(args.confirm)
    
    elif args.command == "ensure-persistence":
        manager.ensure_persistence()


if __name__ == "__main__":
    main() 