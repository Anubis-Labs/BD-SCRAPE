# src/db_logic.py
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import create_engine, func as sqlfunc
from typing import Optional, List
import logging

# Use a direct, unambiguous relative import.
from .database_models import Base, Project, get_db_engine

logger = logging.getLogger(__name__)

def get_session(db_url: Optional[str] = None) -> Session:
    """Creates a new database session."""
    engine = get_db_engine(db_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()

def append_to_project_data(session: Session, project_name: str, text_to_append: str):
    """
    Finds a project by its name or creates it if it doesn't exist,
    then appends the given text to its aggregated_data field.
    """
    normalized_name = " ".join(project_name.strip().split())
    if not normalized_name:
        logger.warning("Attempted to append data to a project with an empty name.")
        return

    try:
        project = session.query(Project).filter(Project.project_name == normalized_name).first()

        if project:
            current_data = project.aggregated_data if project.aggregated_data is not None else ""
            project.aggregated_data = current_data + text_to_append
        else:
            project = Project(
                project_name=normalized_name,
                aggregated_data=text_to_append
            )
            session.add(project)
        
        session.commit()
        session.refresh(project)
        logger.info(f"Successfully saved data for project ID: {project.project_id}")

    except Exception as e:
        logger.error(f"Database error while appending data for project '{normalized_name}': {e}", exc_info=True)
        session.rollback()
        raise

def get_all_project_names(session: Session) -> List[str]:
    """
    Retrieves a sorted list of all project names from the database.
    """
    try:
        projects = session.query(Project.project_name).order_by(Project.project_name).all()
        return [project.project_name for project in projects]
    except Exception as e:
        logger.error(f"Failed to retrieve project names: {e}", exc_info=True)
        return []

def get_project_data(session: Session, project_name: str) -> Optional[str]:
    """
    Retrieves the aggregated_data for a specific project by its name.
    """
    try:
        project = session.query(Project).filter(Project.project_name == project_name).first()
        if project:
            return project.aggregated_data
        return None
    except Exception as e:
        logger.error(f"Failed to retrieve data for project '{project_name}': {e}", exc_info=True)
        return None

def update_project_categorization(session: Session, project_id: int, category: str, sub_category: str, project_scope: str):
    """
    Updates the categorization fields for a specific project.
    """
    try:
        project = session.query(Project).filter(Project.project_id == project_id).first()
        if project:
            project.category = category
            project.sub_category = sub_category
            project.project_scope = project_scope
            session.commit()
            logger.info(f"Successfully updated categorization for project ID: {project_id}")
            return True
        else:
            logger.warning(f"Could not find project with ID {project_id} to update categorization.")
            return False
    except Exception as e:
        logger.error(f"Database error while updating categorization for project ID {project_id}: {e}", exc_info=True)
        session.rollback()
        raise

def get_db_connection_status() -> tuple[bool, str]:
    """
    Checks if a connection to the database can be established.
    Returns a tuple of (bool: success, str: message).
    """
    try:
        engine = get_db_engine()
        with engine.connect() as connection:
            return True, "Connection Successful"
    except Exception as e:
        logger.error(f"Database connection failed: {e}", exc_info=False)
        # Return a concise error message for the UI
        return False, str(e).splitlines()[0] 