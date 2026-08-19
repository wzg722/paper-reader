from django.conf import settings
from django.db import models


class PaperHighlight(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='highlights')
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE, related_name='highlights')
    para_index = models.IntegerField()
    sel_text = models.CharField(max_length=1000)
    color = models.CharField(max_length=10, default='y')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_highlights'


class PaperNote(models.Model):
    VISIBILITY = [('public', '公开'), ('friends', '仅好友'), ('private', '私密')]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notes')
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE, related_name='notes')
    highlight = models.ForeignKey(PaperHighlight, on_delete=models.SET_NULL, null=True, blank=True)
    sel_text = models.CharField(max_length=1000, blank=True, null=True)
    note_text = models.TextField(blank=True, null=True)
    ai_translation = models.TextField(blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)
    source = models.CharField(max_length=20, default='selection')  # selection / ocr
    visibility = models.CharField(max_length=10, choices=VISIBILITY, default='public')
    ocr_image_path = models.CharField(max_length=500, blank=True, null=True)
    ocr_rect = models.CharField(max_length=50, blank=True, null=True)
    para_index = models.IntegerField(null=True, blank=True)
    like_count = models.IntegerField(default=0)
    deleted_at = models.DateTimeField(null=True, blank=True)
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_notes'
        ordering = ['-created_at']


class OcrRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='ocr_records')
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE, related_name='ocr_records')
    image_path = models.CharField(max_length=500)
    rect = models.CharField(max_length=50, blank=True, null=True)
    ocr_text = models.TextField()
    ai_translation = models.TextField(blank=True, null=True)
    ai_summary = models.TextField(blank=True, null=True)
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ocr_records'


class ReadingRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='reading_records')
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE, related_name='reading_records')
    progress = models.PositiveSmallIntegerField(default=0)
    duration_sec = models.PositiveIntegerField(default=0)
    last_section = models.CharField(max_length=50, blank=True, null=True)
    last_position = models.IntegerField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'reading_records'
        unique_together = ('user', 'paper')


class GlossaryTerm(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='glossary')
    term_en = models.CharField(max_length=200)
    term_zh = models.CharField(max_length=200)
    description = models.CharField(max_length=500, blank=True, null=True)
    source_paper = models.ForeignKey(
        'papers.Paper', on_delete=models.SET_NULL, null=True, blank=True, related_name='terms',
    )
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'glossary_terms'
        unique_together = ('user', 'term_en')


class ParagraphTranslation(models.Model):
    """Cache for paragraph-level translations."""
    paper = models.ForeignKey('papers.Paper', on_delete=models.CASCADE, related_name='translations')
    para_index = models.IntegerField()
    text_hash = models.CharField(max_length=64)
    source_text = models.TextField()
    translated_text = models.TextField()
    engine = models.CharField(max_length=50, default='deepseek')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paragraph_translations'
        unique_together = ('paper', 'para_index', 'text_hash')
