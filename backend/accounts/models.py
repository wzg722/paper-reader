from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    def create_user(self, email, username, password=None, **extra):
        if not email:
            raise ValueError('邮箱必填')
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, username, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('role', '技术负责人')
        return self.create_user(email, username, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    ROLE_CHOICES = [
        ('普通用户', '普通用户'),
        ('技术负责人', '技术负责人'),
        ('团队管理员', '团队管理员'),
        ('专业版', '专业版'),
    ]
    username = models.CharField('昵称', max_length=50)
    email = models.EmailField('邮箱', unique=True)
    id_card = models.CharField('身份证', max_length=18, blank=True, null=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='普通用户')
    avatar = models.CharField(max_length=255, default='🦉')
    research_direction = models.CharField(max_length=255, blank=True, null=True)
    status = models.SmallIntegerField(default=1)  # 0禁用 1正常
    is_staff = models.BooleanField(default=False)
    membership_plan = models.ForeignKey(
        'MembershipPlan', on_delete=models.SET_NULL, null=True, blank=True, related_name='users',
    )
    membership_expire_at = models.DateTimeField(null=True, blank=True)
    quota_translate_daily = models.IntegerField(null=True, blank=True)
    quota_parse_daily = models.IntegerField(null=True, blank=True)
    quota_page_limit = models.IntegerField(null=True, blank=True)
    quota_team_share = models.IntegerField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = '用户'

    def __str__(self):
        return self.username

    @property
    def is_admin(self):
        return bool(self.is_staff or self.is_superuser or self.role == '技术负责人')

    @property
    def id_card_masked(self):
        if not self.id_card or len(self.id_card) < 10:
            return self.id_card or ''
        return f'{self.id_card[:6]}********{self.id_card[-4:]}'


class UserPreference(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='preference')
    lang = models.CharField(max_length=10, default='zh')
    translate_engine = models.CharField(max_length=50, blank=True, null=True, default='deepseek')
    translate_config = models.JSONField(blank=True, null=True)
    ocr_engine = models.CharField(max_length=50, blank=True, null=True, default='paddleocr')
    ocr_config = models.JSONField(blank=True, null=True)
    default_category = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'user_preferences'


class Friendship(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friendships')
    friend = models.ForeignKey(User, on_delete=models.CASCADE, related_name='friend_of')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'friendships'
        unique_together = ('user', 'friend')


class UserNotification(models.Model):
    LEVEL_CHOICES = [
        ('info', 'info'),
        ('success', 'success'),
        ('warning', 'warning'),
        ('error', 'error'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    title = models.CharField(max_length=120)
    body = models.CharField(max_length=500, blank=True, default='')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    kind = models.CharField(max_length=20, default='system')  # import / system / share
    paper_id = models.BigIntegerField(null=True, blank=True)
    job_id = models.BigIntegerField(null=True, blank=True)
    extra = models.JSONField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_notifications'
        ordering = ['-id']
        indexes = [
            models.Index(fields=['user', 'is_read', '-id']),
            models.Index(fields=['user', 'job_id']),
        ]


class MembershipPlan(models.Model):
    """Admin-editable membership tiers and prices."""
    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=40)
    daily_translate = models.IntegerField(default=1)
    daily_parse = models.IntegerField(default=1)
    page_limit = models.IntegerField(default=10)
    price_month = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    team_share_limit = models.IntegerField(default=0)  # -1 unlimited, 0 none
    purchasable = models.BooleanField(default=True)
    sort = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'membership_plans'
        ordering = ['sort', 'id']

    def __str__(self):
        return self.name


class DailyUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='daily_usages')
    day = models.DateField()
    translate_ids = models.JSONField(default=list, blank=True)
    parse_ids = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = 'daily_usages'
        unique_together = ('user', 'day')


class MonthlyUsage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='monthly_usages')
    year = models.IntegerField()
    month = models.IntegerField()
    team_share_count = models.IntegerField(default=0)

    class Meta:
        db_table = 'monthly_usages'
        unique_together = ('user', 'year', 'month')


class MembershipOrder(models.Model):
    STATUS_CHOICES = [('pending', 'pending'), ('paid', 'paid'), ('cancelled', 'cancelled')]
    CHANNEL_CHOICES = [('alipay', '支付宝'), ('wechat', '微信支付')]
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='membership_orders')
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name='orders')
    months = models.PositiveSmallIntegerField(default=1)
    amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    channel = models.CharField(max_length=20, choices=CHANNEL_CHOICES, default='alipay')
    trade_no = models.CharField(max_length=40, unique=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'membership_orders'
        ordering = ['-id']
