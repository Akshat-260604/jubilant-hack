import json
from typing import Optional, AsyncGenerator, Union, List
from fastapi import HTTPException
import httpx
from openai import AsyncOpenAI
from configs.config import ollama_settings, openai_settings
from lib.logger import log

async def use_brain(
    messages: List[dict],
    model: str = "gpt-4o",
    stream: Optional[bool] = True,
    respond_in_json: Optional[bool] = False,
    ctx_window: Optional[int] = 2048,
    prediction: Optional[int] = -2,
    inference: str = "openai",
    temperature: Optional[float] = None,
) -> Union[AsyncGenerator[str, None], str]:
    """
    Handles inference using OpenAI or Ollama, returns an async generator for streaming or static responses.

    :param messages: List of message dictionaries for inference
    :param model: Model name for the provider
    :param stream: If True, stream the response chunk by chunk
    :param respond_in_json: Whether to request the response in JSON format (Ollama only)
    :param ctx_window: Context window size (Ollama only)
    :param prediction: Prediction tokens count (Ollama only)
    :param inference: Determines the backend provider ("openai" or "ollama")
    :param temperature: Temperature for response generation (0.0-1.0)
    :return: AsyncGenerator that yields string chunks or full response string
    """
    log(f"DEBUG: inference value is '{inference}', stream={stream}")

    if not messages:
        raise HTTPException(status_code=400, detail="Messages cannot be empty.")

    if inference == "openai":
        try:
            client = AsyncOpenAI(api_key=openai_settings.OPENAI_API_KEY)

            if stream:
                async def stream_response() -> AsyncGenerator[str, None]:
                    try:
                        completion_params = {
                            "model": model,
                            "messages": messages,
                            "stream": True
                        }
                        if temperature is not None:
                            completion_params["temperature"] = temperature

                        response = await client.chat.completions.create(**completion_params)
                        async for chunk in response:
                            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                                yield chunk.choices[0].delta.content
                    except Exception as e:
                        log(f"OpenAI streaming error: {e}")
                        raise HTTPException(status_code=500, detail=f"OpenAI streaming error: {e}")

                return stream_response()

            else:
                completion_params = {
                    "model": model,
                    "messages": messages,
                    "stream": False
                }
                if temperature is not None:
                    completion_params["temperature"] = temperature

                response = await client.chat.completions.create(**completion_params)
                
                if not response.choices or not response.choices[0].message:
                    raise HTTPException(status_code=500, detail="No response from OpenAI")
                
                full_text = response.choices[0].message.content
                if not full_text:
                    raise HTTPException(status_code=500, detail="Empty response from OpenAI")
                
                return full_text

        except HTTPException:
            raise
        except Exception as e:
            log(f"OpenAI Error: {e}")
            raise HTTPException(status_code=500, detail=f"OpenAI error: {e}")

    elif inference == "ollama":
        payload = {
            "model": "llama3.3:70b",
            "messages": messages,
            "stream": stream,
            "options": {
                "num_ctx": ctx_window,
                "num_predict": prediction,
                "temperature": temperature if temperature is not None else 0.3,
                "top_p": 0.95
            }
        }
        
        if respond_in_json:
            payload["format"] = "json"

        payload_json = json.dumps(payload)
        log(f"Sending request to Ollama at {ollama_settings.OLLAMA_ENDPOINT_URL} with model {payload['model']}")

        try:
            if stream:
                async def stream_response() -> AsyncGenerator[str, None]:
                    async with httpx.AsyncClient(timeout=None) as client:
                        async with client.stream(
                            "POST",
                            f'{ollama_settings.OLLAMA_ENDPOINT_URL}/api/chat',
                            data=payload_json,
                        ) as response:
                            if response.status_code != 200:
                                msg = f"Ollama Error: {response.status_code} - {await response.aread()}"
                                log(msg)
                                raise HTTPException(status_code=500, detail=msg)

                            async for line in response.aiter_lines():
                                if line:
                                    try:
                                        response_json = json.loads(line)
                                        content = response_json.get("message", {}).get("content")
                                        if content:
                                            yield content
                                    except json.JSONDecodeError as e:
                                        log(f"JSON decode error: {e}")
                    log("Streaming complete.")

                return stream_response()

            else:
                async with httpx.AsyncClient(timeout=None) as client:
                    response = await client.post(
                        url=f'{ollama_settings.OLLAMA_ENDPOINT_URL}/api/chat',
                        data=payload_json,
                    )
                    if response.status_code != 200:
                        msg = f"Ollama Error: {response.status_code} - {response.text}"
                        log(msg)
                        raise HTTPException(status_code=500, detail=msg)

                    try:
                        response_json = response.json()
                        content = response_json.get("message", {}).get("content")
                        if content:
                            return content
                        else:
                            log("No content in Ollama response.")
                            raise HTTPException(status_code=500, detail="No content in model response.")
                    except json.JSONDecodeError as e:
                        msg = f"Failed to parse Ollama response: {e}"
                        log(msg)
                        raise HTTPException(status_code=500, detail=msg)

        except httpx.TimeoutException as e:
            msg = f"Ollama request timed out: {e}"
            log(msg)
            raise HTTPException(status_code=504, detail=msg)
        except Exception as e:
            msg = f"Unexpected error: {e}"
            log(msg)
            raise HTTPException(status_code=500, detail=msg)

    else:
        raise HTTPException(status_code=400, detail=f"Inference type '{inference}' not supported.")