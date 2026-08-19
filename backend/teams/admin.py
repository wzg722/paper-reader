from django.contrib import admin
from .models import Team, TeamMember, TeamApplication

admin.site.register(Team)
admin.site.register(TeamMember)
admin.site.register(TeamApplication)
