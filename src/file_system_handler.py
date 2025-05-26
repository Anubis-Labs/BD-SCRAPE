import os
from pathlib import Path
from typing import List, Dict, Union, Optional, Tuple, Any
import datetime
import shutil # For clear_upload_folder
import logging

logger = logging.getLogger(__name__)

# Define relevant file types for parsing
SUPPORTED_EXTENSIONS = {".pptx", ".pdf", ".docx", ".xlsx", ".xls"}

# Define the upload folder name as a constant
UPLOAD_FOLDER = "upload_folder" # Relative to the workspace root typically

# Ensure the upload folder exists when the module is loaded (optional, good for robustness)
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

def find_project_files(root_folder: Union[str, Path], 
                       processed_files_log: Optional[Dict[str, datetime.datetime]] = None,
                       force_reprocess: bool = False) -> List[Dict[str, Union[str, Path]]]:
    """
    Traverses a root folder, identifies supported project document files,
    and optionally skips files that have already been processed based on a log.

    Args:
        root_folder: The path to the root folder to scan.
        processed_files_log: A dictionary where keys are absolute file paths (as strings)
                             and values are the datetime objects of their last processing.
                             Can be None if no log is used.
        force_reprocess: If True, all files will be included regardless of the log.

    Returns:
        A list of dictionaries, where each dictionary contains:
        - "file_path": The Path object of the discovered file.
        - "file_type": The extension of the file (e.g., ".pptx").
        - "status": "new" or "updated" or "skipped_processed"
    """
    discovered_files_info = []
    root_path = Path(root_folder)

    if not root_path.is_dir():
        logger.error(f"Error: Root folder '{root_folder}' does not exist or is not a directory.")
        return discovered_files_info

    if processed_files_log is None:
        processed_files_log = {} # Ensure it's a dict for consistent handling

    for item in root_path.rglob("*"): # rglob for recursive globbing
        if item.is_file() and item.suffix.lower() in SUPPORTED_EXTENSIONS:
            file_path_str = str(item.resolve()) # Use absolute, resolved path for logging
            file_status = "new" # Default status
            
            if not force_reprocess and file_path_str in processed_files_log:
                last_processed_time = processed_files_log[file_path_str]
                file_modified_time = datetime.datetime.fromtimestamp(item.stat().st_mtime)
                if file_modified_time > last_processed_time:
                    file_status = "updated"
                else:
                    file_status = "skipped_processed"
            
            if force_reprocess or file_status != "skipped_processed":
                discovered_files_info.append({
                    "file_path": item,
                    "file_type": item.suffix.lower(),
                    "status": file_status
                })
            # Optionally, log that a file was skipped if needed for verbose output
            # else:
            #     print(f"Skipping already processed file: {item}")
                
    return discovered_files_info


# Example of how a processed files log might be maintained (simplified)
# In a real application, this would be loaded from and saved to a persistent store (DB, file).
_processed_log_cache: Dict[str, datetime.datetime] = {}

def update_processed_log(file_path: Union[str, Path], process_time: Optional[datetime.datetime] = None):
    """Updates the processed log for a given file.
       In a real app, this should persist the log.
    """
    global _processed_log_cache
    resolved_path_str = str(Path(file_path).resolve())
    _processed_log_cache[resolved_path_str] = process_time or datetime.datetime.now()
    # print(f"Logged {resolved_path_str} as processed at {_processed_log_cache[resolved_path_str]}.") # For debugging

def load_processed_log() -> Dict[str, datetime.datetime]:
    """Loads the processed log.
       In a real app, this would load from a persistent store.
    """
    global _processed_log_cache
    # print(f"Loaded processed log with {len(_processed_log_cache)} items.") # For debugging
    return _processed_log_cache.copy() # Return a copy

def clear_processed_log():
    """Clears the in-memory processed log. For testing.
    """    
    global _processed_log_cache
    _processed_log_cache.clear()
    # print("Cleared processed log.")

def list_files_in_upload_folder() -> List[str]:
    """Lists the names of files directly within the UPLOAD_FOLDER."""
    upload_path = Path(UPLOAD_FOLDER)
    if not upload_path.is_dir():
        return []
    return sorted([f.name for f in upload_path.iterdir() if f.is_file()])

def clear_upload_folder() -> None:
    """Deletes all files directly within the UPLOAD_FOLDER."""
    upload_path = Path(UPLOAD_FOLDER)
    if not upload_path.is_dir():
        return
    for item in upload_path.iterdir():
        if item.is_file():
            try:
                item.unlink() # Deletes the file
            except Exception as e:
                # print(f"Error deleting file {item}: {e}") \
                logger.error(f"Error deleting file {item}: {e}", exc_info=True)
        # Optionally, handle subdirectories if they are not expected or should also be cleared.
        # For now, only files are deleted.

