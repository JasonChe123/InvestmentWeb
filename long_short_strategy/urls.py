from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from . import views


urlpatterns = [
    path('', views.DashboardView.as_view(), name='longshort'),
    path('backtest', views.BackTestView.as_view(), name='longshort-backtest'),
    path('search-method', csrf_exempt(views.search_method), name='search-method'),
]
