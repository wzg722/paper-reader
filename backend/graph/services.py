"""Build a paper/concept/related knowledge graph from the user's library."""
from __future__ import annotations

import re

from django.db.models import Q

from graph.models import GraphEdge, GraphNode
from papers.models import Paper

RELATED_BY_KEYWORD = [
    (r'OCR|文字识别|光学字符|PP-OCR', [
        ('SVTR', 'A Scene Text Recognition model with a single visual model.', 2022, 'OCR,序列识别'),
        ('CRNN', 'An end-to-end trainable neural network for image-based sequence recognition.', 2016, 'OCR,序列识别,卷积网络 CNN'),
        ('DB (可微分二值化)', 'Real-time scene text detection with differentiable binarization.', 2020, 'OCR,目标检测'),
        ('MASTER', 'Multi-aspect non-local network for scene text recognition.', 2021, 'OCR,序列识别'),
        ('TrOCR', 'Transformer-based optical character recognition with pre-trained models.', 2021, 'OCR,Transformer,预训练'),
        ('ResNet', 'Deep Residual Learning for Image Recognition.', 2016, '卷积网络 CNN,图像分类'),
    ]),
    (r'Transformer|注意力|ViT', [
        ('ViT', 'An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale.', 2021, 'Transformer,图像分类,预训练'),
        ('DETR', 'End-to-End Object Detection with Transformers.', 2020, 'Transformer,目标检测'),
        ('Faster R-CNN', 'Towards Real-Time Object Detection with Region Proposal Networks.', 2015, '目标检测,卷积网络 CNN'),
    ]),
    (r'ResNet|残差|图像分类', [
        ('ResNet', 'Deep Residual Learning for Image Recognition.', 2016, '卷积网络 CNN,图像分类'),
    ]),
    (r'检测|DETR|R-CNN|目标检测', [
        ('Faster R-CNN', 'Towards Real-Time Object Detection with Region Proposal Networks.', 2015, '目标检测,卷积网络 CNN'),
        ('DETR', 'End-to-End Object Detection with Transformers.', 2020, 'Transformer,目标检测'),
    ]),
    (r'轻量|部署', [
        ('PP-LCNet', 'A Lightweight CPU Convolutional Neural Network.', 2021, '轻量化部署,卷积网络 CNN'),
    ]),
]

EXTRA_CONCEPTS = [
    (r'OCR|文字识别|PP-OCR', ['序列识别', '轻量化部署', '卷积网络 CNN']),
    (r'Transformer|注意力', ['预训练', '注意力机制']),
    (r'检测|DETR', ['目标检测']),
]


def short_label(label: str) -> str:
    s = re.sub(r'\s+', ' ', (label or '').strip())
    if not s:
        return ''
    if ':' in s:
        head = s.split(':', 1)[0].strip()
        if 2 <= len(head) <= 28:
            return head
    if len(s) <= 22:
        return s
    return s[:20] + '…'


def sync_library_graph(user) -> dict:
    papers = Paper.objects.filter(user=user, deleted_at__isnull=True)
    created_nodes = 0
    paper_nodes = []
    for p in papers:
        node, created = GraphNode.objects.get_or_create(
            user=user, paper=p, node_type='paper',
            defaults={
                'label': p.title, 'year': p.year, 'cites': p.cites,
                'tags': p.tags, 'read_status': True,
                'description': p.intro or (p.abstract or '')[:240],
            },
        )
        if not created:
            changed = False
            if p.title and node.label != p.title:
                node.label = p.title
                changed = True
            if p.year and node.year != p.year:
                node.year = p.year
                changed = True
            if not node.read_status:
                node.read_status = True
                changed = True
            if changed:
                node.save()
        if created:
            created_nodes += 1
        paper_nodes.append(node)
        concepts = _concepts_for_paper(p)
        for name in concepts:
            concept = _get_concept(user, name)
            _link(user, node, concept, 'concept_of')

    for node in paper_nodes:
        blob = f'{node.label} {node.tags or ""} {node.description or ""}'
        for pattern, works in RELATED_BY_KEYWORD:
            if not re.search(pattern, blob, re.I):
                continue
            for title, desc, year, tags in works:
                _ensure_related(user, node, title, desc, year, tags)

    return {'created_nodes': created_nodes, 'paper_count': len(paper_nodes)}


def _concepts_for_paper(paper) -> list[str]:
    names = []
    if paper.tags:
        names.extend(t.strip() for t in paper.tags.split(',') if t.strip())
    blob = f'{paper.title or ""} {paper.tags or ""} {paper.intro or ""}'
    for pattern, extras in EXTRA_CONCEPTS:
        if re.search(pattern, blob, re.I):
            names.extend(extras)
    short = short_label(paper.title or '')
    out, seen = [], set()
    for n in names:
        key = n.lower()
        if key in seen:
            continue
        if short and n.lower() == short.lower():
            continue
        seen.add(key)
        out.append(n)
    return out[:8]


