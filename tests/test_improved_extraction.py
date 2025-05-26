#!/usr/bin/env python3
"""
Test script for improved document processing with verbatim extraction.
This script tests the enhanced functionality that addresses truncation issues
and improves verbatim text extraction.
"""

import os
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src import database_crud
from src import llm_handler
from src import main_processor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_llm_availability():
    """Test if LLM models are available."""
    logger.info("Testing LLM availability...")
    models = llm_handler.get_available_ollama_models()
    if models:
        logger.info(f"Available models: {models}")
        return models[0]  # Return first available model
    else:
        logger.error("No LLM models available. Please ensure Ollama is running.")
        return None

def test_document_processing():
    """Test the improved document processing functionality."""
    logger.info("Testing improved document processing...")
    
    # Get available model
    model = test_llm_availability()
    if not model:
        return False
    
    # Test with a sample document if available
    upload_folder = Path("upload_folder")
    if upload_folder.exists():
        documents = list(upload_folder.glob("*.pdf")) + list(upload_folder.glob("*.docx")) + list(upload_folder.glob("*.pptx"))
        if documents:
            test_doc = documents[0]
            logger.info(f"Testing with document: {test_doc.name}")
            
            try:
                # Process the document
                main_processor.process_documents(
                    selected_llm_model=model,
                    filename=test_doc.name,
                    upload_dir=str(upload_folder)
                )
                logger.info("Document processing completed successfully!")
                return True
            except Exception as e:
                logger.error(f"Document processing failed: {e}")
                return False
        else:
            logger.warning("No documents found in upload_folder for testing")
    else:
        logger.warning("upload_folder not found")
    
    return False

def test_database_connection():
    """Test database connection and functionality."""
    logger.info("Testing database connection...")
    
    try:
        db_session = database_crud.get_session()
        
        # Test basic query
        projects = database_crud.get_simple_project_list(db_session)
        logger.info(f"Found {len(projects)} projects in database")
        
        # Test document queries
        documents = database_crud.get_processed_documents(db_session)
        logger.info(f"Found {len(documents)} processed documents")
        
        db_session.close()
        logger.info("Database connection test successful!")
        return True
        
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False

def test_verbatim_extraction():
    """Test the verbatim extraction functionality."""
    logger.info("Testing verbatim extraction...")
    
    model = test_llm_availability()
    if not model:
        return False
    
    # Test with sample text
    sample_text = """
    Project Alpha Engineering Report
    
    Executive Summary:
    The West Doe Gas Processing Facility project, managed by Equinox Engineering, 
    commenced on January 15, 2024, with a total budget of $12.5 million CAD.
    
    Key Personnel:
    - Project Manager: Sarah Johnson
    - Lead Engineer: Michael Chen
    - Client Representative: David Wilson (Spectra Energy)
    
    Technical Specifications:
    - Processing capacity: 50 MMscf/d
    - Inlet pressure: 1,200 psig
    - Outlet pressure: 1,000 psig
    
    Project Timeline:
    - Phase 1 (Design): January 2024 - March 2024
    - Phase 2 (Construction): April 2024 - September 2024
    - Phase 3 (Commissioning): October 2024 - November 2024
    """
    
    try:
        # Test project name extraction
        logger.info("Testing project name extraction...")
        project_names = llm_handler.get_project_names_from_text(model, sample_text)
        logger.info(f"Extracted project names: {project_names}")
        
        # Test comprehensive data extraction
        logger.info("Testing comprehensive data extraction...")
        comprehensive_data = llm_handler.extract_all_document_data_verbatim(model, sample_text, "test_document.txt")
        
        if comprehensive_data:
            total_items = sum(len(items) if isinstance(items, list) else 1 for items in comprehensive_data.values())
            logger.info(f"Comprehensive extraction successful! Total items: {total_items}")
            
            # Log some sample extractions
            for category, items in comprehensive_data.items():
                if items and isinstance(items, list) and len(items) > 0:
                    logger.info(f"  {category}: {len(items)} items")
                    if len(items) > 0:
                        logger.info(f"    Sample: {items[0]}")
            
            return True
        else:
            logger.warning("Comprehensive extraction returned no data")
            return False
            
    except Exception as e:
        logger.error(f"Verbatim extraction test failed: {e}")
        return False

def main():
    """Run all tests."""
    logger.info("Starting improved extraction tests...")
    
    tests = [
        ("Database Connection", test_database_connection),
        ("LLM Availability", lambda: test_llm_availability() is not None),
        ("Verbatim Extraction", test_verbatim_extraction),
        ("Document Processing", test_document_processing),
    ]
    
    results = {}
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running test: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            status = "PASSED" if result else "FAILED"
            logger.info(f"Test {test_name}: {status}")
        except Exception as e:
            logger.error(f"Test {test_name} crashed: {e}")
            results[test_name] = False
    
    # Summary
    logger.info(f"\n{'='*50}")
    logger.info("TEST SUMMARY")
    logger.info(f"{'='*50}")
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "PASSED" if result else "FAILED"
        logger.info(f"{test_name}: {status}")
    
    logger.info(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        logger.info("🎉 All tests passed! The improved extraction is working correctly.")
    else:
        logger.warning("⚠️ Some tests failed. Please check the logs above for details.")

if __name__ == "__main__":
    main() 