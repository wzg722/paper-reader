"""Search papers from a user's saved sources (arXiv, Semantic Scholar, etc.)."""
from __future__ import annotations

import os
import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import quote

import requests

from services.arxiv_service import query_arxiv
from services.recommend import _arxiv_sort, annotate_owned, paged, user_owned_map

_HEADERS = {
    'User-Agent': 'PaperMind/1.0 (mailto:papermind@local)',
    'Accept': 'application/json',
}
_MAILTO = 'papermind@local'
_ACL_OPENALEX_SOURCE = 'S4306402567'
_DOI_RE = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.I)


def source_kind(src) -> str:
    blob = f'{getattr(src, "name", "")} {getattr(src, "url", "")} {getattr(src, "icon", "")}'.lower()
    if 'arxiv' in blob:
        return 'arxiv'
    if 'semantic' in blob or blob.strip() == 's2' or '/s2' in blob:
        return 's2'
    if 'acl' in blob or 'anthology' in blob:
        return 'acl'
    if 'openreview' in blob:
        return 'openreview'
    if 'baidu' in blob or 'xueshu' in blob:
        return 'baidu'
    if 'google' in blob or 'scholar.google' in blob:
        return 'google'
    return 'web'


def _norm_sort(sort: str) -> str:
    s = (sort or 'relevance').strip().lower()
    if s in ('cite', 'citation', 'citations', 'cites'):
        return 'cites'
    if s in ('year_desc', 'year'):
        return 'year'
    if s in ('year_asc', 'oldest'):
        return 'year_asc'
    if s in ('newest', 'new', 'date', 'updated'):
        return 'newest'
    return 'relevance'


def search_source(src, q: str, page: int = 1, page_size: int = 10, sort: str = 'relevance') -> dict[str, Any]:
    kind = source_kind(src)
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 10), 1), 50)
    sort = _norm_sort(sort)
    start = (page - 1) * page_size
    if kind == 'arxiv':
        if sort == 'cites':
            return _search_openalex(q, page, page_size, sort=sort)
        sort_by, sort_order = _arxiv_sort(sort)
        data = query_arxiv(
            query=q, start=start, max_results=page_size,
            sort_by=sort_by, sort_order=sort_order,
        )
        items = [_norm(x, venue='arXiv', source='arxiv') for x in data.get('results') or []]
        return paged(items, int(data.get('total') or 0), page, page_size)
    if kind == 's2':
        if sort == 'relevance':
            return _with_fallback(
                lambda: _search_s2(q, page, page_size),
                lambda: _search_openalex(q, page, page_size, sort=sort),
            )
        return _search_openalex(q, page, page_size, sort=sort)
    if kind == 'openreview':
        if sort == 'relevance':
            return _with_fallback(
                lambda: _search_openreview(q, page, page_size),
                lambda: _search_openalex(f'{q} OpenReview', page, page_size, sort=sort),
            )
        return _search_openalex(f'{q} OpenReview', page, page_size, sort=sort)
    if kind == 'acl':
        return _search_acl(q, page, page_size, sort=sort)
    return _with_fallback(
        lambda: _search_openalex(q, page, page_size, sort=sort),
        lambda: _search_crossref(q, page, page_size, sort=sort),
    )


def resolve_oa_pdf(doi: str, existing: str = '') -> str:
    """Best-effort open-access PDF URL from DOI (Unpaywall, then OpenAlex)."""
    if existing and existing.startswith(('http://', 'https://')) and existing.lower().endswith('.pdf'):
        return existing
    doi = _clean_doi(doi)
    if not doi:
        return (existing or '').strip()
    pdf = _unpaywall_pdf(doi) or _openalex_pdf_by_doi(doi)
    return pdf or (existing or '').strip()


def _norm(item: dict, venue='', source='') -> dict:
    row = dict(item)
    row.setdefault('venue', venue)
    row.setdefault('source', source or venue)
    row.setdefault('cites', row.get('cites') or 0)
    row.setdefault('intro', (row.get('abstract') or '')[:200])
    hid = (
        row.get('arxiv_id')
        or row.get('doi')
        or row.get('external_id')
        or row.get('abs_url')
        or row.get('title')
        or ''
    )
    row.setdefault('id', hid)
    return row


