from openai import OpenAI
from configs.config import OpenAISettings

# Load API key from .env via config
openai_settings = OpenAISettings()
client = OpenAI(api_key=openai_settings.OPENAI_API_KEY)

def build_prompt(content_format: str, text: str) -> str:
    return f"""
You are a professional medical content analyst.

Your task is to analyze the following text and extract **findings** specifically tailored for the given content format.

- **Content Format**: {content_format}

### Original Text:
{text}

Please return a clear and concise list of findings that match the format and context of the content type.
"""

def send_to_openai(prompt: str) -> str:
    messages = [
        {"role": "system", "content": "You are a helpful assistant for extracting findings from medical content."},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )
    return response.choices[0].message.content

def generate_findings_from_text(content_format: str, text: str) -> str:
    prompt = build_prompt(content_format, text)
    return send_to_openai(prompt)
