from typing import Optional
from lib.brain import use_brain
from configs.config import openai_settings
async def enhance_user_query(
    user_query: str,
) -> str:
    """
    Enhances the user query using the LLM via use_brain.

    :param user_query: The original user query string.
    :param model: The model to use for enhancement.
    :param inference: The inference backend ("ollama" or "openai").
    :return: The enhanced prompt as a string.
    """
    system_prompt = ("""
                     
You are a medical language model tasked with enhancing user queries to be more precise and comprehensive for medical contexts.
Enhance the medical query by: 
1)Adding proper medical terminology and anatomical details, 
2) Specifying vague symptoms with related manifestations, 
3) Including temporal aspects (onset, duration, frequency, progression), 
4) Clarifying affected body systems and organs,
5) Adding severity indicators and clinical presentation details, 
6) Specifying context (diagnosis, treatment, prevention, management), 
7) Including relevant demographic considerations when applicable. 
 Make the query comprehensive and medically precise while maintaining the user's original intent and question focus. Keep the enhanced query proportional - *avoid making it excessively longer than the original user query*. Return only the enhanced query.                    
"""
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    enhanced_prompt = await use_brain(
        messages=messages,
        model=openai_settings.OPENAI_API_MODEL,
        stream=False,
        temperature=0.2,
        inference="openai"
    )
    return enhanced_prompt