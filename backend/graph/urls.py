from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('nodes', views.GraphNodeViewSet, basename='graph-node')
router.register('edges', views.GraphEdgeViewSet, basename='graph-edge')

urlpatterns = [
    path('data/', views.GraphDataView.as_view()),
    path('search/', views.GraphSearchView.as_view()),
    path('recommend/', views.GraphRecommendView.as_view()),
    path('sync/', views.SyncFromLibraryView.as_view()),
    path('', include(router.urls)),
]
