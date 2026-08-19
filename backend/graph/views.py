from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.views import APIView
from django.db.models import Q
from common.response import ok, fail
from papers.models import Category, ImportRecord, Paper
from papers.serializers import PaperDetailSerializer
from .models import GraphNode, GraphEdge


def _node_has_local_pdf(node) -> bool:
    from services.pdf_import import resolve_paper_pdf_path
    paper = getattr(node, 'paper', None)
    if not paper:
        return False
    return resolve_paper_pdf_path(paper) is not None


def _paper_has_local_pdf(paper) -> bool:
    from services.pdf_import import resolve_paper_pdf_path
    return bool(paper) and resolve_paper_pdf_path(paper) is not None


class GraphNodeSerializer(serializers.ModelSerializer):
    short_label = serializers.SerializerMethodField()
    in_library = serializers.SerializerMethodField()
    has_pdf = serializers.SerializerMethodField()

    class Meta:
        model = GraphNode
        fields = (
            'id', 'node_type', 'label', 'short_label', 'year', 'cites', 'tags',
            'paper', 'description', 'read_status', 'in_library', 'has_pdf', 'created_at',
        )

    def get_short_label(self, obj):
        from graph.services import short_label
        return short_label(obj.label)

    def get_in_library(self, obj):
        return bool(obj.paper_id)

    def get_has_pdf(self, obj):
        return _node_has_local_pdf(obj)


class GraphEdgeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GraphEdge
        fields = ('id', 'source_node', 'target_node', 'relation_type', 'created_at')


class GraphDataView(APIView):
    def get(self, request):
        from graph.services import bind_existing_library_papers
        bind_existing_library_papers(request.user)
        nodes = GraphNode.objects.filter(user=request.user).select_related('paper').prefetch_related('paper__files')
        edges = GraphEdge.objects.filter(user=request.user)
        papers = [
            n for n in nodes
            if n.node_type == 'paper' and _node_has_local_pdf(n)
        ]
        return ok({
            'nodes': GraphNodeSerializer(nodes, many=True).data,
            'edges': GraphEdgeSerializer(edges, many=True).data,
            'center_papers': GraphNodeSerializer(papers, many=True).data,
        })


class GraphSearchView(APIView):
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        if not q:
            return fail('请输入知识点')
        concepts = GraphNode.objects.filter(
            user=request.user, node_type='concept',
        ).filter(Q(label__icontains=q) | Q(tags__icontains=q) | Q(description__icontains=q))
        concept_ids = list(concepts.values_list('id', flat=True))
        # related papers via edges
        edge_qs = GraphEdge.objects.filter(user=request.user).filter(
            Q(source_node_id__in=concept_ids) | Q(target_node_id__in=concept_ids)
        )
        paper_node_ids = set()
        for e in edge_qs:
            paper_node_ids.add(e.source_node_id)
            paper_node_ids.add(e.target_node_id)
        papers = GraphNode.objects.filter(
            user=request.user, id__in=paper_node_ids, node_type__in=['paper', 'related'],
        )
        # also match paper labels/tags
        papers = papers | GraphNode.objects.filter(
            user=request.user, node_type__in=['paper', 'related'],
        ).filter(Q(label__icontains=q) | Q(tags__icontains=q))
        return ok({
            'concepts': GraphNodeSerializer(concepts, many=True).data,
            'papers': GraphNodeSerializer(papers.distinct(), many=True).data,
        })


class GraphRecommendView(APIView):
    """Paginated arXiv papers related to a selected graph node or keyword."""
    def get(self, request):
        from graph.services import recommend_arxiv_for_node
        from services.recommend import annotate_owned, page_params, user_owned_map
        node_id = request.query_params.get('node_id')
        q = (request.query_params.get('q') or '').strip()
        node = None
        if node_id not in (None, ''):
            try:
                nid = int(node_id)
            except (TypeError, ValueError):
                return fail('节点无效')
            node = GraphNode.objects.filter(user=request.user, id=nid).first()
            if not node:
                return fail('未找到该节点')
        if not node and not q:
            return fail('请选择图谱节点或输入知识点')
        page, page_size, _ = page_params(request, default_size=5)
        try:
            payload = recommend_arxiv_for_node(node, q, page, page_size)
        except Exception as e:
            from services.arxiv_service import ArxivBusy
            if isinstance(e, ArxivBusy):
                return fail(str(e))
            return fail('arXiv 推荐暂时不可用，请稍后再试')
        payload['results'] = annotate_owned(payload.get('results') or [], user_owned_map(request.user))
        return ok(payload)


