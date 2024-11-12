from django.urls import path
from . import views


urlpatterns = [
    path('', views.DashboardView.as_view(), name='longshort'),
    path('backtest/', views.BackTestView.as_view(), name='longshort-backtest'),
]
