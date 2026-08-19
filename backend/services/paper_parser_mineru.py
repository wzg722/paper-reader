"""MinerU PDF layout parser.

Calls a running mineru-api (`POST /file_parse`) or the local `mineru` CLI,
then maps content_list blocks into PaperMind bilingual-layout paragraphs.
"""
from __future__ import annotations

import io
import json
import logging
import os
import shutil
import subprocess
import tempfile
import uuid
import zipfile
from typing import Any

import requests

from services.paper_parser import heading_level

logger = logging.getLogger(__name__)

SKIP_TYPES = {
    'header', 'footer', 'page_number', 'aside_text', 'page_footnote',
    'discarded',
}


def parse_pdf_via_mineru(
    path: str,
    user_id: int | None = None,
    api_url: str | None = None,
    timeout: int = 600,
) -> dict[str, Any]:
    """Parse PDF with MinerU. Raises if MinerU is unreachable or returns nothing."""
    from django.conf import settings

    bases = _mineru_base_candidates(api_url)
    last_err: Exception | None = None
    payload: Any = None
    image_dir: str | None = None
    cleanup_dirs: list[str] = []

    for base in bases:
        try:
            payload, image_dir = _call_mineru_api(path, base, timeout)
            if image_dir:
                cleanup_dirs.append(image_dir)
            if payload is not None:
                break
        except Exception as e:
            last_err = e
            logger.warning('MinerU API %s failed: %s', base, e)

    if payload is None:
        try:
            tmp_cli = tempfile.mkdtemp(prefix='mineru_')
            cleanup_dirs.append(tmp_cli)
            payload, image_dir = _call_mineru_cli(path, tmp_cli, timeout)
        except Exception as e:
            last_err = e
            logger.warning('MinerU CLI failed: %s', e)

    if payload is None:
        for d in cleanup_dirs:
            shutil.rmtree(d, ignore_errors=True)
        hint = '、'.join(bases[:3]) or 'http://127.0.0.1:8001'
        raise RuntimeError(
            f'MinerU 不可达（{last_err}）。请启动 mineru-api，例如：'
            f'mineru-api --host 0.0.0.0 --port 8001 ，并设置 MINERU_API_URL={hint}'
        )

    try:
        return _build_from_content_list(path, payload, user_id, image_dir)
    finally:
        for d in cleanup_dirs:
            shutil.rmtree(d, ignore_errors=True)


