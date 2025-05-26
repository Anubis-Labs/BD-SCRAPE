print("--- LOADING LATEST DATABASE_CRUD.PY ---")
# src/database_crud.py
from sqlalchemy.orm import sessionmaker, Session, joinedload
from sqlalchemy.exc import IntegrityError, OperationalError
from typing import List, Optional, Dict, Any, Union
import datetime
from sqlalchemy import String
from sqlalchemy.orm import aliased
from sqlalchemy.sql import func as sqlfunc # Renamed to avoid conflict with re.func if it was ever used
import logging
import json

try:
    from .database_models import ( # Relative import for module use
        Base, Project, Client, ProjectClient, Document, Location, 
        ProjectKeyInformation, Technology, ProjectTechnology, 
        ProjectPersonnelRole, Partner, ProjectPartner, ProjectFinancial,
        ProjectPhaseMilestone, ProjectRiskOrChallenge, ProjectPhaseService,
        PrimarySector, ProjectSubCategory, ProjectCategoryAssignment,
        ProjectExtractionLog, ProjectExtractionLogTag, DocumentProcessingAuditLog,
        get_db_engine
    )
except ImportError:
    from database_models import ( # Direct import for standalone script or testing
        Base, Project, Client, ProjectClient, Document, Location, 
        ProjectKeyInformation, Technology, ProjectTechnology, 
        ProjectPersonnelRole, Partner, ProjectPartner, ProjectFinancial,
        ProjectPhaseMilestone, ProjectRiskOrChallenge, ProjectPhaseService,
        PrimarySector, ProjectSubCategory, ProjectCategoryAssignment,
        ProjectExtractionLog, ProjectExtractionLogTag, DocumentProcessingAuditLog,
        get_db_engine
    )

logger = logging.getLogger(__name__) # Ensure logger is defined for the module

# --- Session Management ---
# In a real application, session management might be more sophisticated (e.g., context managers, FastAPI dependencies)

def get_session(db_url: str = "postgresql://db_user:db_password@localhost:5432/project_db") -> Session:
    """Creates and returns a new SQLAlchemy session."""
    engine = get_db_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

# --- Project CRUD ---

def get_or_create_project(session: Session, project_name: str, equinox_project_number: Optional[str] = None, defaults: Optional[Dict[str, Any]] = None) -> Project:
    """
    Retrieves an existing project by equinox_project_number (if provided and unique) or by name,
    or creates a new one if not found.
    Uses equinox_project_number as the primary lookup if available.
    Project name and number are normalized for lookup.
    """
    if defaults is None:
        defaults = {}
    
    normalized_project_name = project_name.strip().lower() if project_name else None
    normalized_project_number = equinox_project_number.strip().upper() if equinox_project_number else None
    # Consider more aggressive normalization for project_number if needed, e.g., removing hyphens/spaces.
    # For now, stripping and uppercasing is a start.

    project = None
    if normalized_project_number:
        project = session.query(Project).filter(Project.equinox_project_number == normalized_project_number).first()
    
    if not project and normalized_project_name: # If not found by number, or if number was not provided, try by name
        project = session.query(Project).filter(sqlfunc.lower(Project.project_name) == normalized_project_name).first()

    if not project:
        if not normalized_project_name:
            # This case should ideally be prevented by upstream logic ensuring a name or filename fallback
            logger.error("Attempted to create a project with no name.")
            raise ValueError("Project name cannot be empty for creation.")

        logger.info(f"Creating new project: '{normalized_project_name}', Number: '{normalized_project_number or 'N/A'}'")
        # Use the original (or minimally processed) project_name for creation if desired,
        # but ensure normalized_project_name is what was checked for existence.
        # For consistency in storage vs lookup, storing normalized might be better if originals vary too much.
        # Sticking to original project_name for now for the actual field, normalized for lookup.
        project_data = {"project_name": project_name.strip(), "equinox_project_number": normalized_project_number, **defaults}
        
        valid_keys = {col.name for col in Project.__table__.columns}
        filtered_project_data = {k: v for k, v in project_data.items() if k in valid_keys}
        
        project = Project(**filtered_project_data)
        try:
            session.add(project)
            session.commit()
            session.refresh(project) 
        except IntegrityError as e:
            session.rollback()
            logger.error(f"IntegrityError during project creation for name '{normalized_project_name}', num '{normalized_project_number}': {e}. Attempting to retrieve again.")
            # Attempt to retrieve again in case of a race condition where another process created it.
            if normalized_project_number:
                project = session.query(Project).filter(Project.equinox_project_number == normalized_project_number).first()
            if not project and normalized_project_name:
                 project = session.query(Project).filter(sqlfunc.lower(Project.project_name) == normalized_project_name).first()
            if not project: 
                logger.error(f"Still could not find project after IntegrityError. Re-raising original error.")
                raise e 
        except Exception as e:
            session.rollback()
            raise e
    else: # Project was found
        logger.info(f"Found existing project: ID {project.project_id}, Name: '{project.project_name}', Number: '{project.equinox_project_number}'")
        # If project exists, update it with any new default values provided
        if defaults:
            updated = False
            for key, value in defaults.items():
                if hasattr(project, key) and getattr(project, key) != value:
                    # Special handling for project_name and equinox_project_number if they are in defaults
                    # and the found project's fields are different from the *normalized* versions of incoming identifiers
                    # This can happen if an old record has "Project Alpha" and new call is for "project alpha"
                    # We generally want to keep the existing canonical name/number unless explicitly changing.
                    # The defaults are usually for other fields like 'project_status'.
                    if key == "project_name" and value.strip().lower() != project.project_name.strip().lower():
                        logger.warning(f"Skipping update of project_name via defaults to \'{value}\' as it differs from existing \'{project.project_name}\' post-normalization.")
                        continue
                    if key == "equinox_project_number" and value.strip().upper() != (project.equinox_project_number or "").strip().upper():
                        logger.warning(f"Skipping update of equinox_project_number via defaults to \'{value}\' as it differs from existing \'{project.equinox_project_number}\' post-normalization.")
                        continue
                    
                    setattr(project, key, value)
                    updated = True
            if updated:
                try:
                    logger.info(f"Updating existing project ID {project.project_id} with new default values.")
                    session.commit()
                    session.refresh(project)
                except Exception as e:
                    session.rollback()
                    raise e
    return project

