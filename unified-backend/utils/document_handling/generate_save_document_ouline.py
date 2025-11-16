

import asyncio
import re
import json
from time import time
import fitz
from io import BytesIO
from PyPDF2 import PdfReader

from utils.document_handling.logger import log
from services.s3host import current_s3_client
from utils.document_handling.save_document_data_to_DB import save_document_outline_to_db
from lib.brain import use_brain


def extract_text_from_pdf_data(pdf_data, pdf_name: str):
    # Wrap the binary data in a BytesIO object to make it file-like
    pdf_file = BytesIO(pdf_data)

    # Initialize a PdfReader with the file-like object
    pdf_reader = PdfReader(pdf_file)

    raw_text = ''''''

    # Iterate through each page and extract text
    raw_text += f'\nDOCUMENT <{pdf_name}> CONTENTS STARTS HERE\n'
    for page_num in range(len(pdf_reader.pages)):
        page = pdf_reader.pages[page_num]
        page_text = page.extract_text()

        # Replace problematic characters
        page_text = page_text.replace("©", "").replace("�", "")

        # Add markers to the text
        raw_text += f'PAGE NUMBER {page_num + 1} STARTS HERE\n'
        raw_text += page_text
        raw_text += f'\nPAGE NUMBER {page_num + 1} ENDS HERE\n'

    raw_text += f'\nDOCUMENT <{pdf_name}> CONTENTS ENDS HERE\n'

    # Clean the text to remove empty lines
    lines = raw_text.splitlines()
    non_empty_lines = [line + '\n' for line in lines if line.strip()]
    cleaned_text = ''.join(non_empty_lines)

    return cleaned_text


def extract_page_image(pdf_data, page_number):
    try:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
        
        if page_number < 1 or page_number > pdf_document.page_count:
            return None
        
        page = pdf_document.load_page(page_number - 1)
        
        # set the zoom factor
        zoom_x = 2.0
        zoom_y = 2.0
        matrix = fitz.Matrix(zoom_x, zoom_y)
        
        # create the pixmap with the specified resolution
        pix = page.get_pixmap(matrix=matrix)
        
        # return the image data as bytes
        return pix.tobytes("png")

    except Exception as e:
        log(f"An error occurred in generating page image for highlighting | ERROR: {e}")
        return None


async def process_page_hint(pdf_data, page_number, hint):
    image_data = extract_page_image(pdf_data, page_number)
    
    if not image_data:
        log(f"Failed to generate image for page {page_number}")
        return None

    json_structure = {
        'start_text': 'first two words of a paragraph/sentence in the given image that was used to generate the given hint/overview',
        'text_length': 'an integer representing the number of words in the identified paragraph which will be used to highlight the complete paragraph'
    }

    user_message = f"The assistant is an expert OCR. Assistant will be provided with the image of a single page from a pdf document and a document overview in the form of a hint. The hint/document overview was generated using the text written in the provided image. Now the assistant's task is to reverse engineer the sources of the given hint from the given image. To do that, the output structure is restricted to a json that is\n{json_structure}\nHere is the hint:\n{hint}. The assistant will only return a JSON and nothing else. This outcome will be used to annotate/highlight that part of the document. You will extract the text as it is without changing any text, user wants all original. You will not ignore commas, full stop and other punctuation."
    
    messages = [
        {
            "role": "user",
            "content": [
                {"image": {"format": "png", "source": {"bytes": image_data}}},
                {"text": user_message},
            ],
        }
    ]

    try:
        response_text = await use_brain(messages=messages, stream=False, inference="openai")
        
        # Parse JSON response with error handling
        try:
            response_data = json.loads(response_text)
            extracted_text = list(response_data.values())[0]
            word_count = list(response_data.values())[1]
            return {"page_number": page_number, "start_text": extracted_text, "word_count": word_count}
        except (json.JSONDecodeError, IndexError, KeyError) as e:
            log(f"Error parsing JSON response for page {page_number}: {e}")
            log(f"Response was: {response_text}")
            return None
            
    except Exception as e:
        log(f"Error processing page hint for page {page_number}: {e}")
        return None


