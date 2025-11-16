import asyncio
import json
import re
import fitz  # PyMuPDF
from pathlib import Path
from fastapi import HTTPException
from time import time
from utils.chat.logger import log
from lib.brain import use_brain  
from configs.config import ollama_settings
from utils.chat.source_highlighter import save_source_highlights
from utils.chat.get_lay_term_glossary_prompt import get_lay_term_glossary_prompt
from utils.chat.rag_utils import create_specified_pages_dict, clean_sources, find_source_document_and_pages
from models.conversation import conversation_repo
from utils.chat.prompt import CONTENT_FORMAT_prompt
from models.highlight import highlight_repo,HighlightModel
from models.message import message_repo,MessageModel

async def remove_chip(text):
        # Remove occurrences of [Document: any name | PAGE_any number]
        """
        Remove all occurrences of [Document: any name | PAGE_any number] from the given text.

        This is used to remove document/page markers from the final answer.

        Args:
            text (str): Text to remove the markers from

        Returns:
            str: Text with all occurrences of [Document: any name | PAGE_any number] removed
        """
        cleaned_text = re.sub(r'\[Document:\s*.*?\s*\|\s*PAGE_\d+(?:,\s*PAGE_\d+)*\]', '', text)
        return cleaned_text


async def stream_final_answer(
        userId,
        document_ids,
        context,
        pdf_datas,
        pdf_count,
        user_query,
        context_id,
        creativity_percentage=0.7,
    ):
        highlight_tasks = []  # List to store highlight tasks

        log("Preparing final answer")
        log(context)

        ''''
          Args:
        userId (str): Unique identifier for the user.
        document_ids (List[str]): List of document IDs used in the query context.
        context (str): Extracted document content used as context for the RAG model.
        pdf_datas (List[Dict]): List of dictionaries with PDF metadata and binary data (includes 'pdf_name', 'document_id', and 'pdf_data').
        pdf_count (int): Number of documents being used in the current conversation.
        user_query (str): The user’s question or prompt.
        context_id (str): Unique identifier for the conversation context/session.
        objective (str): The goal or purpose of the user’s query (e.g., summarize, generate content).
        content_format (str): The desired output format for the assistant's response (e.g., summary, table, report).

        Returns:
        AsyncGenerator[str, None]: Asynchronously yields JSON strings containing response messages and metadata for streaming,
                                   and ends with "[DONE]" to signal completion.
        '''

        # Format settings
        #creativity_percentage = creativity_percentage / 100
       # user_text = (
        #    f"Also refer to the additional context user has provided\n{additional_text}"
        #    if additional_text and additional_text.strip()
        #    else ""
        #)
        #voice_prompt = "And assistant's voice will be: Active voice" if active_voice_status else ""

        message_id_timeStamp = str(time()).replace(".", "_")
        message_id = f"{userId}_{message_id_timeStamp}"
        await conversation_repo.add_or_update_message(
            context_id=context_id, message_id=message_id, role="user", message=user_query
        )

    
        conversation_history = await conversation_repo.get_messages_by_context(
                context_id=context_id, limit=3
            )
        if conversation_history:
                conversation_history_prompt = (
                    "To improve the answer that the assistant will be generating in this round of conversation the assistant will refer to the last three conversations that he had with the user. With these conversations, assistant will know what task he was assigned, what tone he has to answer in or any other instructions that's needed to follow to make the overall conversation more fluent. Also, assistant will remember that he is a Retrieval Augmented Generation (RAG) chatbot which means that assistant will always be provided with the context of the user query that is extracted from the document in this round of conversation. It is the assistant who will have to act smart and decide how he will/will not use that context along with the past conversation history to make the output better since sometimes the user may be referring to the previous conversation and the context might try to deviate the assistant from generating a fluent conversational output:\nCONVERSATION HISTORY:\n"
                    f"{conversation_history}"
                )
        else:
            conversation_history_prompt = ""
        
        #if selected_lexica is not [""]:
         #   glossary_prompt = get_lay_term_glossary_prompt(retrieved_chunks=context)

        system_prompt = f"""
The assistant is a content creation AI. It only generates content based on provided documents and never uses external knowledge,and answers user queries based on the context provided in the documents. The assistant is designed to be helpful, concise, and informative, always adhering to the user's instructions and the context of the conversation.

# Provided documents:
{context}

# Conversation history:
{conversation_history_prompt}

# Instructions
1. Only extract information explicitly present in the provided documents. Do not invent document names, pages, or data.
2. Each response must be divided into segments:
   - <{{"response_variable":"response_segment"}}> — the text for the user.
   - <{{"response_variable":"sources","document_name":"...","pages":[...]}}> — the source for that segment.
3. Do NOT include sources inside the response segment. Sources must always be in a separate block immediately following the segment.
4. Each <{{ ... }}> block must be valid JSON.
5. Response segments should be short and concise (1–4 sentences or 1 bullet point).
6. If a segment has no source, the sources block must be null.
7. Maintain Markdown formatting inside "response_segment" blocks.
8. Always cite the exact document names and page numbers provided. Never modify them.
9. Only provide information directly relevant to the user's query. Do not add extra context, interpretations, or conclusions.
10.Try to include specific numerical data, study results, and important names or organizations mentioned in the source when generating a response in <{{"response_variable":"response_segment"}}>, if they are relevant to the user query.
11. Start every response with <{{"response_variable":"response_segment"}}>.

# Output Example
<{{"response_variable":"response_segment"}}>Primary endpoint analysis shows a clinical benefit rate of 49% in the combination arm.
<{{"response_variable":"sources","document_name":"ABC","pages":[4,5]}}>

<{{"response_variable":"response_segment"}}>Secondary endpoint analysis shows median progression-free survival of 20 weeks.
<{{"response_variable":"sources","document_name":"ABC","pages":[6]}}>
    """

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query},
        ]

        response_for_our_user=""
        open_documents_cache = {}
        is_first_message = True
        highlight_tasks=[]
        async def source_highlights_initializer(message_id,response, document_data, source_pages):#[1,2,3]
            highlight_details=[]
            
            for current_page in source_pages:

                highlight_details.append({
                    "document_name": document_data["pdf_name"],
                    "document_id": document_data["document_id"],
                    "page_number": current_page,
                })

                highlight_exists = await highlight_repo.get_highlight_by_doc_page(message_id=message_id,document_id=document_data["document_id"],page_number=current_page)
                if not highlight_exists:
                    await highlight_repo.create_highlight(HighlightModel(
                        message_id=message_id,
                        document_id=document_data["document_id"],
                        page_number=current_page))

                if not document_data["document_id"] in open_documents_cache:
                    open_documents_cache[document_data["document_id"]] = fitz.open(stream=document_data["pdf_data"], filetype="pdf")
                task=asyncio.create_task(
                    save_source_highlights(
                        response,
                    document_data["pdf_name"],
                    document_data["document_id"],
                    open_documents_cache[document_data["document_id"]],
                    message_id,
                    current_page   
                    )
                )

                highlight_tasks.append(task)

            return highlight_details

        try:
            print("Generating final (non-streaming) answer")

            # ✅ Get the full response in one shot
            response = await use_brain(
                messages=messages,
                model=ollama_settings.OLLAMA_ANALYTICAL_MODEL,
                temperature=creativity_percentage,
                stream=False  # turn off streaming
            )
            print("response:", response)
            # Process the response into segments
            segments = await process_llm_response(response)
            print("Segments:", segments)
            # Process each segment
            for segment in segments:
                response_for_our_user = segment["text"]#Segment: [{'text': 'Monoclonal.', 'source': {'document_name': 'antibody_1', 'pages': [1, 2, 3, 4, 6, 7]}},]
                source_info = segment["source"]
                
                if source_info and source_info != "null":
                    source_document = source_info["document_name"] # e.g., "antibody_1"
                    source_pages = source_info["pages"] # e.g., [1, 2, 3, 4, 6, 7]
                    
                    document_details = next(
                        (doc for doc in pdf_datas 
                         if Path(doc["pdf_name"]).stem.lower() == source_document.lower()),
                        None
                    )
                    print("Document details:22222", document_details)
                    
                    if document_details:
                        highlights_details = await source_highlights_initializer(
                            message_id,
                            response_for_our_user,
                            document_details,
                            source_pages
                        )
                        
                        if is_first_message:
                            # First chunk includes message + metadata
                            yield json.dumps({
                                "msg_id": message_id,
                                "context_id": context_id,
                                "msg": response_for_our_user,
                                "index": highlights_details
                            }) + "\n"
                            is_first_message = False
                        else:
                            # Subsequent chunks for this response segment
                            yield json.dumps({
                                "index": highlights_details,
                                "msg": response_for_our_user
                            }) + "\n"
                    await asyncio.sleep(0.05)
                else:
                    if is_first_message:
                        # First chunk without index information
                        yield json.dumps({
                            "msg_id": message_id,
                            "context_id": context_id,
                            "msg": response_for_our_user
                        }) + "\n"
                        is_first_message = False
                    else:
                        # Subsequent text-only chunks
                        yield json.dumps({"msg": response_for_our_user}) + "\n"
                    await asyncio.sleep(0.05)

        finally:
            async def cleanup():
                await asyncio.sleep(180)
                for doc in open_documents_cache.values():
                    if not doc.is_closed:
                        doc.close()

            asyncio.create_task(cleanup())

