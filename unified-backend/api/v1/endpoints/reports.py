from typing import Dict, List, Optional, Literal
import textwrap
import uuid

from fastapi import APIRouter, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from configs.config import OpenAISettings
from lib.hasher import hash_param
from models.doc import doc_repo
from models.extracted_text import extracted_text_repo
from models.images import image_repo
from models.summary import summary_repo
from models.tables import table_repo
from services.s3host import current_s3_client


router = APIRouter()


class ReportGenerationRequest(BaseModel):
    """
    Request body for `/reports/generate`.

    Matches the shape used on the frontend:
    - userId: string
    - sections: list of section identifiers (e.g. "introduction", "clinical_findings")
    - instructions: optional free-text instructions
    - documentId: optional specific document ID to target
    - scope: "single" (default) or "combined" (all processed docs)
    """

    userId: str
    sections: List[str]
    instructions: Optional[str] = None
    documentId: Optional[str] = None
    scope: Optional[Literal["single", "combined"]] = "single"


class ReportGenerationResponse(BaseModel):
    report_id: str
    content: str


_REPORT_STORE: Dict[str, str] = {}
_openai_settings = OpenAISettings()
_openai_client = OpenAI(api_key=_openai_settings.OPENAI_API_KEY)


async def _get_user_ready_docs(user_id: str) -> List[Dict]:
    """
    Return all processed documents for the given (raw) user_id.
    """
    if not user_id or not user_id.strip():
        raise HTTPException(status_code=400, detail="userId is required")

    hashed_user_id = await hash_param(user_id)
    docs = await doc_repo.get_docs_by_user(userId=hashed_user_id)
    ready_docs = [d for d in docs if d.get("status") in ("completed", "done")]
    if not ready_docs:
        raise HTTPException(
            status_code=400,
            detail="No processed documents found for this user. Please upload and process a document first.",
        )

    # Ensure deterministic ordering by createdAt
    ready_docs.sort(key=lambda d: d.get("createdAt", ""), reverse=True)
    return ready_docs


async def _collect_document_content(document_id: str) -> Dict:
    """
    Collect raw content for a single document:
    - extracted front-end text per page (fe_text)
    - stored summary (if any)
    - table image URLs
    - figure/image URLs
    """
    # Extracted text (per page)
    extracted = await extracted_text_repo.get_extracted_text_by_document_id(document_id)
    extracted_sorted = sorted(extracted, key=lambda x: x.get("page_number", 0))

    # Summary (if exists)
    summary_doc = await summary_repo.get_summary_by_document_id(document_id)
    summary_text = ""
    if summary_doc and summary_doc.get("summary"):
        # summary is stored as { text: str, highlighted_image_ids: [...] }
        summary_text = summary_doc["summary"].get("text", "")

    # Tables (URLs)
    tables = await table_repo.get_tables_by_document_id(document_id)
    table_entries: List[Dict] = []
    for t in tables:
        try:
            presigned_url = await current_s3_client.get_presigned_view_url(t["id"])
            table_entries.append(
                {
                    "url": presigned_url,
                    "page_number": t.get("page_number"),
                    "table_number": t.get("table_number"),
                }
            )
        except Exception:
            continue

    # Images / graphs (URLs)
    image_urls: List[str] = []
    try:
        image_ids = await image_repo.get_image_by_document_id(document_id)
        for image_id in image_ids:
            try:
                presigned = await current_s3_client.get_presigned_view_url(image_id)
                image_urls.append(presigned)
            except Exception:
                continue
    except Exception:
        image_urls = []

    return {
        "extracted": extracted_sorted,
        "summary_text": summary_text,
        "tables": table_entries,
        "images": image_urls,
    }


def _build_introduction(doc_meta: Dict, content: Dict) -> str:
    intro_page = next((p for p in content["extracted"] if p.get("page_number") == 1), None)
    intro_text = (intro_page or content["extracted"][0])["fe_text"] if content["extracted"] else ""
    intro_text = intro_text.strip()
    if intro_text:
        intro_text = textwrap.shorten(intro_text, width=2000, placeholder="...")
    heading = f"## Introduction\n\n"
    body = intro_text or "No introduction text could be extracted from the document."
    return heading + body


