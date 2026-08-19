"""Background PDF / file parse (thread, no Celery required)."""
from __future__ import annotations

import os
import threading

from django.db import close_old_connections


def enqueue_arxiv_parse(paper_id: int, pdf_url: str, parse_mode: str, rec_id: int) -> None:
    t = threading.Thread(
        target=_parse_arxiv_job,
        args=(paper_id, pdf_url or '', parse_mode or 'ocr', rec_id),
        daemon=True,
        name=f'arxiv-parse-{paper_id}',
    )
    t.start()


def enqueue_file_parse(paper_id: int, abs_path: str, parse_mode: str, rec_id: int, user_id: int) -> None:
    t = threading.Thread(
        target=_parse_file_job,
        args=(paper_id, abs_path or '', parse_mode or 'ocr', rec_id, user_id),
        daemon=True,
        name=f'file-parse-{paper_id}',
    )
    t.start()


def _notify_import(rec, paper, ok: bool) -> None:
    from accounts.notify import push_notification
    title_txt = ((paper.title if paper else None) or rec.file_name or '论文')
    short = str(title_txt)[:60]
    if ok:
        push_notification(
            rec.user_id,
            title='导入成功',
            body=f'《{short}》已加入文献库，可以开始阅读',
            level='success',
            kind='import',
            paper_id=paper.id if paper else None,
            job_id=rec.id,
        )
    else:
        push_notification(
            rec.user_id,
            title='导入未完成',
            body=(rec.error_msg or f'《{short}》解析失败，元数据已保存')[:200],
            level='error',
            kind='import',
            paper_id=paper.id if paper else None,
            job_id=rec.id,
        )


def _apply_parsed(paper, parsed: dict) -> None:
    if not parsed:
        return
    if parsed.get('title'):
        paper.title = str(parsed['title'])[:500]
    if parsed.get('abstract'):
        paper.abstract = parsed['abstract']
    if parsed.get('authors'):
        paper.authors = str(parsed['authors'])[:500]
    paper.content_json = parsed.get('paragraphs')
    paper.outline = parsed.get('outline')
    paper.layout_meta = {
        'pages': parsed.get('pages') or [],
        'parse_mode': parsed.get('parse_mode'),
        'has_figures': parsed.get('has_figures', False),
        'page_count': parsed.get('page_count'),
    }
    paper.save()
    pf = paper.files.first()
    if pf and parsed.get('page_count'):
        pf.page_count = parsed['page_count']
        pf.save(update_fields=['page_count'])


def _parse_arxiv_job(paper_id: int, pdf_url: str, parse_mode: str, rec_id: int) -> None:
    close_old_connections()
    from papers.models import ImportRecord, Paper
    from services.pdf_import import attach_and_parse_pdf

    rec = ImportRecord.objects.filter(id=rec_id).first()
    paper = Paper.objects.filter(id=paper_id).first()
    if not rec or not paper:
        close_old_connections()
        return
    rec.status = 'running'
    rec.save(update_fields=['status'])
    try:
        attach_and_parse_pdf(paper, pdf_url=pdf_url or None, parse_mode=parse_mode)
        rec.status = 'success'
        rec.error_msg = None
        rec.save(update_fields=['status', 'error_msg'])
        _notify_import(rec, paper, True)
    except Exception as e:
        paper.refresh_from_db()
        if paper.abstract and not paper.content_json:
            paper.content_json = [{
                'en': paper.abstract, 'zh': '', 'section': 'Abstract', 'section_id': 's1',
            }]
            paper.outline = [{'id': 's1', 'title': 'Abstract', 'para_index': 0}]
            paper.save(update_fields=['content_json', 'outline'])
        rec.status = 'failed'
        rec.error_msg = str(e)[:500]
        rec.save(update_fields=['status', 'error_msg'])
        _notify_import(rec, paper, False)
    finally:
        close_old_connections()


def _parse_file_job(paper_id: int, abs_path: str, parse_mode: str, rec_id: int, user_id: int) -> None:
    close_old_connections()
    from papers.models import ImportRecord, Paper
    from services.paper_parser import parse_paper_file

    rec = ImportRecord.objects.filter(id=rec_id).first()
    paper = Paper.objects.filter(id=paper_id).first()
    if not rec or not paper:
        close_old_connections()
        return
        rec.status = 'running'
        rec.save(update_fields=['status'])
        try:
            from accounts.quota import prepare_parse
            path = abs_path
            if not path or not os.path.exists(path):
                from django.conf import settings
                rel = paper.file_path or rec.file_path or ''
                path = rel if os.path.isabs(rel) else os.path.join(settings.MEDIA_ROOT, rel)
            prepare_parse(paper.user, paper, path)
            parsed = parse_paper_file(path, mode=parse_mode, user_id=user_id)
        _apply_parsed(paper, parsed)
        rec.status = 'success'
        rec.error_msg = None
        rec.save(update_fields=['status', 'error_msg'])
        paper.refresh_from_db()
        _notify_import(rec, paper, True)
    except Exception as e:
        rec.status = 'failed'
        rec.error_msg = str(e)[:500]
        rec.save(update_fields=['status', 'error_msg'])
        _notify_import(rec, paper, False)
    finally:
        close_old_connections()
