import requests
import json
from typing import Dict, Any, List, Optional
import logging
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

# Setup logger for this module
logger = logging.getLogger(__name__)

# Default Ollama API endpoint
# This will be http://localhost:11434 when Ollama runs directly on host,
# or http://ollama:11434 if Python code runs in another Docker container
# on the same Docker network as the 'ollama' service.
# For now, assuming direct call from host to Ollama container.
OLLAMA_API_BASE_URL = "http://localhost:11434/api"

# --- Helper function to strip markdown from LLM JSON responses (Moved here) ---
def _strip_llm_json_markdown(raw_json_string: str) -> str:
    """Strips common markdown code block fences from a string intended to be JSON."""
    stripped_string = raw_json_string.strip()
    if stripped_string.startswith("```json"):
        stripped_string = stripped_string[7:] # Remove ```json
        if stripped_string.endswith("```"):
            stripped_string = stripped_string[:-3] # Remove trailing ```
    elif stripped_string.startswith("```"):
        stripped_string = stripped_string[3:] # Remove ```
        if stripped_string.endswith("```"):
            stripped_string = stripped_string[:-3] # Remove trailing ```
    return stripped_string.strip()

def get_available_ollama_models() -> List[str]:
    """Fetches the list of available Ollama models from the local server."""
    try:
        response = requests.get(f"{OLLAMA_API_BASE_URL}/tags")
        response.raise_for_status()
        models_data = response.json()
        return sorted([model['name'] for model in models_data.get('models', [])])
    except requests.exceptions.RequestException as e:
        # print(f"Error fetching Ollama models: {e}")
        logger.error(f"Error fetching Ollama models: {e}", exc_info=True)
        return []

def call_ollama_generate(model_name: str, prompt_text: str, retries: int = 1, timeout: int = 240, temperature: float = 0.3, top_p: float = 0.9) -> Optional[Dict[str, Any]]:
    """
    Calls the Ollama /api/generate endpoint with the given model and prompt.
    Includes basic retry logic and specifies JSON format in request.
    """
    current_retry = 0
    api_url = f"{OLLAMA_API_BASE_URL}/generate"
    payload = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": False,
        "format": "json", # Request JSON output
        "options": {
            "temperature": temperature,
            "top_p": top_p
        }
    }
    logger.info(f"Sending request to Ollama model: {model_name}. Prompt length: {len(prompt_text)} chars. Format: JSON")
    if len(prompt_text) > 1000:
        logger.debug(f"Prompt snippet: {prompt_text[:250]}...{prompt_text[-250:]}")
    else:
        logger.debug(f"Full prompt: {prompt_text}")

    while current_retry <= retries:
        try:
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()
            outer_json = response.json()
            if "response" in outer_json and isinstance(outer_json["response"], str):
                try:
                    logger.info(f"Received response from Ollama model {model_name}. LLM output length: {len(outer_json['response'])}")
                    logger.debug(f"LLM Raw (inner) Response Text Snippet: {outer_json['response'][:200]}...")
                    return {"response": outer_json["response"]}
                except json.JSONDecodeError as je:
                    logger.error(f"Ollama returned content in 'response' field that is not valid JSON: {je}. Content: {outer_json['response'][:500]}")
                    return {"error": "LLM output was not valid JSON despite format request." , "details": outer_json['response'][:500]}
            elif "response" in outer_json:
                logger.error(f"Ollama 'response' field was not a string. Type: {type(outer_json['response'])}. Content: {str(outer_json['response'])[:500]}")
                return {"error": "Ollama 'response' field was not a string as expected.", "details": str(outer_json['response'])[:500]}
            else:
                logger.error(f"Ollama response missing 'response' field. Full API response: {str(outer_json)[:1000]}")
                return {"error": "Ollama response structure incorrect, missing 'response' field.", "details": str(outer_json)[:1000]}
        except requests.exceptions.Timeout:
            logger.warning(f"Ollama API call timed out ({timeout}s) for model {model_name}.")
            current_retry += 1
            if current_retry > retries:
                return {"error": f"Timeout after {retries + 1} attempts."}
            logger.info(f"Retrying ({current_retry}/{retries}) for model {model_name} due to timeout...")
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling Ollama API for model {model_name}: {e}", exc_info=True)
            error_detail = str(e)
            if e.response is not None: error_detail = e.response.text[:500]
            return {"error": f"API RequestException: {error_detail}"}
        # Removed redundant json.JSONDecodeError here as the primary parsing is of the outer response.
    return None

