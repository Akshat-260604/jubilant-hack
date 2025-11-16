import requests
from typing import List, Optional
from openai import OpenAI
from configs.config import OpenAISettings
from utils.document_handling.logger import log
from fastapi import HTTPException
from utils.document_handling.content_type import CONTENT_HIERARCHY
from utils.document_handling.prompt_builder import build_prompt 


class ContentGenerator:
    def __init__(self):
        openai_settings = OpenAISettings()
        self.client = OpenAI(api_key=openai_settings.OPENAI_API_KEY)

    @staticmethod
    def validate_parameters(content_format: str, objective: str, audience: str, tone: str):
        log(f"Validating parameters: format={content_format}, objective={objective}, audience={audience}, tone={tone}")
        if content_format not in CONTENT_HIERARCHY:
            log("Invalid content format")
            raise HTTPException(status_code=400, detail="Invalid content format")
        
        if objective not in CONTENT_HIERARCHY[content_format]:
            log("Invalid objective")
            raise HTTPException(status_code=400, detail="Invalid objective")
            
        if audience not in CONTENT_HIERARCHY[content_format][objective]:
            log("Invalid audience")
            raise HTTPException(status_code=400, detail="Invalid audience")
            
        if tone not in CONTENT_HIERARCHY[content_format][objective][audience]:
            log("Invalid tone")
            raise HTTPException(status_code=400, detail="Invalid tone")

    async def generate_content(
        self, 
        content_format: str, 
        objective: str, 
        audience: str, 
        tone: str, 
        text: str,
        image_paths: Optional[List[str]] = None
    ) -> dict:
        try:
            log("Starting content generation")
            log(f"Received params: format={content_format}, objective={objective}, audience={audience}, tone={tone}, text_length={len(text)}, image_paths={image_paths}")

            self.validate_parameters(content_format, objective, audience, tone)

            # Build prompts
            system_prompt, user_prompt = build_prompt(content_format, objective, audience, tone, text)
            log("Prompt built successfully")

            # Add system instruction for strict raw S3 link handling
            system_prompt += (
                '''\n\nInstruction: Must return only the content. If any of the provided S3 image URLs are relevant, insert them exactly as they are (including query parameters) at the appropriate place in the content. 
                Do not change, shorten, reformat, or replace the URL. Do not use HTML, markdown, base64, or placeholders. Just insert the full original URL where it fits naturally. In the link do not add anything just send the raw link'''
            )

            
            if image_paths:
                for image_url in image_paths:
                    if not image_url.startswith("https://") or "s3" not in image_url:
                        log(f"Invalid S3 image URL: {image_url}")
                        raise HTTPException(status_code=400, detail=f"Invalid S3 image URL: {image_url}")
                user_prompt += "\n\nUse the following image links if they are relevant:\n" + "\n".join(image_paths)

            # Prepare messages
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": [{"type": "text", "text": user_prompt}]
                }
            ]

            log("Calling OpenAI API")
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.7
            )

            if not response.choices or not response.choices[0].message.content:
                log("No content generated from OpenAI")
                raise HTTPException(status_code=500, detail="No content generated from OpenAI")

            content = response.choices[0].message.content
            log("Content generated successfully")

            return {
                "generated_content": content
            }

        except HTTPException as e:
            log(f"HTTPException: {e.detail}")
            raise e
        except Exception as e:
            log(f"Error in content generation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Content generation failed: {str(e)}")



content_generator = ContentGenerator()