import os
import uuid
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from common.response import ok, fail
from .models import Category, Paper, PaperFile, UserSource, ImportRecord, PaperShare
from .serializers import (
    CategorySerializer, PaperListSerializer, PaperDetailSerializer,
    PaperWriteSerializer, UserSourceSerializer, PaperShareSerializer,
)
from accounts.models import Friendship
from accounts.quota import QuotaExceeded, quota_fail


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(user=self.request.user).select_related('parent')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, is_system=False)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.children.exists():
            return fail('请先删除子文件夹')
        return super().destroy(request, *args, **kwargs)


class PaperViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['status', 'starred', 'category', 'year']
    search_fields = ['title', 'title_zh', 'authors', 'tags', 'abstract', 'intro']
    ordering_fields = ['year', 'read_progress', 'cites', 'last_read_at', 'created_at']
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        qs = Paper.objects.filter(user=self.request.user)
        trash = self.request.query_params.get('trash')
        if trash in ('1', 'true'):
            return qs.filter(deleted_at__isnull=False)
        return qs.filter(deleted_at__isnull=True)

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return PaperDetailSerializer
        if self.action in ('create', 'update', 'partial_update'):
            return PaperWriteSerializer
        return PaperListSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        paper = self.get_object()
        paper.deleted_at = timezone.now()
        paper.save(update_fields=['deleted_at'])
        return ok(message='已移入回收站')

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        paper = Paper.objects.filter(user=request.user, pk=pk).first()
        if not paper or not paper.deleted_at:
            return fail('论文不在回收站')
        paper.deleted_at = None
        paper.save(update_fields=['deleted_at'])
        return ok(PaperDetailSerializer(paper).data, message='已恢复')

    @action(detail=True, methods=['delete'])
    def purge(self, request, pk=None):
        paper = Paper.objects.filter(user=request.user, pk=pk).first()
        if not paper:
            return fail('不存在')
        # cleanup files
        if paper.file_path:
            full = os.path.join(settings.MEDIA_ROOT, paper.file_path) if not os.path.isabs(paper.file_path) else paper.file_path
            if os.path.exists(full):
                try:
                    os.remove(full)
                except OSError:
                    pass
        paper.delete()
        return ok(message='已彻底删除')

    @action(detail=False, methods=['post'], url_path='import-file')
    def import_file(self, request):
        files = request.FILES.getlist('files') or ([request.FILES['file']] if 'file' in request.FILES else [])
        if not files:
            return fail('请上传文件')
        category_id = request.data.get('category')
        status_val = request.data.get('status', '想读')
        tags = request.data.get('tags', '')
        intro = request.data.get('intro', '')
        parse_mode = request.data.get('parse_mode', 'ocr')  # ocr | mineru | layout
        background = str(request.data.get('background', '1')).lower() not in ('0', 'false', 'no')
        results = []
        for f in files:
            results.append(self._save_upload(
                request.user, f, category_id, status_val, tags, intro, parse_mode,
                background=background,
            ))
        queued = any(r.get('queued') for r in results)
        err = next((r.get('error') for r in results if r.get('error')), None)
        if err and not queued:
            return fail(err, code=402, status=403)
        return ok(
            {'results': results, 'queued': queued},
            message='已加入后台导入' if queued else f'已导入 {len(results)} 篇',
            status=201 if queued else 200,
        )

    def _save_upload(self, user, f, category_id, status_val, tags, intro, parse_mode, background=True):
        from papers.jobs import enqueue_file_parse, _apply_parsed, _notify_import
        from services.paper_parser import parse_paper_file
        ext = (f.name.rsplit('.', 1)[-1] if '.' in f.name else 'pdf').lower()
        rel_dir = f'papers/{user.id}'
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        fname = f'{uuid.uuid4().hex}.{ext}'
        rel_path = f'{rel_dir}/{fname}'
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        with open(abs_path, 'wb') as out:
            for chunk in f.chunks():
                out.write(chunk)

        cat = None
        if category_id:
            cat = Category.objects.filter(user=user, id=category_id).first()

        title = f.name.rsplit('.', 1)[0]
        paper = Paper.objects.create(
            user=user, category=cat, title=title, intro=intro or None,
            tags=tags or None, status=status_val, source_type='file',
            file_type=ext, file_path=rel_path, file_size=f.size,
        )
        PaperFile.objects.create(
            paper=paper, file_type=ext, file_name=f.name,
            file_path=rel_path, file_size=f.size,
        )
        rec = ImportRecord.objects.create(
            user=user, paper=paper, file_name=f.name, file_path=rel_path,
            import_type='file', status='pending',
        )
        from accounts.quota import QuotaExceeded, assert_can_parse, paper_page_count, prepare_parse
        try:
            pages = paper_page_count(paper, abs_path)
            assert_can_parse(user, paper.id, pages)
        except QuotaExceeded as e:
            rec.status = 'failed'
            rec.error_msg = str(e)[:500]
            rec.save(update_fields=['status', 'error_msg'])
            data = PaperDetailSerializer(paper).data
            data['queued'] = False
            data['error'] = str(e)
            return data
        if background:
            enqueue_file_parse(paper.id, abs_path, parse_mode, rec.id, user.id)
            data = PaperDetailSerializer(paper).data
            data['queued'] = True
            data['job_id'] = rec.id
            return data
        try:
            prepare_parse(user, paper, abs_path)
            parsed = parse_paper_file(abs_path, mode=parse_mode, user_id=user.id)
            _apply_parsed(paper, parsed)
            rec.status = 'success'
            rec.save(update_fields=['status'])
            paper.refresh_from_db()
            _notify_import(rec, paper, True)
        except Exception as e:
            rec.status = 'failed'
            rec.error_msg = str(e)[:500]
            rec.save(update_fields=['status', 'error_msg'])
            _notify_import(rec, paper, False)
        data = PaperDetailSerializer(paper).data
        data['queued'] = False
        data['job_id'] = rec.id
        return data

    @action(detail=False, methods=['post'], url_path='import-arxiv')
    def import_arxiv(self, request):
        """Import from arXiv metadata + download PDF + parse text for reader."""
        from services.arxiv_service import fetch_arxiv

        arxiv_id = request.data.get('arxiv_id', '').strip()
        query = request.data.get('query', '').strip()
        pdf_url = request.data.get('pdf_url', '').strip()
        parse_mode = request.data.get('parse_mode', 'ocr')
        download_pdf = str(request.data.get('download_pdf', '1')).lower() not in ('0', 'false', 'no')

        category_id = request.data.get('category')
        cat = None
        if category_id:
            cat = Category.objects.filter(user=request.user, id=category_id).first()
        tags = (request.data.get('tags') or '').strip() or None
        intro = (request.data.get('intro') or '').strip() or None

        background = str(request.data.get('background', '1')).lower() not in ('0', 'false', 'no')

        if arxiv_id:
            items = fetch_arxiv(id_list=[arxiv_id])
        elif query:
            items = fetch_arxiv(query=query, max_results=1)
        else:
            return fail('请提供 arxiv_id 或 query')
        if not items:
            return fail('未找到论文')
        item = items[0]
        src = pdf_url or item.get('pdf_url')
        existing = Paper.objects.filter(
            user=request.user, deleted_at__isnull=True, arxiv_id=item['arxiv_id'],
        ).first()
        if existing:
            if src and existing.pdf_url != src:
                existing.pdf_url = src
                if not existing.cover_url:
                    existing.cover_url = src
                existing.save(update_fields=['pdf_url', 'cover_url', 'updated_at'])
            if download_pdf and (not existing.content_json or not existing.file_path):
                data = self._start_arxiv_pdf(
                    request.user, existing, src, parse_mode, background,
                )
                return self._parse_result(data, '已存在，正在补下 PDF')
            data = PaperDetailSerializer(existing).data
            data['already'] = True
            data['queued'] = False
            return ok(data, message='已存在')

        paper = Paper.objects.create(
            user=request.user,
            category=cat,
            title=item['title'],
            authors=item['authors'],
            year=item.get('year'),
            doi=item.get('doi'),
            arxiv_id=item['arxiv_id'],
            abstract=item.get('abstract'),
            intro=intro or (item.get('abstract') or '')[:200] or None,
            tags=tags,
            source_type='arxiv',
            venue='arXiv',
            cover_url=item.get('pdf_url'),
            pdf_url=src,
            status=request.data.get('status') or '想读',
        )
        if paper.abstract and not download_pdf:
            paper.content_json = [{
                'en': paper.abstract, 'zh': '', 'section': 'Abstract', 'section_id': 's1',
            }]
            paper.outline = [{'id': 's1', 'title': 'Abstract', 'para_index': 0}]
            paper.save(update_fields=['content_json', 'outline'])
        if download_pdf:
            data = self._start_arxiv_pdf(
                request.user, paper, src, parse_mode, background,
            )
            return self._parse_result(data, '已加入后台导入' if background else '导入成功', status=201)
        data = PaperDetailSerializer(paper).data
        data['queued'] = False
        return ok(data, message='导入成功', status=201)

    def _parse_result(self, data, message, status=200):
        if data.get('error'):
            return fail(data['error'], code=402, status=403)
        return ok(data, message=message, status=status)

    def _start_arxiv_pdf(self, user, paper, pdf_url, parse_mode, background):
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
        try:
            attach_and_parse_pdf(paper, pdf_url=pdf_url, parse_mode=parse_mode)
        except Exception as e:
            paper.refresh_from_db()
            if paper.abstract and not paper.content_json:
                paper.content_json = [{
                    'en': paper.abstract, 'zh': '', 'section': 'Abstract', 'section_id': 's1',
                }]
                paper.outline = [{'id': 's1', 'title': 'Abstract', 'para_index': 0}]
                paper.save(update_fields=['content_json', 'outline'])
            paper.refresh_from_db()
            data = PaperDetailSerializer(paper).data
            data['queued'] = False
            data['error'] = str(e)[:200]
            return data
        paper.refresh_from_db()
        data = PaperDetailSerializer(paper).data
        data['queued'] = False
        return data

    @action(detail=False, methods=['get'], url_path='import-jobs')
    def import_jobs(self, request):
        jid = request.query_params.get('id')
        rec = ImportRecord.objects.filter(user=request.user, id=jid).first()
        if not rec:
            return fail('任务不存在')
        return ok({
            'id': rec.id,
            'status': rec.status,
            'error_msg': rec.error_msg,
            'paper_id': rec.paper_id,
        })

    @action(detail=False, methods=['post'], url_path='import-hit')
    def import_hit(self, request):
        """Import a search hit from any saved source (arXiv / S2 / OpenReview / …)."""
        arxiv_id = (request.data.get('arxiv_id') or '').strip()
        if arxiv_id:
            return self.import_arxiv(request)
        title = (request.data.get('title') or '').strip()
        if not title:
            return fail('缺少论文标题')
        doi = (request.data.get('doi') or '').strip()
        pdf_url = (request.data.get('pdf_url') or '').strip()
        pdf_l = pdf_url.lower()
        looks_pdf = pdf_l.endswith('.pdf') or '/pdf' in pdf_l or 'arxiv.org/pdf' in pdf_l
        if doi and not looks_pdf:
            from services.source_search import resolve_oa_pdf
            pdf_url = resolve_oa_pdf(doi, pdf_url)
        existing = None
        if doi:
            existing = Paper.objects.filter(
                user=request.user, deleted_at__isnull=True, doi=doi,
            ).first()
        if not existing:
            title_key = title[:500]
            existing = Paper.objects.filter(
                user=request.user, deleted_at__isnull=True, title=title_key,
            ).first()
        if existing:
            if pdf_url and (not existing.content_json or not existing.file_path):
                if not existing.pdf_url:
                    existing.pdf_url = pdf_url
                    if not existing.cover_url:
                        existing.cover_url = pdf_url
                    existing.save(update_fields=['pdf_url', 'cover_url', 'updated_at'])
                data = self._start_arxiv_pdf(
                    request.user, existing, pdf_url, request.data.get('parse_mode', 'ocr'),
                    str(request.data.get('background', '1')).lower() not in ('0', 'false', 'no'),
                )
                return self._parse_result(data, '已存在，正在补下 PDF')
            data = PaperDetailSerializer(existing).data
            data['already'] = True
            data['queued'] = False
            return ok(data, message='已存在')

        category_id = request.data.get('category')
        cat = Category.objects.filter(user=request.user, id=category_id).first() if category_id else None
        tags = (request.data.get('tags') or '').strip() or None
        intro = (request.data.get('intro') or '').strip() or None
        abstract = (request.data.get('abstract') or '').strip() or None
        parse_mode = request.data.get('parse_mode', 'ocr')
        background = str(request.data.get('background', '1')).lower() not in ('0', 'false', 'no')
        year = request.data.get('year')
        try:
            year = int(year) if year else None
        except (TypeError, ValueError):
            year = None
        paper = Paper.objects.create(
            user=request.user,
            category=cat,
            title=title[:500],
            authors=(request.data.get('authors') or '')[:500] or None,
            year=year,
            doi=doi or None,
            abstract=abstract,
            intro=intro or (abstract or '')[:200] or None,
            tags=tags,
            source_type='site',
            venue=(request.data.get('venue') or '')[:200] or None,
            cover_url=pdf_url or None,
            pdf_url=pdf_url or None,
            cites=int(request.data.get('cites') or 0) or 0,
            status=request.data.get('status') or '想读',
        )
        if abstract and not pdf_url:
            paper.content_json = [{'en': abstract, 'zh': '', 'section': 'Abstract', 'section_id': 's1'}]
            paper.outline = [{'id': 's1', 'title': 'Abstract', 'para_index': 0}]
            paper.save(update_fields=['content_json', 'outline'])
        if pdf_url:
            data = self._start_arxiv_pdf(request.user, paper, pdf_url, parse_mode, background)
            return self._parse_result(data, '已加入后台导入' if background else '导入成功', status=201)
        data = PaperDetailSerializer(paper).data
        data['queued'] = False
        return ok(data, message='导入成功', status=201)

    @action(detail=True, methods=['post'], url_path='fetch-pdf')
    def fetch_pdf(self, request, pk=None):
        """Re-download & parse PDF for an existing paper (arxiv/doi)."""
        from services.pdf_import import attach_and_parse_pdf, resolve_pdf_source_url
        paper = self.get_object()
        pdf_url = resolve_pdf_source_url(paper, request.data.get('pdf_url'))
        if not pdf_url:
            return fail('无 PDF 下载地址，请先填写 pdf_url')
        try:
            # remember URL even if download later fails
            if paper.pdf_url != pdf_url:
                paper.pdf_url = pdf_url
                if not paper.cover_url:
                    paper.cover_url = pdf_url
                paper.save(update_fields=['pdf_url', 'cover_url', 'updated_at'])
            attach_and_parse_pdf(paper, pdf_url=pdf_url, parse_mode=request.data.get('parse_mode', 'ocr'))
            return ok(PaperDetailSerializer(paper).data, message='PDF 已下载并解析')
        except Exception as e:
            return fail(f'下载失败: {e}')

    @action(detail=True, methods=['get'], url_path='file')
    def download_file(self, request, pk=None):
        """Authenticated PDF stream; auto re-download if local file is missing."""
        import mimetypes
        from django.http import FileResponse, Http404
        from services.pdf_import import ensure_local_pdf
        paper = self.get_object()
        try:
            abs_path = ensure_local_pdf(paper, parse_if_empty=False)
        except Exception as e:
            raise Http404(str(e)) from e
        content_type = mimetypes.guess_type(abs_path)[0] or 'application/pdf'
        resp = FileResponse(open(abs_path, 'rb'), content_type=content_type)
        fname = os.path.basename(abs_path)
        resp['Content-Disposition'] = f'inline; filename="{fname}"'
        resp['Accept-Ranges'] = 'bytes'
        return resp

    @action(detail=True, methods=['get'], url_path='page-image')
    def page_image(self, request, pk=None):
        """Render one PDF page to PNG (original layout). Used by the reader."""
        from django.http import HttpResponse, Http404
        from services.pdf_import import ensure_local_pdf
        paper = self.get_object()
        try:
            page_no = max(1, int(request.query_params.get('page') or 1))
        except (TypeError, ValueError):
            page_no = 1
        try:
            zoom = float(request.query_params.get('scale') or 2.5)
        except (TypeError, ValueError):
            zoom = 2.5
        zoom = min(max(zoom, 0.8), 4.5)
        try:
            abs_path = ensure_local_pdf(paper, parse_if_empty=False)
        except Exception as e:
            raise Http404(str(e)) from e
        try:
            import fitz
            doc = fitz.open(abs_path)
            if page_no > doc.page_count:
                page_no = doc.page_count
            pg = doc[page_no - 1]
            pix = pg.get_pixmap(matrix=fitz.Matrix(zoom, zoom), alpha=False)
            data = pix.tobytes('png')
            doc.close()
        except Exception as e:
            raise Http404(f'页面渲染失败: {e}') from e
        resp = HttpResponse(data, content_type='image/png')
        resp['Cache-Control'] = 'private, max-age=120'
        return resp

    @action(detail=True, methods=['post'], url_path='reparse')
    def reparse(self, request, pk=None):
        """Re-run layout parse on local PDF; re-download first if file is missing."""
        from services.pdf_import import attach_and_parse_pdf, ensure_local_pdf
        paper = self.get_object()
        try:
            abs_path = ensure_local_pdf(paper, parse_if_empty=False)
        except Exception as e:
            return fail(str(e))
        try:
            attach_and_parse_pdf(
                paper, abs_path=abs_path,
                parse_mode=request.data.get('parse_mode', 'ocr'),
            )
            mode = (request.data.get('parse_mode') or 'ocr').lower()
            msg = {
                'mineru': '已用 MinerU 还原版面',
                'layout': '已用 PDF 内嵌文本解析',
            }.get(mode, '已用 PaddleOCR 还原版面')
            return ok(PaperDetailSerializer(paper).data, message=msg)
        except Exception as e:
            return fail(str(e))

    @action(detail=False, methods=['get'])
    def discover(self, request):
        from services.recommend import hot_papers
        page = int(request.query_params.get('page', 1) or 1)
        page_size = int(request.query_params.get('page_size', 10) or 10)
        try:
            return ok(hot_papers(request.user, page=page, page_size=page_size))
        except Exception as e:
            qs = self.get_queryset().order_by('-cites', '-year')[:50]
            return ok(PaperListSerializer(qs, many=True).data, message=str(e))

    @action(detail=True, methods=['post'])
    def share(self, request, pk=None):
        paper = self.get_object()
        target_type = request.data.get('target_type', 'user')
        message = request.data.get('message', '')
        if target_type == 'user':
            tid = request.data.get('target_user_id')
            from accounts.models import User
            target = User.objects.filter(id=tid).first()
            if not target:
                return fail('目标用户不存在')
            share = PaperShare.objects.create(
                user=request.user, paper=paper, target_type='user',
                target_user=target, message=message,
            )
            Friendship.objects.get_or_create(user=request.user, friend=target)
            Friendship.objects.get_or_create(user=target, friend=request.user)
        else:
            from accounts.quota import QuotaExceeded, consume_team_share, quota_fail
            try:
                consume_team_share(request.user)
            except QuotaExceeded as e:
                return quota_fail(e)
            team_id = request.data.get('target_team_id')
            share = PaperShare.objects.create(
                user=request.user, paper=paper, target_type='team',
                target_team_id=team_id, message=message,
            )
        return ok(PaperShareSerializer(share).data, message='分享成功')


