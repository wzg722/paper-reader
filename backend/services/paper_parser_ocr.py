"""PaddleOCR-based PDF layout restoration.

Renders each PDF page → PaddleOCR → reading-order blocks with PDF-space bbox
so the bilingual viewer can overlay and sync-highlight.
"""
from __future__ import annotations

import logging
import os
import uuid
from typing import Any

from services.paper_parser import heading_level

logger = logging.getLogger(__name__)

# Render scale: image pixels / PDF points (must match bbox mapping)
RENDER_SCALE = 2.0


def _box_to_pdf_bbox(box, scale: float = RENDER_SCALE) -> list[float] | None:
    """Convert OCR polygon [[x,y],...] in image pixels to PDF [x0,y0,x1,y1]."""
    if not box:
        return None
    try:
        xs, ys = [], []
        for pt in box:
            if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                xs.append(float(pt[0]))
                ys.append(float(pt[1]))
            elif isinstance(pt, (int, float)) and len(box) == 4 and not isinstance(box[0], (list, tuple)):
                # already [x0,y0,x1,y1] in pixels
                x0, y0, x1, y1 = map(float, box[:4])
                return [x0 / scale, y0 / scale, x1 / scale, y1 / scale]
        if not xs or not ys:
            return None
        return [min(xs) / scale, min(ys) / scale, max(xs) / scale, max(ys) / scale]
    except Exception:
        return None


def _merge_lines_to_blocks(lines: list[dict], page_h: float) -> list[dict]:
    """Merge vertically close OCR lines into paragraph-like blocks."""
    if not lines:
        return []
    # sort by y then x
    ordered = sorted(
        lines,
        key=lambda L: (
            (L['bbox'][1] if L.get('bbox') else 0),
            (L['bbox'][0] if L.get('bbox') else 0),
        ),
    )
    # gap threshold ~ 0.9 line height
    blocks: list[dict] = []
    cur: dict | None = None
    for line in ordered:
        bbox = line.get('bbox')
        text = (line.get('text') or '').strip()
        if not text:
            continue
        if not bbox:
            blocks.append({'text': text, 'bbox': None, 'lines': 1})
            cur = None
            continue
        line_h = max(bbox[3] - bbox[1], 1.0)
        if cur is None:
            cur = {'text': text, 'bbox': list(bbox), 'lines': 1, '_lh': line_h}
            continue
        gap = bbox[1] - cur['bbox'][3]
        # same column-ish and close vertically → merge
        same_col = abs(bbox[0] - cur['bbox'][0]) < max(page_h * 0.08, 40)
        if same_col and gap < cur['_lh'] * 1.15:
            cur['text'] = f"{cur['text']} {text}".strip()
            cur['bbox'][0] = min(cur['bbox'][0], bbox[0])
            cur['bbox'][1] = min(cur['bbox'][1], bbox[1])
            cur['bbox'][2] = max(cur['bbox'][2], bbox[2])
            cur['bbox'][3] = max(cur['bbox'][3], bbox[3])
            cur['lines'] += 1
            cur['_lh'] = (cur['_lh'] + line_h) / 2
        else:
            blocks.append(cur)
            cur = {'text': text, 'bbox': list(bbox), 'lines': 1, '_lh': line_h}
    if cur:
        blocks.append(cur)
    for b in blocks:
        b.pop('_lh', None)
    return blocks


def parse_pdf_via_ocr(path: str, user_id: int | None = None, user_config: dict | None = None) -> dict[str, Any]:
    """Restore PDF layout via PaddleOCR page-by-page."""
    from services.ocr_service import ocr_image_layout
    from django.conf import settings

    try:
        import fitz
    except ImportError as e:
        raise RuntimeError('OCR 版面还原需要 PyMuPDF') from e

    doc = fitz.open(path)
    paragraphs: list[dict] = []
    outline: list[dict] = []
    pages_meta: list[dict] = []
    title = ''
    abstract = ''
    section_idx = 0

    asset_rel_dir = None
    asset_abs_dir = None
    if user_id is not None:
        asset_rel_dir = f'papers/{user_id}/assets/{uuid.uuid4().hex[:8]}'
        asset_abs_dir = os.path.join(settings.MEDIA_ROOT, asset_rel_dir)
        os.makedirs(asset_abs_dir, exist_ok=True)

    matrix = fitz.Matrix(RENDER_SCALE, RENDER_SCALE)

    for page_i, page in enumerate(doc):
        page_no = page_i + 1
        page_w, page_h = page.rect.width, page.rect.height
        page_entry = {'page': page_no, 'width': page_w, 'height': page_h, 'thumb': None}

        # thumbnail
        if asset_abs_dir:
            try:
                thumb = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
                thumb_name = f'p{page_no}_thumb.png'
                thumb.save(os.path.join(asset_abs_dir, thumb_name))
                page_entry['thumb'] = f'{asset_rel_dir}/{thumb_name}'
            except Exception:
                pass

        # high-res render for OCR
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_bytes = pix.tobytes('png')
        ocr = ocr_image_layout(img_bytes, user_config=user_config)

        lines: list[dict] = []
        for item in ocr.get('results') or []:
            text = (item.get('text') or '').strip()
            if len(text) < 2:
                continue
            bbox = _box_to_pdf_bbox(item.get('box'), RENDER_SCALE)
            lines.append({'text': text, 'bbox': bbox, 'confidence': item.get('confidence') or 0})

        # if service only returned plain text, split lines without bbox
        if not lines and ocr.get('text'):
            for para in str(ocr['text']).split('\n'):
                para = para.strip()
                if len(para) >= 8:
                    lines.append({'text': para, 'bbox': None, 'confidence': 0})

        blocks = _merge_lines_to_blocks(lines, page_h)

        for blk in blocks:
            text = blk['text']
            if len(text) < 3:
                continue
            if not title and page_i == 0 and len(text) > 12:
                title = text[:500]
            if not abstract and 'abstract' in text.lower()[:40]:
                abstract = text[:1500]
            lv = heading_level(text)
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
            paragraphs.append({
                'type': 'text',
                'en': text,
                'zh': '',
                'section': (outline[-1]['title'] if outline else f'Page {page_no}'),
                'section_id': sid,
                'page': page_no,
                'bbox': blk.get('bbox') or [],
            })

        pages_meta.append(page_entry)

    page_count = doc.page_count
    doc.close()

    if not paragraphs:
        # last resort: plain PyMuPDF text so reader is not empty
        logger.warning('PaddleOCR returned no blocks for %s; falling back to layout extract', path)
        from services.paper_parser import extract_layout
        return extract_layout(path, user_id=user_id)

    return {
        'title': title or os.path.basename(path),
        'authors': '',
        'abstract': abstract,
        'paragraphs': paragraphs,
        'outline': outline,
        'page_count': page_count,
        'pages': pages_meta,
        'parse_mode': 'paddleocr',
        'has_figures': False,
    }
