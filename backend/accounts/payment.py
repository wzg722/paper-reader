"""Membership payment: create order, mark paid, notify admins."""
from __future__ import annotations

import hashlib
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone


def new_trade_no() -> str:
    now = timezone.localtime()
    stamp = now.strftime('%Y%m%d%H%M%S')
    tail = hashlib.md5(f'{stamp}-{now.microsecond}'.encode()).hexdigest()[:8].upper()
    return f'PM{stamp}{tail}'


def pay_qr_svg(payload: str, size: int = 180, dark: str = '#111827') -> str:
    """Deterministic QR-like SVG so the pay panel has a scannable-looking code."""
    n = 25
    digest = hashlib.sha256(payload.encode('utf-8')).digest()
    bits = []
    for b in digest * 8:
        for i in range(8):
            bits.append((b >> i) & 1)
            if len(bits) >= n * n:
                break
        if len(bits) >= n * n:
            break

    def finder(r0, c0):
        for r in range(7):
            for c in range(7):
                edge = r in (0, 6) or c in (0, 6)
                inner = 2 <= r <= 4 and 2 <= c <= 4
                bits[n * (r0 + r) + (c0 + c)] = 1 if (edge or inner) else 0

    finder(0, 0)
    finder(0, n - 7)
    finder(n - 7, 0)
    cell = size / n
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" viewBox="0 0 {size} {size}">',
        f'<rect width="{size}" height="{size}" fill="#fff"/>',
    ]
    for i in range(n * n):
        if not bits[i]:
            continue
        r, c = divmod(i, n)
        parts.append(
            f'<rect x="{c * cell:.2f}" y="{r * cell:.2f}" width="{cell:.2f}" height="{cell:.2f}" fill="{dark}"/>'
        )
    parts.append('</svg>')
    return ''.join(parts)


def admin_users():
    from accounts.models import User
    return User.objects.filter(status=1, deleted_at__isnull=True).filter(
        Q(is_staff=True) | Q(is_superuser=True) | Q(role='技术负责人'),
    )


def notify_admins(*, title: str, body: str, extra=None, exclude_id=None):
    from accounts.notify import push_notification
    qs = admin_users()
    if exclude_id:
        qs = qs.exclude(id=exclude_id)
    for admin in qs:
        push_notification(
            admin.id,
            title=title,
            body=body,
            level='success',
            kind='membership',
            extra=extra,
        )


@transaction.atomic
def fulfill_order(order) -> dict:
    """Mark paid, upgrade membership, notify user and admins. Idempotent."""
    from accounts.models import MembershipOrder
    from accounts.notify import push_notification
    from accounts.quota import activate_plan
    from accounts.serializers import MembershipOrderSerializer, UserSerializer

    order = MembershipOrder.objects.select_for_update().select_related('plan', 'user').get(pk=order.pk)
    if order.status == 'paid':
        return {
            'order': MembershipOrderSerializer(order).data,
            'user': UserSerializer(order.user).data,
            'already': True,
            'need_pay': False,
        }
    if order.status == 'cancelled':
        raise ValueError('订单已取消')

    order.status = 'paid'
    order.paid_at = timezone.now()
    order.save(update_fields=['status', 'paid_at'])
    user = order.user
    activate_plan(user, order.plan, order.months)
    user.refresh_from_db()

    amount = f'{Decimal(order.amount):.2f}'
    expire = user.membership_expire_at
    expire_txt = timezone.localtime(expire).strftime('%Y-%m-%d %H:%M') if expire else '长期'
    channel = '支付宝' if order.channel == 'alipay' else '微信支付'
    extra = {
        'order_id': order.id,
        'trade_no': order.trade_no,
        'plan': order.plan.name,
        'user_id': user.id,
    }
    push_notification(
        user.id,
        title='会员已开通',
        body=f'你已成功开通{order.plan.name}（{order.months}个月），有效期至 {expire_txt}',
        level='success',
        kind='membership',
        extra=extra,
    )
    if Decimal(order.amount) <= 0:
        admin_body = f'用户「{user.username}」已开通{order.plan.name}'
    else:
        admin_body = f'用户「{user.username}」通过{channel}支付 ¥{amount}，已升级为{order.plan.name}'
    notify_admins(
        title='会员支付成功',
        body=admin_body,
        extra=extra,
        exclude_id=user.id,
    )
    return {
        'order': MembershipOrderSerializer(order).data,
        'user': UserSerializer(user).data,
        'already': False,
        'need_pay': False,
    }
