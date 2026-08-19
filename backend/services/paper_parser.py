"""PDF layout-aware parsing: text + embedded figures + page snapshots."""
from __future__ import annotations

import os
import re
import uuid
from typing import Any

SECTION_PATTERNS = [
    r'^(abstract|摘要)$',
    r'^(introduction|引言|绪论)$',
    r'^(related\s+work|相关工作)$',
    r'^(method|methods|methodology|approach|方法)$',
    r'^(experiment|experiments|evaluation|实验)$',
    r'^(result|results|结果)$',
    r'^(discussion|讨论)$',
    r'^(conclusion|conclusions|结论)$',
    r'^(reference|references|参考文献)$',
    r'^(\d+(\.\d+)*)\s+.+',
]


def _is_section_title(text: str) -> bool:
    t = (text or '').strip()
    if len(t) > 120 or len(t) < 3:
        return False
    low = t.lower()
    for pat in SECTION_PATTERNS:
        if re.match(pat, low, re.I):
            return True
    if t.isupper() and 3 <= len(t.split()) <= 12:
        return True
    return False


def heading_level(text: str) -> int:
    """1 = H1 chapter, 2 = H2 subsection, 0 = body."""
    t = re.sub(r'\s+', ' ', (text or '').strip())
    if len(t) < 3 or len(t) > 90:
        return 0
    if re.match(r'^\d+\.\d+(\.\d+)?\s+\S', t):
        return 2
    if re.match(r'^\d+\.?\s+[A-Za-z\u4e00-\u9fff]', t) and len(t) < 80:
        return 1
    if _is_section_title(t):
        return 1
    return 0


def _media_rel(user_id: int | None, sub: str) -> str:
    uid = user_id or 0
    return f'papers/{uid}/assets/{sub}'


