
import uuid
import asyncio
import anyio
from fastapi import HTTPException
import multiprocessing
import uuid
from time import time
from io import BytesIO
from numpy import array
from pathlib import Path
import fitz
from fitz import open, Matrix  # pymupdf not fitz
from qdrant_client.http.models import PointStruct, VectorParams, Distance
import traceback
from utils.document_handling.logger import log
from services.s3host import current_s3_client
from services.document_encoder import DocumentEncoder
from services.qdrant_host import current_qdrant_client
from services.ollama_host import current_ollama_client
from utils.document_handling.chunker import create_optimized_marked_chunks
from utils.document_handling.extraction_engine import extract_and_save_images_from_pdf
from utils.document_handling.generate_save_document_ouline import generate_and_save_document_outline
from utils.document_handling.extraction_engine import extract_and_save_tables_from_pdf
from utils.document_handling.preview_pdf import save_document_preview_images

from utils.document_handling.extraction_engine import ( 
                                     extract_text_from_pdf_data_for_vectorisation)

from utils.document_handling.save_document_data_to_DB import (
                                            mark_doc_status_in_db, 
                                            )


DOCUMENT_TEXT_COLLECTION_NAME = 'creator'


def initialize_collection(collection_name: str) -> bool:
    """
    Initialize a collection if it doesn't exist.
    Returns True if collection was created, False if it already existed.
    """
    collections = current_qdrant_client.get_collections().collections
    exists = any(collection.name == collection_name for collection in collections)
    vector_size = 768  # specifically for nomic embed text
    if not exists:
        current_qdrant_client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=Distance.COSINE
            )
        )
        return True
    return False

def add_document_to_collection(document_extracted_text: str, document_id: str) -> str:
    """
    Add a document to an existing collection.
    Returns the document_id used for storage.
    """
    start_time = time()
    chunks = create_optimized_marked_chunks(document_extracted_text)
    embed_time=time()
    embeddings = current_ollama_client.embed_documents(chunks)
    log(f"Embedding were started at {embed_time} and took {time() - embed_time} seconds")
    embeddings = array(embeddings)
    
    # Initialize collection if it doesn't exist
    initialize_collection(DOCUMENT_TEXT_COLLECTION_NAME)
    
    # Create points with document ID in payload
    points = [
        PointStruct(
            id=uuid.uuid4().int & (1<<63)-1,
            vector=embedding.tolist(),
            payload={
                "text": chunk,
                "document_id": document_id,
                "chunk_index": i
            }
        )
        for i, (embedding, chunk) in enumerate(zip(embeddings, chunks))
    ]
    
    log('Uploading document embeddings to collection')

    # Upload points to collection
    current_qdrant_client.upsert(
        collection_name=DOCUMENT_TEXT_COLLECTION_NAME,
        points=points
    )
    log('Document embeddings have been saved to collection')

    end_time = time()
    processing_time_taken = end_time - start_time
    log(f"The Function add_document_to_collection was started at {start_time} and completed in {processing_time_taken} seconds")
    return document_id

async def vectorise_document(document_content, document_id, document_name, userId):
    start_time = time()
    # handle the collection's existence state
    initialize_collection(collection_name=DOCUMENT_TEXT_COLLECTION_NAME)
    
    # Extract text from the document for vectorisation
    document_extracted_text = await extract_text_from_pdf_data_for_vectorisation(
        pdf_content=document_content,
        pdf_name=document_name,
        userId=userId
    )

    add_document_to_collection(document_extracted_text, document_id)

    end_time = time()
    processing_time_taken = end_time - start_time
    log(f"The Function vectorise_document was started at {start_time} and completed in {processing_time_taken} seconds")
    return True

async def process_document(document_content: bytes, fileName: str, userId: str, document_id: str):
    """
    Process document by running all tasks in parallel, handling both async and sync functions
    """
    start_time = time()
    log(f'Request received to process document: {fileName}')
    document_name = Path(fileName).stem

    status = 'done'

    # Create tasks list with appropriate handling for sync vs async functions
    tasks = [
        # extract_text_from_pdf_data_for_frontend(pdf_content=document_content, pdf_name=document_name),
        vectorise_document(document_content, document_id, document_name, userId),
        save_document_preview_images(document_content, document_name,document_id, userId),
        generate_and_save_document_outline(document_content, document_name, userId, document_id),
        extract_and_save_tables_from_pdf(document_content, document_name, document_id, userId),
        extract_and_save_images_from_pdf(document_content, document_name, document_id, userId)
    ]

    # Log information about each task
    for i, task in enumerate(tasks):
        task_name = task.__name__ if hasattr(task, '__name__') else f"Task {i+1}"
        log(f"Launching child process for {task_name} (PID: {multiprocessing.current_process().pid})")

    try:
        # Run all tasks concurrently and wait for them to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check results and handle any exceptions
        success = True
        tables_extracted = False
        images_extracted = False

        for i, result in enumerate(results):
            task_name = tasks[i].__name__ if hasattr(tasks[i], '__name__') else f"Task {i+1}"
            if isinstance(result, Exception):
                log(f"{task_name} (PID: {multiprocessing.current_process().pid}) failed with error: {str(result)}")
                success = False
            else:
                # Check if the last task (image extraction) was successful
                if i == len(tasks) - 1:
                    images_extracted = result

        end_time = time()
        processing_time_taken = end_time - start_time

        if success and images_extracted:
            await mark_doc_status_in_db("done", document_id, str(processing_time_taken))
            output_response = f"New document processed successfully | Time taken: {processing_time_taken}"
        elif success and not images_extracted:
            await mark_doc_status_in_db("done", document_id, str(processing_time_taken))
            output_response = f"Document processed successfully, but image extraction failed | Time taken: {processing_time_taken}"
        else:
            await mark_doc_status_in_db("error", document_id, str(processing_time_taken))
            output_response = f"Document processing partially failed | Time taken: {processing_time_taken}"

        log(output_response)
        return output_response
    except Exception as e:
        end_time = time()
        processing_time_taken = end_time - start_time
        await mark_doc_status_in_db("error", document_id, str(processing_time_taken))

        error_message = f"Document processing failed: {str(e)} | Time taken: {processing_time_taken}"
        log(error_message)
        return error_message