import argparse
import os
import sys
from pathlib import Path
import logging

# Add project root to the Python path to allow imports from 'src'
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now, we can import from 'src'
from src.file_system_handler import find_project_files
from src.main_processor import process_documents
from src.database_crud import get_session
from src.logging_config import setup_logging

# Setup basic logging for the script
setup_logging(level='INFO')
logger = logging.getLogger(__name__)

# --- CONFIGURATION ---
# Default LLM model to use for processing.
# Ensure this model is available in your Ollama instance.
DEFAULT_LLM_MODEL = "gemma2:9b"

def process_folder_from_backend(folder_path: str, llm_model: str, force_reprocess: bool):
    """
    Scans a folder and processes all supported files using the main processing logic.
    
    Args:
        folder_path: The full path to the folder to process.
        llm_model: The name of the Ollama model to use.
        force_reprocess: If True, re-processes files even if they've been logged before.
    """
    logger.info(f"--- Starting Backend Folder Processing ---")
    logger.info(f"Target folder: {folder_path}")
    logger.info(f"LLM Model: {llm_model}")
    logger.info(f"Force Reprocess: {force_reprocess}")
    
    target_path = Path(folder_path)
    if not target_path.is_dir():
        logger.error(f"Error: The provided path is not a valid directory or is not accessible: {folder_path}")
        return

    logger.info("Discovering files in the target folder...")
    try:
        files_to_process = find_project_files(target_path, force_reprocess=force_reprocess)
    except Exception as e:
        logger.error(f"Failed to discover files due to an error: {e}", exc_info=True)
        return
        
    if not files_to_process:
        logger.warning("No new or updated supported files (.pdf, .docx, .pptx, .xlsx) found to process.")
        return
        
    logger.info(f"Found {len(files_to_process)} file(s) to process.")
    
    total_files = len(files_to_process)
    success_count = 0
    failure_count = 0
    
    for i, file_info in enumerate(files_to_process):
        file_path = file_info["file_path"]
        filename = file_path.name
        directory = str(file_path.parent)
        
        logger.info(f"--- Processing file {i+1}/{total_files}: {filename} ---")
        
        try:
            # The process_documents function handles its own database session
            process_documents(
                selected_llm_model=llm_model,
                filename=filename,
                upload_dir=directory
            )
            logger.info(f"Successfully processed: {filename}")
            success_count += 1
        except Exception as e:
            logger.error(f"A critical error occurred while processing {filename}: {e}", exc_info=True)
            failure_count += 1
            
    logger.info("--- Backend Processing Complete ---")
    logger.info(f"Summary: {success_count} succeeded, {failure_count} failed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Manually process a folder of documents from the backend, bypassing the Streamlit UI.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "folder_path",
        type=str,
        help="The full path to the folder containing documents to process."
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_LLM_MODEL,
        help=f"The name of the Ollama model to use for processing.\n(default: {DEFAULT_LLM_MODEL})"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force the reprocessing of all files, even if they have been processed before."
    )
    
    args = parser.parse_args()
    
    process_folder_from_backend(
        folder_path=args.folder_path,
        llm_model=args.model,
        force_reprocess=args.force
    ) 