async def process_llm_response(buffer):
    segments = []
    current_segment = {"text": "", "source": None}
    
    # Split by response markers
    parts = re.split(r'<\{|\}>', buffer)
    
    for i in range(len(parts)):
        part = parts[i].strip()
        if not part:
            continue
            
        try:
            # Check if this part starts with "response_variable"
            if part.startswith('"response_variable"'):
                # Add missing curly braces
                json_str = "{" + part + "}"
                marker_data = json.loads(json_str)
                
                if marker_data["response_variable"] == "response_segment":
                    # Get the text from next part
                    if i + 1 < len(parts):
                        current_segment = {
                            "text": parts[i + 1].strip(),
                            "source": None
                        }
                elif marker_data["response_variable"] == "sources":
                    if current_segment:
                        current_segment["source"] = {
                            "document_name": marker_data["document_name"],
                            "pages": marker_data["pages"]
                        }
                        segments.append(current_segment)
                        current_segment = {"text": "", "source": None}
                        
        except json.JSONDecodeError as e:
            print(f"Error parsing part: {part}")
            print(f"Error details: {str(e)}")
            continue
        except Exception as e:
            print(f"Unexpected error processing part: {str(e)}")
            continue
    
    # Add any remaining segment
    if current_segment["text"]:
        segments.append(current_segment)
    
    return segments