def _authors(names) -> str:
    if isinstance(names, str):
        return names
    out = []
    for a in names or []:
        if isinstance(a, str):
            out.append(a)
        elif isinstance(a, dict):
            out.append(
                a.get('name')
                or a.get('author', {}).get('name')
                or ' '.join(x for x in (a.get('given'), a.get('family')) if x)
                or ''
            )
    return ', '.join(x for x in out if x)


def _with_fallback(primary, fallback):
    try:
        data = primary()
        if data.get('results'):
            return data
    except Exception:
        pass
    return fallback()


def _get_json(url: str, params: dict | None = None, headers: dict | None = None, timeout: int = 20) -> dict:
    hdrs = dict(_HEADERS)
    if headers:
        hdrs.update(headers)
    r = requests.get(url, params=params or {}, timeout=timeout, headers=hdrs)
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}


def _search_s2(q: str, page: int, page_size: int) -> dict[str, Any]:
    offset = (page - 1) * page_size
    headers = dict(_HEADERS)
    key = (os.environ.get('S2_API_KEY') or os.environ.get('SEMANTIC_SCHOLAR_API_KEY') or '').strip()
    if key:
        headers['x-api-key'] = key
    data = _get_json(
        'https://api.semanticscholar.org/graph/v1/paper/search',
        params={
            'query': q,
            'offset': offset,
            'limit': page_size,
            'fields': 'title,authors,year,abstract,externalIds,citationCount,url,venue,openAccessPdf,paperId',
        },
        headers=headers,
    )
    items = []
    for p in data.get('data') or []:
        ext = p.get('externalIds') or {}
        arxiv_id = ext.get('ArXiv') or ''
        doi = _clean_doi(ext.get('DOI') or '')
        pdf = ((p.get('openAccessPdf') or {}) or {}).get('url') or ''
        if arxiv_id and not pdf:
            pdf = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
        pid = p.get('paperId') or ''
        items.append(_norm({
            'title': p.get('title') or '',
            'authors': _authors(p.get('authors')),
            'year': p.get('year'),
            'abstract': p.get('abstract') or '',
            'arxiv_id': arxiv_id,
            'doi': doi,
            'pdf_url': pdf,
            'abs_url': p.get('url') or (f'https://www.semanticscholar.org/paper/{pid}' if pid else ''),
            'cites': p.get('citationCount') or 0,
            'venue': p.get('venue') or 'Semantic Scholar',
            'category': '',
            'external_id': pid,
        }, venue=p.get('venue') or 'Semantic Scholar', source='s2'))
    total = int(data.get('total') or 0)
    return paged(items, total, page, page_size)


def _search_openreview(q: str, page: int, page_size: int) -> dict[str, Any]:
    offset = (page - 1) * page_size
    data = _get_json(
        'https://api2.openreview.net/notes/search',
        params={
            'term': q,
            'limit': page_size,
            'offset': offset,
            'content': 'all',
            'group': 'all',
            'source': 'forum',
        },
    )
    notes = data.get('notes') or data.get('results') or []
    count = int(data.get('count') or data.get('total') or len(notes))
    items = []
    for n in notes:
        content = n.get('content') or {}
        title = _ov_val(content.get('title'))
        if not title:
            continue
        abstract = _ov_val(content.get('abstract'))
        authors = content.get('authors')
        if isinstance(authors, dict):
            authors = authors.get('value')
        year = None
        cdate = n.get('cdate') or n.get('tcdate') or n.get('pdate')
        if cdate:
            try:
                ts = int(cdate)
                year = ts if ts < 3000 else datetime.fromtimestamp(ts / 1000, tz=timezone.utc).year
            except Exception:
                year = None
        nid = n.get('id') or n.get('forum') or ''
        html = _ov_val(content.get('html'))
        doi = _clean_doi(_ov_val(content.get('doi')) or html)
        pdf_field = _ov_val(content.get('pdf'))
        domain = str(n.get('domain') or '')
        is_or_forum = 'dblp.org' not in domain.lower()
        if pdf_field.startswith('http'):
            pdf_url = pdf_field
        elif is_or_forum and nid:
            pdf_url = f'https://openreview.net/pdf?id={nid}'
        else:
            pdf_url = ''
        abs_url = html or (f'https://openreview.net/forum?id={nid}' if nid else '')
        items.append(_norm({
            'title': title,
            'authors': _authors(authors),
            'year': year,
            'abstract': abstract,
            'arxiv_id': '',
            'doi': doi,
            'pdf_url': pdf_url,
            'abs_url': abs_url,
            'cites': 0,
            'venue': _ov_val(content.get('venue')) or 'OpenReview',
            'category': '',
            'external_id': nid,
        }, venue=_ov_val(content.get('venue')) or 'OpenReview', source='openreview'))
    return paged(items, count, page, page_size)