# For brevity, I'll omit some of the complex function definitions that don't have indentation issues

# --- Pydantic Models for LLM Verification and Enrichment ---
class ProjectVerificationEnrichmentOutput(BaseModel):
    action: str = Field(description="Action to take: 'link_to_existing', 'create_new', 'uncertain_relevance', or 'not_equinox_project'.")
    project_id: Optional[int] = Field(None, description="Database ID of the existing project if action is 'link_to_existing'.")
    confirmed_project_name: Optional[str] = Field(None, description="The confirmed or new project name to use.")
    pertinent_text: Optional[str] = Field(None, description="The specific text segment(s) from the document that are pertinent to this project mention.")
    suggested_tags: List[str] = Field(default_factory=list, description="A list of 3-5 suggested keywords/tags based on document content relevant to this project context.")
    confidence_score: Optional[float] = Field(None, description="LLM's confidence in its verification decision (0.0 to 1.0).")
    reasoning: Optional[str] = Field(None, description="Brief reasoning for the decision, especially if uncertain.")

# --- LLM Interaction Functions ---

def get_project_names_from_text(model_name: str, document_text: str):
    """
    Uses the LLM to extract possible project name mentions from the document text.
    Returns a list of strings.
    """
    
    # Handle very large documents by processing in overlapping chunks
    max_chars_for_extraction = 150000  # Larger limit for initial extraction
    document_chunks = []
    
    if len(document_text) <= max_chars_for_extraction:
        document_chunks = [document_text]
    else:
        # Split document into overlapping chunks to ensure we don't miss project names at boundaries
        chunk_size = max_chars_for_extraction - 5000  # Leave overlap space
        overlap = 2500  # Overlap to catch mentions at boundaries
        
        start = 0
        while start < len(document_text):
            end = min(start + chunk_size, len(document_text))
            chunk = document_text[start:end]
            document_chunks.append(chunk)
            
            if end >= len(document_text):
                break
                
            start = end - overlap
    
    all_project_names = set()
    
    for i, chunk in enumerate(document_chunks):
        logger.info(f"Extracting project names from chunk {i+1}/{len(document_chunks)} (length: {len(chunk)} chars)")
        
        prompt = f"""
You are an AI assistant for Equinox Engineering. Your task is to extract ALL specific project names mentioned in the following document chunk.

Look for:
- Named projects with specific titles (e.g. "West Doe Project", "Pouce South Facility", "Pipeline Extension Phase 2")
- Client-specific projects (e.g. "Spectra Energy - West Doe", "Birchcliff Energy - Pouce South") 
- Projects with clear identifiers or codes (e.g. "Project Alpha", "ENG-2024-001")
- Engineering or construction projects mentioned by name
- Facility names that represent projects (e.g. "Sunrise Processing Plant", "North Terminal Expansion")
- Any project referenced with specific identifying information

Do NOT include:
- Generic terms like "project", "facility", "plant" without specific names
- Company names alone (unless they are clearly project names)
- Technology names or equipment types
- General descriptions without specific project identifiers

**Instructions:**
- Find ALL instances of project names, even if mentioned multiple times
- Include variations of the same project name if they appear differently
- Be thorough - look in headings, tables, lists, and body text
- Include both formal project names and informal references if they are specific

Document Text (Chunk {i+1}/{len(document_chunks)}):
{chunk}

Respond in JSON format with a list of ALL project names found:
{{
    "project_names": ["Project Name 1", "Project Name 2", ...]
}}

If no specific project names are found, return: {{"project_names": []}}
"""
        
        response = call_ollama_generate(model_name, prompt, temperature=0.1, top_p=0.9, timeout=180)
        if response and "response" in response:
            try:
                cleaned_output = _strip_llm_json_markdown(response["response"])
                parsed_json = json.loads(cleaned_output)
                project_names = parsed_json.get("project_names", [])
                if isinstance(project_names, list):
                    chunk_names = [str(name).strip() for name in project_names if name and str(name).strip()]
                    all_project_names.update(chunk_names)
                    logger.info(f"Chunk {i+1} yielded {len(chunk_names)} project names: {chunk_names}")
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse project names from chunk {i+1} LLM response: {e}. Raw response: {response['response'][:500]}")
        else:
            logger.warning(f"No valid response from LLM for chunk {i+1}")
    
    final_project_names = list(all_project_names)
    logger.info(f"Total unique project names extracted from all chunks: {len(final_project_names)} - {final_project_names}")
    return final_project_names

