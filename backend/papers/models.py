from django.conf import settings
from django.db import models


class Category(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='categories')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
    )
    name = models.CharField(max_length=50)
    sort = models.IntegerField(default=0)
    is_system = models.BooleanField(default=False)
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'categories'
        ordering = ['sort', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['user', 'parent', 'name'],
                name='uniq_category_name_per_parent',
            ),
        ]


class Paper(models.Model):
    STATUS_CHOICES = [('想读', '想读'), ('在读', '在读'), ('读完', '读完')]
    SOURCE_CHOICES = [
        ('file', 'file'), ('doi', 'doi'), ('arxiv', 'arxiv'),
        ('site', 'site'), ('graph', 'graph'), ('share', 'share'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='papers')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='papers')
    title = models.CharField(max_length=500)
    title_zh = models.CharField(max_length=500, blank=True, null=True)
    authors = models.CharField(max_length=500, blank=True, null=True)
    venue = models.CharField(max_length=200, blank=True, null=True)
    year = models.SmallIntegerField(null=True, blank=True)
    doi = models.CharField(max_length=100, blank=True, null=True)
    arxiv_id = models.CharField(max_length=50, blank=True, null=True)
    abstract = models.TextField(blank=True, null=True)
    abstract_zh = models.TextField(blank=True, null=True)
    intro = models.CharField(max_length=1000, blank=True, null=True)
    tags = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='想读')
    starred = models.BooleanField(default=False)
    read_progress = models.PositiveSmallIntegerField(default=0)
    source_type = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='file')
    file_type = models.CharField(max_length=10, blank=True, null=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    file_size = models.BigIntegerField(null=True, blank=True)
    cover_url = models.CharField(max_length=500, blank=True, null=True)
    # Remote PDF download URL (kept even if local file is deleted / missing)
    pdf_url = models.CharField(max_length=500, blank=True, null=True)
    cites = models.IntegerField(default=0)
    content_json = models.JSONField(blank=True, null=True)  # parsed blocks [{type,en,zh,image,...}]
    outline = models.JSONField(blank=True, null=True)  # [{id, title, para_index, page}]
    layout_meta = models.JSONField(blank=True, null=True)  # {pages:[{page,thumb,width,height}], parse_mode}
    ai_summary = models.JSONField(blank=True, null=True)  # six-section summary
    share_type = models.CharField(max_length=20, default='private')
    team_id = models.BigIntegerField(null=True, blank=True)
    last_read_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'papers'
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['user', 'category']),
            models.Index(fields=['user', 'starred']),
        ]
        ordering = ['-last_read_at', '-id']

    def __str__(self):
        return self.title


class PaperFile(models.Model):
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='files')
    file_type = models.CharField(max_length=10)
    file_name = models.CharField(max_length=255)
    file_path = models.CharField(max_length=500)
    file_size = models.BigIntegerField(null=True, blank=True)
    page_count = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_files'


class UserSource(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sources')
    name = models.CharField(max_length=50)
    url = models.CharField(max_length=500)
    icon = models.CharField(max_length=200, blank=True, null=True)
    source_type = models.CharField(max_length=20, default='builtin')
    is_default = models.BooleanField(default=False)
    sort = models.IntegerField(default=0)
    enabled = models.BooleanField(default=True)
    team_id = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_sources'
        ordering = ['sort', 'id']


class ImportRecord(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='imports')
    paper = models.ForeignKey(Paper, on_delete=models.SET_NULL, null=True, blank=True)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_path = models.CharField(max_length=500, blank=True, null=True)
    import_type = models.CharField(max_length=20)
    status = models.CharField(max_length=20, default='pending')
    error_msg = models.CharField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'import_records'


class PaperShare(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='shares_sent')
    paper = models.ForeignKey(Paper, on_delete=models.CASCADE, related_name='shares')
    target_type = models.CharField(max_length=10)  # user / team
    target_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        null=True, blank=True, related_name='shares_received',
    )
    target_team_id = models.BigIntegerField(null=True, blank=True)
    message = models.CharField(max_length=500, blank=True, null=True)
    status = models.CharField(max_length=20, default='active')  # active/revoked/accepted/ignored
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'paper_shares'
