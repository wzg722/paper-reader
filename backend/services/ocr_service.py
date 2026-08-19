"""OCR service client — PaddleOCR HTTP API (layout-aware)."""
from __future__ import annotations

import base64
import logging
from typing import Any
from urllib.parse import urlparse

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def _ocr_base_candidates(cfg: dict | None) -> list[str]:
    """Prefer configured URL, but map Docker hostname ``ocr`` to localhost."""
    cfg = cfg or {}
    raw = (cfg.get('url') or getattr(settings, 'OCR_SERVICE_URL', '') or 'http://127.0.0.1:8866').rstrip('/')
    out: list[str] = []

    def add(url: str):
        u = (url or '').rstrip('/')
        if u and u not in out:
            out.append(u)

    add(raw)
    parsed = urlparse(raw)
    if parsed.hostname in ('ocr', 'pm-ocr'):
        add(f'{parsed.scheme or "http"}://127.0.0.1:{parsed.port or 8866}')
    add((getattr(settings, 'OCR_SERVICE_URL', '') or '').rstrip('/'))
    add('http://127.0.0.1:8866')
    return out


def ocr_image_bytes(image_bytes: bytes, user_config: dict | None = None, allow_mock: bool = True) -> str:
    """Call OCR service; returns concatenated text."""
    data = ocr_image_layout(image_bytes, user_config=user_config, allow_mock=allow_mock)
    text = (data.get('text') or '').strip()
    if text:
        return text
    if allow_mock:
        return _mock_ocr()
    raise RuntimeError(data.get('error') or 'OCR 未识别到文字')


def ocr_image_layout(
    image_bytes: bytes,
    user_config: dict | None = None,
    allow_mock: bool = True,
    timeout: int = 30,
) -> dict[str, Any]:
    """Call OCR and return layout lines with boxes."""
    cfg = user_config or {}
    provider = cfg.get('provider') or settings.OCR_PROVIDER or 'paddleocr'
    last_err: Exception | None = None

    for base_url in _ocr_base_candidates(cfg):
        try:
            if provider == 'mineru':
                text = _mineru_ocr(base_url, image_bytes)
                return {'text': text, 'results': [], 'width': None, 'height': None, 'provider': 'mineru'}
            return _paddle_ocr_layout(base_url, image_bytes, timeout=timeout)
        except Exception as e:
            last_err = e
            logger.warning('OCR layout failed via %s: %s', base_url, e)
            continue

    err = str(last_err) if last_err else '未配置 OCR 地址'
    if not allow_mock:
        return {
            'text': '',
            'results': [],
            'width': None,
            'height': None,
            'provider': 'mock',
            'error': err,
        }
    return {
        'text': _mock_ocr(err),
        'results': [],
        'width': None,
        'height': None,
        'provider': 'mock',
        'error': err,
    }


def _paddle_ocr_layout(base_url: str, image_bytes: bytes, timeout: int = 30) -> dict[str, Any]:
    b64 = base64.b64encode(image_bytes).decode('ascii')
    endpoints = [
        f'{base_url}/ocr',
        f'{base_url}/api/ocr',
        f'{base_url}/predict/ocr_system',
        f'{base_url}/predict',
    ]
    payloads = [
        {'images': [b64]},
        {'image': b64},
        {'file': b64},
    ]
    last_err = None
    for url in endpoints:
        for payload in payloads:
            try:
                r = requests.post(url, json=payload, timeout=timeout)
                if r.status_code >= 400:
                    last_err = RuntimeError(f'{url} HTTP {r.status_code}')
                    continue
                data = r.json()
                return _normalize_paddle_response(data)
            except (requests.ConnectionError, requests.Timeout) as e:
                raise RuntimeError(f'PaddleOCR 不可达: {e}') from e
            except Exception as e:
                last_err = e
                continue
    raise RuntimeError(f'PaddleOCR 不可达: {last_err}')


def _normalize_paddle_response(data: Any) -> dict[str, Any]:
    results: list[dict] = []
    if isinstance(data, dict):
        raw = data.get('results') or data.get('data') or data.get('result') or []
        if isinstance(raw, list):
            for item in raw:
                parsed = _parse_line_item(item)
                if parsed:
                    results.append(parsed)
        text = data.get('text')
        if not text:
            text = '\n'.join(x['text'] for x in results)
        return {
            'text': text or '',
            'results': results,
            'width': data.get('width'),
            'height': data.get('height'),
            'provider': 'paddleocr',
        }
    if isinstance(data, list):
        # raw paddle nested list
        for page in data:
            for item in page or []:
                parsed = _parse_line_item(item)
                if parsed:
                    results.append(parsed)
        return {
            'text': '\n'.join(x['text'] for x in results),
            'results': results,
            'width': None,
            'height': None,
            'provider': 'paddleocr',
        }
    return {'text': str(data), 'results': [], 'width': None, 'height': None, 'provider': 'paddleocr'}


def _parse_line_item(item: Any) -> dict | None:
    if isinstance(item, dict):
        text = item.get('text') or item.get('transcription') or ''
        box = item.get('box') or item.get('bbox') or item.get('points')
        conf = item.get('confidence') or item.get('score') or 0
        if text:
            return {'text': str(text), 'confidence': conf, 'box': box}
        return None
    if isinstance(item, (list, tuple)) and len(item) >= 2:
        # [[box], (text, conf)]
        box, meta = item[0], item[1]
        if isinstance(meta, (list, tuple)):
            text = str(meta[0]) if meta else ''
            conf = meta[1] if len(meta) > 1 else 0
        else:
            text = str(meta)
            conf = 0
        if text:
            return {'text': text, 'confidence': conf, 'box': box}
    if isinstance(item, str) and item.strip():
        return {'text': item.strip(), 'confidence': 0, 'box': None}
    return None


def _mineru_ocr(base_url: str, image_bytes: bytes) -> str:
    files = {'file': ('shot.png', image_bytes, 'image/png')}
    r = requests.post(f'{base_url}/parse', files=files, timeout=120)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict):
        return data.get('text') or data.get('md') or data.get('content') or str(data)
    return str(data)


def _mock_ocr(reason: str = '') -> str:
    tip = f'（OCR 服务暂不可用{": " + reason if reason else ""}，返回占位文本）'
    return f'The network architecture is revised based on residual connections. {tip}'


def test_ocr_connection(url: str, timeout: int = 6) -> dict:
    import time
    url = (url or '').rstrip('/')
    if not url:
        return {'ok': False, 'error': '地址为空', 'latency_ms': 0}
    start = time.time()
    try:
        r = requests.get(url, timeout=timeout)
        latency = int((time.time() - start) * 1000)
        return {'ok': r.status_code < 500, 'status_code': r.status_code, 'latency_ms': latency}
    except Exception as e:
        latency = int((time.time() - start) * 1000)
        return {'ok': False, 'error': str(e), 'latency_ms': latency}
