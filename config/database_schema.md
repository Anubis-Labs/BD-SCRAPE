# Database Schema: Engineering Project Data


This document outlines the proposed database schema for storing extracted project information.


## Core Principles
*   **Normalization:** Aim for a reasonable level of normalization to reduce data redundancy and improve data integrity.
*   **Flexibility:** Design tables and fields to accommodate missing data, as not all information will be present in every document.
*   **Queryability:** Structure data to facilitate querying for insights and reporting.


## Table: `Projects`
This is the central table, holding general information about each engineering project.


*   `project_id` (Primary Key, SERIAL) - Unique identifier for the project.
*   `project_name` (TEXT, NOT NULL) - Official name of the project.
*   `equinox_project_number` (VARCHAR(255), UNIQUE) - Internal project number at Equinox.
*   `project_alias_alternate_names` (TEXT) - Any other names or codes used for the project.
*   `project_description_short` (TEXT) - A brief summary or abstract of the project.
*   `project_description_long` (TEXT) - A more detailed description of the project scope and objectives.
*   `project_status` (VARCHAR(100)) - e.g., "Proposal", "Ongoing", "Completed", "On Hold", "Cancelled".
*   `project_type` (VARCHAR(255)) - e.g., "EPCM", "Feasibility Study", "Detailed Design", "Construction Management".
*   `industry_sector` (VARCHAR(255)) - e.g., "Oil & Gas Upstream", "Midstream", "Downstream", "Petrochemical", "Renewables".
*   `start_date_planned` (DATE) - Planned start date.
*   `end_date_planned` (DATE) - Planned end date.
*   `start_date_actual` (DATE) - Actual start date.
*   `end_date_actual` (DATE) - Actual end date.
*   `project_duration_days` (INTEGER) - Calculated or stated duration.
*   `overall_project_value_budget` (DECIMAL(18,2)) - Estimated or budgeted total project value.
*   `overall_project_value_actual` (DECIMAL(18,2)) - Actual total project value.
*   `currency_code` (VARCHAR(3)) - e.g., "USD", "CAD".
*   `main_contract_type` (VARCHAR(255)) - e.g., "Lump Sum", "Cost Plus", "Unit Rate".
*   `project_complexity` (VARCHAR(50)) - e.g., "Low", "Medium", "High", "Very High".
*   `strategic_importance` (VARCHAR(50)) - e.g., "Key Client", "New Market Entry", "High Profile".
*   `internal_project_link` (TEXT, NULLABLE) - Link to internal repository (e.g., SharePoint, network drive).
*   `project_category` (VARCHAR(100), NULLABLE) - e.g., "Greenfield", "Brownfield", "Expansion", "Maintenance".
*   `project_size_category` (VARCHAR(50), NULLABLE) - e.g., "Small", "Medium", "Large" (can complement actual value).
*   `project_management_approach` (VARCHAR(100), NULLABLE) - e.g., "Agile", "Waterfall", "Hybrid".
*   `total_manhours` (INTEGER, NULLABLE) - Estimated or actual total manhours for the project.
*   `facility_type` (VARCHAR(255), NULLABLE) - Type of facility (e.g., "Sour Gas Plant", "Stabilization Facility", "Wellpad Development", "Compressor Station", "CCS Facility", "Hydrogen Production Plant", "Pipeline System", "Amine Treating Unit", "Water Treatment Plant", "Power Generation Facility").
*   `project_narrative_log` (TEXT, NULLABLE) - A running log or concatenated summary of key information extracted over time for this project, forming a single textual source of truth.
*   `created_at` (TIMESTAMP WITH TIME ZONE, DEFAULT CURRENT_TIMESTAMP)
*   `updated_at` (TIMESTAMP WITH TIME ZONE, DEFAULT CURRENT_TIMESTAMP)


## Table: `Clients`
Information about the clients for whom projects are undertaken.


*   `client_id` (Primary Key, SERIAL) - Unique identifier for the client.
*   `client_name` (VARCHAR(255), NOT NULL, UNIQUE) - Official name of the client company.
*   `client_industry` (VARCHAR(255)) - Industry of the client.
*   `client_country` (VARCHAR(100))
*   `client_contact_person` (VARCHAR(255))
*   `client_relationship_type` (VARCHAR(100)) - e.g., "New Client", "Repeat Client".


