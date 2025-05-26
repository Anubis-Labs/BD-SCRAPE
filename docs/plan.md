# Project Plan: Engineering Project Data Extraction and Analysis


## 1. Project Goal
Develop an application to extract information from various project documents (PowerPoint, PDF, Word) from Equinox Engineering, process this information using a locally hosted Ollama LLM, and store it in a PostgreSQL database. The ultimate aim is to create a comprehensive, searchable knowledge base of past project experience to support future project bidding, RFP responses, and internal knowledge sharing.


## 2. Core Technologies
*   **Programming Language:** Python (running directly on host)
*   **LLM:** Locally hosted Ollama (running directly on host)
*   **Database:** PostgreSQL (hosted in a Docker container)
*   **Document Parsers:** Python libraries for PPTX, PDF, DOCX


## 3. Development Phases


### Phase 1: Environment Setup
*   **Task 1.1:** Set up Docker (for PostgreSQL).
    *   Sub-Task 1.1.1: Install Docker Desktop (if not already installed).
    *   Sub-Task 1.1.2: Verify Docker installation and service status.
*   **Task 1.2:** Set up PostgreSQL within a Docker container.
    *   Sub-Task 1.2.1: Create a `docker-compose.yml` file for PostgreSQL.
        *   Define image (e.g., `postgres:latest`).
        *   Map port.
        *   Define volume for persistent data (e.g., `./pgdata:/var/lib/postgresql/data`).
        *   Configure environment variables (`POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`).
    *   Sub-Task 1.2.2: Start container (`docker-compose up -d`).
    *   Sub-Task 1.2.3: Verify PostgreSQL is running and accessible.
*   **Task 1.3:** Set up local Python development environment.
    *   Sub-Task 1.3.1: Create virtual environment (`.venv`).
    *   Sub-Task 1.3.2: Create `requirements.txt`.
    *   Sub-Task 1.3.3: Install initial libraries (e.g., `psycopg2-binary`, `requests`, `SQLAlchemy`, document parsers) and add to `requirements.txt`.
*   **Task 1.4:** Set up Ollama within a Docker container.
    *   Sub-Task 1.4.1: Define Ollama service in `docker-compose.yml` (Done).
        *   Use `ollama/ollama:latest` image.
        *   Map port `11434:11434`.
        *   Define a named volume for model persistence (e.g., `ollama_data_vol:/root/.ollama`).
    *   Sub-Task 1.4.2: Ensure Ollama service starts correctly via `docker-compose up -d`.
    *   Sub-Task 1.4.3: Verify Ollama container is running and API is accessible on `http://localhost:11434`.
    *   Sub-Task 1.4.4: Pull an initial LLM into the Ollama container (e.g., `docker exec -it equinox_ollama_container ollama pull llama3`). This will be done by the user once the container is running.


### Phase 2: Document Parsing and Data Extraction
*   **Task 2.1:** Develop Python scripts/modules for parsing different document types.
    *   Sub-Task 2.1.1: Implement PPTX parser (`python-pptx`).
    *   Sub-Task 2.1.2: Implement PDF parser (`PyPDF2` or `pdfplumber`).
    *   Sub-Task 2.1.3: Implement DOCX parser (`python-docx`).
    *   Sub-Task 2.1.4: Common error handling for parsers.
    *   Sub-Task 2.1.5: Strategy for embedded objects (textual first).
*   **Task 2.2:** Implement logic to traverse project folders.
    *   Sub-Task 2.2.1: Recursive directory scanning (`pathlib`).
    *   Sub-Task 2.2.2: Filtering for relevant file types.
    *   Sub-Task 2.2.3: Tracking processed files to avoid re-processing.
*   **Task 2.3:** Integrate Ollama for information extraction.
    *   Sub-Task 2.3.1: Prompt Engineering (Core Fields & Identifiers).
        *   Iteratively develop prompts for `Projects` table fields and robust project identifiers (`equinox_project_number`, `project_name`).
        *   Experiment with prompts for structured output (e.g., JSON).
    *   **New Sub-Task 2.3.2: Prompt Engineering (Project Categorization).**
        *   Design prompts to guide the LLM in identifying information that maps to `PrimarySectors` and `ProjectSubCategories` (based on `project_categorization_schema.md`).
        *   Include prompts for identifying relevant `Technologies` and `ProjectPhaseServices`.
        *   Prompts should help extract keywords/phrases that Python logic can use to look up category IDs in the database.
    *   Sub-Task 2.3.3: Dynamic Model Selection Integration (from Ollama API `/api/tags`).
    *   Sub-Task 2.3.4: Chunking Strategy for Large Documents.
    *   Sub-Task 2.3.5: Ollama API Interaction Module (robust calls, error handling).
    *   Sub-Task 2.3.6: LLM Response Parsing and Mapping.
        *   Develop Python logic to parse Ollama's responses.
        *   Implement mapping from parsed LLM output to fields in `database_schema.md`, **including new categorization fields.**
*   **Task 2.4:** (Covered by 2.3.6) Define clear mapping from LLM extracted data to database fields.
*   **Task 2.5:** Incremental Project Data Aggregation.
    *   Sub-Task 2.5.1: Develop project matching logic (`equinox_project_number`, normalized `project_name` with fuzzy matching).
    *   Sub-Task 2.5.2: Confidence scoring for name-based matches.
    *   Sub-Task 2.5.3: Data merging logic for existing projects (append narratives, add distinct items, update fields, refresh `updated_at`).
    *   Sub-Task 2.5.4: Handle new project creation if no confident match.
    *   Sub-Task 2.5.5: (Optional) Flagging low-confidence matches for manual review.


