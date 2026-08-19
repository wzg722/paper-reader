from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet, basename='category')
router.register('sources', views.UserSourceViewSet, basename='source')
router.register('', views.PaperViewSet, basename='paper')

urlpatterns = [
    path('arxiv/search/', views.ArxivSearchView.as_view()),
    path('discover/recommend/', views.DiscoverRecommendView.as_view()),
    path('discover/hot/', views.DiscoverHotView.as_view()),
    path('shares/', views.ShareManageView.as_view()),
    path('backup/', views.BackupView.as_view()),
    path('', include(router.urls)),
]
