from django.urls import path
from . import views

urlpatterns = [
    path("backtest/", views.BackTestView.as_view(), name="longshort-backtest"),
    path("backtest/search-method", views.search_method, name="search-method"),
    path(
        "backtest/update-stock-numbers", views.update_stock_numbers, name="update-stock-numbers"
    ),
    path("backtest/export-csv", views.export_csv, name="export-csv"),
    path("backtest/strategies-list/add", views.add_strategies_list, name="add-strategies-list"),
    path("backtest/strategy/add", views.add_strategies_to_list, name="add-strategy-to-list"),
]