def get_project_by_id(session: Session, project_id: int) -> Optional[Project]:
    """Retrieves a project by its primary key ID."""
    return session.query(Project).filter(Project.project_id == project_id).first()

def update_project_narrative(session: Session, project_id: int, narrative_update: str) -> Optional[Project]:
    project = session.query(Project).filter(Project.project_id == project_id).first()
    if project:
        new_narrative = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ": " + narrative_update
        if project.project_narrative_log:
            project.project_narrative_log += "\n" + new_narrative
        else:
            project.project_narrative_log = new_narrative
        try:
            session.commit()
            session.refresh(project)
            return project
        except Exception as e:
            session.rollback()
            print(f"Error updating project narrative: {e}")
            return None
    return None

# --- Document CRUD ---
def add_document_to_project(session: Session, project_id: int, file_name: str, file_path: str, doc_type: str, defaults: Optional[Dict[str, Any]] = None) -> Document:
    if defaults is None:
        defaults = {}
    
    # Check if document already exists by file_path (which should be unique)
    doc = session.query(Document).filter(Document.file_path == file_path).first()
    if doc:
        # If it exists, update its project_id if it's different or not set, and other fields
        updated = False
        if doc.project_id != project_id:
            doc.project_id = project_id
            updated = True
        for key, value in defaults.items():
            if hasattr(doc, key) and getattr(doc,key) != value:
                setattr(doc,key,value)
                updated = True
        if updated:
            session.commit()
            session.refresh(doc)
        return doc

    doc_data = {
        "project_id": project_id,
        "file_name": file_name,
        "file_path": file_path,
        "document_type": doc_type,
        "extraction_status": "Pending", # Default status
        "last_processed_at": None,
        **defaults
    }
    valid_keys = {col.name for col in Document.__table__.columns}
    filtered_doc_data = {k: v for k, v in doc_data.items() if k in valid_keys}

    doc = Document(**filtered_doc_data)
    try:
        session.add(doc)
        session.commit()
        session.refresh(doc)
    except IntegrityError as e: # Should mainly happen if file_path constraint is violated concurrently
        session.rollback()
        print(f"IntegrityError adding document: {e}. Attempting to retrieve.")
        doc = session.query(Document).filter(Document.file_path == file_path).first()
        if not doc: raise e # Should not happen
    except Exception as e:
        session.rollback()
        raise e
    return doc


def update_document_extraction_status(session: Session, document_id: int, status: str, extracted_info: Optional[Dict[str, Any]] = None) -> Optional[Document]:
    doc = session.query(Document).filter(Document.document_id == document_id).first()
    if doc:
        doc.extraction_status = status
        doc.last_processed_at = datetime.datetime.now(datetime.timezone.utc)
        if extracted_info: # Update fields based on parser output
            doc.document_title_extracted = extracted_info.get('metadata',{}).get('title')
            doc.author_extracted = extracted_info.get('metadata',{}).get('author')
            # ... add more fields as needed from extracted_info
            if 'num_pages' in extracted_info: # PDF
                doc.number_of_pages_slides = extracted_info['num_pages']
            elif 'text_from_slides' in extracted_info: # PPTX
                doc.number_of_pages_slides = len(extracted_info['text_from_slides'])
        try:
            session.commit()
            session.refresh(doc)
            return doc
        except Exception as e:
            session.rollback()
            logger.error(f"Error updating document {document_id} extraction status: {e}", exc_info=True)
            return None
    return None

def update_document_full_text(session: Session, document_id: int, full_text: str) -> Optional[Document]:
    """Updates the full document text for a given document ID."""
    try:
        document = session.query(Document).filter(Document.document_id == document_id).first()
        if not document:
            logger.warning(f"Document with ID {document_id} not found for full text update.")
            return None
        
        document.full_document_text = full_text
        session.commit()
        session.refresh(document)
        logger.info(f"Updated full document text for document ID {document_id} ({len(full_text)} characters)")
        return document
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating document {document_id} full text: {e}", exc_info=True)
        return None

def update_document_comprehensive_data(session: Session, document_id: int, comprehensive_data: Dict[str, Any]) -> Optional[Document]:
    """Updates the comprehensive extraction data for a given document ID."""
    try:
        document = session.query(Document).filter(Document.document_id == document_id).first()
        if not document:
            logger.warning(f"Document with ID {document_id} not found for comprehensive data update.")
            return None
        
        # Convert the comprehensive data to JSON string
        comprehensive_json = json.dumps(comprehensive_data, indent=2, ensure_ascii=False)
        document.comprehensive_extraction_data = comprehensive_json
        session.commit()
        session.refresh(document)
        
        total_items = sum(len(items) if isinstance(items, list) else 1 for items in comprehensive_data.values())
        logger.info(f"Updated comprehensive extraction data for document ID {document_id} ({total_items} items)")
        return document
    except Exception as e:
        session.rollback()
        logger.error(f"Error updating document {document_id} comprehensive data: {e}", exc_info=True)
# --- Client CRUD ---
def get_or_create_client(session: Session, client_name: str, defaults: Optional[Dict[str, Any]] = None) -> Client:
    if defaults is None: defaults = {}
    client = session.query(Client).filter(Client.client_name == client_name).first()
    if not client:
        client_data = {"client_name": client_name, **defaults}
        valid_keys = {col.name for col in Client.__table__.columns}
        filtered_data = {k:v for k,v in client_data.items() if k in valid_keys}
        client = Client(**filtered_data)
        try:
            session.add(client)
            session.commit()
            session.refresh(client)
        except IntegrityError: # Handles race condition if client_name is unique
            session.rollback()
            client = session.query(Client).filter(Client.client_name == client_name).first()
            if not client: raise # Should be found now
        except Exception as e:
            session.rollback()
            raise e
    else: # Update if exists and defaults provided
        updated = False
        for key, value in defaults.items():
            if hasattr(client, key) and getattr(client,key) != value:
                setattr(client,key,value)
                updated = True
        if updated: session.commit(); session.refresh(client)
    return client

