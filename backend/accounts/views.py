from django.contrib.auth import authenticate
from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from common.response import ok, fail
from .models import User, UserPreference, UserNotification, MembershipPlan, MembershipOrder
from .serializers import (
    RegisterSerializer, UserSerializer, UserUpdateSerializer, PreferenceSerializer,
    NotificationSerializer, MembershipPlanSerializer, AdminUserSerializer,
    MembershipOrderSerializer,
)
from .quota import ensure_plans, is_admin, snapshot


def tokens_for(user):
    """Each login issues a new independent token pair; other devices stay logged in."""
    refresh = RefreshToken.for_user(user)
    return {'refresh': str(refresh), 'access': str(refresh.access_token)}


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RegisterSerializer(data=request.data)
        if not ser.is_valid():
            return fail(ser.errors, status=400)
        user = ser.save()
        return ok({
            'user': UserSerializer(user).data,
            'tokens': tokens_for(user),
        }, message='注册成功', status=201)


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        password = request.data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if not user:
            return fail('邮箱或密码错误', status=401)
        if user.status != 1:
            return fail('账号已禁用', status=403)
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
        return ok({'user': UserSerializer(user).data, 'tokens': tokens_for(user)})


class AuthRefreshView(APIView):
    """Renew access token for this device only. Other platforms' tokens are untouched."""
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        raw = request.data.get('refresh') or ''
        if not raw:
            return fail('请重新登录', status=401)
        try:
            token = RefreshToken(raw)
            user = User.objects.filter(pk=token.get('user_id'), status=1).first()
            if not user:
                return fail('账号不可用，请重新登录', status=401)
            return ok({'access': str(token.access_token), 'refresh': str(token)})
        except TokenError:
            return fail('登录已过期，请重新登录', status=401)


class MeView(APIView):
    def get(self, request):
        from accounts.quota import ensure_plans
        ensure_plans()
        return ok(UserSerializer(request.user).data)

    def patch(self, request):
        ser = UserUpdateSerializer(request.user, data=request.data, partial=True)
        if not ser.is_valid():
            return fail(ser.errors)
        ser.save()
        return ok(UserSerializer(request.user).data)


