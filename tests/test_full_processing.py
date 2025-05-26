import logging
from src.main_processor import process_documents

# Set up logging to see what happens
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(module)s - %(message)s')

print("Testing full document processing with fixed LLM extraction...")
print("Processing: EQC - Amine - Brownfield & Greenfield Experience.docx")
print("="*60)

try:
    process_documents('gemma3:12b', 'EQC - Amine - Brownfield & Greenfield Experience.docx', upload_dir='upload_folder/temp_uploads')
    print("="*60)
    print("Processing completed!")
    
    # Check what projects were created
    from src.database_crud import get_session
    from src.database_models import Project, ProjectExtractionLog
    
    session = get_session()
    projects = session.query(Project).all()
    print(f"\nFound {len(projects)} projects in database:")
    for project in projects:
        print(f"  - ID: {project.project_id}, Name: '{project.project_name}'")
        
        # Check extraction logs for this project
        logs = session.query(ProjectExtractionLog).filter_by(project_id=project.project_id).all()
        print(f"    Extraction logs: {len(logs)}")
        for log in logs:
            print(f"      * {log.log_entry_title}")
    
    session.close()
    
except Exception as e:
    print(f"Error during processing: {e}")
    import traceback
    traceback.print_exc() 