def _build_clinical_findings(content: Dict) -> str:
    findings_chunks: List[str] = []
    for page in content["extracted"]:
        text = (page.get("fe_text") or "").strip()
        lower = text.lower()
        if any(keyword in lower for keyword in ["finding", "clinical", "efficacy", "safety"]):
            findings_chunks.append(text)

    heading = "## Clinical Findings\n\n"
    if not findings_chunks:
        return heading + "No specific clinical findings section could be reliably extracted from the document.\n"

    # Use exact text from the document (no rewriting)
    body = "\n\n".join(findings_chunks)
    return heading + body


def _build_patient_tables(content: Dict) -> str:
    heading = "## Patient Tables\n\n"
    if not content["tables"]:
        return heading + "No patient tables were detected in the processed document.\n"

    lines = []
    for table in content["tables"]:
        lines.append(
            f"- Table {table.get('table_number')} (page {table.get('page_number')}): {table.get('url')}"
        )
    return heading + "\n".join(lines)


def _build_graphs_and_charts(content: Dict) -> str:
    heading = "## Graphs & Charts\n\n"
    if not content["images"]:
        return heading + "No graphs or charts were detected in the processed document.\n"

    lines = []
    for idx, url in enumerate(content["images"], start=1):
        lines.append(f"![Figure {idx}]({url})")
    return heading + "\n".join(lines)


def _build_raw_body_for_summary(content: Dict) -> str:
    # Use the full extracted text as the basis for summarisation
    if not content["extracted"]:
        return ""
    joined = "\n\n".join((p.get("fe_text") or "").strip() for p in content["extracted"])
    # Avoid over-long prompts
    return textwrap.shorten(joined, width=12000, placeholder="...")


def _build_summary_prompt(raw_body: str, instructions: Optional[str]) -> List[Dict[str, str]]:
    base_system = (
        "You are a clinical summarisation assistant. "
        "Generate a concise, clinically accurate medical report summary based ONLY on the provided text. "
        "Do not invent facts; do not introduce information that is not explicitly supported."
    )
    user_parts = [
        "Summarise the medical content below into a short, structured summary suitable for a clinical report.",
    ]
    if instructions and instructions.strip():
        user_parts.append(f"Additional user instructions: {instructions.strip()}")
    user_parts.append("\n---\nDocument content:\n")
    user_parts.append(raw_body)

    return [
        {"role": "system", "content": base_system},
        {"role": "user", "content": "\n".join(user_parts)},
    ]


async def _build_summary_section(content: Dict, instructions: Optional[str]) -> str:
    heading = "## Summary\n\n"
    raw_body = _build_raw_body_for_summary(content)
    if not raw_body:
        return heading + "No content was available to generate a summary.\n"

    messages = _build_summary_prompt(raw_body, instructions)
    response = _openai_client.chat.completions.create(
        model=_openai_settings.OPENAI_API_MODEL,
        messages=messages,
        temperature=0.3,
    )
    summary_text = (response.choices[0].message.content or "").strip()
    return heading + summary_text


def _normalise_section_id(section: str) -> str:
    return section.strip().lower().replace(" ", "_")


