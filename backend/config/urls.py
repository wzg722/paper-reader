from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
    path('api/auth/', include('accounts.urls')),
    path('api/papers/', include('papers.urls')),
    path('api/reader/', include('reader.urls')),
    path('api/community/', include('community.urls')),
    path('api/teams/', include('teams.urls')),
    path('api/ai/', include('ai_engine.urls')),
    path('api/graph/', include('graph.urls')),
    path('api/vault/', include('vault.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
