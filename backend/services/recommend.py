"""Personalized and hot paper recommendations for the Discover page."""
from __future__ import annotations

import re
from collections import Counter

from django.db.models import Count, Q

from papers.models import Paper
from services.arxiv_service import query_arxiv

# Map user-facing Chinese / domain phrases to arXiv English queries + categories.
_DIRECTION_RULES = [
    (r'OCR|文字识别|光学字符|版面', ['OCR', 'text recognition'], ['cs.CV', 'eess.IV']),
    (r'视觉|检测|图像|CV|计算机视觉', ['computer vision', 'object detection'], ['cs.CV']),
    (r'Transformer|注意力机制|自注意力', ['Transformer', 'self-attention'], ['cs.LG', 'cs.CL']),
    (r'NLP|自然语言|语言模型|大模型|LLM', ['language model', 'NLP'], ['cs.CL']),
    (r'防作弊|监考|proctor|作弊', ['online proctoring', 'cheating detection'], ['cs.CV']),
    (r'考试', ['exam', 'assessment'], ['cs.CY']),
    (r'ResNet', ['ResNet'], ['cs.CV']),
    (r'ViT|视觉Transformer', ['Vision Transformer'], ['cs.CV']),
    (r'DETR', ['DETR', 'object detection'], ['cs.CV']),
    (r'深度学习|神经网络', ['deep learning'], ['cs.LG']),
    (r'多模态', ['multimodal'], ['cs.CV', 'cs.CL']),
]

_SKIP_TOKENS = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'were',
    'paper', 'using', 'based', 'via', 'into', 'over', 'under', 'your', 'our',
    '论文', '研究', '方法', '基于', '一种', '以及', 'pp',
}
_KEEP_SHORT = {'OCR', 'AI', 'CV', 'ML', 'DL', 'IR', 'UI'}

_TOKEN_SPLIT = re.compile(r'[、，,;/|]+')


