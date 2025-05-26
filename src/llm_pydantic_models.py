# src/llm_pydantic_models.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import logging

# Setup logger for this module
logger = logging.getLogger(__name__)

class ProjectIdentificationOutput(BaseModel):
    project_name: Optional[str] = None
    equinox_project_number: Optional[str] = None
    document_context_type: Optional[str] = None

class MainExtractionOutput(BaseModel):
    # Fields from MAIN_EXTRACTION_TARGET_FIELDS in llm_handler.py
    # All fields are made Optional as they may or may not be present in any given chunk.
    # List fields are Optional[List[str]] and default to an empty list if None upon validation (or handled in aggregation).
    
    project_name: Optional[str] = None
    equinox_project_number: Optional[str] = None
    client_name: Optional[str] = None
    end_user_name_if_different: Optional[str] = None
    project_location_country: Optional[str] = None
    project_location_specific: Optional[str] = None
    project_status: Optional[str] = None 
    contract_award_date: Optional[str] = None
    project_completion_date_actual_or_estimated: Optional[str] = None
    project_duration_months: Optional[str] = None # Could be int or str, keep str for flexibility from LLM
    contract_value_currency: Optional[str] = None
    contract_value_amount: Optional[str] = None # Could be float or str, keep str
    project_summary_description: Optional[str] = None 
    detailed_scope_of_work: Optional[str] = None 
    project_objectives_goals: Optional[str] = None
    project_outcomes_results_achievements: Optional[str] = None # This was in CONCAT_TEXT_RESPONSE_FIELDS, but conceptually could be a list. For now, string for concatenation.
                                                            # If it was intended as a list in MAIN_EXTRACTION_TARGET_FIELDS, model should be List[str]

    # List fields - ensuring they are handled as lists
    key_personnel_roles_and_names: Optional[List[str]] = Field(default_factory=list)
    technologies_processes_involved: Optional[List[str]] = Field(default_factory=list)
    project_partners_or_key_subcontractors: Optional[List[str]] = Field(default_factory=list)
    key_project_milestones_or_phases: Optional[List[str]] = Field(default_factory=list)
    major_risks_or_challenges_identified: Optional[List[str]] = Field(default_factory=list)
    services_provided_by_equinox: Optional[List[str]] = Field(default_factory=list)

    # Concatenation fields already covered as Optional[str]
    # commercial_model_or_contract_type: Optional[str] = None # Already part of CONCAT_TEXT_RESPONSE_FIELDS

    # Categorization hints
    primary_sector_hint: Optional[str] = None
    sub_category_hint: Optional[str] = None
    specific_type_hint: Optional[str] = None

    # Allow extra fields to be caught if LLM provides more than defined, though it shouldn't with strict prompting.
    # class Config:
    #     extra = "allow" 
    # For now, we assume LLM adheres to requested fields. If it adds extra, they will be ignored by default unless extra = "allow" and we handle them.

class MentionedProjectItem(BaseModel):
    mentioned_project_name: Optional[str] = None
    mentioned_project_number: Optional[str] = None
    mentioned_project_client: Optional[str] = None
    mentioned_project_year_completed: Optional[str] = None
    mentioned_project_location: Optional[str] = None
    mentioned_project_scope_summary: Optional[str] = None
    mentioned_project_technologies_used: Optional[List[str]] = Field(default_factory=list)
    mentioned_project_value_or_capacity: Optional[str] = None
    primary_sector_hint: Optional[str] = None 
    sub_category_hint: Optional[str] = None   
    specific_type_hint: Optional[str] = None  

class BidScanOutput(BaseModel):
    mentioned_executed_projects: List[MentionedProjectItem] = Field(default_factory=list)