def link_project_client(session: Session, project_id: int, client_id: int, role: str = "Primary") -> Optional[ProjectClient]:
    link = session.query(ProjectClient).filter_by(project_id=project_id, client_id=client_id, role=role).first()
    if not link:
        link = ProjectClient(project_id=project_id, client_id=client_id, role=role)
        try:
            session.add(link)
            session.commit()
            session.refresh(link)
        except IntegrityError: # Primary key violation
            session.rollback()
            link = session.query(ProjectClient).filter_by(project_id=project_id, client_id=client_id, role=role).first()
            if not link: raise
        except Exception as e:
            session.rollback()
            raise e
    return link

# --- Category CRUD (mostly for admin/seeding, less for core app logic) ---

def add_primary_sector(session: Session, name: str, description: Optional[str] = None) -> PrimarySector:
    sector = PrimarySector(sector_name=name, sector_description=description)
    session.add(sector)
    session.commit()
    session.refresh(sector)
    return sector

def add_project_sub_category(session: Session, name: str, code: Optional[str] = None, 
                             sector_id: Optional[int] = None, 
                             parent_sub_category_id: Optional[int] = None, 
                             description: Optional[str] = None) -> ProjectSubCategory:
    sub_category = ProjectSubCategory(
        sub_category_name=name, 
        sub_category_code=code,
        sector_id=sector_id,
        parent_sub_category_id=parent_sub_category_id,
        sub_category_description=description
    )
    session.add(sub_category)
    session.commit()
    session.refresh(sub_category)
    return sub_category

def get_project_sub_category_by_name(session: Session, name: str) -> Optional[ProjectSubCategory]:
    return session.query(ProjectSubCategory).filter(ProjectSubCategory.sub_category_name == name).first()

def assign_project_to_category(session: Session, project_id: int, 
                               primary_sector_id: Optional[int] = None, 
                               sub_category_id: Optional[int] = None, 
                               notes: Optional[str] = None) -> Optional[ProjectCategoryAssignment]:
    """
    Assigns a project to a primary sector and/or a sub-category.
    If only primary_sector_id is provided, it implies a general assignment to that sector.
    If sub_category_id is provided, it implies assignment to that sub-category (which in turn belongs to a primary sector).
    This function will clear existing assignments for the project before adding new ones to ensure 
    a project is not assigned to multiple sub-categories or primary sectors directly via this simple assignment.
    For more complex multi-categorization, this logic would need adjustment.
    """
    # Clear existing assignments for this project to enforce single category assignment via this function
    session.query(ProjectCategoryAssignment).filter_by(project_id=project_id).delete()
    # session.commit() # Commit deletion before adding new, or handle as one transaction

    assignment = None
    if sub_category_id: # Preferred assignment is via sub-category
        # Verify sub_category exists
        sub_cat = session.query(ProjectSubCategory).filter_by(sub_category_id=sub_category_id).first()
        if not sub_cat:
            print(f"Error: Sub-category with ID {sub_category_id} not found.")
            return None
        
        assignment = ProjectCategoryAssignment(
            project_id=project_id,
            sub_category_id=sub_category_id,
            assignment_notes=notes
        )
    elif primary_sector_id: # Fallback to primary sector if no sub-category
        # This case is less common if sub-categories are well-defined under each primary sector.
        # It implies the project is generally associated with a primary sector but not a specific sub-category.
        # We need to ensure ProjectCategoryAssignment can handle a null sub_category_id if we go this route,
        # or create a dummy/general sub-category under the primary sector.
        # For now, this schema (ProjectCategoryAssignment links project_id to sub_category_id) 
        # means we MUST have a sub_category_id. 
        # So, this function should primarily be called with sub_category_id.
        # If you want to assign only to primary sector, you might need a different table or a general sub-category.
        # Let's assume for now `assign_project_to_category` always gets a valid sub_category_id if an assignment is made.
        print(f"""Warning: assign_project_to_category was called with only primary_sector_id. 
              The current schema requires a sub_category_id for ProjectCategoryAssignment. No assignment made.""")
        # To make this work, you'd find/create a general sub-category under primary_sector_id and use its ID.
        return None # Or handle appropriately
    else:
        print("No category (primary or sub) provided for assignment.")
        return None # No assignment to make

    if assignment:
        try:
            session.add(assignment)
            session.commit()
            session.refresh(assignment)
            return assignment
        except IntegrityError as e:
            session.rollback()
            print(f"Error assigning project to category: {e}")
            # Potentially, the combination already exists if not for the delete logic, or other DB constraint
            return None
        except Exception as e:
            session.rollback()
            print(f"Unexpected error assigning project to category: {e}")
            raise
    return None

def is_project_categorized(session: Session, project_id: int) -> bool:
    """Checks if a project has any category assignments."""
    return session.query(ProjectCategoryAssignment).filter_by(project_id=project_id).count() > 0

# --- Key Information --- 
def add_project_key_info(session: Session, project_id: int, info_category: str, info_item: str, 
                         doc_id: Optional[int] = None, 
                         info_details: Optional[str] = None, 
                         page_ref: Optional[str] = None, 
                         confidence: Optional[float] = None) -> ProjectKeyInformation:
    # Check if similar info already exists to avoid simple duplicates for same category/item under project
    # This check might need to be more sophisticated based on requirements
    existing_info = session.query(ProjectKeyInformation).filter_by(
        project_id=project_id, 
        info_category=info_category, 
        info_item=info_item,
        document_id=doc_id # Optionally scope by document
    ).first()

    if existing_info:
        # Decide on update strategy: e.g., update details, confidence, or skip
        # For now, let's assume we update if new details are provided, or if confidence is higher.
        updated = False
        if info_details and existing_info.info_details_qualifier != info_details:
            existing_info.info_details_qualifier = info_details
            updated = True
        if confidence and (existing_info.confidence_score_llm is None or confidence > existing_info.confidence_score_llm):
            existing_info.confidence_score_llm = confidence
            updated = True
        if page_ref and existing_info.source_page_reference != page_ref:
            existing_info.source_page_reference = page_ref
            updated = True
        if updated:
            session.commit()
            session.refresh(existing_info)
        return existing_info

    key_info = ProjectKeyInformation(
        project_id=project_id,
        document_id=doc_id,
        info_category=info_category,
        info_item=info_item,
        info_details_qualifier=info_details,
        source_page_reference=page_ref,
        confidence_score_llm=confidence
    )
    session.add(key_info)
    session.commit()
    session.refresh(key_info)
    return key_info

