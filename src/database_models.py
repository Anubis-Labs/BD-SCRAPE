# src/database_models.py

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, TIMESTAMP, UniqueConstraint
from sqlalchemy.orm import declarative_base, sessionmaker, Mapped, mapped_column
from sqlalchemy.sql import func as sqlfunc
import datetime
import logging
import os
from dotenv import load_dotenv
from typing import Optional

logger = logging.getLogger(__name__)

Base = declarative_base()

# --- New, Simplified Project Model for Snippet Aggregation ---

class Project(Base):
    __tablename__ = "Projects"

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    
    # New Fields for Categorization
    category: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    sub_category: Mapped[Optional[str]] = mapped_column(String(255), index=True)
    project_scope: Mapped[Optional[str]] = mapped_column(String(255), index=True)

    aggregated_data: Mapped[str] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        server_default=sqlfunc.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        TIMESTAMP(timezone=True), 
        server_default=sqlfunc.now(), 
        onupdate=sqlfunc.now()
    )

    def __repr__(self):
        return f"<Project(project_id={self.project_id}, project_name='{self.project_name}')>"

# --- All previous model classes are commented out below to preserve them ---
# --- while we implement the new, simplified data aggregation workflow. ---

# class Project(Base):
#     __tablename__ = "Projects"

#     project_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
#     project_name: Mapped[str] = mapped_column(Text, nullable=False)
#     equinox_project_number: Mapped[Optional[str]] = mapped_column(VARCHAR(255), unique=True, nullable=True)
#     ... (rest of the old Project class) ...

# class Client(Base):
#     __tablename__ = "Clients"
#     ... (and so on for all other classes) ...

def get_db_engine(db_url: str | None = None):
    """
    Creates and returns a SQLAlchemy engine instance.
    It constructs the database URL from environment variables if not provided.
    """
    if db_url:
        final_db_url = db_url
    else:
        load_dotenv()
        db_user = os.getenv("POSTGRES_USER")
        db_password = os.getenv("POSTGRES_PASSWORD")
        db_host = os.getenv("POSTGRES_HOST", "localhost")
        db_port = os.getenv("POSTGRES_PORT", "5432")
        db_name = os.getenv("POSTGRES_DB")

        if not all([db_user, db_password, db_host, db_port, db_name]):
            msg = "One or more database environment variables are not set."
            logger.error(msg)
            raise ValueError(msg)
        
        final_db_url = f"postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"

    try:
        engine = create_engine(final_db_url, pool_size=5, max_overflow=10)
        logger.info(f"Database engine created for URL: postgresql://{db_user}:***@{db_host}:{db_port}/{db_name}")
        return engine
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}", exc_info=True)
        raise

def create_tables(engine):
    """
    Creates all tables defined in the Base metadata.
    This function will now only create the single, simplified 'Projects' table.
    """
    try:
        logger.info("Creating database tables...")
        Base.metadata.create_all(engine)
        logger.info("Tables created successfully (if they didn't exist).")
    except Exception as e:
        logger.error(f"An error occurred during table creation: {e}", exc_info=True)
        raise

def get_session(engine=None):
    """
    Creates and returns a new SQLAlchemy session.
    If no engine is provided, it creates a new one.
    """
    if not engine:
        engine = get_db_engine()
    
    Session = sessionmaker(bind=engine)
    return Session() 