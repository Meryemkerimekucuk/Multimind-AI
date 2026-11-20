import base64
import io
import os

import requests
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
IMAGE_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
EDIT_MODEL = "@cf/black-forest-labs/flux-2-klein-4b"
VISION_MODEL = "@cf/meta/llama-3.2-11b-vision-instruct"
BASE_URL = "https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{model}"


def _auth_headers():
    if not API_TOKEN or not ACCOUNT_ID:
        raise ValueError("CLOUDFLARE_API_TOKEN veya CLOUDFLARE_ACCOUNT_ID .env dosyasında bulunamadı.")
    return {"Authorization": f"Bearer {API_TOKEN}"}


def _model_url(model: str) -> str:
    return BASE_URL.format(account_id=ACCOUNT_ID, model=model)


def _decode_image_result(response: requests.Response) -> bytes:
    content_type = response.headers.get("content-type", "").lower()
    if content_type.startswith("image/"):
        return response.content
    try:
        payload = response.json()
    except ValueError as error:
        raise RuntimeError("Cloudflare yanıtı JSON veya görsel değil: " + response.text[:500]) from error
    if not payload.get("success", False):
        raise RuntimeError(f"Cloudflare AI hatası: {payload.get('errors', payload)}")
    result = payload.get("result", {})
    encoded = None
    if isinstance(result, str):
        encoded = result
    elif isinstance(result, dict):
        encoded = result.get("image")
        if not encoded:
            encoded = result.get("data")
    elif isinstance(result, list) and result:
        first = result[0]
        encoded = first if isinstance(first, str) else first.get("image") if isinstance(first, dict) else None
    if not encoded:
        raise RuntimeError("Cloudflare yanıtında görsel verisi bulunamadı: " + str(result)[:500])
    if encoded.startswith("data:"):
        encoded = encoded.split(",", 1)[1]
    try:
        return base64.b64decode(encoded)
    except Exception as error:
        raise RuntimeError("Cloudflare görsel verisi çözümlenemedi.") from error


def _prepare_reference_image(image_bytes: bytes) -> bytes:
    """FLUX.2 Klein reference inputs must be no larger than 512x512."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            image = image.convert("RGB")
            image.thumbnail((512, 512), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="PNG")
            return output.getvalue()
    except Exception as error:
        raise RuntimeError(f"Kaynak görsel hazırlanamadı: {error}") from error


def _call_flux(prompt: str, input_image: bytes | None = None) -> bytes:
    fields = {
        "prompt": (None, prompt),
        "width": (None, "1024"),
        "height": (None, "1024"),
    }
    if input_image is not None:
        fields["input_image_0"] = ("reference.png", _prepare_reference_image(input_image), "image/png")

    response = requests.post(
        _model_url(EDIT_MODEL if input_image is not None else IMAGE_MODEL),
        headers=_auth_headers(),
        files=fields,
        timeout=300,
    )
    if not response.ok:
        raise RuntimeError(f"Cloudflare FLUX hatası ({response.status_code}): {response.text[:1500]}")
    return _decode_image_result(response)


def generate_image(prompt: str, steps: int = 4) -> bytes:
    # FLUX.2 Klein 4B uses a fixed four-step inference process.
    return _call_flux(prompt)


def analyze_image(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    image_data_url = f"data:{mime_type};base64,{base64.b64encode(image_bytes).decode('ascii')}"
    response = requests.post(
        _model_url(VISION_MODEL),
        headers={**_auth_headers(), "Content-Type": "application/json"},
        json={"messages": [{"role": "user", "content": prompt or "Bu görseli ayrıntılı şekilde açıkla."}],
              "image": image_data_url, "max_tokens": 1000},
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("success", False):
        raise RuntimeError(f"Cloudflare Vision hatası: {payload.get('errors', payload)}")
    result = payload.get("result", {})
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        return result.get("response") or result.get("description") or str(result)
    return str(result)


def edit_image(image_bytes: bytes, mime_type: str, prompt: str) -> bytes:
    if not prompt.strip():
        raise ValueError("Görsel düzenleme talimatı boş olamaz.")


    edit_prompt = (
    """You are an advanced image editing AI. 
    Use the provided reference image as the source image. 
    Carefully understand the user's editing instructions and apply 
    the requested changes clearly and accurately. 
    Preserve all original elements that the user has not asked to change. 
    Maintain the original subject's identity, appearance, structure, 
    position, proportions, perspective and composition whenever relevant. 
    Do not unnecessarily alter the background, lighting, colors or other 
    visual elements unless requested by the user. 
    The result must be a visibly edited image that follows the user's request. 
    Do not simply return the unchanged source image. 
    If the instruction is ambiguous, make the most reasonable visual 
    interpretation while keeping the original image consistent. 
    User's editing instructions:"""  + prompt
)


    
    return _call_flux(edit_prompt, input_image=image_bytes)