def _build_from_content_list(path: str, payload: Any, user_id: int | None, image_dir: str | None) -> dict[str, Any]:
    from django.conf import settings

    content_list = _extract_content_list(payload)
    if not content_list:
        raise RuntimeError('MinerU 未返回版面内容，请检查服务日志')

    try:
        import fitz
    except ImportError as e:
        raise RuntimeError('MinerU 版面还原需要 PyMuPDF') from e

    doc = fitz.open(path)
    page_sizes = [(p.rect.width, p.rect.height) for p in doc]
    page_count = doc.page_count

    asset_rel_dir = None
    asset_abs_dir = None
    if user_id is not None:
        asset_rel_dir = f'papers/{user_id}/assets/{uuid.uuid4().hex[:8]}'
        asset_abs_dir = os.path.join(settings.MEDIA_ROOT, asset_rel_dir)
        os.makedirs(asset_abs_dir, exist_ok=True)

    pages_meta: list[dict] = []
    for i, page in enumerate(doc):
        page_no = i + 1
        page_w, page_h = page_sizes[i]
        entry = {'page': page_no, 'width': page_w, 'height': page_h, 'thumb': None}
        if asset_abs_dir:
            try:
                thumb = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
                name = f'p{page_no}_thumb.png'
                thumb.save(os.path.join(asset_abs_dir, name))
                entry['thumb'] = f'{asset_rel_dir}/{name}'
            except Exception:
                pass
        pages_meta.append(entry)
    doc.close()

    paragraphs: list[dict] = []
    outline: list[dict] = []
    title = ''
    abstract = ''
    section_idx = 0
    has_figures = False

    for item in content_list:
        if not isinstance(item, dict):
            continue
        kind = str(item.get('type') or '').lower()
        if kind in SKIP_TYPES:
            continue
        page_idx = int(item.get('page_idx') or item.get('page_index') or 0)
        page_no = page_idx + 1
        if page_no < 1 or page_no > page_count:
            page_no = min(max(page_no, 1), page_count or 1)
        page_w, page_h = page_sizes[page_no - 1] if page_sizes else (612, 792)
        bbox = _norm_bbox(item.get('bbox'), page_w, page_h)

        text = _block_text(item)
        level = int(item.get('text_level') or 0)
        if kind in ('title',) or level >= 1:
            level = level or heading_level(text) or 1

        if kind in ('image', 'chart', 'figure'):
            has_figures = True
            img_rel = _copy_image(item.get('img_path') or item.get('image_path'), image_dir, asset_rel_dir, asset_abs_dir)
            caption = _join_text(item.get('image_caption') or item.get('table_caption') or item.get('caption'))
            fig_text = caption or text or f'[Figure p.{page_no}]'
            if not title and page_no == 1 and len(fig_text) > 12:
                title = fig_text[:500]
            sid = outline[-1]['id'] if outline else 's0'
            paragraphs.append({
                'type': 'figure',
                'en': fig_text,
                'zh': '',
                'section': (outline[-1]['title'] if outline else f'Page {page_no}'),
                'section_id': sid,
                'page': page_no,
                'bbox': bbox or [],
                **({'image': img_rel, 'image_url': f'/media/{img_rel}'} if img_rel else {}),
            })
            continue

        if kind == 'table':
            body = item.get('table_body') or ''
            caption = _join_text(item.get('table_caption') or item.get('caption'))
            table_text = caption or _html_to_text(body) or text or '[Table]'
            sid = outline[-1]['id'] if outline else 's0'
            img_rel = _copy_image(item.get('img_path'), image_dir, asset_rel_dir, asset_abs_dir)
            blk = {
                'type': 'table',
                'en': table_text,
                'zh': '',
                'section': (outline[-1]['title'] if outline else f'Page {page_no}'),
                'section_id': sid,
                'page': page_no,
                'bbox': bbox or [],
            }
            if img_rel:
                blk['image'] = img_rel
                blk['image_url'] = f'/media/{img_rel}'
            paragraphs.append(blk)
            continue

        if not text or len(text.strip()) < 2:
            continue
        text = text.strip()
        if not title and page_no == 1 and len(text) > 12:
            title = text[:500]
        if not abstract and 'abstract' in text.lower()[:40]:
            abstract = text[:1500]

        lv = level or heading_level(text)
        if lv:
            section_idx += 1
            sid = f's{section_idx}'
            outline.append({
                'id': sid,
                'title': text[:120],
                'para_index': len(paragraphs),
                'page': page_no,
                'level': lv,
            })
        else:
            sid = outline[-1]['id'] if outline else 's0'

        blk_type = 'text'
        if kind in ('equation', 'equation_interline', 'code'):
            blk_type = 'text'
        paragraphs.append({
            'type': blk_type,
            'en': text,
            'zh': '',
            'section': (outline[-1]['title'] if outline else f'Page {page_no}'),
            'section_id': sid,
            'page': page_no,
            'bbox': bbox or [],
        })

    if not paragraphs:
        raise RuntimeError('MinerU 解析结果为空')

    if not outline:
        outline = [{'id': 's0', 'title': '全文', 'para_index': 0, 'page': 1}]

    return {
        'title': title or os.path.basename(path),
        'authors': '',
        'abstract': abstract,
        'paragraphs': paragraphs,
        'outline': outline,
        'page_count': page_count,
        'pages': pages_meta,
        'parse_mode': 'mineru',
        'has_figures': has_figures,
    }


def _mineru_base_candidates(api_url: str | None) -> list[str]:
    from django.conf import settings
    from urllib.parse import urlparse

    raw = (api_url or getattr(settings, 'MINERU_API_URL', '') or 'http://127.0.0.1:8001').rstrip('/')
    out: list[str] = []

    def add(url: str):
        u = (url or '').rstrip('/')
        if u and u not in out:
            out.append(u)

    add(raw)
    parsed = urlparse(raw)
    if parsed.hostname in ('mineru', 'pm-mineru'):
        add(f'{parsed.scheme or "http"}://127.0.0.1:{parsed.port or 8001}')
    add((getattr(settings, 'MINERU_API_URL', '') or '').rstrip('/'))
    add('http://127.0.0.1:8001')
    add('http://127.0.0.1:8000')
    return out


def _call_mineru_api(path: str, base_url: str, timeout: int) -> tuple[Any, str | None]:
    name = os.path.basename(path)
    url = f'{base_url.rstrip("/")}/file_parse'
    form = {
        'return_md': 'true',
        'return_content_list': 'true',
        'return_images': 'true',
        'parse_method': 'auto',
    }
    last = None
    for field in ('files', 'file'):
        with open(path, 'rb') as f:
            files = {field: (name, f, 'application/pdf')}
            try:
                r = requests.post(url, files=files, data=form, timeout=timeout)
            except (requests.ConnectionError, requests.Timeout) as e:
                raise RuntimeError(f'MinerU 不可达: {e}') from e
        if r.status_code >= 400:
            last = RuntimeError(f'{url} HTTP {r.status_code}: {r.text[:300]}')
            continue
        ctype = (r.headers.get('Content-Type') or '').lower()
        if 'zip' in ctype or r.content[:2] == b'PK':
            return _unpack_mineru_zip(r.content)
        try:
            payload = r.json()
        except Exception as e:
            last = RuntimeError(f'MinerU 返回非 JSON: {e}')
            continue
        return payload, None
    raise last or RuntimeError(f'{url} 请求失败')


