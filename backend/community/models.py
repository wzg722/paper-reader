from django.conf import settings
from django.db import models


class NoteLike(models.Model):
    note = models.ForeignKey('reader.PaperNote', on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_note_likes'
        unique_together = ('note', 'user')


class NoteComment(models.Model):
    note = models.ForeignKey('reader.PaperNote', on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.CharField(max_length=1000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_note_comments'
        ordering = ['created_at']