def extract_layout(path: str, user_id: int | None = None) -> dict[str, Any]:
    """
    Layout-preserving parse via PyMuPDF:
    - Keep reading order of text blocks
    - Extract embedded images (figures/tables as images)
    - Build page thumbnails for outline navigation
    - Return paragraphs with type: text | figure
    """
    import fitz
    from django.conf import settings

    doc = fitz.open(path)
    paragraphs: list[dict] = []
    outline: list[dict] = []
    pages_meta: list[dict] = []
    title = ''
    abstract = ''
    current_section = 'body'
    section_idx = 0

    asset_rel_dir = _media_rel(user_id, uuid.uuid4().hex[:8])
    asset_abs_dir = os.path.join(settings.MEDIA_ROOT, asset_rel_dir)
    os.makedirs(asset_abs_dir, exist_ok=True)

    for page_i, page in enumerate(doc):
        page_w, page_h = page.rect.width, page.rect.height
        page_entry = {
            'page': page_i + 1,
            'width': page_w,
            'height': page_h,
            'thumb': None,
        }

        # page thumbnail (for layout preview strip)
        try:
            pix = page.get_pixmap(matrix=fitz.Matrix(0.35, 0.35), alpha=False)
            thumb_name = f'p{page_i + 1}_thumb.png'
            pix.save(os.path.join(asset_abs_dir, thumb_name))
            page_entry['thumb'] = f'{asset_rel_dir}/{thumb_name}'
        except Exception:
            pass

        # Extract images on this page first (by vertical position)
        image_blocks: list[tuple[float, dict]] = []
        for img_i, img in enumerate(page.get_images(full=True)):
            try:
                xref = img[0]
                rects = page.get_image_rects(xref)
                if not rects:
                    continue
                rect = rects[0]
                # skip tiny icons
                if rect.width < 40 or rect.height < 40:
                    continue
                pix = fitz.Pixmap(doc, xref)
                if pix.n > 4:
                    pix = fitz.Pixmap(fitz.csRGB, pix)
                fig_name = f'p{page_i + 1}_img{img_i + 1}.png'
                fig_abs = os.path.join(asset_abs_dir, fig_name)
                pix.save(fig_abs)
                image_blocks.append((rect.y0, {
                    'type': 'figure',
                    'en': f'[Figure p.{page_i + 1}]',
                    'zh': f'[图 第{page_i + 1}页]',
                    'section': current_section,
                    'section_id': outline[-1]['id'] if outline else 's0',
                    'page': page_i + 1,
                    'bbox': [rect.x0, rect.y0, rect.x1, rect.y1],
                    'image': f'{asset_rel_dir}/{fig_name}',
                    'image_url': f'/media/{asset_rel_dir}/{fig_name}',
                }))
            except Exception:
                continue

        # Text blocks with positions
        text_blocks: list[tuple[float, dict]] = []
        for b in page.get_text('dict').get('blocks', []):
            if b.get('type') != 0:
                continue
            lines = []
            for line in b.get('lines', []):
                spans = [s.get('text', '') for s in line.get('spans', [])]
                line_text = ''.join(spans).strip()
                if line_text:
                    lines.append(line_text)
            text = re.sub(r'\s+', ' ', ' '.join(lines)).strip()
            if not text:
                continue
            y0 = b.get('bbox', [0, 0, 0, 0])[1]
            text_blocks.append((y0, {
                'type': 'text',
                'en': text,
                'zh': '',
                'section': current_section,
                'section_id': outline[-1]['id'] if outline else 's0',
                'page': page_i + 1,
                'bbox': list(b.get('bbox', [])),
            }))

        # Merge by reading order (y then x)
        merged = sorted(text_blocks + image_blocks, key=lambda x: x[0])
        for _, block in merged:
            if block['type'] == 'text':
                txt = block['en']
                if not title and page_i == 0 and len(txt) > 10:
                    title = txt[:500]
                if re.match(r'^abstract$', txt, re.I):
                    continue
                if heading_level(txt):
                    section_idx += 1
                    sid = f's{section_idx}'
                    current_section = txt.strip()
                    outline.append({
                        'id': sid,
                        'title': current_section,
                        'para_index': len(paragraphs),
                        'page': page_i + 1,
                        'level': heading_level(txt),
                    })
                    block['section'] = current_section
                    block['section_id'] = sid
                    paragraphs.append(block)
                    continue
                if len(txt) < 15 and not txt.endswith('.'):
                    continue
                # detect table-like plain text (many pipes / tabs)
                if txt.count('|') >= 3 or txt.count('\t') >= 3:
                    block['type'] = 'table'
                    block['en'] = txt
                block['section'] = current_section
                block['section_id'] = outline[-1]['id'] if outline else 's0'
                if re.match(r'^abstract$', current_section, re.I) and not abstract:
                    abstract = txt[:5000]
            paragraphs.append(block)

        # If page has almost no text but has images, still keep figures
        pages_meta.append(page_entry)

    page_count = doc.page_count
    doc.close()

    if not outline:
        outline = [{'id': 's0', 'title': '全文', 'para_index': 0, 'page': 1}]

    # Fallback: if too few text blocks, caller may OCR
    return {
        'title': title,
        'authors': '',
        'abstract': abstract,
        'paragraphs': paragraphs,
        'outline': outline,
        'page_count': page_count,
        'pages': pages_meta,
        'parse_mode': 'layout',
        'has_figures': any(p.get('type') == 'figure' for p in paragraphs),
    }


def parse_pdf(path: str, user_id: int | None = None) -> dict[str, Any]:
    """Default PDF parse: PaddleOCR layout restore, fallback to PyMuPDF extract."""
    try:
        from services.paper_parser_ocr import parse_pdf_via_ocr
        result = parse_pdf_via_ocr(path, user_id=user_id)
        if len([p for p in result.get('paragraphs') or [] if p.get('type', 'text') == 'text']) >= 1:
            return result
    except Exception as e:
        logger = __import__('logging').getLogger(__name__)
        logger.warning('PaddleOCR layout failed, fallback extract_layout: %s', e)
    try:
        return extract_layout(path, user_id=user_id)
    except Exception:
        return _parse_pdf_plain(path)


