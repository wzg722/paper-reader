from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPreference, Friendship, UserNotification, MembershipPlan, MembershipOrder


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'role', 'status', 'created_at')
    list_filter = ('role', 'status')
    search_fields = ('username', 'email')
    ordering = ('-id',)
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('资料', {'fields': ('username', 'id_card', 'avatar', 'role', 'research_direction', 'status')}),
        ('会员', {'fields': (
            'membership_plan', 'membership_expire_at',
            'quota_translate_daily', 'quota_parse_daily', 'quota_page_limit', 'quota_team_share',
        )}),
        ('权限', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'username', 'password1', 'password2')}),
    )


admin.site.register(UserPreference)
admin.site.register(Friendship)
admin.site.register(UserNotification)
admin.site.register(MembershipPlan)
admin.site.register(MembershipOrder)
