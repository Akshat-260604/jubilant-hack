from time import time
from langchain.text_splitter import RecursiveCharacterTextSplitter

from utils.document_handling.logger import log

def finalize_document_chunks(document_name, pdf_extracted_text):
    '''
    Finalizes the document chunks by adding metadata and splitting them into smaller chunks.

    Args:
        document_name (str): The name of the document.
        pdf_extracted_text (dict): A dictionary containing the extracted text for each page of the document.
            The keys are the page numbers, and the values are the corresponding text.

    Returns:
        list: A list of marked chunks, where each chunk is a string containing the following metadata:
            - Document_Name: The name of the document.
            - Total_Pages: The total number of pages in the document.
            - Page_Number: The page number of the current chunk.
            - Content: The text content of the current chunk.
    '''
    splitter = RecursiveCharacterTextSplitter(chunk_size=512, chunk_overlap=150)
    marked_chunks = []

    for page, text in pdf_extracted_text.items():
        chunks = splitter.split_text(text)
        for idx, chunk in enumerate(chunks):
            marker = (
                f"Document_Name {document_name}, Total_Pages {len(pdf_extracted_text)}, {page}\n--{chunk}=="
            )
            marked_chunks.append(marker)

    return marked_chunks


def create_optimized_marked_chunks(extracted_text: str):
    '''
    Creates optimized marked chunks from the extracted text.

    This function processes the extracted text from a PDF document and groups the text by document and page.
    It then creates marked chunks with metadata, including the document name and page number, and returns a list of these chunks.

    Args:
        extracted_text (str): The extracted text from the PDF document.

    Returns:
        list: A list of optimized marked chunks, where each chunk is a dictionary containing the following keys:
            - 'content': The text content of the chunk.
            - 'metadata': A dictionary containing metadata about the chunk, including 'document_name' and 'page_number'.
    '''
    start_time = time()
    # Initialize variables
    all_documents_chunks = []
    lines = extracted_text.split("\n")
    current_page = None
    current_text = []
    document_name = None
    pdf_extracted_text = {}

    # Process lines to group text by document and page
    for line in lines:
        if line.startswith("DOCUMENT") and "CONTENTS STARTS HERE" in line:
            if document_name:  # Finalize the previous document
                if current_page:
                    pdf_extracted_text[current_page] = "\n".join(current_text)
                all_documents_chunks.extend(finalize_document_chunks(document_name, pdf_extracted_text))
                pdf_extracted_text = {}
                current_text = []

            # Extract the new document name
            document_name = line.split("<")[1].split(">")[0]

        elif line.startswith("PAGE NUMBER") and "STARTS HERE" in line:
            if current_page is not None:
                pdf_extracted_text[current_page] = "\n".join(current_text)
            current_page = f"PAGE_{line.split()[2]}"
            current_text = []

        elif line.startswith("PAGE NUMBER") and "ENDS HERE" in line:
            if current_page is not None:
                pdf_extracted_text[current_page] = "\n".join(current_text)
            current_page = None

        elif line.startswith("DOCUMENT") and "CONTENTS ENDS HERE" in line:
            if current_page is not None:
                pdf_extracted_text[current_page] = "\n".join(current_text)
            if document_name:
                all_documents_chunks.extend(finalize_document_chunks(document_name, pdf_extracted_text))
            pdf_extracted_text = {}
            current_text = []
            current_page = None
            document_name = None

        else:
            current_text.append(line)

    # Ensure the last document is processed
    if document_name and current_page is not None:
        pdf_extracted_text[current_page] = "\n".join(current_text)
        all_documents_chunks.extend(finalize_document_chunks(document_name, pdf_extracted_text))
    end_time = time()
    processing_time_taken = end_time - start_time
    log(f"The Function create_optimized_marked_chunks completed in {processing_time_taken} seconds")
    return all_documents_chunks