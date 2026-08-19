import re
from django.conf import settings
from django.db import transaction
from rest_framework import serializers
from .models import User, UserPreference, Friendship, UserNotification, MembershipPlan, MembershipOrder

DEFAULT_SOURCES = [
    ('arXiv', 'https://arxiv.org', 'arxiv', 1),
    ('Semantic Scholar', 'https://www.semanticscholar.org', 's2', 2),
    ('ACL Anthology', 'https://aclanthology.org', 'acl', 3),
    ('OpenReview', 'https://openreview.net', 'openreview', 4),
    ('百度学术', 'https://xueshu.baidu.com', 'baidu', 5),
    ('谷歌学术', 'https://scholar.google.com', 'google', 6),
]

DEFAULT_CATEGORIES = ['Transformer', 'OCR', '目标检测', '图像分类', '其他']


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    password2 = serializers.CharField(min_length=8, write_only=True)
    id_card = serializers.CharField(max_length=18, required=False, allow_blank=True)

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('邮箱已注册')
        return value

    def validate_id_card(self, value):
        if not value:
            return value
        if not re.match(r'^\d{17}[\dXx]$', value):
            raise serializers.ValidationError('身份证须为18位（末位可为X）')
        return value.upper()

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password2': '两次密码不一致'})
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        UserPreference.objects.create(
            user=user,
            translate_engine='newapi',
            translate_config={
                'provider': 'newapi',
                '_type': 'newapi_channel_conn',
                'url': settings.DEEPSEEK_BASE_URL,
                'api_key': '',  # 使用服务端环境变量，不把 Key 写入库
                'model': settings.DEEPSEEK_MODEL,
                'timeout': 60,
            },
            ocr_engine='paddleocr',
            ocr_config={'provider': 'paddleocr', 'url': 'http://127.0.0.1:8866', 'timeout': 60},
        )
        from papers.models import Category, UserSource
        for i, name in enumerate(DEFAULT_CATEGORIES):
            Category.objects.create(user=user, name=name, sort=i, is_system=True)
        for name, url, icon, sort in DEFAULT_SOURCES:
            UserSource.objects.create(
                user=user, name=name, url=url, icon=icon,
                source_type='builtin', is_default=True, sort=sort,
            )
        return user


class UserSerializer(serializers.ModelSerializer):
    id_card_masked = serializers.CharField(read_only=True)
    is_admin = serializers.SerializerMethodField()
    membership = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'id_card_masked', 'role', 'avatar',
            'research_direction', 'status', 'created_at', 'is_admin', 'membership',
            'quota_translate_daily', 'quota_parse_daily', 'quota_page_limit', 'quota_team_share',
            'membership_expire_at',
        )
        read_only_fields = (
            'email', 'role', 'status', 'created_at', 'is_admin', 'membership',
            'quota_translate_daily', 'quota_parse_daily', 'quota_page_limit', 'quota_team_share',
            'membership_expire_at',
        )

    def get_is_admin(self, obj):
        return bool(obj.is_admin)

    def get_membership(self, obj):
        from accounts.quota import snapshot
        return snapshot(obj)


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'id_card', 'avatar', 'research_direction')

    def validate_id_card(self, value):
        if value and not re.match(r'^\d{17}[\dXx]$', value):
            raise serializers.ValidationError('身份证须为18位')
        return value.upper() if value else value


class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = (
            'lang', 'translate_engine', 'translate_config',
            'ocr_engine', 'ocr_config', 'default_category',
        )


class FriendshipSerializer(serializers.ModelSerializer):
    friend_info = UserSerializer(source='friend', read_only=True)

    class Meta:
        model = Friendship
        fields = ('id', 'friend', 'friend_info', 'created_at')


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserNotification
        fields = (
            'id', 'title', 'body', 'level', 'kind', 'paper_id', 'job_id',
            'extra', 'is_read', 'created_at',
        )


class MembershipPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembershipPlan
        fields = (
            'id', 'code', 'name', 'daily_translate', 'daily_parse', 'page_limit',
            'price_month', 'team_share_limit', 'purchasable', 'sort', 'updated_at',
        )
        read_only_fields = ('code', 'updated_at')


class AdminUserSerializer(serializers.ModelSerializer):
    id_card_masked = serializers.CharField(read_only=True)
    is_admin = serializers.SerializerMethodField()
    membership = serializers.SerializerMethodField()
    plan_name = serializers.CharField(source='membership_plan.name', read_only=True, default=None)
    quota_translate_daily = serializers.IntegerField(allow_null=True, required=False)
    quota_parse_daily = serializers.IntegerField(allow_null=True, required=False)
    quota_page_limit = serializers.IntegerField(allow_null=True, required=False)
    quota_team_share = serializers.IntegerField(allow_null=True, required=False)

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'id_card_masked', 'role', 'avatar',
            'research_direction', 'status', 'is_staff', 'created_at',
            'membership_plan', 'plan_name', 'membership_expire_at',
            'quota_translate_daily', 'quota_parse_daily', 'quota_page_limit',
            'quota_team_share', 'is_admin', 'membership',
        )
        read_only_fields = ('created_at', 'is_admin', 'membership', 'plan_name', 'id_card_masked')
        extra_kwargs = {
            'membership_plan': {'allow_null': True, 'required': False},
            'membership_expire_at': {'allow_null': True, 'required': False},
        }

    def get_is_admin(self, obj):
        return bool(obj.is_admin)

    def get_membership(self, obj):
        from accounts.quota import snapshot
        return snapshot(obj)


class MembershipOrderSerializer(serializers.ModelSerializer):
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = MembershipOrder
        fields = (
            'id', 'plan', 'plan_name', 'username', 'months', 'amount', 'status',
            'channel', 'trade_no', 'paid_at', 'created_at',
        )
