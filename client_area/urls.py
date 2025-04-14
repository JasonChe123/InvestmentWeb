from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
from .views import home, profile

urlpatterns = [
    path('', home, name='client_area'),
    path('profile', profile, name='client_profile'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)  # pragma: no cover
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # pragma: no cover