from fastapi import APIRouter, Body
from utils.document_handling.content_findings import generate_findings_from_text

router = APIRouter()

AVAILABLE_CONTENT_FORMATS = [
    "Clinical Trial Report",
    "Clinical Summaries",
    "Patient Case Studies",
    "Plain Language Summaries"
]

@router.get("/get-content-formats/", tags=["Findings"])
def get_content_formats():
    """
    Retrieve a list of available content formats for findings extraction.

    Returns:
        dict: A dictionary containing a list of supported content formats.
    """
    return {"content_formats": AVAILABLE_CONTENT_FORMATS}


@router.post("/generate-findings/", tags=["Findings"])
def get_findings(
    content_format: str = Body(...),
    text: str = Body(...)
):
    """
    Extract findings from the provided text based on the selected content format.

    Args:
        content_format (str): The type of content format to use for extraction.
        text (str): The input text from which to extract findings.

    Returns:
        dict: A dictionary containing the extracted findings or an error message if the format is invalid.
    """
    if content_format not in AVAILABLE_CONTENT_FORMATS:
        return {"error": f"Invalid content format. Choose from: {AVAILABLE_CONTENT_FORMATS}"}
    
    result = generate_findings_from_text(content_format, text)
    return {"findings": result}
