from django.urls import path
from . import views

urlpatterns = [
    path('backtest', views.BackTestView.as_view(), name='longshort-backtest'),
    path('search-method', views.search_method, name='search-method'),
    path('update-stock-numbers', views.update_stock_numbers, name='update-stock-numbers'),
    path('export-csv', views.export_csv, name='export-csv'),
]
