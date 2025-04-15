from django.urls import path
from .views import home, profile

urlpatterns = [
    path('', home, name='client_area'),
    path('profile', profile, name='client_profile'),
]
