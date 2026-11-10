"""Server-side Replicate image upscaling gateway. Keep API tokens on the server."""
import asyncio
import base64
import io
import os
import time
from urllib.parse import urlparse

import httpx
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import Response
from PIL import Image, UnidentifiedImageError

app = FastAPI(title="Ultra HD AI Enhancer API")
REPLICATE_API = "https://api.replicate.com/v1"
MODEL = os.getenv("REPLICATE_MODEL", "nightmareai/real-esrgan")
MAX_UPLOAD = 12 * 1024 * 1024
MAX_PIXELS = 20_000_000

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/enhance")
async def enhance(file: UploadFile = File(...), scale: int = Form(4), face_enhance: bool = Form(False)):
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise HTTPException(503, "Sunucu API anahtarı yapılandırılmamış")
    if scale not in (2, 4):
        raise HTTPException(400, "scale yalnızca 2 veya 4 olabilir")
    data = await file.read(MAX_UPLOAD + 1)
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "En fazla 12 MB fotoğraf yüklenebilir")
    try:
        with Image.open(io.BytesIO(data)) as img:
            img.verify()
        with Image.open(io.BytesIO(data)) as img:
            if img.width * img.height > MAX_PIXELS:
                raise HTTPException(413, "Görsel en fazla 20 megapiksel olabilir")
            rgb = img.convert("RGB")
            buffer = io.BytesIO()
            rgb.save(buffer, format="JPEG", quality=94)
            encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "Geçerli bir görsel yükleyin")

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {"input": {"image": f"data:image/jpeg;base64,{encoded}", "scale": scale, "face_enhance": face_enhance}}
    async with httpx.AsyncClient(timeout=45.0, follow_redirects=False) as client:
        try:
            response = await client.post(f"{REPLICATE_API}/models/{MODEL}/predictions", headers=headers, json=payload)
            response.raise_for_status()
            prediction = response.json()
            deadline = time.monotonic() + 210
            while prediction.get("status") not in ("succeeded", "failed", "canceled"):
                if time.monotonic() >= deadline:
                    raise HTTPException(504, "İşlem zaman aşımına uğradı")
                await asyncio.sleep(2)
                poll = await client.get(f"{REPLICATE_API}/predictions/{prediction['id']}", headers=headers)
                poll.raise_for_status()
                prediction = poll.json()
            if prediction.get("status") != "succeeded":
                raise HTTPException(502, "Yapay zekâ işlemi başarısız oldu")
            output = prediction.get("output")
            if isinstance(output, list):
                output = output[0] if output else None
            if not isinstance(output, str):
                raise HTTPException(502, "Görsel çıktısı alınamadı")
            parsed = urlparse(output)
            # Never fetch arbitrary URLs returned by a remote model.
            if parsed.scheme != "https" or parsed.hostname not in ("replicate.delivery", "pbxt.replicate.delivery", "replicate.com") and not (parsed.hostname or "").endswith(".replicate.delivery"):
                raise HTTPException(502, "Beklenmeyen çıktı adresi")
            image_response = await client.get(output, timeout=90.0)
            image_response.raise_for_status()
            if len(image_response.content) > 45 * 1024 * 1024:
                raise HTTPException(502, "Çıktı boyutu çok büyük")
            with Image.open(io.BytesIO(image_response.content)) as image:
                buffer = io.BytesIO()
                image.convert("RGB").save(buffer, format="PNG")
            return Response(buffer.getvalue(), media_type="image/png")
        except httpx.HTTPError as exc:
            raise HTTPException(502, f"Görüntü işleme hizmetine erişilemiyor: {type(exc).__name__}") from exc
