from django.urls import path
from . import views

urlpatterns = [
    path('us-economy', views.us_economy, name='us-economy'),
]
