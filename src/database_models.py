# src/database_models.py

from sqlalchemy import create_engine, Column, Integer, String, Text, Date, DateTime, DECIMAL, VARCHAR, ForeignKey, TIMESTAMP, UniqueConstraint, Index, Boolean, Float # Added Float
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column # updated for modern SQLAlchemy
from sqlalchemy.sql import func as sqlfunc # For server-side default timestamps, aliased to avoid conflict
import datetime
from typing import List, Optional
import logging # Add this import


Base = declarative_base()

# Setup a logger for this module (similar to other modules)
logger = logging.getLogger(__name__)
# Basic configuration if no handlers are found (e.g., when run standalone or not imported by a configured app)
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# --- Core Project Information Tables ---

class Project(Base):
    __tablename__ = "Projects"

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(Text, nullable=False)
    equinox_project_number: Mapped[Optional[str]] = mapped_column(VARCHAR(255), unique=True, nullable=True)
    project_alias_alternate_names: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_description_short: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_description_long: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_status: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    project_type: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    industry_sector: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    start_date_planned: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    end_date_planned: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    start_date_actual: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    end_date_actual: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    project_duration_days: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    overall_project_value_budget: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(18, 2), nullable=True)
    overall_project_value_actual: Mapped[Optional[DECIMAL]] = mapped_column(DECIMAL(18, 2), nullable=True)
    currency_code: Mapped[Optional[str]] = mapped_column(VARCHAR(3), nullable=True)
    main_contract_type: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    project_complexity: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    strategic_importance: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    internal_project_link: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    project_category: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    project_size_category: Mapped[Optional[str]] = mapped_column(VARCHAR(50), nullable=True)
    project_management_approach: Mapped[Optional[str]] = mapped_column(VARCHAR(100), nullable=True)
    total_manhours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    facility_type: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    project_narrative_log: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sqlfunc.now())
    updated_at: Mapped[datetime.datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=sqlfunc.now(), onupdate=sqlfunc.now())

    # Relationships
    clients: Mapped[List["ProjectClient"]] = relationship(back_populates="project")
    locations: Mapped[List["Location"]] = relationship(back_populates="project")
    documents: Mapped[List["Document"]] = relationship(back_populates="project")
    key_information: Mapped[List["ProjectKeyInformation"]] = relationship(back_populates="project")
    technologies: Mapped[List["ProjectTechnology"]] = relationship(back_populates="project")
    personnel_roles: Mapped[List["ProjectPersonnelRole"]] = relationship(back_populates="project")
    partners: Mapped[List["ProjectPartner"]] = relationship(back_populates="project")
    financials: Mapped[List["ProjectFinancial"]] = relationship(back_populates="project")
    milestones: Mapped[List["ProjectPhaseMilestone"]] = relationship(back_populates="project")
    risks_challenges: Mapped[List["ProjectRiskOrChallenge"]] = relationship(back_populates="project")
    phase_services: Mapped[List["ProjectPhaseService"]] = relationship(back_populates="project")
    category_assignments: Mapped[List["ProjectCategoryAssignment"]] = relationship(back_populates="project")
    extraction_logs: Mapped[List["ProjectExtractionLog"]] = relationship(back_populates="project")


class Client(Base):
    __tablename__ = "Clients"
    client_id = Column(Integer, primary_key=True, autoincrement=True)
    client_name = Column(VARCHAR(255), nullable=False, unique=True)
    client_industry = Column(VARCHAR(255), nullable=True)
    client_country = Column(VARCHAR(100), nullable=True)
    client_contact_person = Column(VARCHAR(255), nullable=True)
    client_relationship_type = Column(VARCHAR(100), nullable=True)

    projects = relationship("ProjectClient", back_populates="client")

class ProjectClient(Base): # Association Table for Projects and Clients
    __tablename__ = "ProjectClients"
    project_id = Column(Integer, ForeignKey("Projects.project_id"), primary_key=True)
    client_id = Column(Integer, ForeignKey("Clients.client_id"), primary_key=True)
    role = Column(VARCHAR(100), primary_key=True) # Role can be part of PK if a client can have multiple roles on one project

    project = relationship("Project", back_populates="clients")
    client = relationship("Client", back_populates="projects")

