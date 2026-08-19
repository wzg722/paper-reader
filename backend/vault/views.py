from django.db.models import Avg, Count, Q
from rest_framework.views import APIView
from common.response import ok, fail
from papers.models import Paper
from reader.models import PaperNote, PaperHighlight, GlossaryTerm
from .models import ExportRecord


class VaultOverviewView(APIView):
    def get(self, request):
        u = request.user
        papers = Paper.objects.filter(user=u, deleted_at__isnull=True)
        notes = PaperNote.objects.filter(user=u, deleted_at__isnull=True)
        card_qs = (
            papers.filter(Q(ai_summary__isnull=False) | Q(read_progress__gt=0))
            .select_related('category')
            .annotate(note_count=Count('notes', filter=Q(notes__deleted_at__isnull=True)))
            .order_by('-updated_at', '-id')
        )
        avg = papers.filter(read_progress__gt=0).aggregate(v=Avg('read_progress'))['v']
        return ok({
            'stats': {
                'cards': card_qs.count(),
                'terms': GlossaryTerm.objects.filter(user=u).count(),
                'notes': notes.count(),
                'highlights': PaperHighlight.objects.filter(user=u).count(),
                'avg_progress': int(round(avg or 0)),
            },
            'cards': [
                {
                    'id': p.id,
                    'title': p.title,
                    'title_zh': p.title_zh,
                    'intro': p.intro,
                    'ai_summary': p.ai_summary,
                    'status': p.status,
                    'read_progress': p.read_progress or 0,
                    'year': p.year,
                    'category': p.category.name if p.category_id else '',
                    'tags': p.tags or '',
                    'note_count': p.note_count or 0,
                }
                for p in card_qs[:200]
            ],
        })


class ObsidianExportView(APIView):
    def post(self, request):
        ids = request.data.get('paper_ids') or []
        papers = Paper.objects.filter(user=request.user, id__in=ids, deleted_at__isnull=True)
        if not papers:
            return fail('请选择论文')
        files = []
        for p in papers:
            terms = GlossaryTerm.objects.filter(user=request.user, source_paper=p)
            notes = PaperNote.objects.filter(user=request.user, paper=p, deleted_at__isnull=True)
            sm = p.ai_summary or {}

            def _sum_text(val):
                if val is None:
                    return ''
                if isinstance(val, str):
                    return val
                if isinstance(val, list):
                    return '；'.join(x for x in (_sum_text(i) for i in val) if x)
                if isinstance(val, dict):
                    zh = val.get('zh') or ''
                    en = val.get('en') or ''
                    if isinstance(zh, list) or isinstance(en, list):
                        return _sum_text(zh or en)
                    if zh and en:
                        return f'{zh} / {en}'
                    return str(zh or en or '')
                return str(val)

            md = [
                '---',
                f'title: "{p.title}"',
                f'title_zh: "{p.title_zh or ""}"',
                f'authors: "{p.authors or ""}"',
                f'year: {p.year or ""}',
                f'tags: [{", ".join(p.tags.split(",")) if p.tags else ""}]',
                f'doi: "{p.doi or ""}"',
                '---',
                '',
                f'# {p.title}',
                '',
                f'> {p.intro or ""}',
                '',
                '## AI 精读总结',
                f'- **核心**: {_sum_text(sm.get("core"))}',
                f'- **问题**: {_sum_text(sm.get("problem"))}',
                f'- **方法**: {_sum_text(sm.get("method"))}',
                f'- **结果**: {_sum_text(sm.get("result"))}',
                f'- **局限**: {_sum_text(sm.get("limit"))}',
                f'- **启发**: {_sum_text(sm.get("insight"))}',
                '',
                '## 摘要',
                p.abstract or '',
                '',
                '## 中文摘要',
                p.abstract_zh or '',
                '',
                '## 术语表',
            ]
            for t in terms:
                md.append(f'- **{t.term_en}** / {t.term_zh}: {t.description or ""}')
            md.append('')
            md.append('## 笔记')
            for n in notes:
                md.append(f'- [[{p.title}]] {n.note_text or n.ai_summary or n.sel_text or ""}')
            content = '\n'.join(md)
            safe_name = ''.join(c if c.isalnum() or c in '._- ' else '_' for c in p.title)[:80]
            files.append({'filename': f'{safe_name}.md', 'content': content})
        ExportRecord.objects.create(
            user=request.user, paper_ids=ids, file_count=len(files), export_type='multi',
        )
        return ok({'files': files})
