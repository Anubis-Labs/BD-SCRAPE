# src/main_processor.py
import os
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
# import json # No longer needed for direct ProjectExtractionLog population
# import re # Likely no longer needed
from sqlalchemy.sql import func as sqlfunc_mp # Still needed for category lookups if those remain
# from pydantic import ValidationError # No longer needed here
import logging
import datetime # Added import
# import threading # For stop_event, though Callable is used in signature
# import datetime # No longer needed here directly, DB handles timestamps
import json

# Assuming src is in PYTHONPATH or running from root with python -m src.main_processor
try:
    # from src.database_models import get_db_engine, PrimarySector, ProjectSubCategory # For categorization if kept
    from src import database_crud
    from src import file_system_handler
    from src.parsers import pptx_parser, pdf_parser, docx_parser, excel_parser
    from src import llm_handler
    # LLM Pydantic models (ProjectIdentificationOutput, MainExtractionOutput, etc.) are no longer directly used for logging by main_processor
except ImportError:
    # Fallback for direct execution (python src/main_processor.py)
    # from database_models import get_db_engine, PrimarySector, ProjectSubCategory # For categorization if kept
    import database_crud
    import file_system_handler
    from parsers import pptx_parser, pdf_parser, docx_parser, excel_parser
    import llm_handler

DEFAULT_PROJECTS_ROOT_FOLDER = "D:/bd_scrape/sample_documents"
DEFAULT_LLM_MODEL = "gemma2:9b" # Ensure this is a model good at simple JSON name extraction

logger = logging.getLogger(__name__)
DEFAULT_UPLOAD_DIR_NAME = "upload_folder"

# _strip_llm_json_markdown has been moved to llm_handler.py
# create_text_chunks is no longer needed for the simplified verbatim logging approach.
# find_primary_sector, find_project_sub_category are for categorization, may be kept if categorization feature remains separate.

# --- Helper Function for Parsing ---
def parse_document(file_path: Path, file_type: str) -> Optional[Dict[str, Any]]:
    # This function remains largely the same.
    parsed_content = None
    logger.info(f"Parsing document: {file_path} (Type: {file_type})")
    try:
        if file_type == ".pptx":
            parsed_content = pptx_parser.parse_pptx(str(file_path))
        elif file_type == ".pdf":
            parsed_content = pdf_parser.parse_pdf(str(file_path))
        elif file_type == ".docx":
            parsed_content = docx_parser.parse_docx(str(file_path))
        elif file_type in [".xlsx", ".xls"]:
            parsed_content = excel_parser.parse_excel(str(file_path))
        else:
            logger.warning(f"Unsupported file type: {file_type} for {file_path}")
            return None
        
        if parsed_content and "error" in parsed_content:
            logger.error(f"Error parsing {file_path}: {parsed_content['error']}")
            return None
        logger.info(f"Successfully parsed: {file_path}")
        return parsed_content
    except Exception as e:
        logger.error(f"Exception during parsing {file_path}: {e}", exc_info=True)
        return {"error": str(e), "file_path": str(file_path)}

def _get_full_text_from_parsed_data(parsed_data: Dict[str, Any], file_type: str) -> str:
    full_text = ""
    if file_type == ".pptx":
        slides_text_list = parsed_data.get("text_from_slides", [])
        for slide_info in slides_text_list:
            full_text += slide_info.get("text", "") + "\n\nSlide Break\n\n" # Add breaks for readability
        notes_text_list = parsed_data.get("speaker_notes", [])
        if notes_text_list:
            full_text += "--- SPEAKER NOTES ---\n"
            for note_info in notes_text_list:
                full_text += note_info.get("notes", "") + "\n\nNote Break\n\n"
    elif file_type == ".pdf":
        pages_text_list = parsed_data.get("text_from_pages", [])
        for page_info in pages_text_list:
            full_text += page_info.get("text", "") + "\n\nPage Break\n\n"
    elif file_type == ".docx":
        full_text = parsed_data.get("document_text", "")
    elif file_type in [".xlsx", ".xls"]:
        full_text = parsed_data.get("full_text", "") # Combined text from all sheets
    return full_text.strip()