class PreferenceView(APIView):
    def get(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        return ok(PreferenceSerializer(pref).data)

    def put(self, request):
        pref, _ = UserPreference.objects.get_or_create(user=request.user)
        ser = PreferenceSerializer(pref, data=request.data, partial=True)
        if not ser.is_valid():
            return fail(ser.errors)
        ser.save()
        return ok(PreferenceSerializer(pref).data)


class ProfileStatsView(APIView):
    def get(self, request):
        from papers.models import Paper
        from reader.models import PaperNote, PaperHighlight, ReadingRecord
        u = request.user
        papers = Paper.objects.filter(user=u, deleted_at__isnull=True)
        return ok({
            'paper_count': papers.count(),
            'read_done': papers.filter(status='读完').count(),
            'note_count': PaperNote.objects.filter(user=u).count(),
            'highlight_count': PaperHighlight.objects.filter(user=u).count(),
            'duration_sec': sum(
                ReadingRecord.objects.filter(user=u).values_list('duration_sec', flat=True)
            ) or 0,
            'ai_ask_count': 0,
        })


class UserSearchView(APIView):
    def get(self, request):
        q = request.query_params.get('q', '').strip()
        qs = User.objects.filter(status=1).exclude(id=request.user.id)
        if q:
            qs = qs.filter(username__icontains=q)
        return ok(UserSerializer(qs[:20], many=True).data)


class NotificationListView(APIView):
    def get(self, request):
        from services.recommend import page_params, paged
        qs = UserNotification.objects.filter(user=request.user)
        unread_count = qs.filter(is_read=False).count()
        if str(request.query_params.get('unread') or '').lower() in ('1', 'true', 'yes'):
            qs = qs.filter(is_read=False)
        page, page_size, start = page_params(request, default_size=20)
        rows = list(qs[start:start + page_size])
        payload = paged(NotificationSerializer(rows, many=True).data, qs.count(), page, page_size)
        payload['unread_count'] = unread_count
        return ok(payload)


class NotificationReadView(APIView):
    def post(self, request, pk):
        obj = UserNotification.objects.filter(user=request.user, id=pk).first()
        if not obj:
            return fail('通知不存在')
        if not obj.is_read:
            obj.is_read = True
            obj.save(update_fields=['is_read'])
        return ok(NotificationSerializer(obj).data)


class NotificationReadAllView(APIView):
    def post(self, request):
        n = UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        return ok({'updated': n}, message='已全部标为已读')


def _require_admin(request):
    if not is_admin(request.user):
        return fail('需要管理员权限', status=403)
    return None


class MembershipPlanListView(APIView):
    def get(self, request):
        ensure_plans()
        qs = MembershipPlan.objects.all()
        if not is_admin(request.user):
            qs = qs.filter(purchasable=True)
        return ok(MembershipPlanSerializer(qs, many=True).data)


class MembershipCheckoutView(APIView):
    def post(self, request):
        from accounts.payment import fulfill_order, new_trade_no, pay_qr_svg
        ensure_plans()
        plan_id = request.data.get('plan_id')
        channel = (request.data.get('channel') or 'alipay').strip()
        if channel not in ('alipay', 'wechat'):
            channel = 'alipay'
        months = request.data.get('months') or 1
        try:
            months = max(1, min(int(months), 12))
        except (TypeError, ValueError):
            months = 1
        plan = MembershipPlan.objects.filter(id=plan_id, purchasable=True).first()
        if not plan:
            return fail('套餐不存在或不可购买')
        amount = (plan.price_month or 0) * months
        MembershipOrder.objects.filter(user=request.user, status='pending').update(status='cancelled')
        order = MembershipOrder.objects.create(
            user=request.user, plan=plan, months=months, amount=amount,
            status='pending', channel=channel, trade_no=new_trade_no(),
        )
        if amount <= 0:
            data = fulfill_order(order)
            return ok(data, message=f'已开通{plan.name}')
        payload = f'{order.trade_no}|{order.amount}|{channel}'
        return ok({
            'order': MembershipOrderSerializer(order).data,
            'need_pay': True,
            'qr_svg': pay_qr_svg(payload, dark='#1677FF' if channel == 'alipay' else '#07C160'),
        }, message='请完成支付')


class MembershipPayView(APIView):
    def get(self, request, pk):
        from accounts.payment import pay_qr_svg
        order = MembershipOrder.objects.filter(user=request.user, id=pk).first()
        if not order:
            return fail('订单不存在')
        payload = f'{order.trade_no}|{order.amount}|{order.channel}'
        color = '#1677FF' if order.channel == 'alipay' else '#07C160'
        return ok({
            'order': MembershipOrderSerializer(order).data,
            'qr_svg': pay_qr_svg(payload, dark=color) if order.status == 'pending' else '',
        })

    def post(self, request, pk):
        from accounts.payment import fulfill_order
        order = MembershipOrder.objects.select_related('plan', 'user').filter(
            user=request.user, id=pk,
        ).first()
        if not order:
            return fail('订单不存在')
        try:
            data = fulfill_order(order)
        except ValueError as e:
            return fail(str(e))
        return ok(data, message=f'支付成功，已开通{order.plan.name}')


class MembershipCancelView(APIView):
    def post(self, request, pk):
        order = MembershipOrder.objects.filter(user=request.user, id=pk, status='pending').first()
        if not order:
            return fail('没有待支付订单')
        order.status = 'cancelled'
        order.save(update_fields=['status'])
        return ok(MembershipOrderSerializer(order).data, message='已取消')


class AdminOrderListView(APIView):
    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied
        qs = MembershipOrder.objects.select_related('user', 'plan').all()
        status = (request.query_params.get('status') or '').strip()
        if status:
            qs = qs.filter(status=status)
        from services.recommend import page_params, paged
        page, page_size, start = page_params(request, default_size=10)
        total = qs.count()
        rows = list(qs[start:start + page_size])
        return ok(paged(MembershipOrderSerializer(rows, many=True).data, total, page, page_size))


class MyQuotaView(APIView):
    def get(self, request):
        ensure_plans()
        return ok(snapshot(request.user))


class AdminUserListView(APIView):
    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied
        ensure_plans()
        q = (request.query_params.get('q') or '').strip()
        qs = User.objects.all().select_related('membership_plan').order_by('-id')
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(email__icontains=q))
        status = request.query_params.get('status')
        if status not in (None, ''):
            qs = qs.filter(status=status)
        from services.recommend import page_params, paged
        page, page_size, start = page_params(request, default_size=10)
        total = qs.count()
        rows = list(qs[start:start + page_size])
        return ok(paged(AdminUserSerializer(rows, many=True).data, total, page, page_size))


