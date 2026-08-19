from django.db.models import Count, Q
from rest_framework import serializers
from rest_framework.views import APIView
from common.response import ok, fail
from common.pagination import StandardPagination
from reader.models import PaperNote
from reader.serializers import NoteSerializer
from .models import NoteLike, NoteComment


class CommentSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.CharField(source='user.avatar', read_only=True)

    class Meta:
        model = NoteComment
        fields = ('id', 'note', 'user', 'username', 'avatar', 'content', 'created_at')
        read_only_fields = ('user',)


class FeedView(APIView):
    def get(self, request):
        filter_type = request.query_params.get('type', 'all')  # all / summary / note / mine
        q = request.query_params.get('q', '').strip()
        qs = PaperNote.objects.filter(deleted_at__isnull=True).select_related('user', 'paper')

        if filter_type == 'mine':
            qs = qs.filter(user=request.user, visibility='public')
        elif filter_type == 'summary':
            qs = qs.filter(visibility='public').exclude(ai_summary__isnull=True).exclude(ai_summary='')
        elif filter_type == 'note':
            qs = qs.filter(visibility='public').exclude(note_text__isnull=True).exclude(note_text='')
        else:
            qs = qs.filter(visibility='public')

        if q:
            qs = qs.filter(
                Q(note_text__icontains=q) | Q(ai_summary__icontains=q) |
                Q(paper__title__icontains=q) | Q(user__username__icontains=q)
            )
        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        data = NoteSerializer(page, many=True).data
        # attach liked flag & comments count
        note_ids = [n['id'] for n in data]
        liked = set(
            NoteLike.objects.filter(user=request.user, note_id__in=note_ids).values_list('note_id', flat=True)
        )
        comment_rows = (
            NoteComment.objects.filter(note_id__in=note_ids)
            .values('note_id')
            .annotate(c=Count('id'))
        )
        comments = {r['note_id']: r['c'] for r in comment_rows}
        for item in data:
            item['liked'] = item['id'] in liked
            item['comment_count'] = comments.get(item['id'], 0)
        return paginator.get_paginated_response(data)


class PaperCommunityView(APIView):
    def get(self, request, paper_id):
        public = PaperNote.objects.filter(paper_id=paper_id, visibility='public', deleted_at__isnull=True)
        mine = PaperNote.objects.filter(paper_id=paper_id, user=request.user, deleted_at__isnull=True)
        from itertools import chain
        ids = set()
        notes = []
        for n in list(public) + list(mine):
            if n.id not in ids:
                ids.add(n.id)
                notes.append(n)
        notes.sort(key=lambda x: x.created_at, reverse=True)
        return ok(NoteSerializer(notes, many=True).data)


class LikeView(APIView):
    def post(self, request):
        note_id = request.data.get('note_id')
        note = PaperNote.objects.filter(id=note_id, visibility='public').first()
        if not note:
            return fail('笔记不存在')
        like, created = NoteLike.objects.get_or_create(note=note, user=request.user)
        if not created:
            like.delete()
            note.like_count = max(0, note.like_count - 1)
            note.save(update_fields=['like_count'])
            return ok({'liked': False, 'like_count': note.like_count})
        note.like_count += 1
        note.save(update_fields=['like_count'])
        return ok({'liked': True, 'like_count': note.like_count})


class CommentView(APIView):
    def get(self, request):
        note_id = request.query_params.get('note_id')
        qs = NoteComment.objects.filter(note_id=note_id).select_related('user')
        return ok(CommentSerializer(qs, many=True).data)

    def post(self, request):
        note_id = request.data.get('note_id')
        content = (request.data.get('content') or '').strip()
        if not content:
            return fail('评论不能为空')
        note = PaperNote.objects.filter(id=note_id, visibility='public').first()
        if not note:
            return fail('笔记不存在')
        c = NoteComment.objects.create(note=note, user=request.user, content=content[:1000])
        return ok(CommentSerializer(c).data, status=201)