# --- Simplified Single File Processor ---
def _execute_processing_for_single_file(
    db_session: database_crud.Session,
    selected_llm_model: str, # For project name identification
    specific_file_name: str,
    upload_dir: str,
    stop_callback: Optional[Callable[[], bool]] = None
):
    full_file_path = Path(upload_dir) / specific_file_name
    file_type = full_file_path.suffix.lower()
    
    logger.info(f"Simplified processing for: {full_file_path}, Type: {file_type}")

    if stop_callback and stop_callback():
        logger.warning(f"Stop requested before processing file: {specific_file_name}")
        return

    parsed_data = parse_document(full_file_path, file_type)
    doc_db_id_for_audit = None # For audit logging even if full doc processing fails later
    source_doc_name_for_audit = specific_file_name # For audit logging

    if not parsed_data or "error" in parsed_data:
        err_msg = parsed_data.get('error', 'Unknown parsing error') if parsed_data else 'Parser returned None'
        logger.error(f"Parsing failed for {specific_file_name}. Error: {err_msg}")
        database_crud.add_document_processing_audit_log(
            session=db_session, source_document_name=source_doc_name_for_audit,
            processing_stage="parsing", llm_action="error", notes=f"Parsing failed: {err_msg}"
        )
        return
    
    # Create Document record early to get an ID for audit logs, status as "Processing"
    # This document record will be updated later with a more specific status.
    temp_doc_defaults = {
        "document_title_extracted": parsed_data.get("metadata", {}).get("title"),
        "author_extracted": parsed_data.get("metadata", {}).get("author"),
        "number_of_pages_slides": parsed_data.get("metadata", {}).get("num_pages") or parsed_data.get("metadata", {}).get("num_slides"),
        "extraction_status": "Processing - Initializing"
    }
    # Try to link to a temporary/placeholder project if needed, or handle project_id as nullable in Document for this stage
    # For now, we will create the document without a project_id, and link it upon first successful project verification.
    # If no project is ever linked, it remains unlinked or linked to a generic "unprocessed" project if desired.
    # Let's assume `add_document_to_project` can handle a temporary placeholder project_id or make it nullable initially.
    # For simplicity, let's ensure project_id is not required for initial Document creation, or create a placeholder Document entry logic.

    # Create a Document record early, even if no project is immediately obvious.
    # The project_id in the Document table might be updated later when the first valid project is identified.
    # If add_document_to_project requires project_id, we might need a placeholder or defer this slightly.
    # Assuming project_id in Document can be nullable initially, or we create it once a project_id is known.
    # For now, we proceed and ensure doc_record is created within the loop if first mention is successful.

    full_text_for_extraction = _get_full_text_from_parsed_data(parsed_data, file_type)
    metadata = parsed_data.get("metadata", {})

    if not full_text_for_extraction:
        logger.warning(f"No text content extracted from {specific_file_name}. Skipping further processing.")
        database_crud.add_document_processing_audit_log(
            session=db_session, source_document_name=source_doc_name_for_audit,
            processing_stage="text_extraction", llm_action="error", notes="No text content extracted"
        )
        # Update actual Document record if it was created, to reflect this status
        # This part needs careful handling of when Document record is made if text extraction fails.
        # Let's assume for now we log an audit and return. If Document table requires a project_id this is fine.
        return

    logger.info(f"Successfully parsed {specific_file_name}. Extracted text length: {len(full_text_for_extraction)} characters.")

    # Phase 0: Comprehensive verbatim data extraction for the entire document
    logger.info(f"Starting comprehensive verbatim data extraction for {specific_file_name}")
    comprehensive_data = llm_handler.extract_all_document_data_verbatim(
        selected_llm_model, 
        full_text_for_extraction, 
        specific_file_name
    )
    
    if comprehensive_data:
        total_items = sum(len(items) if isinstance(items, list) else 1 for items in comprehensive_data.values())
        logger.info(f"Comprehensive extraction completed for {specific_file_name}. Total data items: {total_items}")
        
        # Store the comprehensive extraction results for potential future use
        # This could be stored in a separate table or as JSON in the document record
        database_crud.add_document_processing_audit_log(
            session=db_session, 
            source_document_name=source_doc_name_for_audit,
            processing_stage="comprehensive_extraction", 
            llm_action="verbatim_extraction_completed", 
            notes=f"Extracted {total_items} data items across all categories"
        )
    else:
        logger.warning(f"Comprehensive data extraction failed for {specific_file_name}")
        database_crud.add_document_processing_audit_log(
            session=db_session, 
            source_document_name=source_doc_name_for_audit,
            processing_stage="comprehensive_extraction", 
            llm_action="extraction_failed", 
            notes="Comprehensive verbatim extraction returned no results"
        )

    # Phase 1: Initial scan for potential project name mentions
    raw_project_mentions = llm_handler.get_project_names_from_text(selected_llm_model, full_text_for_extraction)

    if not raw_project_mentions:
        logger.warning(f"Initial LLM scan found no project name mentions in {specific_file_name}. Document will be processed for audit trail but no project records will be created unless verified mentions are found.")
        # Instead of immediately falling back to filename, we'll process the document without specific project mentions
        # This allows for better audit trails and avoids creating projects from filenames
        database_crud.add_document_processing_audit_log(
            session=db_session, source_document_name=source_doc_name_for_audit,
            processing_stage="initial_name_spotting", llm_action="no_mentions_found", 
            notes="LLM found no specific project name mentions in document content."
        )
        # Skip processing since no valid project mentions were found
        logger.info(f"Skipping detailed processing for '{specific_file_name}' as no project mentions were identified.")
        return
    else:
        logger.info(f"Initial LLM scan for {specific_file_name} identified potential mentions: {raw_project_mentions}")
        # Log all raw mentions spotted before verification
        for r_mention in raw_project_mentions:
            database_crud.add_document_processing_audit_log(
                session=db_session, source_document_name=source_doc_name_for_audit,
                processing_stage="initial_name_spotting", raw_mention=r_mention, llm_action="mention_spotted"
            )

    doc_record = None 
    processed_project_ids_for_this_doc = set()
    any_project_linked_for_this_doc = False

    for raw_mention in raw_project_mentions:
        if stop_callback and stop_callback(): # Check for stop request
            logger.warning(f"Stop requested during project mention processing for file: {specific_file_name}")
            break
        
        logger.info(f"Processing mention '{raw_mention}' from document '{specific_file_name}'...")

        verification_result = llm_handler.enrich_and_verify_project_context(
            selected_llm_model, 
            full_text_for_extraction, 
            raw_mention, 
            db_session
        )

        audit_details_for_mention = {
            "source_document_name": source_doc_name_for_audit,
            "processing_stage": "mention_verification",
            "raw_mention": raw_mention,
        }
        if doc_record: # If doc_record was already created (e.g. by a previous successful mention)
            audit_details_for_mention["document_id"] = doc_record.document_id

        if not verification_result:
            logger.warning(f"LLM verification/enrichment failed for mention '{raw_mention}'. Skipping this mention.")
            audit_details_for_mention.update({"llm_action": "verification_error", "notes": "LLM call failed or returned no result."})
            database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention)
            continue

        # Log verification attempt to audit log
        audit_details_for_mention.update({
            "llm_action": verification_result.action,
            "llm_confirmed_project_name": verification_result.confirmed_project_name,
            "llm_project_id_linked": verification_result.project_id if verification_result.action == "link_to_existing" else None,
            "llm_suggested_tags": verification_result.suggested_tags,
            "llm_confidence": verification_result.confidence_score,
            "llm_reasoning": verification_result.reasoning
        })
        # We'll add the audit log entry after attempting to get/create project, to include final linked project ID if 'create_new'

        project_to_log_against = None
        final_project_name_for_log = None

        if verification_result.action == "link_to_existing" and verification_result.project_id is not None:
            project_to_log_against = database_crud.get_project_by_id(db_session, verification_result.project_id)
            if project_to_log_against:
                final_project_name_for_log = project_to_log_against.project_name
                logger.info(f"Mention '{raw_mention}' linked to existing Project ID: {project_to_log_against.project_id}, Name: '{final_project_name_for_log}'")
                audit_details_for_mention["llm_project_id_linked"] = project_to_log_against.project_id # Confirm linked ID for audit
            else:
                logger.error(f"LLM suggested linking '{raw_mention}' to non-existent Project ID: {verification_result.project_id}. Attempting use confirmed name: {verification_result.confirmed_project_name}")
                audit_details_for_mention["notes"] = f"LLM linked to non-existent ID {verification_result.project_id}."
                if verification_result.confirmed_project_name:
                    final_project_name_for_log = verification_result.confirmed_project_name.strip()
                    project_to_log_against = database_crud.get_or_create_project(
                        session=db_session, project_name=final_project_name_for_log,
                        defaults={"project_status": "From Verified Document Ingestion"})
                    if project_to_log_against:
                        audit_details_for_mention["llm_project_id_linked"] = project_to_log_against.project_id
                        audit_details_for_mention["llm_action"] = "create_new_after_failed_link" # Override action for audit clarity
                    logger.info(f"Used confirmed name '{final_project_name_for_log}' to get/create project.")
                else:
                    logger.warning(f"Cannot link or create project for mention '{raw_mention}'. No valid ID or fallback name.")
                    database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention)
                    continue
        
        elif verification_result.action == "create_new" and verification_result.confirmed_project_name:
            final_project_name_for_log = verification_result.confirmed_project_name.strip()
            project_to_log_against = database_crud.get_or_create_project(
                session=db_session, project_name=final_project_name_for_log,
                defaults={"project_status": "New - Verified from Document"})
            if project_to_log_against:
                logger.info(f"Mention '{raw_mention}' resulted in new/existing Project ID: {project_to_log_against.project_id}, Name: '{final_project_name_for_log}'")
                audit_details_for_mention["llm_project_id_linked"] = project_to_log_against.project_id # Add created project ID to audit
            else:
                logger.error(f"Failed to get/create project for '{final_project_name_for_log}' after 'create_new' action.")
                audit_details_for_mention["notes"] = f"Failed to get/create project for confirmed name {final_project_name_for_log}."
                database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention)
                continue
        
        elif verification_result.action in ["uncertain_relevance", "not_equinox_project"]:
            logger.info(f"Mention '{raw_mention}' determined as '{verification_result.action}'. Reasoning: {verification_result.reasoning}. No project record created/linked.")
            database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention)
            continue 
        
        else:
            logger.warning(f"Unknown action '{verification_result.action}' or missing data for mention '{raw_mention}'. Skipping.")
            audit_details_for_mention.update({"llm_action": "unknown_action_or_missing_data", "notes": f"Action: {verification_result.action}, Confirmed Name: {verification_result.confirmed_project_name}"})
            database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention)
            continue

        database_crud.add_document_processing_audit_log(session=db_session, **audit_details_for_mention) # Log the outcome of this mention

        if not project_to_log_against or not final_project_name_for_log:
            logger.error(f"Failed to establish a definitive project for mention '{raw_mention}' after verification. Skipping logging for this mention.")
            continue

        # Document record creation/update logic:
        # Create only once, link to first successful project. Update status if needed.
        current_doc_status = "Content Logged Verbatim with Tags"
        if doc_record is None:
            # Store full document text for better data extraction and future reference
            doc_defaults_with_content = {
                "extraction_status": current_doc_status, 
                "full_document_text": full_text_for_extraction,  # Store the complete document text
                "comprehensive_extraction_data": json.dumps(comprehensive_data, indent=2, ensure_ascii=False) if comprehensive_data else None,  # Store comprehensive data
                **temp_doc_defaults
            }
            doc_record = database_crud.add_document_to_project(
                session=db_session, project_id=project_to_log_against.project_id, 
                file_name=specific_file_name, file_path=str(full_file_path), doc_type=file_type,
                defaults=doc_defaults_with_content
            )
            if not doc_record:
                logger.error(f"CRITICAL: Failed to create document record for {specific_file_name} after successful project verification. Aborting file.")
                database_crud.add_document_processing_audit_log(session=db_session, source_document_name=source_doc_name_for_audit, processing_stage="document_creation", llm_action="error", notes="Failed to create Document DB record.")
                return 
            doc_db_id_for_audit = doc_record.document_id # Update for subsequent audit logs for this file.
            logger.info(f"Created document record with full text ({len(full_text_for_extraction)} chars) for {specific_file_name}")
        else: # Doc record exists, ensure its status reflects ongoing processing or completion
            if doc_record.extraction_status != current_doc_status:
                database_crud.update_document_extraction_status(db_session, doc_record.document_id, current_doc_status)
            # Update the full document text if it's not already stored
            if not doc_record.full_document_text or len(doc_record.full_document_text.strip()) == 0:
                database_crud.update_document_full_text(db_session, doc_record.document_id, full_text_for_extraction)
                logger.info(f"Updated document record with full text ({len(full_text_for_extraction)} chars) for {specific_file_name}")
            
            # Store comprehensive extraction data if available
            if comprehensive_data and not doc_record.comprehensive_extraction_data:
                database_crud.update_document_comprehensive_data(db_session, doc_record.document_id, comprehensive_data)
                logger.info(f"Stored comprehensive extraction data for {specific_file_name}")

        if project_to_log_against.project_id not in processed_project_ids_for_this_doc:
            # Get pertinent text from verification_result
            pertinent_text_for_log = verification_result.pertinent_text
            current_timestamp = datetime.datetime.now(datetime.timezone.utc)

            if pertinent_text_for_log:
                logger.info(f"Logging pertinent text from '{specific_file_name}' (mention: '{raw_mention}') to project '{final_project_name_for_log}' (ID: {project_to_log_against.project_id})")
                log_entry = database_crud.add_project_extraction_log(
                    session=db_session, 
                    project_id=project_to_log_against.project_id,
                    log_entry_title=f"Info from doc: {specific_file_name} (Mention: '{raw_mention}')", 
                    pertinent_content=pertinent_text_for_log, # Pass pertinent text
                    source_document_name=specific_file_name,
                    entry_timestamp=current_timestamp, # Pass current timestamp
                    llm_verification_action=verification_result.action,
                    llm_verification_confidence=verification_result.confidence_score,
                    llm_verification_reasoning=verification_result.reasoning
                )
                if log_entry:
                    any_project_linked_for_this_doc = True
                    logger.info(f"Successfully logged/appended pertinent content from '{specific_file_name}' for project '{final_project_name_for_log}'. Log ID: {log_entry.log_entry_id}")
                    processed_project_ids_for_this_doc.add(project_to_log_against.project_id)
                    if verification_result.suggested_tags:
                        logger.info(f"Adding tags for log entry {log_entry.log_entry_id}: {verification_result.suggested_tags}")
                        database_crud.add_project_extraction_log_tags(db_session, log_entry.log_entry_id, verification_result.suggested_tags)
                else:
                    logger.error(f"Failed to create/append project extraction log for project '{final_project_name_for_log}' with pertinent text.")
            else:
                logger.warning(f"No pertinent text provided by LLM for mention '{raw_mention}' in '{specific_file_name}'. Skipping ProjectExtractionLog entry for this mention.")
        else:
            logger.info(f"Pertinent text from '{specific_file_name}' (mention: '{raw_mention}') already processed for project ID {project_to_log_against.project_id} in this document run. Skipping duplicate ProjectExtractionLog entry.")

    # After loop, finalize Document status if it was created
    if doc_record:
        final_doc_status = "Processed - Linked with Tags" if any_project_linked_for_this_doc else "Processed - No Project Links Established"
        if doc_record.extraction_status != final_doc_status:
            database_crud.update_document_extraction_status(db_session, doc_record.document_id, final_doc_status)
    elif not any_project_linked_for_this_doc: # No doc_record created and no links made
        logger.warning(f"No valid project contexts established for '{specific_file_name}'. No document record or logs created beyond audit.")
        # An audit log for parsing failure or text extraction failure would have already been made.
        # If it passed those but all mentions were invalid, the audit trail for mentions will show this.