## Table: `ProjectClients` (Junction Table)
Links projects to clients (many-to-many, though often one primary client).


*   `project_id` (Foreign Key to `Projects.project_id`)
*   `client_id` (Foreign Key to `Clients.client_id`)
*   `role` (VARCHAR(100)) - e.g., "Primary Client", "Partner", "End User".
*   PRIMARY KEY (`project_id`, `client_id`, `role`)


## Table: `Locations`
Geographical locations related to projects.


*   `location_id` (Primary Key, SERIAL) - Unique identifier for the location.
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `latitude` (DECIMAL(9,6), NULLABLE) - GPS latitude.
*   `longitude` (DECIMAL(10,6), NULLABLE) - GPS longitude.
*   `land_survey_identifier` (TEXT, NULLABLE) - Land survey system coordinates (e.g., DLS in Alberta: "W5-25-16-W4", PLSS in US, etc.).
*   `location_type` (VARCHAR(100)) - e.g., "Project Site", "Well Site", "Facility Location", "Right-of-Way".


## Table: `Documents`
Metadata about the source documents from which information is extracted.


*   `document_id` (Primary Key, SERIAL) - Unique identifier for the document.
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `file_name` (TEXT, NOT NULL) - Original name of the document file.
*   `file_path` (TEXT, NOT NULL, UNIQUE) - Full path to the document file.
*   `document_type` (VARCHAR(50)) - e.g., "PPTX", "PDF", "DOCX", "RFP", "Image", "Design Basis Memorandum (DBM)", "P&ID", "Plot Plan", "Datasheet".
*   `document_title_extracted` (TEXT) - Title extracted from the document, if available.
*   `author_extracted` (TEXT) - Author extracted from document metadata.
*   `creation_date_extracted` (DATE) - Creation date from document metadata.
*   `last_modified_date_extracted` (DATE) - Last modified date from document metadata.
*   `number_of_pages_slides` (INTEGER)
*   `extraction_status` (VARCHAR(50)) - e.g., "Pending", "Processed", "Error".
*   `last_processed_at` (TIMESTAMP WITH TIME ZONE)


## Table: `ProjectKeyInformation`
Stores specific key-value pairs or categorized information extracted by the LLM. This table provides flexibility for diverse data points.