# --- Query Functions for GUI / Reporting ---

def get_projects_with_client_info(session: Session) -> List[Dict[str, Any]]:
    # """
    # Retrieves a list of projects along with their primary client's name.
    # If a project has multiple clients, only the one marked 'Primary' or the first one found is listed.
    # This function might be superseded or augmented by get_projects_for_display
    # """
    # logger.info("Fetching projects with client information...")
    # # Alias for ProjectClient if joining multiple times or for clarity
    # pc_alias = aliased(ProjectClient)

    # results = (
    #     session.query(
    #         Project.project_id,
    #         Project.project_name,
    #         Project.equinox_project_number,
    #         Project.project_status,
    #         Client.client_name
    #     )
    #     .outerjoin(pc_alias, Project.project_id == pc_alias.project_id)
    #     .outerjoin(Client, pc_alias.client_id == Client.client_id)
    #     # .filter(pc_alias.role == "Primary") # Add this if you want to strictly filter by primary client role
    #     .group_by(
    #         Project.project_id,
    #         Project.project_name,
    #         Project.equinox_project_number,
    #         Project.project_status,
    #         Client.client_name
    #     ) # Group by to get distinct projects if multiple links exist but we only show one client
    #     .order_by(Project.project_name)
    #     .all()
    # )
    # projects_list = [{
    #     "project_id": r.project_id,
    #     "project_name": r.project_name,
    #     "equinox_project_number": r.equinox_project_number,
    #     "project_status": r.project_status,
    #     "client_name": r.client_name if r.client_name else "N/A"
    # } for r in results]
    # logger.info(f"Found {len(projects_list)} projects with client info.")
    # return projects_list
    # This function is kept for reference but get_projects_for_display is preferred
    logger.warning("get_projects_with_client_info is deprecated. Use get_projects_for_display instead.")
    return []


def get_projects_for_display(session: Session) -> List[Dict[str, Any]]:
    """Retrieves a list of projects with their primary client, primary sector, and sub-category.
    Uses left joins to ensure all projects are listed even if some details are missing.
    Now includes all fields from the Project model.
    """
    logger.info("Fetching all project details for display (including client and category)...")
    
    # Aliases for clarity in joins
    pc_alias = aliased(ProjectClient, name="primary_client_link")
    client_alias = aliased(Client, name="primary_client")
    pca_alias = aliased(ProjectCategoryAssignment, name="category_assignment")
    ps_alias = aliased(PrimarySector, name="primary_sector")
    psc_alias = aliased(ProjectSubCategory, name="project_sub_category")

    results = (
        session.query(
            Project.project_id,
            Project.project_name,
            Project.equinox_project_number,
            Project.project_alias_alternate_names,
            Project.project_description_short,
            Project.project_description_long,
            Project.project_status,
            Project.project_type,
            Project.industry_sector, # Legacy field
            Project.start_date_planned,
            Project.end_date_planned,
            Project.start_date_actual,
            Project.end_date_actual,
            Project.project_duration_days,
            Project.overall_project_value_budget,
            Project.overall_project_value_actual,
            Project.currency_code,
            Project.main_contract_type,
            Project.project_complexity,
            Project.strategic_importance,
            Project.internal_project_link,
            Project.project_category, # Legacy tag
            Project.project_size_category,
            Project.project_management_approach,
            Project.total_manhours,
            Project.facility_type, # Legacy field
            Project.project_narrative_log,
            Project.created_at,
            Project.updated_at,
            client_alias.client_name.label("client_name"),
            ps_alias.sector_name.label("primary_sector_name"),
            psc_alias.sub_category_name.label("sub_category_name")
        )
        .outerjoin(pc_alias, (Project.project_id == pc_alias.project_id) & (pc_alias.role == "Primary"))
        .outerjoin(client_alias, pc_alias.client_id == client_alias.client_id)
        .outerjoin(pca_alias, Project.project_id == pca_alias.project_id) 
        .outerjoin(psc_alias, pca_alias.sub_category_id == psc_alias.sub_category_id)
        .outerjoin(ps_alias, psc_alias.sector_id == ps_alias.sector_id)
        .order_by(Project.project_name)
        .all()
    )

    projects_list = [{
        "ID": r.project_id,
        "Project Name": r.project_name,
        "Eq. Number": r.equinox_project_number,
        "Alias/Alternate Names": r.project_alias_alternate_names,
        "Short Description": r.project_description_short,
        "Long Description": r.project_description_long,
        "Status": r.project_status,
        "Project Type": r.project_type,
        "Industry Sector (Legacy)": r.industry_sector,
        "Planned Start": r.start_date_planned.strftime("%Y-%m-%d") if r.start_date_planned else None,
        "Planned End": r.end_date_planned.strftime("%Y-%m-%d") if r.end_date_planned else None,
        "Actual Start": r.start_date_actual.strftime("%Y-%m-%d") if r.start_date_actual else None,
        "Actual End": r.end_date_actual.strftime("%Y-%m-%d") if r.end_date_actual else None,
        "Duration (Days)": r.project_duration_days,
        "Budget Value": r.overall_project_value_budget,
        "Actual Value": r.overall_project_value_actual,
        "Currency": r.currency_code,
        "Contract Type": r.main_contract_type,
        "Complexity": r.project_complexity,
        "Strategic Importance": r.strategic_importance,
        "Internal Link": r.internal_project_link,
        "Project Category (Tag)": r.project_category,
        "Size Category": r.project_size_category,
        "Mgmt Approach": r.project_management_approach,
        "Total Manhours": r.total_manhours,
        "Facility Type (Legacy)": r.facility_type,
        "Narrative Log": r.project_narrative_log,
        "Created At": r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else None,
        "Updated At": r.updated_at.strftime("%Y-%m-%d %H:%M:%S") if r.updated_at else None,
        "Client": r.client_name if r.client_name else "N/A",
        "Sector": r.primary_sector_name if r.primary_sector_name else "N/A",
        "Sub-Category": r.sub_category_name if r.sub_category_name else "N/A",
    } for r in results]
    
    logger.info(f"Found {len(projects_list)} projects with all details for display.")
    return projects_list