class Location(Base):
    __tablename__ = "Locations"
    location_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    latitude = Column(DECIMAL(9, 6), nullable=True)
    longitude = Column(DECIMAL(10, 6), nullable=True)
    land_survey_identifier = Column(Text, nullable=True)
    location_type = Column(VARCHAR(100), nullable=True)

    project = relationship("Project", back_populates="locations")

class Document(Base):
    __tablename__ = "Documents"
    document_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=True) # Allow null if a doc isn't immediately linked
    file_name = Column(Text, nullable=False)
    file_path = Column(Text, nullable=False, unique=True)
    document_type = Column(VARCHAR(50), nullable=True) # e.g., PPTX, PDF, DOCX (from parser)
    document_title_extracted = Column(Text, nullable=True)
    author_extracted = Column(Text, nullable=True)
    creation_date_extracted = Column(Date, nullable=True)
    last_modified_date_extracted = Column(Date, nullable=True)
    number_of_pages_slides = Column(Integer, nullable=True)
    extraction_status = Column(VARCHAR(50), nullable=True) # e.g., Pending, Processed, Error
    last_processed_at = Column(TIMESTAMP(timezone=True), nullable=True)
    full_document_text = Column(Text, nullable=True) # Store complete document text for better extraction and analysis
    comprehensive_extraction_data = Column(Text, nullable=True) # Store comprehensive extraction results as JSON

    project = relationship("Project", back_populates="documents")
    key_information_entries = relationship("ProjectKeyInformation", back_populates="document_source")

class ProjectKeyInformation(Base):
    __tablename__ = "ProjectKeyInformation"
    info_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    document_id = Column(Integer, ForeignKey("Documents.document_id"), nullable=True)
    info_category = Column(VARCHAR(255), nullable=False)
    info_item = Column(Text, nullable=False)
    info_details_qualifier = Column(Text, nullable=True)
    source_page_reference = Column(VARCHAR(50), nullable=True)
    confidence_score_llm = Column(DECIMAL(5,4), nullable=True) # Assuming score like 0.xxxx

    project = relationship("Project", back_populates="key_information")
    document_source = relationship("Document", back_populates="key_information_entries")

# --- Technology Related Tables ---
class Technology(Base):
    __tablename__ = "Technologies"
    technology_id = Column(Integer, primary_key=True, autoincrement=True)
    technology_name = Column(VARCHAR(255), nullable=False, unique=True)
    technology_type = Column(VARCHAR(100), nullable=True)
    technology_version = Column(VARCHAR(100), nullable=True)
    technology_domain = Column(VARCHAR(255), nullable=True)
    primary_purpose_or_application = Column(Text, nullable=True)
    vendor_manufacturer = Column(VARCHAR(255), nullable=True)
    description = Column(Text, nullable=True)

    projects = relationship("ProjectTechnology", back_populates="technology")

class ProjectTechnology(Base): # Association Table for Projects and Technologies
    __tablename__ = "ProjectTechnologies"
    project_id = Column(Integer, ForeignKey("Projects.project_id"), primary_key=True)
    technology_id = Column(Integer, ForeignKey("Technologies.technology_id"), primary_key=True)
    application_notes = Column(Text, nullable=True)
    # Replicated fields from ProjectKeyInformation as per schema - this design might be reviewed.
    # If these are always tied to a technology within a project, it's fine.
    # Alternatively, ProjectKeyInformation could have a nullable technology_id.
    info_category = Column(VARCHAR(255), nullable=True) # Made nullable as it may not always apply or primary key covers it
    info_item = Column(Text, nullable=True) # Made nullable
    info_details_qualifier = Column(Text, nullable=True)

    project = relationship("Project", back_populates="technologies")
    technology = relationship("Technology", back_populates="projects")

# --- Personnel, Partners, Financials, Milestones, Risks, Phases ---

class ProjectPersonnelRole(Base):
    __tablename__ = "ProjectPersonnelRoles"
    personnel_role_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    person_name = Column(VARCHAR(255), nullable=True)
    role_on_project = Column(VARCHAR(255), nullable=True)
    organization_affiliation = Column(VARCHAR(255), nullable=True)
    contact_details = Column(Text, nullable=True)

    project = relationship("Project", back_populates="personnel_roles")

