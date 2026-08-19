from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.RegisterView.as_view()),
    path('login/', views.LoginView.as_view()),
    path('refresh/', views.AuthRefreshView.as_view()),
    path('me/', views.MeView.as_view()),
    path('preference/', views.PreferenceView.as_view()),
    path('stats/', views.ProfileStatsView.as_view()),
    path('users/search/', views.UserSearchView.as_view()),
    path('notifications/', views.NotificationListView.as_view()),
    path('notifications/read-all/', views.NotificationReadAllView.as_view()),
    path('notifications/<int:pk>/read/', views.NotificationReadView.as_view()),
    path('membership/plans/', views.MembershipPlanListView.as_view()),
    path('membership/checkout/', views.MembershipCheckoutView.as_view()),
    path('membership/orders/<int:pk>/', views.MembershipPayView.as_view()),
    path('membership/orders/<int:pk>/pay/', views.MembershipPayView.as_view()),
    path('membership/orders/<int:pk>/cancel/', views.MembershipCancelView.as_view()),
    path('quota/', views.MyQuotaView.as_view()),
    path('admin/users/', views.AdminUserListView.as_view()),
    path('admin/users/<int:pk>/', views.AdminUserDetailView.as_view()),
    path('admin/users/<int:pk>/reset-password/', views.AdminUserResetPasswordView.as_view()),
    path('admin/plans/', views.AdminPlanView.as_view()),
    path('admin/plans/<int:pk>/', views.AdminPlanView.as_view()),
    path('admin/orders/', views.AdminOrderListView.as_view()),
]
