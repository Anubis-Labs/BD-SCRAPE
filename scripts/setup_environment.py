#!/usr/bin/env python3
"""
Equinox Document Intelligence Processor - Environment Setup Script

This script helps set up the development environment and verifies system requirements.
"""

import os
import sys
import subprocess
import shutil
import platform
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional

class EnvironmentSetup:
    """Comprehensive environment setup and verification."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.requirements_met = True
        self.setup_log = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log setup messages."""
        log_entry = f"[{level}] {message}"
        self.setup_log.append(log_entry)
        print(log_entry)
        
    def check_python_version(self) -> bool:
        """Check if Python version meets requirements."""
        self.log("Checking Python version...")
        
        version = sys.version_info
        required_major, required_minor = 3, 8
        
        if version.major < required_major or (version.major == required_major and version.minor < required_minor):
            self.log(f"Python {required_major}.{required_minor}+ required, found {version.major}.{version.minor}", "ERROR")
            return False
            
        self.log(f"Python {version.major}.{version.minor}.{version.micro} - OK")
        return True
        
    def check_docker(self) -> bool:
        """Check if Docker is installed and running."""
        self.log("Checking Docker installation...")
        
        try:
            # Check Docker version
            result = subprocess.run(['docker', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Docker not found or not working", "ERROR")
                return False
                
            self.log(f"Docker found: {result.stdout.strip()}")
            
            # Check if Docker daemon is running
            result = subprocess.run(['docker', 'ps'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Docker daemon not running", "ERROR")
                return False
                
            self.log("Docker daemon is running - OK")
            
            # Check Docker Compose
            result = subprocess.run(['docker-compose', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Docker Compose not found", "ERROR")
                return False
                
            self.log(f"Docker Compose found: {result.stdout.strip()}")
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            self.log(f"Docker check failed: {e}", "ERROR")
            return False
            
    def check_git(self) -> bool:
        """Check if Git is installed."""
        self.log("Checking Git installation...")
        
        try:
            result = subprocess.run(['git', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode != 0:
                self.log("Git not found", "WARNING")
                return False
                
            self.log(f"Git found: {result.stdout.strip()}")
            return True
            
        except (subprocess.TimeoutExpired, FileNotFoundError):
            self.log("Git not found", "WARNING")
            return False
            
    def check_system_resources(self) -> bool:
        """Check system resources."""
        self.log("Checking system resources...")
        
        try:
            import psutil
            
            # Check memory
            memory = psutil.virtual_memory()
            memory_gb = memory.total / (1024**3)
            
            if memory_gb < 8:
                self.log(f"Warning: Only {memory_gb:.1f}GB RAM available. 8GB+ recommended", "WARNING")
            else:
                self.log(f"Memory: {memory_gb:.1f}GB - OK")
                
            # Check disk space
            disk = psutil.disk_usage(str(self.project_root))
            disk_gb = disk.free / (1024**3)
            
            if disk_gb < 10:
                self.log(f"Warning: Only {disk_gb:.1f}GB disk space available. 10GB+ recommended", "WARNING")
            else:
                self.log(f"Disk space: {disk_gb:.1f}GB available - OK")
                
            return True
            
        except ImportError:
            self.log("psutil not available, skipping resource check", "WARNING")
            return True
        except Exception as e:
            self.log(f"Resource check failed: {e}", "WARNING")
            return True
            
    def create_directories(self) -> bool:
        """Create required directories."""
        self.log("Creating required directories...")
        
        directories = [
            "data/upload_folder",
            "data/database_exports", 
            "data/workspace_sample_documents",
            "logs",
            "backups"
        ]
        
        try:
            for directory in directories:
                dir_path = self.project_root / directory
                dir_path.mkdir(parents=True, exist_ok=True)
                self.log(f"Created directory: {directory}")
                
            return True
            
        except Exception as e:
            self.log(f"Failed to create directories: {e}", "ERROR")
            return False
            
    def setup_virtual_environment(self) -> bool:
        """Set up Python virtual environment."""
        self.log("Setting up virtual environment...")
        
        venv_path = self.project_root / "venv"
        
        if venv_path.exists():
            self.log("Virtual environment already exists")
            return True
            
        try:
            subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], 
                         check=True, timeout=60)
            self.log("Virtual environment created successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to create virtual environment: {e}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            self.log("Virtual environment creation timed out", "ERROR")
            return False
            
    def install_requirements(self) -> bool:
        """Install Python requirements."""
        self.log("Installing Python requirements...")
        
        requirements_file = self.project_root / "requirements.txt"
        if not requirements_file.exists():
            self.log("requirements.txt not found", "ERROR")
            return False
            
        # Determine pip executable
        if platform.system() == "Windows":
            pip_executable = self.project_root / "venv" / "Scripts" / "pip.exe"
        else:
            pip_executable = self.project_root / "venv" / "bin" / "pip"
            
        if not pip_executable.exists():
            # Fall back to system pip
            pip_executable = "pip"
            
        try:
            subprocess.run([str(pip_executable), 'install', '-r', str(requirements_file)], 
                         check=True, timeout=300)
            self.log("Requirements installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to install requirements: {e}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            self.log("Requirements installation timed out", "ERROR")
            return False
            
    def setup_environment_file(self) -> bool:
        """Set up environment configuration file."""
        self.log("Setting up environment configuration...")
        
        env_example = self.project_root / "config" / "env.example"
        env_file = self.project_root / ".env"
        
        if env_file.exists():
            self.log(".env file already exists")
            return True
            
        if not env_example.exists():
            self.log("env.example not found", "WARNING")
            return True
            
        try:
            shutil.copy2(env_example, env_file)
            self.log("Created .env file from template")
            self.log("Please review and customize .env file as needed", "INFO")
            return True
            
        except Exception as e:
            self.log(f"Failed to create .env file: {e}", "ERROR")
            return False
            
    def start_docker_services(self) -> bool:
        """Start Docker services."""
        self.log("Starting Docker services...")
        
        docker_compose_file = self.project_root / "config" / "docker-compose.yml"
        if not docker_compose_file.exists():
            self.log("docker-compose.yml not found", "ERROR")
            return False
            
        try:
            subprocess.run(['docker-compose', '-f', str(docker_compose_file), 'up', '-d'], 
                         check=True, timeout=120, cwd=str(self.project_root))
            self.log("Docker services started successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to start Docker services: {e}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            self.log("Docker services startup timed out", "ERROR")
            return False
            
    def verify_services(self) -> bool:
        """Verify that services are running correctly."""
        self.log("Verifying services...")
        
        try:
            # Test database connection
            sys.path.insert(0, str(self.project_root / "src"))
            from database_crud import get_db_session
            
            with get_db_session() as session:
                # Simple query to test connection
                session.execute("SELECT 1")
                self.log("Database connection - OK")
                
        except Exception as e:
            self.log(f"Database connection failed: {e}", "ERROR")
            return False
            
        try:
            # Test Ollama connection
            from llm_handler import get_available_ollama_models
            
            models = get_available_ollama_models()
            if models:
                self.log(f"Ollama connection - OK ({len(models)} models available)")
            else:
                self.log("Ollama connection - OK (no models installed yet)", "WARNING")
                
        except Exception as e:
            self.log(f"Ollama connection failed: {e}", "WARNING")
            
        return True
        
    def pull_default_model(self) -> bool:
        """Pull default AI model."""
        self.log("Pulling default AI model...")
        
        try:
            subprocess.run(['docker', 'exec', 'equinox_ollama_container', 
                          'ollama', 'pull', 'gemma2:9b'], 
                         check=True, timeout=600)
            self.log("Default model (gemma2:9b) pulled successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"Failed to pull default model: {e}", "WARNING")
            return False
        except subprocess.TimeoutExpired:
            self.log("Model pull timed out", "WARNING")
            return False
            
    def run_tests(self) -> bool:
        """Run system tests."""
        self.log("Running system tests...")
        
        test_file = self.project_root / "tests" / "test_db_management.py"
        if not test_file.exists():
            self.log("Test file not found", "WARNING")
            return True
            
        try:
            # Determine python executable
            if platform.system() == "Windows":
                python_executable = self.project_root / "venv" / "Scripts" / "python.exe"
            else:
                python_executable = self.project_root / "venv" / "bin" / "python"
                
            if not python_executable.exists():
                python_executable = sys.executable
                
            subprocess.run([str(python_executable), str(test_file)], 
                         check=True, timeout=120, cwd=str(self.project_root))
            self.log("System tests passed - OK")
            return True
            
        except subprocess.CalledProcessError as e:
            self.log(f"System tests failed: {e}", "ERROR")
            return False
        except subprocess.TimeoutExpired:
            self.log("System tests timed out", "ERROR")
            return False
            
    def generate_setup_report(self) -> str:
        """Generate setup report."""
        report = [
            "=" * 60,
            "EQUINOX DOCUMENT INTELLIGENCE PROCESSOR",
            "Environment Setup Report",
            "=" * 60,
            "",
            f"Setup completed at: {os.getcwd()}",
            f"Python version: {sys.version}",
            f"Platform: {platform.platform()}",
            "",
            "Setup Log:",
            "-" * 40
        ]
        
        report.extend(self.setup_log)
        
        report.extend([
            "",
            "-" * 40,
            "Next Steps:",
            "",
            "1. Review and customize .env file if needed",
            "2. Start the application:",
            "   streamlit run src/gui/streamlit_app.py",
            "3. Open browser to http://localhost:8501",
            "4. Upload test documents to verify functionality",
            "",
            "For troubleshooting, see docs/TROUBLESHOOTING.md",
            "For development info, see docs/DEVELOPER_GUIDE.md",
            "",
            "=" * 60
        ])
        
        return "\n".join(report)
        
    def run_setup(self) -> bool:
        """Run complete setup process."""
        self.log("Starting Equinox Document Intelligence Processor setup...")
        self.log(f"Project root: {self.project_root}")
        
        # Check prerequisites
        if not self.check_python_version():
            self.requirements_met = False
            
        if not self.check_docker():
            self.requirements_met = False
            
        self.check_git()  # Optional
        self.check_system_resources()  # Optional
        
        if not self.requirements_met:
            self.log("Prerequisites not met. Please install required software.", "ERROR")
            return False
            
        # Setup steps
        setup_steps = [
            ("Creating directories", self.create_directories),
            ("Setting up virtual environment", self.setup_virtual_environment),
            ("Installing requirements", self.install_requirements),
            ("Setting up environment file", self.setup_environment_file),
            ("Starting Docker services", self.start_docker_services),
            ("Verifying services", self.verify_services),
            ("Pulling default AI model", self.pull_default_model),
            ("Running system tests", self.run_tests)
        ]
        
        for step_name, step_function in setup_steps:
            self.log(f"Step: {step_name}")
            if not step_function():
                self.log(f"Setup step failed: {step_name}", "ERROR")
                # Continue with other steps even if one fails
                
        # Generate report
        report = self.generate_setup_report()
        
        # Save report
        report_file = self.project_root / "setup_report.txt"
        try:
            with open(report_file, 'w') as f:
                f.write(report)
            self.log(f"Setup report saved to: {report_file}")
        except Exception as e:
            self.log(f"Failed to save setup report: {e}", "WARNING")
            
        print("\n" + report)
        
        return True


def main():
    """Main setup function."""
    setup = EnvironmentSetup()
    
    try:
        success = setup.run_setup()
        
        if success:
            print("\n✅ Setup completed! Check the report above for any issues.")
            print("\nTo start the application:")
            print("  streamlit run src/gui/streamlit_app.py")
            return 0
        else:
            print("\n❌ Setup encountered errors. Check the log above.")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user.")
        return 1
    except Exception as e:
        print(f"\n\nSetup failed with unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 