*   `info_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `document_id` (Foreign Key to `Documents.document_id`, NULLABLE) - Source document if specific to one.
*   `info_category` (VARCHAR(255), NOT NULL) - e.g., "ScopeOfWorkItem", "TechnologyApplied", "ProjectDriverObjective", "Challenge", "SolutionImplementedForChallenge", "LessonLearned", "KeyPersonnelName", "EngineeringDiscipline", "EquipmentUsedInProject", "MaterialUsed", "SafetyIncident", "OperationalCapacity", "KeyPerformanceIndicator", "FeedstockProperty", "InnovationHighlight", "ValueEngineeringOutcome", "EnvironmentalMitigationFeature", "SoundAttenuationMeasure", "ModularizationStrategy", "ManagementOfChangeRationale", "SubcontractorOrPartner", "KeyDeliverable", "ESGAspect", "FinalResult", "ClientFeedback", "AwardRecognition", "FuturePotential", "VersionControlSystem", "ReferenceContact", "DocumentationAvailable".
*   `info_item` (TEXT, NOT NULL) - The actual piece of information (e.g., "Crude Oil Desalting Unit", "HAZOP Study Completion", "John Doe", "Civil Engineering", "100 MMSCFD Gas Output", "Application of HYSYS for simulation", "Reduced CAPEX by 10% through design optimization").
*   `info_details_qualifier` (TEXT) - Further details, context, or sub-categorization for the item (e.g., "Capacity: 50,000 BPD" for equipment, "Project Manager" for personnel, "Achieved US$24/tonne CO2 capture cost" for KPI, "Due to unforeseen ground conditions" for Challenge, "Implemented alternative foundation design" for Solution).
*   `source_page_reference` (VARCHAR(50)) - Page or slide number in the source document.
*   `confidence_score_llm` (FLOAT) - If the LLM provides a confidence score for the extraction.


## Table: `Technologies`
A more structured table for distinct technologies, processes, major equipment types, critical methodologies, and digital systems relevant to EPCM and Oil & Gas projects. This table acts as a catalog of unique technological items.


*   `technology_id` (Primary Key, SERIAL)
*   `technology_name` (VARCHAR(255), NOT NULL, UNIQUE) - The common or specific name of the technology, process, equipment, or system (e.g., "Steam Assisted Gravity Drainage (SAGD)", "Delayed Coking Unit Process", "UOP Merox Process", "GE Frame 7FA Gas Turbine", "Advanced Composite Piping Systems", "Modular Skid-Mounted Construction", "AVEVA E3D for Plant Design", "Emerson DeltaV DCS").
*   `technology_type` (VARCHAR(100)) - e.g., "Core Process Technology", "Major Processing Unit", "Specialized Equipment", "Advanced Material", "Construction/Fabrication Methodology", "Digital Technology", "Engineering Software Platform", "Industry Standard".
*   `technology_version` (VARCHAR(100), NULLABLE) - Specific version, model, revision, or grade if applicable (e.g., for software, equipment models, material grades, standard revisions).
*   `technology_domain` (VARCHAR(255), NULLABLE) - Broader classification or engineering area (e.g., "Enhanced Oil Recovery (EOR)", "Heavy Oil Upgrading", "Gas Compression & Transportation", "Pipeline Integrity", "Process Control & Automation", "Materials Science", "Offshore Structures", "Carbon Capture & Sequestration (CCS)").
*   `primary_purpose_or_application` (TEXT, NULLABLE) - A brief description of what this technology is primarily used for (e.g., "In-situ bitumen extraction from oil sands", "Thermal cracking of heavy residues", "Removal of mercaptans from LPG streams", "High-efficiency power generation for large facilities", "Corrosion-resistant piping for sour service").
*   `vendor_manufacturer` (VARCHAR(255), NULLABLE) - Key vendor, licensor, OEM, or manufacturer if applicable.
*   `description` (TEXT, NULLABLE) - More general description or notes about the technology itself, its advantages, or typical use cases.


## Table: `ProjectTechnologies` (Junction Table)
Links projects to specific technologies.


*   `project_id` (Foreign Key to `Projects.project_id`)
*   `technology_id` (Foreign Key to `Technologies.technology_id`)
*   `application_notes` (TEXT) - How this technology was used or applied in this specific project.
*   `info_category` (VARCHAR(255), NOT NULL) - e.g., "ScopeOfWorkItem", "TechnologyApplied", "ProjectObjective", "Challenge", "Solution", "LessonLearned", "KeyPersonnelName", "EngineeringDiscipline", "EquipmentUsedInProject", "MaterialUsed", "SafetyIncident", "OperationalCapacity", "SubcontractorOrPartner", "KeyDeliverable", "InnovationIntroduced", "ProjectMetric", "RegulatoryPermit", "QAStandard", "SafetyMeasure", "SafetyStatistic", "EnvironmentalConsideration", "ESGAspect", "FinalResult", "ClientFeedback", "AwardRecognition", "FuturePotential", "VersionControlSystem", "ReferenceContact", "DocumentationAvailable".
*   `info_item` (TEXT, NOT NULL) - The actual piece of information (e.g., "Crude Oil Desalting Unit", "HAZOP Study Completion", "John Doe", "Civil Engineering", "100 MMSCFD Gas Output", "Application of HYSYS for simulation").
*   `info_details_qualifier` (TEXT) - Further details, context, or sub-categorization for the item (e.g., "Capacity: 50,000 BPD" for equipment, "Project Manager" for personnel, "Achieved 95% on-time delivery" for a metric, "ISO 9001:2015 Certified" for QA standard, "Version 11.2 used for X module" for TechnologyApplied).
*   PRIMARY KEY (`project_id`, `technology_id`)


## Table: `ProjectPersonnelRoles`
Key personnel involved in the project and their roles. This can also be captured in `ProjectKeyInformation` but a dedicated table allows for more structured queries on roles and people.


*   `personnel_role_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `person_name` (VARCHAR(255))
*   `role_on_project` (VARCHAR(255)) - e.g., "Project Manager", "Lead Process Engineer", "Client Representative".
*   `organization_affiliation` (VARCHAR(255)) - (e.g., "Equinox", "Client XYZ", "Subcontractor ABC").
*   `contact_details` (TEXT) - e.g., email, phone (if appropriate and available).