class GraphNodeViewSet(viewsets.ModelViewSet):
    serializer_class = GraphNodeSerializer

    def get_queryset(self):
        return GraphNode.objects.filter(user=self.request.user).select_related('paper').prefetch_related('paper__files')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['get'])
    def lookup(self, request, pk=None):
        """Resolve a graph node against the library, then arXiv."""
        from graph.services import bind_node_to_paper, find_library_paper, lookup_arxiv_for_node
        from services.recommend import annotate_owned, user_owned_map

        node = self.get_object()
        if node.node_type == 'concept':
            return fail('概念节点请从右侧推荐中选择论文导入')
        if node.paper_id and _paper_has_local_pdf(node.paper):
            return ok({
                'in_library': True,
                'has_pdf': True,
                'paper_id': node.paper_id,
                'hit': None,
            })
        lib = find_library_paper(request.user, node)
        if lib and _paper_has_local_pdf(lib):
            bind_node_to_paper(node, lib)
            return ok({'in_library': True, 'has_pdf': True, 'paper_id': lib.id, 'hit': None})
        hit = lookup_arxiv_for_node(node)
        if not hit:
            return fail('未在 arXiv 找到对应论文')
        hit = annotate_owned([hit], user_owned_map(request.user))[0]
        if hit.get('in_library') and hit.get('paper_id'):
            paper = Paper.objects.filter(
                user=request.user, id=hit['paper_id'], deleted_at__isnull=True,
            ).first()
            if paper and _paper_has_local_pdf(paper):
                bind_node_to_paper(node, paper)
                return ok({'in_library': True, 'has_pdf': True, 'paper_id': paper.id, 'hit': hit})
        return ok({
            'in_library': bool(node.paper_id or (lib and lib.id)),
            'has_pdf': False,
            'paper_id': node.paper_id or (lib.id if lib else hit.get('paper_id')),
            'hit': hit,
        })

    @action(detail=True, methods=['post'])
    def import_paper(self, request, pk=None):
        """Attach an existing paper, or fetch from arXiv and parse in the background."""
        from graph.services import bind_node_to_paper, find_library_paper, lookup_arxiv_for_node
        from services.arxiv_service import fetch_arxiv

        node = self.get_object()
        if node.node_type == 'concept':
            return fail('概念节点请从右侧推荐中选择论文导入')

        paper_id = request.data.get('paper_id')
        if paper_id:
            paper = Paper.objects.filter(
                user=request.user, id=paper_id, deleted_at__isnull=True,
            ).first()
            if not paper:
                return fail('论文不存在')
            bind_node_to_paper(node, paper)
            if _paper_has_local_pdf(paper):
                data = PaperDetailSerializer(paper).data
                data['already'] = True
                data['queued'] = False
                data['has_local_pdf'] = True
                return ok(data)

        if node.paper_id and _paper_has_local_pdf(node.paper):
            paper = node.paper
            data = PaperDetailSerializer(paper).data
            data['already'] = True
            data['queued'] = False
            data['has_local_pdf'] = True
            return ok(data)

        arxiv_id = (request.data.get('arxiv_id') or '').strip()
        pdf_url = (request.data.get('pdf_url') or '').strip()
        hit = None
        if arxiv_id:
            items = fetch_arxiv(id_list=[arxiv_id])
            hit = items[0] if items else None
        if not hit:
            hit = lookup_arxiv_for_node(node)
        if not hit:
            return fail('未在 arXiv 找到对应论文')

        lib = find_library_paper(request.user, node, hit)
        parse_mode = request.data.get('parse_mode', 'ocr')
        background = str(request.data.get('background', '1')).lower() not in ('0', 'false', 'no')
        src = pdf_url or hit.get('pdf_url') or (
            f"https://arxiv.org/pdf/{hit['arxiv_id']}.pdf" if hit.get('arxiv_id') else ''
        )

        if lib:
            bind_node_to_paper(node, lib)
            running = ImportRecord.objects.filter(
                user=request.user, paper=lib, status__in=['pending', 'running'],
            ).order_by('-id').first()
            if running:
                data = PaperDetailSerializer(lib).data
                data['queued'] = True
                data['job_id'] = running.id
                data['has_local_pdf'] = False
                return ok(data, message='正在下载解析')
            if src and not _paper_has_local_pdf(lib):
                if not lib.pdf_url:
                    lib.pdf_url = src
                    if not lib.cover_url:
                        lib.cover_url = src
                    lib.save(update_fields=['pdf_url', 'cover_url', 'updated_at'])
                data = self._enqueue_pdf(request.user, lib, src, parse_mode, background)
                data['has_local_pdf'] = False
                if data.get('error'):
                    return fail(data['error'], code=402, status=403)
                return ok(data, message='已存在，正在补下 PDF')
            data = PaperDetailSerializer(lib).data
            data['already'] = True
            data['queued'] = False
            data['has_local_pdf'] = _paper_has_local_pdf(lib)
            return ok(data, message='已存在')

        category_id = request.data.get('category')
        cat = Category.objects.filter(user=request.user, id=category_id).first() if category_id else None
        tags = (request.data.get('tags') or '').strip() or node.tags or None
        intro = (request.data.get('intro') or '').strip() or None
        paper = Paper.objects.create(
            user=request.user,
            category=cat,
            title=hit.get('title') or node.label,
            authors=(hit.get('authors') or '')[:500] or None,
            year=hit.get('year') or node.year,
            doi=hit.get('doi') or None,
            arxiv_id=hit.get('arxiv_id') or None,
            abstract=hit.get('abstract'),
            intro=intro or (hit.get('abstract') or node.description or '')[:200] or None,
            tags=tags,
            source_type='graph',
            venue=hit.get('venue') or 'arXiv',
            cover_url=src or None,
            pdf_url=src or None,
            cites=int(hit.get('cites') or node.cites or 0) or 0,
            status=request.data.get('status') or '想读',
        )
        bind_node_to_paper(node, paper)
        if not src:
            data = PaperDetailSerializer(paper).data
            data['queued'] = False
            return ok(data, message='已加入文献库，但未找到 PDF', status=201)
        data = self._enqueue_pdf(request.user, paper, src, parse_mode, background)
        if data.get('error'):
            return fail(data['error'], code=402, status=403)
        return ok(data, message='已加入后台导入' if background else '导入成功', status=201)

    def _enqueue_pdf(self, user, paper, pdf_url, parse_mode, background):
        from papers.jobs import enqueue_arxiv_parse
        from services.pdf_import import attach_and_parse_pdf
        from accounts.quota import QuotaExceeded, assert_can_parse

        try:
            assert_can_parse(user, paper.id)
        except QuotaExceeded as e:
            data = PaperDetailSerializer(paper).data
            data['queued'] = False
            data['error'] = str(e)
            return data
        if background:
            rec = ImportRecord.objects.create(
                user=user, paper=paper,
                file_name=paper.arxiv_id or paper.title,
                import_type='arxiv', status='pending',
            )
            enqueue_arxiv_parse(paper.id, pdf_url, parse_mode, rec.id)
            data = PaperDetailSerializer(paper).data
            data['queued'] = True
            data['job_id'] = rec.id
            return data
        attach_and_parse_pdf(paper, pdf_url=pdf_url, parse_mode=parse_mode)
        paper.refresh_from_db()
        data = PaperDetailSerializer(paper).data
        data['queued'] = False
        return data


class GraphEdgeViewSet(viewsets.ModelViewSet):
    serializer_class = GraphEdgeSerializer

    def get_queryset(self):
        return GraphEdge.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class SyncFromLibraryView(APIView):
    """Create graph nodes from user's papers + tags as concepts."""
    def post(self, request):
        from graph.services import sync_library_graph
        data = sync_library_graph(request.user)
        return ok(data, message='图谱已同步')