@router.post("/reports/generate", response_model=ReportGenerationResponse)
async def generate_report(request: ReportGenerationRequest):
    """
    Generate a structured medical report.

    Modes:
    - scope == "single"  -> current/selected document only (optionally by documentId)
    - scope == "combined" -> aggregate across all processed documents for this user

    Behaviour:
    - Uses ONLY the user's processed documents (no external sources).
    - For most sections, inserts exact text/tables/images as extracted from the documents.
    - For the 'summary' section, uses an LLM to generate a concise summary based on the raw text.
    """
    if not request.sections:
        raise HTTPException(status_code=400, detail="At least one section is required")

    ready_docs = await _get_user_ready_docs(request.userId)

    # Determine which documents to include
    docs_to_use: List[Dict] = []
    if request.scope == "combined":
        docs_to_use = ready_docs
    else:
        # "single" – either specific documentId or most recent
        if request.documentId:
            match = next((d for d in ready_docs if d.get("id") == request.documentId), None)
            if not match:
                raise HTTPException(
                    status_code=404,
                    detail="Requested documentId was not found among the user's processed documents.",
                )
            docs_to_use = [match]
        else:
            # default to most recent document
            docs_to_use = [ready_docs[0]]

    # Collect content for each selected document
    doc_contents: List[Dict] = []
    for meta in docs_to_use:
        content = await _collect_document_content(meta["id"])
        doc_contents.append({"meta": meta, "content": content})

    # Build sections in the requested order
    section_blocks: List[str] = []
    for raw_section in request.sections:
        sid = _normalise_section_id(raw_section)

        if sid == "introduction":
            parts = []
            for item in doc_contents:
                meta = item["meta"]
                content = item["content"]
                heading = _build_introduction(meta, content)
                # If combined, prefix with document name
                if len(doc_contents) > 1:
                    heading = f"### {meta.get('filename', meta.get('id'))}\n\n" + heading
                parts.append(heading)
            section_blocks.append("\n\n".join(parts))

        elif sid == "clinical_findings":
            parts = []
            for item in doc_contents:
                meta = item["meta"]
                content = item["content"]
                block = _build_clinical_findings(content)
                if len(doc_contents) > 1:
                    block = f"### {meta.get('filename', meta.get('id'))}\n\n" + block
                parts.append(block)
            section_blocks.append("\n\n".join(parts))

        elif sid in ("patient_tables", "patient_table", "tables"):
            parts = []
            for item in doc_contents:
                meta = item["meta"]
                content = item["content"]
                block = _build_patient_tables(content)
                if len(doc_contents) > 1:
                    block = f"### {meta.get('filename', meta.get('id'))}\n\n" + block
                parts.append(block)
            section_blocks.append("\n\n".join(parts))

        elif sid in ("graphs", "graphs_&_charts", "graphs_and_charts", "graphs_charts"):
            parts = []
            for item in doc_contents:
                meta = item["meta"]
                content = item["content"]
                block = _build_graphs_and_charts(content)
                if len(doc_contents) > 1:
                    block = f"### {meta.get('filename', meta.get('id'))}\n\n" + block
                parts.append(block)
            section_blocks.append("\n\n".join(parts))

        elif sid == "summary":
            # For summary, build a combined summary across all selected docs
            if len(doc_contents) == 1:
                section_blocks.append(
                    await _build_summary_section(doc_contents[0]["content"], request.instructions)
                )
            else:
                # Build a single summary from concatenated raw text of all docs
                combined_body_parts: List[str] = []
                for item in doc_contents:
                    combined_body_parts.append(_build_raw_body_for_summary(item["content"]))
                combined_body = "\n\n".join(p for p in combined_body_parts if p)
                heading = "## Summary\n\n"
                if not combined_body:
                    section_blocks.append(heading + "No content was available to generate a summary.\n")
                else:
                    messages = _build_summary_prompt(combined_body, request.instructions)
                    response = _openai_client.chat.completions.create(
                        model=_openai_settings.OPENAI_API_MODEL,
                        messages=messages,
                        temperature=0.3,
                    )
                    summary_text = (response.choices[0].message.content or "").strip()
                    section_blocks.append(heading + summary_text)

        else:
            # Fallback: include a heading and note that this is not yet specialised
            title = raw_section.strip() or "Section"
            section_blocks.append(f"## {title}\n\n(This section is not yet specialised; no content extracted.)")

    content_markdown = "\n\n".join(section_blocks)
    report_id = str(uuid.uuid4())
    _REPORT_STORE[report_id] = content_markdown

    return ReportGenerationResponse(report_id=report_id, content=content_markdown)


@router.get("/reports/{report_id}/download")
async def download_report(report_id: str):
    """
    Download endpoint for a previously generated report.

    For now this returns the stored markdown content as JSON; the frontend can
    later turn this into a PDF if needed.
    """
    content = _REPORT_STORE.get(report_id)
    if not content:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "report_id": report_id,
        "content": content,
    }
