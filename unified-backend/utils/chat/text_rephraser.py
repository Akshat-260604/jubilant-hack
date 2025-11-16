from typing import Dict, Optional, Union
from lib.brain import use_brain
from configs.config import openai_settings, ollama_settings

async def rephrase_text(
    text: str,
    tone: str
) -> Union[str, Exception]:
    """
    Rephrase the given text according to specified tone.

    Args:
        text (str): The input text to be rephrased
        tone (str): Desired tone for rephrasing (e.g., 'formal', 'casual', 
            'friendly', 'technical'). Defaults to 'formal'

    Returns:
        Union[str, Exception]: 
            - str: The rephrased text with applied tone
            - Exception: If an error occurs during processing
    """
    
    system_prompt = f"""You are an expert text rephraser specialized in adjusting tone.
    Rephrase the given text while maintaining its core meaning.
    
    Guidelines:
    - Use a {tone} tone throughout the text
    - Preserve key technical terms and concepts
    - Maintain the original meaning and intent
    - Ensure accuracy of information
    - Adjust vocabulary and phrasing to match the {tone} tone
    - IMPORTANT: Provide ONLY the rephrased text in your response, without any additional explanations or comments
    """

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"Please rephrase this text in a {tone} tone: {text}"}
    ]

    try:
        # Get the response from use_brain with stream=False
        response = await use_brain(
            messages=messages,
            model=openai_settings.OPENAI_API_MODEL,
            stream=False,
            ctx_window=1024*8,
            inference="openai"
        )

        # Handle async generator response
        if hasattr(response, '__aiter__'):
            full_response = ""
            async for chunk in response:
                if isinstance(chunk, dict):
                    full_response += chunk.get("content", "")
                elif isinstance(chunk, str):
                    full_response += chunk
            return full_response.strip()
        
        # Handle direct response
        if isinstance(response, dict):
            return response.get("content", "").strip()
        elif isinstance(response, str):
            return response.strip()
        
        return str(response).strip()

    except Exception as e:
        raise Exception(f"Error in text rephrasing: {str(e)}")