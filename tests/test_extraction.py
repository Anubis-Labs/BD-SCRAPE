from src.llm_handler import get_project_names_from_text

# Sample text based on what you showed from the actual document
sample_text = """
Equinox has extensive experience with amine sweetening projects including:
- Spectra Energy – West Doe (100 MMscfd)
- Birchcliff Energy - Pouce South (60 MMscfd) 
- ARC Resources – West Dawson (120 MMscfd)
- Ovintiv (Encana) – Swan (200 MMscfd)

These projects demonstrate our capabilities in both greenfield and brownfield applications.
Additional projects include the reimbursable Spectra Energy – West Doe project.
"""

print("Testing improved project name extraction...")
print(f"Sample text length: {len(sample_text)}")

result = get_project_names_from_text('gemma3:12b', sample_text)

print(f"\nExtracted project names: {result}")
print(f"Number of projects found: {len(result)}")

for i, project in enumerate(result, 1):
    print(f"  {i}. {project}") 