def _unpack_mineru_zip(blob: bytes) -> tuple[Any, str]:
    tmp = tempfile.mkdtemp(prefix='mineru_zip_')
    with zipfile.ZipFile(io.BytesIO(blob)) as zf:
        zf.extractall(tmp)
    content = _find_content_list_file(tmp)
    if content is None:
        shutil.rmtree(tmp, ignore_errors=True)
        raise RuntimeError('MinerU zip 中未找到 content_list.json')
    return content, tmp


def _call_mineru_cli(path: str, out_dir: str, timeout: int) -> tuple[Any, str]:
    cmd = shutil.which('mineru')
    if not cmd:
        raise RuntimeError('未安装 mineru 命令，也未连上 mineru-api')
    subprocess.run(
        [cmd, '-p', path, '-o', out_dir],
        check=True,
        timeout=timeout,
        capture_output=True,
        text=True,
    )
    content = _find_content_list_file(out_dir)
    if content is None:
        raise RuntimeError('mineru CLI 未产出 content_list.json')
    return content, out_dir


def _find_content_list_file(root: str) -> Any | None:
    found = []
    for dirpath, _, files in os.walk(root):
        for fn in files:
            if fn.endswith('_content_list.json') or fn == 'content_list.json':
                found.append(os.path.join(dirpath, fn))
    if not found:
        return None
    found.sort(key=lambda p: (0 if '_content_list.json' in p else 1, len(p)))
    with open(found[0], 'r', encoding='utf-8') as f:
        return json.load(f)


def _extract_content_list(payload: Any) -> list:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], dict) and (
            'type' in payload[0] or 'text' in payload[0] or 'bbox' in payload[0]
        ):
            return payload
        for item in payload:
            found = _extract_content_list(item)
            if found:
                return found
        return []
    if isinstance(payload, dict):
        for key in ('content_list', 'contentList', 'content_list_v2'):
            val = payload.get(key)
            if isinstance(val, str):
                try:
                    val = json.loads(val)
                except Exception:
                    val = None
            if val:
                found = _extract_content_list(val)
                if found:
                    return found
        for key in ('results', 'result', 'data', 'files'):
            if key in payload and payload[key]:
                found = _extract_content_list(payload[key])
                if found:
                    return found
        # v2 wrapper: {type, content: {type:text,...}}
        if 'type' in payload:
            return [payload]
    return []


def _norm_bbox(bbox, page_w: float, page_h: float) -> list[float] | None:
    if not bbox or not isinstance(bbox, (list, tuple)) or len(bbox) < 4:
        return None
    try:
        x0, y0, x1, y1 = [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])]
    except (TypeError, ValueError):
        return None
    # MinerU content_list bbox is 0-1000; already-PDF coords are typically larger.
    if max(x0, y0, x1, y1) <= 1000.5 and page_w > 0 and page_h > 0:
        x0, x1 = x0 / 1000.0 * page_w, x1 / 1000.0 * page_w
        y0, y1 = y0 / 1000.0 * page_h, y1 / 1000.0 * page_h
    if x1 < x0:
        x0, x1 = x1, x0
    if y1 < y0:
        y0, y1 = y1, y0
    return [x0, y0, x1, y1]


def _join_text(val) -> str:
    if val is None:
        return ''
    if isinstance(val, list):
        return ' '.join(_join_text(x) for x in val if x).strip()
    if isinstance(val, dict):
        return str(val.get('text') or val.get('zh') or val.get('en') or '').strip()
    return str(val).strip()


def _block_text(item: dict) -> str:
    for key in ('text', 'md', 'latex', 'content'):
        val = item.get(key)
        if isinstance(val, dict):
            inner = _block_text(val)
            if inner:
                return inner
        text = _join_text(val)
        if text:
            return text
    return ''


def _html_to_text(html: str) -> str:
    if not html:
        return ''
    import re
    t = re.sub(r'<br\s*/?>', '\n', str(html), flags=re.I)
    t = re.sub(r'</tr>', '\n', t, flags=re.I)
    t = re.sub(r'</t[dh]>', '\t', t, flags=re.I)
    t = re.sub(r'<[^>]+>', '', t)
    return re.sub(r'[ \t]+\n', '\n', t).strip()


def _copy_image(src: str | None, search_dir: str | None, rel_dir: str | None, abs_dir: str | None) -> str | None:
    if not src or not abs_dir or not rel_dir:
        return None
    candidates = [src]
    if search_dir:
        candidates.append(os.path.join(search_dir, src))
        candidates.append(os.path.join(search_dir, os.path.basename(src)))
        candidates.append(os.path.join(search_dir, 'images', os.path.basename(src)))
    src_abs = next((p for p in candidates if p and os.path.isfile(p)), None)
    if not src_abs:
        return None
    ext = os.path.splitext(src_abs)[1] or '.jpg'
    name = f'fig_{uuid.uuid4().hex[:10]}{ext}'
    dest = os.path.join(abs_dir, name)
    try:
        shutil.copy2(src_abs, dest)
        return f'{rel_dir}/{name}'
    except Exception:
        return None
