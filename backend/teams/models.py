from django.conf import settings
from django.db import models


class Team(models.Model):
    name = models.CharField(max_length=50)
    description = models.CharField(max_length=500, blank=True, null=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='owned_teams')
    avatar = models.CharField(max_length=255, blank=True, null=True, default='👥')
    invite_code = models.CharField(max_length=20, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'teams'

    @property
    def member_count(self):
        return self.members.count()


class TeamMember(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_memberships')
    role = models.CharField(max_length=20, default='member')  # owner/admin/member
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_members'
        unique_together = ('team', 'user')


class TeamApplication(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='applications')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='team_applications')
    status = models.CharField(max_length=20, default='pending')  # pending/approved/rejected
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'team_applications'