MAX_CHARS_VERIFIER = 100000 # Increased from 20000 to handle larger documents - Gemma2 can handle much more context

def construct_enrich_verify_prompt(
    document_text_snippet: str, # Changed from document_text
    raw_name_mention: str, 
    candidate_projects: List[Dict[str, Any]],
    is_full_document: bool
) -> str:
    """Constructs a prompt for an LLM to verify a raw project name mention against existing project data
    and decide whether to link to an existing project, suggest creating a new one, or mark as uncertain/irrelevant.
    It also asks the LLM to extract pertinent text related to the mention.
    """

    candidate_list_str = "No similar projects found in database."
    if candidate_projects:
        candidate_list_str = "\n".join([
            f"  - ID: {p['id']}, Name: \"{p['name']}\", Number: {p['number'] or 'N/A'}, Status: {p['status'] or 'N/A'}, Alias: {p['alias'] or 'N/A'}"
            for p in candidate_projects
        ])

    document_context_indicator = "full document" if is_full_document else "a document snippet with extended context"

    prompt = f"""
You are an AI assistant for Equinox Engineering. Your task is to analyze a potential project name mention within a document and decide how to classify it. You MUST extract the EXACT verbatim text related to this project mention.

Document Text ({document_context_indicator}):
```
{document_text_snippet}
```

Potential Project Name Mentioned: "{raw_name_mention}"

Known Equinox Projects (for comparison):
{candidate_list_str}

Please evaluate the mention "{raw_name_mention}" based on the document text and the list of known projects.

**CRITICAL INSTRUCTIONS FOR VERBATIM TEXT EXTRACTION:**
- For "pertinent_text", extract the EXACT text as it appears in the document
- Include complete sentences that mention or discuss "{raw_name_mention}"
- Include any tables, lists, or structured data that contain this project mention
- Preserve all formatting, numbers, dates, and technical details exactly as written
- If the project is mentioned in multiple places, include ALL relevant mentions
- Do NOT paraphrase, summarize, or rewrite - copy the text EXACTLY as it appears

Respond in JSON format with the following structure:
{{
    "action": "string",                              // Options: 'link_to_existing', 'create_new', 'uncertain_relevance', 'not_equinox_project'
    "project_id": integer | null,                  // Database ID if action is 'link_to_existing'
    "confirmed_project_name": string | null,       // The confirmed or new project name. Use the exact name from "Known Equinox Projects" if linking, or a standardized new name if creating.
    "pertinent_text": string | null,               // **VERBATIM TEXT ONLY** - The exact sentence(s) or paragraph(s) from the document that discuss '{raw_name_mention}'. Include complete context and preserve all formatting.
    "suggested_tags": ["string"],                 // 3-5 keywords/tags from the pertinent_text relevant to this specific project context.
    "confidence_score": float | null,              // Your confidence (0.0-1.0) in this decision.
    "reasoning": string | null                     // Brief reasoning, especially if 'uncertain_relevance', 'not_equinox_project', or complex 'link_to_existing'/'create_new' choices.
}}

Guidelines:
1.  **Action Priority**:
    *   `link_to_existing`: If the mention clearly refers to a project in the "Known Equinox Projects" list (match on name, number, or strong alias). Set `project_id` and use the exact `confirmed_project_name` from the list.
    *   `create_new`: If the mention seems like a valid Equinox project but is NOT in the list. Provide a clear `confirmed_project_name`.
    *   `uncertain_relevance`: If it MIGHT be an Equinox project, but you lack certainty or context. Explain in `reasoning`.
    *   `not_equinox_project`: If it's clearly not an Equinox project (e.g., a client's project, a competitor's, a generic term).
2.  **Project Name Standardization**: For `create_new`, if the `raw_name_mention` is messy, try to standardize it (e.g., proper casing, remove document artifacts). If linking, use the exact name from the database.
3.  **VERBATIM Text Extraction**: For `pertinent_text`, extract the surrounding text from the "Document Text" that directly discusses "{raw_name_mention}". 
    - Copy text EXACTLY as it appears - no paraphrasing
    - Include complete sentences and context
    - Preserve formatting, bullet points, table structure
    - Include technical details, dates, numbers exactly as written
    - If mentioned multiple times, include all relevant instances
4.  **Confidence**: Provide a confidence score, especially if the decision isn't clear-cut.
5.  **Reasoning**: Succinctly explain your decision, especially for `uncertain_relevance`, `not_equinox_project', or complex 'link_to_existing'/'create_new' choices.
6.  **Tags**: Tags should be relevant to the project in the context of the extracted pertinent text.

Ensure your response is a valid JSON object.
"""
    return prompt

