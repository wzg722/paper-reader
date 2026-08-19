from django.urls import path
from . import views

urlpatterns = [
    path('summarize/', views.SummarizePaperView.as_view()),
    path('ask/', views.AskView.as_view()),
    path('intro/', views.GenerateIntroView.as_view()),
    path('test-engine/', views.TestEngineView.as_view()),
    path('conversations/', views.ConversationListView.as_view()),
]