## Table: `Partners`
Information about subcontractors, joint venture partners, or other key external organizations.


*   `partner_id` (Primary Key, SERIAL) - Unique identifier for the partner.
*   `partner_name` (VARCHAR(255), NOT NULL, UNIQUE) - Official name of the partner organization.
*   `partner_type` (VARCHAR(100)) - e.g., "Subcontractor", "Joint Venture Partner", "Consultant", "Vendor".
*   `contact_info` (TEXT) - Key contact person, email, phone for the partner organization.
*   `description` (TEXT) - Brief description of the partner or their typical services.


## Table: `ProjectPartners` (Junction Table)
Links projects to partners involved.


*   `project_partner_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `partner_id` (Foreign Key to `Partners.partner_id`)
*   `role_on_project` (TEXT) - Specific role, scope of work, or services provided by the partner on this project.
*   `notes` (TEXT) - Additional notes about this partnership for the project.


## Table: `ProjectFinancials`
High-level financial data points associated with a project.


*   `financial_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `financial_category` (VARCHAR(255), NOT NULL) - e.g., "TotalBudget", "EngineeringCost", "EquipmentProcurementCost", "ConstructionCost", "Contingency".
*   `amount` (DECIMAL(18,2), NOT NULL)
*   `currency_code` (VARCHAR(3), NOT NULL) - e.g., "USD", "CAD".
*   `date_recorded` (DATE) - When this financial figure was recorded or relevant.
*   `notes` (TEXT)
*   `responsible_party` (VARCHAR(255))


## Table: `ProjectPhasesMilestones`
Significant phases or milestones within a project lifecycle.


