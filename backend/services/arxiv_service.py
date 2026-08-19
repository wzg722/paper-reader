"""arXiv search & metadata via official API."""
from __future__ import annotations

import re
import threading
import time
from typing import Any
from xml.etree import ElementTree as ET

import requests

ATOM_NS = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
OPEN_NS = {'opensearch': 'http://a9.com/-/spec/opensearch/1.1/'}
ARXIV_API = 'https://export.arxiv.org/api/query'
_HEADERS = {
    'User-Agent': 'PaperMind/1.0 (private research reader; mailto:demo@papermind.local)',
    'Accept': 'application/atom+xml, application/xml;q=0.9, */*;q=0.8',
}
_MIN_INTERVAL = 3.2
_CACHE_TTL = 15 * 60
_CACHE_MAX = 80

_lock = threading.Lock()
_last_slot = 0.0
_cache: dict[str, tuple[float, dict[str, Any]]] = {}


class ArxivBusy(Exception):
    def __init__(self, message='arXiv 请求过于频繁，请稍后再试'):
        super().__init__(message)


def fetch_arxiv(
    query: str | None = None,
    id_list: list[str] | None = None,
    start: int = 0,
    max_results: int = 10,
    sort_by: str = 'relevance',
) -> list[dict[str, Any]]:
    return query_arxiv(
        query=query, id_list=id_list, start=start,
        max_results=max_results, sort_by=sort_by,
    )['results']


def query_arxiv(
    query: str | None = None,
    id_list: list[str] | None = None,
    start: int = 0,
    max_results: int = 10,
    sort_by: str = 'relevance',
    sort_order: str = 'descending',
) -> dict[str, Any]:
    """Return {results, total, start, max_results} from the arXiv Atom API."""
    max_results = max(1, min(int(max_results or 10), 50))
    start = max(0, int(start or 0))
    sort_by = sort_by if sort_by in ('relevance', 'lastUpdatedDate', 'submittedDate') else 'relevance'
    sort_order = sort_order if sort_order in ('descending', 'ascending') else 'descending'
    params: dict[str, Any] = {
        'start': start,
        'max_results': max_results,
        'sortBy': sort_by,
        'sortOrder': sort_order,
    }
    if id_list:
        params['id_list'] = ','.join(_normalize_id(x) for x in id_list)
    elif query:
        q = query.strip()
        if re.match(r'^\d{4}\.\d{4,5}(v\d+)?$', q):
            params['id_list'] = _normalize_id(q)
        else:
            params['search_query'] = _build_search_query(q)
    else:
        return {'results': [], 'total': 0, 'start': start, 'max_results': max_results}

    key = _cache_key(params)
    hit = _cache_get(key)
    if hit is not None:
        return hit
    try:
        xml = _request_atom(params)
    except ArxivBusy:
        stale = _cache_get(key, allow_stale=True)
        if stale is not None:
            return stale
        raise
    results, total = _parse_atom(xml)
    payload = {
        'results': results,
        'total': total,
        'start': start,
        'max_results': max_results,
    }
    _cache_set(key, payload)
    return payload


def _cache_key(params: dict[str, Any]) -> str:
    return '&'.join(f'{k}={params[k]}' for k in sorted(params))


def _cache_get(key: str, allow_stale: bool = False) -> dict[str, Any] | None:
    row = _cache.get(key)
    if not row:
        return None
    exp, data = row
    if exp >= time.time() or allow_stale:
        return data
    return None


def _cache_set(key: str, data: dict[str, Any]):
    if len(_cache) >= _CACHE_MAX:
        oldest = sorted(_cache.items(), key=lambda kv: kv[1][0])[:20]
        for k, _ in oldest:
            _cache.pop(k, None)
    _cache[key] = (time.time() + _CACHE_TTL, data)


def _wait_slot():
    global _last_slot
    with _lock:
        now = time.monotonic()
        wait = _MIN_INTERVAL - (now - _last_slot)
        if wait < 0:
            wait = 0
        _last_slot = now + wait
    if wait > 0:
        time.sleep(wait)


