# src/main_processor.py
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from sqlalchemy.orm import Session

# Use the new, clean db_logic file and an alias to minimize changes
from src import db_logic as database_crud
from src import llm_handler
from src.parsers import pptx_parser, pdf_parser, docx_parser, excel_parser
from src.file_system_handler import find_project_files

# Setup logger
logger = logging.getLogger(__name__)

def parse_document(file_path: Path) -> str:
    """
    Parses a document and returns its full verbatim text content.
    Returns an empty string if parsing fails or document is empty.
    """
    file_type = file_path.suffix.lower()
    logger.info(f"Parsing document: {file_path} (Type: {file_type})")
    try:
        if file_type == ".pptx":
            parsed_data = pptx_parser.parse_pptx(str(file_path))
            text = "\n\n".join(s.get("text", "") for s in parsed_data.get("text_from_slides", []))
            notes = "\n\n".join(n.get("notes", "") for n in parsed_data.get("speaker_notes", []))
            return f"{text}\n\n--- SPEAKER NOTES ---\n\n{notes}".strip()
        elif file_type == ".pdf":
            parsed_data = pdf_parser.parse_pdf(str(file_path))
            return "\n\n".join(p.get("text", "") for p in parsed_data.get("text_from_pages", []))
        elif file_type == ".docx":
            parsed_data = docx_parser.parse_docx(str(file_path))
            return parsed_data.get("document_text", "")
        elif file_type in [".xlsx", ".xls"]:
            parsed_data = excel_parser.parse_excel(str(file_path))
            return parsed_data.get("full_text", "")
        else:
            logger.warning(f"Unsupported file type: {file_type} for {file_path}")
            return ""
    except Exception as e:
        logger.error(f"Exception during parsing {file_path}: {e}", exc_info=True)
        return ""

def _chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """Splits text into overlapping chunks."""
    if not text:
        return []
    words = text.split()
    if not words:
        return []
    
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start += (chunk_size - overlap)
        
    return chunks

def process_single_file(db_session: Session, llm_model: str, file_path: Path):
    """
    The refactored core processing workflow for a single file. It chunks the document,
    finds project names, extracts relevant snippets, and appends them to the database.
    """
    logger.info(f"--- Starting new snippet extraction process for: {file_path.name} ---")

    # 1. Parse Document to get full verbatim text
    full_text = parse_document(file_path)
    if not full_text:
        logger.warning(f"No text content extracted from {file_path.name}. Skipping.")
        return

    # 2. Chunk the text for scalable processing
    text_chunks = _chunk_text(full_text)
    logger.info(f"Document split into {len(text_chunks)} chunks for analysis.")

    total_snippets_found = 0
    # A set to keep track of project names found in this document run
    projects_in_this_run = set()

    # 3. Iterate through chunks to find projects and extract snippets
    for i, chunk in enumerate(text_chunks):
        logger.info(f"Processing chunk {i+1}/{len(text_chunks)}...")
        
        # Step 3a: Find project names in the current chunk
        project_names = llm_handler.find_project_names_in_chunk(llm_model, chunk)
        
        if not project_names:
            logger.debug(f"No project names found in chunk {i+1}.")
            continue
        
        logger.info(f"Found potential projects in chunk {i+1}: {project_names}")

        # Step 3b: For each name, extract its specific snippet from the chunk
        for name in project_names:
            logger.info(f"Extracting snippet for '{name}' from chunk {i+1}...")
            projects_in_this_run.add(name) # Add name to our set
            snippet = llm_handler.extract_relevant_snippet(llm_model, chunk, name)
            
            if snippet:
                total_snippets_found += 1
                # Format the snippet with a header
                header = f"\n\n--- Snippet from '{file_path.name}' at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---\n\n"
                formatted_snippet = header + snippet
                
                # Step 3c: Append the formatted snippet to the project's data log
                try:
                    database_crud.append_to_project_data(
                        session=db_session,
                        project_name=name,
                        text_to_append=formatted_snippet
                    )
                    logger.info(f"Successfully appended snippet for '{name}' to the database.")
                except Exception as e:
                    logger.error(f"Failed to append snippet for project '{name}': {e}", exc_info=True)
            else:
                logger.warning(f"Could not extract a snippet for '{name}' from chunk {i+1}.")

    logger.info(f"--- Finished snippet extraction for: {file_path.name}. Found and appended {total_snippets_found} snippets. ---")

    # 4. Post-processing: Categorize all projects that were touched in this run
    if not projects_in_this_run:
        logger.info("No projects were identified in this document. Skipping categorization.")
        return

    logger.info(f"Starting categorization for {len(projects_in_this_run)} projects touched in this run...")
    for project_name in projects_in_this_run:
        try:
            # We need the full project data to categorize accurately
            full_project_data = database_crud.get_project_data(db_session, project_name)
            if not full_project_data:
                logger.warning(f"Could not retrieve full data for project '{project_name}'. Skipping categorization.")
                continue

            # Call the new LLM handler function
            categorization_result = llm_handler.categorize_project(llm_model, full_project_data)

            # Get the project ID to perform the update
            project = db_session.query(database_crud.Project).filter_by(project_name=project_name).first()
            if not project:
                logger.error(f"Logic error: Could not find project '{project_name}' in database for category update.")
                continue

            # Update the database with the new categories
            database_crud.update_project_categorization(
                session=db_session,
                project_id=project.project_id,
                category=categorization_result.get("category"),
                sub_category=categorization_result.get("sub_category"),
                project_scope=categorization_result.get("project_scope"),
            )
            logger.info(f"Successfully categorized and updated project: {project_name}")

        except Exception as e:
            logger.error(f"An error occurred during categorization for project '{project_name}': {e}", exc_info=True)