def get_simple_project_list(session: Session) -> List[Dict[str, Any]]:
    """Retrieves a simple list of projects with ID, Name, Created At, Updated At,
    and the title and full content of the latest project extraction log.
    """
    logger.info("Fetching simple project list with latest extraction log title and content...")
    try:
        # Subquery to get the latest log entry ID for each project
        latest_log_subquery = session.query(
            ProjectExtractionLog.project_id,
            sqlfunc.max(ProjectExtractionLog.log_entry_timestamp).label("latest_timestamp")
        ).group_by(ProjectExtractionLog.project_id).subquery("latest_log_sq")

        # Query projects and left join with ProjectExtractionLog on project_id and the latest_timestamp
        projects_with_logs = session.query(
            Project.project_id,
            Project.project_name,
            Project.created_at,
            Project.updated_at,
            ProjectExtractionLog.log_entry_title,
            ProjectExtractionLog.log_entry_content
        ).outerjoin(
            latest_log_subquery, Project.project_id == latest_log_subquery.c.project_id
        ).outerjoin(
            ProjectExtractionLog,
            (ProjectExtractionLog.project_id == latest_log_subquery.c.project_id) &
            (ProjectExtractionLog.log_entry_timestamp == latest_log_subquery.c.latest_timestamp)
        ).order_by(Project.project_name).all()
        
        project_list = []
        for p in projects_with_logs:
            project_list.append({
                "ID": p.project_id,
                "Project Name": p.project_name,
                "Created At": p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else None,
                "Updated At": p.updated_at.strftime("%Y-%m-%d %H:%M:%S") if p.updated_at else None,
                "Latest Log Title": p.log_entry_title if p.log_entry_title else "N/A",
                "Latest Log Content": p.log_entry_content if p.log_entry_content else "N/A"
            })
            
        logger.info(f"Found {len(project_list)} projects for simple list with full log info.")
        return project_list
    except Exception as e:
        logger.error(f"Error fetching simple project list with full log info: {e}", exc_info=True)
        return []

def get_documents_for_project(session: Session, project_id: int) -> List[Dict[str, Any]]:
    """Retrieves all documents associated with a given project_id.
    Returns a list of dictionaries with key document attributes.
    """
    logger.info(f"Fetching documents for project_id: {project_id}...")
    documents = session.query(Document).filter(Document.project_id == project_id).order_by(Document.file_name).all()
    
    if not documents:
        logger.info(f"No documents found for project_id: {project_id}")
        return []

    doc_list = [{
        "document_id": doc.document_id,
        "File Name": doc.file_name,
        "Type": doc.document_type,
        "Extraction Status": doc.extraction_status,
        "Processed At": doc.last_processed_at.strftime("%Y-%m-%d %H:%M:%S") if doc.last_processed_at else "N/A",
        "Pages/Slides": doc.number_of_pages_slides
    } for doc in documents]
    logger.info(f"Found {len(doc_list)} documents for project_id: {project_id}")
    return doc_list


def get_processed_documents(session: Session) -> List[Dict[str, Any]]:
    """Retrieves all documents that have been processed.
    Returns a list of dictionaries with key document attributes.
    """
    logger.info("Fetching all processed documents...")
    # Consider "Processed - Linked with Tags" and "Processed - No Project Links Established" as processed states
    # Or any status that starts with "Processed"
    processed_statuses = ["Processed - Linked with Tags", "Processed - No Project Links Established"] 
    
    # A more general approach if there are other "Processed" statuses:
    # documents = session.query(Document).filter(Document.extraction_status.like("Processed%")).order_by(Document.last_processed_at.desc()).all()

    documents = session.query(Document).filter(
        Document.extraction_status.in_(processed_statuses)
    ).order_by(Document.last_processed_at.desc()).all()
    
    if not documents:
        logger.info("No processed documents found.")
        return []

    doc_list = [{\
        "document_id": doc.document_id,\
        "File Name": doc.file_name,\
        "Type": doc.document_type,\
        "Extraction Status": doc.extraction_status,\
        "Processed At": doc.last_processed_at.strftime("%Y-%m-%d %H:%M:%S") if doc.last_processed_at else "N/A",\
        "Pages/Slides": doc.number_of_pages_slides,\
        "Project ID": doc.project_id # Added Project ID for context\
    } for doc in documents]
    logger.info(f"Found {len(doc_list)} processed documents.")
    return doc_list


def get_key_info_for_document(session: Session, document_id: int) -> List[Dict[str, Any]]:
    """Retrieves all key information items associated with a given document_id.
    Returns a list of dictionaries with key information attributes.
    """
    logger.info(f"Fetching key information for document_id: {document_id}...")
    key_info_items = session.query(ProjectKeyInformation).filter(ProjectKeyInformation.document_id == document_id).order_by(ProjectKeyInformation.info_category).all()

    if not key_info_items:
        logger.info(f"No key information found for document_id: {document_id}")
        return []
        
    info_list = [{
        "key_info_id": item.key_info_id,
        "Category": item.info_category,
        "Item": item.info_item,
        "Details": item.info_details,
        "Summary": item.info_details_qualifier,
        "Page Ref": item.page_reference_in_document,
        "Confidence": item.extraction_confidence
    } for item in key_info_items]
    logger.info(f"Found {len(info_list)} key info items for document_id: {document_id}")
    return info_list

# --- Database/System Status Functions (New) ---