def _request_atom(params: dict[str, Any]) -> str:
    last_status = 0
    for attempt in range(4):
        _wait_slot()
        try:
            r = requests.get(ARXIV_API, params=params, headers=_HEADERS, timeout=25)
        except requests.RequestException as e:
            if attempt >= 3:
                raise ArxivBusy('暂时无法连接 arXiv，请稍后再试') from e
            time.sleep(min(8.0, 2.0 * (attempt + 1)))
            continue
        last_status = r.status_code
        if r.status_code == 200 and _looks_like_atom(r.text):
            return r.text
        if r.status_code in (429, 502, 503, 504) or (
            r.status_code == 200 and not _looks_like_atom(r.text)
        ):
            delay = _retry_delay(r, attempt)
            time.sleep(delay)
            continue
        r.raise_for_status()
        raise ArxivBusy('arXiv 返回了无法解析的结果')
    if last_status == 429:
        raise ArxivBusy('arXiv 请求过于频繁，请稍后再试')
    raise ArxivBusy('arXiv 暂时不可用，请稍后再试')


def _retry_delay(response, attempt: int) -> float:
    raw = response.headers.get('Retry-After')
    try:
        delay = float(raw)
    except (TypeError, ValueError):
        delay = 2.0 * (attempt + 1)
    return min(max(delay, 1.0), 10.0)


def _looks_like_atom(text: str) -> bool:
    head = (text or '')[:800].lstrip()
    return head.startswith('<?xml') or head.startswith('<feed') or '<feed' in head[:200]


def _build_search_query(query: str) -> str:
    q = query.strip()
    if re.search(r'\b(all|ti|abs|au|cat|co):', q, re.I) or ' OR ' in q or ' AND ' in q:
        return q
    if ' ' in q:
        return f'all:"{q}"'
    return f'all:{q}'


def _normalize_id(arxiv_id: str) -> str:
    arxiv_id = arxiv_id.strip()
    arxiv_id = re.sub(r'^arxiv:', '', arxiv_id, flags=re.I)
    arxiv_id = re.sub(r'^https?://arxiv\.org/(abs|pdf)/', '', arxiv_id)
    arxiv_id = arxiv_id.replace('.pdf', '')
    return arxiv_id


def _parse_atom(xml_text: str) -> tuple[list[dict[str, Any]], int]:
    root = ET.fromstring(xml_text)
    total_text = (
        root.findtext('opensearch:totalResults', default='', namespaces=OPEN_NS)
        or root.findtext('{http://a9.com/-/spec/opensearch/1.1/}totalResults')
        or '0'
    )
    try:
        total = int(total_text)
    except ValueError:
        total = 0
    items = []
    for entry in root.findall('atom:entry', ATOM_NS):
        aid = entry.findtext('atom:id', default='', namespaces=ATOM_NS)
        arxiv_id = aid.rstrip('/').split('/abs/')[-1] if '/abs/' in aid else aid
        title = (entry.findtext('atom:title', default='', namespaces=ATOM_NS) or '').strip()
        title = re.sub(r'\s+', ' ', title)
        summary = (entry.findtext('atom:summary', default='', namespaces=ATOM_NS) or '').strip()
        summary = re.sub(r'\s+', ' ', summary)
        published = entry.findtext('atom:published', default='', namespaces=ATOM_NS) or ''
        year = int(published[:4]) if published[:4].isdigit() else None
        authors = [
            a.findtext('atom:name', default='', namespaces=ATOM_NS)
            for a in entry.findall('atom:author', ATOM_NS)
        ]
        pdf_url = ''
        for link in entry.findall('atom:link', ATOM_NS):
            if link.attrib.get('title') == 'pdf' or link.attrib.get('type') == 'application/pdf':
                pdf_url = link.attrib.get('href', '')
                break
        doi = entry.findtext('arxiv:doi', default='', namespaces=ATOM_NS) or ''
        cat_el = entry.find('arxiv:primary_category', ATOM_NS)
        category = (cat_el.attrib.get('term') if cat_el is not None else '') or ''
        items.append({
            'arxiv_id': arxiv_id,
            'title': title,
            'authors': ', '.join(authors),
            'abstract': summary,
            'year': year,
            'doi': doi or f'10.48550/arXiv.{arxiv_id}',
            'pdf_url': pdf_url or f'https://arxiv.org/pdf/{arxiv_id}.pdf',
            'abs_url': f'https://arxiv.org/abs/{arxiv_id}',
            'category': category,
            'venue': 'arXiv',
            'cites': 0,
        })
    if not total:
        total = len(items)
    return items, total
