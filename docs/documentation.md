# Project Documentation

This document provides an overview of the `bd_scrape` project components and their functionalities.

## `src/llm_handler.py`

This module is responsible for all interactions with the Ollama Large Language Model (LLM).

### Core Functionalities:

1.  **Model Discovery**:
    *   `get_available_ollama_models()`: Fetches and lists all available models from the local Ollama server instance.

2.  **LLM Interaction**:
    *   `call_ollama_generate()`: A generic function to send prompts to a specified Ollama model. It handles API requests, retries, timeouts, and can request JSON formatted output from the LLM. It also includes logging for requests and responses.

3.  **Project Context Verification and Enrichment**:
    *   `ProjectVerificationEnrichmentOutput` (Pydantic Model): Defines the expected structured JSON output for project verification tasks. This includes fields like action to take (link, create new, etc.), project ID, confirmed name, pertinent text from the document, suggested tags, confidence score, and reasoning.
    *   `construct_enrich_verify_prompt()`: Dynamically builds a detailed prompt for the LLM. This prompt instructs the LLM to analyze a document snippet for a potential project name mention, compare it against a list of known projects from the database, and provide a structured JSON response according to the `ProjectVerificationEnrichmentOutput` model. It guides the LLM on how to decide actions, standardize names, extract relevant text, and provide confidence/reasoning.
    *   `enrich_and_verify_project_context()`: Orchestrates the project verification process.
        *   It takes the full document text and a raw project name mention.
        *   It creates a snippet of the document around the mention if the full text is too long for the LLM context window (`MAX_CHARS_VERIFIER`).
        *   It queries the database (if a session is provided) for candidate projects that might match the mention.
        *   It calls `construct_enrich_verify_prompt()` to get the prompt.
        *   It uses `call_ollama_generate()` to get the LLM's response.
        *   It then attempts to parse and validate the LLM's JSON string output against the `ProjectVerificationEnrichmentOutput` Pydantic model.
        *   It includes error handling and logging throughout the process.

4.  **Helper Functions**:
    *   `_strip_llm_json_markdown()`: A utility to clean up potential markdown code fences (e.g., \`\`\`json ... \`\`\`) that LLMs sometimes wrap around JSON output.

### Workflow for Project Verification:

The typical flow for verifying a project mention using this module would be:

1.  An external process identifies a potential project name (`raw_name_mention`) within a document (`full_document_text`).
2.  `enrich_and_verify_project_context()` is called with these details and a database session.
3.  The function prepares a focused snippet of the document text and fetches potential matching projects from the database.
4.  A detailed prompt is constructed, asking the LLM to analyze the mention in context and decide on an action (link, create, etc.), extract relevant text, and suggest tags.
5.  The LLM is called via `call_ollama_generate()`, requesting a JSON response.
6.  The response is cleaned, parsed, and validated.
7.  The validated `ProjectVerificationEnrichmentOutput` object (or `None` if errors occur) is returned.

### Configuration:

*   `OLLAMA_API_BASE_URL`: Defines the base URL for the Ollama API (default: `http://localhost:11434/api`).
*   `MAX_CHARS_VERIFIER`: Maximum characters from the document to send to the LLM for verification tasks.

### Main Block (`if __name__ == '__main__':`)

The script includes a `main` block for testing purposes. When run directly, it:
1.  Configures basic logging.
2.  Fetches available Ollama models.
3.  Selects a preferred model for testing (e.g., "gemma3:12b", "qwen3:14b", or the first available).
4.  If a model is found, it logs a sample text and indicates where test calls would be made (though the actual calls to extraction/verification functions in the provided `__main__` are commented out or illustrative).

This initial documentation should give us a good starting point. We can expand it as we understand more about the other parts of your application and after we refactor `llm_handler.py`. 