from django.urls import path
from .views import account_username_validation

urlpatterns = [
    path('', account_username_validation, name='account_username_validation'),
]