def get_file_stats() -> Tuple[int, List[Dict[str, Any]]]:
    """
    Calculates total size and details of files in the UPLOAD_FOLDER.
    Returns a tuple: (total_size_bytes, list_of_file_details_dicts).
    Each file_details_dict contains: {'name', 'size_bytes', 'modified_time'}.
    """
    upload_path = Path(UPLOAD_FOLDER)
    total_size_bytes = 0
    file_details_list = []
    if not upload_path.is_dir():
        return total_size_bytes, file_details_list

    for item in upload_path.iterdir():
        if item.is_file():
            try:
                stats = item.stat()
                size_bytes = stats.st_size
                modified_time = datetime.datetime.fromtimestamp(stats.st_mtime)
                file_details_list.append({
                    "name": item.name,
                    "size_bytes": size_bytes,
                    "modified_time": modified_time
                })
                total_size_bytes += size_bytes
            except Exception as e:
                # print(f"Error getting stats for file {item}: {e}")
                logger.error(f"Error getting stats for file {item}: {e}", exc_info=True)
    return total_size_bytes, file_details_list

if __name__ == '__main__':
    # Configure basic logging for direct script execution if not already configured by streamlit_app
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    logger.info(f"Current working directory: {os.getcwd()}")
    # Create a dummy directory structure and files for testing
    test_root = Path("test_project_folder")
    sub_folder = test_root / "sub_projectA"
    sub_folder_b = test_root / "sub_projectB_empty"
    
    try:
        sub_folder.mkdir(parents=True, exist_ok=True)
        sub_folder_b.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created directory: {test_root}")
        logger.info(f"Created directory: {sub_folder}")
        logger.info(f"Created directory: {sub_folder_b}")

        # Create some dummy files
        (test_root / "doc1.pptx").touch()
        (sub_folder / "doc2.pdf").touch()
        (sub_folder / "doc3.docx").touch()
        (sub_folder / "unsupported.txt").touch()
        (test_root / "Doc4.PPTX").touch() # Test case-insensitivity of extension
        (test_root / "~temporary_file.docx").touch() # Example of a file to potentially ignore later

        logger.info("\n--- Test 1: Initial Scan (no log) ---")
        files_to_process = find_project_files(test_root)
        for f_info in files_to_process:
            logger.info(f"Found: {f_info['file_path']} (Type: {f_info['file_type']}, Status: {f_info['status']})")
            update_processed_log(f_info['file_path']) # Simulate processing and logging
        
        logger.info(f"\nProcessed log after initial scan: {load_processed_log()}")

        logger.info("\n--- Test 2: Second Scan (with log, no changes) ---")
        # To make this test meaningful, we'd need to ensure file mod times are older than log times.
        # For simplicity, this scan should show them as 'skipped_processed' if log is used.
        files_to_process_again = find_project_files(test_root, processed_files_log=load_processed_log())
        if not files_to_process_again:
            logger.info("No new or updated files found, as expected.")
        for f_info in files_to_process_again:
             logger.info(f"Found: {f_info['file_path']} (Type: {f_info['file_type']}, Status: {f_info['status']})")

        logger.info("\n--- Test 3: Scan with force_reprocess=True ---")
        files_to_process_forced = find_project_files(test_root, processed_files_log=load_processed_log(), force_reprocess=True)
        for f_info in files_to_process_forced:
            logger.info(f"Found (forced): {f_info['file_path']} (Type: {f_info['file_type']}, Status: {f_info['status']})")

        logger.info("\n--- Test 4: Modifying a file and re-scanning ---")
        # Simulate modifying a file by touching it again (updates mtime)
        # Note: A tiny delay might be needed for mtime to differ enough from log time on some systems.
        import time
        time.sleep(0.1) # Small delay
        (test_root / "doc1.pptx").touch() 
        logger.info(f"Touched {test_root / 'doc1.pptx'} to update its modification time.")

        current_log = load_processed_log()
        files_after_mod = find_project_files(test_root, processed_files_log=current_log)
        found_updated = False
        for f_info in files_after_mod:
            logger.info(f"Found: {f_info['file_path']} (Type: {f_info['file_type']}, Status: {f_info['status']})")
            if f_info['status'] == 'updated':
                found_updated = True
        if not found_updated and not files_after_mod:
             logger.info("No files marked as updated (this might happen if mtime resolution is low or log time is too close).")
        elif not found_updated and any(f['status'] == 'skipped_processed' for f in files_after_mod):
             logger.info("File was found but not marked as updated. Check mtime vs log time.")

        logger.info("\n--- Test 5: Scanning non-existent directory ---")
        find_project_files("non_existent_folder")

    finally:
        # Clean up dummy files and folders
        import shutil
        if test_root.exists():
            shutil.rmtree(test_root)
            logger.info(f"\nCleaned up dummy directory: {test_root}")
        pass 