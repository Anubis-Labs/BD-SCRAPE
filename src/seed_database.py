# src/seed_database.py
import re
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError
import os
import json
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

# Adjust import path assuming running from workspace root: python src/seed_database.py
# If src is not in PYTHONPATH, this might need adjustment or running with `python -m src.seed_database`
try:
    # For running as a module (e.g. python -m src.seed_database)
    from .database_models import get_db_engine, PrimarySector, ProjectSubCategory, create_tables
except ImportError:
    # For running as a script from the root (e.g. python src/seed_database.py)
    from database_models import get_db_engine, PrimarySector, ProjectSubCategory, create_tables

# Setup logger for this module
logger = logging.getLogger(__name__)

# Assuming project_categorization_schema.md is in the workspace root
# Get the absolute path to the directory containing the current script
_CURRENT_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Go up one level to the 'src' directory's parent (workspace root)
_WORKSPACE_ROOT = os.path.dirname(_CURRENT_SCRIPT_DIR)
PROJECT_CATEGORIZATION_SCHEMA_PATH = os.path.join(_WORKSPACE_ROOT, "project_categorization_schema.md")


def parse_and_seed_categories(session):
    """
    Parses the project_categorization_schema.md and seeds the
    PrimarySectors and ProjectSubCategories tables.
    This is a simplified parser tailored to the schema's markdown format.
    """
    logger.info(f"Parsing categorization schema from: {PROJECT_CATEGORIZATION_SCHEMA_PATH}")
    if not os.path.exists(PROJECT_CATEGORIZATION_SCHEMA_PATH):
        logger.error(f"{PROJECT_CATEGORIZATION_SCHEMA_PATH} not found. Cannot seed categories.")
        return
        
    try:
        with open(PROJECT_CATEGORIZATION_SCHEMA_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        logger.error(f"Error reading {PROJECT_CATEGORIZATION_SCHEMA_PATH}: {e}", exc_info=True)
        return

    current_primary_sector_db = None
    # This dictionary will store the last seen sub-category that can act as a parent
    # Key: depth/level (e.g., based on number of dots in code '1.1'), Value: ProjectSubCategory object
    parent_sub_categories_stack = {} 

    # Regex patterns to identify levels
    # Level 1: ### 1. Sector Name
    primary_sector_pattern = re.compile(r"^###\s*([\d.]+)\s*(.+)")
    # Level 2 (SubCategory under PrimarySector): #### 1.1. SubCategory Name
    sub_category_pattern = re.compile(r"^####\s*([\d.]+)\s*(.+)")
    # Level 3 (Specific Type under SubCategory): *   **1.1.1. Specific Type**
    specific_type_pattern = re.compile(r"^\s*\*\s*\*\*([\d.]+)\s*([^*]+)\*\*")

    # Track existing entries to avoid duplicates if script is run multiple times
    existing_sectors = {s.sector_name: s for s in session.query(PrimarySector).all()}
    existing_sub_categories = {sc.sub_category_name: sc for sc in session.query(ProjectSubCategory).all()}

    logger.info("Starting to seed categories...")

    for line_num, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue

        ps_match = primary_sector_pattern.match(line)
        sc_match = sub_category_pattern.match(line)
        st_match = specific_type_pattern.match(line)

        try:
            if ps_match:
                code = ps_match.group(1).strip()
                name = ps_match.group(2).strip()
                if name not in existing_sectors:
                    current_primary_sector_db = PrimarySector(sector_name=name)
                    session.add(current_primary_sector_db)
                    session.flush() # Get ID for potential children
                    existing_sectors[name] = current_primary_sector_db
                    logger.info(f"  Added PrimarySector: {name} (Code: {code})")
                else:
                    current_primary_sector_db = existing_sectors[name]
                parent_sub_categories_stack.clear() # Reset for new primary sector

            elif sc_match and current_primary_sector_db:
                code = sc_match.group(1).strip()
                name = sc_match.group(2).strip()
                current_code_depth = code.count('.') # Depth for '1.1' is 1, '1' is 0

                if name not in existing_sub_categories:
                    new_sub_cat = ProjectSubCategory(
                        sub_category_name=name, 
                        sub_category_code=code,
                        sector_id=current_primary_sector_db.sector_id
                    )
                    session.add(new_sub_cat)
                    session.flush() # Get ID
                    existing_sub_categories[name] = new_sub_cat
                    parent_sub_categories_stack[current_code_depth] = new_sub_cat
                    logger.info(f"    Added SubCategory: {name} (Code: {code}) under {current_primary_sector_db.sector_name}")
                else:
                    parent_sub_categories_stack[current_code_depth] = existing_sub_categories[name]
            
            elif st_match and current_primary_sector_db: # Specific type, potentially under a sub_category
                code = st_match.group(1).strip()
                name = st_match.group(2).strip()
                
                parent_to_use = None
                current_code_depth = code.count('.') # Depth for '1.1.1' is 2
                
                parent_depth_key = current_code_depth - 1 
                if parent_depth_key in parent_sub_categories_stack:
                    potential_parent = parent_sub_categories_stack[parent_depth_key]
                    # Ensure the parent's code is a prefix of the current item's code.
                    # E.g. parent '1.1' is prefix of child '1.1.1'
                    if code.startswith(potential_parent.sub_category_code + '.'):
                         parent_to_use = potential_parent
                
                if name not in existing_sub_categories:
                    if parent_to_use:
                        new_spec_type = ProjectSubCategory(
                            sub_category_name=name,
                            sub_category_code=code,
                            sector_id=current_primary_sector_db.sector_id, 
                            parent_sub_category_id=parent_to_use.sub_category_id
                        )
                        session.add(new_spec_type)
                        session.flush()
                        existing_sub_categories[name] = new_spec_type
                        parent_sub_categories_stack[current_code_depth] = new_spec_type 
                        logger.info(f"      Added Specific Type: {name} (Code: {code}) under {parent_to_use.sub_category_name}")
                    else: 
                        new_spec_type = ProjectSubCategory(
                            sub_category_name=name,
                            sub_category_code=code,
                            sector_id=current_primary_sector_db.sector_id
                        )
                        session.add(new_spec_type)
                        session.flush()
                        existing_sub_categories[name] = new_spec_type
                        parent_sub_categories_stack[current_code_depth] = new_spec_type
                        logger.info(f"      Added Specific Type (as direct sub of sector): {name} (Code: {code}) under {current_primary_sector_db.sector_name}")
                else: 
                     parent_sub_categories_stack[current_code_depth] = existing_sub_categories[name]

        except IntegrityError as ie:
            session.rollback()
            logger.warning(f"Skipping due to IntegrityError for line '{line.strip()}': {ie}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error processing line {line_num+1} ('{line.strip()}'): {e}", exc_info=True)

    try:
        session.commit()
        logger.info("Category seeding committed successfully.")
    except Exception as e:
        session.rollback()
        logger.error(f"Error committing seeded categories: {e}", exc_info=True)

def seed_initial_data(db: Optional[Session] = None):
    # Configure basic logging for direct script execution
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    logger.info("Running seed_database.py directly...")
    db_url = "postgresql://db_user:db_password@localhost:5432/project_db"
    engine = get_db_engine(db_url)
    
    # --- ADDED: Create tables if they don't exist ---
    logger.info("Ensuring database tables are created...")
    try:
        create_tables(engine) # This function should be in database_models.py
        logger.info("Database tables verified/created successfully.")
    except Exception as e:
        logger.error(f"Error creating database tables: {e}", exc_info=True)
        # Depending on the error, we might not want to proceed with seeding.
        # For now, it will try to continue, but seeding might fail if tables are missing.
    # --- END ADDED ---

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        parse_and_seed_categories(session)
        logger.info("Seeding process completed.")
    except Exception as e:
        logger.error(f"An error occurred during the seeding process: {e}", exc_info=True)
    finally:
        session.close()
        logger.info("Database session closed by seed_initial_data.")

if __name__ == '__main__':
    seed_initial_data()
    logger.info("Seeding finished when run directly.")