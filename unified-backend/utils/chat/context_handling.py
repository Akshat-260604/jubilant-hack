import re
from utils.chat.logger import log
from services.qdrant_host import current_qdrant_client
from lib.brain import use_brain
from utils.chat.vectorise_text import vectorise_text
from configs.config import ollama_settings

DOCUMENT_TEXT_COLLECTION_NAME = 'creator'

async def perform_retrieval_in_collection(query_text: str, document_ids: list[str]):
    """
    Perform vector similarity search in the Qdrant collection with dynamic top-k determination.

    Args:
        query_text (str): The query text to search for
        document_ids (list[str]): List of document IDs to filter the search results

    Returns:
        str: Retrieved text content from the matched documents concatenated together
    """
    query_embedding = await vectorise_text(query_text)

    filter_condition = None
    if document_ids:
        filter_condition = {
            "must": [
                {
                    "key": "document_id",
                    "match": {
                        "any": document_ids
                    }
                }
            ]
        }

    max_top_k = 1000

    search_result = current_qdrant_client.search(
        collection_name=DOCUMENT_TEXT_COLLECTION_NAME,
        query_vector=query_embedding,
        limit=max_top_k,
        query_filter=filter_condition
    )

    total_points_found = len(search_result)

    binary_prompt = f""" 
        YOU ARE A QEURY ROUTER. YOU CAN ONLY RESPOND IN 0 and 1. You don't know how to write or speak in english.
        Only language you know is Binary, and that too 0 and 1 Only.

        Response would be only single digit. There is no need to write any additional text or explaination

        You are part of a Retreival Augmented Generation framework. Where based on your output, it is decided 
        how many top results are required to fulfil a query.

        Check the following query and return 0 or 1.

        Say 1 if the query requires more retrieval results.
        Say 0 if the query does not require many retreival results.

        For example: Queries like Summary, Summarize, and multi intent queries require a lot of retrieval results.

        QUERY### {query_text}
    """
    
    range_bound_prompt = f""" 
        You are part of a Retreival Augmented Generation framework. Where based on your output, retreival happens.
        You are responsible for deciding the topK value. Top K Value typically is used to fetch number of datapoints from the 
        Vector Space.

        You can only respond in numerics. Any number between 0 to 35. There is no need to write any additional text or explaination

        # How to Decide top K:
        Generally queries that have multiple intents and is required to cover a wider aspect of a document, the topK value is higher.
        When the query is concise and direct, top K value is generally lower.

        # Keep in Mind:
        Higher Top K Values result in Higher throughput times, think wisely and respond in numerics.

        QUERY### {query_text}
    """

    try:
        messages = [{"role": "user", "content": range_bound_prompt}]
        output = await use_brain(
            messages=messages,
            model=ollama_settings.OLLAMA_ANALYTICAL_MODEL2,
            stream=True
        )

        num_str = ""
        async for char in output:
            if char.isdigit():
                num_str += char
            else:
                break

        num_val = int(num_str)
        if 0 <= num_val <= 35:
            dynamic_top_k = num_val
        else:
            raise TypeError
    except:
        messages = [{"role": "user", "content": binary_prompt}]
        output = await use_brain(
            messages=messages,
            model=ollama_settings.OLLAMA_ANALYTICAL_MODEL2,
            stream=True
        )

        output_str = ""
        async for chunk in output:
            output_str += chunk

        num_str = ""
        for char in output_str:
            if char.isdigit():
                num_str += char
            else:
                break

        if num_str == "1":
            dynamic_top_k = 25
        else:
            if total_points_found < 50:
                dynamic_top_k = 20
            elif total_points_found < 100:
                dynamic_top_k = 25
            else:
                dynamic_top_k = 35

    log(f'Dynamic top_k determined: {dynamic_top_k}')

    retrieved_text = ""
    iterator = min(dynamic_top_k, total_points_found)
    for i in range(iterator):
        retrieved_text += search_result[i].payload["text"]

    return retrieved_text


async def revamp_context(context: str) -> str:
    """
    Reformat the context string into a structured document format.

    Args:
        context (str): Raw context string containing document content with page markers

    Returns:
        str: Formatted context string with document names and page numbers in the format:
            "**Document: doc_name | PAGE_number**\n\ntext content\n\n"
    """
    log('Request received to revamp context')
    result = []
    pages = context.split('==')

    for page in pages:
        if page.strip():
            doc_name_start = page.find('Document_Name ') + len('Document_Name ')
            doc_name_end = page.find(',', doc_name_start)
            doc_name = page[doc_name_start:doc_name_end].strip()

            page_number_start = page.find('PAGE_') + len('PAGE_')
            page_number_end = page.find('--', page_number_start)
            page_number = page[page_number_start:page_number_end].strip()

            text_start = page.find('--') + len('--')
            text = page[text_start:].strip()

            result.append(f"**Document: {doc_name} | PAGE_{page_number}**\n\n{text}\n\n")

    output = ''.join(result)
    log('Context has been revamped')
    return output


async def retrieve_context(query: str, document_ids: list):
    """
    Retrieve and format relevant context from documents based on the query.

    Args:
        query (str): The search query text
        document_ids (list): List of document IDs to search within

    Returns:
        tuple[str, str]: A tuple containing:
            - revamped_context (str): Formatted context with document and page markers
            - final_formatted_context (str): Cleaned context with page markers removed
    """
    log(f'Request received to retrieve context for documents {document_ids}')
    retrieved_text = await perform_retrieval_in_collection(query, document_ids)

    clutter = ['"', "query", ":", "'", query, "result", "text=", "Helpful", "Answer", "{", "}", "Question"]
    result_text = retrieved_text
    for element in clutter:
        result_text = result_text.replace(element, "")

    page_marker_pattern = r"(PAGE NUMBER \d+ (?:STARTS|ENDS) HERE)"
    final_formatted_context = re.sub(page_marker_pattern, "\n", result_text)

    revamped_context = await revamp_context(context=final_formatted_context)

    log('Context retrieval successfully completed')
    return revamped_context, final_formatted_context