class AdminUserDetailView(APIView):
    def patch(self, request, pk):
        denied = _require_admin(request)
        if denied:
            return denied
        user = User.objects.filter(pk=pk).first()
        if not user:
            return fail('用户不存在')
        ser = AdminUserSerializer(user, data=request.data, partial=True)
        if not ser.is_valid():
            return fail(ser.errors)
        ser.save()
        return ok(AdminUserSerializer(user).data, message='已保存')

    def delete(self, request, pk):
        denied = _require_admin(request)
        if denied:
            return denied
        user = User.objects.filter(pk=pk).first()
        if not user:
            return fail('用户不存在')
        if user.id == request.user.id:
            return fail('不能删除当前登录账号')
        hard = str(request.query_params.get('hard') or '').lower() in ('1', 'true')
        if hard:
            user.delete()
            return ok(message='已彻底删除')
        user.status = 0
        user.deleted_at = timezone.now()
        user.save(update_fields=['status', 'deleted_at'])
        return ok(message='已停用并删除')


class AdminUserResetPasswordView(APIView):
    def post(self, request, pk):
        from django.contrib.auth.password_validation import validate_password
        from django.core.exceptions import ValidationError
        from accounts.notify import push_notification

        denied = _require_admin(request)
        if denied:
            return denied
        user = User.objects.filter(pk=pk).first()
        if not user:
            return fail('用户不存在')
        password = (request.data.get('password') or '').strip()
        password2 = request.data.get('password2')
        if password2 is None:
            password2 = password
        else:
            password2 = str(password2).strip()
        if len(password) < 8:
            return fail('新密码至少 8 位')
        if password != password2:
            return fail('两次密码不一致')
        try:
            validate_password(password, user=user)
        except ValidationError as e:
            return fail('；'.join(e.messages))
        user.set_password(password)
        user.save(update_fields=['password', 'updated_at'])
        push_notification(
            user.id,
            title='密码已重置',
            body='管理员已重置你的登录密码，请使用新密码登录。',
            level='warning',
            kind='system',
        )
        return ok(message=f'已重置「{user.username}」的密码')


class AdminPlanView(APIView):
    def get(self, request):
        denied = _require_admin(request)
        if denied:
            return denied
        ensure_plans()
        return ok(MembershipPlanSerializer(MembershipPlan.objects.all(), many=True).data)

    def patch(self, request, pk=None):
        denied = _require_admin(request)
        if denied:
            return denied
        plan = MembershipPlan.objects.filter(pk=pk).first()
        if not plan:
            return fail('套餐不存在')
        ser = MembershipPlanSerializer(plan, data=request.data, partial=True)
        if not ser.is_valid():
            return fail(ser.errors)
        ser.save()
        return ok(MembershipPlanSerializer(plan).data, message='套餐已更新')