async def highlight_text_in_pdf_with_vision(pdf_data, pdf_name, page_hints, userId, document_id):
    added_highlights = 0
    highlighted_pages_set = set()
    highlighted_images_ids = []
    image_output_dir_key = f'DB/USERS/{userId}/document_outline_sources/{pdf_name}'

    try:
        pdf_document = fitz.open(stream=pdf_data, filetype="pdf")

        for hint in page_hints:
            if not hint:  # Skip None results
                continue
                
            page_number = hint['page_number']
            start_text = hint['start_text']
            word_count = hint['word_count'] + 5  # give it some buffer

            if not isinstance(start_text, str):
                continue

            page = pdf_document.load_page(page_number - 1)
            words = page.get_text("words")

            start_words = start_text.split()
            start_length = len(start_words)

            start_index = None
            for i in range(len(words) - start_length + 1):
                try:
                    if all(words[i + j][4] == start_words[j] for j in range(start_length)):
                        start_index = i
                        break
                except IndexError:
                    continue

            if start_index is None:
                log(f"Could not find start text '{start_text}' on page {page_number}")
                continue

            # Highlight the start words
            for j in range(start_length):
                try:
                    rect = fitz.Rect(words[start_index + j][:4])
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=(1, 1, 0.5))  # yellow
                    highlight.update()
                    added_highlights += 1
                    highlighted_pages_set.add(page_number)
                except (IndexError, ValueError) as e:
                    log(f"Error highlighting word {j} on page {page_number}: {e}")
                    continue

            # Highlight additional words
            for i in range(start_index + start_length, min(start_index + start_length + word_count, len(words))):
                try:
                    rect = fitz.Rect(words[i][:4])
                    highlight = page.add_highlight_annot(rect)
                    highlight.set_colors(stroke=(1, 1, 0.5))
                    highlight.update()
                    added_highlights += 1
                    highlighted_pages_set.add(page_number)
                except (IndexError, ValueError) as e:
                    log(f"Error highlighting additional word {i} on page {page_number}: {e}")
                    continue

        # CONCURRENT UPLOADS START HERE
        upload_tasks = []

        for page_number in highlighted_pages_set:
            try:
                page = pdf_document.load_page(page_number - 1)
                pix = page.get_pixmap()

                image_bytes = BytesIO()
                image_bytes.write(pix.tobytes())
                image_bytes.seek(0)

                image_save_key = f"{image_output_dir_key}/Page_{page_number}.png"
                image_id = f'{document_id}_PN{page_number}_DOSI'
                highlighted_images_ids.append({"id": image_id, "page_number": page_number})

                upload_tasks.append(
                    current_s3_client.save_to_s3(file_data=image_bytes.getvalue(), key=image_save_key)
                )

                log(f'Scheduled upload for Page {page_number} highlighted image')
            except Exception as e:
                log(f"Error preparing upload for page {page_number}: {e}")
                continue

        if upload_tasks:
            await asyncio.gather(*upload_tasks, return_exceptions=True)

        log(f'Added {added_highlights} highlights and uploaded {len(highlighted_pages_set)} page images to S3.')
        return highlighted_images_ids

    except Exception as e:
        log(f"An error occurred while highlighting text: {e}")
        return []


