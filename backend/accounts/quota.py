"""Membership quotas for translation, PDF layout parse, and team sharing."""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

DEFAULT_PLANS = [
    {
        'code': 'free', 'name': '未开通会员', 'daily_translate': 1, 'daily_parse': 1,
        'page_limit': 10, 'price_month': Decimal('0'), 'team_share_limit': 0,
        'purchasable': False, 'sort': 0,
    },
    {
        'code': 'basic', 'name': '普通会员', 'daily_translate': 1, 'daily_parse': 1,
        'page_limit': 10, 'price_month': Decimal('0'), 'team_share_limit': 0,
        'purchasable': True, 'sort': 1,
    },
    {
        'code': 'baijin', 'name': '白金会员', 'daily_translate': 10, 'daily_parse': 10,
        'page_limit': 10, 'price_month': Decimal('20'), 'team_share_limit': 0,
        'purchasable': True, 'sort': 2,
    },
    {
        'code': 'gold', 'name': '黄金会员', 'daily_translate': 20, 'daily_parse': 20,
        'page_limit': 15, 'price_month': Decimal('30'), 'team_share_limit': 0,
        'purchasable': True, 'sort': 3,
    },
    {
        'code': 'platinum', 'name': '铂金会员', 'daily_translate': 20, 'daily_parse': 20,
        'page_limit': 20, 'price_month': Decimal('40'), 'team_share_limit': 5,
        'purchasable': True, 'sort': 4,
    },
    {
        'code': 'diamond', 'name': '钻石会员', 'daily_translate': 30, 'daily_parse': 30,
        'page_limit': 30, 'price_month': Decimal('50'), 'team_share_limit': -1,
        'purchasable': True, 'sort': 5,
    },
]


def quota_fail(exc):
    from common.response import fail
    return fail(str(exc), code=402, status=403, data={'kind': getattr(exc, 'kind', 'quota')})


class QuotaExceeded(Exception):
    def __init__(self, message: str, kind: str = 'quota'):
        super().__init__(message)
        self.kind = kind


def is_admin(user) -> bool:
    return bool(
        getattr(user, 'is_staff', False)
        or getattr(user, 'is_superuser', False)
        or getattr(user, 'role', '') == '技术负责人'
    )


def ensure_plans():
    from accounts.models import MembershipPlan
    for item in DEFAULT_PLANS:
        MembershipPlan.objects.get_or_create(code=item['code'], defaults=item)
    return list(MembershipPlan.objects.all())


def free_plan():
    from accounts.models import MembershipPlan
    plan = MembershipPlan.objects.filter(code='free').first()
    if plan:
        return plan
    ensure_plans()
    return MembershipPlan.objects.filter(code='free').first()


def active_plan(user):
    from accounts.models import MembershipPlan
    ensure_plans()
    plan = getattr(user, 'membership_plan', None)
    expire = getattr(user, 'membership_expire_at', None)
    if plan and plan.code != 'free':
        if expire is None or expire > timezone.now():
            return plan
    return MembershipPlan.objects.filter(code='free').first() or free_plan()


def _ids(raw) -> list:
    if not isinstance(raw, list):
        return []
    out = []
    for x in raw:
        try:
            out.append(int(x))
        except (TypeError, ValueError):
            continue
    return out


def paper_page_count(paper, abs_path: str | None = None) -> int | None:
    meta = getattr(paper, 'layout_meta', None) or {}
    if isinstance(meta, dict) and meta.get('page_count'):
        try:
            return int(meta['page_count'])
        except (TypeError, ValueError):
            pass
    try:
        pf = paper.files.filter(page_count__isnull=False).first()
        if pf and pf.page_count:
            return int(pf.page_count)
    except Exception:
        pass
    path = abs_path
    if not path:
        try:
            from services.pdf_import import resolve_paper_pdf_path
            path = resolve_paper_pdf_path(paper)
        except Exception:
            path = None
    if not path:
        return None
    try:
        import fitz
        doc = fitz.open(path)
        n = int(doc.page_count or 0)
        doc.close()
        return n or None
    except Exception:
        return None


def limits_for(user) -> dict:
    if is_admin(user):
        return {
            'unlimited': True,
            'plan_id': None,
            'plan_code': 'admin',
            'plan_name': '管理员',
            'purchasable': False,
            'price_month': '0',
            'expire_at': None,
            'daily_translate': None,
            'daily_parse': None,
            'page_limit': None,
            'team_share_limit': -1,
            'override': False,
        }
    plan = active_plan(user)
    expire = getattr(user, 'membership_expire_at', None)
    if not plan or plan.code == 'free':
        expire = None
    translate = plan.daily_translate if plan else 1
    parse = plan.daily_parse if plan else 1
    pages = plan.page_limit if plan else 10
    share = plan.team_share_limit if plan else 0
    override = False
    if user.quota_translate_daily is not None:
        translate = user.quota_translate_daily
        override = True
    if user.quota_parse_daily is not None:
        parse = user.quota_parse_daily
        override = True
    if user.quota_page_limit is not None:
        pages = user.quota_page_limit
        override = True
    if user.quota_team_share is not None:
        share = user.quota_team_share
        override = True
    return {
        'unlimited': False,
        'plan_id': plan.id if plan else None,
        'plan_code': plan.code if plan else 'free',
        'plan_name': plan.name if plan else '未开通会员',
        'purchasable': bool(plan.purchasable) if plan else False,
        'price_month': str(plan.price_month if plan else 0),
        'expire_at': expire.isoformat() if expire else None,
        'daily_translate': int(translate),
        'daily_parse': int(parse),
        'page_limit': int(pages),
        'team_share_limit': int(share),
        'override': override,
    }