def enrich_and_verify_project_context(
    model_name: str, 
    full_document_text: str, # Changed from document_text
    raw_name_mention: str, 
    db_session: Session
) -> Optional[ProjectVerificationEnrichmentOutput]:
    
    logger.info(f"Verifying project context for mention '{raw_name_mention}' with LLM {model_name}. Full doc length: {len(full_document_text)}")
    
    document_snippet_for_llm = full_document_text
    is_full_doc_in_snippet = True

    if len(full_document_text) > MAX_CHARS_VERIFIER:
        is_full_doc_in_snippet = False
        logger.debug(f"Document length ({len(full_document_text)}) exceeds MAX_CHARS_VERIFIER ({MAX_CHARS_VERIFIER}). Creating intelligent snippet.")
        try:
            mention_pos = full_document_text.lower().find(raw_name_mention.lower())
            if mention_pos != -1:
                # Use larger context window - 75% around the mention, 25% for the rest
                context_window = int(MAX_CHARS_VERIFIER * 0.75)
                half_window = context_window // 2
                start_pos = max(0, mention_pos - half_window + (len(raw_name_mention) // 2))
                end_pos = min(len(full_document_text), start_pos + context_window)
                
                # Adjust start_pos if end_pos hit the document end and we have room at the beginning
                if end_pos == len(full_document_text) and (end_pos - start_pos) < context_window:
                    start_pos = max(0, end_pos - context_window)
                
                context_snippet = full_document_text[start_pos:end_pos]
                
                # Add document beginning and end for additional context if we have space
                remaining_chars = MAX_CHARS_VERIFIER - len(context_snippet)
                if remaining_chars > 1000:  # If we have significant space left
                    beginning_chars = remaining_chars // 2
                    ending_chars = remaining_chars - beginning_chars
                    
                    beginning_text = full_document_text[:beginning_chars] if start_pos > 0 else ""
                    ending_text = full_document_text[-ending_chars:] if end_pos < len(full_document_text) else ""
                    
                    if beginning_text and ending_text:
                        document_snippet_for_llm = f"{beginning_text}\n\n[... CONTEXT AROUND MENTION ...]\n\n{context_snippet}\n\n[... END OF DOCUMENT ...]\n\n{ending_text}"
                    elif beginning_text:
                        document_snippet_for_llm = f"{beginning_text}\n\n[... CONTEXT AROUND MENTION ...]\n\n{context_snippet}"
                    elif ending_text:
                        document_snippet_for_llm = f"{context_snippet}\n\n[... END OF DOCUMENT ...]\n\n{ending_text}"
                    else:
                        document_snippet_for_llm = context_snippet
                else:
                    document_snippet_for_llm = context_snippet
                    
                logger.debug(f"Created intelligent snippet around mention '{raw_name_mention}'. Snippet length: {len(document_snippet_for_llm)}. Original pos: {start_pos}-{end_pos}")
            else:
                logger.warning(f"Raw mention '{raw_name_mention}' not found in full text for snippet creation. Using comprehensive beginning.")
                # Take a larger chunk from the beginning when mention not found
                document_snippet_for_llm = full_document_text[:MAX_CHARS_VERIFIER]
        except Exception as e_snip:
            logger.error(f"Error creating intelligent snippet for '{raw_name_mention}': {e_snip}. Using beginning part.")
            document_snippet_for_llm = full_document_text[:MAX_CHARS_VERIFIER]
    
    candidate_projects_data = []
    if db_session: # Only query if session is provided
        try:
            # Simplified candidate search - could be more sophisticated (fuzzy matching, etc.)
            # Using the existing normalization from get_or_create_project concept
            from database_models import Project # Fixed absolute import
            from sqlalchemy.sql import func as sqlfunc_for_verify # Alias to avoid conflict if llm_handler.sqlfunc exists
            
            normalized_mention = raw_name_mention.lower().strip()
            candidates = db_session.query(Project).filter(
                sqlfunc_for_verify.lower(Project.project_name).ilike(f"%{normalized_mention}%")
            ).limit(5).all() # Limit candidates to a manageable number for the prompt
            
            for cand in candidates:
                candidate_projects_data.append({
                    "id": cand.project_id,
                    "name": cand.project_name,
                    "number": cand.equinox_project_number,
                    "status": getattr(cand, 'project_status', None),
                    "alias": getattr(cand, 'project_alias_alternate_names', None)
                })
            logger.debug(f"Found {len(candidate_projects_data)} candidates for mention '{raw_name_mention}': {candidate_projects_data}")
        except Exception as e:
            logger.error(f"Database error while fetching candidates for '{raw_name_mention}': {e}", exc_info=True)
            # Proceed without candidates if DB error

    prompt = construct_enrich_verify_prompt(document_snippet_for_llm, raw_name_mention, candidate_projects_data, is_full_doc_in_snippet)
    
    try:
        ollama_api_response = call_ollama_generate(model_name, prompt, temperature=0.1, top_p=0.8, timeout=300) # Lower temp for more consistent verbatim extraction, longer timeout

        if ollama_api_response and "response" in ollama_api_response:
            llm_json_string = ollama_api_response["response"]
            logger.debug(f"Raw LLM JSON for verification/enrichment of '{raw_name_mention}': {llm_json_string[:1000]}...")
            try:
                cleaned_llm_output = _strip_llm_json_markdown(llm_json_string)
                parsed_json = json.loads(cleaned_llm_output)
                validated_output = ProjectVerificationEnrichmentOutput.model_validate(parsed_json)
                logger.info(f"Successfully verified/enriched context for '{raw_name_mention}'. Action: {validated_output.action}, Tags: {validated_output.suggested_tags}")
                return validated_output
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to parse/validate LLM JSON for verification/enrichment of '{raw_name_mention}'. Error: {e}. LLM Output: {llm_json_string[:500]}")
                return None
        elif ollama_api_response and "error" in ollama_api_response:
            logger.error(f"LLM call for verification/enrichment of '{raw_name_mention}' reported error: {ollama_api_response['error']}. Details: {ollama_api_response.get('details', '')}")
            return None
        else:
            logger.error(f"LLM call for verification/enrichment of '{raw_name_mention}' failed or returned unexpected structure. Response: {str(ollama_api_response)[:1000]}")
            return None
            
    except Exception as e:
        logger.error(f"Unexpected exception during LLM verification/enrichment for '{raw_name_mention}': {e}", exc_info=True)
        return None

# --- Document-wide Data Extraction Function ---

def extract_all_document_data_verbatim(model_name: str, document_text: str, document_filename: str = "") -> Optional[Dict[str, Any]]:
    """
    Extracts ALL relevant engineering/project data from a document verbatim.
    This function provides comprehensive data extraction beyond just project names.
    """
    
    # Handle very large documents by processing in overlapping chunks
    max_chars_for_extraction = 120000  # Large limit for comprehensive extraction
    document_chunks = []
    
    if len(document_text) <= max_chars_for_extraction:
        document_chunks = [{"text": document_text, "chunk_num": 1, "total_chunks": 1}]
    else:
        # Split document into overlapping chunks
        chunk_size = max_chars_for_extraction - 8000  # Leave overlap space
        overlap = 4000  # Overlap to catch information at boundaries
        
        start = 0
        chunk_num = 1
        while start < len(document_text):
            end = min(start + chunk_size, len(document_text))
            chunk = document_text[start:end]
            document_chunks.append({
                "text": chunk, 
                "chunk_num": chunk_num,
                "total_chunks": None  # Will be set after loop
            })
            
            if end >= len(document_text):
                break
                
            start = end - overlap
            chunk_num += 1
        
        # Update total chunks count
        for chunk in document_chunks:
            chunk["total_chunks"] = len(document_chunks)
    
    all_extracted_data = {
        "projects": [],
        "technologies": [],
        "key_information": [],
        "financial_data": [],
        "personnel": [],
        "dates_milestones": [],
        "locations": [],
        "client_information": [],
        "technical_specifications": [],
        "document_metadata": {}
    }
    
    for chunk_info in document_chunks:
        chunk = chunk_info["text"]
        chunk_num = chunk_info["chunk_num"]
        total_chunks = chunk_info["total_chunks"]
        
        logger.info(f"Extracting comprehensive data from chunk {chunk_num}/{total_chunks} (length: {len(chunk)} chars) of {document_filename}")
        
        prompt = f"""
You are an AI assistant for Equinox Engineering. Your task is to extract ALL relevant engineering, project, and business information from this document chunk. Extract VERBATIM text - do NOT paraphrase or summarize.

Document: {document_filename}
Chunk: {chunk_num} of {total_chunks}

Document Text:
```
{chunk}
```

Extract ALL information in the following categories. For each item, provide the EXACT text as it appears in the document:

**CRITICAL INSTRUCTIONS:**
- Copy text EXACTLY as it appears - no paraphrasing or summarizing
- Include complete sentences with full context
- Preserve formatting, numbers, dates, technical specifications exactly
- Include table data, lists, and structured information verbatim
- If information spans multiple sentences, include the complete context

Respond in JSON format:
{{
    "projects": [
        {{
            "project_name": "exact name as mentioned",
            "verbatim_text": "complete sentence(s) or paragraph(s) mentioning this project",
            "context_type": "heading/paragraph/table/list"
        }}
    ],
    "technologies": [
        {{
            "technology_name": "exact technology name",
            "verbatim_text": "complete text describing this technology",
            "specifications": "any technical specs mentioned verbatim"
        }}
    ],
    "key_information": [
        {{
            "category": "budget/schedule/scope/requirements/etc",
            "verbatim_text": "exact text from document",
            "data_type": "financial/technical/operational/etc"
        }}
    ],
    "financial_data": [
        {{
            "amount": "exact amount as written",
            "currency": "currency if mentioned",
            "verbatim_text": "complete sentence(s) containing financial information",
            "financial_type": "budget/cost/revenue/etc"
        }}
    ],
    "personnel": [
        {{
            "name": "exact name",
            "role": "exact role/title",
            "verbatim_text": "complete text mentioning this person"
        }}
    ],
    "dates_milestones": [
        {{
            "date": "exact date as written",
            "milestone": "exact milestone description",
            "verbatim_text": "complete text containing date and milestone"
        }}
    ],
    "locations": [
        {{
            "location": "exact location name",
            "verbatim_text": "complete text mentioning this location",
            "location_type": "facility/office/site/etc"
        }}
    ],
    "client_information": [
        {{
            "client_name": "exact client name",
            "verbatim_text": "complete text about this client",
            "relationship": "owner/contractor/partner/etc"
        }}
    ],
    "technical_specifications": [
        {{
            "specification_type": "equipment/process/material/etc",
            "verbatim_text": "exact technical specification text",
            "values": "exact values, measurements, parameters"
        }}
    ],
    "document_metadata": {{
        "title": "document title if mentioned",
        "author": "author if mentioned", 
        "date": "document date if mentioned",
        "version": "version if mentioned",
        "purpose": "document purpose if explicitly stated"
    }}
}}

If no information is found for a category, return an empty array or object for that category.
"""
        
        response = call_ollama_generate(model_name, prompt, temperature=0.1, top_p=0.9, timeout=300)
        if response and "response" in response:
            try:
                cleaned_output = _strip_llm_json_markdown(response["response"])
                parsed_json = json.loads(cleaned_output)
                
                # Merge chunk data into all_extracted_data
                for category, items in parsed_json.items():
                    if category in all_extracted_data:
                        if isinstance(items, list):
                            all_extracted_data[category].extend(items)
                        elif isinstance(items, dict) and category == "document_metadata":
                            # Merge metadata, giving preference to later chunks for completeness
                            all_extracted_data[category].update(items)
                
                logger.info(f"Successfully extracted data from chunk {chunk_num}/{total_chunks}")
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to parse comprehensive extraction from chunk {chunk_num} LLM response: {e}. Raw response: {response['response'][:500]}")
        else:
            logger.warning(f"No valid response from LLM for comprehensive extraction chunk {chunk_num}")
    
    # Remove duplicates based on verbatim_text while preserving order
    for category in all_extracted_data:
        if isinstance(all_extracted_data[category], list):
            seen_texts = set()
            unique_items = []
            for item in all_extracted_data[category]:
                if isinstance(item, dict) and "verbatim_text" in item:
                    text_key = item["verbatim_text"].strip()
                    if text_key not in seen_texts:
                        seen_texts.add(text_key)
                        unique_items.append(item)
                else:
                    unique_items.append(item)  # Keep items without verbatim_text
            all_extracted_data[category] = unique_items
    
    # Add extraction summary
    total_items = sum(len(items) if isinstance(items, list) else 1 for items in all_extracted_data.values())
    logger.info(f"Comprehensive extraction completed for {document_filename}. Total items extracted: {total_items}")
    
    return all_extracted_data

# --- Document Type and Usefulness Classification ---

if __name__ == '__main__':
    # Configure basic logging for direct script execution if not already configured by streamlit_app
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    logger.info("LLM Handler Test Script")
    
    available_models = get_available_ollama_models()
    if available_models:
        logger.info(f"Available Ollama Models: {available_models}")
        
        test_model = None
        preferred_models = ["gemma3:12b", "qwen3:14b"] # Example preferred models
        for model in preferred_models:
            if model in available_models:
                test_model = model
                break
        if not test_model and available_models: 
            test_model = available_models[0]

        if test_model:
            logger.info(f"Attempting to use model: {test_model}")
            
            sample_text = ("Project Equinox Phase 1, led by Project Manager Jane Doe, commenced on 2023-01-15 "
                         "with an estimated budget of $2,500,000. The primary objective is to develop a new "
                         "pipeline infrastructure. Key technologies include advanced composite piping and AI-driven monitoring.")
            
            # Not including all functions, but this would call construct_extraction_prompt
            logger.info(f"Sample text for testing: {sample_text}")
            
            # Test the fixed code here
            
        else:
            logger.warning("No suitable models found to run a test. Please ensure models like 'gemma3:12b' or 'qwen3:14b' are pulled or edit preferred_models list.")
    else:
        logger.error("Could not fetch any models from Ollama. Ensure Ollama is running and accessible.")

    logger.info("-----------------------") 