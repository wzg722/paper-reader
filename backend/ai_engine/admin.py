from django.contrib import admin
from .models import AIConversation, AIMessage

admin.site.register(AIConversation)
admin.site.register(AIMessage)
