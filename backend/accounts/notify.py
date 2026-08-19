"""Create in-app notifications for a user."""
from __future__ import annotations


def push_notification(
    user_id: int,
    *,
    title: str,
    body: str = '',
    level: str = 'info',
    kind: str = 'system',
    paper_id: int | None = None,
    job_id: int | None = None,
    extra=None,
):
    from accounts.models import UserNotification
    if job_id:
        exists = UserNotification.objects.filter(user_id=user_id, job_id=job_id, kind=kind).exists()
        if exists:
            return None
    return UserNotification.objects.create(
        user_id=user_id,
        title=(title or '通知')[:120],
        body=(body or '')[:500],
        level=level or 'info',
        kind=kind or 'system',
        paper_id=paper_id,
        job_id=job_id,
        extra=extra,
    )
