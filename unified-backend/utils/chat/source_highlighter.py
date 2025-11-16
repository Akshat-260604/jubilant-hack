import json
import fitz
import asyncio
import traceback
from time import time
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
from services.s3host import current_s3_client
from models.highlight import highlight_repo
from lib.brain import use_brain
# Create a global ThreadPoolExecutor
thread_pool = ThreadPoolExecutor()
import logging

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)-8s %(message)s'
)
logger = logging.getLogger(__name__)

class PreciseHighlightService:
    """
    A service to find precise source text highlights in a PDF document
    based on a claim, using an LLM to identify the exact source lines.
    """

    def _extract_lines_from_doc_page(self, pdf_document: fitz.Document, page_number: int) -> list[dict]:
        """Extracts text lines from a specific page of an open fitz document."""
        all_lines = []
        
        if not 0 < page_number <= len(pdf_document):
            logger.error(f"Page number {page_number} is out of range for document with {len(pdf_document)} pages.")
            return []

        page = pdf_document.load_page(page_number - 1)
        page_dict = page.get_text("dict", flags=2)
        
        for block_idx, block in enumerate(page_dict.get("blocks", [])):
            for line_idx, line in enumerate(block.get("lines", [])):
                line_text = " ".join([span["text"] for span in line.get("spans", [])])
                if line_text:
                    line_id = f"p{page_number}_b{block_idx}_l{line_idx}"
                    all_lines.append({
                        "line_id": line_id,
                        "text": line_text,
                        "bbox": line["bbox"]
                    })
        
        return all_lines

    async def _get_relevant_line_ids_from_llm(self, claim: str, source_lines: list[dict]) -> list[str]:
        """Identifies source lines by calling the Bedrock LLM."""

        if not source_lines:
            logger.warning("No source lines provided to LLM; returning empty list.")
            return []

        system_prompt = """The assistant is an AI created to assist with medical content generation.

This assistant is part of an AI system called Content Creator, which generates content from documents using Retrieval Augmented Generation (RAG).
The assistant's specific role is to perform markup (highlighting) in source PDF documents by returning the exact line_ids from the source document that support the generated content.

The assistant is always provided with two inputs:
1. Generated Content: A paragraph or multiple sentences created by Content Creator.
2. Source Document Text: A list of source document lines, where each line has a unique line_id.

The assistant's goals:
1. Analyze the generated content and source document lines.
2. Identify exactly which source lines contain the information referenced in the generated content.
3. Match facts, dates, numbers, claims, criteria, or paraphrased sentences from the generated content to the correct source lines.
4. Perform semantic matching, not just exact word matching, since Content Creator often paraphrases document content.

OUTPUT FORMAT:
The assistant always returns ONLY a JSON array of line_ids in this exact format. Example:
["p4_b1_l2", "p4_b5_l1"]

The array must include all and only the line_ids that directly support any part of the generated content.

The assistant should always follow these matching rules:

1. Match based on facts, dates, numbers, claims, criteria, and paraphrased sentences.
2. Avoid unrelated lines, vague semantic matches, or entire paragraphs when only specific lines are relevant.
3. In case of doubt, prefer returning fewer line_ids with strong semantic or factual matches rather than many loosely related ones.
4. Do NOT include any additional text, explanation, or formatting—just the JSON array of line_ids.

Example Expected Output:
["p4_b1_l2", "p4_b5_l1"]
"""
        
        user_prompt = f"""Statement to verify (response portion): "{claim}"

Source lines from the page:
{json.dumps(source_lines, indent=2)}"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        temperature = 0.1
        
        response_text = ""
        try:
            # Use 'async for' directly within the async method
            stream = await use_brain(
            messages,
            stream=True,
            respond_in_json=True,
            inference="openai",
            temperature=temperature,
            )
            response_text = ""
            async for chunk in stream:
                response_text += chunk
            
            # Clean the response: remove markdown code block markers if present
            cleaned_text = response_text.strip()
            # Remove ```json and ``` markers
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]  # Remove ```json
            elif cleaned_text.startswith("```"):
                cleaned_text = cleaned_text[3:]  # Remove ```
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]  # Remove trailing ```
            cleaned_text = cleaned_text.strip()
            
            # The LLM should return a JSON list as a string, e.g., '["id1", "id2"]'
            return json.loads(cleaned_text)
        except json.JSONDecodeError:
            logger.error(f"LLM did not return valid JSON. Response: '{response_text}'")
            return []
        except Exception as e:
            logger.error(f"An error occurred during Bedrock API call: {e}")
            return []

    async def find_highlights(self, pdf_document: fitz.Document, claim: str, page_number: int) -> list[dict]:
        """
        Orchestrates the process of finding precise highlights for a claim.

        Returns:
            A list of dictionaries for the lines that should be highlighted.
            Each dictionary contains the line_id, text, and bbox.
        """
        # Step 1: Extract all lines and their bboxes from the page.
        # This is a synchronous operation, so we can run it in an executor to avoid blocking.
        loop = asyncio.get_running_loop()
        all_lines_with_bboxes = await loop.run_in_executor(
            None, self._extract_lines_from_doc_page, pdf_document, page_number
        )
        
        
        if not all_lines_with_bboxes:
            return []

        # Step 2: Prepare a clean payload (without bboxes) for the LLM.
        lines_for_llm = [{"line_id": line["line_id"], "text": line["text"]} for line in all_lines_with_bboxes]
        # Step 3: Call the LLM to get the IDs of the relevant source lines.
        relevant_ids = await self._get_relevant_line_ids_from_llm(claim, lines_for_llm)
        print("relevant_ids",relevant_ids)
        # Step 4: Filter the original data to get the full line info for the relevant IDs.
        lines_to_highlight = [line for line in all_lines_with_bboxes if line["line_id"] in relevant_ids]
        print("lines_to_highlight",lines_to_highlight)
        return lines_to_highlight
    

async def save_pdf_screenshots(pdf_document: fitz.Document, highlighted_pages_set, message_id, document_name):
    """
    Save screenshots of highlighted PDF pages to S3.

    Args:
        pdf_document (fitz.Document): The PDF document object
        highlighted_pages_set (set): Set of page numbers with highlights
        message_id (str): ID of the message requesting the screenshots
        document_name (str): Name of the document
    """
    # iterate through the set of highlighted page numbers
    for page_num in highlighted_pages_set:
        # load the page (page_num-1 because PyMuPDF is 0-indexed)
        page = pdf_document.load_page(page_num - 1)

        # set the zoom factor
        zoom_x=2.0
        zoom_y=2.0
        matrix = fitz.Matrix(zoom_x, zoom_y)

        # create the pixmap with the specified resolution
        pix = page.get_pixmap(matrix=matrix)

        # convert the pixmap to an image byte stream
        image_bytes = BytesIO()
        image_bytes.write(pix.tobytes())  # write the pixmap PNG data
        image_bytes.seek(0)  # reset the stream position
        image_data = image_bytes.getvalue()
        image_key = f"ChatHighlights/{message_id}/{document_name}/Page_{page_num}.png"

        # upload the image to s3
        await current_s3_client.save_to_s3(image_data, image_key)

    return


async def apply_and_upload_precise_highlights(pdf_document: fitz.Document, lines_to_highlight: list[dict], message_id: str, document_name: str):
    """
    Applies highlights to a PDF based on precise line data and uploads screenshots to S3.

    Args:
        pdf_document (fitz.Document): The PDF document object to be modified.
        lines_to_highlight (list[dict]): A list of dictionaries from PreciseHighlightService,
                                        each containing the 'bbox' and 'line_id'.
        message_id (str): ID of the message for S3 pathing.
        document_name (str): Name of the document for S3 pathing.

    Returns:
        int: The total number of highlights added.
    """
    highlights_added = 0
    highlighted_pages_set = set()
    for line in lines_to_highlight:
        try:
            # Extract the 1-based page number from the line_id (e.g., "p4_b1_l2")
            page_num_str = line['line_id'].split('_')[0][1:]
            page_number = int(page_num_str)

            # PyMuPDF is 0-indexed
            page = pdf_document.load_page(page_number - 1)
            
            # Get the bounding box and create the highlight
            bbox = line['bbox']
            rect = fitz.Rect(bbox)
            highlight = page.add_highlight_annot(rect)
            highlight.update()

            highlights_added += 1
            highlighted_pages_set.add(page_number) # Add 1-based page number to the set
        except Exception as e:
            logger.error(f"Failed to apply highlight for line '{line.get('line_id', 'N/A')}' | Exception: {e}")

    # If any highlights were successfully added, generate and upload screenshots
    if highlights_added > 0:
        # This function will also close the pdf_document
        await save_pdf_screenshots(pdf_document, highlighted_pages_set, message_id, document_name)
    
    return highlights_added



async def highlight_pdf_text(pdf_document: fitz.Document, matches_df, message_id, document_name):
    """
    Highlight text in PDF document based on matching coordinates.

    Args:
        pdf_document (fitz.Document): The PDF document object
        matches_df (DataFrame): DataFrame containing match information and coordinates
        message_id (str): ID of the message requesting the highlight
        document_name (str): Name of the document

    Returns:
        int: Number of highlights added
    """
    highlights_added = 0
    highlighted_pages_set = set()
    for _, row in matches_df.iterrows():
        # correct 1-indexed page number from the DataFrame to 0-indexed for PyMuPDF
        page_number_0_indexed = int(row['page_number']) - 1
        match_percentage = row['match_percentage']
        coords = row['coordinates']
        if match_percentage >= 70 and coords:
            try:
                x0, y0, x1, y1 = eval(coords) if isinstance(coords, str) else coords
                rect = fitz.Rect(x0, y0, x1, y1)
                page = pdf_document.load_page(page_number_0_indexed)
                highlight = page.add_highlight_annot(rect)
                # highlight.set_colors(stroke=(1, 1, 0.7))  # light yellow color
                highlight.update()
                highlights_added += 1
                # store the original page number (1-indexed) for downstream consistency
                highlighted_pages_set.add(page_number_0_indexed + 1)
            except Exception as e:
                logger.error(f"Highlights on page '{page_number_0_indexed + 1}' entered exception | Exception: {e}")

    # pass 0-indexed pages as is; if save_pdf_screenshots expects 1-indexed, adjust accordingly
    await save_pdf_screenshots(pdf_document, highlighted_pages_set, message_id, document_name)
    return highlights_added


async def extract_highlighted_text(
    pdf_document: fitz.Document,  # kept for signature consistency
    page_number: int,
    lines_to_highlight: list
) -> str:
    """
    Return the exact 'text' values from lines_to_highlight,
    joined into a single string without newlines.
    """
    extracted_texts = []

    for item in lines_to_highlight:
        if isinstance(item, dict) and "text" in item:
            extracted_texts.append(item["text"].strip())

    return "".join(extracted_texts) if extracted_texts else ""
 


async def save_source_highlights(
    response_portion: str, 
    document_name: str,
    document_id: str,
    pdf_document: fitz.Document,
    message_id: str, 
    page_number: int, 
):
    """
    Finds and applies highlights to a PDF document page,
    uploading a new screenshot with highlights.
    """
    try:
        start = time()
        logger.info(
            f'HIGHLIGHTING STARTED > Doc: {document_name} | Page: {page_number}'
        )

        highlighter = PreciseHighlightService()
        lines_to_highlight = await highlighter.find_highlights(
            pdf_document=pdf_document,
            claim=response_portion,
            page_number=page_number
        )

        highlights_added = await apply_and_upload_precise_highlights(
            pdf_document=pdf_document,
            lines_to_highlight=lines_to_highlight,
            message_id=message_id,
            document_name=document_name
        )

        status = "done" if highlights_added > 0 else "error"
        end = time()
        logger.info(
            f'HIGHLIGHTING FINISHED > Doc: {document_name} | Page: {page_number} | '
            f'Status: {status} | Highlights added: {highlights_added} | '
        )

        if not highlights_added > 0:
            # Replace gchat message with logger
            logger.warning(
                f"No highlights added for:\n"
                f"Document: {document_name}\n"
                f"Page: {page_number}\n"
                f"Claimed Paragraph: {response_portion}\n"
                f"Lines to Highlight from model: {lines_to_highlight}"
            )

    except Exception as e:
        logger.error(
            f'An error occurred while highlighting doc {document_name} | '
            f'Error: {e} | Full traceback: {traceback.format_exc()}'
        )
        status = "error"
        highlights_added = 0

    # Update database status
    await highlight_repo.update_highlight_status_by_doc_page(
        message_id, document_id, page_number, status
    )
