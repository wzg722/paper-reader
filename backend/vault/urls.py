from django.urls import path
from . import views

urlpatterns = [
    path('overview/', views.VaultOverviewView.as_view()),
    path('export/obsidian/', views.ObsidianExportView.as_view()),
]