def _parse_pdf_plain(path: str) -> dict[str, Any]:
    paragraphs: list[dict] = []
    outline: list[dict] = []
    title = ''
    abstract = ''
    try:
        import fitz
        doc = fitz.open(path)
        page_count = doc.page_count
        all_blocks: list[str] = []
        for page in doc:
            blocks = page.get_text('blocks')
            for b in sorted(blocks, key=lambda x: (x[1], x[0])):
                text = (b[4] or '').strip()
                if text:
                    all_blocks.append(re.sub(r'\s+', ' ', text))
        doc.close()
    except Exception as e:
        raise RuntimeError(f'PDF 解析失败: {e}') from e

    if all_blocks:
        title = all_blocks[0][:500]
    current_section = 'body'
    section_idx = 0
    for blk in all_blocks:
        lv = heading_level(blk)
        if lv:
            section_idx += 1
            sid = f's{section_idx}'
            current_section = blk.strip()
            outline.append({
                'id': sid,
                'title': current_section,
                'para_index': len(paragraphs),
                'level': lv,
            })
            paragraphs.append({
                'type': 'text', 'en': blk, 'zh': '',
                'section': current_section, 'section_id': sid,
            })
            continue
        if len(blk) < 20:
            continue
        paragraphs.append({
            'type': 'text', 'en': blk, 'zh': '',
            'section': current_section,
            'section_id': outline[-1]['id'] if outline else 's0',
        })
    if not outline:
        outline = [{'id': 's0', 'title': '全文', 'para_index': 0}]
    return {
        'title': title, 'authors': '', 'abstract': abstract,
        'paragraphs': paragraphs, 'outline': outline,
        'page_count': page_count, 'parse_mode': 'pdf',
    }


def parse_pdf_via_ocr(path: str, user_id: int | None = None) -> dict[str, Any]:
    from services.paper_parser_ocr import parse_pdf_via_ocr as _ocr
    return _ocr(path, user_id=user_id)


def parse_paper_file(path: str, mode: str = 'ocr', user_id: int | None = None) -> dict[str, Any]:
    """Parse paper file. Default mode ``ocr`` = PaddleOCR layout restore."""
    ext = path.rsplit('.', 1)[-1].lower()
    if ext == 'pdf':
        mode = (mode or 'ocr').lower()
        if mode in ('mineru', 'miner-u'):
            from services.paper_parser_mineru import parse_pdf_via_mineru
            return parse_pdf_via_mineru(path, user_id=user_id)
        if mode in ('ocr', 'paddleocr', 'layout-ocr'):
            return parse_pdf_via_ocr(path, user_id=user_id)
        if mode in ('layout', 'pymupdf'):
            return extract_layout(path, user_id=user_id)
        # legacy 'pdf' → still prefer OCR layout restore
        return parse_pdf(path, user_id=user_id)
    if ext in ('txt', 'md'):
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        paras = [{'type': 'text', 'en': p.strip(), 'zh': '', 'section': 'body', 'section_id': 's0'}
                 for p in text.split('\n\n') if p.strip()]
        return {
            'title': paras[0]['en'][:100] if paras else os.path.basename(path),
            'authors': '', 'abstract': '',
            'paragraphs': paras,
            'outline': [{'id': 's0', 'title': '全文', 'para_index': 0}],
            'page_count': 1, 'parse_mode': 'text',
        }
    return {
        'title': os.path.basename(path).rsplit('.', 1)[0],
        'authors': '', 'abstract': '',
        'paragraphs': [],
        'outline': [{'id': 's0', 'title': '文档', 'para_index': 0}],
        'page_count': 1, 'parse_mode': 'file',
    }
