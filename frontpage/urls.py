from django.urls import path
from .views import FrontPageView


urlpatterns = [
    path('', FrontPageView.as_view(), name='frontpage'),
]