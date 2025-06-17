# scripts/populate_dummy_data.py
import sys
import os
from sqlalchemy.orm import Session

# Add the project root to the Python path to allow for absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.db_logic import get_session, append_to_project_data
from src.database_models import Base, Project

def populate_data():
    """
    Populates the database with some dummy projects and aggregated data.
    """
    print("--- Starting to populate dummy data ---")
    
    dummy_projects = {
        "Project Alpha": (
            "--- Snippet from 'Initial Report.docx' at 2024-01-15 10:30:00 ---\n\n"
            "Project Alpha will focus on the development of a new solar power generation facility. "
            "The initial phase involves site selection and environmental impact assessment.\n\n"
            "--- Snippet from 'Meeting Notes.pdf' at 2024-02-20 14:00:00 ---\n\n"
            "Discussion on Project Alpha's budget concluded with an approval of the revised funding model. "
            "Key stakeholders from Equinox Engineering are to be assigned by month-end."
        ),
        "Beta Battery Initiative": (
            "--- Snippet from 'Technical Spec.pdf' at 2024-03-01 09:00:00 ---\n\n"
            "The Beta Battery Initiative aims to revolutionize energy storage. "
            "The core technology is based on a proprietary lithium-sulfur chemistry, promising higher density and lower cost."
        ),
        "Gamma Gas Pipeline": (
            "--- Snippet from 'Feasibility Study.pptx' at 2024-04-10 11:45:00 ---\n\n"
            "The Gamma Gas Pipeline project has been deemed viable. The proposed route will minimize environmental disruption "
            "while maximizing delivery efficiency to the western territories. Construction is slated to begin in Q4."
        )
    }

    session: Session = get_session()
    engine = session.get_bind() # Get the engine from the session
    Base.metadata.create_all(engine) # Create tables if they don't exist
    
    try:
        for name, data in dummy_projects.items():
            print(f"Adding data for project: '{name}'")
            # Use a simplified approach: just create/replace the data
            project = session.query(Project).filter(Project.project_name == name).first()
            if project:
                project.aggregated_data = data
            else:
                project = Project(project_name=name, aggregated_data=data)
                session.add(project)
        
        session.commit()
        print("--- Dummy data populated successfully! ---")

    except Exception as e:
        print(f"An error occurred: {e}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    populate_data() 