def _today_usage(user):
    from accounts.models import DailyUsage
    day = timezone.localdate()
    row, _ = DailyUsage.objects.get_or_create(user=user, day=day, defaults={'translate_ids': [], 'parse_ids': []})
    return row


def _month_usage(user):
    from accounts.models import MonthlyUsage
    now = timezone.localtime()
    row, _ = MonthlyUsage.objects.get_or_create(
        user=user, year=now.year, month=now.month, defaults={'team_share_count': 0},
    )
    return row


def snapshot(user) -> dict:
    lim = limits_for(user)
    if lim['unlimited']:
        lim.update({
            'translate_used': 0,
            'parse_used': 0,
            'team_share_used': 0,
            'translate_left': None,
            'parse_left': None,
            'team_share_left': None,
        })
        return lim
    usage = _today_usage(user)
    month = _month_usage(user)
    t_ids = _ids(usage.translate_ids)
    p_ids = _ids(usage.parse_ids)
    share_used = int(month.team_share_count or 0)
    t_lim = lim['daily_translate']
    p_lim = lim['daily_parse']
    s_lim = lim['team_share_limit']
    lim.update({
        'translate_used': len(t_ids),
        'parse_used': len(p_ids),
        'team_share_used': share_used,
        'translate_left': max(0, t_lim - len(t_ids)),
        'parse_left': max(0, p_lim - len(p_ids)),
        'team_share_left': None if s_lim < 0 else max(0, s_lim - share_used),
    })
    return lim


def _check_pages(lim: dict, pages: int | None):
    cap = lim.get('page_limit')
    if lim.get('unlimited') or cap is None or pages is None:
        return
    if int(pages) > int(cap):
        raise QuotaExceeded(
            f'该论文共 {int(pages)} 页，当前套餐限制 {int(cap)} 页。请升级会员后再解析/翻译。',
            kind='pages',
        )


def assert_can_parse(user, paper_id=None, page_count: int | None = None):
    lim = limits_for(user)
    _check_pages(lim, page_count)
    if lim.get('unlimited'):
        return
    usage = _today_usage(user)
    ids = _ids(usage.parse_ids)
    if paper_id and int(paper_id) in ids:
        return
    if len(ids) >= int(lim['daily_parse']):
        raise QuotaExceeded(
            f'今日版面解析次数已用完（{len(ids)}/{lim["daily_parse"]}）。升级会员可提升额度。',
            kind='quota',
        )


def consume_parse(user, paper_id, page_count: int | None = None):
    lim = limits_for(user)
    _check_pages(lim, page_count)
    if lim.get('unlimited') or not paper_id:
        return
    with transaction.atomic():
        from accounts.models import DailyUsage
        day = timezone.localdate()
        row, _ = DailyUsage.objects.select_for_update().get_or_create(
            user=user, day=day, defaults={'translate_ids': [], 'parse_ids': []},
        )
        ids = _ids(row.parse_ids)
        pid = int(paper_id)
        if pid in ids:
            return
        if len(ids) >= int(lim['daily_parse']):
            raise QuotaExceeded(
                f'今日版面解析次数已用完（{len(ids)}/{lim["daily_parse"]}）。升级会员可提升额度。',
                kind='quota',
            )
        ids.append(pid)
        row.parse_ids = ids
        row.save(update_fields=['parse_ids'])


def consume_translate(user, paper_id, page_count: int | None = None):
    lim = limits_for(user)
    _check_pages(lim, page_count)
    if lim.get('unlimited') or not paper_id:
        return
    with transaction.atomic():
        from accounts.models import DailyUsage
        day = timezone.localdate()
        row, _ = DailyUsage.objects.select_for_update().get_or_create(
            user=user, day=day, defaults={'translate_ids': [], 'parse_ids': []},
        )
        ids = _ids(row.translate_ids)
        pid = int(paper_id)
        if pid in ids:
            return
        if len(ids) >= int(lim['daily_translate']):
            raise QuotaExceeded(
                f'今日翻译次数已用完（{len(ids)}/{lim["daily_translate"]}）。升级会员可提升额度。',
                kind='quota',
            )
        ids.append(pid)
        row.translate_ids = ids
        row.save(update_fields=['translate_ids'])


def consume_team_share(user):
    lim = limits_for(user)
    if lim.get('unlimited'):
        return
    cap = int(lim['team_share_limit'])
    if cap == 0:
        raise QuotaExceeded('当前套餐无法团队共享。升级铂金/钻石会员后可使用。', kind='team_share')
    if cap < 0:
        return
    with transaction.atomic():
        from accounts.models import MonthlyUsage
        now = timezone.localtime()
        row, _ = MonthlyUsage.objects.select_for_update().get_or_create(
            user=user, year=now.year, month=now.month, defaults={'team_share_count': 0},
        )
        used = int(row.team_share_count or 0)
        if used >= cap:
            raise QuotaExceeded(
                f'本月团队共享次数已用完（{used}/{cap}）。升级钻石会员可不限次数。',
                kind='team_share',
            )
        row.team_share_count = used + 1
        row.save(update_fields=['team_share_count'])


def prepare_parse(user, paper, abs_path: str | None = None):
    pages = paper_page_count(paper, abs_path)
    consume_parse(user, paper.id, page_count=pages)


def prepare_translate(user, paper):
    pages = paper_page_count(paper)
    consume_translate(user, paper.id, page_count=pages)


def activate_plan(user, plan, months: int = 1):
    months = max(1, int(months or 1))
    now = timezone.now()
    start = now
    if (
        user.membership_plan_id == plan.id
        and user.membership_expire_at
        and user.membership_expire_at > now
    ):
        start = user.membership_expire_at
    user.membership_plan = plan
    user.membership_expire_at = start + timedelta(days=30 * months)
    user.save(update_fields=['membership_plan', 'membership_expire_at', 'updated_at'])
    return user