class UserSourceViewSet(viewsets.ModelViewSet):
    serializer_class = UserSourceSerializer
    pagination_class = None

    def get_queryset(self):
        return UserSource.objects.filter(user=self.request.user, enabled=True)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, source_type='custom', is_default=False)

    def destroy(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.is_default:
            return fail('预置来源不可删除')
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def search(self, request):
        from services.source_search import annotate_search, search_source
        from services.recommend import page_params
        q = (request.query_params.get('q') or '').strip()
        if not q:
            return fail('请输入关键词')
        page, page_size, _ = page_params(request, default_size=10)
        sort = (request.query_params.get('sort') or 'relevance').strip()
        sid = request.query_params.get('source_id') or request.query_params.get('source')
        src = None
        qs = self.get_queryset()
        sid_int = None
        if sid not in (None, ''):
            try:
                sid_int = int(sid)
            except (TypeError, ValueError):
                return fail('收藏网站无效')
            src = qs.filter(id=sid_int).first()
            if not src:
                return fail('未找到该收藏网站')
        else:
            src = (
                qs.filter(name__icontains='arxiv').first()
                or qs.filter(url__icontains='arxiv.org').first()
                or qs.first()
            )
        if not src:
            return fail('没有可用的收藏网站')
        try:
            payload = search_source(src, q, page=page, page_size=page_size, sort=sort)
            payload = annotate_search(request.user, payload)
            payload['source_id'] = src.id
            payload['source_name'] = src.name
            return ok(payload)
        except Exception as e:
            from services.arxiv_service import ArxivBusy
            if isinstance(e, ArxivBusy):
                return fail(str(e))
            msg = str(e).split('\n')[0][:180]
            if '429' in msg:
                return fail('检索过于频繁，请稍后再试')
            return fail(f'{src.name} 检索失败: {msg}')


class ArxivSearchView(APIView):
    def get(self, request):
        from services.arxiv_service import query_arxiv
        from services.recommend import annotate_owned, page_params, paged, user_owned_map
        q = request.query_params.get('q', '').strip()
        if not q:
            return fail('请输入关键词')
        page, page_size, start = page_params(request, default_size=10)
        if request.query_params.get('start') is not None and request.query_params.get('page') is None:
            try:
                start = max(int(request.query_params.get('start', 0) or 0), 0)
            except (TypeError, ValueError):
                start = 0
            try:
                page_size = min(int(request.query_params.get('max_results', page_size) or page_size), 50)
            except (TypeError, ValueError):
                pass
            page = start // page_size + 1 if page_size else 1
        elif request.query_params.get('max_results') and request.query_params.get('page') is None:
            try:
                page_size = min(int(request.query_params.get('max_results', 10)), 50)
            except (TypeError, ValueError):
                page_size = 10
        try:
            data = query_arxiv(query=q, start=start, max_results=page_size, sort_by='relevance')
            owned = user_owned_map(request.user)
            results = annotate_owned(data['results'], owned)
            payload = paged(results, data['total'], page, page_size)
            payload['results'] = results
            return ok(payload)
        except Exception as e:
            from services.arxiv_service import ArxivBusy
            if isinstance(e, ArxivBusy):
                return fail(str(e))
            return fail('arXiv 检索失败，请稍后再试')


class DiscoverRecommendView(APIView):
    def get(self, request):
        from services.recommend import list_filters, page_params, recommend_from_arxiv
        page, page_size, _ = page_params(request, default_size=5)
        flt = list_filters(request)
        try:
            return ok(recommend_from_arxiv(
                request.user, page=page, page_size=page_size, **flt,
            ))
        except Exception as e:
            return fail(f'推荐失败: {e}')


class DiscoverHotView(APIView):
    def get(self, request):
        from services.recommend import hot_papers, list_filters, page_params
        page, page_size, _ = page_params(request, default_size=5)
        flt = list_filters(request)
        if not request.query_params.get('sort'):
            flt['sort'] = 'cites'
        try:
            return ok(hot_papers(
                request.user, page=page, page_size=page_size, **flt,
            ))
        except Exception as e:
            return fail(f'热门论文加载失败: {e}')


class ShareManageView(APIView):
    def get(self, request):
        direction = request.query_params.get('direction', 'inbox')
        if direction == 'outbox':
            qs = PaperShare.objects.filter(user=request.user, status='active')
        else:
            from teams.models import TeamMember
            team_ids = list(TeamMember.objects.filter(user=request.user).values_list('team_id', flat=True))
            qs = PaperShare.objects.filter(status='active').filter(
                Q(target_user=request.user) | Q(target_team_id__in=team_ids)
            ).exclude(user=request.user)
        return ok(PaperShareSerializer(qs[:50], many=True).data)

    def post(self, request):
        share_id = request.data.get('id')
        action_name = request.data.get('action')  # accept / ignore / revoke
        share = PaperShare.objects.filter(id=share_id).first()
        if not share:
            return fail('分享不存在')
        if action_name == 'revoke' and share.user_id == request.user.id:
            share.status = 'revoked'
            share.save(update_fields=['status'])
            return ok(message='已撤销')
        if action_name == 'ignore' and share.target_user_id == request.user.id:
            share.status = 'ignored'
            share.save(update_fields=['status'])
            return ok(message='已忽略')
        if action_name == 'accept' and (
            share.target_user_id == request.user.id
            or share.target_team_id
        ):
            # copy paper into receiver library
            src = share.paper
            paper = Paper.objects.create(
                user=request.user,
                title=src.title, title_zh=src.title_zh, authors=src.authors,
                venue=src.venue, year=src.year, doi=src.doi, arxiv_id=src.arxiv_id,
                abstract=src.abstract, abstract_zh=src.abstract_zh, intro=src.intro,
                tags=src.tags, source_type='share', starred=True, status='想读',
                content_json=src.content_json, outline=src.outline, ai_summary=src.ai_summary,
            )
            share.status = 'accepted'
            share.save(update_fields=['status'])
            return ok(PaperDetailSerializer(paper).data, message='已收下')
        return fail('操作无效')


class BackupView(APIView):
    def get(self, request):
        """Export all user data as JSON."""
        from reader.models import PaperNote, PaperHighlight, ReadingRecord, OcrRecord, GlossaryTerm
        from graph.models import GraphNode, GraphEdge
        u = request.user
        data = {
            'app': 'PaperMind',
            'version': '2.0',
            'user': {
                'username': u.username, 'email': u.email, 'avatar': u.avatar,
                'research_direction': u.research_direction, 'role': u.role,
            },
            'papers': list(Paper.objects.filter(user=u).values()),
            'notes': list(PaperNote.objects.filter(user=u).values()),
            'highlights': list(PaperHighlight.objects.filter(user=u).values()),
            'terms': list(GlossaryTerm.objects.filter(user=u).values()),
            'sources': list(UserSource.objects.filter(user=u).values()),
            'graph_nodes': list(GraphNode.objects.filter(user=u).values()),
            'graph_edges': list(GraphEdge.objects.filter(user=u).values()),
            'reading': list(ReadingRecord.objects.filter(user=u).values()),
            'ocr': list(OcrRecord.objects.filter(user=u).values()),
        }
        # JSON-serialize datetimes
        import json
        from django.core.serializers.json import DjangoJSONEncoder
        return ok(json.loads(json.dumps(data, cls=DjangoJSONEncoder)))
