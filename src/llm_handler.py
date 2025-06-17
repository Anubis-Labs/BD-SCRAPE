# src/llm_handler.py
import requests
import json
import logging
from typing import Dict, Any, List, Optional
# from pydantic import BaseModel, Field # No longer needed for this simplified workflow
from sqlalchemy.orm import Session

# from src import database_crud # No longer directly calling database from here

# Setup logger
logger = logging.getLogger(__name__)
OLLAMA_API_BASE_URL = "http://localhost:11434/api"

def _strip_llm_json_markdown(raw_json_string: str) -> str:
    """Strips markdown code block fences from a string intended to be JSON."""
    return raw_json_string.strip().removeprefix("```json").removesuffix("```").strip()

def call_ollama_generate(model_name: str, prompt_text: str, timeout: int = 240, temperature: float = 0.3) -> Optional[Dict[str, Any]]:
    """Calls the Ollama /api/generate endpoint with retry logic."""
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False,
        "format": "json",
        "options": {"temperature": temperature}
    }
    logger.info(f"Sending request to Ollama model: {model_name} (prompt length: {len(prompt_text)} chars)")
    try:
        response = requests.post(f"{OLLAMA_API_BASE_URL}/generate", json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Ollama API call failed: {e}", exc_info=True)
        return None

def get_available_ollama_models() -> List[str]:
    """Fetches the list of available Ollama models."""
    try:
        response = requests.get(f"{OLLAMA_API_BASE_URL}/tags")
        response.raise_for_status()
        models_data = response.json()
        return sorted([model['name'] for model in models_data.get('models', [])])
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching Ollama models: {e}", exc_info=True)
        return []

def find_project_names_in_chunk(model_name: str, text_chunk: str) -> List[str]:
    """
    Uses an LLM to extract possible project name mentions from a small chunk of text.
    """
    prompt = f"""
You are an AI assistant for an engineering company. Your task is to identify and extract the names of specific engineering or construction projects from the text provided below.

INSTRUCTIONS:
- Scan the text for proper nouns that appear to be project names (e.g., "Kaybob South Gas Plant", "West Doe Battery").
- Do NOT extract generic terms like "the project" or "the facility" unless they are part of a specific name.
- Return your answer in JSON format with a single key "project_names", which contains a list of the names you found.
- If no project names are found, return an empty list: {{"project_names": []}}

TEXT TO ANALYZE:
---
{text_chunk}
---

JSON Response:
"""
    response_data = call_ollama_generate(model_name, prompt, temperature=0.1)
    if response_data and "response" in response_data:
        try:
            parsed_json = json.loads(_strip_llm_json_markdown(response_data["response"]))
            names = parsed_json.get("project_names", [])
            if isinstance(names, list):
                # Clean and filter the names
                return sorted(list(set([str(name).strip() for name in names if name and isinstance(name, str) and len(name.strip()) > 3])))
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse project names from LLM response: {e}")
    return []

def extract_relevant_snippet(model_name: str, text_chunk: str, project_name: str) -> Optional[str]:
    """
    Given a chunk of text and a project name, extracts the verbatim paragraph(s)
    related to that specific project.
    """
    prompt = f"""
You are an AI assistant. Your task is to extract the verbatim text related to a specific project from the document chunk provided below.

INSTRUCTIONS:
- The project you are looking for is named: "{project_name}"
- Find the paragraph or section in the "DOCUMENT CHUNK" that discusses this project.
- Extract this text *exactly* as it appears in the document, without any modification, summarization, or added commentary.
- Respond in JSON format with a single key "snippet" containing the verbatim text you extracted.
- If you cannot find a relevant snippet for "{project_name}", return null for the snippet value.

DOCUMENT CHUNK:
---
{text_chunk}
---

JSON Response (only the snippet for "{project_name}"):
"""
    response_data = call_ollama_generate(model_name, prompt, temperature=0.0) # Temperature is 0.0 for deterministic extraction
    if response_data and "response" in response_data:
        try:
            parsed_json = json.loads(_strip_llm_json_markdown(response_data["response"]))
            snippet = parsed_json.get("snippet")
            if snippet and isinstance(snippet, str):
                return snippet.strip()
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Failed to parse snippet from LLM response: {e}")
    return None

def categorize_project(llm_model: str, project_text_content: str) -> Dict[str, str]:
    """
    Analyzes project text content to determine its category, sub-category, and scope.

    Args:
        llm_model: The name of the LLM model to use.
        project_text_content: The aggregated text data of the project.

    Returns:
        A dictionary containing 'category', 'sub_category', and 'project_scope'.
    """
    logger.info("Starting project categorization...")

    # For clarity and to ensure the AI has the full context, we load the schema.
    try:
        with open("config/project_categorization_schema.md", "r") as f:
            schema_text = f.read()
    except FileNotFoundError:
        logger.error("FATAL: project_categorization_schema.md not found in config/ directory.")
        # Return empty if schema is missing, as categorization is impossible.
        return {"category": "", "sub_category": "", "project_scope": ""}

    system_prompt = f"""
You are an expert EPCM (Engineering, Procurement, and Construction Management) project classifier. 
Your task is to analyze the provided project text and assign it a `category`, `sub_category`, and `project_scope` based *only* on the official schema provided below.

**OFFICIAL SCHEMA:**
{schema_text}

**Instructions:**
1.  Read the project text carefully.
2.  Compare the text against the categories, sub-categories, and scopes in the official schema.
3.  Choose the BEST and MOST SPECIFIC `category` and `sub_category` that fits the project description.
4.  Determine the MOST ACCURATE `project_scope`.
5.  If no sub-category is applicable for a chosen category, return an empty string for `sub_category`.
6.  If the text is ambiguous or lacks information, make the best possible choice but do not invent new classifications.
7.  Your output MUST be a JSON object with three keys: "category", "sub_category", and "project_scope".
"""

    prompt = f"""
**Project Text to Analyze:**
---
{project_text_content[:8000]} 
---

Based on the official schema, please classify this project.
"""

    try:
        response_data = call_ollama_generate(
            model_name=llm_model,
            prompt_text=f"{system_prompt}\n\n{prompt}",
            temperature=0.0
        )

        if response_data and "response" in response_data:
            raw_response_str = response_data["response"]
            logger.info(f"Raw LLM response for categorization: {raw_response_str}")
            # If Ollama returns a string, it's likely a JSON string. Parse it.
            try:
                parsed_data = json.loads(_strip_llm_json_markdown(raw_response_str))
            except json.JSONDecodeError:
                logger.error(f"Failed to decode JSON string from Ollama: {raw_response_str}")
                return {"category": "Uncategorized", "sub_category": "", "project_scope": "Unclassified"}
        else:
            logger.warning(f"No valid 'response' in Ollama output. Full response: {response_data}")
            parsed_data = {}

        # Validate the response keys
        category = parsed_data.get("category", "Uncategorized")
        sub_category = parsed_data.get("sub_category", "")
        project_scope = parsed_data.get("project_scope", "Unclassified")

        logger.info(f"Project successfully categorized as: {category} / {sub_category} / {project_scope}")
        return {"category": category, "sub_category": sub_category, "project_scope": project_scope}

    except Exception as e:
        logger.error(f"An error occurred during project categorization: {e}", exc_info=True)
        return {"category": "Uncategorized", "sub_category": "", "project_scope": "Error"}

# --- OLD, DEPRECATED FUNCTIONS ARE COMMENTED OUT BELOW ---
#
# class ProjectVerificationEnrichmentOutput(BaseModel):
#     action: str = Field(description="Action to take: 'link_to_existing', 'create_new', 'uncertain_relevance', or 'not_equinox_project'.")
#     project_id: Optional[int] = Field(None)
#     confirmed_project_name: Optional[str] = Field(None)
#     pertinent_text: Optional[str] = Field(None)
#     suggested_tags: List[str] = Field(default_factory=list)
#     confidence_score: Optional[float] = Field(None)
#     reasoning: Optional[str] = Field(None)
#
# def enrich_and_verify_project_context(
#     model_name: str, full_document_text: str, raw_name_mention: str, db_session: Session
# ) -> Optional[ProjectVerificationEnrichmentOutput]:
#     """Uses an LLM to verify a project mention against existing DB projects."""
#     logger.info(f"Fetching candidate projects from DB for mention: '{raw_name_mention}'")
#     candidate_projects = database_crud.find_project_by_name_or_alias_for_verification(db_session, raw_name_mention)
#     ... (rest of function) ...
#
# def extract_all_document_data_verbatim(model_name: str, document_text: str, document_filename: str = "") -> Optional[Dict[str, Any]]:
#     """Uses an LLM to extract a comprehensive set of data points from the document."""
#     logger.info(f"Starting comprehensive data extraction for {document_filename}...")
#     ... (rest of function) ... 