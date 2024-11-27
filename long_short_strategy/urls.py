from django.urls import path
from . import views


urlpatterns = [
    path('', views.DashboardView.as_view(), name='longshort'),
    path('backtest', views.BackTestView.as_view(), name='longshort-backtest'),
    path('search-method', views.search_method, name='search-method'),
    path('export-csv', views.export_csv, name='export-csv'),
]
