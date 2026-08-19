from django.conf import settings
from django.db import models


class ExportRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='exports')
    paper_ids = models.JSONField(blank=True, null=True)
    file_count = models.IntegerField(default=0)
    export_type = models.CharField(max_length=20, default='multi')  # single/multi/zip/backup
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'export_records'