def _ov_val(v):
    if isinstance(v, dict):
        return v.get('value') or ''
    return v or ''


def _search_acl(q: str, page: int, page_size: int, sort: str = 'relevance') -> dict[str, Any]:
    try:
        data = _search_openalex(q, page, page_size, extra={
            'filter': f'primary_location.source.id:{_ACL_OPENALEX_SOURCE}',
        }, sort=sort)
        if data.get('results'):
            return data
    except Exception:
        pass
    return _search_openalex(f'{q} ACL', page, page_size, sort=sort)


def _openalex_sort_param(sort: str) -> str:
    return {
        'cites': 'cited_by_count:desc',
        'year': 'publication_year:desc',
        'newest': 'publication_date:desc',
        'year_asc': 'publication_year:asc',
        'relevance': 'relevance_score:desc',
    }.get(sort or 'relevance', 'relevance_score:desc')


def _search_openalex(q: str, page: int, page_size: int, extra: dict | None = None, sort: str = 'relevance') -> dict[str, Any]:
    params = {
        'search': q,
        'page': page,
        'per_page': page_size,
        'mailto': _MAILTO,
        'sort': _openalex_sort_param(sort),
    }
    extra = dict(extra or {})
    if extra:
        params.update(extra)
    try:
        data = _get_json('https://api.openalex.org/works', params=params)
    except Exception:
        params.pop('sort', None)
        data = _get_json('https://api.openalex.org/works', params=params)
    items = []
    for w in data.get('results') or []:
        row = _from_openalex(w)
        if row.get('title'):
            items.append(row)
    total = int((data.get('meta') or {}).get('count') or 0)
    return paged(items, total, page, page_size)


def _from_openalex(w: dict) -> dict:
    ids = w.get('ids') or {}
    arxiv_id = ''
    arxiv_url = ids.get('arxiv') or ''
    m = re.search(r'arxiv\.org/abs/([^/\s]+)', arxiv_url or '')
    if m:
        arxiv_id = m.group(1)
    doi = _clean_doi(w.get('doi') or ids.get('doi') or '')
    oa = w.get('open_access') or {}
    pdf = oa.get('oa_url') or ''
    loc = (w.get('primary_location') or {}) or {}
    if not pdf:
        pdf = loc.get('pdf_url') or ''
    if not pdf:
        for extra in w.get('locations') or []:
            if extra.get('pdf_url'):
                pdf = extra['pdf_url']
                break
    if arxiv_id and not pdf:
        pdf = f'https://arxiv.org/pdf/{arxiv_id}.pdf'
    authors = [
        (a.get('author') or {}).get('display_name')
        for a in (w.get('authorships') or [])
    ]
    venue = ((loc.get('source') or {}) or {}).get('display_name') or ''
    oid = (w.get('id') or '').rsplit('/', 1)[-1]
    return _norm({
        'title': w.get('display_name') or w.get('title') or '',
        'authors': ', '.join(x for x in authors if x),
        'year': w.get('publication_year'),
        'abstract': _openalex_abstract(w.get('abstract_inverted_index')),
        'arxiv_id': arxiv_id,
        'doi': doi,
        'pdf_url': pdf,
        'abs_url': ids.get('openalex') or loc.get('landing_page_url') or '',
        'cites': w.get('cited_by_count') or 0,
        'venue': venue,
        'category': '',
        'external_id': oid,
    }, venue=venue or 'OpenAlex', source='openalex')


