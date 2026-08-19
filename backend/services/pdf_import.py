"""Download remote PDF and parse into paper content."""
from __future__ import annotations

import logging
import os
import uuid

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def resolve_pdf_source_url(paper, override: str | None = None) -> str | None:
    """Prefer explicit URL, then paper.pdf_url / cover_url, then arXiv."""
    for candidate in (
        (override or '').strip(),
        (getattr(paper, 'pdf_url', None) or '').strip(),
        (getattr(paper, 'cover_url', None) or '').strip(),
    ):
        if candidate and candidate.startswith(('http://', 'https://')):
            return candidate
    arxiv_id = (getattr(paper, 'arxiv_id', None) or '').strip()
    if arxiv_id:
        return f'https://arxiv.org/pdf/{arxiv_id}.pdf'
    return None


def resolve_paper_pdf_path(paper) -> str | None:
    """Return absolute PDF path if the file exists on disk."""
    candidates = []
    if paper.file_path:
        candidates.append(paper.file_path)
    try:
        for pf in paper.files.all():
            if getattr(pf, 'file_type', '') == 'pdf' and pf.file_path and pf.file_path not in candidates:
                candidates.append(pf.file_path)
    except Exception:
        pass
    for rel in candidates:
        abs_path = rel if os.path.isabs(rel) else os.path.join(settings.MEDIA_ROOT, rel)
        if os.path.exists(abs_path):
            return abs_path
    return None


def download_pdf(url: str, user_id: int, timeout: int = 60) -> tuple[str, str, int]:
    """
    Download PDF to MEDIA_ROOT/papers/{user_id}/.
    Returns (rel_path, abs_path, size).
    """
    if not url:
        raise ValueError('PDF URL 为空')
    headers = {
        'User-Agent': 'PaperMind/2.0 (research; +https://localhost)',
        'Accept': 'application/pdf,*/*',
    }
    r = requests.get(url, headers=headers, timeout=timeout, stream=True, allow_redirects=True)
    r.raise_for_status()
    content_type = (r.headers.get('Content-Type') or '').lower()
    data = r.content
    if 'html' in content_type and len(data) < 5000:
        raise RuntimeError('下载到的不是 PDF（可能被拦截）')
    if not data.startswith(b'%PDF') and 'pdf' not in content_type:
        if len(data) < 1000:
            raise RuntimeError('下载内容过小，疑似非 PDF')

    rel_dir = f'papers/{user_id}'
    abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
    os.makedirs(abs_dir, exist_ok=True)
    fname = f'{uuid.uuid4().hex}.pdf'
    rel_path = f'{rel_dir}/{fname}'
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
    with open(abs_path, 'wb') as f:
        f.write(data)
    return rel_path, abs_path, len(data)


def _persist_pdf_fields(paper, rel_path: str, size: int, source_url: str | None = None):
    from papers.models import PaperFile

    paper.file_path = rel_path
    paper.file_size = size
    paper.file_type = 'pdf'
    if source_url:
        paper.pdf_url = source_url
        # keep cover_url as fallback for older clients
        if not paper.cover_url:
            paper.cover_url = source_url
    pf, created = PaperFile.objects.get_or_create(
        paper=paper, file_type='pdf',
        defaults={
            'file_name': f'{paper.arxiv_id or paper.id}.pdf',
            'file_path': rel_path,
            'file_size': size,
        },
    )
    if not created:
        pf.file_path = rel_path
        pf.file_size = size
        pf.file_name = f'{paper.arxiv_id or paper.id}.pdf'
        pf.save(update_fields=['file_path', 'file_size', 'file_name'])


