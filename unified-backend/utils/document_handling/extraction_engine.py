from io import BytesIO, StringIO
from time import time
import fitz
import pandas as pd
import json
from ultralyticsplus import YOLO
from PIL import Image
from services.s3host import current_s3_client
from utils.document_handling.logger import log
from models.images import ImageModel, image_repo  # Update import
from models.tables import TableModel, table_repo
import torch
from PIL import Image
import io
import os 

async def extract_text_from_pdf_data_for_vectorisation(pdf_content: bytes, pdf_name: str, userId:str) -> str:
    """
    Asynchronously extract text from PDF content.
    
    Args:
        pdf_content (bytes): The PDF file content as bytes
        pdf_name (str): Name of the PDF file
    
    Returns:
        str: Extracted and formatted text from the PDF
    """
    pdf_document = None
    try:
        # TEXT EXTRACTION INTO DATAFRAME FOR HIGHLIGHTS
        highlights_helper_table = []
        pdf_document = fitz.open(stream=pdf_content, filetype="pdf")
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            lines = page.get_text("dict")["blocks"]
 
            line_counter = 1
            for block in lines:
                for line in block.get("lines", []):
                    line_text = " ".join([span["text"] for span in line["spans"]]).strip()
                    if line_text:
                        #get bounding box from the line itself
                        x0 = min([span["bbox"][0] for span in line["spans"]])
                        y0 = min([span["bbox"][1] for span in line["spans"]])
                        x1 = max([span["bbox"][2] for span in line["spans"]])
                        y1 = max([span["bbox"][3] for span in line["spans"]])
 
                        highlights_helper_table.append({
                            "Page Number": page_num + 1,
                            "Line Number": line_counter,
                            "Content": line_text,
                            "Coordinates": (x0, y0, x1, y1)
                        })
                        line_counter += 1

        df = pd.DataFrame(highlights_helper_table)
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_bytes = csv_buffer.getvalue().encode("utf-8")  # Convert to bytes

        # Define the key
        key = f'DB/USERS/{userId}/highlight_helper_tables/{pdf_name}.csv'

        # Upload using AsyncS3Host
        await current_s3_client.save_to_s3(csv_bytes, key)

        # TEXT EXTRACTION FOR VECTORISATION
        extracted_text = []
        extracted_text.append(f'DOCUMENT <{pdf_name}> CONTENTS STARTS HERE')
       
        for page_num in range(len(pdf_document)):
            page = pdf_document.load_page(page_num)
            page_text = page.get_text("text") or ""
            page_text = page_text.replace("©", "").replace("�", "")
           
            extracted_text.append(f'PAGE NUMBER {page_num + 1} STARTS HERE')
            extracted_text.append(page_text.strip())
            extracted_text.append(f'PAGE NUMBER {page_num + 1} ENDS HERE')
       
        extracted_text.append(f'DOCUMENT <{pdf_name}> CONTENTS ENDS HERE')
        
        output = "\n".join(extracted_text)
        return output

    except Exception as e:
        raise Exception(f"Error extracting text from PDF {pdf_name}: {str(e)}")
    
    finally:
        if pdf_document:
            pdf_document.close()


async def extract_and_save_images_from_pdf(document_content: bytes, document_name: str, document_id: str, userId: str):
    """
    Extract images from PDF and save them to S3 under a folder named after the PDF filename.

    Args:
        document_content (bytes): The PDF file content as bytes
        document_name (str): Name of the PDF file (e.g., "mydoc.pdf")
        document_id (str): Unique identifier for the document
        userId (str): User identifier

    Returns:
        bool: True if images were extracted successfully
    """
    try:
        pdf_document = fitz.open(stream=document_content, filetype="pdf")
        image_count = 0
        image_metadata = []

        
        pdf_name = os.path.splitext(document_name)[0]

        # Iterate through each page
        for page_num, page in enumerate(pdf_document):
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]
                base_image = pdf_document.extract_image(xref)
                image_bytes = base_image["image"]
                ext = base_image["ext"]

                image_filename = f"pg{page_num+1}_img{img_index+1}.{ext}"
                s3_key = f'DB/USERS/{userId}/document_images/{pdf_name}/{image_filename}'
                await current_s3_client.save_to_s3(image_bytes, s3_key)

                image_id=f'{pdf_name}_pg{page_num+1}_img{img_index+1}.{ext}'
                await image_repo.add_new_image(ImageModel(id=image_id,document_id=document_id))

        log(f"Extracted {image_count} images from document {document_name}")
        return True

    except Exception as e:
        log(f"Error extracting images from PDF {document_name}: {str(e)}")
        return False

    finally:
        if 'pdf_document' in locals() and pdf_document:
            pdf_document.close()


async def extract_and_save_tables_from_pdf(document_content: bytes, document_name: str, document_id: str, userId: str) -> list:
    """
    Asynchronously extracts tables from PDF content using YOLOv8 model.
    
    Args:
        document_content (bytes): The PDF file content as bytes
        document_name (str): Name of the PDF file
        document_id (str): Unique identifier for the document
        userId (str): User identifier
    
    Returns:
        list: List of S3 paths to extracted table images
    """

    try:
        # Patch torch.load to force weights_only=False for compatibility
        original_load = torch.load
        def safe_load(f, map_location=None, pickle_module=None, weights_only=None, **kwargs):
            return original_load(f, map_location=map_location, pickle_module=pickle_module, 
                                weights_only=False, **kwargs)
        torch.load = safe_load

        # Initialize YOLO model
        model = YOLO('keremberke/yolov8m-table-extraction')
        model.overrides['conf'] = 0.25
        model.overrides['iou'] = 0.45
        model.overrides['agnostic_nms'] = False
        model.overrides['max_det'] = 1000

        extracted_tables = []
        doc = fitz.open(stream=document_content, filetype="pdf")

        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            pix = page.get_pixmap(dpi=300)
            image = Image.open(io.BytesIO(pix.tobytes("png")))

            # Detect tables
            results = model.predict(image)
            boxes = results[0].boxes.xyxy.cpu().numpy()

            # Process each detected table
            for i, (x1, y1, x2, y2) in enumerate(boxes):
                table_crop = image.crop((x1, y1, x2, y2))
                
                # Convert table image to bytes
                img_byte_arr = io.BytesIO()
                table_crop.save(img_byte_arr, format='PNG')
                img_byte_arr = img_byte_arr.getvalue()

                # Define S3 path and save
                s3_key = f'DB/USERS/{userId}/document_tables/{document_name}/page_{page_num+1}_table_{i+1}.png'
                await current_s3_client.save_to_s3(img_byte_arr, s3_key)
                
                # Create and save table metadata
                table_model = TableModel(
                    id=s3_key,
                    document_id=document_id,
                    page_number=page_num + 1,
                    table_number=i + 1
                )
                await table_repo.add_new_table(table_model)
                
                extracted_tables.append(s3_key)
                log(f"Saved table: {s3_key}")
                
                table_crop.close()
            
            image.close()
            pix = None  # Release pixmap memory

        return extracted_tables

    except Exception as e:
        log(f"Error extracting tables from PDF {document_name}: {str(e)}")
        raise

    finally:
        if 'doc' in locals():
            doc.close()


