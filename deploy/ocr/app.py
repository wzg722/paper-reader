"""Lightweight PaddleOCR HTTP service for PaperMind."""
from __future__ import annotations

import base64
import io
import os
from typing import Any

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title='PaperMind OCR', version='1.0')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        from paddleocr import PaddleOCR
        lang = os.getenv('OCR_LANG', 'ch')
        _ocr = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
    return _ocr


class ImageBody(BaseModel):
    images: list[str] | None = None
    image: str | None = None
    file: str | None = None


def _run_ocr(image_bytes: bytes) -> dict[str, Any]:
    from PIL import Image
    import numpy as np

    img = Image.open(io.BytesIO(image_bytes)).convert('RGB')
    arr = np.array(img)
    h, w = arr.shape[:2]
    result = get_ocr().ocr(arr, cls=True)
    lines: list[str] = []
    raw = []
    for page in result or []:
        for line in page or []:
            text = line[1][0] if line and len(line) > 1 else ''
            conf = line[1][1] if line and len(line) > 1 else 0
            if text:
                lines.append(text)
                raw.append({'text': text, 'confidence': conf, 'box': line[0]})
    return {'text': '\n'.join(lines), 'results': raw, 'width': w, 'height': h}


@app.get('/')
def health():
    return {'ok': True, 'service': 'paddleocr'}


@app.get('/health')
def health2():
    return {'ok': True}


@app.post('/ocr')
@app.post('/api/ocr')
@app.post('/predict')
@app.post('/predict/ocr_system')
async def ocr_json(body: ImageBody):
    b64 = None
    if body.images:
        b64 = body.images[0]
    elif body.image:
        b64 = body.image
    elif body.file:
        b64 = body.file
    if not b64:
        return {'text': '', 'error': 'no image'}
    if ',' in b64:
        b64 = b64.split(',', 1)[1]
    data = base64.b64decode(b64)
    return _run_ocr(data)


@app.post('/ocr/upload')
async def ocr_upload(file: UploadFile = File(...)):
    data = await file.read()
    return _run_ocr(data)
