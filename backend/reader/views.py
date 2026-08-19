import hashlib
import os
import uuid
from django.conf import settings
from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.views import APIView
from common.response import ok, fail
from papers.models import Paper
from .models import (
    PaperHighlight, PaperNote, OcrRecord, ReadingRecord,
    GlossaryTerm, ParagraphTranslation,
)
from .serializers import (
    HighlightSerializer, NoteSerializer, OcrRecordSerializer,
    ReadingRecordSerializer, GlossarySerializer,
)


def _user_ai_config(user):
    pref = getattr(user, 'preference', None)
    if pref and pref.translate_config:
        return pref.translate_config
    return None


def _is_bad_translation(text) -> bool:
    """Detect offline / error placeholders that must not be reused from cache."""
    s = str(text or '')
    return (
        '离线占位' in s
        or '【译文占位】' in s
        or '【AI 占位回复】' in s
        or 'Authorization Required' in s
    )


def _user_ocr_config(user):
    pref = getattr(user, 'preference', None)
    if pref and pref.ocr_config:
        return pref.ocr_config
    return None


class HighlightViewSet(viewsets.ModelViewSet):
    serializer_class = HighlightSerializer

    def get_queryset(self):
        qs = PaperHighlight.objects.filter(user=self.request.user)
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            qs = qs.filter(paper_id=paper_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class NoteViewSet(viewsets.ModelViewSet):
    serializer_class = NoteSerializer

    def get_queryset(self):
        qs = PaperNote.objects.filter(user=self.request.user, deleted_at__isnull=True).select_related(
            'paper', 'highlight', 'user',
        )
        paper_id = self.request.query_params.get('paper')
        if paper_id:
            qs = qs.filter(paper_id=paper_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ReadingProgressView(APIView):
    def get(self, request):
        paper_id = request.query_params.get('paper')
        qs = ReadingRecord.objects.filter(user=request.user)
        if paper_id:
            qs = qs.filter(paper_id=paper_id)
        return ok(ReadingRecordSerializer(qs, many=True).data)

    def post(self, request):
        paper_id = request.data.get('paper')
        paper = Paper.objects.filter(user=request.user, id=paper_id, deleted_at__isnull=True).first()
        if not paper:
            return fail('论文不存在')
        progress = int(request.data.get('progress', 0))
        duration = int(request.data.get('duration_sec', 0))
        last_section = request.data.get('last_section')
        last_position = request.data.get('last_position')
        rec, _ = ReadingRecord.objects.get_or_create(user=request.user, paper=paper)
        rec.progress = max(0, min(100, progress))
        rec.duration_sec = (rec.duration_sec or 0) + max(0, duration)
        if last_section is not None:
            rec.last_section = last_section
        if last_position is not None:
            rec.last_position = last_position
        rec.read_at = timezone.now()
        rec.save()
        paper.read_progress = rec.progress
        paper.last_read_at = rec.read_at
        if paper.status == '想读' and rec.progress > 0:
            paper.status = '在读'
        if rec.progress >= 95:
            paper.status = '读完'
        paper.save(update_fields=['read_progress', 'last_read_at', 'status'])
        return ok(ReadingRecordSerializer(rec).data)


class TranslateSelectionView(APIView):
    def post(self, request):
        from services.deepseek import translate, summarize_selection
        text = request.data.get('text', '').strip()
        if not text:
            return fail('文本为空')
        cfg = _user_ai_config(request.user)
        glossary = list(
            GlossaryTerm.objects.filter(user=request.user).values_list('term_en', 'term_zh', 'description')[:30]
        )
        translation = translate(text, user_config=cfg, glossary=glossary)
        summary = summarize_selection(text, user_config=cfg)
        return ok({'translation': translation, 'summary': summary})


class TranslateParagraphsView(APIView):
    def post(self, request):
        from services.deepseek import translate
        paper_id = request.data.get('paper')
        indices = request.data.get('indices')  # list of para indices, or null = all untranslated
        only_page = request.data.get('page')  # optional: translate one page blocks
        force = str(request.data.get('force', '')).lower() in ('1', 'true', 'yes')
        paper = Paper.objects.filter(user=request.user, id=paper_id).first()
        if not paper or not paper.content_json:
            return fail('论文无正文')
        from accounts.quota import QuotaExceeded, prepare_translate, quota_fail
        try:
            prepare_translate(request.user, paper)
        except QuotaExceeded as e:
            return quota_fail(e)
        cfg = _user_ai_config(request.user)
        glossary = list(
            GlossaryTerm.objects.filter(user=request.user).values_list('term_en', 'term_zh', 'description')[:30]
        )
        paras = list(paper.content_json)
        if indices is not None:
            targets = indices
        elif only_page is not None:
            targets = [
                i for i, p in enumerate(paras)
                if p.get('page') == int(only_page) and p.get('type', 'text') in ('text', 'table')
            ]
        else:
            targets = list(range(len(paras)))
        results = []
        for i in targets:
            if i < 0 or i >= len(paras):
                continue
            block = paras[i]
            btype = block.get('type', 'text')
            # figures keep layout slot, no AI translation of image bytes
            if btype == 'figure':
                block['zh'] = block.get('zh') or block.get('en') or '[图]'
                results.append({'index': i, 'zh': block['zh'], 'skipped': 'figure'})
                continue
            en = (block.get('en') or '').strip()
            if not en or en.startswith('['):
                continue
            h = hashlib.sha256(en.encode('utf-8')).hexdigest()
            cached = None if force else ParagraphTranslation.objects.filter(
                paper=paper, para_index=i, text_hash=h,
            ).first()
            zh = None
            if cached and not _is_bad_translation(cached.translated_text):
                zh = cached.translated_text
            elif (not force) and block.get('zh') and not _is_bad_translation(block.get('zh')) and not str(block.get('zh')).startswith('（未'):
                zh = block['zh']
            else:
                zh = translate(en, user_config=cfg, glossary=glossary)
                # never persist offline / error placeholders
                if not _is_bad_translation(zh):
                    ParagraphTranslation.objects.update_or_create(
                        paper=paper, para_index=i, text_hash=h,
                        defaults={'source_text': en, 'translated_text': zh, 'engine': 'newapi'},
                    )
                elif cached:
                    cached.delete()
            paras[i]['zh'] = zh
            # keep layout correspondence metadata
            paras[i]['type'] = btype
            if block.get('page') is not None:
                paras[i]['page'] = block['page']
            if block.get('bbox'):
                paras[i]['bbox'] = block['bbox']
            results.append({'index': i, 'zh': zh, 'page': block.get('page')})
        paper.content_json = paras
        paper.save(update_fields=['content_json'])
        return ok({'results': results, 'count': len(results)})


class OcrScreenshotView(APIView):
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        from services.deepseek import translate, summarize_selection
        paper_id = request.data.get('paper')
        paper = Paper.objects.filter(user=request.user, id=paper_id).first()
        if not paper:
            return fail('论文不存在')
        image = request.FILES.get('image')
        if not image:
            return fail('请上传截图')
        rect = request.data.get('rect', '')
        rel_dir = f'ocr/{request.user.id}'
        abs_dir = os.path.join(settings.MEDIA_ROOT, rel_dir)
        os.makedirs(abs_dir, exist_ok=True)
        fname = f'{uuid.uuid4().hex}.png'
        rel_path = f'{rel_dir}/{fname}'
        abs_path = os.path.join(settings.MEDIA_ROOT, rel_path)
        with open(abs_path, 'wb') as f:
            for chunk in image.chunks():
                f.write(chunk)
        with open(abs_path, 'rb') as f:
            img_bytes = f.read()
        from services.ocr_service import ocr_image_layout
        layout = ocr_image_layout(
            img_bytes, user_config=_user_ocr_config(request.user),
            allow_mock=False, timeout=20,
        )
        ocr_text = (layout.get('text') or '').strip()
        if layout.get('provider') == 'mock' or layout.get('error') or not ocr_text:
            err = layout.get('error') or '未识别到文字'
            return fail(
                f'OCR 识别失败：{err}。请先启动 OCR 服务（本机 http://127.0.0.1:8866，'
                '或执行 docker compose up -d ocr）'
            )
        cfg = _user_ai_config(request.user)
        translation = translate(ocr_text, user_config=cfg) if ocr_text else ''
        summary = summarize_selection(ocr_text, user_config=cfg) if ocr_text else ''
        rec = OcrRecord.objects.create(
            user=request.user, paper=paper, image_path=rel_path, rect=rect,
            ocr_text=ocr_text, ai_translation=translation, ai_summary=summary,
        )
        return ok(OcrRecordSerializer(rec).data)


class GlossaryViewSet(viewsets.ModelViewSet):
    serializer_class = GlossarySerializer

    def get_queryset(self):
        return GlossaryTerm.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