# Public wrapper (remains similar, calls the simplified internal processor)
def process_documents(
    selected_llm_model: str, 
    filename: str, 
    stop_callback: Optional[Callable[[], bool]] = None, 
    upload_dir: Optional[str] = None
):
    logger.info(f"Simplified verbatim document processing for: {filename} with model {selected_llm_model}")
    actual_upload_dir = upload_dir or DEFAULT_UPLOAD_DIR_NAME
    db = None
    try:
        db = database_crud.get_session()
        _execute_processing_for_single_file(
            db_session=db,
            selected_llm_model=selected_llm_model,
            specific_file_name=filename,
            upload_dir=actual_upload_dir,
            stop_callback=stop_callback
        )
        logger.info(f"Verbatim document processing completed for: {filename}")
    except Exception as e:
        logger.error(f"Unhandled error in simplified process_documents for {filename}: {e}", exc_info=True)
    finally:
        if db:
            db.close()
            logger.debug(f"DB session closed for process_documents of {filename}")


# --- Main Processing Workflow (processes a whole folder) ---
def process_documents_workflow(root_folder_to_scan: str, 
                               selected_llm_model: str, 
                               db_session: database_crud.Session, 
                               force_reprocess_all: bool = False,
                               stop_callback: Optional[Callable[[], bool]] = None):
    logger.info(f"Starting SIMPLIFIED document processing workflow for folder: {root_folder_to_scan}")
    logger.info(f"Using LLM Model for project name ID: {selected_llm_model}")
    logger.info(f"Force reprocess all files: {force_reprocess_all}")

    discovered_files = file_system_handler.find_project_files(root_folder_to_scan, force_reprocess=force_reprocess_all)
    if not discovered_files:
        logger.warning("No documents found to process in the specified folder.")
        return

    logger.info(f"Found {len(discovered_files)} supported documents to potentially process.")
    total_files = len(discovered_files)

    for idx, file_info in enumerate(discovered_files):
        if stop_callback and stop_callback():
            logger.warning("Stop request detected. Halting document processing workflow.")
            return

        file_path_obj = Path(file_info["file_path"])
        # Use the simplified single file processor
        logger.info(f"\nCalling simplified processor for file {idx+1}/{total_files}: {file_path_obj.name}")
        _execute_processing_for_single_file(
            db_session=db_session,
            selected_llm_model=selected_llm_model,
            specific_file_name=file_path_obj.name,
            upload_dir=str(file_path_obj.parent), # Pass directory of the current file
            stop_callback=stop_callback
        )
        # Old complex logic that was here is now removed.
        
    logger.info("Simplified document processing workflow finished.")
    if stop_callback and stop_callback():
        logger.warning("Workflow finished due to earlier stop request.")