def _get_concept(user, name: str) -> GraphNode:
    node = GraphNode.objects.filter(user=user, node_type='concept', label=name).first()
    if node:
        return node
    return GraphNode.objects.create(
        user=user, node_type='concept', label=name,
        description=f'概念：{name}',
    )


def _ensure_related(user, source_paper_node, title, desc, year, tags):
    existing = GraphNode.objects.filter(user=user).exclude(node_type='concept').filter(
        Q(label=title) | Q(label__istartswith=f'{title}:') | Q(label__istartswith=f'{title} '),
    ).first()
    if existing:
        related = existing
        if related.paper_id and not related.read_status:
            related.read_status = True
            related.save(update_fields=['read_status'])
    else:
        lib = Paper.objects.filter(user=user, deleted_at__isnull=True).filter(
            Q(title__iexact=title) | Q(title__istartswith=title),
        ).first()
        related = GraphNode.objects.create(
            user=user,
            node_type='paper' if lib else 'related',
            label=title if not lib else lib.title,
            year=year if not lib else lib.year,
            cites=lib.cites if lib else 0,
            tags=tags,
            paper=lib,
            description=desc if not lib else (lib.intro or desc),
            read_status=bool(lib),
        )
    for tag in [t.strip() for t in (tags or '').split(',') if t.strip()]:
        concept = _get_concept(user, tag)
        _link(user, related, concept, 'concept_of')
        _link(user, source_paper_node, concept, 'concept_of')
    _link(user, source_paper_node, related, 'related')


def _link(user, a: GraphNode, b: GraphNode, relation: str) -> None:
    if not a or not b or a.id == b.id:
        return
    if GraphEdge.objects.filter(user=user, source_node=a, target_node=b).exists():
        return
    if GraphEdge.objects.filter(user=user, source_node=b, target_node=a).exists():
        return
    GraphEdge.objects.create(
        user=user, source_node=a, target_node=b, relation_type=relation,
    )


_QUERY_RULES = [
    (r'OCR|文字识别|光学字符|PP-OCR|SVTR|CRNN|TrOCR|MASTER', ['OCR', 'text recognition']),
    (r'序列识别', ['scene text recognition', 'sequence recognition']),
    (r'轻量化|轻量部署|PP-LCNet', ['lightweight network', 'efficient OCR']),
    (r'卷积网络|\bCNN\b', ['CNN', 'convolutional neural network']),
    (r'预训练|pre-?train', ['pre-training', 'pretrained']),
    (r'注意力机制|self-attention|注意力', ['attention', 'Transformer']),
    (r'Transformer', ['Transformer']),
    (r'目标检测|object detection|Faster R-CNN|\bDETR\b', ['object detection']),
    (r'图像分类|image classification', ['image classification']),
    (r'ViT|Vision Transformer', ['Vision Transformer']),
    (r'ResNet', ['ResNet']),
    (r'可微分二值化|\bDB\b', ['scene text detection']),
    (r'NLP|自然语言', ['language model', 'NLP']),
    (r'深度学习', ['deep learning']),
    (r'BERT', ['BERT', 'language model']),
]
_ASCII_TERM = re.compile(r'^[A-Za-z][A-Za-z0-9+\-()]{1,40}$')
_SKIP_QUERY = {
    'the', 'and', 'for', 'with', 'from', 'that', 'this', 'are', 'was', 'a', 'an',
    'of', 'in', 'on', 'to', 'is', 'practical', 'system', 'network', 'model',
}


def build_arxiv_query(text: str, extra: str = '') -> dict:
    """Turn a graph node / keyword into an arXiv search_query."""
    blob = f'{text or ""} {extra or ""}'
    terms: list[str] = []
    seen = set()

    def add(term: str):
        t = (term or '').strip()
        if not t:
            return
        key = t.lower()
        if key in seen:
            return
        seen.add(key)
        terms.append(t)

    for pat, ens in _QUERY_RULES:
        if re.search(pat, blob, re.I):
            for t in ens:
                add(t)
    for tok in re.split(r'[\s,;:/|]+', blob):
        t = tok.strip('()[]「」《》')
        if _ASCII_TERM.match(t) and t.lower() not in _SKIP_QUERY and len(t) >= 2:
            add(t)

    if not terms:
        add('computer vision')

    parts = []
    for t in terms[:3]:
        parts.append(f'all:"{t}"' if ' ' in t else f'all:{t}')
    return {
        'query': ' OR '.join(parts),
        'topic': terms[0],
        'terms': terms[:4],
    }


def recommend_arxiv_for_node(node: GraphNode | None, q: str, page: int, page_size: int) -> dict:
    from services.arxiv_service import query_arxiv
    from services.recommend import paged

    extra = ''
    label = q
    if node is not None:
        label = node.label or q
        extra = f'{getattr(node, "tags", "") or ""} {short_label(node.label)}'
    built = build_arxiv_query(label, extra)
    page = max(int(page or 1), 1)
    page_size = min(max(int(page_size or 5), 1), 20)
    start = (page - 1) * page_size
    data = query_arxiv(
        query=built['query'], start=start, max_results=page_size, sort_by='relevance',
    )
    return paged(data.get('results') or [], int(data.get('total') or 0), page, page_size, extra={
        'query': built['query'],
        'topic': built['topic'],
        'terms': built['terms'],
        'source': 'arxiv',
        'node_id': node.id if node else None,
        'node_label': short_label(label) if label else '',
    })