class Partner(Base):
    __tablename__ = "Partners"
    partner_id = Column(Integer, primary_key=True, autoincrement=True)
    partner_name = Column(VARCHAR(255), nullable=False, unique=True)
    partner_type = Column(VARCHAR(100), nullable=True)
    contact_info = Column(Text, nullable=True)
    description = Column(Text, nullable=True)

    projects = relationship("ProjectPartner", back_populates="partner")

class ProjectPartner(Base): # Association Table
    __tablename__ = "ProjectPartners"
    project_partner_id = Column(Integer, primary_key=True, autoincrement=True) # Own PK for this association
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    partner_id = Column(Integer, ForeignKey("Partners.partner_id"), nullable=False)
    role_on_project = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="partners")
    partner = relationship("Partner", back_populates="projects")
    __table_args__ = (UniqueConstraint('project_id', 'partner_id', 'role_on_project', name='_project_partner_role_uc'),) # Example constraint

class ProjectFinancial(Base):
    __tablename__ = "ProjectFinancials"
    financial_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    financial_category = Column(VARCHAR(255), nullable=False)
    amount = Column(DECIMAL(18, 2), nullable=False)
    currency_code = Column(VARCHAR(3), nullable=False)
    date_recorded = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)
    responsible_party = Column(VARCHAR(255), nullable=True)

    project = relationship("Project", back_populates="financials")

class ProjectPhaseMilestone(Base):
    __tablename__ = "ProjectPhasesMilestones"
    milestone_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    milestone_name_description = Column(Text, nullable=False)
    phase_name = Column(VARCHAR(255), nullable=True)
    planned_date = Column(Date, nullable=True)
    actual_completion_date = Column(Date, nullable=True)
    status = Column(VARCHAR(100), nullable=True)

    project = relationship("Project", back_populates="milestones")

class ProjectRiskOrChallenge(Base):
    __tablename__ = "ProjectRisksOrChallenges"
    item_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    item_type = Column(VARCHAR(50), nullable=False) # Risk, Challenge, Issue, Opportunity
    description = Column(Text, nullable=False)
    date_identified = Column(Date, nullable=True)
    impact_assessment = Column(Text, nullable=True)
    response_mitigation_solution = Column(Text, nullable=True)
    status = Column(VARCHAR(100), nullable=True)
    responsible_party = Column(VARCHAR(255), nullable=True)

    project = relationship("Project", back_populates="risks_challenges")

class ProjectPhaseService(Base):
    __tablename__ = "ProjectPhaseServices"
    service_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey("Projects.project_id"), nullable=False)
    service_name = Column(Text, nullable=False)
    service_description_scope = Column(Text, nullable=True)
    service_start_date = Column(Date, nullable=True)
    service_end_date = Column(Date, nullable=True)

    project = relationship("Project", back_populates="phase_services")

# --- New Tables for Hierarchical Project Categorization ---

class PrimarySector(Base):
    __tablename__ = "PrimarySectors"
    sector_id = Column(Integer, primary_key=True, autoincrement=True)
    sector_name = Column(VARCHAR(255), nullable=False, unique=True)
    sector_description = Column(Text, nullable=True)

    sub_categories = relationship("ProjectSubCategory", back_populates="primary_sector")

class ProjectSubCategory(Base):
    __tablename__ = "ProjectSubCategories"
    sub_category_id = Column(Integer, primary_key=True, autoincrement=True)
    sector_id = Column(Integer, ForeignKey("PrimarySectors.sector_id"), nullable=True)
    parent_sub_category_id = Column(Integer, ForeignKey("ProjectSubCategories.sub_category_id"), nullable=True)
    sub_category_name = Column(VARCHAR(255), nullable=False, unique=True)
    sub_category_code = Column(VARCHAR(50), nullable=True, unique=True)
    sub_category_description = Column(Text, nullable=True)

    primary_sector = relationship("PrimarySector", back_populates="sub_categories")
    parent_category = relationship("ProjectSubCategory", remote_side=[sub_category_id], back_populates="child_categories")
    child_categories = relationship("ProjectSubCategory", back_populates="parent_category")
    project_assignments = relationship("ProjectCategoryAssignment", back_populates="sub_category")