def _search_crossref(q: str, page: int, page_size: int, sort: str = 'relevance') -> dict[str, Any]:
    offset = (page - 1) * page_size
    cr_sort, cr_order = {
        'cites': ('is-referenced-by-count', 'desc'),
        'year': ('published', 'desc'),
        'newest': ('published', 'desc'),
        'year_asc': ('published', 'asc'),
        'relevance': ('relevance', 'desc'),
    }.get(sort or 'relevance', ('relevance', 'desc'))
    data = _get_json(
        'https://api.crossref.org/works',
        params={
            'query': q,
            'rows': page_size,
            'offset': offset,
            'sort': cr_sort,
            'order': cr_order,
            'select': 'DOI,title,author,published,abstract,URL,link,is-referenced-by-count,container-title,issued',
        },
    )
    message = data.get('message') or {}
    items = []
    for w in message.get('items') or []:
        title = ''
        titles = w.get('title') or []
        if titles:
            title = titles[0]
        if not title:
            continue
        issued = (w.get('issued') or w.get('published') or {}).get('date-parts') or [[None]]
        year = issued[0][0] if issued and issued[0] else None
        doi = _clean_doi(w.get('DOI') or '')
        pdf = ''
        for link in w.get('link') or []:
            ctype = (link.get('content-type') or '').lower()
            url = link.get('URL') or ''
            if 'pdf' in ctype or url.lower().endswith('.pdf'):
                pdf = url
                break
        venue = ''
        containers = w.get('container-title') or []
        if containers:
            venue = containers[0]
        items.append(_norm({
            'title': title,
            'authors': _authors(w.get('author')),
            'year': year,
            'abstract': _strip_xml(w.get('abstract') or ''),
            'arxiv_id': '',
            'doi': doi,
            'pdf_url': pdf,
            'abs_url': w.get('URL') or (f'https://doi.org/{doi}' if doi else ''),
            'cites': w.get('is-referenced-by-count') or 0,
            'venue': venue,
            'category': '',
            'external_id': doi,
        }, venue=venue or 'Crossref', source='crossref'))
    total = int(message.get('total-results') or 0)
    return paged(items, total, page, page_size)


def _openalex_abstract(inv) -> str:
    if not inv or not isinstance(inv, dict):
        return ''
    size = 0
    for positions in inv.values():
        if positions:
            size = max(size, max(positions) + 1)
    if not size:
        return ''
    arr = [''] * size
    for word, positions in inv.items():
        for p in positions or []:
            if 0 <= p < size:
                arr[p] = word
    return ' '.join(arr).strip()


def _strip_xml(text: str) -> str:
    cleaned = re.sub(r'<[^>]+>', ' ', text or '')
    return re.sub(r'\s+', ' ', cleaned).strip()


def _clean_doi(value: str) -> str:
    raw = (value or '').strip()
    if not raw:
        return ''
    raw = raw.replace('https://doi.org/', '').replace('http://doi.org/', '')
    m = _DOI_RE.search(raw)
    return m.group(0).rstrip(').,;') if m else ''


def _unpaywall_pdf(doi: str) -> str:
    try:
        data = _get_json(
            f'https://api.unpaywall.org/v2/{quote(doi, safe="/")}',
            params={'email': _MAILTO},
            timeout=15,
        )
    except Exception:
        return ''
    loc = data.get('best_oa_location') or {}
    for key in ('url_for_pdf', 'url'):
        url = (loc.get(key) or '').strip()
        if url and (key == 'url_for_pdf' or url.lower().endswith('.pdf')):
            return url
    return ''


def _openalex_pdf_by_doi(doi: str) -> str:
    try:
        data = _get_json(
            f'https://api.openalex.org/works/doi:{quote(doi, safe="/")}',
            params={'mailto': _MAILTO},
            timeout=15,
        )
    except Exception:
        return ''
    row = _from_openalex(data)
    return (row.get('pdf_url') or '').strip()


def annotate_search(user, payload: dict) -> dict:
    owned = user_owned_map(user)
    payload['results'] = annotate_owned(payload.get('results') or [], owned)
    return payload