def page_params(request, default_size=10):
    try:
        page = max(int(request.query_params.get('page', 1) or 1), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = int(request.query_params.get('page_size', default_size) or default_size)
    except (TypeError, ValueError):
        page_size = default_size
    page_size = min(max(page_size, 1), 50)
    start = (page - 1) * page_size
    return page, page_size, start


def paged(results, count, page, page_size, extra=None):
    total_pages = (count + page_size - 1) // page_size if count else 0
    data = {
        'results': results,
        'count': count,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }
    if extra:
        data.update(extra)
    return data


def user_owned_map(user):
    rows = Paper.objects.filter(user=user, deleted_at__isnull=True).values_list(
        'arxiv_id', 'doi', 'title', 'id',
    )
    mapping = {'arxiv': {}, 'doi': {}, 'title': {}}
    for aid, doi, title, pid in rows:
        if aid:
            key = re.sub(r'v\d+$', '', aid.strip())
            mapping['arxiv'][aid] = pid
            mapping['arxiv'][key] = pid
        if doi:
            mapping['doi'][doi.strip().lower()] = pid
        if title:
            mapping['title'][_norm_title(title)] = pid
    return mapping


def _norm_title(title: str) -> str:
    return re.sub(r'\s+', ' ', (title or '').strip().lower())


def annotate_owned(items, owned):
    arxiv_map = owned.get('arxiv') if isinstance(owned, dict) and 'arxiv' in owned else owned
    doi_map = owned.get('doi') if isinstance(owned, dict) else {}
    title_map = owned.get('title') if isinstance(owned, dict) else {}
    out = []
    for it in items:
        row = dict(it)
        aid = row.get('arxiv_id') or ''
        bare = re.sub(r'v\d+$', '', aid)
        doi = (row.get('doi') or '').strip().lower()
        pid = (arxiv_map or {}).get(aid) or (arxiv_map or {}).get(bare)
        if not pid and doi:
            pid = (doi_map or {}).get(doi)
        if not pid:
            pid = (title_map or {}).get(_norm_title(row.get('title') or ''))
        row['in_library'] = bool(pid)
        row['paper_id'] = pid
        out.append(row)
    return out


def collect_user_profile(user) -> dict:
    """Keywords, arXiv categories, and human-readable reasons from profile + behavior."""
    weights = Counter()
    reasons = []
    cats = []

    direction = (getattr(user, 'research_direction', None) or '').strip()
    if direction:
        reasons.append(f'研究方向：{direction}')
        for part in _TOKEN_SPLIT.split(direction):
            part = part.strip()
            if not part:
                continue
            mapped = False
            for pat, kws, cat_list in _DIRECTION_RULES:
                if re.search(pat, part, re.I):
                    for kw in kws:
                        weights[kw] += 4
                    cats.extend(cat_list)
                    mapped = True
            if not mapped:
                en = _englishish(part)
                if en:
                    weights[en] += 3

    recent = list(
        Paper.objects.filter(user=user, deleted_at__isnull=True)
        .order_by('-last_read_at', '-updated_at')[:8]
    )
    if recent:
        titles = [p.title for p in recent if p.title][:2]
        if titles:
            reasons.append('最近阅读：' + '、'.join(t[:40] for t in titles))
        for p in recent:
            _absorb_paper(p, weights, cats, boost=3)

    starred = Paper.objects.filter(user=user, starred=True, deleted_at__isnull=True)[:6]
    for p in starred:
        _absorb_paper(p, weights, cats, boost=2)

    noted = (
        Paper.objects.filter(user=user, deleted_at__isnull=True)
        .annotate(nc=Count('notes'))
        .filter(nc__gt=0)
        .order_by('-nc')[:5]
    )
    if noted:
        reasons.append('根据你的笔记与划词兴趣')
        for p in noted:
            _absorb_paper(p, weights, cats, boost=2)

    try:
        from reader.models import GlossaryTerm
        terms = GlossaryTerm.objects.filter(user=user).order_by('-id')[:12]
        for t in terms:
            token = (t.term_en or t.term_zh or '').strip()
            if token and _englishish(token):
                weights[_englishish(token)] += 2
    except Exception:
        pass

    keywords = [k for k, _ in weights.most_common(8) if k]
    cats = list(dict.fromkeys(cats))[:4]
    if not keywords:
        keywords = ['computer vision', 'deep learning']
        cats = cats or ['cs.CV', 'cs.LG']
        reasons.append('暂无足够行为数据，先按计算机视觉 / 深度学习推荐')
    return {
        'keywords': keywords,
        'categories': cats or ['cs.CV', 'cs.LG', 'cs.AI'],
        'reasons': reasons[:3],
        'query': _arxiv_or_query(keywords),
    }


def _englishish(text: str) -> str:
    text = (text or '').strip()
    if not text or text.lower() in _SKIP_TOKENS:
        return ''
    if re.search(r'[\u4e00-\u9fff]', text) and not re.search(r'[A-Za-z]', text):
        return ''
    if len(text) < 2:
        return ''
    return text


def _absorb_paper(paper, weights: Counter, cats: list, boost: int = 1):
    blob = ' '.join(filter(None, [
        paper.title, paper.title_zh, paper.tags, getattr(paper.category, 'name', None) if paper.category_id else '',
    ]))
    for pat, kws, cat_list in _DIRECTION_RULES:
        if re.search(pat, blob, re.I):
            for kw in kws:
                weights[kw] += boost
            cats.extend(cat_list)
    if paper.tags:
        for tag in _TOKEN_SPLIT.split(paper.tags):
            en = _englishish(tag)
            if en:
                weights[en] += boost
    for token in re.findall(r'\b[A-Z]{2,}\b', paper.title or ''):
        if token.lower() in _SKIP_TOKENS:
            continue
        if len(token) <= 2 and token.upper() not in _KEEP_SHORT:
            continue
        weights[token] += boost
    for token in re.findall(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b', paper.title or ''):
        weights[token] += boost


def _arxiv_or_query(keywords: list[str]) -> str:
    parts = []
    for kw in keywords:
        kw = kw.strip()
        if not kw:
            continue
        if ' ' in kw:
            parts.append(f'all:"{kw}"')
        else:
            parts.append(f'all:{kw}')
    return ' OR '.join(parts[:6]) or 'all:deep learning'


def list_filters(request):
    sort = (request.query_params.get('sort') or '').strip() or 'relevance'
    if sort not in ('relevance', 'newest', 'year', 'year_asc', 'cites', 'updated'):
        sort = 'relevance'
    year_from = _as_int(request.query_params.get('year_from'))
    year_to = _as_int(request.query_params.get('year_to'))
    min_cites = _as_int(request.query_params.get('min_cites')) or 0
    return {
        'sort': sort,
        'year_from': year_from,
        'year_to': year_to,
        'min_cites': max(0, min_cites),
    }


def _as_int(val):
    try:
        if val is None or val == '':
            return None
        return int(val)
    except (TypeError, ValueError):
        return None


def _with_year(query: str, year_from, year_to) -> str:
    if not year_from and not year_to:
        return query
    y0 = year_from or 1991
    y1 = year_to or 2099
    clause = f'submittedDate:[{y0:04d}0101000000 TO {y1:04d}1231235959]'
    q = (query or '').strip()
    if not q:
        return clause
    return f'({q}) AND {clause}'


def _arxiv_sort(sort: str) -> tuple[str, str]:
    return {
        'relevance': ('relevance', 'descending'),
        'newest': ('submittedDate', 'descending'),
        'year': ('submittedDate', 'descending'),
        'year_asc': ('submittedDate', 'ascending'),
        'updated': ('lastUpdatedDate', 'descending'),
        'cites': ('submittedDate', 'descending'),
    }.get(sort or 'relevance', ('relevance', 'descending'))


def filter_items(items, year_from=None, year_to=None, min_cites=0):
    out = []
    for it in items:
        y = it.get('year')
        if year_from and (not y or int(y) < year_from):
            continue
        if year_to and (not y or int(y) > year_to):
            continue
        if min_cites and (it.get('cites') or 0) < min_cites:
            continue
        out.append(it)
    return out


def sort_items(items, sort: str):
    if sort == 'cites':
        items.sort(key=lambda x: (x.get('cites') or 0, x.get('year') or 0, x.get('readers') or 0), reverse=True)
    elif sort == 'year':
        items.sort(key=lambda x: (x.get('year') or 0, x.get('cites') or 0), reverse=True)
    elif sort == 'year_asc':
        items.sort(key=lambda x: (x.get('year') or 9999, -(x.get('cites') or 0)))
    elif sort == 'newest':
        items.sort(key=lambda x: (x.get('year') or 0, str(x.get('arxiv_id') or '')), reverse=True)
    return items


def platform_match_items(keywords, limit=80) -> list[dict]:
    q = Q()
    for kw in (keywords or [])[:6]:
        kw = (kw or '').strip()
        if len(kw) < 2:
            continue
        q |= Q(title__icontains=kw) | Q(tags__icontains=kw) | Q(intro__icontains=kw) | Q(abstract__icontains=kw)
    if not q:
        return platform_hot_items(limit)
    qs = (
        Paper.objects.filter(deleted_at__isnull=True)
        .filter(q)
        .select_related('category')
        .order_by('-cites', '-year', '-id')[:300]
    )
    buckets = {}
    for p in qs:
        key = (p.arxiv_id or '').lower() or f't:{(p.title or "").strip().lower()}'
        if key in buckets:
            buckets[key]['cites'] = max(buckets[key].get('cites') or 0, p.cites or 0)
            continue
        buckets[key] = {
            'title': p.title,
            'title_zh': p.title_zh,
            'authors': p.authors,
            'year': p.year,
            'abstract': (p.abstract or p.intro or '')[:500],
            'arxiv_id': p.arxiv_id,
            'doi': p.doi,
            'cites': p.cites or 0,
            'venue': p.venue or '',
            'pdf_url': p.pdf_url or (f'https://arxiv.org/pdf/{p.arxiv_id}.pdf' if p.arxiv_id else ''),
            'abs_url': f'https://arxiv.org/abs/{p.arxiv_id}' if p.arxiv_id else '',
            'category': p.category.name if p.category_id else '',
            'source': 'platform',
            'paper_id': p.id,
            'reason': '站内高引用匹配',
        }
    items = list(buckets.values())
    items.sort(key=lambda x: (x.get('cites') or 0, x.get('year') or 0), reverse=True)
    return items[:limit]


def recommend_from_arxiv(user, page=1, page_size=5, sort='relevance',
                         year_from=None, year_to=None, min_cites=0) -> dict:
    profile = collect_user_profile(user)
    owned = user_owned_map(user)
    reason = ' · '.join(profile['reasons']) if profile['reasons'] else '根据你的研究方向推荐'
    query = _with_year(profile['query'], year_from, year_to)
    sort_by, sort_order = _arxiv_sort(sort)
    start = (page - 1) * page_size

    if sort == 'cites' or min_cites:
        local = filter_items(
            platform_match_items(profile['keywords']),
            year_from, year_to, min_cites,
        )
        arxiv_items = []
        if not min_cites:
            try:
                data = query_arxiv(
                    query=query, start=0, max_results=40,
                    sort_by=sort_by, sort_order=sort_order,
                )
                seen = {(x.get('arxiv_id') or '').lower() for x in local if x.get('arxiv_id')}
                for it in annotate_owned(data.get('results') or [], owned):
                    if (it.get('arxiv_id') or '').lower() in seen:
                        continue
                    it['reason'] = reason
                    it['source'] = 'arxiv'
                    arxiv_items.append(it)
            except Exception:
                pass
        merged = local + arxiv_items
        sort_items(merged, sort or 'cites')
        total = min(len(merged), 100)
        page_rows = annotate_owned(merged[start:start + page_size], owned)
        return paged(page_rows, total, page, page_size, extra={
            'keywords': profile['keywords'],
            'reasons': profile['reasons'],
        })

    data = None
    try:
        data = query_arxiv(
            query=query,
            start=start,
            max_results=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except Exception:
        data = None
    if data:
        results = []
        for it in annotate_owned(data['results'], owned):
            it['reason'] = reason
            it['source'] = 'arxiv'
            results.append(it)
        results = filter_items(results, year_from, year_to, min_cites)
        total = min(int(data['total'] or 0), 100)
        return paged(results, total, page, page_size, extra={
            'keywords': profile['keywords'],
            'reasons': profile['reasons'],
        })

    local = filter_items(platform_match_items(profile['keywords']), year_from, year_to, min_cites)
    sort_items(local, sort if sort != 'relevance' else 'cites')
    page_rows = annotate_owned(local[start:start + page_size], owned)
    for it in page_rows:
        it.setdefault('reason', reason)
        it.setdefault('source', 'platform')
    reasons = list(profile['reasons'])
    reasons.append('arXiv 暂时繁忙，已改用站内论文')
    return paged(page_rows, min(len(local), 100), page, page_size, extra={
        'keywords': profile['keywords'],
        'reasons': reasons,
    })


def platform_hot_items(limit=80) -> list[dict]:
    """Deduped papers across all users, ranked by cites then reader count."""
    qs = (
        Paper.objects.filter(deleted_at__isnull=True)
        .select_related('category')
        .order_by('-cites', '-year', '-id')
    )
    buckets = {}
    readers = Counter()
    for p in qs[:400]:
        key = (p.arxiv_id or '').lower() or f't:{ (p.title or "").strip().lower() }'
        readers[key] += 1
        if key in buckets:
            buckets[key]['cites'] = max(buckets[key].get('cites') or 0, p.cites or 0)
            continue
        buckets[key] = {
            'title': p.title,
            'title_zh': p.title_zh,
            'authors': p.authors,
            'year': p.year,
            'abstract': (p.abstract or p.intro or '')[:500],
            'arxiv_id': p.arxiv_id,
            'doi': p.doi,
            'cites': p.cites or 0,
            'venue': p.venue or '',
            'pdf_url': p.pdf_url or (f'https://arxiv.org/pdf/{p.arxiv_id}.pdf' if p.arxiv_id else ''),
            'abs_url': f'https://arxiv.org/abs/{p.arxiv_id}' if p.arxiv_id else '',
            'category': p.category.name if p.category_id else '',
            'source': 'platform',
            'paper_id': p.id,
        }
    items = list(buckets.values())
    for it in items:
        key = (it.get('arxiv_id') or '').lower() or f't:{ (it.get("title") or "").strip().lower() }'
        it['readers'] = readers[key]
    items.sort(key=lambda x: (x.get('cites') or 0, x.get('readers') or 0, x.get('year') or 0), reverse=True)
    return items[:limit]


def hot_papers(user, page=1, page_size=5, sort='cites',
               year_from=None, year_to=None, min_cites=0) -> dict:
    local = filter_items(platform_hot_items(), year_from, year_to, min_cites)
    sort_items(local, sort if sort != 'relevance' else 'cites')
    owned = user_owned_map(user)
    profile = collect_user_profile(user)
    cat_query = _with_year(
        ' OR '.join(f'cat:{c}' for c in profile['categories'][:3]) or 'cat:cs.LG',
        year_from, year_to,
    )
    sort_by, sort_order = _arxiv_sort(sort if sort != 'cites' else 'newest')

    start = (page - 1) * page_size
    local_n = len(local)
    need_arxiv = not min_cites
    arxiv_data = {'results': [], 'total': 0}
    arxiv_items = []
    if need_arxiv:
        need_arxiv_start = max(0, start - local_n)
        fill = page_size if start >= local_n else max(0, page_size - (local_n - start))
        include_arxiv = fill > 0 or start >= local_n
        try:
            arxiv_data = query_arxiv(
                query=cat_query,
                start=need_arxiv_start if include_arxiv else 0,
                max_results=max(fill, page_size) if include_arxiv else 1,
                sort_by=sort_by,
                sort_order=sort_order,
            )
        except Exception:
            arxiv_data = {'results': [], 'total': 0}
        local_ids = {(x.get('arxiv_id') or '').lower() for x in local if x.get('arxiv_id')}
        if include_arxiv:
            for it in arxiv_data.get('results') or []:
                if (it.get('arxiv_id') or '').lower() in local_ids:
                    continue
                row = dict(it)
                row['source'] = 'arxiv'
                row['reason'] = '近期领域新作'
                arxiv_items.append(row)
        arxiv_items = filter_items(arxiv_items, year_from, year_to, 0)

    if sort in ('cites', 'year', 'year_asc', 'newest') and (local or arxiv_items):
        merged = []
        for it in local:
            row = dict(it)
            row.setdefault('reason', '站内高引用 / 多人在读')
            row.setdefault('source', 'platform')
            merged.append(row)
        merged.extend(arxiv_items)
        sort_items(merged, sort)
        total = min(len(merged) if min_cites else (local_n + int(arxiv_data.get('total') or 0)), 200)
        page_rows = merged[start:start + page_size]
    elif start >= local_n:
        page_rows = arxiv_items[:page_size]
        total = min(local_n + int(arxiv_data.get('total') or 0), 200)
    else:
        page_rows = []
        for it in local[start:start + page_size]:
            row = dict(it)
            row.setdefault('reason', '站内高引用 / 多人在读')
            row.setdefault('source', 'platform')
            page_rows.append(row)
        if len(page_rows) < page_size:
            page_rows.extend(arxiv_items[: page_size - len(page_rows)])
        total = min(local_n + int(arxiv_data.get('total') or 0), 200)

    page_rows = annotate_owned(page_rows, owned)
    for i, row in enumerate(page_rows):
        row['rank'] = start + i + 1
    return paged(page_rows, total, page, page_size)
