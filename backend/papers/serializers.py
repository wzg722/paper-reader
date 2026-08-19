from rest_framework import serializers
from services.pdf_import import resolve_paper_pdf_path, resolve_pdf_source_url
from .models import Category, Paper, PaperFile, UserSource, ImportRecord, PaperShare


class CategorySerializer(serializers.ModelSerializer):
    paper_count = serializers.SerializerMethodField()
    child_count = serializers.SerializerMethodField()
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(), allow_null=True, required=False,
    )

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'sort', 'is_system', 'parent',
            'paper_count', 'child_count', 'created_at',
        )
        read_only_fields = ('is_system',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and getattr(user, 'is_authenticated', False):
            self.fields['parent'].queryset = Category.objects.filter(user=user)

    def get_paper_count(self, obj):
        return obj.papers.filter(deleted_at__isnull=True).count()

    def get_child_count(self, obj):
        return obj.children.count()

    def validate_parent(self, parent):
        if not parent:
            return parent
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        if user and parent.user_id != user.id:
            raise serializers.ValidationError('不能放到其他人的文件夹下')
        instance = getattr(self, 'instance', None)
        if instance:
            cur = parent
            seen = set()
            while cur:
                if cur.id == instance.id:
                    raise serializers.ValidationError('不能把文件夹放到自己的子文件夹下')
                if cur.id in seen:
                    break
                seen.add(cur.id)
                cur = cur.parent
        depth = 1
        cur = parent
        while cur:
            depth += 1
            if depth > 8:
                raise serializers.ValidationError('文件夹最多嵌套 8 层')
            cur = cur.parent
        return parent

    def validate(self, attrs):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        name = attrs.get('name') or getattr(self.instance, 'name', None)
        parent = attrs['parent'] if 'parent' in attrs else getattr(self.instance, 'parent', None)
        qs = Category.objects.filter(user=user, name=name, parent=parent)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError({'name': '同级已有同名文件夹'})
        return attrs


class PaperFileSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaperFile
        fields = ('id', 'file_type', 'file_name', 'file_path', 'file_size', 'page_count')


class PaperListSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    class Meta:
        model = Paper
        fields = (
            'id', 'title', 'title_zh', 'authors', 'venue', 'year', 'doi', 'arxiv_id',
            'intro', 'tags', 'status', 'starred', 'read_progress', 'source_type',
            'file_type', 'cites', 'category', 'category_name', 'last_read_at',
            'created_at', 'deleted_at',
        )


class PaperDetailSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)
    files = PaperFileSerializer(many=True, read_only=True)
    has_pdf = serializers.SerializerMethodField()
    pdf_file_url = serializers.SerializerMethodField()

    class Meta:
        model = Paper
        fields = (
            'id', 'title', 'title_zh', 'authors', 'venue', 'year', 'doi', 'arxiv_id',
            'abstract', 'abstract_zh', 'intro', 'tags', 'status', 'starred',
            'read_progress', 'source_type', 'file_type', 'file_path', 'file_size',
            'cites', 'category', 'category_name', 'content_json', 'outline',
            'layout_meta', 'ai_summary', 'files', 'has_pdf', 'pdf_file_url',
            'cover_url', 'pdf_url', 'last_read_at', 'created_at', 'updated_at',
        )

    def get_has_pdf(self, obj):
        # Local file present, or remountable via stored / inferred download URL
        return resolve_paper_pdf_path(obj) is not None or bool(resolve_pdf_source_url(obj))

    def get_pdf_file_url(self, obj):
        if self.get_has_pdf(obj):
            return f'/api/papers/{obj.id}/file/'
        return None


class PaperWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paper
        fields = (
            'title', 'title_zh', 'authors', 'venue', 'year', 'doi', 'arxiv_id',
            'abstract', 'abstract_zh', 'intro', 'tags', 'status', 'starred',
            'category', 'source_type', 'pdf_url',
        )


class UserSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserSource
        fields = (
            'id', 'name', 'url', 'icon', 'source_type', 'is_default',
            'sort', 'enabled', 'created_at',
        )
        read_only_fields = ('is_default', 'source_type')


class ImportRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportRecord
        fields = (
            'id', 'paper', 'file_name', 'file_path', 'import_type',
            'status', 'error_msg', 'created_at',
        )


class PaperShareSerializer(serializers.ModelSerializer):
    paper_title = serializers.CharField(source='paper.title', read_only=True)
    from_user = serializers.CharField(source='user.username', read_only=True)
    from_avatar = serializers.CharField(source='user.avatar', read_only=True)
    from_role = serializers.CharField(source='user.role', read_only=True)
    target_username = serializers.SerializerMethodField()

    class Meta:
        model = PaperShare
        fields = (
            'id', 'paper', 'paper_title', 'target_type', 'target_user', 'target_username',
            'target_team_id', 'message', 'status', 'created_at',
            'from_user', 'from_avatar', 'from_role',
        )

    def get_target_username(self, obj):
        return obj.target_user.username if getattr(obj, 'target_user_id', None) else None
