import fitz  # PyMuPDF
import os
import logging
import warnings
from typing import Dict, Any, List

# Setup logger for this module
logger = logging.getLogger(__name__)

# Suppress specific PyMuPDF warnings about CropBox
warnings.filterwarnings("ignore", message="CropBox missing from /Page, defaulting to MediaBox")

def parse_pdf(file_path: str) -> Dict[str, Any]:
    """
    Parse a PDF file and extract text and metadata.
    Returns a dictionary containing the extracted information.
    """
    try:
        doc = fitz.open(file_path)
        result = {
            "text_from_pages": [],
            "metadata": {
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
                "num_pages": len(doc),
                "file_type": "pdf"
            }
        }

        # Extract text from each page
        for page_num, page in enumerate(doc):
            try:
                # Get page text with improved extraction settings
                text = page.get_text("text", sort=True)
                
                # Clean up the text
                text = text.strip()
                
                # Only add non-empty pages
                if text:
                    result["text_from_pages"].append({
                        "page_number": page_num + 1,
                        "text": text
                    })
                else:
                    logger.warning(f"⚠️ Page {page_num + 1} appears to be empty or contains no extractable text")
            except Exception as e:
                logger.warning(f"⚠️ Error extracting text from page {page_num + 1}: {str(e)}")
                continue

        # Combine all text for full document text
        full_text = "\n\n".join(page["text"] for page in result["text_from_pages"])
        result["full_text"] = full_text

        # Log extraction quality
        if not full_text.strip():
            logger.warning("⚠️ No text could be extracted from the PDF")
        else:
            logger.info(f"✅ Successfully extracted {len(full_text)} characters from PDF")
            if len(result["text_from_pages"]) < len(doc):
                logger.warning(f"⚠️ Only extracted text from {len(result['text_from_pages'])} out of {len(doc)} pages")

        doc.close()
        return result

    except Exception as e:
        logger.error(f"Error parsing PDF {file_path}: {str(e)}")
        return {"error": str(e)}

if __name__ == '__main__':
    # Configure basic logging for direct script execution
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

    # To test this parser, create a dummy PDF file named 'example.pdf' 
    # in your workspace root (D:\bd_scrape) or provide a path to an existing PDF file.
    
    # For demonstration, we'll try to create a very simple text-based PDF if reportlab is available.
    # Otherwise, we'll just point to a non-existent file and show how to test manually.
    example_file_name = "example.pdf"
    created_dummy = False

    try:
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        
        c = canvas.Canvas(example_file_name, pagesize=letter)
        c.drawString(72, 800, "Hello, World!")
        c.drawString(72, 780, "This is a test PDF document created by ReportLab.")
        c.drawString(72, 760, "It contains some sample text on the first page.")
        c.showPage()
        c.drawString(72, 800, "This is the second page.")
        # Add some metadata
        c.setTitle("Test PDF Document")
        c.setAuthor("Automated Script")
        c.setSubject("Parser Test")
        c.save()
        logger.info(f"Created dummy {example_file_name} for testing.")
        created_dummy = True
    except ImportError:
        logger.warning("ReportLab library not found. Skipping dummy PDF creation.")
        logger.info(f"Please create or place an '{example_file_name}' in the directory '{os.getcwd()}' or modify the script to point to an existing PDF.")
    except Exception as e:
        logger.error(f"Error creating dummy PDF: {e}", exc_info=True)

    if created_dummy or os.path.exists(example_file_name):
        parsed_data = parse_pdf(example_file_name)
        logger.info(f"\n--- Parsed Data for {example_file_name} ---")
        for key, value in parsed_data.items():
            if key == "text_from_pages":
                logger.debug(f"\n{key.replace('_', ' ').title()}:")
                for item in value:
                    logger.debug(f"  Page {item['page_number']}:\n{item['text'][:200]}..." if item['text'] else f"  Page {item['page_number']}: [No text extracted]")
            elif key == "metadata":
                logger.debug(f"\n{key.title()}:")
                raw_meta = value.pop("raw_metadata", None) # separate raw metadata for cleaner display
                for meta_key, meta_val in value.items():
                    if meta_val:
                        logger.debug(f"  {meta_key.title()}: {meta_val}")
                if raw_meta:
                    logger.debug(f"  Raw_Metadata: {raw_meta}")
            else:
                logger.debug(f"\n{key.title()}: {value}")
        logger.info("-------------------------------------")
    elif not created_dummy:
        logger.warning(f"Skipping parsing test as '{example_file_name}' was not found and dummy creation failed/skipped.") 