def ensure_local_pdf(
    paper,
    pdf_url: str | None = None,
    *,
    parse_if_empty: bool = True,
    parse_mode: str = 'pdf',
) -> str:
    """
    Ensure a local PDF exists for the paper.
    If missing, re-download from paper.pdf_url (or arXiv / override).
    Returns absolute path.
    """
    abs_path = resolve_paper_pdf_path(paper)
    if abs_path:
        # still backfill pdf_url if we can infer it
        url = resolve_pdf_source_url(paper, pdf_url)
        if url and not paper.pdf_url:
            paper.pdf_url = url
            if not paper.cover_url:
                paper.cover_url = url
            paper.save(update_fields=['pdf_url', 'cover_url', 'updated_at'])
        return abs_path

    url = resolve_pdf_source_url(paper, pdf_url)
    if not url:
        raise FileNotFoundError('本地 PDF 丢失，且数据库中无下载地址')

    logger.info('Re-downloading missing PDF for paper %s from %s', paper.id, url)
    rel_path, abs_path, size = download_pdf(url, paper.user_id)
    _persist_pdf_fields(paper, rel_path, size, source_url=url)
    paper.save()

    if parse_if_empty and not paper.content_json:
        attach_and_parse_pdf(paper, abs_path=abs_path, parse_mode=parse_mode)

    return abs_path


def attach_and_parse_pdf(paper, pdf_url: str | None = None, abs_path: str | None = None, parse_mode: str = 'ocr'):
    """Download (optional) + parse PDF into paper.content_json / outline / file fields.

    Default ``parse_mode='ocr'`` uses PaddleOCR for layout restoration.
    """
    from services.paper_parser import parse_paper_file

    if not abs_path:
        url = resolve_pdf_source_url(paper, pdf_url)
        if not url:
            return paper
        rel_path, abs_path, size = download_pdf(url, paper.user_id)
        _persist_pdf_fields(paper, rel_path, size, source_url=url)
    else:
        # ensure remote url is remembered when known
        url = resolve_pdf_source_url(paper, pdf_url)
        if url and not paper.pdf_url:
            paper.pdf_url = url
            if not paper.cover_url:
                paper.cover_url = url

    # prefer user OCR preference URL if set
    user_ocr = None
    try:
        pref = getattr(paper.user, 'preference', None)
        if pref and pref.ocr_config:
            user_ocr = pref.ocr_config
    except Exception:
        pass

    from accounts.quota import QuotaExceeded, prepare_parse
    prepare_parse(paper.user, paper, abs_path)

    try:
        mode = (parse_mode or 'ocr').lower()
        if mode in ('mineru', 'miner-u'):
            from services.paper_parser_mineru import parse_pdf_via_mineru
            mineru_url = None
            if user_ocr and str(user_ocr.get('provider') or '').lower() == 'mineru':
                mineru_url = user_ocr.get('url')
            parsed = parse_pdf_via_mineru(abs_path, user_id=paper.user_id, api_url=mineru_url)
        elif mode in ('ocr', 'paddleocr', 'layout-ocr', 'pdf'):
            from services.paper_parser_ocr import parse_pdf_via_ocr
            parsed = parse_pdf_via_ocr(abs_path, user_id=paper.user_id, user_config=user_ocr)
        else:
            parsed = parse_paper_file(abs_path, mode=parse_mode, user_id=paper.user_id)
        if parsed.get('paragraphs'):
            paper.content_json = parsed['paragraphs']
        if parsed.get('outline'):
            paper.outline = parsed['outline']
        if parsed.get('abstract') and not paper.abstract:
            paper.abstract = parsed['abstract']
        if parsed.get('title') and (not paper.title or paper.title.endswith('.pdf')):
            paper.title = parsed['title']
        paper.layout_meta = {
            'pages': parsed.get('pages') or [],
            'parse_mode': parsed.get('parse_mode'),
            'has_figures': parsed.get('has_figures', False),
            'page_count': parsed.get('page_count'),
        }
        pf = paper.files.filter(file_type='pdf').first()
        if pf and parsed.get('page_count'):
            pf.page_count = parsed['page_count']
            pf.save(update_fields=['page_count'])
    except Exception as e:
        logger.warning('PDF parse failed for paper %s: %s', paper.id, e)
        if paper.abstract and not paper.content_json:
            paper.content_json = [
                {
                    'type': 'text',
                    'en': paper.abstract,
                    'zh': paper.abstract_zh or '',
                    'section': 'Abstract',
                    'section_id': 's1',
                },
            ]
            paper.outline = [{'id': 's1', 'title': 'Abstract', 'para_index': 0}]

    paper.save()
    return paper