def get_db_connection_status(db_url: str = "postgresql://db_user:db_password@localhost:5432/project_db") -> tuple[bool, str]:
    """Checks the database connection status."""
    try:
        engine = get_db_engine(db_url) # Assuming get_db_engine is available (imported from database_models)
        with engine.connect() as connection:
            # You can execute a simple query if needed, e.g., connection.execute(text("SELECT 1"))
            # For now, successful connect() is enough.
            return True, "Database connected successfully."
    except OperationalError as oe:
        # This typically catches connection errors like host not found, access denied, etc.
        return False, f"Database connection failed (OperationalError): {oe}"
    except Exception as e:
        return False, f"Database connection failed (General Exception): {str(e)}"

def get_primary_sectors(session: Session) -> List[PrimarySector]:
    """Fetches all primary sectors."""
    try:
        return session.query(PrimarySector).order_by(PrimarySector.sector_name).all()
    except Exception as e:
        # print(f"Error fetching primary sectors: {e}") # Temporary print, replace with logger
        logger.error(f"Error fetching primary sectors: {e}", exc_info=True)
        return []

def get_project_sub_categories(session: Session, sector_id: Optional[int] = None) -> List[ProjectSubCategory]:
    """Fetches all project sub-categories, optionally filtered by sector_id."""
    try:
        query = session.query(ProjectSubCategory)
        if sector_id:
            query = query.filter(ProjectSubCategory.sector_id == sector_id)
        return query.order_by(ProjectSubCategory.sub_category_name).all()
    except Exception as e:
        # print(f"Error fetching project sub-categories: {e}") # Temporary print, replace with logger
        logger.error(f"Error fetching project sub-categories: {e}", exc_info=True)
        return []

def get_project_statuses() -> List[str]:
    """Returns a predefined list of common project statuses."""
    # These could eventually come from a dedicated lookup table or be dynamically generated
    # For now, a static list suffices for UI elements like dropdowns.
    return [
        "Unknown/Other",
        "Lead/Inquiry",
        "Bid/Proposal",
        "In Progress",
        "On Hold",
        "Completed",
        "Cancelled",
        "Executed" # For mentioned projects
    ]

# --- ProjectExtractionLog CRUD --- NEW SECTION ---

def add_project_extraction_log(
    session: Session, 
    project_id: int, 
    pertinent_content: str,         # Changed from log_entry_content
    source_document_name: Optional[str],
    entry_timestamp: datetime.datetime, # New parameter for the specific entry's timestamp
    log_entry_title: Optional[str] = None, 
    llm_verification_action: Optional[str] = None,
    llm_verification_confidence: Optional[float] = None,
    llm_verification_reasoning: Optional[str] = None
) -> Optional[ProjectExtractionLog]:
    """Adds or appends to a project extraction log entry. 
    The log_entry_content becomes a cumulative record.
    LLM verification details are updated to reflect the latest appended entry.
    """
    try:
        existing_log = session.query(ProjectExtractionLog).filter_by(project_id=project_id).first()

        formatted_pertinent_text = f"\n\n---\nTimestamp: {entry_timestamp.strftime('%Y-%m-%d %H:%M:%S %Z')}\nSource Document: {source_document_name or 'Unknown'}\n---\n{pertinent_content}"

        if existing_log:
            logger.info(f"Appending to existing ProjectExtractionLog ID {existing_log.log_entry_id} for project ID {project_id}.")
            existing_log.log_entry_content += formatted_pertinent_text
            # Update fields to reflect the latest appended information
            existing_log.source_document_name = source_document_name
            existing_log.llm_verification_action = llm_verification_action
            existing_log.llm_verification_confidence = llm_verification_confidence
            existing_log.llm_verification_reasoning = llm_verification_reasoning
            # The model's own log_entry_timestamp will be updated by server_default on commit/refresh if defined as onupdate.
            # If not, we should set it explicitly: existing_log.log_entry_timestamp = datetime.datetime.now(datetime.timezone.utc)
            # Assuming server_default=sqlfunc.now() on the model handles update timestamp or it's not critical to reflect append time on the main row ts.
            # For clarity, let's explicitly update it to the entry_timestamp of this latest piece of info.
            existing_log.log_entry_timestamp = entry_timestamp

            session.commit()
            session.refresh(existing_log)
            logger.info(f"Appended content to ProjectExtractionLog ID {existing_log.log_entry_id}.")
            return existing_log
        else:
            logger.info(f"Creating new ProjectExtractionLog for project ID {project_id}.")
            # For a new log, the title is more relevant.
            # The initial pertinent_content forms the base.
            new_log_data = {
                "project_id": project_id,
                "log_entry_title": log_entry_title if log_entry_title else f"Initial Log from {source_document_name or 'document'}",
                "log_entry_content": formatted_pertinent_text.strip(), # Remove leading newlines for the first entry
                "source_document_name": source_document_name,
                "llm_verification_action": llm_verification_action,
                "llm_verification_confidence": llm_verification_confidence,
                "llm_verification_reasoning": llm_verification_reasoning,
                "log_entry_timestamp": entry_timestamp # Set initial timestamp
            }
            # Filter for valid keys just in case, though all should be valid here
            valid_keys = {col.name for col in ProjectExtractionLog.__table__.columns if col.name != 'log_entry_id'}
            filtered_log_data = {k: v for k, v in new_log_data.items() if k in valid_keys}

            new_log = ProjectExtractionLog(**filtered_log_data)
            session.add(new_log)
            session.commit()
            session.refresh(new_log)
            logger.info(f"Created new ProjectExtractionLog ID {new_log.log_entry_id} for project ID {project_id}.")
            return new_log

    except Exception as e:
        session.rollback()
        logger.error(f"Error adding/appending project extraction log for project ID {project_id}: {e}", exc_info=True)
        return None

def get_project_extraction_logs(session: Session, project_id: int) -> List[ProjectExtractionLog]:
    """Retrieves all extraction log entries for a given project, ordered by timestamp descending."""
    try:
        logs = session.query(ProjectExtractionLog).filter(
            ProjectExtractionLog.project_id == project_id
        ).order_by(ProjectExtractionLog.log_entry_timestamp.desc()).all()
        logger.info(f"Retrieved {len(logs)} extraction logs for project ID {project_id}")
        return logs
    except Exception as e:
        logger.error(f"Error retrieving project extraction logs for project ID {project_id}: {e}", exc_info=True)
        return []

# --- ProjectExtractionLogTag CRUD ---

