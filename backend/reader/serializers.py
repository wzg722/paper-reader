from rest_framework import serializers
from .models import (
    PaperHighlight, PaperNote, OcrRecord, ReadingRecord, GlossaryTerm,
)


class HighlightSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperHighlight
        fields = ('id', 'paper', 'para_index', 'sel_text', 'color', 'created_at')
        read_only_fields = ('id', 'created_at')


class NoteSerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source='paper.title', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    avatar = serializers.CharField(source='user.avatar', read_only=True)
    role = serializers.CharField(source='user.role', read_only=True)
    color = serializers.SerializerMethodField()

    class Meta:
        model = PaperNote
        fields = (
            'id', 'paper', 'paper_title', 'highlight', 'sel_text', 'note_text',
            'ai_translation', 'ai_summary', 'source', 'visibility',
            'ocr_image_path', 'ocr_rect', 'para_index', 'like_count',
            'username', 'avatar', 'role', 'user', 'color', 'created_at',
        )
        read_only_fields = ('user', 'like_count', 'created_at', 'color')

    def get_color(self, obj):
        if obj.highlight_id and obj.highlight:
            return obj.highlight.color or 'y'
        return 'y'


class OcrRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OcrRecord
        fields = (
            'id', 'paper', 'image_path', 'rect', 'ocr_text',
            'ai_translation', 'ai_summary', 'is_edited', 'created_at',
        )
        read_only_fields = ('image_path',)


class ReadingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReadingRecord
        fields = (
            'id', 'paper', 'progress', 'duration_sec',
            'last_section', 'last_position', 'read_at', 'updated_at',
        )


class GlossarySerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source='source_paper.title', read_only=True, default=None)

    class Meta:
        model = GlossaryTerm
        fields = (
            'id', 'term_en', 'term_zh', 'description',
            'source_paper', 'paper_title', 'created_at',
        )