*   `milestone_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `milestone_name_description` (TEXT, NOT NULL) - e.g., "Feasibility Study Approved", "Detailed Design Complete", "Construction Started", "Plant Commissioned".
*   `phase_name` (VARCHAR(255)) - Optional, to group milestones under a phase (e.g., "Design Phase", "Execution Phase").
*   `planned_date` (DATE)
*   `actual_completion_date` (DATE)
*   `status` (VARCHAR(100)) - e.g., "Planned", "In Progress", "Completed", "Delayed".


## Table: `ProjectRisksOrChallenges`
Identified risks, challenges, or significant issues encountered during the project.


*   `item_id` (Primary Key, SERIAL)
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `item_type` (VARCHAR(50), NOT NULL) - "Risk", "Challenge", "Issue", "Opportunity".
*   `description` (TEXT, NOT NULL)
*   `date_identified` (DATE)
*   `impact_assessment` (TEXT) - e.g., "High/Medium/Low", description of potential impact.
*   `response_mitigation_solution` (TEXT)
*   `status` (VARCHAR(100)) - e.g., "Open", "Closed", "Mitigated", "Realized".
*   `responsible_party` (VARCHAR(255))


## Table: `ProjectPhaseServices`
Captures the specific services or project phases Equinox Engineering was responsible for, including sub-categories of work.


*   `service_id` (Primary Key, SERIAL) - Unique identifier for the service/phase entry.
*   `project_id` (Foreign Key to `Projects.project_id`)
*   `service_name` (TEXT, NOT NULL) - Name of the service or project phase Equinox delivered. Examples: "Conceptual Study", "Feasibility Study", "Pre-FEED", "FEED (Front End Engineering Design)", "Design Basis Development/Finalization", "Detailed Engineering Design", "Procurement Services", "Construction Management / Support", "Commissioning & Start-up Assistance", "Management of Change (MOC) Execution / Engineering", "Debottlenecking Study / Services", "HAZOP Facilitation / Safety Review", "Integrity Assessment / Fit-for-Service Evaluation", "Brownfield Tie-in Engineering", "Technology Evaluation / Selection Study", "Regulatory Support / Permitting Assistance", "Operations & Maintenance Engineering Support".
*   `service_description_scope` (TEXT, NULLABLE) - Detailed description of Equinox's specific scope of work for this service/phase.
*   `service_start_date` (DATE, NULLABLE) - Start date of this specific service/phase.
*   `service_end_date` (DATE, NULLABLE) - End date of this specific service/phase.


## Table: `PrimarySectors`
Defines the highest-level project sector categories (Level 1 from `project_categorization_schema.md`).

*   `sector_id` (Primary Key, SERIAL) - Unique identifier for the primary sector.
*   `sector_name` (VARCHAR(255), NOT NULL, UNIQUE) - Name of the primary sector (e.g., "Energy", "Renewable & Sustainable Energy", "Specialized Infrastructure", "Other Industrial Projects").
*   `sector_description` (TEXT, NULLABLE) - Optional description of the sector.

## Table: `ProjectSubCategories`
Defines more granular project sub-categories or specific project types, potentially hierarchical under PrimarySectors (Corresponds to Level 1 sub-points and deeper in `project_categorization_schema.md`).

*   `sub_category_id` (Primary Key, SERIAL) - Unique identifier for the sub-category.
*   `sector_id` (Foreign Key to `PrimarySectors.sector_id`, NULLABLE) - Links to the parent primary sector.
*   `parent_sub_category_id` (Foreign Key to `ProjectSubCategories.sub_category_id`, NULLABLE) - For creating nested sub-categories (e.g., Midstream within Oil & Gas).
*   `sub_category_name` (VARCHAR(255), NOT NULL, UNIQUE) - Name of the sub-category or specific project type (e.g., "Oil & Gas", "Solar Energy", "Gas Processing Plants", "Utility-Scale Solar Farms", "Hyperscale Data Centers").
*   `sub_category_code` (VARCHAR(50), NULLABLE, UNIQUE) - Optional short code or identifier from the schema (e.g., "1.1", "2.1.1").
*   `sub_category_description` (TEXT, NULLABLE) - Optional description.

## Table: `ProjectCategoryAssignment` (Junction Table)
Links projects to their assigned sub-categories. A project might be assigned to multiple specific sub-categories if it spans across them.

*   `project_id` (Foreign Key to `Projects.project_id`)
*   `sub_category_id` (Foreign Key to `ProjectSubCategories.sub_category_id`)
*   PRIMARY KEY (`project_id`, `sub_category_id`)
*   `assignment_notes` (TEXT, NULLABLE) - Any notes specific to why this project is assigned to this category.


## Consolidated List of All Data Fields
*   `project_id` (from Projects, ProjectClients, Locations, Documents, ProjectKeyInformation, ProjectTechnologies, ProjectPersonnelRoles, ProjectPartners, ProjectFinancials, ProjectPhasesMilestones, ProjectRisksOrChallenges, ProjectPhaseServices, ProjectCategoryAssignment)
*   `project_name` (from Projects)
*   `equinox_project_number` (from Projects)
*   `project_alias_alternate_names` (from Projects)
*   `project_description_short` (from Projects)
*   `project_description_long` (from Projects)
*   `project_status` (from Projects)
*   `project_type` (from Projects)
*   `industry_sector` (from Projects)
*   `start_date_planned` (from Projects)
*   `end_date_planned` (from Projects)
*   `start_date_actual` (from Projects)
*   `end_date_actual` (from Projects)
*   `project_duration_days` (from Projects)
*   `overall_project_value_budget` (from Projects)
*   `overall_project_value_actual` (from Projects)
*   `currency_code` (from Projects, ProjectFinancials)
*   `main_contract_type` (from Projects)
*   `project_complexity` (from Projects)
*   `strategic_importance` (from Projects)
*   `internal_project_link` (from Projects)
*   `project_category` (from Projects)
*   `project_size_category` (from Projects)
*   `project_management_approach` (from Projects)
*   `total_manhours` (from Projects)
*   `facility_type` (from Projects)
*   `project_narrative_log` (from Projects)
*   `created_at` (from Projects)
*   `updated_at` (from Projects)
*   `client_id` (from Clients, ProjectClients)
*   `client_name` (from Clients)
*   `client_industry` (from Clients)
*   `client_country` (from Clients)
*   `client_contact_person` (from Clients)
*   `client_relationship_type` (from Clients)
*   `role` (from ProjectClients)
*   `location_id` (from Locations)
*   `latitude` (from Locations)
*   `longitude` (from Locations)
*   `land_survey_identifier` (from Locations)
*   `location_type` (from Locations)
*   `document_id` (from Documents, ProjectKeyInformation)
*   `file_name` (from Documents)
*   `file_path` (from Documents)
*   `document_type` (from Documents)
*   `document_title_extracted` (from Documents)
*   `author_extracted` (from Documents)
*   `creation_date_extracted` (from Documents)
*   `last_modified_date_extracted` (from Documents)
*   `number_of_pages_slides` (from Documents)
*   `extraction_status` (from Documents)
*   `last_processed_at` (from Documents)
*   `info_id` (from ProjectKeyInformation)
*   `info_category` (from ProjectKeyInformation)
*   `info_item` (from ProjectKeyInformation)
*   `info_details_qualifier` (from ProjectKeyInformation)
*   `source_page_reference` (from ProjectKeyInformation)
*   `confidence_score_llm` (from ProjectKeyInformation)
*   `technology_id` (from Technologies, ProjectTechnologies)
*   `technology_name` (from Technologies)
*   `technology_type` (from Technologies)
*   `technology_version` (from Technologies)
*   `technology_domain` (from Technologies)
*   `primary_purpose_or_application` (from Technologies)
*   `vendor_manufacturer` (from Technologies)
*   `description` (from Technologies, Partners, ProjectRisksOrChallenges)
*   `application_notes` (from ProjectTechnologies)
*   `personnel_role_id` (from ProjectPersonnelRoles)
*   `person_name` (from ProjectPersonnelRoles)
*   `role_on_project` (from ProjectPersonnelRoles, ProjectPartners)
*   `organization_affiliation` (from ProjectPersonnelRoles)
*   `contact_details` (from ProjectPersonnelRoles)
*   `partner_id` (from Partners, ProjectPartners)
*   `partner_name` (from Partners)
*   `partner_type` (from Partners)
*   `contact_info` (from Partners)
*   `project_partner_id` (from ProjectPartners)
*   `notes` (from ProjectFinancials, ProjectPartners)
*   `financial_id` (from ProjectFinancials)
*   `financial_category` (from ProjectFinancials)
*   `amount` (from ProjectFinancials)
*   `date_recorded` (from ProjectFinancials)
*   `milestone_id` (from ProjectPhasesMilestones)
*   `milestone_name_description` (from ProjectPhasesMilestones)
*   `phase_name` (from ProjectPhasesMilestones)
*   `planned_date` (from ProjectPhasesMilestones)
*   `actual_completion_date` (from ProjectPhasesMilestones)
*   `status` (from ProjectPhasesMilestones, ProjectRisksOrChallenges)
*   `item_id` (from ProjectRisksOrChallenges)
*   `item_type` (from ProjectRisksOrChallenges)
*   `date_identified` (from ProjectRisksOrChallenges)
*   `impact_assessment` (from ProjectRisksOrChallenges)
*   `response_mitigation_solution` (from ProjectRisksOrChallenges)
*   `responsible_party` (from ProjectRisksOrChallenges)
*   `service_id` (from ProjectPhaseServices)
*   `service_name` (from ProjectPhaseServices)
*   `service_description_scope` (from ProjectPhaseServices)
*   `service_start_date` (from ProjectPhaseServices)
*   `service_end_date` (from ProjectPhaseServices)
*   `sector_id` (from PrimarySectors, ProjectSubCategories)
*   `sector_name` (from PrimarySectors)
*   `sector_description` (from PrimarySectors)
*   `sub_category_id` (from ProjectSubCategories, ProjectCategoryAssignment)
*   `parent_sub_category_id` (from ProjectSubCategories)
*   `sub_category_name` (from ProjectSubCategories)
*   `sub_category_code` (from ProjectSubCategories)
*   `sub_category_description` (from ProjectSubCategories)
*   `assignment_notes` (from ProjectCategoryAssignment) 