def process_documents(
    selected_llm_model: str,
    filename: str,
    upload_dir: Optional[str] = None,
    db_session: Optional[Session] = None,
    stop_callback: Optional[Callable[[], bool]] = None, 
):
    """
    Provides the entry point for processing a single file.
    It can use a provided database session or create its own.
    """
    if not upload_dir:
        logger.error("`upload_dir` must be provided.")
        return
        
    file_path = Path(upload_dir) / filename
    
    if not file_path.exists():
        logger.error(f"File not found at path: {file_path}")
        return

    # If a session is provided, use it. Otherwise, create a new one.
    if db_session:
        process_single_file(
            db_session=db_session,
            llm_model=selected_llm_model,
            file_path=file_path
        )
    else:
        logger.warning("No external DB session provided. Creating a temporary one.")
        try:
            with database_crud.get_session() as temp_session:
                process_single_file(
                    db_session=temp_session,
                    llm_model=selected_llm_model,
                    file_path=file_path
                )
        except Exception as e:
            logger.error(f"A critical error occurred in the processing entry point for {filename}: {e}", exc_info=True)

def process_folder_workflow(
    root_folder_to_scan: str,
    llm_model: str,
    force_reprocess: bool = False,
    stop_callback: Optional[Callable[[], bool]] = None,
):
    """Scans a root folder and processes all found documents."""
    logger.info(f"Starting folder scan workflow for: {root_folder_to_scan}")
    
    try:
        files_to_process = find_project_files(Path(root_folder_to_scan), force_reprocess)
    except Exception as e:
        logger.error(f"Error discovering files in {root_folder_to_scan}: {e}", exc_info=True)
        return

    if not files_to_process:
        logger.info("No new or updated files to process.")
        return

    logger.info(f"Found {len(files_to_process)} files to process.")
    
    with database_crud.get_session() as db_session:
        for i, file_info in enumerate(files_to_process):
            if stop_callback and stop_callback():
                logger.warning("Processing stopped by user request.")
                break
            
            logger.info(f"Processing file {i+1}/{len(files_to_process)}: {file_info['file_path'].name}")
            try:
                process_single_file(
                    db_session=db_session,
                    llm_model=llm_model,
                    file_path=file_info["file_path"],
                )
            except Exception as e:
                logger.error(
                    f"A critical unhandled error occurred in main workflow for file {file_info['file_path'].name}: {e}",
                    exc_info=True
                )

    logger.info("Folder scan workflow finished.") 