### Phase 3: Database Design and Integration
*   **Task 3.1:** Implement Database Interaction Layer using SQLAlchemy (or preferred ORM/library).
    *   Sub-Task 3.1.1: Set up models/table metadata mirroring `database_schema.md`.
        *   Include `Projects`, `Clients`, `Documents`, `Technologies`, etc.
        *   **New:** Include `PrimarySectors`, `ProjectSubCategories`, `ProjectCategoryAssignment`.
    *   Sub-Task 3.1.2: Database connection management.
    *   Sub-Task 3.1.3: Idempotent table creation logic.
    *   **New Sub-Task 3.1.4: Populate Initial Categorization Data.**
        *   Write a script to populate `PrimarySectors` and top-level `ProjectSubCategories` based on `project_categorization_schema.md`. This might be a one-time script or managed through migrations.
    *   Sub-Task 3.1.5: Develop CRUD helper functions for `Projects`, `Documents`.
    *   Sub-Task 3.1.6: Develop CRUD functions for `ProjectKeyInformation`, `Technologies`, `Clients`, junction tables.
    *   **New Sub-Task 3.1.7: Develop CRUD functions for `PrimarySectors`, `ProjectSubCategories`, `ProjectCategoryAssignment`.**
    *   Sub-Task 3.1.8: Implement query logic for project existence checks (for Task 2.5).
    *   **New Sub-Task 3.1.9: Implement logic to map extracted categorization keywords/phrases (from LLM output) to `PrimarySector` IDs and `ProjectSubCategory` IDs and store these links in `ProjectCategoryAssignment`.**
    *   Sub-Task 3.1.10: Implement logic for updating `project_narrative_log`.
    *   Sub-Task 3.1.11: Transaction management.
*   **Task 3.2:** Define and Facilitate Population of Flat Export Table (`ProjectExportFlat`).
    *   Sub-Task 3.2.1: Finalize `ProjectExportFlat` schema.
    *   Sub-Task 3.2.2: Develop Python scripts or PostgreSQL views/materialized views to populate `ProjectExportFlat`.
        *   Ensure new categorization data is included in the flat table.
    *   Sub-Task 3.2.3: Logic for triggering `ProjectExportFlat` population.


### Phase 4: Core Application Development & Workflow
*   **Task 4.1:** Main Application Orchestrator (`main.py`).
    *   Sub-Task 4.1.1: Structure main script (file scan, parse, LLM, DB interaction, flat table population).
    *   Sub-Task 4.1.2: Integrate calls to modules from Phases 2 & 3.
*   **Task 4.2:** Configuration Management (`config.yaml` or `config.ini`).
    *   Sub-Task 4.2.1: Define parameters (paths, API, model, DB, logging).
    *   Sub-Task 4.2.2: Secure handling of sensitive data.
*   **Task 4.3:** Logging and Monitoring (Python `logging` module).
*   **Task 4.4:** Error Handling and Resilience (global, specific, retries, partial success).
*   **Task 4.5:** Intelligent Data Aggregation (ensure end-to-end integration of Task 2.5).


### Phase 5: User Interface Development
*   **Task 5.1:** Develop the primary Graphical User Interface (GUI).
    *   Sub-Task 5.1.1: Technology Selection & Setup (Flask/FastAPI + React/Vue/Svelte, or PyQt/Streamlit).
    *   Sub-Task 5.1.2: Core UI Design and Navigation (wireframes/mockups).
    *   Sub-Task 5.1.3: Input Configuration Components (folder select, Ollama model select).
    *   Sub-Task 5.1.4: Process Control Components ("Start Processing" button).
    *   Sub-Task 5.1.5: Status Display and Logging View.
    *   Sub-Task 5.1.6: Project Data Browser Implementation.
        *   Design table/grid for project list.
        *   Implement data fetching (from `ProjectExportFlat` or dynamic views).
        *   Implement searching and basic filtering.
        *   **New: Implement filtering by `PrimarySectors` and `ProjectSubCategories`.**
    *   **New Sub-Task 5.1.7: Project Detail View.**
        *   Display comprehensive details for a selected project.
        *   **New: Clearly display assigned `PrimarySector`, `ProjectSubCategories`, linked `Technologies`, and `ProjectPhaseServices`.**
    *   Sub-Task 5.1.8: Data Export Functionality (CSV/JSON from `ProjectExportFlat`).
    *   Sub-Task 5.1.9: (Optional) UI for Configuration Settings.
    *   Sub-Task 5.1.10: Styling and Theming (modern aesthetics, dark theme, icons, animations).


### Phase 6: Testing and Refinement
*   **Task 6.1:** Unit tests (parsers, LLM interaction, DB functions, aggregation logic).
*   **Task 6.2:** Integration tests (workflow, updates, flat table population).
*   **Task 6.3:** Manual end-to-end testing (diverse documents, GUI, data verification).
    *   **New: Specifically test accuracy of project categorization against `project_categorization_schema.md`.**
*   **Task 6.4:** Refine LLM prompts iteratively, **especially for categorization accuracy.**
*   **Task 6.5:** Performance review and optimization.


### Phase 7: (Optional) Advanced Semantic Search Capabilities
This phase is reserved for future consideration if the primary data extraction, storage, GUI-based structured querying, and flat export functionalities (Phases 1-6) prove insufficient for advanced knowledge discovery or RFP response needs.


## 4. Future Enhancements
*   Advanced querying and reporting features.
*   Integration with other data sources.
*   More sophisticated NLP techniques.
*   User authentication and access control.
*   Web-based UI for easier interaction and visualization of data (if not chosen initially). 