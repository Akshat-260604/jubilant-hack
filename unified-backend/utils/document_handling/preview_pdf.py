import fitz  # PyMuPDF
import io
from PIL import Image
from services.s3host import current_s3_client
from utils.document_handling.logger import log
from models.preview import PreviewModel, preview_repo

async def save_document_preview_images(
    pdf_content: bytes,
    document_name: str,
    document_id: str,
    userId: str,
    dpi: int = 150,
    image_format: str = 'PNG'
):
    """
    Convert each page of a PDF to an image and save to S3 in PNG format.

    Args:
        pdf_content (bytes): The PDF file content as bytes
        document_name (str): Name of the PDF file
        document_id (str): Unique identifier for the document
        userId (str): User identifier
        dpi (int): Resolution for the output images (default: 150)
        image_format (str): Image format ('PNG' by default)

    Returns:
        list: List of S3 keys for saved images
    """
    try:
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        saved_previews = []

        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            mat = fitz.Matrix(dpi / 72, dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            img = Image.open(io.BytesIO(pix.tobytes("png")))

            # Convert image to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format=image_format)
            img_bytes = img_byte_arr.getvalue()

            # S3 key
            s3_key = f'DB/USERS/{userId}/document_previews/{document_name}/page_{page_num+1}.{image_format.lower()}'
            await current_s3_client.save_to_s3(img_bytes, s3_key)

            # Save preview metadata
            preview_model = PreviewModel(
                id=s3_key,
                document_id=document_id,
                page_number=page_num + 1
            )
            await preview_repo.add_new_preview(preview_model)

            saved_previews.append(s3_key)
            log(f"Saved preview image: {s3_key}")

            img.close()
            pix = None

        return saved_previews

    except Exception as e:
        log(f"Error generating PDF previews for {document_name}: {str(e)}")
        raise

    finally:
        if 'pdf_document' in locals():
            pdf_document.close()