# (categorize_project_from_hints and its helpers find_primary_sector, find_project_sub_category
# are related to a separate categorization feature. They are not part of the verbatim logging.
# They can be kept if categorization based on LLM hints (from a different LLM call or manual input) 
# is still a desired separate feature. For now, they are left in but not called by the simplified flow.)

# --- Category Lookup Helper Functions (Potentially for a separate categorization feature) ---
def find_primary_sector(session: database_crud.Session, sector_hint: str) -> Optional[Any]: # Return type was PrimarySector
    from src.database_models import PrimarySector # Delayed import to avoid circular if model not fully loaded
    if not sector_hint or not sector_hint.strip(): return None
    normalized_hint = sector_hint.strip()
    sector = session.query(PrimarySector).filter(sqlfunc_mp.lower(PrimarySector.sector_name) == sqlfunc_mp.lower(normalized_hint)).first()
    if not sector: sector = session.query(PrimarySector).filter(PrimarySector.sector_name.ilike(f"%{normalized_hint}%")).first()
    return sector

def find_project_sub_category(session: database_crud.Session, sub_category_hint: str, primary_sector_id: Optional[int] = None) -> Optional[Any]: # ProjectSubCategory
    from src.database_models import ProjectSubCategory # Delayed import
    if not sub_category_hint or not sub_category_hint.strip(): return None
    normalized_hint = sub_category_hint.strip()
    query = session.query(ProjectSubCategory)
    if primary_sector_id: query = query.filter(ProjectSubCategory.sector_id == primary_sector_id)
    sub_cat = query.filter(sqlfunc_mp.lower(ProjectSubCategory.sub_category_name) == sqlfunc_mp.lower(normalized_hint)).first()
    if not sub_cat:
        query = session.query(ProjectSubCategory)
        if primary_sector_id: query = query.filter(ProjectSubCategory.sector_id == primary_sector_id)
        sub_cat = query.filter(ProjectSubCategory.sub_category_name.ilike(f"%{normalized_hint}%")).first()
    return sub_cat