# Example Usage (for testing this file directly)
if __name__ == "__main__":
    # Configure basic logging for direct script execution
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Test ProjectIdentificationOutput
    logger.info("--- Testing ProjectIdentificationOutput ---")
    valid_id_data = {
        "equinox_project_number": "EPN-123",
        "project_name": "Project Alpha",
        "document_context_type": "Project Execution Plan"
    }
    try:
        id_output = ProjectIdentificationOutput(**valid_id_data)
        # print("ProjectIdentificationOutput valid:", id_output.model_dump_json(indent=2))
        logger.info(f"ProjectIdentificationOutput valid:\n{id_output.model_dump_json(indent=2)}")
    except Exception as e:
        # print("ProjectIdentificationOutput error:", e)
        logger.error(f"ProjectIdentificationOutput error:\n{e}", exc_info=True)

    partial_id_data = {"project_name": "Project Beta"} # Missing fields should be None
    try:
        id_output_partial = ProjectIdentificationOutput(**partial_id_data)
        # print("ProjectIdentificationOutput (partial) valid:", id_output_partial.model_dump_json(indent=2))
        logger.info(f"ProjectIdentificationOutput (partial) valid:\n{id_output_partial.model_dump_json(indent=2)}")
        if id_output_partial.equinox_project_number is None:
            # print("Project number is correctly None")
            logger.info("Project number is correctly None for partial ID test.")
    except Exception as e:
        # print("ProjectIdentificationOutput (partial) error:", e)
        logger.error(f"ProjectIdentificationOutput (partial) error:\n{e}", exc_info=True)

    # Test MainExtractionOutput
    logger.info("--- Testing MainExtractionOutput ---")
    valid_main_data = {
        "project_name": "Gamma Ray Project",
        "client_name": "Client X",
        "project_description": "A very important project about gamma rays.",
        "services_provided": ["Engineering", "Design"],
        "key_technologies_used": ["Gamma Emitters", "Lead Shielding"],
        "project_value_usd": 1000000.50,
        "primary_sector_hint": "Energy"
    }
    try:
        main_output = MainExtractionOutput(**valid_main_data)
        # print("MainExtractionOutput valid:", main_output.model_dump_json(indent=2))
        logger.info(f"MainExtractionOutput valid:\n{main_output.model_dump_json(indent=2)}")
        # print(f"Technologies: {main_output.key_technologies_used}")
        logger.info(f"Technologies from MainExtractionOutput: {main_output.key_technologies_used}")
    except Exception as e:
        # print("MainExtractionOutput error:", e)
        logger.error(f"MainExtractionOutput error:\n{e}", exc_info=True)

    # Test BidScanOutput
    logger.info("--- Testing BidScanOutput ---")
    valid_bid_data = {
        "mentioned_executed_projects": [
            {
                "mentioned_project_name": "Old Project Zeta",
                "mentioned_project_number": "OP-Zeta-001",
                "mentioned_project_client": "Past Client Inc.",
                "mentioned_project_year_completed": "2020",
                "mentioned_project_technologies_used": ["Old Tech", "Very Old Tech"]
            },
            {
                "mentioned_project_name": "Another Old One",
                "mentioned_project_scope_summary": "Did lots of things."
            }
        ]
    }
    try:
        bid_output = BidScanOutput(**valid_bid_data)
        # print("BidScanOutput valid:", bid_output.model_dump_json(indent=2))
        logger.info(f"BidScanOutput valid:\n{bid_output.model_dump_json(indent=2)}")
        if bid_output.mentioned_executed_projects:
            # print(f"First mentioned project: {bid_output.mentioned_executed_projects[0].mentioned_project_name}")
            logger.info(f"First mentioned project: {bid_output.mentioned_executed_projects[0].mentioned_project_name}")
            # print(f"First mentioned project techs: {bid_output.mentioned_executed_projects[0].mentioned_project_technologies_used}")
            logger.info(f"First mentioned project techs: {bid_output.mentioned_executed_projects[0].mentioned_project_technologies_used}")
    except Exception as e:
        # print("BidScanOutput error:", e)
        logger.error(f"BidScanOutput error:\n{e}", exc_info=True)

    empty_bid_data = {"mentioned_executed_projects": []}
    try:
        bid_output_empty = BidScanOutput(**empty_bid_data)
        # print("BidScanOutput (empty) valid:", bid_output_empty.model_dump_json(indent=2))
        logger.info(f"BidScanOutput (empty) valid:\n{bid_output_empty.model_dump_json(indent=2)}")
    except Exception as e:
        # print("BidScanOutput (empty) error:", e)
        logger.error(f"BidScanOutput (empty) error:\n{e}", exc_info=True)

    logger.info("--- Pydantic Model Testing Complete ---") 