Simplified Process Overview (Post-Upload):
For each uploaded document:

Parse: The system first reads the document and extracts all its text content.

Initial LLM Scan (Spotting Potential Names):
The full text is sent to an LLM.

The LLM quickly scans the text and returns a list of potential project 
names it thinks are mentioned (e.g., "Alpha Project," "Project Beta Phase II," "Old Power Plant Study").

Detailed LLM Review & Enrichment (For Each Potential Name):

Now, for each potential project name spotted in step 2, a more detailed 
LLM review happens:

The system checks our database for any existing Equinox projects with names similar to the one spotted.
A second LLM call is made. This "smarter" LLM call is given:
The full document text.
The specific project name mention from the initial scan (e.g., "Alpha Project").
A list of any similar-sounding Equinox projects we found in our database (e.g., "Project Alpha," "Alpha Project - Design Stage").
Based on all this information, this LLM decides:
Project Link/Creation:
Does this mention refer to one of our existing projects? (e.g., "Yes, 'Alpha Project' in the text refers to our database 'Project Alpha' ID #123").
Or, is this a new Equinox project that we should add to our database? (e.g., "Yes, 'Old Power Plant Study' seems to be a new project for Equinox").
Or, is this mention not relevant or not an Equinox project? (e.g., "No, this is just a generic term").
Confirmed Project Name: What's the best official name to use for this project (either confirming an existing one or naming a new one)?
Automated Tags/Categories: Considering the document's content in relation to this specific project, what are 3-5 useful keywords, tags, or categories? (e.g., for "Project Alpha," tags might be: "pipeline design," "feasibility study," "technical specification," "Client X").
Store Information in Database:
Based on the LLM's detailed review:
The correct Project record (either existing or newly created) is identified in the database.
The document's full verbatim text is saved into the ProjectExtractionLog table, linked to this confirmed Project.
The LLM's suggested tags/categories (e.g., "pipeline design," "feasibility study") are saved in a new table and linked to that specific log entry, providing richer metadata for future searching and analysis.
This means we're using the LLM in a more sophisticated loop to refine project identification and enrich the data.