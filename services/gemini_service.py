import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

api_key = os.getenv("google_apikey")
if not api_key:
    raise ValueError("google_apikey anahtarını .env dosyasında tanımlayın.")

client = genai.Client(api_key=api_key)


def generate_text(
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 1000,
) -> str:
    response = client.models.generate_content(
        model=os.getenv("GEMINI_TEXT_MODEL", "gemini-3.5-flash-lite"),
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        ),
    )
    return response.text or ""


def safe_generate_text(
    prompt: str,
    temperature: float = 0.7,
    max_output_tokens: int = 1000,
) -> str | None:
    try:
        return generate_text(
            prompt,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
    except Exception as error:
        print(f"Gemini API hatası: {error}")
        return None


def analyze_audio(
    prompt: str,
    audio_bytes: bytes,
    mime_type: str = "audio/mpeg",
    max_output_tokens: int = 1800,
) -> str:
    """Analyze audio bytes directly with Gemini multimodal input."""
    audio_part = types.Part.from_bytes(data=audio_bytes, mime_type=mime_type)
    response = client.models.generate_content(
        model=os.getenv("GEMINI_AUDIO_MODEL", os.getenv("GEMINI_TEXT_MODEL", "gemini-3.5-flash-lite")),
        contents=[prompt, audio_part],
        config=types.GenerateContentConfig(temperature=0.7, max_output_tokens=max_output_tokens),
    )
    return response.text or ""


def safe_analyze_audio(
    prompt: str,
    audio_bytes: bytes,
    mime_type: str = "audio/mpeg",
    max_output_tokens: int = 1800,
) -> str | None:
    try:
        return analyze_audio(prompt, audio_bytes, mime_type, max_output_tokens)
    except Exception as error:
        print(f"Gemini ses analiz hatası: {error}")
        return None
