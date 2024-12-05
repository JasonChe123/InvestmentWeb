from django.urls import path
from . import views


urlpatterns = [
    path('', views.PerformanceView.as_view(), name='performance'),
]
