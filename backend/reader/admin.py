from django.contrib import admin
from .models import PaperHighlight, PaperNote, OcrRecord, ReadingRecord, GlossaryTerm, ParagraphTranslation

for m in (PaperHighlight, PaperNote, OcrRecord, ReadingRecord, GlossaryTerm, ParagraphTranslation):
    admin.site.register(m)