def add_project_extraction_log_tag(session: Session, log_entry_id: int, tag_name: str) -> Optional[ProjectExtractionLogTag]:
    """Adds a tag to a specific project extraction log entry."""
    # Check if the tag already exists for this log entry to prevent duplicates from code logic
    # The database has a unique constraint, but this check avoids an explicit IntegrityError
    existing_tag = session.query(ProjectExtractionLogTag).filter_by(log_entry_id=log_entry_id, tag_name=tag_name).first()
    if existing_tag:
        return existing_tag

    new_tag = ProjectExtractionLogTag(log_entry_id=log_entry_id, tag_name=tag_name)
    try:
        session.add(new_tag)
        session.commit()
        session.refresh(new_tag)
        return new_tag
    except IntegrityError: # Catch potential race condition if constraint is violated
        session.rollback()
        logger.warning(f"IntegrityError adding tag '{tag_name}' to log_entry_id {log_entry_id}. Likely already exists.")
        # Attempt to return the existing tag if the error was due to a race condition on the unique constraint
        return session.query(ProjectExtractionLogTag).filter_by(log_entry_id=log_entry_id, tag_name=tag_name).first()
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding tag '{tag_name}' to log_entry_id {log_entry_id}: {e}", exc_info=True)
        return None

def add_project_extraction_log_tags(session: Session, log_entry_id: int, tag_names: List[str]) -> List[ProjectExtractionLogTag]:
    """Adds multiple tags to a specific project extraction log entry."""
    added_tags = []
    for tag_name in tag_names:
        if not tag_name.strip(): # Skip empty tags
            continue
        tag = add_project_extraction_log_tag(session, log_entry_id, tag_name.strip())
        if tag:
            added_tags.append(tag)
    return added_tags

def get_tags_for_log_entry(session: Session, log_entry_id: int) -> List[ProjectExtractionLogTag]:
    """Retrieves all tags for a specific project extraction log entry."""
    return session.query(ProjectExtractionLogTag).filter(ProjectExtractionLogTag.log_entry_id == log_entry_id).all()

# --- DocumentProcessingAuditLog CRUD ---
def add_document_processing_audit_log(
    session: Session,
    document_id: Optional[int] = None,
    source_document_name: Optional[str] = None,
    processing_stage: Optional[str] = None,
    raw_mention: Optional[str] = None,
    llm_action: Optional[str] = None,
    llm_confirmed_project_name: Optional[str] = None,
    llm_project_id_linked: Optional[int] = None,
    llm_suggested_tags: Optional[List[str]] = None, # Input as list, store as JSON string
    llm_confidence: Optional[float] = None,
    llm_reasoning: Optional[str] = None,
    notes: Optional[str] = None
) -> Optional[DocumentProcessingAuditLog]:
    """Adds an entry to the document processing audit log."""
    try:
        tags_json_string = None
        if llm_suggested_tags:
            try:
                tags_json_string = json.dumps(llm_suggested_tags)
            except TypeError as te:
                logger.error(f"Could not serialize suggested_tags to JSON: {te}. Tags: {llm_suggested_tags}")

        audit_entry = DocumentProcessingAuditLog(
            document_id=document_id,
            source_document_name=source_document_name,
            processing_stage=processing_stage,
            raw_mention=raw_mention,
            llm_action=llm_action,
            llm_confirmed_project_name=llm_confirmed_project_name,
            llm_project_id_linked=llm_project_id_linked,
            llm_suggested_tags=tags_json_string,
            llm_confidence=llm_confidence,
            llm_reasoning=llm_reasoning,
            notes=notes
        )
        session.add(audit_entry)
        session.commit()
        session.refresh(audit_entry)
        logger.info(f"Added audit log entry ID {audit_entry.audit_id} for doc: {source_document_name or document_id}, stage: {processing_stage}, action: {llm_action}")
        return audit_entry
    except Exception as e:
        session.rollback()
        logger.error(f"Error adding document processing audit log: {e}", exc_info=True)
        return None

def get_comprehensive_project_list(session: Session) -> List[Dict[str, Any]]:
    """Retrieves a comprehensive list of projects with ALL their extraction log content aggregated.
    This provides a complete view of all gathered content for each project, not just the latest log.
    """
    logger.info("Fetching comprehensive project list with ALL extraction log content aggregated...")
    try:
        # Get all projects first
        projects = session.query(Project).order_by(Project.project_name).all()
        
        project_list = []
        for project in projects:
            # Get ALL extraction logs for this project
            all_logs = session.query(ProjectExtractionLog).filter(
                ProjectExtractionLog.project_id == project.project_id
            ).order_by(ProjectExtractionLog.log_entry_timestamp.desc()).all()
            
            # Aggregate all log content
            all_titles = []
            all_content = []
            log_count = len(all_logs)
            
            for log in all_logs:
                if log.log_entry_title:
                    all_titles.append(log.log_entry_title)
                if log.log_entry_content:
                    all_content.append(log.log_entry_content)
            
            # Create comprehensive content summary
            comprehensive_titles = " | ".join(all_titles) if all_titles else "N/A"
            comprehensive_content = "\n---\n".join(all_content) if all_content else "N/A"
            
            # Truncate for display if too long
            display_titles = comprehensive_titles[:200] + "..." if len(comprehensive_titles) > 200 else comprehensive_titles
            display_content = comprehensive_content[:500] + "..." if len(comprehensive_content) > 500 else comprehensive_content
            
            project_list.append({
                "ID": project.project_id,
                "Project Name": project.project_name,
                "Created At": project.created_at.strftime("%Y-%m-%d %H:%M:%S") if project.created_at else None,
                "Updated At": project.updated_at.strftime("%Y-%m-%d %H:%M:%S") if project.updated_at else None,
                "Total Logs": log_count,
                "All Log Titles": display_titles,
                "Comprehensive Content": display_content,
                "Full Content": comprehensive_content  # Store full content for detailed view
            })
            
        logger.info(f"Found {len(project_list)} projects with comprehensive content aggregation.")
        return project_list
    except Exception as e:
        logger.error(f"Error fetching comprehensive project list: {e}", exc_info=True)
        return []