async def get_and_save_outline_source_images(document_outline_source_pages, document_outline, pdf_data, pdf_name, userId, document_id):
    log('Request received to save document_outline source highlighted pdf')

    tasks = [
        process_page_hint(pdf_data, page, document_outline)
        for page in document_outline_source_pages
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    page_hints = [result for result in results if result and not isinstance(result, Exception)]

    highlighted_images_ids = await highlight_text_in_pdf_with_vision(pdf_data, pdf_name, page_hints, userId, document_id)

    return highlighted_images_ids


async def generate_and_save_document_outline(pdf_data, pdf_name, userId, document_id):
    log(f'Request received to generate document outline')
    start_time = time()
    
    try:
        pdf_text = extract_text_from_pdf_data(pdf_data=pdf_data, pdf_name=pdf_name)
    except Exception as e:
        log(f'Error extracting text from PDF: {e}')
        return False
   
    system_prompt = f'''The user will provide you with the extracted text from a document and your task is to generate a 600 word Document Overview of that document in markdown format. Make sure that you try to outline the following things:
    - Factual description and summary of Disease if any is present in the content (Can be Definition, Cause Effect, Characteristics, prognosis)
    - Factual description and summary of Therapy if any is present in the content (Definition, Mechanism, Purpose)
    - Factual description and summary of Clinical study if any is present in the content (Design, Duration, Blinding Study, Outcome)
    - Factual description and summary of Treatment if any is present in the content (Side Effects, Duration, Serious Side Effects)
    - Factual description and summary of Assessment if any is present in the content (Tool, Additional tests, Outcome), Insights(results , conclusion , discussion)
    - All the Important and relevant numbers from the text of the document

    Use the following markdown format:
    # Document {pdf_name} Overview

    ## Objective and Scope
    [Write all the content related to objective and scope here making sure that it is quantitative]

    ## Purpose
    [Write all the purpose related content of whatever is being discussed in the document here]

    ## Detailed Analysis
    [Write all the detailed analysis in bullet points]
    - Point 1
    - Point 2
    - Point 3

    ## Key Findings
    [Write all key findings with proper formatting]
    - **Response Rate:** [details]
    - **Median Time:** [details]
    - **Disease Progression:** [details]

    ## Claims
    [List all claims as bullet points]
    - Claim 1
    - Claim 2

    ## Observations
    [Write all quantitative observations]
    - Observation 1
    - Observation 2

    ## In-depth Analysis
    [Write data interpretation and quotes]
    > Important quotes and interpretations

    Follow the rules:
    1. Make sure that all content should be very detailed
    2. Make sure your response length is not less than 600 words
    3. Use proper markdown formatting (headings, bullet points, bold text, quotes)
    4. Do not mention the word count in your response
    5.Do not add the questions like let me know or anything extra in the end of the summary

    After your markdown formatted response, insert the page numbers as integers inside a python list in triple markdown quotes like this:
    ```
    [1, 2, 3, 4, 5]
    ```
    '''

    messages = [
        {"role": "user", "content": system_prompt},
        {"role": "user", "content": pdf_text}
    ]
    highlighted_images_ids = []

    try:
        # Fixed: Properly handle the async call
        document_outline = await use_brain(messages=messages, stream=False, inference="openai")
        print(document_outline)

        log(f'Document text outline generated in {time() - start_time} seconds')

        # Extract page numbers from document_outline with better error handling
        try:
            match = re.search(r'```\s*\[(\d+(?:,\s*\d+)*)\]\s*```', document_outline)
            if match:
                list_string = match.group(1)
                outline_source_pages = [int(num.strip()) for num in list_string.split(',')]
                document_outline = re.sub(r'```\s*\[.*?\]\s*```', '', document_outline, flags=re.DOTALL)
                highlighted_images_ids = await get_and_save_outline_source_images(
                    document_outline_source_pages=outline_source_pages,
                    document_outline=document_outline,
                    pdf_data=pdf_data,
                    pdf_name=pdf_name,
                    userId=userId,
                    document_id=document_id
                )
            elif "[" in document_outline and "]" in document_outline:
                fallback_match = re.search(r'\[\s*(\d+(?:,\s*\d+)*)\s*\]', document_outline)
                if fallback_match:
                    list_string = fallback_match.group(1)
                    outline_source_pages = [int(num.strip()) for num in list_string.split(',')]
                    document_outline = re.sub(r'\[\s*.*?\s*\]', '', document_outline, flags=re.DOTALL)
                    highlighted_images_ids = await get_and_save_outline_source_images(
                        document_outline_source_pages=outline_source_pages,
                        document_outline=document_outline,
                        pdf_data=pdf_data,
                        pdf_name=pdf_name,
                        userId=userId,
                        document_id=document_id
                    )
                else:
                    log('Unable to extract source page numbers from document outline.')
            else:
                log('No page numbers found in document outline.')
        except Exception as e:
            log(f'Error processing page numbers: {e}')

    except Exception as e:
        log(f'An error occurred in generation of document outline: Error: {e}')
        document_outline = "It seems the document you provided is so hefty, I couldn't quite digest it all to generate a document outline!"

    if not highlighted_images_ids:
        highlighted_images_ids = []

    try:
        await save_document_outline_to_db(
            userId=userId, 
            document_id=document_id, 
            document_outline=document_outline, 
            highlighted_images_ids=highlighted_images_ids
        )
    except Exception as e:
        log(f'Error saving document outline to database: {e}')
        return False
    
    end_time = time()
    processing_time_taken = end_time - start_time
    log(f"The Function generate_and_save_document_outline was started at {start_time} and completed in {processing_time_taken} seconds")
    
    return True