def categorize_project_from_hints(session: database_crud.Session, 
                                 project: Any, # Was database_crud.Project
                                 primary_hint: Optional[str], 
                                 sub_hint: Optional[str], 
                                 type_hint: Optional[str]):
    # This function is for a SEPARATE categorization step, not verbatim logging.
    # Its dependencies (PrimarySector, ProjectSubCategory) are now imported locally within the functions.
    if not primary_hint and not sub_hint and not type_hint: return
    # ... (rest of the logic remains, but it's not part of the core verbatim logging flow)
    logger.info(f"(Separate Step) Attempting to categorize project ID {project.project_id}...")
    # The actual assignment logic using database_crud.assign_project_to_category would follow here.

if __name__ == '__main__':
    if not logging.getLogger().handlers:
         logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

    logger.info("Starting main_processor.py SIMPLIFIED test run...")
    engine = database_crud.get_db_engine()
    SessionLocal = database_crud.sessionmaker(autocommit=False, autoflush=False, bind=engine)
    # SessionLocal.configure(bind=engine) # Already done by sessionmaker arg
    db = SessionLocal()

    try:
        logger.info("Ensuring categories are seeded (for potential separate categorization step)...")
        from seed_database import seed_initial_data
        seed_initial_data(db)
        logger.info("Category data seeded.")

        test_root_folder = DEFAULT_PROJECTS_ROOT_FOLDER 
        test_llm_model = DEFAULT_LLM_MODEL
        
        if not os.path.isdir(test_root_folder):
            logger.error(f"ERROR: Test folder '{test_root_folder}' does not exist. Please create it and add test documents.")
        else:
            logger.info(f"Test folder: {test_root_folder}")
            logger.info(f"Test LLM model for project name ID: {test_llm_model}")
            
            # Test the simplified folder processing workflow
            process_documents_workflow(
                root_folder_to_scan=test_root_folder,
                selected_llm_model=test_llm_model, 
                db_session=db, 
                force_reprocess_all=True, 
                stop_callback=lambda: False
            )
            
            # Example of testing single file processing (ensure a file exists in DEFAULT_UPLOAD_DIR_NAME or adjust)
            # sample_file_for_single_test = "your_test_document.pdf" # Change this
            # upload_folder_for_single_test = DEFAULT_UPLOAD_DIR_NAME
            # if Path(upload_folder_for_single_test, sample_file_for_single_test).exists():
            #    logger.info(f"\nTesting single file simplified processing for: {sample_file_for_single_test}")
            #    process_documents(
            #        selected_llm_model=test_llm_model,
            #        filename=sample_file_for_single_test,
            #        upload_dir=upload_folder_for_single_test
            #    )
            # else:
            #    logger.warning(f"Skipping single file test, {sample_file_for_single_test} not found in {upload_folder_for_single_test}")

    except Exception as e:
        logger.error(f"An error occurred during the SIMPLIFIED test workflow: {e}", exc_info=True)
    finally:
        db.close()
        logger.info("Simplified test run finished. Database session closed.") 