class ProjectCategoryAssignment(Base): # Association Table
    __tablename__ = "ProjectCategoryAssignment"
    project_id = Column(Integer, ForeignKey("Projects.project_id"), primary_key=True)
    sub_category_id = Column(Integer, ForeignKey("ProjectSubCategories.sub_category_id"), primary_key=True)
    assignment_notes = Column(Text, nullable=True)

    project = relationship("Project", back_populates="category_assignments")
    sub_category = relationship("ProjectSubCategory", back_populates="project_assignments")

# --- New Table for Simple Extraction Logging ---

class ProjectExtractionLog(Base):
    __tablename__ = "ProjectExtractionLog"
    log_entry_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    project_id: Mapped[int] = mapped_column(Integer, ForeignKey("Projects.project_id"), nullable=False, index=True)
    log_entry_title: Mapped[Optional[str]] = mapped_column(String)
    log_entry_content: Mapped[str] = mapped_column(Text, nullable=False)
    refined_log_entry_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    source_document_name: Mapped[Optional[str]] = mapped_column(String(255))
    log_entry_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlfunc.now()
    )
    # New fields for LLM verification details
    llm_verification_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g., link_to_existing, create_new
    llm_verification_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_verification_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="extraction_logs")
    tags: Mapped[List["ProjectExtractionLogTag"]] = relationship(back_populates="log_entry", cascade="all, delete-orphan")


class ProjectExtractionLogTag(Base):
    __tablename__ = "ProjectExtractionLogTags" # Pluralized for convention
    tag_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    log_entry_id: Mapped[int] = mapped_column(Integer, ForeignKey("ProjectExtractionLog.log_entry_id"), nullable=False, index=True)
    tag_name: Mapped[str] = mapped_column(String(100), nullable=False) # Max length for tag
    tag_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlfunc.now()
    )

    log_entry: Mapped["ProjectExtractionLog"] = relationship(back_populates="tags")

    # Add a unique constraint to prevent duplicate tags for the same log entry
    __table_args__ = (UniqueConstraint('log_entry_id', 'tag_name', name='uq_log_entry_tag'),)

class DocumentProcessingAuditLog(Base):
    __tablename__ = "DocumentProcessingAuditLog"
    audit_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    document_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("Documents.document_id", ondelete="SET NULL"), nullable=True, index=True)
    source_document_name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    processing_stage: Mapped[Optional[str]] = mapped_column(String(100), nullable=True) # e.g., "initial_name_spotting", "mention_verification"
    raw_mention: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_action: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    llm_confirmed_project_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    llm_project_id_linked: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("Projects.project_id", ondelete="SET NULL"), nullable=True, index=True)
    llm_suggested_tags: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # Stored as JSON string
    llm_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    llm_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # For any other processing notes or errors
    audit_timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=sqlfunc.now()
    )

    document: Mapped[Optional["Document"]] = relationship()
    project_linked: Mapped[Optional["Project"]] = relationship()

# --- Database Engine Setup and Table Creation (Example) ---

def get_db_engine(db_url: str = "postgresql://db_user:db_password@localhost:5432/project_db"):
    """Creates and returns a SQLAlchemy engine."""
    return create_engine(db_url)

def create_tables(engine):
    """Creates all tables in the database based on the defined models."""
    # Base.metadata.drop_all(bind=engine) # Use with caution: drops all tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables checked/created (including ProjectExtractionLog, ProjectExtractionLogTags, and DocumentProcessingAuditLog).")

if __name__ == '__main__':
    # This is an example of how to create the tables in your database.
    # Ensure your PostgreSQL server is running and accessible via the db_url.
    print("Creating database models...")
    db_url = "postgresql://db_user:db_password@localhost:5432/project_db" # Matches docker-compose
    engine = get_db_engine(db_url)
    
    try:
        print(f"Attempting to connect to database and create tables at {db_url}...")
        # The following will attempt to connect and create tables.
        # It will raise an error if the database is not accessible.
        create_tables(engine)
        print("Tables created successfully (if they didn't exist already).")
        print("Please check your PostgreSQL database.")
    except Exception as e:
        print(f"Error creating tables: {e}")
        print("Please ensure your PostgreSQL container (equinox_project_db_container) is running and accessible.")
        print("You might need to wait a few seconds after starting the container for the DB to be ready.")
        print("Also verify the connection URL, username, password, and database name match your docker-compose.yml.") 