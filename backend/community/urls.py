from django.urls import path
from . import views

urlpatterns = [
    path('feed/', views.FeedView.as_view()),
    path('paper/<int:paper_id>/', views.PaperCommunityView.as_view()),
    path('like/', views.LikeView.as_view()),
    path('comments/', views.CommentView.as_view()),
]