def bind_node_to_paper(node: GraphNode, paper: Paper) -> GraphNode:
    node.paper = paper
    node.read_status = True
    if node.node_type != 'paper':
        node.node_type = 'paper'
    if paper.title:
        node.label = paper.title[:300]
    if paper.year:
        node.year = paper.year
    if paper.intro or paper.abstract:
        node.description = paper.intro or (paper.abstract or '')[:240]
    node.save()
    return node


def bind_existing_library_papers(user) -> int:
    """Link related graph nodes to papers already in the user's library."""
    unbound = list(
        GraphNode.objects.filter(user=user, paper__isnull=True).exclude(node_type='concept')
    )
    if not unbound:
        return 0
    papers = list(
        Paper.objects.filter(user=user, deleted_at__isnull=True).only(
            'id', 'title', 'arxiv_id', 'doi', 'intro', 'abstract', 'year',
        )
    )
    if not papers:
        return 0
    linked = 0
    for node in unbound:
        paper = match_library_paper(papers, node)
        if not paper:
            continue
        bind_node_to_paper(node, paper)
        linked += 1
    return linked


def match_library_paper(papers: list[Paper], node: GraphNode, hit: dict | None = None) -> Paper | None:
    if hit:
        aid = (hit.get('arxiv_id') or '').strip()
        doi = (hit.get('doi') or '').strip()
        title = (hit.get('title') or '').strip().lower()
        for p in papers:
            if aid and (p.arxiv_id or '') == aid:
                return p
            if doi and (p.doi or '') == doi:
                return p
            if title and (p.title or '').strip().lower() == title:
                return p
    label = (node.label or '').strip()
    hint = _title_hint(node)
    for p in papers:
        pt = (p.title or '').strip()
        if not pt:
            continue
        if label and (pt.lower() == label.lower() or pt.lower().startswith(label.lower() + ':')
                      or pt.lower().startswith(label.lower() + ' ')):
            return p
        if hint and len(hint) >= 12 and hint.lower() in pt.lower():
            return p
    return None


def find_library_paper(user, node: GraphNode, hit: dict | None = None) -> Paper | None:
    papers = list(Paper.objects.filter(user=user, deleted_at__isnull=True))
    return match_library_paper(papers, node, hit)


def lookup_arxiv_for_node(node: GraphNode) -> dict | None:
    """Best arXiv hit for a paper / related graph node."""
    from services.arxiv_service import query_arxiv

    queries = _node_search_queries(node)
    hint = _title_hint(node)
    label = (node.label or '').strip()
    best = None
    best_score = -1
    seen = set()
    for q in queries:
        key = q.lower()
        if key in seen:
            continue
        seen.add(key)
        try:
            data = query_arxiv(query=q, start=0, max_results=5, sort_by='relevance')
        except Exception:
            continue
        for item in data.get('results') or []:
            score = _score_arxiv_hit(item, label, hint)
            if score > best_score:
                best_score = score
                best = item
        if best_score >= 80:
            break
    return best if best_score >= 18 else None


def _title_hint(node: GraphNode) -> str:
    desc = re.sub(r'\s+', ' ', (node.description or '').strip())
    if not desc or desc.startswith('概念'):
        return ''
    first = desc.split('.')[0].strip()
    return first if len(first) >= 12 else ''


def _node_search_queries(node: GraphNode) -> list[str]:
    queries: list[str] = []
    hint = _title_hint(node)
    label = re.sub(r'\s+', ' ', (node.label or '').strip())
    if hint:
        queries.append(f'ti:"{hint}"')
        queries.append(hint)
    ascii_name = re.sub(r'（.*?）|\([^)]*\)', '', label).strip()
    if re.match(r'^[A-Za-z][A-Za-z0-9+\- ]{1,48}$', ascii_name):
        queries.append(f'ti:"{ascii_name}"' if ' ' in ascii_name else f'ti:{ascii_name}')
        queries.append(ascii_name)
    if label:
        queries.append(label)
    return queries


def _score_arxiv_hit(item: dict, label: str, hint: str) -> int:
    title = (item.get('title') or '')
    blob = f'{title} {item.get("abstract") or ""}'.lower()
    score = 0
    nl = (label or '').lower()
    ascii_name = re.sub(r'（.*?）|\([^)]*\)', '', label or '').strip().lower()
    if ascii_name and len(ascii_name) >= 2 and ascii_name in blob:
        score += 35
    if nl and nl in blob:
        score += 15
    if hint:
        h = hint.lower()
        nt = title.lower()
        if h in nt or nt in h:
            score += 55
        ht = set(re.findall(r'[a-z0-9]{3,}', h))
        tt = set(re.findall(r'[a-z0-9]{3,}', nt))
        if ht and tt:
            score += int(40 * len(ht & tt) / max(len(ht), 1))
    return score

