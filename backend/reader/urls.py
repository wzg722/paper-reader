from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('highlights', views.HighlightViewSet, basename='highlight')
router.register('notes', views.NoteViewSet, basename='note')
router.register('glossary', views.GlossaryViewSet, basename='glossary')

urlpatterns = [
    path('progress/', views.ReadingProgressView.as_view()),
    path('translate/selection/', views.TranslateSelectionView.as_view()),
    path('translate/paragraphs/', views.TranslateParagraphsView.as_view()),
    path('ocr/', views.OcrScreenshotView.as_view()),
    path('', include(router.urls)),
]
