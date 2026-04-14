from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('apps.dashboard.urls', namespace='dashboard')),
    path('clients/', include('apps.clients.urls', namespace='clients')),
    path('loans/', include('apps.loans.urls', namespace='loans')),
    path('scoring/', include('apps.scoring.urls', namespace='scoring')),
    path('documents/', include('apps.documents.urls', namespace='documents')),
    path('alerts/', include('apps.alerts.urls', namespace='alerts')),
    path('auth/', include('django.contrib.auth.urls')),
    path('api/', include('apps.dashboard.api_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