# --- Example Usage (Illustrative) ---
if __name__ == '__main__':
    db_session = get_session()
    print("Database CRUD Operations Test Script")
    print("------------------------------------")

    # 1. Get or Create Project
    print("\n1. Testing Project Get/Create...")
    project_defaults = {"project_description_short": "Initial test project for CRUD ops."}
    proj1 = get_or_create_project(db_session, "Test Project Alpha", "EQX-001-ALPHA", defaults=project_defaults)
    print(f"  Got/Created Project ID: {proj1.project_id}, Name: {proj1.project_name}, Number: {proj1.equinox_project_number}")
    proj2_defaults = {"project_status": "Planning", "currency_code":"USD"}
    proj2 = get_or_create_project(db_session, "Test Project Beta", defaults=proj2_defaults) # No project number initially
    print(f"  Got/Created Project ID: {proj2.project_id}, Name: {proj2.project_name}, Status: {proj2.project_status}")
    # Try to get proj1 again
    proj1_again = get_or_create_project(db_session, "Test Project Alpha", "EQX-001-ALPHA", defaults={"project_status": "Active"})
    print(f"  Fetched Project ID: {proj1_again.project_id}, Name: {proj1_again.project_name}, Status: {proj1_again.project_status}")

    # 2. Add Document to Project
    print("\n2. Testing Add Document...")
    doc1_defaults = {"document_title_extracted": "Alpha Presentation Q1"}
    doc1 = add_document_to_project(db_session, proj1.project_id, "alpha_q1.pptx", "/path/to/alpha_q1.pptx", ".pptx", defaults=doc1_defaults)
    print(f"  Added Document ID: {doc1.document_id} to Project ID: {proj1.project_id}, Path: {doc1.file_path}")
    doc2 = add_document_to_project(db_session, proj1.project_id, "alpha_report.pdf", "/path/to/alpha_report.pdf", ".pdf")
    print(f"  Added Document ID: {doc2.document_id} to Project ID: {proj1.project_id}, Path: {doc2.file_path}")

    # 3. Update Document Status
    print("\n3. Testing Update Document Status...")
    updated_doc1 = update_document_extraction_status(db_session, doc1.document_id, "Processed", extracted_info={"metadata":{"title":"Final Alpha Q1 Deck"}, "num_pages":20})
    if updated_doc1:
        print(f"  Updated Doc ID: {updated_doc1.document_id}, Status: {updated_doc1.extraction_status}, Title: {updated_doc1.document_title_extracted}")

    # 4. Get or Create Client and Link to Project
    print("\n4. Testing Client Get/Create and Linking...")
    client1_defaults = {"client_industry": "Energy"}
    client1 = get_or_create_client(db_session, "Global Energy Corp", defaults=client1_defaults)
    print(f"  Got/Created Client ID: {client1.client_id}, Name: {client1.client_name}")
    link1 = link_project_client(db_session, proj1.project_id, client1.client_id, role="Primary Client")
    if link1:
        print(f"  Linked Project ID: {link1.project_id} with Client ID: {link1.client_id} as '{link1.role}'")

    # 5. Assign Project to Category (assuming categories seeded)
    print("\n5. Testing Assign Project to Category...")
    # Find a sub-category to assign to (e.g., 'Gas Processing Plants')
    gas_processing_sub_cat = db_session.query(ProjectSubCategory).filter(ProjectSubCategory.sub_category_name.ilike("%Gas Processing Plants%")).first()
    if gas_processing_sub_cat:
        print(f"  Found sub-category for assignment: {gas_processing_sub_cat.sub_category_name} (ID: {gas_processing_sub_cat.sub_category_id})")
        assignment = assign_project_to_category(db_session, proj1.project_id, gas_processing_sub_cat.sub_category_id, notes="Key gas plant project")
        if assignment:
            print(f"  Assigned Project ID: {proj1.project_id} to SubCategory ID: {gas_processing_sub_cat.sub_category_id}")
    else:
        print("  Could not find 'Gas Processing Plants' sub-category to test assignment. Please ensure it was seeded.")

    # 6. Add Project Key Information
    print("\n6. Testing Add Project Key Information...")
    key_info1 = add_project_key_info(db_session, proj1.project_id, 
                                     info_category="Budget", info_item="$5M", 
                                     doc_id=doc1.document_id, info_details="Initial approved budget", 
                                     page_ref="Slide 3", confidence=0.95)
    if key_info1:
        print(f"  Added Key Info ID: {key_info1.info_id}, Category: {key_info1.info_category}, Item: {key_info1.info_item}")
    key_info2 = add_project_key_info(db_session, proj1.project_id, 
                                     info_category="Technology", info_item="Advanced Carbon Capture")
    if key_info2:
        print(f"  Added Key Info ID: {key_info2.info_id}, Category: {key_info2.info_category}, Item: {key_info2.info_item}")

    # 7. Update Project Narrative Log
    print("\n7. Testing Update Project Narrative Log...")
    update_project_narrative(db_session, proj1.project_id, "Client meeting held, scope clarified.")
    updated_proj1 = db_session.query(Project).filter(Project.project_id == proj1.project_id).first()
    if updated_proj1 and updated_proj1.project_narrative_log:
        print(f"  Project {updated_proj1.project_id} Narrative Log (last entry):\n    {updated_proj1.project_narrative_log.splitlines()[-1] if updated_proj1.project_narrative_log else 'Empty'}")

    print("\n8. Testing Get Projects with Client Info...")
    projects_info = get_projects_with_client_info(db_session)
    if projects_info:
        print(f"  Found {len(projects_info)} projects.")
        for i, p_info in enumerate(projects_info[:3]): # Print first 3
            print(f"    Project {i+1}: ID {p_info['project'].project_id}, Name: {p_info['project'].project_name}, Clients: {p_info['client_names']}")
    else:
        print("  No projects found by get_projects_with_client_info.")

    print("\n------------------------------------")
    print("CRUD Operations Test Script Finished.")
    print("Note: This script makes changes to the database.")
    print("Run src/clean_db_test_data.py (to be created) or manually clean if needed.")

    db_session.close() 