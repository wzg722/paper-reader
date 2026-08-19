from django.contrib import admin
from .models import Category, Paper, PaperFile, UserSource, ImportRecord, PaperShare

admin.site.register(Category)
admin.site.register(Paper)
admin.site.register(PaperFile)
admin.site.register(UserSource)
admin.site.register(ImportRecord)
admin.site.register(PaperShare)
